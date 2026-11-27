"""Configuración en %APPDATA%\\Aguacate\\config.json.

- Si no existe, se crea con los valores por defecto.
- Si el JSON está mal escrito, se usan los valores por defecto y se avisa
  (el archivo no se sobrescribe hasta que guardes desde Ajustes).
- Cada valor se valida por separado: uno incorrecto se sustituye por el de
  por defecto y se avisa, sin perder el resto.
"""
import json
import os

from .blocker import clean_domains

DEFAULTS = {
    "work_minutes": 25,
    "break_minutes": 5,
    "always_on_top": False,
    "volume": 0.45,           # 0.0 – 1.0
    "beep_ms": 300,           # duración de cada nota de la alarma
    "beep_frequency": 523,    # Hz (Do5)
    "vibration": True,
    "position": None,         # [x, y] de la ventana; None = abajo a la derecha
    "blocked_domains": [
        "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
        "chess.com", "www.chess.com",
        "colonist.io", "www.colonist.io",
    ],
}

# (tipo, mínimo, máximo) para validar números
RANGES = {
    "work_minutes": (int, 1, 180),
    "break_minutes": (int, 1, 60),
    "volume": (float, 0.0, 1.0),
    "beep_ms": (int, 100, 1000),
    "beep_frequency": (int, 200, 2000),
}


def config_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(base, "Aguacate", "config.json")


def validate(data) -> tuple[dict, list[str]]:
    """Devuelve (config completa y válida, lista de avisos)."""
    cfg = json.loads(json.dumps(DEFAULTS))          # copia profunda
    problems = []
    if not isinstance(data, dict):
        return cfg, ["config.json no contiene un objeto { ... }; uso los valores por defecto."]

    for key, (typ, lo, hi) in RANGES.items():
        if key not in data:
            continue
        v = data[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            problems.append(f"«{key}»: {v!r} no es válido (de {lo} a {hi}). Uso {cfg[key]}.")
        else:
            cfg[key] = typ(v)

    for key in ("always_on_top", "vibration"):
        if key in data:
            if isinstance(data[key], bool):
                cfg[key] = data[key]
            else:
                problems.append(f"«{key}»: debe ser true o false. Uso {str(cfg[key]).lower()}.")

    pos = data.get("position")
    if (isinstance(pos, list) and len(pos) == 2
            and all(isinstance(n, int) and not isinstance(n, bool) for n in pos)):
        cfg["position"] = pos

    if "blocked_domains" in data:
        raw = data["blocked_domains"]
        if not isinstance(raw, list):
            problems.append("«blocked_domains»: debe ser una lista [\"web.com\", ...]. "
                            "Uso la lista por defecto.")
        else:
            good = clean_domains(raw)
            bad = [d for d in raw if not clean_domains([d])]
            if bad:
                problems.append("Dominios no válidos que ignoro: " + ", ".join(map(str, bad)))
            cfg["blocked_domains"] = good
    return cfg, problems


def load(path=None, fallback=None) -> tuple[dict, list[str]]:
    """fallback: config a mantener si el archivo no se puede leer o está mal escrito
    (al recargar en caliente no queremos volver a los valores por defecto)."""
    path = path or config_path()
    if not os.path.exists(path):
        cfg = json.loads(json.dumps(DEFAULTS))
        try:
            save(cfg, path)
        except OSError as e:
            return cfg, [f"No he podido crear {path}: {e}"]
        return cfg, []
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        cfg = fallback if fallback is not None else validate({})[0]
        que = "la configuración actual" if fallback is not None else "los valores por defecto"
        return cfg, [f"config.json tiene un error de formato (línea {e.lineno}, "
                     f"columna {e.colno}): {e.msg}.\nUso {que}. "
                     "Corrígelo o guarda desde Ajustes para reescribirlo."]
    except OSError as e:
        cfg = fallback if fallback is not None else validate({})[0]
        return cfg, [f"No puedo leer {path}: {e}"]
    return validate(data)


def save(cfg: dict, path=None):
    """Escritura atómica (archivo temporal + sustituir)."""
    path = path or config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
