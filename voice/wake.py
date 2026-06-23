import collections
import logging

import webrtcvad
import sounddevice as sd
import numpy as np

from core.config import settings


log = logging.getLogger("zari")


class WakeWordDetector:
    # webrtcvad qo'llaydigan sample rate'lar
    _VAD_RATES = (48000, 32000, 16000)

    def __init__(self):
        self.vad = webrtcvad.Vad(1)  # low aggressiveness (with transient skip + robust counter)
        self.frame_ms = 30

        self.sample_rate = 16000
        self.frame_samples = int(self.sample_rate * self.frame_ms / 1000)
        self.frame_size = self.frame_samples * 2

        self.energy_threshold = 5
        self.speech_frames_needed = 8    # 240ms sustained VAD
        self.startup_frames = 10         # skip first 300ms transient
        self.device = self._find_input_device()

    def _find_input_device(self) -> int | None:
        preferred = settings.audio_input_device
        devices = sd.query_devices()

        if preferred is not None:
            if 0 <= preferred < len(devices) and devices[preferred]["max_input_channels"] > 0:
                dev = devices[preferred]
                for sr in [int(dev.get("default_samplerate", 0))] + list(self._VAD_RATES):
                    if sr not in self._VAD_RATES:
                        continue
                    try:
                        sd.check_input_settings(device=preferred, samplerate=sr)
                        self.sample_rate = sr
                        self.frame_samples = int(self.sample_rate * self.frame_ms / 1000)
                        self.frame_size = self.frame_samples * 2
                        log.info("Mikrofon: [%d] %s @ %d Hz", preferred, dev["name"], sr)
                        return preferred
                    except Exception:
                        continue
                log.warning("Tanlangan qurilma [%d] sozlanmadi, auto-qidiruvga o'tiladi", preferred)
            else:
                log.warning("Tanlangan qurilma [%d] topilmadi, auto-qidiruvga o'tiladi", preferred)

        for i, dev in enumerate(devices):
            if dev["max_input_channels"] == 0:
                continue

            native_sr = int(dev.get("default_samplerate", 0)) if dev.get("default_samplerate") else 0

            rates = [native_sr] if native_sr in self._VAD_RATES else []
            rates += [r for r in self._VAD_RATES if r != native_sr]

            for sr in rates:
                try:
                    sd.check_input_settings(device=i, samplerate=sr)
                    self.sample_rate = sr
                    self.frame_samples = int(self.sample_rate * self.frame_ms / 1000)
                    self.frame_size = self.frame_samples * 2
                    log.info("Mikrofon: [%d] %s @ %d Hz", i, dev["name"], sr)
                    return i
                except Exception:
                    continue

        for i, dev in enumerate(devices):
            if dev["max_input_channels"] == 0:
                continue
            for sr in self._VAD_RATES:
                try:
                    sd.check_input_settings(device=i, samplerate=sr)
                    self.sample_rate = sr
                    self.frame_samples = int(self.sample_rate * self.frame_ms / 1000)
                    self.frame_size = self.frame_samples * 2
                    log.warning("Mikrofon (fallback): [%d] %s @ %d Hz", i, dev["name"], sr)
                    return i
                except Exception:
                    continue

        log.error("Mikrofon topilmadi!")
        return None

    def _rms(self, audio: np.ndarray) -> float:
        return float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))

    def wait_for_speech(self, timeout: float = 60.0) -> bytes | None:
        buffer = collections.deque(maxlen=50)
        speech_count = 0
        total_blocks = int(timeout * 1000 / self.frame_ms)
        frame_idx = 0
        rms_log_interval = 10

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                device=self.device,
                blocksize=self.frame_samples,
            ) as stream:
                for _ in range(total_blocks):
                    frame_idx += 1

                    audio, _ = stream.read(self.frame_samples)
                    audio_bytes = audio.tobytes()
                    buffer.append(audio.copy())

                    if frame_idx <= self.startup_frames:
                        continue

                    rms = self._rms(audio)

                    if frame_idx % rms_log_interval == 0:
                        log.debug("Frame %d: RMS=%.1f, speech_count=%d", frame_idx, rms, speech_count)

                    if rms < self.energy_threshold:
                        speech_count = 0
                        continue

                    if len(audio_bytes) >= self.frame_size and self.vad.is_speech(audio_bytes, self.sample_rate):
                        speech_count += 1
                        if speech_count >= self.speech_frames_needed:
                            log.info("Nutq aniqlandi (frames=%d, RMS=%.1f)", speech_count, rms)
                            return self._record_command(stream, list(buffer))
                    else:
                        speech_count = max(0, speech_count - 1)
        except Exception as e:
            log.error("Mikrofon xatosi: %s", e)
            return None

        return None

    def _record_command(self, stream: sd.InputStream, buffer: list[np.ndarray]) -> bytes:
        frames = buffer
        silence_frames = 0
        max_silence = int(2.0 * 1000 / self.frame_ms)
        max_frames = int(15.0 * 1000 / self.frame_ms)
        rms_threshold = self.energy_threshold * 30

        for _ in range(max_frames):
            audio, _ = stream.read(self.frame_samples)
            audio_bytes = audio.tobytes()
            frames.append(audio)

            rms = self._rms(audio)
            is_speech = False
            if rms >= rms_threshold and len(audio_bytes) >= self.frame_size:
                is_speech = self.vad.is_speech(audio_bytes, self.sample_rate)

            if not is_speech:
                silence_frames += 1
                if silence_frames >= max_silence:
                    break
            else:
                silence_frames = 0

        if not frames:
            return None

        full_audio = np.concatenate(frames)
        duration = len(full_audio) / self.sample_rate
        log.info("Yozildi: %.1f soniya", duration)
        return full_audio.tobytes()

    def close(self):
        pass
