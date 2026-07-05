import collections
import struct

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

    def detect_speech(self, audio_chunk: bytes) -> bool:
        frames = list(self._frame_generator(audio_chunk))
        if not frames:
            return False
        speech_count = sum(1 for f in frames if self.vad.is_speech(f, self.sample_rate))
        ratio = speech_count / len(frames)
        return ratio >= 0.3
