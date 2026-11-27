"""Aguacate Pomodoro – punto de entrada.

    python main.py          # normal (25 / 5 minutos)
    python main.py --demo   # pruebas rápidas: 10 s trabajo / 5 s descanso
"""
import sys

from PySide6.QtWidgets import QApplication

from aguacate import config
from aguacate.window import AvocadoWindow


def main() -> int:
    demo = "--demo" in sys.argv
    cfg = config.load()
    if demo:
        cfg["work_minutes"], cfg["break_minutes"] = 10, 5

    app = QApplication(sys.argv)
    app.setApplicationName("Aguacate Pomodoro")
    win = AvocadoWindow(cfg, demo=demo)
    win.show()
    win.place_bottom_right()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
