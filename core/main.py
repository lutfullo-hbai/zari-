import asyncio
import signal
import sys
import tempfile
import threading
import uuid
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from core.config import settings
from core.dialog_state import DialogManager
from core.logging import get_logger
from core.messages import Incoming, ResponseRouter
from core.rate_limiter import rate_limiter
from core.router import match_intents, route
from core.scheduler import init_scheduler_table, run_scheduler_loop
from db.cache import cache_llm_response, close_redis, get_cached_llm_response
from db.database import close_db, init_db
from llm.factory import create_llm_client
from llm.habits import analyze_and_store_habits
from llm.long_term_memory import retrieve_context
from llm.memory import SessionMemory
from llm.persona import UserPersona
from llm.translator import Translator
from skills.base import BaseSkill
from skills.email import EmailSkill
from skills.loader import SkillLoader
from skills.search import SearchSkill
from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from voice.vad import VAD
from voice.wake import WakeWordDetector

log = get_logger("zari")


class ZariPipeline:
    def __init__(self):
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.memory = SessionMemory()
        self.wake = WakeWordDetector()
        self.vad = VAD()
        self.persona = UserPersona()
        self.dialog = DialogManager()

        self.llm = create_llm_client()
        self.translator = Translator(client=self.llm) if settings.enable_translation else None

        self._init_skills()

        self.router = ResponseRouter()
        self._background_tasks: set[asyncio.Task] = set()
        self.audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.text_queue: asyncio.Queue[Incoming] = asyncio.Queue()
        self.response_queue: asyncio.Queue[str] = asyncio.Queue()

        self.running = False
        self._wake_stop_event = threading.Event()
        self._tts_is_speaking = threading.Event()
        self._wake_cooldown = 3.0

    def _init_skills(self):
        loader = SkillLoader()

        self.search_skill = SearchSkill(llm=self.llm)
        self.email_skill = EmailSkill(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_username=settings.smtp_username,
            smtp_password=settings.smtp_password,
            smtp_use_tls=settings.smtp_use_tls,
            sender_address=settings.sender_address or settings.email_address,
            default_recipient=settings.default_recipient or settings.email_address,
        )

        self._skill_map: dict[str, BaseSkill] = {
            "search": self.search_skill,
            "email": self.email_skill,
        }

        for name, instance in loader.instantiate_all().items():
            if name not in ("search", "email"):
                self._skill_map[name] = instance

        log.info("Skills loaded: %s", ", ".join(sorted(self._skill_map.keys())))

    def _get_skill(self, name: str) -> BaseSkill | None:
        return self._skill_map.get(name)

    async def _run_skill(self, skill: BaseSkill, text: str) -> str | None:
        try:
            result = await skill.execute_with_retry(text)
            if result:
                log.info("%s: %s", skill.__class__.__name__, result["response"])
                return result["response"]
        except Exception as e:
            log.error("%s skill error: %s", skill.__class__.__name__, e)
        return None

    async def init(self):
        await init_db()
        await self.persona.ensure_table()
        await self.memory.init()

        await self.memory.system(
            "Sen Zari — o'zbek tilida gapiradigan shaxsiy AI yordamchi. "
            "Sen Zari'san, Jervis, Cortana yoki boshqa hech qanday AI EMAS. "
            "Hech qachon o'zini boshqa AI deb atama.\n\n"
            "MUHIM QOIDALAR:\n"
            "1. Doim o'zbek tilida, qisqa va aniq javob ber.\n"
            "2. Agar so'z noto'g'ri tushungan bo'lsa, qayta so'ra: 'Men tushunmadim, qaytadan ayting'\n"
            "3. Hech qachon o'ylab chiqarilgan (hallucination) ma'lumot bermaslik. "
            "Agar bilmasang, 'Bilmayman' yoki 'Aniq ma'lumotim yo'q' deb aytil.\n"
            "4. Noto'g'ri transkripsiyani to'g'irlashga harakat qil. "
            "Masalan: 'enxte' → 'Einstein', 'telefram' → 'Telegram' bo'lishi mumkin.\n"
            "5. Faqat aniq, ishonchli ma'lumot ber. Shubhali bo'lsa, foydalanuvchidan qayta so'ra.\n"
            "6. Uzoq va murakkab javob bermaslik. Qisqa va tushunarli javob ber."
        )

        persona_text = await self.persona.get_system_text()
        if persona_text:
            await self.memory.add("system", persona_text)
            log.info("Persona context injected into memory")

    async def ask(self, text: str, timeout: float = 65.0) -> str:
        """
        Web so'rovi uchun — javobni o'z waiter'i orqali kutadi.

        Correlation ID tufayli parallel so'rovlar javoblari
        bir-biri bilan almashib qolmaydi.
        """
        request_id = uuid.uuid4().hex[:12]
        future = self.router.register(request_id)
        try:
            await self.text_queue.put(
                Incoming(text=text, source="web", request_id=request_id)
            )
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            raise
        finally:
            self.router.unregister(request_id)

    async def _respond(self, text: str, request_id: str | None) -> None:
        """Javobni to'g'ri manbaga yetkazadi."""
        delivered = self.router.resolve(request_id, text)
        if not delivered:
            await self.response_queue.put(text)

    def spawn_background(self, coro, name: str = "background") -> asyncio.Task:
        """
        Fire-and-forget task — kuchli referens bilan.

        Referens saqlanmasa, Python taskni GC qilishi mumkin
        (asyncio dokumentatsiyasidagi ma'lum tuzoq).
        """
        task: asyncio.Task = asyncio.create_task(coro, name=name)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def audio_worker(self):
        while self.running:
            try:
                audio_data = await asyncio.wait_for(self.audio_queue.get(), timeout=1.0)
                if not audio_data:
                    log.debug("Empty audio data, skipping")
                    continue

                if not self.vad.detect_speech(audio_data, self.wake.sample_rate):
                    log.debug("VAD: no speech detected, skipping")
                    continue

                tmp = None
                try:
                    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                    sf.write(tmp.name, audio_array, self.wake.sample_rate)

                    text = await asyncio.to_thread(self.stt.transcribe, tmp.name)
                    log.info("STT: %s", repr(text))

                    if not text.strip():
                        log.debug("Empty transcription, skipping")
                        continue

                    await self.text_queue.put(
                        Incoming(text=text.strip(), source="voice")
                    )
                except Exception as e:
                    log.error("Audio processing error: %s", e, exc_info=True)
                finally:
                    if tmp is not None:
                        try:
                            Path(tmp.name).unlink()
                        except Exception:
                            pass
            except TimeoutError:
                continue
            except Exception as e:
                log.error("Audio worker error: %s", e, exc_info=True)

    # === llm_worker helper methods ===

    async def _handle_dialog(
        self, text: str, request_id: str | None
    ) -> tuple[bool, str | None, str | None]:
        if self.dialog.is_awaiting_confirm:
            decision = self.dialog.handle_confirm_response(text)
            if decision is True:
                text = self.dialog.pending_text or text
                intent = self.dialog.pending_intent or route(text)
                self.dialog.reset()
                return False, text, intent
            elif decision is False:
                await self._respond("Bekor qilindi.", request_id)
                self.dialog.reset()
                return True, None, None
            else:
                await self._respond(
                    "Iltimos, ha yoki yo'q deb javob bering.", request_id
                )
                return True, None, None

        if self.dialog.is_active:
            still_needed = self.dialog.add_param(text)
            if still_needed:
                await self._respond(still_needed, request_id)
                return True, None, None
            text = self.dialog.enriched_text()
            intent = self.dialog.pending_intent or route(text)
            self.dialog.reset()
            return False, text, intent

        return False, text, None

    async def _translate_input(self, text: str) -> str:
        if not self.translator:
            return text
        try:
            translated = await self.translator.uz_to_en_async(text)
            log.info("UZ->EN: '%s' -> '%s'", text, translated)
            return translated
        except Exception as e:
            log.error("Translation error: %s", e)
            return text

    async def _translate_output(self, response: str, skill_responded: bool) -> str:
        if not self.translator or skill_responded:
            return response
        try:
            translated = await self.translator.en_to_uz_async(response)
            log.info("EN->UZ: '%s' -> '%s'", response, translated)
            return translated
        except Exception as e:
            log.error("Output translation error: %s", e)
            return response

    async def _execute_skill_for_intent(
        self, intent: str, text: str, request_id: str | None
    ) -> tuple[str | None, bool]:
        if intent == "search":
            search_result = await self.search_skill.execute(text)
            if search_result:
                response = search_result["response"]
                ctx = search_result.get("context", "")
                src = search_result.get("source", "")
                await self.memory.add("system", f"Internetdan topilgan ma'lumot ({src}): {ctx}")
                log.info("Search (%s): %s", src, response)
                return response, True
            return None, False

        if intent == "email":
            email_result = await self.email_skill.execute(text)
            if email_result:
                response = email_result["response"]
                log.info("Email: %s", response)
                return response, True
            return None, False

        if intent == "workflow":
            wf_skill = self._get_skill("n8n_workflow")
            if wf_skill:
                if not rate_limiter.is_allowed("N8nWorkflowSkill"):
                    await self._respond(
                        "Kechirasiz, workflow juda tez-tez ishga tushirilmoqda. Biroz kuting.",
                        request_id,
                    )
                    return None, True
                wf_result = await wf_skill.execute(text)
                if wf_result:
                    response = wf_result["response"]
                    ctx = wf_result.get("context", "")
                    src = wf_result.get("source", "")
                    await self.memory.add("system", f"N8N workflow ma'lumoti ({src}): {ctx}")
                    log.info("Workflow: %s", response)
                    return response, True
            return None, False

        skill = self._get_skill(intent)
        if not skill:
            return None, False

        skill_name = skill.__class__.__name__
        if getattr(skill, "requires_confirmation", False):
            if not rate_limiter.is_allowed(skill_name):
                await self._respond(
                    f"Kechirasiz, {skill_name} juda tez-tez ishlatilyapti. "
                    "Biroz kuting va qayta urinib ko'ring.",
                    request_id,
                )
                return None, True

            question = self.dialog.begin_confirm(intent, text, skill)
            await self._respond(question, request_id)
            return None, True

        if intent in ("music", "weather", "timer", "note"):
            if self.dialog.begin(intent, text):
                question = self.dialog.next_question()
                await self._respond(question, request_id)
                return None, True

        response = await self._run_skill(skill, text)
        if response:
            return response, True

        return None, False

    async def _match_and_execute_skills(
        self, text: str, request_id: str | None
    ) -> tuple[str | None, bool]:
        for candidate_intent in match_intents(text):
            response, responded = await self._execute_skill_for_intent(
                candidate_intent, text, request_id
            )
            if responded:
                return response, True
            if response is not None:
                return response, True
        return None, False

    async def _llm_fallback(self, llm_input: str) -> str:
        for _ in range(2):
            try:
                cached = await get_cached_llm_response(llm_input)
                if cached:
                    log.info("LLM (cache): %s", cached)
                    return cached

                messages = self.memory.get()

                context = await retrieve_context(
                    llm_input,
                    exclude_session_id=self.memory.session_id,
                )
                if context:
                    messages = [*messages, {"role": "system", "content": context}]
                    log.info("Kontekst qo'shildi (%d ta qator)", context.count("\n") + 1)

                response = await asyncio.wait_for(
                    self.llm.chat_async(messages, timeout=60),
                    timeout=65,
                )
                await cache_llm_response(llm_input, response)
                log.info("LLM: %s", response)
                return response
            except TimeoutError:
                log.error("LLM timeout")
                return "Kechirasiz, javob bermay ketib qoldi. Iltimos, boshqatdan harakat qiling."
            except Exception as e:
                log.error("LLM error: %s", e, exc_info=True)
                return "Kechirasiz, hozir javob bera olmayman."

        return "Kechirasiz, javob berolmayman."

    async def llm_worker(self):
        while self.running:
            try:
                incoming = await asyncio.wait_for(self.text_queue.get(), timeout=1.0)
                text = incoming.text
                request_id = incoming.request_id

                skip, processed, pending_intent = await self._handle_dialog(
                    text, request_id
                )
                if skip:
                    continue
                if processed is not None:
                    text = processed

                if pending_intent:
                    intent = pending_intent
                else:
                    intent = route(text)
                log.info("Intent: %s | Text: %s", intent, text[:60])

                llm_input = await self._translate_input(text)
                await self.memory.add("user", llm_input)

                if not self.dialog.is_active and not self.dialog.is_awaiting_confirm:
                    self.spawn_background(self.persona.extract_from_conversation(text, self.llm))

                if pending_intent:
                    skill = self._get_skill(pending_intent)
                    if skill:
                        response = await self._run_skill(skill, text)
                        skill_responded = response is not None
                    else:
                        response, skill_responded = None, False
                else:
                    response, skill_responded = await self._match_and_execute_skills(
                        text, request_id
                    )

                if response is None and not skill_responded:
                    response = await self._llm_fallback(llm_input)

                if not response:
                    response = "Kechirasiz, javob berolmayman."

                await self.memory.add("assistant", response)

                output = await self._translate_output(response, skill_responded)
                await self._respond(output, request_id)
            except TimeoutError:
                continue
            except Exception as e:
                log.error("llm_worker xatosi: %s", e, exc_info=True)

    async def tts_worker(self):
        while self.running:
            try:
                response = await asyncio.wait_for(self.response_queue.get(), timeout=1.0)
                if not response or not response.strip():
                    log.warning("Empty response from LLM, skipping TTS")
                    continue

                try:
                    log.info("TTS: %s", response[:100])
                    self._tts_is_speaking.set()
                    await self.tts.speak(response)
                except Exception as e:
                    log.error("TTS speak error: %s", e, exc_info=True)
                finally:
                    self._tts_is_speaking.clear()
            except TimeoutError:
                continue
            except Exception as e:
                log.error("TTS worker error: %s", e, exc_info=True)

    async def wake_loop(self):
        if self.wake.device is None:
            log.critical(
                "Mikrofon topilmadi! Dockerda --text rejimini sinab ko'ring:"
                " docker compose run zari python -m core.main --text"
            )
            while self.running:
                await asyncio.sleep(1)
            return

        import time as time_module
        log.info("'%s' so'zi kutilmoqda (%d Hz)...", settings.wake_word.capitalize(), self.wake.sample_rate)
        self._wake_stop_event.clear()
        last_activation = 0.0
        while self.running:
            try:
                if self._tts_is_speaking.is_set():
                    await asyncio.sleep(0.1)
                    continue
                now = time_module.monotonic()
                if now - last_activation < self._wake_cooldown:
                    await asyncio.sleep(0.1)
                    continue
                audio_data = await asyncio.to_thread(
                    self.wake.wait_for_speech,
                    timeout=1.0,
                    stop_event=self._wake_stop_event,
                )
                if audio_data:
                    log.info("Ovoz aniqlandi!")
                    last_activation = time_module.monotonic()
                    await self.audio_queue.put(audio_data)
            except Exception as e:
                log.error("Wake loop xatosi: %s", e, exc_info=True)
                await asyncio.sleep(0.1)

    async def start(self):
        self.running = True

        async def _spawn(worker_coro, name: str):
            while self.running:
                task = asyncio.create_task(worker_coro())
                try:
                    await task
                except asyncio.CancelledError:
                    log.info("%s cancelled", name)
                    break
                except Exception as e:
                    log.error("Worker %s crashed: %s", name, e, exc_info=True)
                    await asyncio.sleep(1)
                else:
                    log.info("Worker %s exited cleanly, restarting...", name)
                    await asyncio.sleep(0.5)

        self._supervisors = [
            asyncio.create_task(_spawn(self.wake_loop, "wake_loop")),
            asyncio.create_task(_spawn(self.audio_worker, "audio_worker")),
            asyncio.create_task(_spawn(self.llm_worker, "llm_worker")),
            asyncio.create_task(_spawn(self.tts_worker, "tts_worker")),
        ]

        self.spawn_background(self._run_habit_analysis(), "habit-analysis")

        log.info("Zari ishga tushdi (supervised)")

        try:
            await asyncio.gather(*self._supervisors)
        finally:
            self.running = False
            for s in getattr(self, "_supervisors", []):
                s.cancel()

    async def start_text_only(self):
        self.running = True

        async def _spawn(worker_coro, name: str):
            while self.running:
                task = asyncio.create_task(worker_coro())
                try:
                    await task
                except asyncio.CancelledError:
                    log.info("%s cancelled", name)
                    break
                except Exception as e:
                    log.error("Worker %s crashed: %s", name, e, exc_info=True)
                    await asyncio.sleep(1)
                else:
                    log.info("Worker %s exited cleanly, restarting...", name)
                    await asyncio.sleep(0.5)

        self._supervisors = [
            asyncio.create_task(_spawn(self.llm_worker, "llm_worker")),
        ]

        self.spawn_background(self._run_habit_analysis(), "habit-analysis")
        self.spawn_background(self._run_scheduler(), "scheduler")
        log.info("Zari text mode ishga tushdi")

        try:
            await asyncio.gather(*self._supervisors)
        finally:
            self.running = False
            for s in getattr(self, "_supervisors", []):
                s.cancel()

    async def _run_habit_analysis(self):
        try:
            await asyncio.sleep(10)
            facts = await analyze_and_store_habits(self.persona)
            if facts:
                log.info("Odatlar aniqlandi: %s", facts)
        except Exception as e:
            log.warning("Odat tahlili xatosi (kritik emas): %s", e)

    async def _run_scheduler(self):
        try:
            await init_scheduler_table()
            await run_scheduler_loop(self.text_queue, interval=30.0)
        except Exception as e:
            log.warning("Scheduler xatosi (kritik emas): %s", e)

    async def stop(self):
        self.running = False
        self._wake_stop_event.set()
        log.info("Zari shutdown requested")

        supervisors = getattr(self, "_supervisors", [])
        for s in supervisors:
            try:
                s.cancel()
            except Exception:
                pass

        if supervisors:
            try:
                await asyncio.wait_for(asyncio.gather(*supervisors, return_exceptions=True), timeout=5)
            except TimeoutError:
                log.warning("Timeout waiting for supervisor tasks to exit")

        await self._drain_queues(timeout=3)
        log.info("Zari to'xtadi")

    async def _drain_queues(self, timeout: float = 3.0) -> None:
        end = asyncio.get_event_loop().time() + timeout
        queues = [self.audio_queue, self.text_queue, self.response_queue]
        for q in queues:
            try:
                while not q.empty() and asyncio.get_event_loop().time() < end:
                    await asyncio.sleep(0.05)
            except Exception as e:
                log.debug("Error while draining queue: %s", e)


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
            await pipeline.text_queue.put(text)


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
