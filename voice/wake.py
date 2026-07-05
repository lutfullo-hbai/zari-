import collections
import logging
import threading

import webrtcvad
import sounddevice as sd
import numpy as np

from core.config import settings


log = logging.getLogger("zari")

try:
    from openwakeword import Model
    HAS_OPENWAKEWORD = True
except ImportError:
    HAS_OPENWAKEWORD = False


class WakeWordDetector:
    _VAD_RATES = (48000, 32000, 16000)

    def __init__(self):
        self.vad = webrtcvad.Vad(1)
        self.frame_ms = 30
        self.sample_rate = 16000
        self.frame_samples = int(self.sample_rate * self.frame_ms / 1000)
        self.frame_size = self.frame_samples * 2
        self.energy_threshold = 5
        self.speech_frames_needed = 8
        self.startup_frames = 10
        self.device = self._find_input_device()

        self._oww_model = None
        self._wake_threshold = 0.5
        if HAS_OPENWAKEWORD:
            try:
                model_paths = getattr(settings, "wake_word_models", None)
                if model_paths:
                    self._oww_model = Model(wakeword_models=model_paths)
                else:
                    self._oww_model = Model(wakeword_models=["hey_jarvis"])
                self._wake_threshold = getattr(settings, "wake_threshold", 0.5)
                log.info(
                    "OpenWakeWord: loaded (threshold=%.2f)",
                    self._wake_threshold,
                )
            except Exception as e:
                log.warning("OpenWakeWord init failed: %s", e)

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

    def wait_for_speech(
        self, timeout: float = 60.0, stop_event: threading.Event | None = None
    ) -> bytes | None:
        if self._oww_model is not None:
            return self._wait_for_wakeword(timeout, stop_event)
        return self._wait_for_vad(timeout, stop_event)

    def _wait_for_wakeword(
        self, timeout: float, stop_event: threading.Event | None
    ) -> bytes | None:
        buffer = collections.deque(maxlen=50)
        total_blocks = int(timeout * 1000 / self.frame_ms)
        frame_idx = 0

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                device=self.device,
                blocksize=self.frame_samples,
            ) as stream:
                for _ in range(total_blocks):
                    if stop_event and stop_event.is_set():
                        return None

                    frame_idx += 1
                    audio, _ = stream.read(self.frame_samples)
                    audio_bytes = audio.tobytes()
                    buffer.append(audio.copy())

                    if frame_idx <= self.startup_frames:
                        continue

                    prediction = self._oww_model.predict(audio_bytes)
                    wake_score = prediction.get("hey_jarvis", 0)

                    if wake_score > self._wake_threshold:
                        log.info(
                            "Wake word detected (score=%.3f, threshold=%.2f)",
                            wake_score,
                            self._wake_threshold,
                        )
                        return self._record_command(stream, list(buffer))
        except Exception as e:
            log.error("OpenWakeWord error: %s", e)
        return None

    def _wait_for_vad(
        self, timeout: float, stop_event: threading.Event | None
    ) -> bytes | None:
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
                    if stop_event and stop_event.is_set():
                        return None

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
                            log.info("Nutq aniqlandi (VAD fallback, frames=%d, RMS=%.1f)", speech_count, rms)
                            return self._record_command(stream, list(buffer))
                    else:
                        speech_count = max(0, speech_count - 1)
        except Exception as e:
            log.error("VAD error: %s", e)
        return None

    def _record_command(self, stream: sd.InputStream, buffer: list[np.ndarray]) -> bytes:
        frames = buffer
        silence_frames = 0
        max_silence = int(2.0 * 1000 / self.frame_ms)
        max_frames = int(15.0 * 1000 / self.frame_ms)

        noise_floor = max([self._rms(f) for f in list(buffer)[:3]]) or 1
        rms_threshold = max(noise_floor * 3, self.energy_threshold * 50)

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
