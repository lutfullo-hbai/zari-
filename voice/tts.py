import asyncio
import logging
import edge_tts
import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile
from pathlib import Path

from core.config import settings

log = logging.getLogger("zari")


def resample(data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return data
    ratio = target_sr / orig_sr
    n_samples = int(len(data) * ratio)
    indices = np.linspace(0, len(data) - 1, n_samples)
    return np.interp(indices, np.arange(len(data)), data).astype(data.dtype)


class TextToSpeech:
    def __init__(self, voice: str = ""):
        self.voice = voice or settings.tts_voice
        self.output_device = settings.audio_output_device
        self.output_sample_rate = settings.audio_output_sample_rate

    async def speak(self, text: str):
        communicate = edge_tts.Communicate(text, self.voice)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
            await communicate.save(tmp_path)

        await asyncio.to_thread(self._play_file, tmp_path)

    def _play_file(self, path: str):
        try:
            data, sr = sf.read(path)
            if sr != self.output_sample_rate:
                data = resample(data, sr, self.output_sample_rate)
                sr = self.output_sample_rate
            device = self.output_device
            if device is not None:
                sd.play(data, sr, device=device)
            else:
                sd.play(data, sr)
            sd.wait()
        except Exception as e:
            log.error("Ovoz chiqarish xatosi: %s", e, exc_info=True)
        finally:
            Path(path).unlink()

    async def save(self, text: str, output_path: str):
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_path)
