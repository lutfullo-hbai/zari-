import asyncio
import logging
import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from core.config import settings

log = logging.getLogger("zari")


def resample(data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return data
    ratio = target_sr / orig_sr
    n_samples = int(len(data) * ratio)
    indices = np.linspace(0, len(data) - 1, n_samples)
    return np.interp(indices, np.arange(len(data)), data).astype(data.dtype)


class _EdgeTTSBackend:
    def __init__(self, voice: str):
        import edge_tts

        self._communicate = edge_tts.Communicate
        self.voice = voice

    async def synthesize(self, text: str) -> str:
        communicate = self._communicate(text, self.voice)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
            await communicate.save(tmp_path)
        return tmp_path

    async def save(self, text: str, output_path: str):
        communicate = self._communicate(text, self.voice)
        await communicate.save(output_path)


class _PiperTTSBackend:
    def __init__(self, voice: str):
        self.model_path = settings.piper_model_path
        self.voice = voice or settings.piper_voice
        self._init_piper()

    def _init_piper(self):
        try:
            import piper

            self._piper = piper
            voice = self.voice
            if self.model_path:
                voice = self.model_path
            self._pipe = piper.load_voice(voice)
            log.info("Piper TTS: voice=%s", voice)
        except Exception as e:
            log.error("Piper init failed: %s, fallback to edge-tts", e)
            raise

    async def synthesize(self, text: str) -> str:
        import soundfile as sf

        loop = asyncio.get_event_loop()

        def _generate():
            audio = self._piper.synthesize(text, self._pipe)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            sf.write(tmp.name, audio, self._pipe.sample_rate)
            return tmp.name

        tmp_path = await loop.run_in_executor(None, _generate)
        return tmp_path

    async def save(self, text: str, output_path: str):
        import soundfile as sf

        loop = asyncio.get_event_loop()

        def _save():
            audio = self._piper.synthesize(text, self._pipe)
            sf.write(output_path, audio, self._pipe.sample_rate)

        await loop.run_in_executor(None, _save)


class TextToSpeech:
    def __init__(self, voice: str = ""):
        self.voice = voice or settings.tts_voice
        self.output_device = settings.audio_output_device
        self.output_sample_rate = settings.audio_output_sample_rate

        engine = (settings.tts_engine or "edge").lower()
        if engine == "piper":
            try:
                self._backend = _PiperTTSBackend(self.voice)
                log.info("TTS engine: Piper")
            except Exception:
                log.warning("Piper unavailable, falling back to edge-tts")
                self._backend = _EdgeTTSBackend(self.voice)
        else:
            self._backend = _EdgeTTSBackend(self.voice)
            log.info("TTS engine: edge-tts")

    async def speak(self, text: str):
        tmp_path = await self._backend.synthesize(text)
        await asyncio.to_thread(self._play_file, tmp_path)

    def _play_file(self, path: str):
        try:
            data, sr = sf.read(path)
            if data.ndim > 1 and data.shape[1] > 1:
                data = data.mean(axis=1)
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
        await self._backend.save(text, output_path)
