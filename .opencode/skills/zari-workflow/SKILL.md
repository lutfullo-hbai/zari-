---
name: zari-workflow
description: Zari loyihasi uchun ishlash standartlari. Git workflow, Clean Code, 12 Factor App. Use when developing Zari, writing skills, fixing bugs, refactoring, or committing changes.
---

# Zari Workflow Standartlari

## 1. Git Workflow

### Branch Strategy

```
main         (production-ready, faqat user merge qiladi)
  └── dev    (integration branch, barcha o'zgarishlar yig'iladi)
       ├── feature/XXX    (yangi feature)
       ├── fix/XXX        (bug fix)
       ├── refactor/XXX   (refactoring)
       └── docs/XXX       (documentation)
```

### Qoidalar

1. **main** — har doim production-ready holatda. Hech qachon to'g'ridan-to'g'ri push qilinmaydi. Faqat user o'zi merge qiladi dev → main.

2. **dev** — barcha o'zgarishlar yig'iladigan branch. Feature branchlar shu yerdan ochiladi va shu yerga merge qilinadi.

3. **Feature branch** — har bir o'zgarish uchun yangi branch:
   ```
   git checkout dev
   git pull origin dev
   git checkout -b feature/nima-ozgarishi
   ```

### Commit Messages (Conventional Commits)

```
feat: yangi skill qo'shildi — WeatherForecast
fix: memory leak tuzatildi — session cleanup
refactor: ZariPipeline -> alohida worker'larga ajratildi
docs: READEME ga API documentation qo'shildi
test: SystemInfoSkill testlari yozildi
style: formatting, import order
chore: dependency update, config change
```

Format: `type: qisqa tavsif — qo'shimcha detal`

### Pull Request (Merge) Strategy

1. Kichik o'zgarishlar (< 10 fayl) — bitta commit bilan PR
2. Katta o'zgarishlar — mayda qismlarga bo'linadi:
   ```
   feat: database schema qo'shildi
   feat: repository layer yozildi
   feat: service layer yozildi
   feat: API endpoint yozildi
   ```
3. Har bir qism test qilinadi va alohida PR qilinadi

### Merge Checklist

Har bir PR dev'ga merge qilishdan oldin:
- [ ] `pytest` dan o'tgan
- [ ] `ruff` lint dan o'tgan
- [ ] Hech qanday crash/exception yo'q
- [ ] Loglar tekshirilgan
- [ ] Kod Clean Code tamoyillariga mos
- [ ] 12 Factor App ga mos

---

## 2. Clean Code Tamoyillari

### 2.1 Naming

```python
# YOMON
def process(d, x):
    pass


# YAXSHI
def process_user_data(user_data: dict, max_retries: int) -> Result:
    pass
```

- Class -> `UpperCamelCase`: `UserPersona`, `SessionMemory`, `SystemInfoSkill`
- Function -> `snake_case`: `get_user_name()`, `validate_input()`
- Variable -> `snake_case`: `user_name`, `max_retries`, `is_active`
- Constant -> `UPPER_CASE`: `MAX_RETRIES = 3`, `DEFAULT_TIMEOUT = 30`
- Boolean -> `is_`, `has_`, `should_`: `is_ready`, `has_permission`, `should_retry`

### 2.2 Functions

```python
# YOMON — 3 xil ish qiladi
def process(data):
    data = validate(data)
    result = calculate(data)
    save(result)
    send_email(result)
    return result


# YAXSHI — bitta ish qiladi
def validate_and_calculate(data: dict) -> Result:
    validated = validate(data)
    return calculate(validated)


def save_and_notify(result: Result) -> None:
    save_to_database(result)
    send_notification(result)
```

- Har bir function **bitta ish** qiladi
- **3 dan ko'p argument** bo'lsa, dataclass yoki Settings obyekti ishlatilsin
- **Side-effect** lar minimallasin
- **Early return** — nesting chuqur bo'lmasin

### 2.3 Classes

```python
# YOMON — God class
class ZariPipeline:
    def audio_worker(self): ...
    def llm_worker(self): ...
    def tts_worker(self): ...
    def email_send(self): ...
    def search_web(self): ...


# YAXSHI — Single Responsibility
class AudioProcessor:
    def process(self, audio: bytes) -> str: ...


class SkillExecutor:
    def execute(self, intent: str, text: str) -> Result: ...
```

- SRP (Single Responsibility) — bitta klass = bitta mas'uliyat
- DI (Dependency Injection) — dependency'lar tashqaridan berilsin
- Inheritance o'rniga Composition (Agar mumkin bo'lsa)

### 2.4 Error Handling

```python
# YOMON
try:
    result = risky_operation()
except:
    pass

# YAXSHI
try:
    result = risky_operation()
except ValueError as e:
    log.warning("Invalid input: %s", e)
    return default_value
except TimeoutError as e:
    log.error("Operation timed out: %s", e)
    raise
```

- Hech qachon `except: pass` ishlatilmasin
- Specific exception'lar tutilsin
- Error handling domainga mos bo'lsin
- Log message'lari informative bo'lsin

### 2.5 Comments

