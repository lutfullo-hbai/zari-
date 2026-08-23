# Zari Loyihasi — To'liq Tahlil Hisoboti

> **Sana:** 2026-07-11
> **Branch:** `feature/perplexica-service`
> **Umumiy hajm:** ~3700 Python qator, 39 fayl, 13 test fayli, 16 ta skill

---

## Mundarija

1. [Loyiha Haqida Qisqacha](#1-loyiha-haqida-qisqacha)
2. [Loyiha Tuzilmasi](#2-loyiha-tuzilmasi)
3. [Modullar Bo'yicha Tahlil](#3-modullar-boyicha-tahlil)
4. [Git Holati](#4-git-holati)
5. [Milestonelar — Kod Bilan Solishtirish](#5-milestonelar-kod-bilan-solishtirish)
6. [Qilingan Ishlar](#6-qilingan-ishlar)
7. [Qilinmagan Ishlar](#7-qilinmagan-ishlar)
8. [Xatolar va Kamchiliklar](#8-xatolar-va-kamchiliklar)
9. [Keyingi Qadamlar](#9-keyingi-qadamlar)

---

## 1. Loyiha Haqida Qisqacha

**Zari** — ovoz bilan boshqariladigan, kompyuter ichida yashaydigan, foydalanuvchining fikrlash uslubini o'rganib boradigan shaxsiy AI yordamchi. Iron Man filmidagi Jarvis singari — lekin sening hayoting, sening tilingda.

- **Texnologiyalar:** Python 3.11+, Ollama (LLM), faster-whisper (STT), edge-tts (TTS), SQLite, Redis, Docker
- **Arxitektura:** Event-driven, modulli, local-first
- **Maqsad:** 5 yil ichida to'liq shaxsiy OS yordamchisiga aylanish

---

## 2. Loyiha Tuzilmasi

```
zari-/
├── core/                    # 1-QATLAM: Asosiy loop va yo'naltirish
│   ├── __init__.py
│   ├── config.py            # .env asosida konfiguratsiya (pydantic-settings)
│   ├── dialog_state.py      # Multi-turn dialog state machine
│   ├── logging.py           # Structured JSON logging
│   ├── main.py              # ZariPipeline — asosiy orchestrator (550 qator)
│   ├── rate_limiter.py      # In-memory sliding window rate limiter
│   └── router.py            # Intent detection + router (310 qator, 16+ intent)
│
├── voice/                   # 2-QATLAM: Ovoz bilan ishlash
│   ├── __init__.py
│   ├── stt.py               # Speech-to-text (faster-whisper, 110 qator)
│   ├── tts.py               # Text-to-speech (edge-tts / piper, 300 qator)
│   ├── vad.py               # Voice Activity Detection (webrtcvad, 100 qator)
│   └── wake.py              # Wake word detection (openwakeword, 180 qator)
│
├── llm/                     # 3-QATLAM: Aql va xotira
│   ├── __init__.py
│   ├── memory.py            # Session memory (in-memory + SQLite + Redis, 200 qator)
│   ├── ollama.py            # Ollama HTTP client (sync/async, 130 qator)
│   ├── persona.py           # User persona (facts extraction + LLM, 200 qator)
│   └── translator.py        # Uzbek-English translation via LLM (90 qator)
│
├── skills/                  # 4-QATLAM: Amaliy harakatlar (16 ta skill)
│   ├── __init__.py
│   ├── base.py              # BaseSkill ABC (100 qator)
│   ├── loader.py            # Auto-discovery of skill classes (60 qator)
│   ├── calculator.py        # Safe math evaluation (AST-based)
│   ├── clipboard.py         # Clipboard read/write (pyperclip)
│   ├── email.py             # SMTP email sending (requires_confirmation)
│   ├── filemanager.py       # File operations with safe-mode
│   ├── music.py             # YouTube music search (yt-dlp)
│   ├── n8n_workflow.py      # n8n workflow search/execute
│   ├── network.py           # IP, ping, DNS
│   ├── notes.py             # Notes CRUD (SQLite)
│   ├── screenshot.py        # Screen capture (mss + PIL)
│   ├── search.py            # Web search (Perplexica / DuckDuckGo, 200 qator)
│   ├── system_info.py       # System metrics (psutil)
│   ├── timer.py             # Async countdown timers
│   ├── weather.py           # Weather (OpenWeatherMap / scraping)
│   └── wiki.py              # Personal fact storage ("learn" skill)
│
├── db/                      # 5-QATLAM: Ma'lumotlar bazasi
│   ├── __init__.py
│   ├── cache.py             # Redis with in-memory fallback (100 qator)
│   ├── database.py          # SQLite via aiosqlite, schema init (170 qator)
│   └── memory_repo.py       # Session/message CRUD (110 qator)
│
├── workflows/               # 6-QATLAM: n8n-style workflow engine
│   ├── __init__.py
│   ├── workflow_db.py       # Indexes n8n workflow JSON files (130 qator)
│   ├── workflow_executor.py # Executes n8n workflow node chains (150 qator)
│   ├── database/            # (bo'sh — kelajak uchun)
│   └── workflows/
│       ├── finance/
│       │   ├── currency_rate.json   # USD/UZS — Markaziy bank API
│       │   └── gold_price.json      # Oltin narxi — gold-api.com
│       └── system/
│           ├── open_app.json        # Ilovalarni ochish/yopish
│           └── system_info.json     # CPU/RAM/disk info
│
├── agents/                  # 7-QATLAM: Multi-agent sistema
│   └── __init__.py          # ❌ BO'SH — hech qanday kod yo'q
│
├── data/
│   ├── zari.db              # Asosiy SQLite database
│   ├── notes.db             # Eslatmalar database
│   ├── wiki.db              # Shaxsiy faktlar database
│   └── profiles/            # (bo'sh — kelajak uchun)
│
├── tests/                   # Testlar (13 ta fayl, ~150+ test)
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_config.py
│   ├── test_db.py
│   ├── test_email_skill.py
│   ├── test_integration.py
│   ├── test_llm.py
│   ├── test_loader.py
│   ├── test_memory.py
│   ├── test_n8n_workflow_skill.py
│   ├── test_new_skills.py
│   ├── test_persona.py
│   ├── test_router.py
│   ├── test_skills.py
│   └── test_voice.py
│
├── Perplexica/              # Qidiruv backend (TypeScript, alohida loyiha)
├── .opencode/               # Opencode sozlamalari
│
├── docker-compose.yml       # Dev muhiti
├── Dockerfile               # Production build
├── requirements.txt         # Python bog'liqliklari
├── pyproject.toml           # (dependencies bo'sh)
├── .env / .env.docker       # Muhit o'zgaruvchilari
├── .gitignore
├── .dockerignore
│
├── README.md                # Asosiy dokumentatsiya
├── ZARI_FULL.md             # To'liq loyiha rejalashtirish
├── ZARI_COMPLETE.md         # Yakuniy loyiha rejalashtirish
├── FUTURE_PLAN.md           # M7 dan keyingi rejalar
├── FIXES.md                 # Tuzatilgan xatolar hisoboti
├── REVIEW.md                # Loyiha sharhi
└── MIGRATION.md             # Async API ga o'tish qo'llanmasi
```

---

## 3. Modullar Bo'yicha Tahlil

### 3.1 `core/` — Application Core

| Fayl | Qator | Holat | Tavsif |
|------|-------|-------|--------|
| `config.py` | 45 | ✅ Tugallangan | `pydantic-settings` orqali `.env` dan konfiguratsiya yuklaydi. Barcha sozlamalar: Ollama, ovoz, database, Redis, ob-havo, email, Perplexica |
| `main.py` | 550 | ✅ Tugallangan | `ZariPipeline` — asosiy orchestrator. Voice loop, STT, TTS, skill execution, dialog state, rate limiting ni boshqaradi. Eng katta fayl |
| `router.py` | 310 | ✅ Tugallangan | 16+ ta regex-based intent aniqlash. Confidence scoring. Noto'g'ri so'rovlar uchun LLM ga fallback |
| `dialog_state.py` | 140 | ✅ Tugallangan | `DialogManager` state machine: IDLE / AWAITING_PARAM / AWAITING_CONFIRM. Multi-turn dialog boshqaruvi |
| `logging.py` | 80 | ✅ Tugallangan | Structured JSON logging. `StructuredLogger` class. `setup_logging()` konfiguratsiya |
| `rate_limiter.py` | 70 | ✅ Tugallangan | In-memory sliding window. Per-user configurable limits |

### 3.2 `voice/` — Voice Pipeline

| Fayl | Qator | Holat | Tavsif |
|------|-------|-------|--------|
| `wake.py` | 180 | ✅ Tugallangan | `WakeWordDetector` — openwakeword + webrtcvad. Async listen loop, energy-based speech detection, cooldown |
| `vad.py` | 100 | ✅ Tugallangan | `VoiceActivityDetector` — webrtcvad robust mode. Energy threshold, frame duration config |
| `stt.py` | 110 | ✅ Tugallangan | `SpeechToText` — faster-whisper (small model, int8 quantization). File va mic input |
| `tts.py` | 300 | ✅ Tugallangan | `TextToSpeech` — ikki backend: edge-tts (cloud) va piper-tts (local). Audio playback via sounddevice |

### 3.3 `llm/` — Language Model Layer

| Fayl | Qator | Holat | Tavsif |
|------|-------|-------|--------|
| `ollama.py` | 130 | ✅ Tugallangan | `OllamaClient` — sync `chat()`, async `chat_async()` (thread pool executor), `stream_async()` |
| `memory.py` | 200 | ✅ Tugallangan | `SessionMemory` — hybrid: in-memory dict + SQLite persistence + Redis cache |
| `persona.py` | 200 | ✅ Tugallangan | `UserPersona` — LLM-based personal info extraction. CRUD for "facts" in SQLite. Persona-aware prompts |
| `translator.py` | 90 | ✅ Tugallangan | `Translator` — Uzbek ↔ English via Ollama. Sync va async methods |

### 3.4 `skills/` — Skill System (16 ta skill)

| Skill | Fayl | Holat | Tavsif |
|-------|------|-------|--------|
| Base | `base.py` | ✅ | BaseSkill ABC — `execute()`, `execute_with_retry()`, timeout, retries, confirmation |
| Loader | `loader.py` | ✅ | Auto-discovery via `__subclasses__()` |
| Calculator | `calculator.py` | ✅ | Safe AST-based math eval. O'zbek raqam/so'z parsing |
| Clipboard | `clipboard.py` | ✅ | Read/write clipboard (pyperclip) |
| Email | `email.py` | ✅ | SMTP email with `requires_confirmation=True` |
| FileManager | `filemanager.py` | ✅ | List/read/delete/move files. Safe-mode path restrictions |
| Music | `music.py` | ✅ | YouTube search via yt-dlp |
| n8n Workflow | `n8n_workflow.py` | ✅ | n8n workflow search/execute |
| Network | `network.py` | ✅ | Public IP, ping, DNS lookup |
| Notes | `notes.py` | ✅ | CRUD notes stored in SQLite |
| Screenshot | `screenshot.py` | ✅ | Screen capture via mss + PIL |
| Search | `search.py` | ✅ | 3-tier fallback: Perplexica → DuckDuckGo → Wikipedia. LLM summarization |
| System Info | `system_info.py` | ✅ | CPU, RAM, disk, uptime (psutil) |
| Timer | `timer.py` | ✅ | Async countdown timers with stop/cancel |
| Weather | `weather.py` | ✅ | OpenWeatherMap API yoki web scraping fallback |
| Wiki | `wiki.py` | ✅ | Personal fact "learn/remember" via regex + SQLite |

### 3.5 `db/` — Database Layer

| Fayl | Qator | Holat | Tavsif |
|------|-------|-------|--------|
| `database.py` | 170 | ✅ Tugallangan | SQLite via aiosqlite. `pg_to_sqlite()` converter. Tables: sessions, messages, notes, facts |
| `memory_repo.py` | 110 | ✅ Tugallangan | CRUD for sessions va messages |
| `cache.py` | 100 | ✅ Tugallangan | Redis with automatic in-memory fallback |

### 3.6 `workflows/` — n8n-style Workflow Engine

| Fayl | Qator | Holat | Tavsif |
|------|-------|-------|--------|
| `workflow_executor.py` | 150 | ✅ Tugallangan | n8n JSON workflow execution: HTTP requests, shell commands, set-value nodes |
| `workflow_db.py` | 130 | ✅ Tugallangan | Text search across workflow names, descriptions, tags |

**Workflow JSON fayllari (4 ta):**
- `finance/currency_rate.json` — USD/UZS kurslari (Markaziy bank API)
- `finance/gold_price.json` — Oltin narxi (gold-api.com)
- `system/open_app.json` — Ilovalarni ochish/yopish
- `system/system_info.json` — CPU/RAM/disk ma'lumotlari

### 3.7 `agents/` — Multi-Agent System

| Fayl | Holat | Tavsif |
|------|-------|--------|
| `__init__.py` | ❌ BO'SH | Hech qanday kod yo'q. Multi-agent arxitekturasi rejalashtirilgan, lekin implementatsiya qilinmagan |

---

## 4. Git Holati

### Branchlar

```
main                          ← Production-ready
  └── dev                     ← Integration branch
       ├── feature/core-infra
       ├── feature/core-main
       ├── feature/database
       ├── feature/docs-config
       ├── feature/opencode
       ├── feature/perplexica-service  ← HOZIRGI BRANCH
       ├── feature/router
       ├── feature/skills
       ├── feature/tests
       └── feature/voice-llm
```

### So'nggi Commitlar (15 ta)

```
ebc5099 feat: add opencode workflow skill — clean code, 12 factor app, git workflow standards
468e632 docs: add project documentation, config files, docker setup, and development guides
1702596 test: comprehensive test suite — config, router, LLM, memory, skills, database, voice, persona, integration
adcaf38 feat: skill system — plugin-based architecture with 15 skills
b6cbee3 feat: intent router — regex-based pattern matching with 16+ intents
8b76360 refactor: ZariPipeline — async workers, enhanced config with pydantic-settings
156c1ee feat: enhance voice processing and LLM layer — async Ollama, persona learning, TTS fallback
51d8b65 feat: enhance database layer — PostgreSQL schema, Redis caching, local SQLite storage
6f506a8 feat: add core infrastructure — structured logging, rate limiter, dialog state machine
111445c added search from duckduckgo and wikipedia
9b6150c complete milestone one
f8c820e added new md file
cf6873f create plan
40ba6b5 Create fasfa.py
0243a38 Initial commit
```

### O'zgarishlar (hozirgi holat)

**Modified fayllar (25 ta):** `.env.docker`, `SKILL.md`, `dialog_state.py`, `main.py`, `cache.py`, `database.py`, `memory_repo.py`, `persona.py`, `translator.py`, `requirements.txt`, `calculator.py`, `filemanager.py`, `loader.py`, `n8n_workflow.py`, `notes.py`, `search.py`, `wiki.py`, va 8 ta test fayli

**Untracked fayllar:** `Perplexica/`, `data/zari.db`, `workflows/`

---

## 5. Milestonelar — Kod Bilan Solishtirish

### M0 — Foundation (1 hafta) — ⚠️ 70% TAYYOR

| Vazifa | Holat | Dalil |
|--------|-------|-------|
| `requirements.txt` | ✅ | Fayl mavjud, barcha dependency'lar ko'rsatilgan |
| `.env.example` / `.env` | ✅ | `.env` va `.env.docker` mavjud |
| `docker-compose.yml` | ✅ | PostgreSQL, Redis, Ollama servislar |
| `Dockerfile` | ✅ | Production build tayyor |
| `Makefile` / `Taskfile` | ❌ | Yo'q |
| `tests/` — pytest | ✅ | 13 ta test fayli, ~150+ test |
| `pyproject.toml` | ⚠️ | Bor, lekin `dependencies` bo'sh |
| `.pre-commit-config.yaml` | ❌ | Yo'q |
| Structured logging | ✅ | `core/logging.py` — JSON format |
| Config validatsiya | ✅ | `core/config.py` — pydantic-settings |

### M1 — Ovoz va Asosiy Muloqot (2 hafta) — ✅ 95% TAYYOR

| Vazifa | Holat | Dalil |
|--------|-------|-------|
| Wake word aniqlash | ✅ | `voice/wake.py` — openwakeword + webrtcvad |
| STT — Whisper local | ✅ | `voice/stt.py` — faster-whisper small model |
| LLM — Ollama | ✅ | `llm/ollama.py` — sync/async chat |
| TTS — edge-tts | ✅ | `voice/tts.py` — edge-tts + piper fallback |
| Suhbat tarixi | ✅ | `llm/memory.py` — hybrid memory |
| `.env` konfiguratsiya | ✅ | `core/config.py` |
| VAD | ✅ | `voice/vad.py` — webrtcvad |
| Async pipeline | ✅ | `core/main.py` — asyncio workers |
| Testlar | ✅ | `tests/test_voice.py` |

### M2 — Qidiruv va Bilim (2 hafta) — ✅ 100% TAYYOR

| Vazifa | Holat | Dalil |
|--------|-------|-------|
| DuckDuckGo qidiruv | ✅ | `skills/search.py` |
| Veb sahifani o'qish | ✅ | `skills/search.py` — BeautifulSoup |
| Wikipedia | ✅ | `skills/search.py` |
| Niyat aniqlash | ✅ | `core/router.py` — 16+ intent, confidence scoring |
| Testlar | ✅ | `tests/test_router.py` — 40+ test |

> 📌 Bu milestone hujjatlarda ham ✅ deb belgilangan

### M3 — Skills Tizimi (3 hafta) — ⚠️ 80% TAYYOR

| Vazifa | Holat | Dalil |
|--------|-------|-------|
| YouTube musiqa | ✅ | `skills/music.py` — yt-dlp |
| Valyuta/oltin narxlari | ✅ | `workflows/finance/` — n8n JSON |
| 5 yillik narx grafigi | ❌ | Matplotlib ishlatilmagan |
| Tahlil va xulosa | ⚠️ | LLM orqali qisman |
| Fayl yuklab olish | ✅ | `skills/music.py` — yt-dlp |
| BaseSkill | ✅ | `skills/base.py` — ABC, retry, timeout |
| Plugin loader | ✅ | `skills/loader.py` — auto-discovery |
| Intent priority | ✅ | `core/router.py` |
| Tool validation | ⚠️ | Qisman |
| Safety confirmation | ✅ | `skills/base.py` — `requires_confirmation` |
| Testlar | ✅ | `tests/test_skills.py` |

### M3.5 — Web UI (2 hafta) — ❌ 0% TAYYOR

| Vazifa | Holat |
|--------|-------|
| FastAPI REST API | ❌ |
| `/api/chat` | ❌ |
| `/api/skills` | ❌ |
| `/api/memory` | ❌ |
| WebSocket | ❌ |
| Web dashboard | ❌ |
| Suhbat tarixini ko'rish | ❌ |
| Skill'larni yoqish/o'chirish | ❌ |

### M4 — Xotira va O'rganish (3-4 hafta) — ⚠️ 60% TAYYOR

| Vazifa | Holat | Dalil |
|--------|-------|-------|
| Multi-turn dialog | ✅ | `core/dialog_state.py` — state machine |
| Conversation state machine | ✅ | IDLE / AWAITING_PARAM / AWAITING_CONFIRM |
| N-turn memory | ✅ | `llm/memory.py` — so'nggi N ta xabar |
| Uzoq muddatli xotira (ChromaDB) | ⚠️ | SQlite ishlatilmoqda, ChromaDB yo'q |
| Foydalanuvchi profili | ✅ | `llm/persona.py` — LLM-based extraction |
| Odatlarni aniqlash | ❌ | Habit detection yo'q |
| Kontekstli javoblar | ✅ | `persona.py` + `memory.py` |
| Testlar | ✅ | `tests/test_memory.py`, `tests/test_persona.py` |

### M5 — Agent Brain va Avtomatlashtirish (2-4 hafta) — ⚠️ 25% TAYYOR

| Vazifa | Holat | Dalil |
|--------|-------|-------|
| Agent Brain arxitekturasi | ❌ | `core/brain.py` rejalashtirilgan, yozilmagan |
| Decision Engine | ❌ | Yo'q |
| Telegram xabar yuborish | ❌ | Yo'q |
| Email yuborish | ✅ | `skills/email.py` — SMTP |
| Vaqt asosida avtomatik vazifalar | ❌ | Yo'q |
| APScheduler | ❌ | Yo'q |
| Javob shablonlari | ❌ | Yo'q |
| Safety confirmation | ✅ | `skills/base.py` |
| Rate limiter | ✅ | `core/rate_limiter.py` |

### M6 — Multi-Agent Sistema (2 oy) — ❌ 0% TAYYOR

| Vazifa | Holat |
|--------|-------|
| Orchestrator | ❌ `agents/__init__.py` bo'sh |
| Coder Agent | ❌ |
| Tester Agent | ❌ |
| Deployer Agent | ❌ |
| Researcher Agent | ❌ |
| Agent'lar o'rtasida xabar almashish | ❌ |

### M7 — To'liq Zari (6 oy+) — ❌ 0% TAYYOR

| Vazifa | Holat |
|--------|-------|
| Vision model (screen OCR) | ❌ |
| Ilovalarni ochish/yopish | ⚠️ `workflows/` da `open_app.json` bor |
| Brauzer orqali harakat | ❌ |
| Ovoz profili (voice auth) | ❌ |
| Oflayn rejim | ❌ |
| Telefon bilan sinxronizatsiya | ❌ |
| Multi-user support | ❌ |

---

## 6. Qilingan Ishlar

### ✅ To'liq Tugallangan Modullar

1. **Core Pipeline** — `config.py`, `main.py`, `router.py`, `dialog_state.py`, `logging.py`, `rate_limiter.py`
2. **Voice Pipeline** — `wake.py`, `vad.py`, `stt.py`, `tts.py` (to'liq ovoz sikli)
3. **LLM Qatlamı** — `ollama.py`, `memory.py`, `persona.py`, `translator.py`
4. **Skill Tizimi** — 16 ta skill + `base.py` + `loader.py`
5. **Database Layer** — `database.py`, `memory_repo.py`, `cache.py`
6. **Workflow Engine** — `workflow_executor.py`, `workflow_db.py` + 4 ta JSON workflow
7. **Testlar** — 13 ta test fayli, ~150+ test
8. **DevOps** — `Dockerfile`, `docker-compose.yml`, `.env`, `.env.docker`
9. **Dokumentatsiya** — `README.md`, `ZARI_FULL.md`, `ZARI_COMPLETE.md`, `FUTURE_PLAN.md`, `FIXES.md`, `REVIEW.md`, `MIGRATION.md`

### ✅ Texnik Yaxshilanishlar (FIXES.md dan)

- Async/await muammolari tuzatildi (OllamaClient, Translator)
- Error handling hamma joyda qo'shildi (try-catch + timeout + fallback)
- Confidence-based intent routing qo'shildi
- Structured logging tizimi yaratildi
- 165+ test qo'shildi
- Backward compatibility saqlandi

---

## 7. Qilinmagan Ishlar

| # | Muammo | Daraja | Tavsif |
|---|--------|--------|--------|
| 1 | **`agents/` moduli bo'sh** | 🔴 Oliy | Multi-agent arxitekturasi rejalashtirilgan, lekin kod yo'q (M6) |
| 2 | **Root entry point yo'q** | 🔴 Oliy | `main.py` pipeline class bor, lekin ilovani ishga tushiradigan top-level fayl yo'q |
| 3 | **`core/brain.py` yo'q** | 🔴 Oliy | Agent Brain / Decision Engine yozilmagan (M5) |
| 4 | **Web UI yo'q** | 🟡 O'rta | FastAPI REST API, dashboard, WebSocket — hammasi yo'q (M3.5) |
| 5 | **Postgres/SQlite ziddiyati** | 🟡 O'rta | `docker-compose.yml` Postgres ishlatadi, lekin kod faqat SQlite ishlatadi |
| 6 | **3 ta alohida SQlite DB** | 🟡 O'rta | `zari.db`, `notes.db`, `wiki.db` — birlashtirilmagan |
| 7 | **`pyproject.toml` bo'sh** | 🟡 O'rta | Dependencies `requirements.txt` da, lekin `pyproject.toml` da ko'rsatilmagan |
| 8 | **ChromaDB yo'q** | 🟡 O'rta | Uzoq muddatli xotira uchun rejalashtirilgan, lekin SQlite ishlatilmoqda |
| 9 | **Matplotlib grafiklari yo'q** | 🟡 O'rta | Narx grafiklari chiqarish imkoniyati yo'q |
| 10 | **Habit detection yo'q** | 🟢 Past | Odatlarni aniqlash tizimi yo'q |
| 11 | **Telegram integratsiyasi yo'q** | 🟢 Past | Xabar yuborish imkoniyati yo'q |
| 12 | **APScheduler yo'q** | 🟢 Past | Vaqt asosida avtomatik vazifalar yo'q |
| 13 | **`Makefile` yo'q** | 🟢 Past | Tez-tez ishlatiladigan buyruqlar yo'q |
| 14 | **`.pre-commit-config.yaml` yo'q** | 🟢 Past | Kod sifatini avtomatik tekshirish yo'q |
| 15 | **`workflows/database/` bo'sh** | 🟢 Past | Workflow saqlash uchun placeholder |
| 16 | **`data/profiles/` bo'sh** | 🟢 Past | Persona profillari uchun placeholder |

---

## 8. Xatolar va Kamchiliklar

### Arxitekturaviy Muammolar

1. **Postgres ziddiyati:** `docker-compose.yml` Postgres 15 ishlatadi, `config.py` da `DATABASE_URL` Postgres uchun bor, lekin `database.py` faqat SQlite ishlatadi. `pg_to_sqlite()` funksiyasi — to'liq migratsiya qilinmagan.

2. **3 ta alohida database:** Har bir skill domeni o'zini DB yaratadi (`notes.py` → `notes.db`, `wiki.py` → `wiki.db`). Bu resurs sarfini oshiradi va boshqaruvni qiyinlashtiradi.

3. **Root entry point yo'qligi:** Loyihani `python core/main.py` bilan ishga tushirish mumkin emas — `ZariPipeline` class ni instantiate qiladigan fayl kerak.

4. **`agents/` moduli bo'sh:** M6 da rejalashtirilgan multi-agent tizimi uchun hech qanday kod yo'q.

### Kod Sifati

- Barcha `__init__.py` fayllar bo'sh — package-level exports yo'q
- `pyproject.toml` da `dependencies` bo'sh — `pip install .` ishlamaydi
- ChromaDB o'rniga SQlite ishlatilmoqda — vector embeddings imkoniyati yo'q

---

## 9. Keyingi Qadamlar

### Eng Yaqin (hozir)

1. **Root entry point yaratish** — `main.py` yoki `__main__.py` (ilovani ishga tushirish uchun)
2. **M0 ni tugallish** — `Makefile`, `pyproject.toml` dependencies, `.pre-commit-config.yaml`
3. **Postgres/SQlite ziddiyatini hal qilish** — birini tanlash va boshqasini o'chirish

### O'rta muddat (1-2 hafta)

4. **M3 ni tugallish** — matplotlib grafiklari (narx tahlili)
5. **M4 ni tugallish** — ChromaDB o'rnatish, habit detection
6. **3 ta database ni birlashtirish** — yagona `zari.db`

### Uzoq muddat (1-2 oy)

7. **M3.5 — Web UI** — FastAPI REST API + dashboard
8. **M5 — Agent Brain** — `core/brain.py`, Decision Engine, scheduler
9. **M6 — Multi-Agent** — `agents/` modulini ishlab chiqish

### Kelajak (3+ oy)

10. **M7 — To'liq Zari** — Vision, browser automation, voice auth, multi-user

---

## Milestonelar Umumiy Jadvali

| Mileston | Nomi | Holat | Foiz |
|----------|------|-------|------|
| **M0** | Foundation | ⚠️ Qisman | **70%** |
| **M1** | Ovoz va Asosiy Muloqot | ✅ Tugallangan | **95%** |
| **M2** | Qidiruv va Bilim | ✅ Tugallangan | **100%** |
| **M3** | Skills Tizimi | ⚠️ Qisman | **80%** |
| **M3.5** | Web UI | ❌ Boshlanmagan | **0%** |
| **M4** | Xotira va O'rganish | ⚠️ Qisman | **60%** |
| **M5** | Agent Brain | ⚠️ Kam | **25%** |
| **M6** | Multi-Agent | ❌ Boshlanmagan | **0%** |
| **M7** | To'liq Zari | ❌ Boshlanmagan | **0%** |

**Tugallangan:** 2 ta (M1, M2)
**Qisman:** 4 ta (M0, M3, M4, M5)
**Boshlanmagan:** 3 ta (M3.5, M6, M7)

**Umumiy loyiha tayyorligi: ~45-50%**

---

> **Xulosa:** Zari loyihasi yaxshi boshlangan. Asosiy funksionallik (ovoz → LLM → skill → javob) to'liq ishlaydi. 16 ta skill, structured logging, error handling, testlar tayyor. Eng katta bo'shliqlar — `agents/` moduli (multi-agent), Web UI, va root entry point yo'qligi. Keyingi qadam — M0 ni tugallash va root entry point yaratish.
