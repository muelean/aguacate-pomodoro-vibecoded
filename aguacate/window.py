"""Ventana del aguacate: sin bordes, transparente, arrastrable, con menú."""
import os
import random
import subprocess
import sys
import time

from PySide6.QtCore import QFileSystemWatcher, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QPainter
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox, QWidget

from . import config, painter
from .beeper import Beeper
from .blocker import HostsError
from .timer import (
    ALARM, BREAK, PAUSED, READY, RUNNING,
    EV_BREAK_DONE, EV_WORK_DONE, Pomodoro,
)

DRAG_THRESHOLD = 5          # px: menos que esto es un clic, no un arrastre
WORK_OPTIONS = [15, 20, 25, 30, 45, 50, 60]
BREAK_OPTIONS = [3, 5, 10, 15]
DEMO_SECONDS = (10, 5)      # trabajo / descanso en modo demo


class AvocadoWindow(QWidget):
    def __init__(self, cfg: dict, demo: bool = False, hosts=None, cfg_path=None):
        super().__init__()
        self.cfg = cfg
        self.cfg_path = cfg_path or config.config_path()
        self._save_error_shown = False
        self.hosts = hosts          # HostsFile o None si el bloqueo está desactivado
        self._blocked = False
        self._block_error = None
        self.demo = demo
        # En modo demo los tiempos son segundos y NO se guardan en config.json
        self._demo = list(DEMO_SECONDS)
        self.pomo = Pomodoro(*self._durations())

        self.beeper = Beeper(self)
        self._apply_sound(cfg)

        self.setWindowTitle("Aguacate Pomodoro")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._apply_flags(cfg["always_on_top"])
        self.resize(224, 296)

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
        self._temp_on_top = False   # encima temporalmente porque ha acabado un tiempo

        # Recargar config.json si se edita a mano (p. ej. con el Bloc de notas)
        self._watcher = QFileSystemWatcher(self)
        self._watch_config()
        self._watcher.fileChanged.connect(lambda _: QTimer.singleShot(300, self.reload_config))
        self._watcher.directoryChanged.connect(lambda _: self._watch_config())

        self.setWindowIcon(painter.app_icon())

    # ---- configuración -------------------------------------------------------
    def _durations(self):
        if self.demo:
            return self._demo[0], self._demo[1]
        return self.cfg["work_minutes"] * 60, self.cfg["break_minutes"] * 60

    def _apply_sound(self, cfg):
        self.beeper.volume = cfg["volume"]
        self.beeper.beep_ms = cfg["beep_ms"]
        self.beeper.frequency = cfg["beep_frequency"]
        self.beeper.prepare()

    def _watch_config(self):
        folder = os.path.dirname(self.cfg_path)
        if os.path.isdir(folder) and folder not in self._watcher.directories():
            self._watcher.addPath(folder)
        if os.path.exists(self.cfg_path) and self.cfg_path not in self._watcher.files():
            self._watcher.addPath(self.cfg_path)
            QTimer.singleShot(300, self.reload_config)   # el Bloc de notas reemplaza el archivo

    def save_config(self):
        try:
            config.save(self.cfg, self.cfg_path)
        except OSError as e:
            if not self._save_error_shown:
                self._save_error_shown = True
                QMessageBox.warning(self, "Aguacate", f"No puedo guardar la configuración:\n{e}")

    def reload_config(self):
        new, problems = config.load(self.cfg_path, fallback=self.cfg)
        if problems:
            QMessageBox.warning(self, "Aguacate", "\n\n".join(problems))
        if new != self.cfg:
            self.apply_config(new)

    def apply_config(self, new: dict):
        """Aplica una configuración nueva sin reiniciar la app."""
        old, self.cfg = self.cfg, new
        if not self.demo:
            self.pomo.set_durations(*self._durations())
        if any(old[k] != new[k] for k in ("volume", "beep_ms", "beep_frequency")):
            self._apply_sound(new)
        if old["always_on_top"] != new["always_on_top"]:
            self._temp_on_top = False
            self._set_on_top_keep_pos(new["always_on_top"])
        if old["blocked_domains"] != new["blocked_domains"] and self._blocked:
            try:
                self.hosts.block(new["blocked_domains"])     # sustituye el bloque
            except HostsError as e:
                QMessageBox.warning(self, "Aguacate", str(e))
        self.update()

    def open_config_file(self):
        self.save_config()
        if sys.platform == "win32":
            subprocess.Popen(["notepad.exe", self.cfg_path])
        else:
            QMessageBox.information(self, "Aguacate", self.cfg_path)

    def _open_settings(self):
        from .settings import SettingsDialog
        dlg = SettingsDialog(self.cfg, self.beeper, self.open_config_file, demo=self.demo,
                             parent=self)
        if dlg.exec() and dlg.result_cfg is not None:
            new = dlg.result_cfg
            new["position"] = self.cfg.get("position")
            self.apply_config(new)
            self.save_config()

    def restore_position(self):
        pos = self.cfg.get("position")
        if pos:
            p = QPoint(*pos)
            center = p + QPoint(self.width() // 2, self.height() // 2)
            if QGuiApplication.screenAt(center) is not None:   # sigue en una pantalla
                self.move(p)
                return
        self.place_bottom_right()

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
    def _icon(self):
        if self._blocked:
            return "lock"
        if self.hosts is None and self.pomo.is_work_running():
            return "unlock"          # trabajando, pero sin permisos no se bloquea nada
        return {READY: "play", PAUSED: "pause"}.get(self.pomo.status)

    def paintEvent(self, _event):
        # En alarma el contador parpadea (medio segundo visible, medio oculto)
        blink_off = self.pomo.status == ALARM and (time.monotonic() % 1.0) > 0.5
        p = QPainter(self)
        painter.draw(
            p, painter.Geometry(self.width(), self.height()),
            remaining=self.pomo.remaining(),
            fraction=self.pomo.fraction_left(),
            is_break=self.pomo.phase == BREAK,
            icon=self._icon(),
            show_time=not blink_off,
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
            self._bring_to_front()
            if self.cfg["vibration"]:
                self._start_shake()
        elif ev == EV_BREAK_DONE:
            self.beeper.soft_chime()
            self._bring_to_front()
        if ev:
            self._sync_block()
        self.update()

    def _on_avocado_click(self):
        if self.pomo.status == ALARM:
            self.beeper.stop()
            self._stop_shake()
        self._end_temp_on_top()
        self.pomo.click()
        self._sync_block()
        self.update()

    def _bring_to_front(self):
        """Al acabar un tiempo, pone el aguacate por encima de todas las ventanas
        hasta el siguiente clic (aunque «Siempre encima» esté desactivado)."""
        if self.isMinimized():
            self.showNormal()
        if not self.cfg["always_on_top"] and not self._temp_on_top:
            self._temp_on_top = True
            self._set_on_top_keep_pos(True)
        self.raise_()
        self.activateWindow()
        QApplication.alert(self)

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
            else:
                pos = self._shake_base if self._shake.isActive() else self.pos()
                self.cfg["position"] = [pos.x(), pos.y()]
                self.save_config()
            self._press_global = None
            self._dragging = False

    # ---- menú contextual ----------------------------------------------------
    def contextMenuEvent(self, e):
        m = QMenu(self)
        u = "s, demo" if self.demo else "min"
        work, brk = (self._demo if self.demo
                     else (self.cfg["work_minutes"], self.cfg["break_minutes"]))

        m.addMenu(self._minutes_menu(m, f"Trabajo ({u})", WORK_OPTIONS, work, self._set_work))
        m.addMenu(self._minutes_menu(m, f"Descanso ({u})", BREAK_OPTIONS, brk, self._set_break))
        m.addSeparator()

        status = m.addAction(self._block_status())
        status.setEnabled(False)
        m.addSeparator()

        reset = m.addAction("Reiniciar")
        reset.triggered.connect(self._reset)

        top = m.addAction("Siempre encima")
        top.setCheckable(True)
        top.setChecked(self.cfg["always_on_top"])
        top.toggled.connect(self._toggle_on_top)

        settings = m.addAction("Ajustes…")
        settings.triggered.connect(self._open_settings)
        open_json = m.addAction("Abrir config.json")
        open_json.triggered.connect(self.open_config_file)

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
        if self.demo:
            self._demo[0] = v
        else:
            self.cfg["work_minutes"] = v
            self.save_config()
        self.pomo.set_durations(work_seconds=self._durations()[0])
        self._note_if_pending(self.pomo.phase != BREAK)
        self.update()

    def _set_break(self, v):
        if self.demo:
            self._demo[1] = v
        else:
            self.cfg["break_minutes"] = v
            self.save_config()
        self.pomo.set_durations(break_seconds=self._durations()[1])
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
        self._end_temp_on_top()
        self.pomo.reset()
        self._sync_block()
        self.update()

    def _end_temp_on_top(self):
        if self._temp_on_top:
            self._temp_on_top = False
            self._set_on_top_keep_pos(self.cfg["always_on_top"])

    def _set_on_top_keep_pos(self, on):
        pos = self._shake_base if self._shake.isActive() else self.pos()
        self._apply_flags(on)
        self.move(pos)

    def _toggle_on_top(self, on):
        self.cfg["always_on_top"] = on
        self._temp_on_top = False
        self._set_on_top_keep_pos(on)
        self.save_config()

    # ---- bloqueo de webs -----------------------------------------------------
    def _sync_block(self):
        """Bloquea solo mientras el trabajo está en marcha; si no, desbloquea."""
        if self.hosts is None:
            return
        want = self.pomo.is_work_running()
        if want == self._blocked:
            return
        try:
            if want:
                self.hosts.block(self.cfg["blocked_domains"])
            else:
                self.hosts.unblock()
            self._blocked = want
        except HostsError as e:
            self._block_error = str(e)
            self.release_block()
            self.hosts = None
            QMessageBox.warning(self, "Aguacate",
                                f"{e}\n\nDesactivo el bloqueo; el temporizador sigue.")

    def _block_status(self) -> str:
        if self._block_error:
            return "Bloqueo de webs: error (ver aviso)"
        if self.hosts is None:
            return "Bloqueo de webs: desactivado"
        return "Bloqueo de webs: ACTIVO" if self._blocked else "Bloqueo de webs: en espera"

    def release_block(self):
        """Quita el bloqueo. Se llama al salir por cualquier vía; nunca lanza errores."""
        if self.hosts is None:
            return
        try:
            self.hosts.unblock()
        except Exception:
            pass
        self._blocked = False

    def closeEvent(self, e):
        self.beeper.stop()
        self._stop_shake()
        self.release_block()
        super().closeEvent(e)
