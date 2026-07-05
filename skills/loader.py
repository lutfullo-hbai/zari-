import importlib
import inspect
import pkgutil
from pathlib import Path

from skills.base import BaseSkill


class SkillLoader:
    """Load concrete skills from the skills package dynamically."""

    def __init__(self, package_name: str = "skills"):
        self.package_name = package_name

    def discover(self) -> dict[str, type[BaseSkill]]:
        skills: dict[str, type[BaseSkill]] = {}
        package = importlib.import_module(self.package_name)
        package_path = getattr(package, "__file__", None)
        if not package_path:
            return {}

        package_dir = Path(package_path).resolve().parent

        for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
            if module_name.startswith("_"):
                continue
            if module_name in {"base", "loader"}:
                continue

            module = importlib.import_module(f"{self.package_name}.{module_name}")
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is BaseSkill or not issubclass(obj, BaseSkill):
                    continue
                if inspect.isabstract(obj):
                    continue
                skills[module_name] = obj

        return skills

    def instantiate_all(self) -> dict[str, BaseSkill]:
        instances: dict[str, BaseSkill] = {}
        for name, skill_cls in self.discover().items():
            try:
                instances[name] = skill_cls()
            except Exception:
                continue
        return instances
