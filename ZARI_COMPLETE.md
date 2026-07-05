# Zari — Shaxsiy AI Yordamchi (Jarvis-like Assistant)

> "Ikkinchi miyyang — doim yoningda, doim o'rganib boradi."

Zari — ovoz bilan boshqariladigan, kompyuter ichida yashaydigan, foydalanuvchining fikrlash uslubini o'rganib boradigan shaxsiy AI yordamchi. Iron Man filmidagi Jarvis singari — lekin sening hayoting, sening tilingda.

**5 yil ichida Zari quyidagiga aylanadi:**
- Sening fikrlash uslubingni biladigan va shu asosda harakat qiladigan agent
- Mustaqil ravishda vazifalarni rejalashtirib, bajarib, tekshirib topshiradigan multi-agent sistema
- Ovoz, matn, veb va tizim darajasida ishlaydigan to'liq shaxsiy OS ichidagi yordamchi
- Hech qanday bulut xizmati kerak bo'lmaydigan, to'liq local va xususiy sistema

---

## Mundarija

1. [Arxitektura](#arxitektura)
2. [Twelve-Factor App Tamoyillari](#twelve-factor-app-tamoyillari)
3. [Texnologiyalar](#texnologiyalar)
4. [Kamchiliklar va Xavflar](#kamchiliklar-va-xavflar)
5. [Milestonelar](#milestonelar)
6. [Jarvis-like Functionlar](#jarvis-like-functionlar)
7. [Development Guide](#development-guide)
8. [O'rnatish](#ornatish)
9. [Muhit o'zgaruvchilari](#muhit-ozgaruvchilari)
10. [Hissa qo'shish](#hissa-qoshish)
11. [Litsenziya](#litsenziya)

---

## Arxitektura

### Loyiha Tuzilmasi

```
zari/
├── core/                    # 1-QATLAM: Asosiy loop va yo'naltirish
│   ├── main.py              # Wake word eshitish, asosiy loop
│   ├── config.py            # .env asosida konfiguratsiya
│   └── router.py            # Niyat → modul yo'naltirish
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

### Qatlamlar Tahlili

Zari — **event-driven, modulli, local-first** AI agent. 5 asosiy qatlam:

**1. Voice Layer (core/ + voice/)**
- Wake word detektori doimiy ravishda mikrofonni tinglaydi
- Ovoz kelganda STT (Whisper) matnga aylantiradi
- LLM javob beradi, TTS (edge-tts) ovozga aylantiradi
- Sync pipeline: wake → STT → LLM → TTS → play

**2. Intent Router (core/router.py)**
- Foydalanuvchi niyatini aniqlaydi: suhbatmi, qidiruvmi, buyruqmi?
- To'g'ri skill/modulga yo'naltiradi

**3. Skills Layer (skills/)**
- Har bir skill `BaseSkill` dan inheritance oladi
- Plugin arxitekturasi — yangi skill qo'shish oson
- Skill'lar mustaqil, bir-biriga bog'liq emas

**4. Agent Layer (agents/)**
- Multi-agent sistema: Orchestrator bosh agent, qolganlari sub-agent
- Agent'lar o'rtasida xabar almashish protokoli kerak
- Har bir agent o'z vazifasiga ixtisoslashgan

**5. Memory Layer (data/)**
- SQLite — qisqa muddatli xotira (suhbat tarixi)
- ChromaDB — uzun muddatli xotira (vector embeddings)
- Profillar — foydalanuvchi modeli JSON da

### Ma'lumot Oqimi

```
Mikrofon
   │
   ▼
┌─────────────────────┐
│  Voice Layer        │  Wake word detection + VAD
│  (wake.py)          │
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
| `loguru` | Structured logging |
| `pydantic` | Config validatsiya |
| `httpx` | Async HTTP (API lar uchun) |
| `websockets` | Real-time muloqot |
| `jinja2` | Web UI templating |
| `alembic` | Database migration |
| `pre-commit` | Kod sifatini tekshirish |
| `ruff` | Tez linter |
| `webrtcvad` | Voice Activity Detection |

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

---

## Kamchiliklar va Xavflar

### 1. Sync Pipeline Muammosi
Ovoz pipeline'i sync ishlaydi — bir narsa sekin ketsa, butun tizim to'xtab qoladi.
**Taklif:** async pipeline + queue (Redis yoki asyncio.Queue). STT, LLM, TTS parallel ishlashi kerak.

### 2. Wake Word Doimiy Tinglash
Mikrofon doim ochiq — resurs sarfi yuqori, privacy muammosi.
**Taklif:** VAD (Voice Activity Detection) — faqat ovoz bor paytda ishlasin. Yoki PTT (push-to-talk) rejimi.

### 3. Single Point of Failure — Router
Router bir o'zi hamma narsani yo'naltiradi. Agar router ishlamasa, tizim ishlamaydi.
**Taklif:** Router'ni agent'larga tarqatish — orchestrator faqat yuqori darajadagi qarorlar qabul qilsin.

### 4. Testlar Yo'q
README da `tests/` papkasi bor, lekin testlar haqida hech narsa yo'q.
**Taklif:** Har bir milestone test bilan kelishi kerak (pytest + mock).

### 5. Monitoring va Logging
"Logs stdout ga, tizim yig'adi" deyilgan — lekin aniq logging strukturasi yo'q.
**Taklif:** Structured logging (JSON format) + darajalar (DEBUG, INFO, ERROR).

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

### Milestone 3 — Skills Tizimi (3 hafta)

**Maqsad:** Zari amaliy vazifalarni bajaradi.

- [ ] YouTube dan musiqa qidirish va link berish
- [ ] Valyuta va oltin narxlarini scraping qilish
- [ ] 5 yillik narx grafigi chiqarish (matplotlib)
- [ ] Tahlil va xulosa aytish
- [ ] Fayl yuklab olish (yt-dlp)
- [ ] BaseSkill — yangi skill qo'shish oson bo'lsin
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

### Milestone 4 — Xotira va O'rganish (3 hafta)

**Maqsad:** Zari seni o'rganib boradi.

- [ ] Uzun muddatli xotira (ChromaDB — local vector DB)
- [ ] Foydalanuvchi profili — qiziqishlar, fikrlash uslubi, odatlar
- [ ] "Sen doim ertalab ishlay olmasang" — o'zi sezadi
- [ ] Yangi ma'lumot o'rgatsa — eslab qoladi
- [ ] Kontekstli javoblar — oldingi suhbatlardan foydalanadi
- [ ] Test: xotira saqlash va qayta olish

**Natija:** 1 oy ishlatgandan keyin Zari seni taniydi.

---

### Milestone 5 — Xabar va Avtomatlashtirish (2 hafta)

**Maqsad:** Zari sening nomingdan harakat qiladi.

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

## Jarvis-like Functionlar

Haqiqiy Iron Man Jarvis'iga o'xshash bo'lishi uchun kerakli functionlar.

### 1. Situational Awareness (Vaziyatni Tushunish)

| Function | Tavsif |
|----------|--------|
| **Screen OCR** | Ekranda nima ko'rinayotganini o'qish (Tesseract + screenshot) |
| **App Detection** | Qaysi ilova ochiqligini bilish (window title) |
| **Clipboard Watch** | Nusxa olingan matnni avtomatik o'qib, kontekst berish |
| **File Change Watcher** | Muhim fayllar o'zgarganida xabar berish |
| **System Health** | CPU/RAM/Disk holatini kuzatish, muammo bo'lsa aytish |
| **Network Monitor** | Internet tezligi, qaysi device ulangan, xavfsizlik |

**Misol:** Sen brauzerda biror maqola o'qiyapsan. Zari: "*Bu maqola haqida qisqacha xulosa beraymi?*"

---

### 2. Proactive Intelligence (Oldindan Harakat Qilish)

| Function | Tavsif |
|----------|--------|
| **Morning Brief** | Ertalab: ob-havo, kalendar, muhim yangiliklar, xabarlar |
| **Habit Detection** | Odatlarni o'rganib, "har kuni soat 10 da choy ichasan, eslataymi?" |
| **Smart Reminder** | "30 daqiqadan beri ishlayapsan, tanaffus qil" |
| **Contextual Suggestions** | Ish qilayotganingga qarab kerakli tool'ni taklif qilish |
| **Auto-Backup** | Muhim fayllarni avtomatik backup qilish |
| **Focus Mode** | "Ish rejimi" — notificationlarni bloklash, musiqani moslash |

**Misol:** Zari: "*Ertaga 9 da meeting'ing bor. Bugun kech qolma, ertalab uyg'otaymi?*"

---

### 3. Communication Hub (Aloqa Markazi)

| Function | Tavsif |
|----------|--------|
| **Call Forwarding** | Telefon qo'ng'iroqlarini kompyuterga yo'naltirish |
| **Voicemail AI** | "Kimdir qoldirgan xabarni o'qib ber" |
| **Meeting Assistant** | Zoom/Google Meet da avtomatik join qilish, transkript yozish |
| **Smart Reply** | Xabarlarga kontekst asosida javob taklif qilish |
| **Spam Filter** | Spam qo'ng'iroq va xabarlarni filtrlash |

---

### 4. Personal Knowledge Base (Shaxsiy Bilim Baza)

| Function | Tavsif |
|----------|--------|
| **Auto-Clip** | Brauzerdan muhim narsalarni avtomatik saqlash |
| **Smart Search** | Shaxsiy fayllar, xabarlar, eslatmalar ichidan qidirish |
| **Meeting Notes** | Meetinglarni yozib, qisqacha xulosa chiqarish |
| **Code History** | "3 kun oldin qaysi faylda nimani o'zgartirgan eding?" |
| **Web History** | "O'tgan hafta qaysi saytni ko'rgan eding?" |

**Misol:** "*Zari, o'tgan oyda men ko'rgan maqolani top, blockchain haqida edi*"

---

### 5. Security & Privacy (Xavfsizlik)

| Function | Tavsif |
|----------|--------|
| **Voice Auth** | Faqat sening ovozingni tanish |
| **Face Auth** | Webcam orqali tanib olish |
| **Intrusion Alert** | Kompyuterga kimdir kirsa, xabar berish |
| **Encryption** | Muhim fayllarni avtomatik shifrlash |
| **VPN Manager** | Zarur bo'lganda VPN yoqish/o'chirish |

---

### 6. Entertainment (Ko'ngilochar)

| Function | Tavsif |
|----------|--------|
| **Music DJ** | Kayfiyatingga qarab musiqa tanlash |
| **Movie Suggester** | Ko'rgan filmlaringga qarab tavsiya |
| **Gaming Mode** | Game ishga tushganda RGB, sound, performance sozlash |
| **Storyteller** | Uxlash oldidan hikoya aytib berish |
| **Jokes/Facts** | "Zari, meni kuldir" |

---

### 7. Developer Tools (Dasturchi Uchun)

| Function | Tavsif |
|----------|--------|
| **Auto-Commit** | "Zari, dars qilganlarimni commit qil" |
| **Code Review** | Pull request larni avtomatik review qilish |
| **Bug Hunter** | Log lardan xatolarni topib, tuzatish taklif qilish |
| **Dependency Watch** | "Qaysi library eskirgan, yangilash kerak" |
| **Doc Generator** | Kodga qarab avtomatik dokumentatsiya |

---

### Priority bo'yicha (Jarvis-like bo'lish uchun eng muhimlari)

| # | Function | Nima uchun? |
|---|----------|-------------|
| 1 | **Screen OCR + App Detection** | Jarvis sening nima qilayotganingni ko'radi |
| 2 | **Morning Brief** | Ertalab nonushtada yangiliklar + kalendar |
| 3 | **Meeting Assistant** | Real hayotda eng kerakli narsa |
| 4 | **Proactive Reminders** | Sen aytmasdan turib, o'zi eslatadi |
| 5 | **Voice Auth** | Faqat sening ovozingni tanish |
| 6 | **Auto-Clip + Smart Search** | Shaxsiy bilim bazang |
| 7 | **System Health** | Kompyuter holatini kuzatish |

Jarvis bo'lish uchun eng asosiy 3 ta xususiyat:
1. **Ko'rish** (ekranni tushunish) — Screen OCR
2. **Oldindan harakat** (proactive) — Morning Brief + Reminders
3. **Aloqa** — Meeting Assistant + Smart Reply

---

## Development Guide

### Code Style
- Python 3.11+
- Ruff linter (tez va qattiq)
- Typed Python — hamma funksiyalarda type hints
- No comments in code (self-documenting code)

### Testing
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

### Git Workflow
- `main` — barqaror versiya
- `develop` — ishlab chiqish
- `feature/*` — yangi feature branch
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`

### Monitoring va Logging
- Structured logging (JSON format)
- Darajalar: DEBUG, INFO, WARNING, ERROR
- stdout ga chiqish, Docker log'lar orqali yig'ish
- Kelajakda: Prometheus + Grafana

### Priority va Roadmap

| Priority | Nima | Milestone |
|----------|------|-----------|
| 🔴 Critical | Foundation (requirements, .env, Docker, tests) | M0 |
| 🔴 Critical | Voice pipeline (wake, STT, LLM, TTS) | M1 |
| 🟢 Medium | Search va intent detection | M2 ✅ |
| 🟡 High | Skills tizimi va plugin loader | M3 |
| 🟢 Medium | Web UI va REST API | M3.5 |
| 🟢 Medium | Uzoq muddatli xotira | M4 |
| 🔵 Low | Messaging va scheduler | M5 |
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
