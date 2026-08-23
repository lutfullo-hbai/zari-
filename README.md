# Zari — Shaxsiy AI Yordamchi

> "Ikkinchi miyyang — doim yoningda, doim o'rganib boradi."

Zari — ovoz bilan boshqariladigan, kompyutеr ichida yashaydigan, foydalanuvchining fikrlash uslubini o'rganib boradigan shaxsiy AI yordamchi. Iron Man filmidagi Jarvis singari — lekin sening hayoting, sening tilingda.

---

## Holat (2026-08)

**Ishlayapti:**

- 🎙️ **Ovoz zanjiri**: openwakeword ("Zari") → faster-whisper STT → LLM → edge-tts/piper
- 🧠 **Agent Brain**: ko'p intentli so'rovlarda LLM reja tuzadi, skill zanjirini bajaradi
- 🔀 **SkillExecutor**: 15+ skill — qidiruv, wiki, musiqa, ob-havo, email, fayllar, screenshot, kalkulyator, taymer, eslatmalar, tarmoq, n8n workflow...
- ⏰ **Scheduler**: `once/daily/interval` vazifalar Postgres'da saqlanadi, voice rejimda ham ishlaydi
- 💬 **Dialog holati**: ko'p bosqichli so'rovlar + xavfli harakatlar uchun tasdiqlash
- 🌐 **Web UI**: FastAPI + WebSocket chat, dashboard, API key auth (`WEB_API_KEY`)
- 🗄️ **DB**: PostgreSQL (asyncpg) + Redis cache, schema alembic migratsiyalari orqali
- 📊 **Sifat**: 320 test yashil, ruff toza, pre-commit yoqilgan

**Yo'q (yo'l xaritasida):**

- 🌐 Browser agent (browser-use), 🖥️ system control pack, 📄 hujjatlar (PDF/Word/Excel),
  👁️ vision, 🎙️ XTTS ovoz kloni, 🧠 semantik vector xotira, 📅 Google Calendar, 🏠 Smart Home

Batafsil tahlillar: `docs/archive/` (REVIEW, FIXES, MIGRATION va boshqalar)

---

## Maqsad

5 yil ichida Zari quyidagiga aylanadi:

- Sening fikrlash uslubingni biladigan va shu asosida harakat qiladigan agent
- Mustaqil ravishda vazifalarni rejalashtirib, bajarib, tekshirib topshiradigan multi-agent sistema
- Ovoz, matn, veb va tizim darajasida ishlaydigan to'liq shaxsiy OS ichidagi yordamchi
- Hech qanday bulut xizmati kerak bo'lmaydigan, to'liq local va xususiy sistema

---

## Twelve-Factor App Tamoyillari

