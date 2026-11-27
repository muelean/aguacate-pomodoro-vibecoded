"""Valores por defecto. En la Fase 3 se leerán y guardarán en config.json."""

DEFAULTS = {
    "work_minutes": 25,
    "break_minutes": 5,
    "always_on_top": False,
    "volume": 0.45,           # 0.0 – 1.0
    "beep_ms": 300,           # duración de cada nota de la alarma
    "beep_frequency": 523,    # Hz (Do5)
    "vibration": True,
    "blocked_domains": [
        "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
        "chess.com", "www.chess.com",
        "colonist.io", "www.colonist.io",
    ],
}


def load() -> dict:
    return dict(DEFAULTS)
