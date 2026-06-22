# Zari Loyhasi Sharhi

> README asosida tahlil va takliflar

---

## Arxitektura Tahlili

Zari — bu **event-driven, modulli, local-first** AI agent. Arxitekturasi 5 asosiy qatlamga bo'lingan:

### 1. Voice Layer (core/ + voice/)
- **Wake word** detektori doimiy ravishda mikrofonni tinglaydi
- Ovoz kelganda STT (Whisper) matnga aylantiradi
- LLM javob beradi, TTS (edge-tts) ovozga aylantiradi
- Bu **synchronous pipeline**: wake → STT → LLM → TTS → play

### 2. Intent Router (core/router.py)
- Foydalanuvchi niyatini aniqlaydi: suhbatmi, qidiruvmi, buyruqmi?
- To'g'ri skill/modulga yo'naltiradi

### 3. Skills Layer (skills/)
- Har bir skill `BaseSkill` dan inheritance oladi
- Plugin arxitekturasi — yangi skill qo'shish oson
- Skill'lar mustaqil, bir-biriga bog'liq emas

### 4. Agent Layer (agents/)
- Multi-agent sistema: Orchestrator bosh agent, qolganlari sub-agent
- Agent'lar o'rtasida xabar almashish protokoli kerak
- Har bir agent o'z vazifasiga ixtisoslashgan

### 5. Memory Layer (data/)
- SQLite — qisqa muddatli xotira (suhbat tarixi)
- ChromaDB — uzun muddatli xotira (vector embeddings)
- Profillar — foydalanuvchi modeli JSON da

---

## Muhim Kamchiliklar / Xavflar

### 1. Sync pipeline muammosi
Ovoz pipeline'i sync ishlaydi — bir narsa sekin ketsa, butun tizim to'xtab qoladi.
Taklif: **async pipeline + queue** (Redis yoki asyncio.Queue). STT, LLM, TTS parallel ishlashi kerak.

### 2. Wake word doimiy tinglash
Mikrofon doim ochiq — resurs sarfi yuqori, privacy muammosi.
Taklif: **VAD (Voice Activity Detection)** — faqat ovoz bor paytda ishlasin. Yoki PTT (push-to-talk) rejimi.

### 3. Single point of failure — router
Router bir o'zi hamma narsani yo'naltiradi. Agar router ishlamasa, tizim ishlamaydi.
Taklif: **Router'ni agent'larga tarqatish** — orchestrator faqat yuqori darajadagi qarorlar qabul qilsin.

### 4. Testlar yo'q
README da `tests/` papkasi bor lekin testlar haqida hech narsa yo'q.
Har bir milestone test bilan kelishi kerak (pytest + mock).

### 5. Monitoring va logging
"Logs stdout ga, tizim yig'adi" deyilgan — lekin aniq logging strukturasi yo'q.
Taklif: **Structured logging** (JSON format) + darajalar (DEBUG, INFO, ERROR).

---

## Nima Qo'shish Mumkin?

### Qo'shimcha Skill'lar

| Skill | Nima uchun kerak? |
|-------|-------------------|
| **Weather** | Ob-havo ma'lumoti (OpenWeatherMap API) |
| **Calendar** | Google Calendar integratsiyasi |
| **Notes** | Tez eslatma olish, qidirish |
| **Timer/Alarm** | Vaqt o'lchash, uyg'otish |
| **Translation** | Tarjimon (local model yoki API) |
| **File manager** | Fayllarni ochish, ko'chirish, o'chirish |
| **Screen reader** | Ekrandagi matnni o'qish (OCR) |
| **Smart home** | IoT qurilmalarni boshqarish (MQTT) |

### Arxitektura yaxshilanishlari

#### Plugin System
Skill'larni **dinamik yuklash** — papkaga .py fayl tashlasang, Zari uni avtomatik topib ishlatsin.

```python
# plugin_loader.py
import importlib, pkgutil, inspect
from skills.base import BaseSkill

def load_skills():
    skills = {}
    for finder, name, ispkg in pkgutil.iter_modules(['skills']):
        module = importlib.import_module(f'skills.{name}')
        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj != BaseSkill:
                skills[name] = obj()
    return skills
```

#### Web UI
Ovozli interfeys yetarli emas — **web dashboard** kerak:
- Suhbat tarixini ko'rish
- Skill'larni yoqish/o'chirish
- Profilni tahrirlash
- Loglarni kuzatish

#### REST API
FastAPI bor — lekin faqat port bind uchun. Aslida to'liq REST API qilish mumkin:
- `/api/chat` — matn orqali muloqot
- `/api/skills` — skill'larni boshqarish
- `/api/memory` — xotirani boshqarish
- WebSocket — real-time streaming

#### Multi-user Support
Hozir bir foydalanuvchi uchun. Agar profil va xotira user_id asosida ajratilsa, bir necha kishi ishlata oladi.

---

## Nima Qilish Kerak (Priority)

### Immediate (hozir)
1. `.env.example` ni to'ldirish — hamma kerakli o'zgaruvchilar bilan
2. `requirements.txt` yaratish (hozir mavjud emas)
3. `docker-compose.yml` ni yozish
4. `tests/` ga pytest konfiguratsiyasi qo'shish
5. Makefile yoki Taskfile qo'shish — tez-tez ishlatiladigan buyruqlar uchun

### Short-term (1-2 hafta)
1. Async pipeline ga o'tish (asyncio)
2. Plugin loader yozish
3. VAD qo'shish (WebRTC VAD yoki Silero VAD)
4. Structured logging (loguru yoki structlog)

### Long-term (1-2 oy)
1. Web UI (FastAPI + Jinja2 yoki React)
2. Multi-agent protokoli (Agent'lar o'rtasida xabar almashish)
3. Vision model qo'shish (ekranni tushunish)
4. Mobile sinxronizatsiya

---

## Foydali Kutubxonalar

| Kutubxona | Nima uchun |
|-----------|------------|
| `loguru` | Chiroyli logging |
| `pydantic` | Config validatsiya |
| `httpx` | Async HTTP (DuckDuckGo, API lar) |
| `asyncio` | Async pipeline |
| `websockets` | Real-time muloqot |
| `jinja2` | Web UI templating |
| `alembic` | Database migration |
| `pre-commit` | Kod sifatini tekshirish |
| `ruff` | Linter (tez) |
| `webrtcvad` | Voice Activity Detection |

---

## Umumiy Xulosa

**Zari — juda yaxshi boshlangan loyiha.** Modular arxitektura, to'g'ri texnologiyalar tanlovi, aniq milestonelar bor.

Asosiy kuchli tomonlari:
- To'liq local (privacy)
- Plugin arxitekturasi (kengaytirish oson)
- Multi-agent (keyinchalik murakkab vazifalar uchun)

Asosiy zalf tomonlari:
- Sync pipeline (tezlik muammosi)
- Testlar yo'q
- Monitoring yo'q
- Web UI yo'q

Loyiha hozir **prototip bosqichida** — ovozli muloqot va asosiy skill'lar ishlab chiqilsa, MVP bo'ladi.
