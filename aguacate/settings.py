"""Ventana de Ajustes. Edita una copia de la configuración; si se pulsa Guardar,
devuelve la nueva (validada con config.validate)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QMessageBox, QPlainTextEdit, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from . import config


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, beeper, open_config_file, demo=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes – Aguacate Pomodoro")
        self.setMinimumWidth(380)
        self._cfg = cfg
        self._beeper = beeper
        self.result_cfg = None

        form = QFormLayout()

        self.work = QSpinBox(minimum=1, maximum=180, suffix=" min", value=cfg["work_minutes"])
        self.brk = QSpinBox(minimum=1, maximum=60, suffix=" min", value=cfg["break_minutes"])
        form.addRow("Trabajo:", self.work)
        form.addRow("Descanso:", self.brk)
        if demo:
            form.addRow("", QLabel("<i>Modo demo: el aguacate sigue usando 10 s / 5 s;\n"
                                   "estos minutos se guardan para el modo normal.</i>"))

        # Sonido
        self.volume = QSlider(Qt.Orientation.Horizontal, minimum=0, maximum=100,
                              value=round(cfg["volume"] * 100))
        self.vol_label = QLabel()
        self.volume.valueChanged.connect(lambda v: self.vol_label.setText(f"{v} %"))
        self.vol_label.setText(f"{self.volume.value()} %")
        self.vol_label.setMinimumWidth(40)
        vol_row = QHBoxLayout()
        vol_row.addWidget(self.volume)
        vol_row.addWidget(self.vol_label)
        form.addRow("Volumen:", _wrap(vol_row))

        self.note_ms = QSpinBox(minimum=100, maximum=1000, singleStep=50, suffix=" ms",
                                value=cfg["beep_ms"])
        form.addRow("Duración de cada nota:", self.note_ms)
        self.freq = QSpinBox(minimum=200, maximum=2000, singleStep=20, suffix=" Hz",
                             value=cfg["beep_frequency"])
        self.freq.setToolTip("Más bajo = más grave. 523 Hz es un Do.")
        form.addRow("Tono:", self.freq)
        test = QPushButton("▶ Probar sonido")
        test.clicked.connect(self._preview)
        form.addRow("", test)

        self.vibration = QCheckBox("Vibrar al acabar el trabajo", checked=cfg["vibration"])
        self.on_top = QCheckBox("Siempre encima de otras ventanas", checked=cfg["always_on_top"])
        form.addRow("", self.vibration)
        form.addRow("", self.on_top)

        # Webs
        self.domains = QPlainTextEdit("\n".join(cfg["blocked_domains"]))
        self.domains.setMinimumHeight(140)
        domains_help = QLabel("Una por línea, sin http:// ni barras. Cada subdominio va "
                              "aparte\n(youtube.com no bloquea music.youtube.com).")
        domains_help.setStyleSheet("color: gray")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        open_json = QPushButton("Abrir config.json")
        open_json.clicked.connect(open_config_file)
        buttons.addButton(open_json, QDialogButtonBox.ButtonRole.ResetRole)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(QLabel("<b>Webs bloqueadas durante el trabajo</b>"))
        lay.addWidget(self.domains)
        lay.addWidget(domains_help)
        lay.addWidget(buttons)

    def _preview(self):
        self._beeper.preview(self.freq.value(), self.note_ms.value(),
                             self.volume.value() / 100)

    def _save(self):
        lines = [l.strip() for l in self.domains.toPlainText().splitlines() if l.strip()]
        data = dict(self._cfg)
        data.update({
            "work_minutes": self.work.value(),
            "break_minutes": self.brk.value(),
            "volume": self.volume.value() / 100,
            "beep_ms": self.note_ms.value(),
            "beep_frequency": self.freq.value(),
            "vibration": self.vibration.isChecked(),
            "always_on_top": self.on_top.isChecked(),
            "blocked_domains": lines,
        })
        cfg, problems = config.validate(data)
        if problems:
            ans = QMessageBox.question(
                self, "Ajustes", "\n".join(problems) + "\n\n¿Guardar igualmente sin ellos?")
            if ans != QMessageBox.StandardButton.Yes:
                return
        self.result_cfg = cfg
        self.accept()


def _wrap(layout) -> QWidget:
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w
