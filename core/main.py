import asyncio
import logging
import string
import sys
import tempfile
import signal

import numpy as np
import soundfile as sf
import sounddevice as sd

from core.config import settings
from core.router import route
from db.database import init_db, close_db
from db.cache import close_redis, cache_llm_response, get_cached_llm_response
from llm.memory import SessionMemory
from llm.ollama import OllamaClient
from llm.translator import Translator
from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from voice.wake import WakeWordDetector


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("zari")


class ZariPipeline:
    def __init__(self):
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.llm = OllamaClient()
        self.memory = SessionMemory()
        self.wake = WakeWordDetector()
        self.translator = Translator() if settings.enable_translation else None

        self.audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.text_queue: asyncio.Queue[str] = asyncio.Queue()
        self.response_queue: asyncio.Queue[str] = asyncio.Queue()

        self.running = False

    async def init(self):
        await init_db()
        await self.memory.init()

        if settings.enable_translation:
            await self.memory.system(
                "You are Zari — a personal AI assistant. You speak in English. "
                "Keep responses short, clear, and helpful."
            )
        else:
            await self.memory.system(
                "Sen Zari — o'zbek tilida gapiradigan shaxsiy AI yordamchi. "
                "Foydalanuvchiga doim o'zbek tilida, qisqa va aniq javob ber."
            )

    async def audio_worker(self):
        while self.running:
            try:
                audio_data = await self.audio_queue.get()

                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                sf.write(tmp.name, audio_array, self.wake.sample_rate)

                text = await asyncio.to_thread(self.stt.transcribe, tmp.name)
                log.info("STT: %s", repr(text))

                if not text.strip():
                    log.info("Bo'sh ovoz, tashlandi")
                    continue

                words = text.strip().lower().split()
                wake = settings.wake_word.lower()
                words_clean = [w.strip(string.punctuation) for w in words]

                if words_clean[0] == wake:
                    command = " ".join(words[1:]).strip().strip(string.punctuation) or "salom"
                    log.info("Wake word aniqlandi: '%s'", command)
                    await self.text_queue.put(command)
                elif wake in words_clean:
                    idx = words_clean.index(wake)
                    command = " ".join(words[idx + 1:]).strip().strip(string.punctuation) or "salom"
                    log.info("Wake word (o'rtada): '%s'", command)
                    await self.text_queue.put(command)
                else:
                    log.info("Wake word topilmadi, tashlandi")
            except Exception as e:
                log.error("audio_worker xatosi: %s", e, exc_info=True)

    async def llm_worker(self):
        while self.running:
            try:
                text = await self.text_queue.get()
                intent = route(text)
                log.info("Intent: %s", intent)

                llm_input = text
                if self.translator:
                    llm_input = await asyncio.to_thread(self.translator.uz_to_en, text)
                    log.info("UZ->EN: '%s' -> '%s'", text, llm_input)

                await self.memory.add("user", llm_input)
                try:
                    cached = await get_cached_llm_response(llm_input)
                    if cached:
                        response = cached
                        log.info("LLM (cache): %s", response)
                    else:
                        response = await asyncio.to_thread(self.llm.chat, self.memory.get())
                        await cache_llm_response(llm_input, response)
                        log.info("LLM: %s", response)
                except Exception as e:
                    log.error("LLM xatosi (Ollama ishlayaptimi?): %s", e, exc_info=True)
                    response = "Kechirasiz, hozir javob bera olmayman. Ollama bilan bog'liq muammo bor."
                await self.memory.add("assistant", response)

                output = response
                if self.translator:
                    output = await asyncio.to_thread(self.translator.en_to_uz, response)
                    log.info("EN->UZ: '%s' -> '%s'", response, output)

                await self.response_queue.put(output)
            except Exception as e:
                log.error("llm_worker xatosi: %s", e, exc_info=True)

    async def tts_worker(self):
        while self.running:
            try:
                response = await self.response_queue.get()
                log.info("TTS: %s", response)
                await self.tts.speak(response)
            except Exception as e:
                log.error("TTS xatosi: %s", e, exc_info=True)

    async def wake_loop(self):
        if self.wake.device is None:
            log.critical("Mikrofon topilmadi! Dockerda --text rejimini sinab ko'ring: docker compose run zari python -m core.main --text")
            return

        log.info("'%s' so'zi kutilmoqda (%d Hz)...", settings.wake_word.capitalize(), self.wake.sample_rate)
        while self.running:
            try:
                audio_data = await asyncio.to_thread(self.wake.wait_for_speech)
                if audio_data:
                    log.info("Ovoz aniqlandi!")
                    await self.audio_queue.put(audio_data)
                else:
                    log.debug("wait_for_speech None qaytardi (davom etiladi)")
            except Exception as e:
                log.error("Wake loop xatosi: %s", e, exc_info=True)
                await asyncio.sleep(1)

    async def start(self):
        self.running = True
        workers = [
            asyncio.create_task(self.wake_loop()),
            asyncio.create_task(self.audio_worker()),
            asyncio.create_task(self.llm_worker()),
            asyncio.create_task(self.tts_worker()),
        ]
        log.info("Zari ishga tushdi")
        await asyncio.gather(*workers)

    async def stop(self):
        self.running = False
        log.info("Zari to'xtadi")


