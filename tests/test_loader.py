from skills.base import BaseSkill
from skills.loader import SkillLoader


def test_skill_loader_discovers_concrete_skills():
    loader = SkillLoader(package_name="skills")
    discovered = loader.discover()

    assert isinstance(discovered, dict)
    assert "search" in discovered
    assert issubclass(discovered["search"], BaseSkill)
    assert "base" not in discovered
    assert "loader" not in discovered


def test_skill_loader_skips_private_modules():
    loader = SkillLoader(package_name="skills")
    discovered = loader.discover()

    for name in discovered:
        assert not name.startswith("_")


def test_skill_loader_instantiate_all():
    from unittest.mock import patch

    with patch("llm.groq_client.Groq"):
        loader = SkillLoader(package_name="skills")
        instances = loader.instantiate_all()

        assert isinstance(instances, dict)
        assert "search" in instances
        assert isinstance(instances["search"], BaseSkill)
