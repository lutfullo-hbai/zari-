import asyncio
import tempfile
import threading
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from core.brain import AgentBrain
from core.config import settings
from core.dialog_state import DialogManager
from core.logging import get_logger
from core.messages import Incoming, ResponseRouter
from core.router import route
from core.scheduler import run_scheduler_loop
from core.skill_executor import SkillExecutor
from db.cache import cache_llm_response, get_cached_llm_response
from db.database import init_db
from llm.factory import create_llm_client
from llm.habits import analyze_and_store_habits
from llm.long_term_memory import retrieve_context
from llm.memory import SessionMemory
from llm.persona import UserPersona
from llm.response_cleaner import clean_llm_response
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
        self.brain = AgentBrain() if settings.enable_brain else None
        self.translator = Translator(client=self.llm) if settings.enable_translation else None

        self._init_skills()

        self.router = ResponseRouter()
        self.executor = SkillExecutor(
            skills=self._skill_map,
            memory=self.memory,
            dialog=self.dialog,
            brain=self.brain,
            respond=self._respond,
        )
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
            await self.text_queue.put(Incoming(text=text, source="web", request_id=request_id))
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

                    await self.text_queue.put(Incoming(text=text.strip(), source="voice"))
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

    async def _handle_dialog(self, text: str, request_id: str | None) -> tuple[bool, str | None, str | None]:
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
                await self._respond("Iltimos, ha yoki yo'q deb javob bering.", request_id)
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
                response = clean_llm_response(response)
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

                skip, processed, pending_intent = await self._handle_dialog(text, request_id)
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
                    skill = self.executor.get_skill(pending_intent)
                    if skill:
                        response = await self.executor.run_skill(skill, text)
                        skill_responded = response is not None
                    else:
                        response, skill_responded = None, False
                else:
                    response, skill_responded = await self.executor.route_and_execute(text, request_id)

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
        self.spawn_background(self._run_scheduler(), "scheduler")
        # Ovozli rejimda ham scheduler ishlashi kerak — eslatmalar TTS bilan aytiladi

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

    async def _run_habit_analysis(self) -> None:
        """Periodik odat tahlili — har habit_interval soatda bir marta."""
        interval_hours = max(settings.habit_analysis_interval, 0.5)
        first_run = True
        while True:
            try:
                if not first_run:
                    await asyncio.sleep(interval_hours * 3600)
                facts = await analyze_and_store_habits(self.persona)
                if facts:
                    log.info("Odatlar aniqlandi: %s", facts)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Odat tahlili xatosi (kritik emas): %s", e)
            finally:
                first_run = False

    async def _run_scheduler(self) -> None:
        # scheduled_tasks jadvali init_db() (alembic) da yaratilgan bo'ladi
        while True:
            try:
                await run_scheduler_loop(self.text_queue, interval=30.0)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Postgres vaqtincha uzilsa — loop o'lib qolmasin, qayta urinsin
                log.warning("Scheduler xatosi, 5 soniyadan keyin qayta urinadi: %s", e)
                await asyncio.sleep(5)

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


def main():
    from core.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
