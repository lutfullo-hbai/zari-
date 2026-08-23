# Zari — Shaxsiy AI Yordamchi

> "Ikkinchi miyyang — doim yoningda, doim o'rganib boradi."

Zari — ovoz bilan boshqariladigan, kompyuter ichida yashaydigan, foydalanuvchining fikrlash uslubini o'rganib boradigan shaxsiy AI yordamchi. Iron Man filmidagi Jarvis singari — lekin sening hayoting, sening tilingda.

5 yil ichida Zari quyidagiga aylanadi:
- Sening fikrlash uslubingni biladigan va shu asosda harakat qiladigan agent
- Mustaqil ravishda vazifalarni rejalashtirib, bajarib, tekshirib topshiradigan multi-agent sistema
- Ovoz, matn, veb va tizim darajasida ishlaydigan to'liq shaxsiy OS ichidagi yordamchi
- Hech qanday bulut xizmati kerak bo'lmaydigan, to'liq local va xususiy sistema

---

## Mundarija

1. [Arxitektura](#arxitektura)
2. [Twelve-Factor App Tamoyillari](#twelve-factor-app-tamoyillari)
3. [Texnologiyalar](#texnologiyalar)
4. [Milestonelar](#milestonelar)
5. [Development Guide](#development-guide)
6. [O'rnatish](#ornatish)
7. [Muhit o'zgaruvchilari](#muhit-ozgaruvchilari)
8. [Hissa qo'shish](#hissa-qoshish)
9. [Litsenziya](#litsenziya)

---

## Arxitektura

### Qatlamlar Tahlili

Zari **event-driven, modulli, local-first** AI agent. 5 asosiy qatlamga bo'lingan:

```
zari/
├── core/                    # 1-QATLAM: Asosiy loop va yo'naltirish
│   ├── main.py              # Wake word eshitish, asosiy loop
│   ├── config.py            # .env asosida konfiguratsiya
│   ├── router.py            # Niyat → modul yo'naltirish (priority)
│   └── brain.py             # Agent Brain: Decision Engine + State Machine
├── voice/                   # 2-QATLAM: Ovoz bilan ishlash
│   ├── wake.py              # "Zari" so'zini aniqlash (Porcupine/Vosk)
│   ├── stt.py               # Ovoz → matn (Whisper local)
│   └── tts.py               # Matn → ovoz (edge-tts)
├── llm/                     # 3-QATLAM: Aql va xotira
│   ├── ollama.py            # Ollama bilan muloqot
│   ├── memory.py            # Suhbat tarixi + uzun xotira
│   └── persona.py           # Foydalanuvchi profili va fikrlash uslubi
├── skills/                  # 4-QATLAM: Amaliy harakatlar
│   ├── base.py              # BaseSkill abstract class
│   ├── search.py            # Internet qidiruv
│   ├── music.py             # YouTube musiqa
│   ├── finance.py           # Valyuta, oltin narxlari + tahlil
│   ├── messaging.py         # Telegram, Email yuborish
│   └── system.py            # OS buyruqlari
├── agents/                  # 5-QATLAM: Multi-agent sistema
│   ├── orchestrator.py      # Zari — bosh agent
│   ├── coder.py             # Kod yozuvchi agent
│   ├── tester.py            # Test yozuvchi agent
│   ├── deployer.py          # Deploy qiluvchi agent
│   └── researcher.py        # Ma'lumot to'plovchi agent
├── data/
│   ├── memory.db            # SQLite — lokal xotira
│   └── profiles/            # Foydalanuvchi profili JSON
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

### Qatlamlar O'rtasidagi Ma'lumot Oqimi

```
Mikrofon
   │
   ▼
┌─────────────────────┐
│  Voice Layer        │  Wake word detection
│  (wake.py)          │  VAD (Voice Activity Detection)
└─────────┬───────────┘
          │ "Zari" eshitildi
          ▼
┌─────────────────────┐
│  STT (stt.py)       │  Whisper local → matn
└─────────┬───────────┘
          │ Matn: "bugun ob-havo qanday?"
          ▼
┌─────────────────────┐
│  Router (router.py) │  Intent detection
│                     │  Qaysi skill/agent kerak?
└─────────┬───────────┘
          │
          ├──→ Skill (search, music, etc.)
          ├──→ LLM suhbat (ollama.py)
          └──→ Agent (coder, tester, etc.)
          │
          ▼
┌─────────────────────┐
│  TTS (tts.py)       │  edge-tts → ovoz
└─────────┬───────────┘
          │
          ▼
       Karnay
```

### Async Pipeline Taklifi

Hozirgi pipeline sync ishlaydi — bir narsa sekin ketsa, butun tizim to'xtab qoladi. Kelajakda async pipeline ga o'tish kerak:

```
Mikrofon → VAD → Queue → [STT worker, LLM worker, TTS worker] → Play
                         └─────────── parallel ──────────────┘
```

Bu bilan STT, LLM, TTS bir vaqtda ishlaydi, kechikish kamayadi.

### Plugin System Taklifi

Skill'larni dinamik yuklash — papkaga .py fayl tashlasang, Zari uni avtomatik topib ishlatsin:

```python
# plugin_loader.py (kelajakda)
import importlib, pkgutil, inspect
from skills.base import BaseSkill


def load_skills():
    skills = {}
    for finder, name, ispkg in pkgutil.iter_modules(["skills"]):
        module = importlib.import_module(f"skills.{name}")
        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj != BaseSkill:
                skills[name] = obj()
    return skills
```

---

## Twelve-Factor App Tamoyillari

Zari [12factor.net](https://12factor.net/) tamoyillariga asoslanib quriladi:

| Factor | Zari da qanday |
|--------|----------------|
| **Codebase** | Bitta repo, barcha muhitlar uchun |
| **Dependencies** | `requirements.txt` + virtual env, tizimga bog'liq emas |
| **Config** | `.env` fayl, kod ichida hech qanday sir yo'q |
| **Backing services** | Ollama, Redis, PostgreSQL — almashtirish mumkin |
| **Build/Release/Run** | Docker orqali ajratilgan bosqichlar |
| **Processes** | Stateless processlar, holat tashqi xizmatlarda |
| **Port binding** | FastAPI o'z portini expose qiladi |
| **Concurrency** | Vazifalar parallel ishlaydigan worker'lar orqali |
| **Disposability** | Tez ishga tushish, to'xtash — ma'lumot yo'qolmaydi |
| **Dev/Prod parity** | Docker Compose — dev va prod bir xil |
| **Logs** | stdout ga, tizim yig'adi |
| **Admin processes** | Alohida CLI buyruqlar orqali |

---

## Texnologiyalar

### Asosiy Stack

| Qatlam | Texnologiya | Sabab |
|--------|-------------|-------|
| Wake word | Vosk / Porcupine | Local, bepul |
| STT | Whisper (local) | Aniq, oflayn |
| LLM | Ollama (qwen2.5, llama3) | Local, bepul |
| TTS | edge-tts | Sifatli, bepul |
| Xotira | ChromaDB + SQLite | Local vector DB |
| Qidiruv | DuckDuckGo API | Bepul |
| Scraping | BeautifulSoup + Selenium | Moslashuvchan |
| Grafik | Matplotlib | Oddiy, kuchli |
| Rejalashtirish | APScheduler | Yengil |
| Backend | FastAPI | Tez, async |
| Deploy | Docker Compose | Har joyda ishlaydi |

### Tavsiya Etilgan Qo'shimcha Kutubxonalar

| Kutubxona | Nima uchun |
|-----------|------------|
| `loguru` | Chiroyli structured logging |
| `pydantic` | Config validatsiya |
| `httpx` | Async HTTP (API lar uchun) |
| `websockets` | Real-time muloqot |
| `jinja2` | Web UI templating |
| `alembic` | Database migration |
| `pre-commit` | Kod sifatini tekshirish |
| `ruff` | Tez linter |
| `webrtcvad` | Voice Activity Detection |

---

## Milestonelar

### Milestone 0 — Foundation (1 hafta)

**Maqsad:** Loyiha asosi quriladi, ishlab chiqish muhiti tayyor.

- [ ] `requirements.txt` — asosiy bog'liqliklar
- [ ] `.env.example` — to'liq konfiguratsiya namunalari
- [ ] `docker-compose.yml` — dev muhiti
- [ ] `Dockerfile` — production build
- [ ] `Makefile` yoki `Taskfile` — tez-tez ishlatiladigan buyruqlar
- [ ] `tests/` — pytest konfiguratsiyasi va ilk testlar
- [ ] `pyproject.toml` — loyiha metama'lumotlari
- [ ] `.pre-commit-config.yaml` — kod sifatini avtomatik tekshirish
- [ ] Structured logging sozlamalari (loguru yoki structlog)
- [ ] Config validatsiya (pydantic)

---

### Milestone 1 — Ovoz va Asosiy Muloqot (2 hafta)

**Maqsad:** Zari birinchi marta gapiradi.

- [ ] Wake word aniqlash — "Zari" deyilsa faollashadi, boshqa ovozlarga javob bermaydi
- [ ] STT — Whisper local orqali ovozni matnga aylantiradi
- [ ] LLM — Ollama (qwen2.5:3b) orqali javob beradi
- [ ] TTS — edge-tts orqali ovoz bilan javob qaytaradi
- [ ] Suhbat tarixi — sessiya davomida eslab qoladi
- [ ] `.env` asosida konfiguratsiya
- [ ] VAD (Voice Activity Detection) — faqat ovoz bor paytda ishlasin
- [ ] Async pipeline — STT, LLM, TTS parallel ishlaydigan queue tizimi
- [ ] Test: wake word, STT, LLM muloqot

**Natija:** "Zari, bugun qanday kun?" deysan — u javob beradi.

---

### Milestone 2 — Qidiruv va Bilim (2 hafta) ✅

**Maqsad:** Zari internetdan ma'lumot topadi va tahlil qiladi.

- [x] DuckDuckGo / SerpAPI orqali qidiruv
- [x] Veb sahifani o'qish va xulosalash
- [x] Ilmiy manbalardan (Wikipedia) ma'lumot olish
- [x] "Alzheimer kasalligi nima?" → internetdan o'qib, tahlil qilib, ovoz bilan tushuntiradi
- [x] Niyat aniqlash (Intent detection) — qidiruv, suhbat, buyruq farqlash
- [x] Test: qidiruv, xulosa, intent detection

**Natija:** Har qanday savolga fact-based javob beradi.

---

### Milestone 3 — Skills va Router Tizimi (3 hafta)

**Maqsad:** Zari amaliy vazifalarni bajaradi va xavfsiz boshqaradi.

- [ ] Intent priority tizimi (system → music → finance → search → chat)
- [ ] Tool parameter validation — required/optional params tekshirish
- [ ] Async retry + timeout — har bir skill uchun alohida
- [ ] Safety confirmation — xavfli buyruqlarni tasdiqlatish
- [ ] YouTube dan musiqa qidirish va link berish
- [ ] Valyuta va oltin narxlarini scraping qilish
- [ ] 5 yillik narx grafigi chiqarish (matplotlib)
- [ ] Tahlil va xulosa aytish
- [ ] Fayl yuklab olish (yt-dlp)
- [ ] BaseSkill — priority, timeout, fallback maydonlari bilan
- [ ] Plugin loader — skill'larni dinamik yuklash
- [ ] Skill'lar uchun testlar

**Natija:** "Zari, so'nggi 5 yil oltin narxini tahlil qil" — grafik + ovozli xulosa.

---

### Milestone 3.5 — Web UI (2 hafta)

**Maqsad:** Ovozdan tashqari matn orqali ham muloqot qilish.

- [ ] FastAPI asosida REST API
- [ ] `/api/chat` — matn orqali muloqot
- [ ] `/api/skills` — skill'larni boshqarish
- [ ] `/api/memory` — xotirani boshqarish
- [ ] WebSocket — real-time streaming
- [ ] Web dashboard (Jinja2 yoki React)
- [ ] Suhbat tarixini ko'rish
- [ ] Skill'larni yoqish/o'chirish
- [ ] Loglarni kuzatish

---

### Milestone 4 — Dialog, Xotira va O'rganish (4 hafta)

**Maqsad:** Zari kontekstli dialog yuritadi va seni o'rganib boradi.

- [ ] Multi-turn dialog — "Musiqa qo'y" → "Qanday musiqa?" → "Jazz"
- [ ] Conversation state machine — IDLE → AWAITING_PARAM → EXECUTING
- [ ] N-turn conversation memory — so'nggi 5 ta xabar konteksti
- [ ] Uzun muddatli xotira (ChromaDB — local vector DB)
- [ ] Foydalanuvchi profili — qiziqishlar, fikrlash uslubi, odatlar
- [ ] "Sen doim ertalab ishlay olmasang" — o'zi sezadi
- [ ] Yangi ma'lumot o'rgatsa — eslab qoladi
- [ ] Kontekstli javoblar — oldingi suhbatlardan foydalanadi
- [ ] Test: xotira saqlash va qayta olish

**Natija:** 1 oy ishlatgandan keyin Zari seni taniydi.

---

### Milestone 5 — Agent Brain va Avtomatlashtirish (4 hafta)

**Maqsad:** Zari mustaqil qaror qabul qiladigan agent arxitekturasiga o'tadi.

- [ ] Agent Brain arxitekturasi: NLU → Router → Tool Executor → LLM → Response
- [ ] Decision Engine — qaysi tool kerak, qanday parametrlar bilan
- [ ] Telegram xabar yuborish
- [ ] Email yuborish
- [ ] Vaqt asosida avtomatik vazifalar — "soat 8 da Oybek ga xabar yubor"
- [ ] APScheduler orqali rejalashtirish
- [ ] Javob shablonlari — "bunday qilib javob ber"

**Natija:** "Zari, ertaga ertalab Akbar aka ga xabar yubor" — bajaradi.

---

### Milestone 6 — Multi-Agent Sistema (2 oy)

**Maqsad:** Zari boshqa agentlarni boshqaradi.

- [ ] Orchestrator — Zari bosh agent sifatida
- [ ] Coder Agent — kod yozadi (Ollama)
- [ ] Tester Agent — test yozadi va ishlatadi
- [ ] Deployer Agent — Docker, Git orqali deploy qiladi
- [ ] Researcher Agent — ma'lumot to'playdi
- [ ] Agent'lar o'rtasida xabar almashish protokoli
- [ ] "Zari, menga vazifa boshqaruv tizimi qur" → agentlar birgalikda quradi

**Natija:** Bitta buyruq — to'liq loyiha quriladi.

---

### Milestone 7 — To'liq Zari (6 oy+)

**Maqsad:** Haqiqiy shaxsiy OS yordamchisi.

- [ ] Kompyuter ekranini ko'radi va tushunadi (vision model)
- [ ] Ilovalarni ochadi, yopadi, boshqaradi
- [ ] Brauzer orqali harakat qiladi (Selenium/Playwright)
- [ ] Ovoz profili — faqat sening ovozingni taniydi
- [ ] Oflayn rejim — internet bo'lmasa ham ishlaydi
- [ ] Telefon bilan sinxronizatsiya
- [ ] Multi-user support — bir necha foydalanuvchi

---

## Development Guide

### Ishlab Chiqish Standartlari

#### Code Style
- Python 3.11+
- Ruff linter (tez va qattiq)
- Typed Python — hamma funksiyalarda type hints
- No comments in code (self-documenting code)

#### Testing
- pytest asosiy framework
- Har bir milestone test bilan kelishi kerak
- Mock tashqi xizmatlarni (Ollama, API lar)
- Test coverage 80%+ maqsad

```
tests/
├── test_voice/
│   ├── test_wake.py
│   ├── test_stt.py
│   └── test_tts.py
├── test_skills/
│   ├── test_search.py
│   ├── test_music.py
│   └── test_finance.py
├── test_agents/
│   ├── test_orchestrator.py
│   └── test_coder.py
└── conftest.py
```

#### Git Workflow
- `main` — barqaror versiya
- `develop` — ishlab chiqish
- `feature/*` — yangi feature branch
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`

#### Monitoring va Logging
- Structured logging (JSON format)
- Darajalar: DEBUG, INFO, WARNING, ERROR
- stdout ga chiqish, Docker log'lar orqali yig'ish
- Kelajakda: Prometheus + Grafana

### Priority va Roadmap

| Priority | Nima | Milestone |
|----------|------|-----------|
| 🔴 Critical | Foundation (requirements, .env, Docker, tests) | M0 |
| 🔴 Critical | Voice pipeline (wake, STT, LLM, TTS) | M1 |
| 🟡 High | Search va intent detection | M2 |
| 🟡 High | Skills tizimi, router priority, safety | M3 |
| 🟢 Medium | Web UI va REST API | M3.5 |
| 🟢 Medium | Dialog, xotira, conversation state | M4 |
| 🔵 Low | Agent Brain, messaging, scheduler | M5 |
| 🔵 Low | Multi-agent sistema | M6 |
| ⚪ Future | Vision, OS integration, mobile | M7 |

---

## O'rnatish

```bash
git clone https://github.com/username/zari.git
cd zari
cp .env.example .env
# Tahrirlash: .env faylini o'z sozlamalaringga mosla
pip install -r requirements.txt
python core/main.py
```

Yoki Docker orqali:

```bash
docker-compose up --build
```

---

## Muhit o'zgaruvchilari (.env)

```env
# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b

# Ovoz
WAKE_WORD=zari
TTS_VOICE=uz-UZ-MadinaNeural

# Xabarlar
TELEGRAM_TOKEN=
EMAIL_ADDRESS=

# Ma'lumotlar bazasi
MEMORY_DB_PATH=data/memory.db
CHROMA_DB_PATH=data/chroma

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Hissa qo'shish

Hozircha shaxsiy loyiha. Keyinchalik ochiq manba bo'lishi mumkin.

---

## Litsenziya

MIT