Zari [12factor.net](https://12factor.net/) tamoyillariga asoslanib quriladi:

| Factor | Zari da qanday |
|--------|----------------|
| Codebase | Bitta repo, barcha muhitlar uchun |
| Dependencies | `requirements.txt` + virtual env, tizimga bog'liq emas |
| Config | `.env` fayl, kod ichida hech qanday sir yo'q |
| Backing services | Ollama, Redis, PostgreSQL — almashtirish mumkin |
| Build/Release/Run | Docker orqali ajratilgan bosqichlar |
| Processes | Stateless processlar, holat tashqi xizmatlarda |
| Port binding | FastAPI o'z portini expose qiladi |
| Concurrency | Vazifalar parallel ishlaydigan worker'lar orqali |
| Disposability | Tez ishga tushish, to'xtash — ma'lumot yo'qolmaydi |
| Dev/Prod parity | Docker Compose — dev va prod bir xil |
| Logs | stdout ga, tizim yig'adi |
| Admin processes | Alohida CLI buyruqlar orqali |

---

## Arxitektura

```
zari/
├── core/
│   ├── main.py              # ZariPipeline — worker orkestratsiyasi (audio/llm/tts)
│   ├── cli.py               # Kirish nuqtasi: ovoz/matn rejimi, diagnostika
│   ├── skill_executor.py    # Intent → skill routing + Brain zanjiri
│   ├── brain.py             # AgentBrain — ko'p intentli Decision Engine
│   ├── router.py            # Regex intent aniqlash (tez yo'l)
│   ├── scheduler.py         # Postgres asosida vazifa rejalashtirish
│   ├── messages.py          # Incoming + ResponseRouter (correlation ID)
│   ├── dialog_state.py      # Ko'p bosqichli dialog + tasdiqlash
│   ├── rate_limiter.py      # Skill chaqiruv limitlari
│   └── config.py            # .env asosida konfiguratsiya (pydantic-settings)
├── voice/
│   ├── wake.py              # "Zari" wake word (openwakeword, local)
│   ├── stt.py               # Ovoz → matn (faster-whisper)
│   ├── tts.py               # Matn → ovoz (edge-tts / piper)
│   └── vad.py               # Ovoz faolligi aniqlash (webrtcvad)
├── llm/
│   ├── factory.py           # Provider tanlash: Ollama | Groq
│   ├── ollama.py            # Local LLM muloqoti
│   ├── groq_client.py       # Groq bulut fallback
│   ├── memory.py            # Suhbat tarixi (Postgres + Redis cache)
│   ├── persona.py           # Foydalanuvchi profili + odat tahlili
│   ├── habits.py            # Odatlarni aniqlash va saqlash
│   ├── translator.py        # UZ↔EN tarjima zanjiri (ixtiyoriy)
│   └── long_term_memory.py  # Wiki — uzoq muddatli fakt xotirasi
├── skills/                  # 15+ skill — BaseSkill'dan meros
│   ├── base.py              # execute() + execute_with_retry() abstract
│   ├── loader.py            # Avtomatik skill yuklash
│   ├── search.py            # DuckDuckGo + Perplexica + sahifa o'qish
│   ├── wiki.py              # Wikipedia (uz/en) + xulosalash
│   ├── music.py             # YouTube musiqa
│   ├── weather.py, calculator.py, timer.py, notes.py
│   ├── email.py, clipboard.py, filemanager.py, screenshot.py
│   ├── system_info.py, network.py, n8n_workflow.py
├── db/
│   ├── database.py          # asyncpg pool + init_db → alembic upgrade
│   ├── memory_repo.py       # Sessions/messages repo
│   └── cache.py             # Redis LLM/session cache
├── web/
│   ├── server.py            # FastAPI + WebSocket chat (API key auth)
│   ├── app.py               # Dashboard (HTML/JS)
│   └── schemas.py           # Pydantic request validatsiya
├── alembic/                 # Migratsiyalar (001_initial, 002_scheduled_tasks)
├── tests/                   # 320 test
├── docker-compose.yml       # PostgreSQL (5434) + Redis (6380)
└── .env.example
```

**So'rov oqimi:** Wake word → STT → `Incoming` queue → `_handle_dialog` → Router/AgentBrain → SkillExecutor → javob `ResponseRouter` orqali to'g'ri manbaga (voice/web/scheduler).

---

## Milestonelar

### Milestone 1 — Ovoz va Asosiy Muloqot ✅
**Muddat: 2 hafta**

**Maqsad:** Zari birinchi marta gapiradi.

- [x] Wake word aniqlash — "Zari" deyilsa faollashadi (openwakeword, local)
- [x] STT — faster-whisper orqali ovozni matnga aylantiradi
- [x] LLM — Ollama (qwen2.5:3b) orqali javob beradi; Groq fallback
- [x] TTS — edge-tts/piper orqali ovoz bilan javob qaytaradi
- [x] Suhbat tarixi — sessiya davomida eslab qoladi (Postgres + Redis)
- [x] `.env` asosida konfiguratsiya

**Natija:** "Zari, bugun qanday kun?" deysan — u javob beradi.

---

### Milestone 2 — Qidiruv va Bilim ✅
**Muddat: 2 hafta**

**Maqsad:** Zari internetdan ma'lumot topadi va tahlil qiladi.

- [x] DuckDuckGo / SerpAPI orqali qidiruv
- [x] Veb sahifani o'qish va xulosalash
- [x] Ilmiy manbalardan (Wikipedia) ma'lumot olish
- [x] "Alzheimer kasalligi nima?" → internetdan o'qib, tahlil qilib, ovoz bilan tushuntiradi
- [x] Niyat aniqlash (Intent detection) — qidiruv, suhbat, buyruq farqlash

**Natija:** Har qanday savolga fact-based javob beradi.

---

### Milestone 3 — Skills Tizimi ✅
**Muddat: 3 hafta**

**Maqsad:** Zari amaliy vazifalarni bajaradi.

- [x] YouTube dan musiqa qidirish va qo'yish
- [x] Valyuta kurslari (n8n workflow integratsiya)
- [x] Ob-havo, kalkulyator, taymer, eslatmalar, clipboard
- [x] Screenshot, fayl boshqaruvi, tarmoq diagnostikasi
- [x] BaseSkill + avtomatik loader — yangi skill qo'shish juda oson
- [ ] 5 yillik narx grafigi chiqarish (matplotlib)

**Natija:** "Zari, musiqa qo'y" / "Zari, screenshot ol" / "Zari, taymer 5 daqiqa".

---

### Milestone 4 — Xotira va O'rganish ⚙️ (qisman)
**Muddat: 3 hafta**

**Maqsad:** Zari seni o'rganib boradi.

- [x] Uzun muddatli xotira — wiki jadvali (fakt saqlash va olish)
- [x] Foydalanuvchi profili (UserPersona) + odat tahlili (har N soatda)
- [x] Kontekstli javoblar — oldingi suhbatlardan foydalanadi
- [ ] Semantik vector xotira (pgvector) — "o'xshash" esdaliklarni topish
- [ ] "Sen doim ertalab ishlay olmasang" — proaktiv xulosa

**Natija:** 1 oy ishlatgandan keyin Zari seni taniydi.

---

### Milestone 5 — Xabar, Avtomatlashtirish va Brain ✅
**Muddat: 2 hafta**

**Maqsad:** Zari sening nomingdan harakat qiladi.

- [x] Email yuborish (SMTP + confirmation dialog)
- [x] Scheduler — `once/daily/interval` vazifalar Postgres'da, voice rejimda ham ishlaydi
- [x] Web API auth + `/api/tasks` orqali vazifa yaratish
- [x] AgentBrain — ko'p intentli so'rovlarda reja tuzish va skill zanjiri bajarish
- [x] Rate limiter — xavfli skill'larni suiiste'moldan himoya
- [ ] Telegram xabar yuborish

**Natija:** "Zari, ertaga ertalab Akbar akaga email yubor" — tasdiqlaydi va bajaradi.

---

### Milestone 6 — System Control Pack ✅
**Muddat: 1-2 kun**

**Maqsad:** Zari kompyuterni ovoz bilan boshqaradi.

- [x] Volume boshqarish (`amixer`) — "ovozni 50 ga qo'y", mute, holat
- [x] Ilovalarni ochish/yopish (`xdg-open`, `pkill -x`, confirmation bilan)
- [x] Monitor yorqinligi (`xrandr`, 20–100% xavfsiz diapazon)
- [x] Klaviatura/sichqoncha (`xdotool`) — allowlist + tasdiqlash majburiy
- [x] Lokal musiqa/video (`mpv`) + transport (`playerctl`): pauza/next/prev

---

### Milestone 7 — Hujjatlar va Kod ✅
**Muddat: 1 hafta**

- [x] PDF/DOCX/XLSX/CSV/TXT o'qish (pypdf, python-docx, openpyxl) + Brain orqali xulosa
- [x] Word/Excel yaratish ("excel jadval yarat", "word hujjat yarat")
- [x] Papkalarni tartibga solish (`organize`) — tasdiq bilan, ustma-ust yozish taqiqlangan
- [x] Code Runner — subprocess izolyatsiya + timeout 30s + MAJBURIY tasdiq

---

### Milestone 8 — Browser Agent 🔜
**Muddat: 1 hafta**

- [ ] browser-use + Playwright integratsiya (skill sifatida)
- [ ] Google Sheets/Docs/Gmail browser orqali
- [ ] YouTube to'liq boshqaruv (qidirish, qo'yish, to'xtatish)
- [ ] Form to'ldirish, ma'lumot olish, ticket bron
- ⚠️ Pul ketadigan harakatlarda ikki bosqichli tasdiq majburiy

---

### Milestone 9 — Semantik Xotira va Vision 🔜
**Muddat: 1 hafta**

- [ ] pgvector — Postgres ichida vector qidiruv (yangi DB kerak emas)
- [ ] Ollama vision modellari (`llama3.2-vision`/`qwen2.5-vl`)
- [ ] Ekrandagi narsani tushuntirish, rasm tahlili, hujjat skanerlash

---

### Milestone 10 — XTTS Ovoz Kloni 🔜
**Muddat: GPU kerak (~6GB VRAM)**

- [ ] Coqui XTTS-v2 — Zari sening ovozingda javob beradi

---

### Milestone 11 — Google Calendar va Smart Home 🔜
**Muddat: kelajak**

- [ ] Google Calendar OAuth sinxronizatsiya + kun rejasi
- [ ] Home Assistant API orqali chiroqlar, harorat, kameralar
- [ ] Yuzni tanish (ixtiyoriy, insightface)

---

### Milestone 12 — Multi-Agent Sistema 🔜
**Muddat: 2 oy**

**Maqsad:** Zari boshqa agentlarni boshqaradi.

- [ ] Orchestrator — Zari bosh agent sifatida (AgentBrain asosida kengaytiriladi)
- [ ] Coder Agent — kod yozadi
- [ ] Tester Agent — test yozadi va ishlatadi
- [ ] Deployer Agent — Docker, Git orqali deploy qiladi
- [ ] Researcher Agent — ma'lumot to'playdi
- [ ] "Zari, menga vazifa boshqaruv tizimi qur" → agentlar birgalikda quradi

**Natija:** Bitta buyruq — to'liq loyiha quriladi.

---

### Milestone 13 — To'liq Zari 🔜
**Muddat: 6 oy+**

**Maqsad:** Haqiqiy shaxsiy OS yordamchisi.

- [ ] Faqat sening ovozingni taniydi (voiceprint)
- [ ] To'liq oflayn rejim
- [ ] Telefon bilan sinxronizatsiya

---

## Texnologiyalar

| Qatlam | Texnologiya | Sabab |
|--------|-------------|-------|
| Wake word | openwakeword | Local, bepul, custom model trening mumkin |
| STT | faster-whisper | Aniq, oflayn, o'zbek tilini biladi |
| LLM | Ollama (local-first) + Groq fallback | Xususiylik + tezlik |
| Decision Engine | AgentBrain (LLM) | Ko'p intentli so'rovlarda reja tuzadi |
| TTS | edge-tts + piper | Sifatli, local; XTTS kloni rejalarda |
| VAD | webrtcvad | Yengil, real-time |
| Xotira | PostgreSQL (asyncpg) + Redis | Ishonchli, transactional; pgvector rejalarda |
| Migratsiya | Alembic | Bitta schema manbasi |
| Qidiruv | DuckDuckGo + Wikipedia + Perplexica | Bepul, almashtirish mumkin |
| Rejalashtirish | O'z Scheduler (Postgres asosida) | Voice rejimda ham ishlaydi, retry bilan |
| Backend | FastAPI + WebSocket + API key auth | Tez, async, xavfsiz |
| Web UI | HTML/JS dashboard (React rejalarda) | Yengil |
| Test/Sifat | pytest (320 test) + ruff + pre-commit | Toza kod majburiy |
| Deploy | Docker Compose (PG 5434, Redis 6380) | Har joyda ishlaydi |

---

## O'rnatish

Talab: Python 3.12+, Docker, (ixtiyoriy) Ollama.

```bash
git clone https://github.com/username/zari.git
cd zari
cp .env.example .env          # .env ni o'zingizga moslang
make db-up                    # PostgreSQL + Redis (docker)
pip install -r requirements.txt
python -m core.main           # ovoz rejimi
```

Yoki `Makefile` orqali:

```bash
make install       # dependency'larni o'rnatadi
make dev           # + dev tool'lar (pytest, ruff, pre-commit)
make test          # testlarni ishga tushiradi
make lint          # ruff tekshiradi
make run           # ovoz rejimida ishga tushiradi
make run-text      # matn rejimida (mikrofonsiz)
make run-web       # web server + dashboard
make test-mic      # mikrofonni tekshiradi
make db-up         # PostgreSQL (5434) + Redis (6380) docker'da
```

> ⚠️ **Diqqat:** DB port **5434** — 5433 emas. Boshqa loyihalar bilan to'qnashmaslik uchun.

---

## Muhit o'zgaruvchilari (.env)

```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
WAKE_WORD=zari
TTS_VOICE=uz-UZ-MadinaNeural
TELEGRAM_TOKEN=
EMAIL_ADDRESS=

# Qidiruv backend'i
SEARCH_BACKEND=auto
PERPLEXICA_URL=http://localhost:3000

# Web API himoyasi (bo'sh = auth o'chiq, dev uchun)
WEB_API_KEY=

# Agent Brain (ko'p intentli so'rovlarda LLM reja tuzadi)
ENABLE_BRAIN=true

# UZ->EN tarjima zanjiri (default: o'chiq — O'zbekcha to'g'ridan ishlaydi)
ENABLE_TRANSLATION=false

# Baza (docker compose db → 5434 port!)
DATABASE_URL=postgresql://zari:zari@localhost:5434/zari
REDIS_URL=redis://localhost:6380/0
```

### SMTP / Email

If you want Zari to send email via SMTP (used by `skills/email.py`), add:

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SMTP_USE_TLS=true
SENDER_ADDRESS=from@example.com
DEFAULT_RECIPIENT=to@example.com
```

For Gmail API / OAuth flow (recommended for production using Gmail), see the `EMAIL` task in `docs/archive/FUTURE_PLAN.md` for steps.

### Perplexica bilan qidiruv

Agar Perplexica ni mahalliy server sifatida ishga tushirsangiz, quyidagi buyruq bilan boshlang:

```bash
cd Perplexica
docker compose up -d
```

So'ngra loyiha `.env` faylida:

```env
SEARCH_BACKEND=perplexica
PERPLEXICA_URL=http://localhost:3000
```

Agar `SEARCH_BACKEND=auto`, loyiha avval Perplexica ni sinab ko'radi, bo'lmasa eski fallback qidiruvga o'tadi.

---

## Hissa qo'shish

Hozircha shaxsiy loyiha. Keyinchalik ochiq manba bo'lishi mumkin.

---

## Litsenziya

MIT
