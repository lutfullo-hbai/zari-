"""
Zari CLI — kirish nuqtasi (ovoz rejimi, matn rejimi, diagnostika).

python -m core.main            → ovoz rejimi
python -m core.main --text     → matn rejimi
python -m core.main --test-mic → mikrofon testi
python -m core.main --list-devices
"""

import asyncio
import signal
import sys

import numpy as np
import sounddevice as sd
from voice.wake_word import WakeWordDetector

from core.config import settings
from core.logging import get_logger
from core.main import ZariPipeline
from core.messages import Incoming
from db.cache import close_redis
from db.database import close_db

log = get_logger("zari.cli")


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


async def text_input_worker(pipeline):
    loop = asyncio.get_event_loop()
    while pipeline.running:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            await asyncio.sleep(0.1)
            continue
        text = line.strip()
        if text:
            log.info("TEXT INPUT: %s", text)
            await pipeline.text_queue.put(Incoming(text=text, source="voice"))


async def text_output_worker(pipeline):
    while pipeline.running:
        try:
            response = await asyncio.wait_for(pipeline.response_queue.get(), timeout=1.0)
            if response:
                print(f"\nZari: {response}\n")
        except TimeoutError:
            continue
        except Exception as e:
            log.error("Output worker xatosi: %s", e)


async def main_text_async():
    pipeline = ZariPipeline()

    def shutdown():
        pipeline.running = False

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    await pipeline.init()
    log.info("Matn rejimi ishga tushdi. Savolingizni yozing (Ctrl+C chiqish):")

    pipeline.running = True
    workers = [
        asyncio.create_task(text_input_worker(pipeline)),
        asyncio.create_task(pipeline.llm_worker()),
        asyncio.create_task(text_output_worker(pipeline)),
    ]
    try:
        await asyncio.gather(*workers)
    finally:
        pipeline.running = False
        for w in workers:
            w.cancel()
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
    if len(sys.argv) > 1 and sys.argv[1] == "--text":
        asyncio.run(main_text_async())
        return

    asyncio.run(main_async())


if __name__ == "__main__":
    main()
