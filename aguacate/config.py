"""Valores por defecto. En la Fase 3 se leerán y guardarán en config.json."""

DEFAULTS = {
    "work_minutes": 25,
    "break_minutes": 5,
    "always_on_top": False,
    "volume": 0.6,            # 0.0 – 1.0
    "beep_ms": 250,           # duración de cada pitido
    "beep_frequency": 880,    # Hz
    "vibration": True,
    "blocked_domains": [
        "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
        "chess.com", "www.chess.com",
        "colonist.io", "www.colonist.io",
    ],
}


def load() -> dict:
    return dict(DEFAULTS)
