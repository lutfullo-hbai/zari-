from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from voice.vad import VAD


class TestVAD:
    def test_vad_init(self):
        vad = VAD(aggressiveness=3)
        assert vad.sample_rate == 16000
        assert vad.frame_ms == 30
        assert vad.frame_size > 0

    def test_frame_generator_splits_correctly(self):
        vad = VAD()
        frame_size = vad.frame_size
        audio = b"x" * (frame_size * 3)
        frames = list(vad._frame_generator(audio))
        assert len(frames) == 3
        assert all(len(f) == frame_size for f in frames)

    def test_frame_generator_partial_frame_skipped(self):
        vad = VAD()
        frame_size = vad.frame_size
        audio = b"x" * (frame_size * 2 + 10)
        frames = list(vad._frame_generator(audio))
        assert len(frames) == 2

    def test_is_speech_too_short(self):
        vad = VAD()
        assert vad.is_speech(b"") is False
        assert vad.is_speech(b"short") is False
        assert vad.is_speech(b"x" * (vad.frame_size - 1)) is False

    def test_is_speech_delegates_to_webrtcvad(self):
        vad = VAD()
        frame = b"x" * vad.frame_size
        with patch.object(vad.vad, "is_speech", return_value=True):
            assert vad.is_speech(frame) is True

    def test_detect_speech_no_frames(self):
        vad = VAD()
        assert vad.detect_speech(b"") is False
        assert vad.detect_speech(b"short") is False

    def test_detect_speech_below_threshold(self):
        vad = VAD()
        frame_size = vad.frame_size
        audio = b"x" * frame_size * 5
        with patch.object(vad.vad, "is_speech", return_value=False):
            assert vad.detect_speech(audio) is False

    def test_detect_speech_above_threshold(self):
        vad = VAD()
        frame_size = vad.frame_size
        audio = b"x" * frame_size * 5
        with patch.object(vad.vad, "is_speech", return_value=True):
            assert vad.detect_speech(audio) is True

    def test_detect_speech_partial_speech(self):
        vad = VAD()
        frame_size = vad.frame_size
        audio = b"x" * frame_size * 5
        call_count = 0

        def mock_is_speech(*args):
            nonlocal call_count
            call_count += 1
            return call_count <= 2

        with patch.object(vad.vad, "is_speech", side_effect=mock_is_speech):
            result = vad.detect_speech(audio)
            assert result == (2 / 5 >= 0.3)

    def test_is_speech_robust_with_history(self):
        vad = VAD()
        frame = b"x" * vad.frame_size
        with patch.object(vad.vad, "is_speech", return_value=True):
            for _ in range(6):
                assert vad.is_speech_robust(frame) is True

    def test_is_speech_robust_below_threshold(self):
        vad = VAD()
        frame = b"x" * vad.frame_size
        with patch.object(vad.vad, "is_speech", return_value=False):
            for _ in range(5):
                result = vad.is_speech_robust(frame)
            assert result is False
        assert sum(vad.history) == 0


class TestSTT:
    def test_stt_init(self):
        with patch("voice.stt.WhisperModel") as mock_model:
            from voice.stt import SpeechToText

            stt = SpeechToText(model_name="tiny")
            mock_model.assert_called_once_with("tiny", compute_type="int8")
            assert stt.language == "uz"

    def test_stt_transcribe(self):
        with patch("voice.stt.WhisperModel") as mock_model:
            from voice.stt import SpeechToText

            mock_segment = MagicMock()
            mock_segment.text = "salom dunyo"
            mock_model.return_value.transcribe.return_value = (
                iter([mock_segment]),
                MagicMock(language="uz", language_probability=0.95),
            )

            stt = SpeechToText()
            result = stt.transcribe("/fake/path.wav")

            assert result == "salom dunyo"

    def test_stt_transcribe_empty(self):
        with patch("voice.stt.WhisperModel") as mock_model:
            from voice.stt import SpeechToText

            mock_model.return_value.transcribe.return_value = (
                iter([]),
                MagicMock(language="uz", language_probability=0.0),
            )

            stt = SpeechToText()
            result = stt.transcribe("/fake/path.wav")

            assert result == ""


class TestTTS:
    @pytest.mark.asyncio
    async def test_tts_speak(self):
        with (
            patch("voice.tts._EdgeTTSBackend") as mock_backend,
            patch("voice.tts.sf.read") as mock_read,
            patch("voice.tts.sd.play"),
            patch("voice.tts.sd.wait"),
            patch("voice.tts.Path"),
        ):
            from voice.tts import TextToSpeech

            mock_backend.return_value.synthesize = AsyncMock(return_value="/tmp/test.mp3")
            mock_read.return_value = (np.zeros(16000, dtype=np.float32), 24000)

            tts = TextToSpeech(voice="uz-UZ-MadinaNeural")
            await tts.speak("Salom")

            mock_backend.assert_called_once_with("uz-UZ-MadinaNeural")

    @pytest.mark.asyncio
    async def test_tts_save(self):
        with patch("voice.tts._EdgeTTSBackend") as mock_backend:
            from voice.tts import TextToSpeech

            mock_backend.return_value.save = AsyncMock()

            tts = TextToSpeech(voice="uz-UZ-MadinaNeural")
            await tts.save("Salom", "/tmp/test.mp3")

            mock_backend.assert_called_once_with("uz-UZ-MadinaNeural")
            mock_backend.return_value.save.assert_called_once_with("Salom", "/tmp/test.mp3")

    def test_resample_same_rate(self):
        from voice.tts import resample

        data = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        result = resample(data, 16000, 16000)
        assert np.array_equal(result, data)

    def test_resample_different_rate(self):
        from voice.tts import resample

        data = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        result = resample(data, 16000, 48000)
        assert len(result) > len(data)
        assert result.dtype == data.dtype


class TestWakeWordDetector:
    def test_wake_init(self):
        mock_devices = [
            {"name": "fake mic", "max_input_channels": 1, "default_samplerate": 16000},
        ]
        with (
            patch("voice.wake.sd.query_devices", return_value=mock_devices),
            patch("voice.wake.sd.check_input_settings"),
        ):
            from voice.wake import WakeWordDetector

            wake = WakeWordDetector()
            assert wake.sample_rate == 16000
            assert wake.frame_ms == 30
            assert wake.energy_threshold == 5
            assert wake.speech_frames_needed == 8

    def test_wake_device_not_found(self):
        with (
            patch("voice.wake.sd.query_devices", return_value=[]),
            patch("voice.wake.sd.check_input_settings", side_effect=Exception("No device")),
        ):
            from voice.wake import WakeWordDetector

            wake = WakeWordDetector()
            assert wake.device is None

    def test_rms_calculation(self):
        mock_devices = [
            {"name": "fake mic", "max_input_channels": 1, "default_samplerate": 16000},
        ]
        with (
            patch("voice.wake.sd.query_devices", return_value=mock_devices),
            patch("voice.wake.sd.check_input_settings"),
        ):
            from voice.wake import WakeWordDetector

            wake = WakeWordDetector()
            audio = np.array([100, 200, -100, -200], dtype=np.int16)
            rms = wake._rms(audio)
            expected = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
            assert rms == expected
