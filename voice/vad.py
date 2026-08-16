import collections

import numpy as np
import webrtcvad


class VAD:
    def __init__(self, aggressiveness: int = 2):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = 16000
        self.frame_ms = 30
        self.frame_size = int(self.sample_rate * self.frame_ms / 1000) * 2
        self.history = collections.deque(maxlen=10)
        self.speech_frames = 0
        self.silence_frames = 0

    def _frame_generator(self, audio_data: bytes):
        offset = 0
        while offset + self.frame_size <= len(audio_data):
            yield audio_data[offset:offset + self.frame_size]
            offset += self.frame_size

    def is_speech(self, audio_data: bytes) -> bool:
        if len(audio_data) < self.frame_size:
            return False
        return self.vad.is_speech(audio_data, self.sample_rate)

    def is_speech_robust(self, audio_data: bytes) -> bool:
        if len(audio_data) < self.frame_size:
            return False
        result = self.vad.is_speech(audio_data, self.sample_rate)
        self.history.append(result)
        return sum(self.history) >= len(self.history) * 0.6

    def detect_speech(self, audio_chunk: bytes, sample_rate: int | None = None) -> bool:
        if sample_rate is not None and sample_rate != self.sample_rate:
            chunk = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32)
            ratio = self.sample_rate / sample_rate
            n_samples = int(len(chunk) * ratio)
            indices = np.linspace(0, len(chunk) - 1, n_samples)
            resampled = np.interp(indices, np.arange(len(chunk)), chunk).astype(np.int16)
            audio_chunk = resampled.tobytes()
        frames = list(self._frame_generator(audio_chunk))
        if not frames:
            return False
        speech_count = sum(1 for f in frames if self.vad.is_speech(f, self.sample_rate))
        ratio = speech_count / len(frames)
        return ratio >= 0.3