```python
# YOMON
x = x + 1  # x ni 1 ga oshir

# YAXSHI — kod o'zini o'zi tushuntirsin
increment_counter()

# YAXSHI — nega qilinganini tushuntirish
# Retry bilan chunki DB vaqti-vaqti bilan connection drop qiladi
for attempt in range(3):
    try:
        return await db.save(data)
    except ConnectionError:
        if attempt == 2:
            raise
        await asyncio.sleep(1)
```

- **Nega** qilinganini yozing, **nima** qilinganini emas
- Kod o'zini o'zi tushuntirishi kerak
- TODO commentlari `# TODO(username): nima qilish kerak` formatida

### 2.6 Type Hints

```python
# YOMON
def get_user(id):
    return db.query(id)


# YAXSHI
from collections.abc import Sequence


def get_user(user_id: int) -> User | None:
    return db.query(User, user_id)
```

- Barcha function signature'larida type hints bo'lishi shart
- Return type ko'rsatilishi shart
- Union type'lar uchun `X | Y` (Python 3.10+) sintaksis

---

## 3. 12 Factor App

### 3.1 Codebase (1-faktor)
- Bitta repo, bitta codebase
- Har bir deploy uchun bitta version
- `.env` va config fayllar **commit qilinmaydi** (faqat `.env.example` commit qilinadi)

### 3.2 Dependencies (2-faktor)
- `requirements.txt` yoki `pyproject.toml` da aniq version ko'rsatilsin
- `pip freeze > requirements.txt` — aniq versionlarni saqlash
- Hech qachon `pip install package` qilib, requirements.txt ga yozmasdan qoldirmang

### 3.3 Config (3-faktor)
- Config environment variable'lar orqali
- `pydantic-settings` ishlatiladi (allaqachon ishlatilyapti)
- `.env.example` da default qiymatlar bilan
- Hech qachon secret'lar kodga hardcode qilinmaydi

### 3.4 Backing Services (4-faktor)
- DB, Redis, Ollama — barchasi `config` dan URL orqali ulansin
- Local va production bir xil interface
- Docker Compose bilan local development

### 3.5 Build, Release, Run (5-faktor)
- `Dockerfile` — build
- `docker-compose.yml` — release
- `docker compose up` — run
- Build va run qat'iy ajratilgan

### 3.6 Processes (6-faktor)
- Stateless process'lar
- Session state faqat DB/Redis da
- Process restart da hech qanday ma'lumot yo'qolmasligi kerak

### 3.7 Port Binding (7-faktor)
- Zari self-contained (port binding orqali)
- HTTP server bo'lsa, port config'dan olinadi

### 3.8 Concurrency (8-faktor)
- Process modeli: worker'lar (asyncio tasks)
- Horizontal scaling: worker soni config'da
- Har bir worker o'z queue'siga ega

### 3.9 Disposability (9-faktor)
- Graceful shutdown: `pipeline.stop()` — queue'larni drain qiladi
- Signal handling: SIGINT/SIGTERM
- Worker crash → supervisor auto-restart

### 3.10 Dev/Prod Parity (10-faktor)
- Docker Compose development uchun
- Production bilan bir xil stack: PostgreSQL + Redis + Ollama
- `.env.docker` — docker muhiti uchun

### 3.11 Logs (11-faktor)
- Structured JSON logging (allaqachon ishlatyapti)
- stdout ga log (faylga emas)
- Log aggregation uchun tayyor

### 3.12 Admin Processes (12-faktor)
- Migrations: database schema `init_db()` da yaratiladi
- Admin scripts: `python -m core.main --test-mic`, `--list-devices`
- Bir martalik task'lar container ichida run qilinadi

---

## 4. Zari Skill Yozish Standarti

### Skill strukturasi

```python
"""
Skill name — qisqa description

Longer description of what this skill does,
configuration options, and usage examples.
"""

import logging
from collections.abc import Sequence
from typing import Any

from core.config import settings
from skills.base import BaseSkill

log = logging.getLogger("zari")


class SystemInfoSkill(BaseSkill):
    """Bir gapda skill nima qilishi."""

    priority = 10
    timeout = 5.0
    retries = 0

    def __init__(self, custom_param: str | None = None) -> None:
        super().__init__()
        self._custom_param = custom_param or settings.some_config_value

    async def execute(self, query: str) -> dict[str, Any] | None:
        try:
            result = await self._do_work(query)
            return {"response": result, "context": result, "source": "skill_name"}
        except ValueError:
            log.warning("Invalid query: %s", query)
            return None
        except Exception as e:
            log.error("Skill error: %s", e, exc_info=True)
            return None

    async def _do_work(self, query: str) -> str:
        """Bir vazifani bajaradi."""
        ...
```

### Skill yozish qoidalari

1. **`BaseSkill`** dan voris oling
2. `priority`, `timeout`, `retries` ni aniq belgilang
3. `execute()` async bo'lsin
4. Return dict: `{"response": ..., "context": ..., "source": ...}`
5. Error handling: specific exception'lar
6. Logging: informative message'lar
7. Type hints: barcha method'lar
8. Hech qachon `except: pass` ishlatmang
9. Config qiymatlari `settings` dan, hardcode emas
10. Skill nomi fayl nomi bilan bir xil bo'lsin
