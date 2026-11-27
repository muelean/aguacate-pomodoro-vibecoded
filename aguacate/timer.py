"""Máquina de estados del pomodoro. No depende de Qt para poder testearla.

Fases:   "work" | "break"
Estados: "ready"   -> esperando un clic para empezar
         "running" -> contando
         "paused"  -> pausado
         "alarm"   -> el trabajo terminó; suena hasta que se haga clic
"""
import time

WORK, BREAK = "work", "break"
READY, RUNNING, PAUSED, ALARM = "ready", "running", "paused", "alarm"

# Eventos que devuelve tick()/click() para que la ventana reaccione
EV_WORK_DONE = "work_done"      # empezar alarma
EV_BREAK_DONE = "break_done"    # sonido suave
EV_ALARM_STOPPED = "alarm_stopped"


class Pomodoro:
    def __init__(self, work_seconds=25 * 60, break_seconds=5 * 60, clock=time.monotonic):
        self.clock = clock
        self.work_seconds = float(work_seconds)
        self.break_seconds = float(break_seconds)
        self.phase = WORK
        self.status = READY
        self._remaining = self.work_seconds   # válido cuando no está en marcha
        self._end_time = None                 # válido cuando está en marcha

    # ---- consultas -------------------------------------------------------
    def duration(self) -> float:
        return self.work_seconds if self.phase == WORK else self.break_seconds

    def remaining(self) -> float:
        if self.status == RUNNING:
            return max(0.0, self._end_time - self.clock())
        return max(0.0, self._remaining)

    def fraction_left(self) -> float:
        d = self.duration()
        return 0.0 if d <= 0 else min(1.0, self.remaining() / d)

    def is_work_running(self) -> bool:
        """True solo cuando se deben bloquear webs (Fase 2)."""
        return self.phase == WORK and self.status == RUNNING

    # ---- acciones --------------------------------------------------------
    def click(self):
        """Clic en el aguacate. Devuelve un evento o None."""
        if self.status in (READY, PAUSED):
            self._start()
        elif self.status == RUNNING:
            self._remaining = self.remaining()
            self._end_time = None
            self.status = PAUSED
        elif self.status == ALARM:
            self.phase = BREAK
            self._remaining = self.break_seconds
            self._start()
            return EV_ALARM_STOPPED
        return None

    def tick(self):
        """Llamar periódicamente. Devuelve un evento si una fase termina."""
        if self.status != RUNNING or self.remaining() > 0:
            return None
        self._end_time = None
        self._remaining = 0.0
        if self.phase == WORK:
            self.status = ALARM
            return EV_WORK_DONE
        self.phase = WORK
        self.status = READY
        self._remaining = self.work_seconds
        return EV_BREAK_DONE

    def reset(self):
        self.phase = WORK
        self.status = READY
        self._end_time = None
        self._remaining = self.work_seconds

    def set_durations(self, work_seconds=None, break_seconds=None):
        """Cambia duraciones. Si la fase afectada está esperando, se aplica ya;
        si está en marcha o pausada, se aplicará la próxima vez."""
        if work_seconds is not None:
            self.work_seconds = float(work_seconds)
        if break_seconds is not None:
            self.break_seconds = float(break_seconds)
        if self.status == READY:
            self._remaining = self.duration()

    def _start(self):
        self._end_time = self.clock() + self._remaining
        self.status = RUNNING
