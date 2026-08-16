import enum
import logging
from typing import Literal

log = logging.getLogger("zari")


class DialogState(enum.Enum):
    IDLE = "idle"
    AWAITING_PARAM = "awaiting_param"
    AWAITING_CONFIRM = "awaiting_confirm"


PARAM_QUESTIONS: dict[str, str] = {
    "song": "Qanday musiqa turi? Masalan: jazz, pop, rock, yoki qo'shiq nomi",
    "city": "Qaysi shahar?",
    "duration": "Qancha vaqt? Masalan: 5 daqiqa yoki 30 soniya",
    "content": "Nima yozib olay?",
    "path": "Qaysi fayl yoki papka?",
    "target": "Kimga?",
    "query": "Nima qidiraymi?",
}


SKILL_PARAMS: dict[str, list[str]] = {
    "music": ["song"],
    "weather": ["city"],
    "timer": ["duration"],
    "note": ["content"],
    "search": ["query"],
    "filemanager": [],
    "email": ["target", "content"],
    "calculator": [],
    "network": [],
    "clipboard": [],
    "screenshot": [],
    "workflow": [],
    "wiki": [],
    "system_info": [],
}


def requires_params(intent: str) -> list[str]:
    return SKILL_PARAMS.get(intent, [])


AFFIRMATIVE = {"ha", "yes", "ok", "xa", "okey", "yaxshi", "ma'qul", "tasdiq", "albatta"}
NEGATIVE = {"yo'q", "yoq", "no", "not", "bekor", "to'xta", "bas"}


class DialogManager:
    def __init__(self):
        self.state = DialogState.IDLE
        self.pending_intent: str | None = None
        self.pending_text: str | None = None
        self.remaining_params: list[str] = []
        self.collected_params: dict[str, str] = {}
        self.danger_skill = None

    def reset(self):
        self.state = DialogState.IDLE
        self.pending_intent = None
        self.pending_text = None
        self.remaining_params = []
        self.collected_params = {}
        self.danger_skill = None

    def begin(self, intent: str, text: str) -> bool:
        needed = requires_params(intent)
        if not needed:
            return False
        self.state = DialogState.AWAITING_PARAM
        self.pending_intent = intent
        self.pending_text = text
        self.remaining_params = list(needed)
        self.collected_params = {}
        return True

    def begin_confirm(self, intent: str, text: str, skill) -> str:
        self.state = DialogState.AWAITING_CONFIRM
        self.pending_intent = intent
        self.pending_text = text
        self.danger_skill = skill
        label = getattr(skill, "confirmation_type", "danger")
        return f"{skill.__class__.__name__}: Bu buyruq {label}. Tasdiqlaysizmi? (ha/yo'q)"

    def handle_confirm_response(self, text: str) -> bool | None:
        text_clean = text.lower().strip().strip(".,!?")
        if text_clean in AFFIRMATIVE:
            self.state = DialogState.IDLE
            return True
        if text_clean in NEGATIVE:
            self.state = DialogState.IDLE
            return False
        return None

    def next_question(self) -> str | None:
        if not self.remaining_params:
            return None
        p = self.remaining_params[0]
        return PARAM_QUESTIONS.get(p, f"Iltimos, {p} ni ayting.")

    def add_param(self, value: str) -> str | None:
        if not self.remaining_params:
            self.reset()
            return None
        param_name = self.remaining_params.pop(0)
        self.collected_params[param_name] = value
        if self.remaining_params:
            return self.next_question()
        return None

    def enriched_text(self) -> str:
        if not self.pending_text:
            return ""
        extra = " ".join(self.collected_params.values())
        return f"{self.pending_text} {extra}" if extra else self.pending_text

    @property
    def is_active(self) -> bool:
        return self.state in (DialogState.AWAITING_PARAM, DialogState.AWAITING_CONFIRM)

    @property
    def is_awaiting_confirm(self) -> bool:
        return self.state == DialogState.AWAITING_CONFIRM
