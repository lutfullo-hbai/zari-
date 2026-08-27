# Zari AI Assistant — STT/LLM Muammolari Tahlili

**Sana:** 2026-07-11
**Muammo turi:** Ovozli savolga noto'g'ri javob berish
**Holat:** Faol — tuzatish kerak

---

## 1. Muammo Tavsifi

Foydalanuvchi ovoz orqali savol beradi (masalan: "Einstein haqida ayting"), lekin tizim noto'g'ri javob beradi (masalan: "Microsoft Jervis haqida ma'lumot yo'q").

**Loglar misoli:**
```
STT: 'Menge enxten haqada ayeti ber. Ishii nochi? Ishii nochi? Ayi. Dede omla kirlile ishii nochi?'
Intent: chat
LLM: Menga enxten haqida gapiraman. Enxte - bu virtual yordamchi, lekin men topolmadim, enxte haqida ma'lumot yo'q.
```

**Aslida aytgan:** "Menga Einstein haqida ayting ber. Ishlaydi? Ishlaydi? Axir. Deylik biz bilan ishlaydi?"

---

## 2. Tizim Arxitekturasi

```
Foydalanuvchi → Mikrofon → STT (Whisper) → Router → LLM (Groq/llama) → TTS → Speaker
                                    ↓
                              Intent Aniqlash
                              (chat/weather/search/workflow)
```

### Komponentlar

| Komponent | Texnologiya | vazifa |
|-----------|-------------|--------|
| STT | faster-whisper | Ovozni matnga aylantirish |
| Router | Regex pattern | Intent aniqlash |
| LLM | Groq API (llama-3.3-70b) | Javob yaratish |
| Memory | PostgreSQL + Redis | Suhbat tarixini saqlash |
| TTS | edge-tts | Matnni ovozga aylantirish |

---

## 3. Muammo Sabablari

### 3.1 STT (Speech-to-Text) — Whisper

