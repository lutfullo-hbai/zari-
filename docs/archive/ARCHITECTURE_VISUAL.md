# Zari — Vizual Arxitektura Xaritasi

> Sana: 2026-07-11 | Umumiy tayyorlik: ~45-50%

---

## 🔥 To'liq Arxitektura (Qatlamlar)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                         ZARI — SHAXSIY AI YORDAMCHI                           ║
║                    "Ikkinchi miyyang — doim yoningda"                          ║
╚══════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────┐
│                        1-QATLAM: CORE (Asosiy Loop)                            │
│                        ✅ TAYYOR — 70-95%                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ config.py    │  │ main.py      │  │ router.py    │  │ dialog_state.py  │   │
│  │ ✅ 45 qator  │  │ ✅ 550 qator │  │ ✅ 310 qator │  │ ✅ 140 qator     │   │
│  │ pydantic     │  │ ZariPipeline │  │ 16+ intent   │  │ State Machine    │   │
│  │ settings     │  │ orchestrator │  │ confidence   │  │ IDLE→AWAITING    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐                                            │
│  │ logging.py   │  │ rate_limiter │                                            │
│  │ ✅ 80 qator  │  │ ✅ 70 qator  │                                            │
│  │ JSON struct  │  │ sliding win  │                                            │
│  └──────────────┘  └──────────────┘                                            │
│                                                                                 │
│  ❌ brain.py — YOZILMAGAN (Agent Brain / Decision Engine)                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     2-QATLAM: VOICE (Ovoz bilan ishlash)                       │
│                     ✅ TAYYOR — 95%                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ wake.py      │  │ vad.py       │  │ stt.py       │  │ tts.py           │   │
│  │ ✅ 180 qator │  │ ✅ 100 qator │  │ ✅ 110 qator │  │ ✅ 300 qator     │   │
│  │ openwake     │  │ webrtcvad    │  │ faster-      │  │ edge-tts +       │   │
│  │ + webrtcvad  │  │ robust mode  │  │ whisper      │  │ piper fallback   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                                 │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐                        │
│  │ Mikrofon│──▶│  VAD    │──▶│   STT   │──▶│   TTS   │──▶ Karnay             │
│  │  🎤     │   │ 🔇/🔊  │   │ 📝 Matn │   │ 🔊 Ovoz │                        │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        3-QATLAM: LLM (Aql va Xotira)                          │
│                        ✅ TAYYOR — 90%                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ ollama.py    │  │ memory.py    │  │ persona.py   │  │ translator.py    │   │
│  │ ✅ 130 qator │  │ ✅ 200 qator │  │ ✅ 200 qator │  │ ✅ 90 qator      │   │
│  │ sync/async   │  │ in-mem +     │  │ LLM-based    │  │ uz ↔ en          │   │
│  │ chat/stream  │  │ SQLite +     │  │ facts +      │  │ via Ollama       │   │
│  │              │  │ Redis cache  │  │ profile      │  │                  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     XOTIRA ARXITEKTURASI                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │   │
│  │  │ In-Memory   │  │   SQLite    │  │    Redis    │                     │   │
│  │  │ Dict (RAM)  │  │  (Disk)     │  │  (Cache)    │                     │   │
│  │  │ ⚡ Tez      │  │ 💾 Barqaror │  │ 🚀 Kesh     │                     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                     │   │
│  │                                                                         │   │
│  │  ❌ ChromaDB — YOZILMAGAN (Vector embeddings uchun)                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                   4-QATLAM: SKILLS (Amaliy Harakatlar)                         │
│                   ✅ TAYYOR — 80%                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    SKILL ARXITEKTURASI                                  │   │
│  │  ┌─────────────┐     ┌─────────────┐                                    │   │
│  │  │ BaseSkill   │◀────│ SkillLoader │  (auto-discovery)                 │   │
│  │  │ ✅ ABC      │     │ ✅ loader   │                                    │   │
│  │  │ retry       │     │ __subclasses│                                    │   │
│  │  │ timeout     │     └─────────────┘                                    │   │
│  │  │ confirm     │                                                        │   │
│  │  └─────────────┘                                                        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      16 TA SKILL                                         │   │
│  │                                                                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│  │  │🔍 search │ │🎵 music  │ │📧 email  │ │⏰ timer  │ │📝 notes  │     │   │
│  │  │ ✅ 200q  │ │ ✅ 100q  │ │ ✅ 130q  │ │ ✅ 110q  │ │ ✅ 120q  │     │   │
│  │  │Perplexica│ │yt-dlp    │ │SMTP      │ │async     │ │SQLite    │     │   │
│  │  │DDG/Wiki  │ │YouTube   │ │confirm   │ │countdown │ │CRUD      │     │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │   │
│  │                                                                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│  │  │🧮 calc   │ │📋 clip   │ │📁 file   │ │🖼 screen │ │🌐 net    │     │   │
│  │  │ ✅ 110q  │ │ ✅ 80q   │ │ ✅ 140q  │ │ ✅ 70q   │ │ ✅ 80q   │     │   │
│  │  │AST safe  │ │pyperclip │ │safe-mode │ │mss+PIL   │ │IP/ping   │     │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │   │
│  │                                                                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                   │   │
│  │  │⚙ sysinfo │ │🌤 weather│ │📚 wiki   │ │🔄 n8n    │                   │   │
│  │  │ ✅ 120q  │ │ ✅ 130q  │ │ ✅ 100q  │ │ ✅ 110q  │                   │   │
│  │  │psutil    │ │OWM/scrape│ │learn     │ │workflow  │                   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ❌ finance.py — YOZILMAGAN (valyuta/grafik tahlili uchun)                    │
│  ❌ messaging.py — YOZILMAGAN (Telegram uchun)                                │
│  ❌ system.py — QISMAN (open_app workflow bor)                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      5-QATLAM: DATABASE (Ma'lumotlar Bazasi)                   │
│                      ✅ TAYYOR — 75%                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                         │
│  │ database.py  │  │ memory_repo  │  │ cache.py     │                         │
│  │ ✅ 170 qator │  │ ✅ 110 qator │  │ ✅ 100 qator │                         │
│  │ aiosqlite    │  │ CRUD for     │  │ Redis +      │                         │
│  │ pg_to_sqlite │  │ sessions     │  │ in-mem       │                         │
│  └──────────────┘  └──────────────┘  └──────────────┘                         │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     DATABASE XARITASI                                    │   │
│  │                                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │   │
│  │  │  zari.db    │  │  notes.db   │  │  wiki.db    │                     │   │
│  │  │  ✅ Asosiy  │  │  ✅ Eslatma │  │  ✅ Faktlar  │                     │   │
│  │  │  sessions   │  │  notes CRUD │  │  wiki CRUD  │                     │   │
│  │  │  messages   │  │             │  │             │                     │   │
│  │  │  facts      │  │             │  │             │                     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                     │   │
│  │                                                                          │   │
│  │  ⚠️ MUAMMO: 3 ta alohida DB — birlashtirilishi kerak                  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  ⚠️ POSTGRES ZIDDİYATİ:                                                │   │
│  │  docker-compose.yml → PostgreSQL 15 ishlatadi                          │   │
│  │  config.py → DATABASE_URL Postgres uchun                               │   │
│  │  database.py → FAQAT SQlite ishlatadi ❌                               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                  6-QATLAM: WORKFLOWS (n8n-style Engine)                        │
│                  ✅ TAYYOR — 85%                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌────────────────────┐  ┌────────────────────┐                               │
│  │ workflow_executor  │  │ workflow_db        │                               │
│  │ ✅ 150 qator       │  │ ✅ 130 qator       │                               │
│  │ HTTP, shell, set   │  │ text search        │                               │
│  │ node chains        │  │ index + query      │                               │
│  └────────────────────┘  └────────────────────┘                               │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  WORKFLOW JSON LAR (4 ta)                                               │   │
│  │                                                                          │   │
│  │  📁 finance/                                                            │   │
│  │  ├── currency_rate.json  ✅  USD/UZS — Markaziy bank API               │   │
│  │  └── gold_price.json     ✅  Oltin narxi — gold-api.com                │   │
│  │                                                                          │   │
│  │  📁 system/                                                             │   │
│  │  ├── open_app.json       ✅  Ilovalarni ochish/yopish                  │   │
│  │  └── system_info.json    ✅  CPU/RAM/disk info                          │   │
│  │                                                                          │   │
│  │  📁 database/         ❌ BO'SH                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    7-QATLAM: AGENTS (Multi-Agent Sistema)                      │
│                    ❌ 0% — TO'LIQ BO'SH                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │   ❌ orchestrator.py  — YOZILMAGAN (bosh agent)                        │   │
│  │                                                                          │   │
│  │   ❌ coder.py         — YOZILMAGAN (kod yozuvchi)                      │   │
│  │                                                                          │   │
│  │   ❌ tester.py        — YOZILMAGAN (test yozuvchi)                     │   │
│  │                                                                          │   │
│  │   ❌ deployer.py      — YOZILMAGAN (deploy qiluvchi)                   │   │
│  │                                                                          │   │
│  │   ❌ researcher.py    — YOZILMAGAN (ma'lumot to'plovchi)               │   │
│  │                                                                          │   │
│  │   ❌ Agent protokoli  — YOZILMAGAN (xabar almashish)                   │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  agents/__init__.py  ← BO'SH Fayl                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Ma'lumot Oqimi (Flow)

```
    👤 Foydalanuvchi
         │
         │ "Zari, bugun ob-havo qanday?"
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VOICE PIPELINE                                    │
│                                                                      │
│   🎤 Mikrofon ──▶ 🔇 VAD ──▶ 📝 STT ──▶ "bugun ob-havo qanday?" │
│                      │              │                                │
│                      │              ▼                                │
│                      │         Wake Word? ──▶ "Zari" aniqlandi     │
│                      │              │                                │
│                      ▼              ▼                                │
│              ┌───────────────────────────────┐                      │
│              │     WAKE WORD DETECTOR        │                      │
│              │     ✅ openwakeword            │                      │
│              │     ✅ webrtcvad               │                      │
│              └───────────────┬───────────────┘                      │
│                              │                                      │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INTENT ROUTER                                     │
│                                                                      │
│   "bugun ob-havo qanday?"                                          │
│         │                                                           │
│         ▼                                                           │
│   ┌─────────────────────────────────────────────────┐              │
│   │  Regex Pattern Matching (16+ intent)            │              │
│   │                                                   │              │
│   │  weather?  ✅ confidence: 0.85                   │              │
│   │  search?   ❌                                    │              │
│   │  music?    ❌                                    │              │
│   │  chat?     ❌                                    │              │
│   └─────────────────────────────────────────────────┘              │
│         │                                                           │
│         ▼                                                           │
│   Intent: "weather" ──▶ WeatherSkill ga yo'naltirish               │
│                                                                      │
│   ⚠️ Confidence < 0.6 bo'lsa ──▶ LLM ga fallback                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SKILL EXECUTION                                   │
│                                                                      │
│   ┌─────────────────────────────────────────────────┐              │
│   │              WeatherSkill.execute()              │              │
│   │                                                   │              │
│   │  1. OpenWeatherMap API dan so'rov               │              │
│   │  2. Yoki web scraping fallback                   │              │
│   │  3. Natija: "Toshkentda 28°C, quyoshli"        │              │
│   └─────────────────────────────────────────────────┘              │
│         │                                                           │
│         ▼                                                           │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
│   │   Memory    │    │   Persona   │    │   Cache     │           │
│   │  ✅ saqlaydi │    │  ✅ profile │    │  ✅ Redis   │           │
│   └─────────────┘    └─────────────┘    └─────────────┘           │
│                                                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TTS PIPELINE                                      │
│                                                                      │
│   "Toshkentda 28°C, quyoshli ob-havo"                              │
│         │                                                           │
│         ▼                                                           │
│   ┌─────────────────────────────────────────────────┐              │
│   │              TextToSpeech.speak()                │              │
│   │                                                   │              │
│   │  Backend 1: edge-tts (cloud, bepul) ✅           │              │
│   │  Backend 2: piper-tts (local)     ✅             │              │
│   └─────────────────────────────────────────────────┘              │
│         │                                                           │
│         ▼                                                           │
│   🔊 Karnay ──▶ 👤 Foydalanuvchi eshityapti                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📈 Milestone Holati (Vizual)

```
M0  Foundation      [██████████████████░░░░░░░░░░░░] 70%  ⚠️
M1  Ovoz/Muloqot    [█████████████████████████████░] 95%  ✅
M2  Qidiruv/Bilim   [██████████████████████████████] 100% ✅
M3  Skills          [████████████████████████░░░░░░] 80%  ⚠️
M3.5 Web UI         [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0%   ❌
M4  Xotira/O'rganish[██████████████████░░░░░░░░░░░░] 60%  ⚠️
M5  Agent Brain     [███████░░░░░░░░░░░░░░░░░░░░░░░] 25%  ⚠️
M6  Multi-Agent     [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0%   ❌
M7  To'liq Zari     [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0%   ❌

    ████ = Tugallangan    ░░░░ = Qolgan
```

---

## 🎯 Qaysi Qism Ishlaydi, Qaysi Qism Yo'q

### ✅ ISHLAYDI (Test qilingan)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   🎤 "Zari" ──▶ STT ──▶ LLM ──▶ TTS ──▶ 🔊 Javob             │
│                                                                  │
│   Barcha ovoz sikli to'liq ishlaydi                            │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   🔍 Qidiruv: Perplexica ──▶ DuckDuckGo ──▶ Wikipedia         │
│   📧 Email: SMTP orqali yuborish                                │
│   🎵 Musiqa: YouTube qidiruv                                    │
│   🧮 Kalkulyator: xavfsiz math eval                            │
│   ⏰ Timer: async countdown                                     │
│   📝 Eslatmalar: CRUD                                          │
│   📚 Wiki: shaxsiy faktlar                                      │
│   🌤 Ob-havo: OpenWeatherMap                                    │
│   🖼 Screenshot: ekran rasm                                     │
│   📁 Fayl menejer: fayllar bilan ishlash                        │
│   🌐 Tarmoq: IP, ping, DNS                                     │
│   ⚙ Tizim ma'lumotlari                                        │
│   💻 Kalkulyator                                               │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   💾 Database: SQLite + Redis cache                             │
│   🔄 Workflow: n8n JSON execution                               │
│   📊 Logging: structured JSON                                   │
│   🛡 Rate limiting: sliding window                              │
│   💬 Dialog state: multi-turn                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### ❌ ISHLAMAYDI (Yo'q)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   🌐 Web UI — FastAPI REST API yo'q                             │
│   🤖 Multi-Agent — orchestrator, coder, tester yo'q             │
│   🧠 Agent Brain — decision engine yo'q                         │
│   📊 Grafik — matplotlib narx tahlili yo'q                      │
│   📱 Telegram — xabar yuborish yo'q                             │
│   ⏰ Scheduler — APScheduler yo'q                               │
│   🧬 ChromaDB — vector embeddings yo'q                          │
│   👁 Vision — screen OCR yo'q                                   │
│   🔐 Voice Auth — ovoz tanib olish yo'q                         │
│   📱 Mobile — telefon sinxronizatsiya yo'q                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Texnik Muammolar (Vizual)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ⚠️ MUAMMOLAR                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. POSTGRES vs SQLITE ZIDDİYATİ                                │
│     ┌──────────────┐      ┌──────────────┐                      │
│     │ docker-compose│      │ database.py  │                      │
│     │ PostgreSQL 15 │  ✗   │ SQLite only  │                      │
│     └──────────────┘      └──────────────┘                      │
│                                                                  │
│  2. 3 TA ALOHIDA DATABASE                                       │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│     │ zari.db  │  │ notes.db │  │ wiki.db  │                    │
│     └──────────┘  └──────────┘  └──────────┘                   │
│     ⚠️ Birlashtirilishi kerak                                  │
│                                                                  │
│  3. ROOT ENTRY POINT YO'Q                                       │
│     ┌──────────────────────────────┐                             │
│     │  python core/main.py  ← ❌   │                             │
│     │  ZariPipeline ni start       │                             │
│     │  qiladigan fayl yo'q         │                             │
│     └──────────────────────────────┘                             │
│                                                                  │
│  4. PYPROJECT.TOML BO'SH                                        │
│     ┌──────────────────────────────┐                             │
│     │  [project]                   │                             │
│     │  dependencies = []  ← ❌     │                             │
│     └──────────────────────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Keyingi Qadamlar (Prioritet)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRIORITET 1 (HOZIR)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  □ Root entry point yaratish                                    │
│  □ M0 tugallash (Makefile, pyproject.toml)                     │
│  □ Postgres/SQLite ziddiyatini hal qilish                      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    PRIORITET 2 (1-2 HAFTA)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  □ M3 tugallash (matplotlib grafiklari)                        │
│  □ M4 tugallash (ChromaDB, habit detection)                    │
│  □ 3 ta DB ni birlashtirish                                    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    PRIORITET 3 (1-2 OY)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  □ M3.5 — Web UI (FastAPI + dashboard)                         │
│  □ M5 — Agent Brain (core/brain.py)                            │
│  □ M6 — Multi-Agent (agents/ moduli)                           │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    PRIORITET 4 (3+ OY)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  □ M7 — To'liq Zari (Vision, browser, voice auth)              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Umumiy Statistika

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOYIHA STATISTIKASI                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Python fayllar:        39 ta                                    │
│  Test fayllari:         13 ta                                    │
│  Skill'lar:             16 ta                                    │
│  Workflow'lar:          4 ta                                     │
│  Git commitlar:         15 ta                                    │
│  Git branchlar:         12 ta                                    │
│                                                                  │
│  Umumiy qator:          ~3700+                                   │
│  Testlar soni:          ~150+                                    │
│                                                                  │
│  Tugallangan:           2 milestone (M1, M2)                    │
│  Qisman:                4 milestone (M0, M3, M4, M5)           │
│  Boshlanmagan:          3 milestone (M3.5, M6, M7)             │
│                                                                  │
│  Umumiy tayyorlik:      ~45-50%                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
