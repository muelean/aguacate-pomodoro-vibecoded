"""Sonidos generados por código (onda senoidal PCM de 16 bits), sin archivos.

- alarm: "bip-bip" que se repite hasta llamar a stop().
- soft_chime: dos notas suaves descendentes, una sola vez (fin del descanso).
"""
import math
from array import array

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QTimer
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QMediaDevices
from PySide6.QtWidgets import QApplication

RATE = 44100


def tone(freq: float, ms: int, volume: float, fade_ms: int = 8) -> array:
    """Muestras de una nota con fundido de entrada/salida (evita chasquidos)."""
    n = int(RATE * ms / 1000)
    fade = max(1, int(RATE * fade_ms / 1000))
    amp = 32767 * max(0.0, min(1.0, volume))
    out = array("h")
    for i in range(n):
        env = min(1.0, i / fade, (n - 1 - i) / fade)
        out.append(int(amp * env * math.sin(2 * math.pi * freq * i / RATE)))
    return out


def silence(ms: int) -> array:
    return array("h", bytes(2 * int(RATE * ms / 1000)))


def alarm_pattern(freq: float, beep_ms: int, volume: float) -> array:
    """bip – pausa – bip – pausa larga."""
    pcm = tone(freq, beep_ms, volume)
    pcm += silence(beep_ms // 2)
    pcm += tone(freq, beep_ms, volume)
    pcm += silence(700)
    return pcm


def chime_pattern(volume: float) -> array:
    v = volume * 0.5
    pcm = tone(660, 180, v, fade_ms=30)
    pcm += tone(523, 320, v, fade_ms=60)
    return pcm


class Beeper(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QAudioFormat()
        fmt.setSampleRate(RATE)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._format = fmt
        self._sink = None
        self._buffer = None
        self._data = None
        self._alarm_pcm = None
        self._loop = QTimer(self)
        self._loop.timeout.connect(self._play_alarm_once)
        self.volume = 0.6
        self.beep_ms = 250
        self.frequency = 880

    # ---- API ----------------------------------------------------------------
    def start_alarm(self):
        self._alarm_pcm = alarm_pattern(self.frequency, self.beep_ms, self.volume)
        cycle_ms = int(len(self._alarm_pcm) * 1000 / RATE)
        self._play_alarm_once()
        self._loop.start(cycle_ms)

    def stop(self):
        self._loop.stop()
        if self._sink is not None:
            self._sink.stop()

    def soft_chime(self):
        self.stop()
        self._play(chime_pattern(self.volume))

    def is_alarm_active(self) -> bool:
        return self._loop.isActive()

    # ---- interno ------------------------------------------------------------
    def _play_alarm_once(self):
        self._play(self._alarm_pcm)

    def _play(self, pcm: array):
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull():
            QApplication.beep()      # sin tarjeta de sonido: pitido del sistema
            return
        if self._sink is not None:
            self._sink.stop()
        self._sink = QAudioSink(device, self._format, self)
        self._data = QByteArray(pcm.tobytes())
        self._buffer = QBuffer(self)
        self._buffer.setData(self._data)
        self._buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self._sink.start(self._buffer)
        if self._sink.error() != QAudio.Error.NoError:
            QApplication.beep()