| Parametr | Qiymat |
|----------|--------|
| Model | faster-whisper |
| Til | uz (o'zbek) |
| Xato darajasi | Yuqori (technical so'zlar uchun) |

**Misol xatolari:**
- "Einstein" → "enxten" / "enxte" / "enste"
- "Telegram" → "telefram" (taxminiy)
- "Python" → "paison" (taxminiy)

**Sabab:** Whisper o'zbek tilida zaif, technical so'zlarni noto'g'ri transkripsiya qiladi.

### 3.2 Router (Intent Aniqlash)

| Intent | Pattern |
|--------|---------|
| chat | `.*` (fallback) |
| weather | `ob-havo`, `harorat` |
| search | `qidir`, `top`, `izla` |
| workflow | `workflow`, `n8n`, `telegram` |
| time | `soat`, `vaqt`, `kun` |
| system | `och`, `yop`, `run` |

**Muammo:** "Einstein" hech qanday pattern ga mos kelmaydi → "chat" intent ga yo'naltiriladi → LLM ga boradi.

### 3.3 LLM (Groq/llama-3.3-70b)

| Parametr | Qiymat |
|----------|--------|
| Provider | Groq API |
| Model | llama-3.3-70b-versatile |
| System Prompt | "Sen Zari — o'zbek tilida gapiradigan AI yordamchi" |
| Memory | Oxirgi 20 ta xabar saqlanadi |

**Muammo 1:** LLM "enxte" so'zini tushunmaydi → hallucination qiladi (Microsoft Jervis/Cortana haqida javob beradi).

**Muammo 2:** System prompt "Sen Zari" deydi, lekin xotirada avvalgi noto'g'ri javoblar bor → LLM o'zini "Jervis" deb ataydi.

**Muammo 3:** Har bir noto'g'ri javob xotirada qoladi → keyingi savollar yanada yomonlashadi.

### 3.4 Memory (Xotira)

| Parametr | Qiymat |
|----------|--------|
| Saqlash | PostgreSQL + Redis |
| Limit | Oxirgi 20 ta xabar |
| Tozalash | Avtomatik (yo'q) |

**Muammo:** Eski noto'g'ri javoblar tozalanmaydi → xotira ifloslanadi.

---

## 4. Muammo Oqimi (Flow)

```
1. Foydalanuvchi: "Einstein haqida ayting"
2. STT: "enxten haqada ayeti ber" (XATO)
3. Router: "chat" intent (TO'G'RI)
4. LLM: "enxte haqida ma'lumot yo'q" (XATO — hallucination)
5. Memory: noto'g'ri javob saqlanadi
6. Keyingi savol: yanada yomon javob
```

### Detailed Flow

```
[Foydalanuvchi] "Einstein haqida ayting"
       ↓
[Mikrofon] Audio yozadi (15 soniya)
       ↓
[STT/Whisper] "enxten haqada ayeti ber" ❌
       ↓
[Router] "chat" intent aniqladi ✓
       ↓
[Memory] System prompt + avvalgi xabarlar + noto'g'ri transkripsiya
       ↓
[LLM/Groq] "Enxte haqida ma'lumot yo'q" ❌ (hallucination)
       ↓
[Memory] Noto'g'ri javob saqlanadi ❌
       ↓
[TTS] "Enxte haqida ma'lumot yo'q" deydi
       ↓
[Speaker] Foydalanuvchi eshityapti
```

---

## 5. Ta'sir Qilgan Qismlar

| Qism | Ta'sir | Daraja | Izoh |
|------|--------|--------|------|
| STT | Noto'g'ri transkripsiya | Yuqori | Asosiy sabab |
| LLM | Hallucination | Yuqori | Ikkinchi darajali sabab |
| Memory | Ifloslanish | O'rtacha | Vaqt o'tishi bilan yomonlashadi |
| System Prompt | Zaif | O'rtacha | LLM ga to'g'ri yo'nalish bermaydi |
| Router | Normal | Past | Intent aniqlash to'g'ri ishlayapti |

---

## 6. Yechimlar

### Yechim 1: STT Post-Processing (Eng Oddiy)

```python
STT_CORRECTIONS = {
    "enxten": "Einstein",
    "enxte": "Einstein",
    "enste": "Einstein",
    "telefram": "Telegram",
    "paison": "Python",
    "javris": "Jarvis",
    "nayn": "n8n",
    "nayn": "n8n",
    "kortana": "Cortana",
    "vindovs": "Windows",
}


def correct_stt(text: str) -> str:
    for wrong, correct in STT_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    return text
```

**Afzallik:**
- Oddiy, tez, kam xarajatli
- Natija darhol ko'rinadi
- Qo'shimcha API kerak emas

**Kamchilik:**
- Har bir noto'g'ri so'zni qo'lda kiritish kerak
- Yangi so'zlar uchun doimiy yangilash kerak
- Regex bilan qilinsa yaxshiroq (case-insensitive)

### Yechim 2: System Prompt Kuchaytirish

```
Sen Zari — o'zbek tilida gapiradigan shaxsiy AI yordamchi.

MUHIM QOIDALAR:
1. Sen Zari'san, Jervis EMAS. Hech qachon o'zini Jervis deb atama.
2. Agar so'z noto'g'ri tushungan bo'lsa, qayta so'ra: "Men tushunmadim, qaytadan ayting"
3. Hallucination qilma — faqat aniq ma'lumot ber. Agar bilmasang, "Bilmayman" deb aytil.
4. Noto'g'ri transkripsiyani to'g'irlashga harakat qil. Masalan: "enxte" → "Einstein" bo'lishi mumkin.
5. Qisqa va aniq javob ber. Uzoq javob bermaysan.
```

**Afzallik:**
- LLM ga to'g'ri yo'nalish beradi
- Hallucination kamayadi
- Qo'shimcha kod kerak emas

**Kamchilik:**
- LLM hali ham hallucination qilishi mumkin
- System prompt uzunligi oshadi

### Yechim 3: Memory Boshqaruvi

```python
# Faqat oxirgi 10 ta xabarni saqlash
MAX_MESSAGES = 10

# Har 30 daqiqada eski xabarlarni tozalash
MEMORY_TTL = 1800  # seconds


# Session yangilash
async def clean_old_messages():
    messages = memory.get()
    if len(messages) > MAX_MESSAGES:
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]
        memory._messages = system_msgs + other_msgs[-MAX_MESSAGES:]
```

**Afzallik:**
- Xotira tozalanadi
- Eski xatolar yo'qoladi
- Tezlik oshadi

**Kamchilik:**
- Suhbat tarixi saqlanmaydi
- Foydalanuvchi eski suhbatlarni eslay olmaydi

### Yechim 4: LLM ga Tuzatish Mexanizmi

```python
CORRECTION_PROMPT = """
Agar foydalanuvchi so'zi noto'g'ri tushungan bo'lsa:
1. "Men tushunmadim, qaytadan ayting" de
2. Yoki "Siz X haqida so'rayapsizmi?" deb so'ra
3. Hech qachon "Jervis" deb o'zini atama
4. Faqat aniq ma'lumot ber, hallucination qilma
"""
```

**Afzallik:**
- LLM o'zi xatoni tuzatadi
- Foydalanuvchi tajribasi yaxshilanadi

**Kamchilik:**
- LLM har doim to'g'ri aniqlamaydi
- Qo'shimcha API so'rovlar kerak

---

## 7. Tavsiya Etilgan Tartib

| Tartib | Vazifa | Vaqt | Qiyinlik |
|--------|--------|------|----------|
| 1 | STT post-processing qo'shish | 1-2 kun | Oddiy |
| 2 | System prompt kuchaytirish | 1 kun | Oddiy |
| 3 | Memory boshqaruvini yaxshilash | 1-2 kun | O'rtacha |
| 4 | LLM tuzatish mexanizmi | 2-3 kun | Qiyin |

### Bosqich 1: STT Post-Processing

**Qilinishi kerak:**
1. `voice/stt.py` fayliga `correct_stt()` funksiyasi qo'shish
2. `STT_CORRECTIONS` lug'atini yaratish
3. Barcha noto'g'ri transkripsiyalarni qo'shish

**Kutilgan natija:** STT xatolari 70-80% ga kamayadi.

### Bosqich 2: System Prompt

**Qilinishi kerak:**
1. `core/main.py` faylidagi system prompt ni yangilash
2. Qo'shimcha qoidalar qo'shish
3. LLM ga "Zari" ekanini eslatish

**Kutilgan natija:** LLM hallucination 50-60% ga kamayadi.

### Bosqich 3: Memory

**Qilinishi kerak:**
1. `llm/memory.py` fayliga tozalash logikasi qo'shish
2. MAX_MESSAGES limitini qo'shish
3. Eski xabarlarni avtomatik tozalash

**Kutilgan natija:** Xotira ifloslanishi 80-90% ga kamayadi.

### Bosqich 4: LLM Tuzatish

**Qilinishi kerak:**
1. System prompt ga tuzatish qoidalari qo'shish
2. LLM ga "qayta so'ra" deb o'rgatish
3. Hallucination aniqlash logikasi

**Kutilgan natija:** LLM xatolarni o'zi tuzatadi.

---

## 8. Xulosa

**Asosiy muammo:** STT noto'g'ri transkripsiya + LLM hallucination + Memory ifloslanish.

**Eng samarali yechim:** STT post-processing + System prompt kuchaytirish.

**Kutilgan natija:** STT xatolari 70-80% ga kamayadi, LLM to'g'ri javob beradi, foydalanuvchi tajribasi yaxshilanadi.

**Keyingi qadamlar:**
1. STT post-processing qo'shish
2. System prompt ni yangilash
3. Memory tozalash logikasini qo'shish
4. Test qilish
5. Monitoring qo'shish

---

**Report muallifi:** Zari Development Team
**Sana:** 2026-07-11
**Versiya:** 1.0