def test_mic():
    wake = WakeWordDetector()
    if wake.device is None:
        log.error("Mikrofon topilmadi!")
        return

    log.info("MIKROFON TESTI: 5 soniya ovoz yozilmoqda...")
    log.info("Iltimos, '%s bu sinov' deb gapiring", settings.wake_word)

    rms_values = []
    speech_frames = 0
    total_frames = 0
    sample_rate = wake.sample_rate
    frame_samples = wake.frame_samples

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=wake.device,
            blocksize=frame_samples,
        ) as stream:
            for i in range(int(5.0 * 1000 / wake.frame_ms)):
                audio, _ = stream.read(frame_samples)
                audio_bytes = audio.tobytes()
                rms = wake._rms(audio)
                rms_values.append(rms)

                is_speech = False
                if len(audio_bytes) >= wake.frame_size:
                    is_speech = wake.vad.is_speech(audio_bytes, sample_rate)
                    if is_speech:
                        speech_frames += 1
                total_frames += 1

                if i % 33 == 0:
                    log.info("  RMS=%.1f, VAD=%s", rms, "SPEECH" if is_speech else "silence")

    except Exception as e:
        log.error("Xato: %s", e)
        return

    avg_rms = np.mean(rms_values) if rms_values else 0
    max_rms = max(rms_values) if rms_values else 0
    speech_pct = (speech_frames / total_frames * 100) if total_frames > 0 else 0

    log.info("=== NATIJALAR ===")
    log.info("O'rtacha RMS: %.1f", avg_rms)
    log.info("Maksimal RMS: %.1f", max_rms)
    log.info("VAD speech: %d/%d (%.0f%%)", speech_frames, total_frames, speech_pct)
    log.info("Eshik qiymati (threshold): %d", wake.energy_threshold)

    if max_rms < wake.energy_threshold:
        log.warning("MUAMMO: RMS (% .1f) < threshold (%d)!", max_rms, wake.energy_threshold)
        log.warning("Sabab: Mikrofon juda past ovoz oladi yoki umuman ishlamayapti")
        log.warning("Tuzatish: `amixer sset 'Mic' 80%` yoki `pavucontrol` bilan mikrofon balandligini oshiring")
    elif speech_pct > 10:
        log.info("NATIJA: Mikrofon ishlayapti! VAD ovozni taniyapti")
    else:
        log.warning("MUAMMO: VAD ovozni tanimadi. Mikrofon balandligini tekshiring")


async def main_async():
    pipeline = ZariPipeline()

    def shutdown():
        pipeline.running = False

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    await pipeline.init()
    log.info("Ovoz rejimi ishga tushdi")
    try:
        await pipeline.start()
    finally:
        await close_db()
        await close_redis()
        await pipeline.stop()


def list_devices():
    log.info("Mavjud audio qurilmalar:")
    for i, dev in enumerate(sd.query_devices()):
        log.info("  [%d] %s", i, dev["name"])
    log.info("Default kirish: %s", sd.default.device[0])
    log.info("Default chiqish: %s", sd.default.device[1])


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test-mic":
        test_mic()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--list-devices":
        list_devices()
        return

    asyncio.run(main_async())


if __name__ == "__main__":
    main()
