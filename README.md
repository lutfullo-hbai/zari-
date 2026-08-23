# Zari — Shaxsiy AI Yordamchi

> "Ikkinchi miyyang — doim yoningda, doim o'rganib boradi."

Zari — ovoz bilan boshqariladigan, kompyutеr ichida yashaydigan, foydalanuvchining fikrlash uslubini o'rganib boradigan shaxsiy AI yordamchi. Iron Man filmidagi Jarvis singari — lekin sening hayoting, sening tilingda.

---

## Holat (2026-08)

- **320 test** yashil, ruff to'liq toza, pre-commit yoqilgan
- **Web API auth**: `WEB_API_KEY` o'rnatilsa barcha `/api/*` va WebSocket himoyalanadi
- **Agent Brain**: ko'p intentli so'rovlarda LLM reja tuzadi (`ENABLE_BRAIN=true`, default)
- **Scheduler**: voice rejimda ham ishlaydi; `once` vazifalar aniq vaqtda trigger bo'ladi
- **DB**: PostgreSQL 5434 portda, schema faqat alembic migratsiyalari orqali (`alembic upgrade head`)
- **Default provider**: Ollama (local-first); Groq uchun `.env` da `LLM_PROVIDER=groq`
- Batafsil tahlil: `REVIEW.md`, `FIXES.md`, `MIGRATION.md`

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
│   ├── main.py              # Asosiy loop — wake word eshitish
│   ├── config.py            # .env asosida konfiguratsiya
│   └── router.py            # Niyat → modul yo'naltirish
├── voice/
│   ├── wake.py              # "Zari" so'zini aniqlash (Porcupine/Vosk)
│   ├── stt.py               # Ovoz → matn (Whisper local)
│   └── tts.py               # Matn → ovoz (edge-tts)
├── llm/
│   ├── ollama.py            # Ollama bilan muloqot
│   ├── memory.py            # Suhbat tarixi + uzun xotira
│   └── persona.py           # Foydalanuvchi profili va fikrlash uslubi
├── skills/
│   ├── base.py              # BaseSkill abstract class
│   ├── search.py            # Internet qidiruv
│   ├── music.py             # YouTube musiqa
│   ├── finance.py           # Valyuta, oltin narxlari + tahlil
│   ├── messaging.py         # Telegram, Email yuborish
│   └── system.py            # OS buyruqlari
├── agents/
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

---

## Milestonelar

### Milestone 1 — Ovoz va Asosiy Muloqot
**Muddat: 2 hafta**

**Maqsad:** Zari birinchi marta gapiradi.

- [ ] Wake word aniqlash — "Zari" deyilsa faollashadi, boshqa ovozlarga javob bermaydi
- [ ] STT — Whisper local orqali ovozni matnga aylantiradi
- [ ] LLM — Ollama (qwen2.5:3b) orqali javob beradi
- [ ] TTS — edge-tts orqali ovoz bilan javob qaytaradi
- [ ] Suhbat tarixi — sessiya davomida eslab qoladi
- [ ] `.env` asosida konfiguratsiya

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

### Milestone 3 — Skills Tizimi
**Muddat: 3 hafta**

**Maqsad:** Zari amaliy vazifalarni bajaradi.

- [ ] YouTube dan musiqa qidirish va link berish
- [ ] Valyuta va oltin narxlarini scraping qilish
- [ ] 5 yillik narx grafigi chiqarish (matplotlib)
- [ ] Tahlil va xulosa aytish
- [ ] Fayl yuklab olish (yt-dlp)
- [ ] BaseSkill — yangi skill qo'shish oson bo'lsin

**Natija:** "Zari, so'nggi 5 yil oltin narxini tahlil qil" — grafik + ovozli xulosa.

---

### Milestone 4 — Xotira va O'rganish
**Muddat: 3 hafta**

**Maqsad:** Zari seni o'rganib boradi.

- [ ] Uzun muddatli xotira (ChromaDB — local vector DB)
- [ ] Foydalanuvchi profili — qiziqishlar, fikrlash uslubi, odatlar
- [ ] "Sen doim ertalab ishlay olmasang" — o'zi sezadi
- [ ] Yangi ma'lumot o'rgatsa — eslab qoladi
- [ ] Kontekstli javoblar — oldingi suhbatlardan foydalanadi

**Natija:** 1 oy ishlatgandan keyin Zari seni taniydi.

---

### Milestone 5 — Xabar va Avtomatlashtirish
**Muddat: 2 hafta**

**Maqsad:** Zari sening nomingdan harakat qiladi.

- [ ] Telegram xabar yuborish
- [ ] Email yuborish
- [ ] Vaqt asosida avtomatik vazifalar — "soat 8 da Oybek ga xabar yubor"
- [ ] APScheduler orqali rejalashtirish
- [ ] Javob shablonlari — "bunday qilib javob ber"

**Natija:** "Zari, ertaga ertalab Akbar aka ga xabar yubor" — bajaradi.

---

### Milestone 6 — Multi-Agent Sistema
**Muddat: 2 oy**

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

### Milestone 7 — To'liq Zari
**Muddat: 6 oy+**

**Maqsad:** Haqiqiy shaxsiy OS yordamchisi.

- [ ] Kompyuter ekranini ko'radi va tushunadi (vision model)
- [ ] Ilovalarni ochadi, yopadi, boshqaradi
- [ ] Brauzer orqali harakat qiladi (Selenium/Playwright)
- [ ] Ovoz profili — faqat sening ovozingni taniydi
- [ ] Oflayn rejim — internet bo'lmasa ham ishlaydi
- [ ] Telefon bilan sinxronizatsiya

---

## Texnologiyalar

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

---

## O'rnatish

```bash
git clone https://github.com/username/zari.git
cd zari
cp .env.example .env
pip install -r requirements.txt
python core/main.py
```

Yoki `Makefile` orqali:

```bash
make install       # dependency'larni o'rnatadi
make dev           # + dev tool'lar (pytest, ruff, pre-commit)
make test          # testlarni ishga tushiradi
make lint          # ruff tekshiradi
make run           # ovoz rejimida ishga tushiradi
make run-text      # matn rejimida (mikrofonsiz)
make test-mic      # mikrofonni tekshiradi
make db-up         # PostgreSQL + Redis ni dockerda ko'taradi
```

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

For Gmail API / OAuth flow (recommended for production using Gmail), see the `EMAIL` task in `FUTURE_PLAN.md` for steps.

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
