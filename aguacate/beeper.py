"""Sonidos generados por código, sin archivos incluidos en el proyecto.

- alarm: "ding-dong" suave (dos notas con caída tipo marimba) que se repite
  hasta llamar a stop().
- soft_chime: las mismas notas al revés y más bajas, una sola vez (fin del descanso).

Al arrancar se generan las muestras y se guardan como WAV en la carpeta temporal.
En Windows se reproducen con winsound (API PlaySound), que repite el bucle sin
abrir y cerrar la salida de audio en cada pitido. En otros sistemas (solo para
desarrollo) se usa QSoundEffect.
"""
import math
import os
import sys
import tempfile
import wave
from array import array

from PySide6.QtCore import QObject

RATE = 44100
IS_WINDOWS = sys.platform == "win32"


# ---- síntesis -----------------------------------------------------------------
def tone(freq: float, ms: int, volume: float, fade_ms: int = 8) -> array:
    """Nota plana con fundido de entrada/salida (evita chasquidos)."""
    n = int(RATE * ms / 1000)
    fade = max(1, int(RATE * fade_ms / 1000))
    amp = 32767 * max(0.0, min(1.0, volume))
    out = array("h")
    for i in range(n):
        env = min(1.0, i / fade, (n - 1 - i) / fade)
        out.append(int(amp * env * math.sin(2 * math.pi * freq * i / RATE)))
    return out


def soft_note(freq: float, ms: int, volume: float) -> array:
    """Nota suave: ataque de 12 ms, caída exponencial y un poco de 2º armónico."""
    n = int(RATE * ms / 1000)
    attack = int(RATE * 0.012)
    amp = 32767 * max(0.0, min(1.0, volume)) / 1.25    # 1.25 = suma de armónicos
    out = array("h")
    for i in range(n):
        t = i / RATE
        env = (i / attack) if i < attack else math.exp(-5.0 * (i - attack) / n)
        env *= min(1.0, (n - 1 - i) / (RATE * 0.005))   # cierre sin chasquido
        s = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t)
        out.append(int(amp * env * s))
    return out


def silence(ms: int) -> array:
    return array("h", bytes(2 * int(RATE * ms / 1000)))


def alarm_pattern(freq: float, note_ms: int, volume: float) -> array:
    """ding (freq) – dong (una tercera mayor más aguda) – silencio."""
    pcm = soft_note(freq, note_ms, volume)
    pcm += soft_note(freq * 1.26, int(note_ms * 1.6), volume)
    pcm += silence(900)
    return pcm


def chime_pattern(freq: float, note_ms: int, volume: float) -> array:
    v = volume * 0.6
    return soft_note(freq * 1.26, note_ms, v) + soft_note(freq, int(note_ms * 1.8), v)


def write_wav(path: str, pcm: array):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


# ---- reproducción -------------------------------------------------------------
class Beeper(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.volume = 0.45
        self.beep_ms = 300
        self.frequency = 523
        self._dir = os.path.join(tempfile.gettempdir(), "aguacate")
        os.makedirs(self._dir, exist_ok=True)
        self._alarm_wav = os.path.join(self._dir, "alarma.wav")
        self._chime_wav = os.path.join(self._dir, "descanso.wav")
        self._alarm_active = False
        self._effects = {}       # solo fuera de Windows

    def prepare(self):
        """Genera los WAV con los ajustes actuales. Llamar tras cambiar volumen, etc."""
        write_wav(self._alarm_wav, alarm_pattern(self.frequency, self.beep_ms, self.volume))
        write_wav(self._chime_wav, chime_pattern(self.frequency, self.beep_ms, self.volume))
        self._effects.clear()

    def start_alarm(self):
        self._alarm_active = True
        self._play(self._alarm_wav, loop=True)

    def soft_chime(self):
        self.stop()
        self._play(self._chime_wav, loop=False)

    def stop(self):
        self._alarm_active = False
        if IS_WINDOWS:
            import winsound
            winsound.PlaySound(None, 0)
        else:
            for e in self._effects.values():
                e.stop()

    def is_alarm_active(self) -> bool:
        return self._alarm_active

    def _play(self, path: str, loop: bool):
        if not os.path.exists(path):
            self.prepare()
        if IS_WINDOWS:
            import winsound
            flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
            if loop:
                flags |= winsound.SND_LOOP
            winsound.PlaySound(path, flags)
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QSoundEffect
        effect = self._effects.get(path)
        if effect is None:
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(path))
            self._effects[path] = effect
        effect.setLoopCount(QSoundEffect.Loop.Infinite.value if loop else 1)
        effect.play()
