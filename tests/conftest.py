import pytest


@pytest.fixture
def sample_text():
    return "bugun havo qanday"


@pytest.fixture
def sample_audio_path(tmp_path):
    path = tmp_path / "test.wav"
    import numpy as np
    import soundfile as sf

    data = np.zeros(16000, dtype=np.float32)
    sf.write(str(path), data, 16000)
    return str(path)
