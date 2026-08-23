"""M6 System Control Pack testlari: Volume, Brightness, Input, Media."""

from unittest.mock import patch

import pytest

from core.router import match_intents
from skills.brightness import BrightnessSkill


class TestVolumeSkill:
    @pytest.fixture
    def skill(self):
        from skills.volume import VolumeSkill

        return VolumeSkill()

    @pytest.mark.asyncio
    async def test_set_exact_level(self, skill):
        with (
            patch("skills.volume.shutil.which", return_value="/usr/bin/amixer"),
            patch("skills.volume.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            result = await skill.execute("ovozni 50 ga qo'y")

        assert result is not None
        assert "50%" in result["response"]
        cmd = mock_run.call_args.args[0]
        assert cmd == ["amixer", "sset", "Master", "50%"]

    @pytest.mark.asyncio
    async def test_level_clamped_to_100(self, skill):
        with (
            patch("skills.volume.shutil.which", return_value="/usr/bin/amixer"),
            patch("skills.volume.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            await skill.execute("ovozni 250 ga qo'y")

        assert mock_run.call_args.args[0][-1] == "100%"

    @pytest.mark.asyncio
    async def test_mute_and_unmute(self, skill):
        with (
            patch("skills.volume.shutil.which", return_value="/usr/bin/amixer"),
            patch("skills.volume.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            await skill.execute("ovozni o'chir")
            assert mock_run.call_args.args[0][-1] == "mute"
            await skill.execute("ovozni qayta yoq")
            assert mock_run.call_args.args[0][-1] == "unmute"

    @pytest.mark.asyncio
    async def test_increase_without_number(self, skill):
        with (
            patch("skills.volume.shutil.which", return_value="/usr/bin/amixer"),
            patch("skills.volume.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            await skill.execute("ovozni oshir")
        assert mock_run.call_args.args[0][-1] == "10%+"

    @pytest.mark.asyncio
    async def test_no_amixer(self, skill):
        with patch("skills.volume.shutil.which", return_value=None):
            result = await skill.execute("ovozni 50 ga")
        assert "topilmadi" in result["response"]


class TestBrightnessSkill:
    @pytest.fixture
    def skill(self):
        from skills.brightness import BrightnessSkill

        s = BrightnessSkill()
        s._output = "HDMI-1"
        return s

    @pytest.mark.asyncio
    async def test_set_percent(self, skill):
        with (
            patch("skills.brightness.shutil.which", return_value="/usr/bin/xrandr"),
            patch.object(BrightnessSkill, "_get_current", return_value=1.0),
            patch("skills.brightness.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            result = await skill.execute("yorqinlikni 70 ga qo'y")

        assert result is not None
        assert "70%" in result["response"]
        cmd = mock_run.call_args.args[0]
        assert cmd[:4] == ["xrandr", "--output", "HDMI-1", "--brightness"]
        assert cmd[4] == "0.7"

    @pytest.mark.asyncio
    async def test_minimum_floor_20_percent(self, skill):
        """0.2 dan past aniq so'rov ham xavfsiz chegara (0.2) da qoladi."""
        with (
            patch("skills.brightness.shutil.which", return_value="/usr/bin/xrandr"),
            patch.object(BrightnessSkill, "_get_current", return_value=1.0),
            patch("skills.brightness.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            await skill.execute("yorqinlikni 5 ga qo'y")

        assert mock_run.call_args.args[0][-1] == "0.2"

    @pytest.mark.asyncio
    async def test_decrease_step(self, skill):
        with (
            patch("skills.brightness.shutil.which", return_value="/usr/bin/xrandr"),
            patch.object(BrightnessSkill, "_get_current", return_value=0.8),
            patch("skills.brightness.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            await skill.execute("ekranni xiralashtir")
        # 0.8 - 0.10 = 0.7
        assert mock_run.call_args.args[0][-1] == "0.7"


class TestInputControlSkill:
    @pytest.fixture
    def skill(self):
        from skills.input import InputControlSkill

        return InputControlSkill()

    def test_requires_confirmation(self, skill):
        """Klaviatura/sichqoncha hech qachon tasdiqsiz bajarilmasligi kerak."""
        assert skill.requires_confirmation is True

    @pytest.mark.asyncio
    async def test_press_enter(self, skill):
        with (
            patch("skills.input.shutil.which", return_value="/usr/bin/xdotool"),
            patch("skills.input.subprocess.run") as mock_run,
        ):
            result = await skill.execute("enter tugmasini bosing")

        assert result is not None
        assert mock_run.call_args.args[0] == ["xdotool", "key", "Return"]

    @pytest.mark.asyncio
    async def test_reject_unknown_key(self, skill):
        with (
            patch("skills.input.shutil.which", return_value="/usr/bin/xdotool"),
            patch("skills.input.subprocess.run") as mock_run,
        ):
            result = await skill.execute("super+secret bosing")

        assert "ruxsat etilmagan" in result["response"]
        mock_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_ctrl_combo(self, skill):
        with (
            patch("skills.input.shutil.which", return_value="/usr/bin/xdotool"),
            patch("skills.input.subprocess.run") as mock_run,
        ):
            await skill.execute("ctrl+s bosing")
        assert mock_run.call_args.args[0] == ["xdotool", "key", "ctrl+s"]

    @pytest.mark.asyncio
    async def test_mouse_move_bounds(self, skill):
        with (
            patch("skills.input.shutil.which", return_value="/usr/bin/xdotool"),
            patch("skills.input.subprocess.run") as mock_run,
        ):
            await skill.execute("sichqonchani 999999,100 ga sur")

        # Chegaradan tashqari koordinata parse qilinmaydi → key yo'liga ketmaydi
        args = mock_run.call_args.args[0] if mock_run.call_args else []
        if args:
            x = int(args[args.index("mousemove") + 1])
            assert x <= 7680


class TestMediaSkill:
    @pytest.fixture
    def skill(self):
        from skills.media import MediaSkill

        return MediaSkill()

    @pytest.mark.asyncio
    async def test_pause_via_playerctl(self, skill):
        with (
            patch("skills.media.shutil.which", return_value="/usr/bin/playerctl"),
            patch("skills.media.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            result = await skill.execute("musiqani to'xtat")

        assert result is not None
        assert mock_run.call_args.args[0] == ["/usr/bin/playerctl", "play-pause"]

    @pytest.mark.asyncio
    async def test_next_track(self, skill):
        with (
            patch("skills.media.shutil.which", return_value="/usr/bin/playerctl"),
            patch("skills.media.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            await skill.execute("keyingi trekka o't")
        assert mock_run.call_args.args[0] == ["/usr/bin/playerctl", "next"]

    @pytest.mark.asyncio
    async def test_no_playerctl(self, skill):
        with patch("skills.media.shutil.which", return_value=None):
            result = await skill.execute("pauza")
        assert "topilmadi" in result["response"]

    @pytest.mark.asyncio
    async def test_play_local_file_missing(self, skill, tmp_path):
        with patch("skills.media.shutil.which", return_value="/usr/bin/mpv"):
            result = await skill.execute(f"{tmp_path}/yok_musiqa.mp3 ni ijro et")

        assert result is not None
        assert "topilmadi" in result["response"]


class TestM6Routing:
    def test_volume_routing(self):
        assert match_intents("ovozni 50 ga qo'y")[0] == "volume"

    def test_brightness_routing(self):
        assert match_intents("yorqinlikni 70 ga qo'y")[0] == "brightness"

    def test_media_beats_music_on_pause(self):
        intents = match_intents("musiqani to'xtat")
        assert intents[0] == "media"

    def test_input_routing(self):
        assert match_intents("sichqonchani 100,200 ga sur")[0] == "input"
        assert match_intents("enter bosing")[0] == "input"

    def test_faylni_och_goes_filemanager_first(self):
        """REGRESSIYA: 'faylni och' filemanager(80) > system(25)."""
        intents = match_intents("faylni och")
        assert intents[0] == "filemanager"

    def test_brain_knows_new_skills(self):
        from core.brain import AVAILABLE_SKILLS

        for name in ("volume", "brightness", "input", "media"):
            assert name in AVAILABLE_SKILLS


class TestBrightnessRealWorld:
    @pytest.mark.asyncio
    async def test_zero_report_treated_as_unreadable(self):
        """REGRESSIYA: ba'zi drayverlar yoniq ekranda Brightness: 0.0 reportlaydi —
        bunday qiymat neytral 1.0 baza sifatida olinadi."""
        from skills.brightness import BrightnessSkill

        fake_verbose = (
            "Screen 0: minimum 8 x 8, current 3840 x 1080\n"
            "HDMI-1 connected primary 1920x1080+0+0 (0x43) normal\n"
            "\tBrightness: 0.0\n"
            "eDP-1 connected 1920x1080+1920+0 (0x5f) normal\n"
            "\tBrightness: 1.0\n"
        )
        skill = BrightnessSkill()
        with patch("skills.brightness.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = fake_verbose
            cur = await skill._get_current()

        assert cur == 1.0

    @pytest.mark.asyncio
    async def test_reads_own_monitor_section_not_first_found(self):
        """HDMI-1 primary tanlanadi va O'Z Brightness'i o'qiladi."""
        from skills.brightness import BrightnessSkill

        fake_verbose = (
            "HDMI-1 connected primary (0x43)\n\tBrightness: 0.85\neDP-1 connected (0x5f)\n\tBrightness: 1.0\n"
        )
        skill = BrightnessSkill()
        skill._output = None
        with patch("skills.brightness.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = fake_verbose
            out = await skill._get_output()
            cur = await skill._get_current()

        assert out == "HDMI-1"
        assert cur == 0.85
