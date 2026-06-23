import webrtcvad
import collections
import struct


class VAD:
    def __init__(self, aggressiveness: int = 2):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = 16000
        self.frame_ms = 30
        self.frame_size = int(self.sample_rate * self.frame_ms / 1000) * 2
        self.history = collections.deque(maxlen=10)
        self.speech_frames = 0
        self.silence_frames = 0

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
