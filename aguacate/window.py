"""Ventana del aguacate: sin bordes, transparente, arrastrable, con menú."""
import random

from PySide6.QtCore import QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QPainter
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QWidget

from . import painter
from .beeper import Beeper
from .timer import (
    ALARM, BREAK, PAUSED, READY, RUNNING,
    EV_BREAK_DONE, EV_WORK_DONE, Pomodoro,
)

DRAG_THRESHOLD = 5          # px: menos que esto es un clic, no un arrastre
WORK_OPTIONS = [15, 20, 25, 30, 45, 50, 60]
BREAK_OPTIONS = [3, 5, 10, 15]


class AvocadoWindow(QWidget):
    def __init__(self, cfg: dict, demo: bool = False):
        super().__init__()
        self.cfg = cfg
        self.demo = demo
        unit = 1 if demo else 60    # en modo demo los "minutos" son segundos
        self._unit = unit
        self.pomo = Pomodoro(cfg["work_minutes"] * unit, cfg["break_minutes"] * unit)

        self.beeper = Beeper(self)
        self.beeper.volume = cfg["volume"]
        self.beeper.beep_ms = cfg["beep_ms"]
        self.beeper.frequency = cfg["beep_frequency"]

        self.setWindowTitle("Aguacate Pomodoro")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._apply_flags(cfg["always_on_top"])
        self.resize(220, 300)

        # Refresco del contador (5 veces por segundo)
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(200)

        # Vibración
        self._shake = QTimer(self)
        self._shake.timeout.connect(self._shake_step)
        self._shake_t = 0
        self._shake_base = None

        self._press_global = None
        self._press_win = None
        self._dragging = False

    # ---- ventana -------------------------------------------------------------
    def _apply_flags(self, on_top: bool):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        visible = self.isVisible()
        self.setWindowFlags(flags)
        if visible:
            self.show()     # cambiar flags oculta la ventana; hay que volver a mostrarla

    def place_bottom_right(self):
        screen = self.screen().availableGeometry()
        self.move(screen.right() - self.width() - 40, screen.bottom() - self.height() - 40)

    # ---- dibujo --------------------------------------------------------------
    def _status_text(self) -> str:
        phase = "DESCANSO" if self.pomo.phase == BREAK else "TRABAJO"
        s = self.pomo.status
        if s == READY:
            return f"{phase} · clic para empezar"
        if s == PAUSED:
            return f"{phase} · en pausa"
        if s == ALARM:
            return "¡FIN! · clic para descansar"
        return phase

    def paintEvent(self, _event):
        p = QPainter(self)
        painter.draw(
            p, painter.Geometry(self.width(), self.height()),
            remaining=self.pomo.remaining(),
            fraction=self.pomo.fraction_left(),
            is_break=self.pomo.phase == BREAK,
            status_text=self._status_text(),
        )
        p.end()

    def _hit_avocado(self, pos: QPointF) -> bool:
        g = painter.Geometry(self.width(), self.height())
        return painter.skin_path(g.avocado_rect).contains(pos)

    # ---- temporizador --------------------------------------------------------
    def _on_tick(self):
        ev = self.pomo.tick()
        if ev == EV_WORK_DONE:
            self.beeper.start_alarm()
            if self.cfg["vibration"]:
                self._start_shake()
        elif ev == EV_BREAK_DONE:
            self.beeper.soft_chime()
        self.update()

    def _on_avocado_click(self):
        if self.pomo.status == ALARM:
            self.beeper.stop()
            self._stop_shake()
        self.pomo.click()
        self.update()

    # ---- vibración -----------------------------------------------------------
    def _start_shake(self):
        self._shake_base = self.pos()
        self._shake_t = 0
        self._shake.start(30)

    def _stop_shake(self):
        if self._shake.isActive():
            self._shake.stop()
            if self._shake_base is not None:
                self.move(self._shake_base)

    def _shake_step(self):
        # Ciclo de 1 s: 400 ms temblando + 600 ms quieto
        self._shake_t = (self._shake_t + 30) % 1000
        if self._shake_t < 400:
            dx, dy = random.randint(-4, 4), random.randint(-2, 2)
        else:
            dx = dy = 0
        self.move(self._shake_base + QPoint(dx, dy))

    # ---- ratón ---------------------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._hit_avocado(e.position()):
            self._press_global = e.globalPosition().toPoint()
            self._press_win = self._shake_base if self._shake.isActive() else self.pos()
            self._dragging = False

    def mouseMoveEvent(self, e):
        if self._press_global is None:
            return
        delta = e.globalPosition().toPoint() - self._press_global
        if not self._dragging and delta.manhattanLength() > DRAG_THRESHOLD:
            self._dragging = True
        if self._dragging:
            new_pos = self._press_win + delta
            if self._shake.isActive():
                self._shake_base = new_pos
            else:
                self.move(new_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._press_global is not None:
            if not self._dragging:
                self._on_avocado_click()
            self._press_global = None
            self._dragging = False

    # ---- menú contextual ----------------------------------------------------
    def contextMenuEvent(self, e):
        m = QMenu(self)
        u = "s" if self.demo else "min"

        m.addMenu(self._minutes_menu(m, f"Trabajo ({u})", WORK_OPTIONS,
                                     self.cfg["work_minutes"], self._set_work))
        m.addMenu(self._minutes_menu(m, f"Descanso ({u})", BREAK_OPTIONS,
                                     self.cfg["break_minutes"], self._set_break))
        m.addSeparator()

        reset = m.addAction("Reiniciar")
        reset.triggered.connect(self._reset)

        top = m.addAction("Siempre encima")
        top.setCheckable(True)
        top.setChecked(self.cfg["always_on_top"])
        top.toggled.connect(self._toggle_on_top)

        settings = m.addAction("Ajustes… (Fase 3)")
        settings.setEnabled(False)

        m.addSeparator()
        quit_ = m.addAction("Salir")
        quit_.triggered.connect(self.close)
        m.exec(e.globalPos())

    def _minutes_menu(self, parent, title, options, current, setter):
        sub = QMenu(title, parent)
        group = QActionGroup(sub)
        values = sorted(set(options) | {current})
        for v in values:
            a = QAction(str(v), sub, checkable=True, checked=(v == current))
            a.triggered.connect(lambda _=False, v=v: setter(v))
            group.addAction(a)
            sub.addAction(a)
        sub.addSeparator()
        other = sub.addAction("Otro…")
        other.triggered.connect(lambda: self._ask_minutes(title, current, setter))
        return sub

    def _ask_minutes(self, title, current, setter):
        v, ok = QInputDialog.getInt(self, "Aguacate", title, current, 1, 180)
        if ok:
            setter(v)

    def _set_work(self, v):
        self.cfg["work_minutes"] = v
        self.pomo.set_durations(work_seconds=v * self._unit)
        self._note_if_pending(self.pomo.phase != BREAK)
        self.update()

    def _set_break(self, v):
        self.cfg["break_minutes"] = v
        self.pomo.set_durations(break_seconds=v * self._unit)
        self._note_if_pending(self.pomo.phase == BREAK)
        self.update()

    def _note_if_pending(self, same_phase: bool):
        if same_phase and self.pomo.status in (RUNNING, PAUSED):
            QMessageBox.information(self, "Aguacate",
                                    "El cambio se aplicará en la próxima vuelta.\n"
                                    "Usa «Reiniciar» si lo quieres ya.")

    def _reset(self):
        self.beeper.stop()
        self._stop_shake()
        self.pomo.reset()
        self.update()

    def _toggle_on_top(self, on):
        self.cfg["always_on_top"] = on
        pos = self.pos()
        self._apply_flags(on)
        self.move(pos)

    def closeEvent(self, e):
        self.beeper.stop()
        self._stop_shake()
        super().closeEvent(e)
