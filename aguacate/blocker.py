"""Bloqueo de webs editando el archivo hosts.

Las entradas de la app van siempre entre dos marcas:

    # AGUACATE-START
    127.0.0.1 youtube.com
    ::1 youtube.com
    ...
    # AGUACATE-END

Todo lo que hay fuera de las marcas no se toca nunca. Reglas de seguridad:
- Copia de seguridad del hosts original antes del primer cambio (solo una vez).
- Escritura atómica: se escribe un archivo temporal y se sustituye el hosts de golpe,
  así nunca queda a medias.
- Si las marcas están rotas (falta una, están desordenadas o repetidas), no se toca
  nada y se lanza HostsCorrupt para avisar al usuario.
- Se respetan la codificación y los saltos de línea (CRLF/LF) del archivo.
"""
import os
import re
import shutil
import subprocess
import sys

START = "# AGUACATE-START"
END = "# AGUACATE-END"

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


class HostsError(Exception):
    """No se ha podido leer o escribir el hosts."""


class HostsCorrupt(HostsError):
    """Las marcas de la app están rotas; no se toca el archivo."""


def default_hosts_path() -> str:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    return os.path.join(root, "System32", "drivers", "etc", "hosts")


def default_backup_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(base, "Aguacate", "hosts.backup")


def clean_domains(domains) -> list[str]:
    """Normaliza y valida dominios. Descarta los inválidos para que nadie pueda
    colar líneas arbitrarias en el hosts desde config.json."""
    out = []
    for d in domains:
        d = str(d).strip().lower().rstrip(".")
        if DOMAIN_RE.match(d) and d not in out:
            out.append(d)
    return out


def flush_dns():
    """ipconfig /flushdns sin abrir ventana y sin esperar (tarda ~0,2 s)."""
    if sys.platform != "win32":
        return
    subprocess.Popen(
        ["ipconfig", "/flushdns"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


# ---- manipulación de texto (sin tocar disco; fácil de testear) -----------------
def _marker_lines(lines):
    starts = [i for i, l in enumerate(lines) if l.strip() == START]
    ends = [i for i, l in enumerate(lines) if l.strip() == END]
    return starts, ends


def has_block(text: str) -> bool:
    """True si hay un bloque de la app. Lanza HostsCorrupt si las marcas están rotas."""
    lines = text.splitlines()
    starts, ends = _marker_lines(lines)
    if not starts and not ends:
        return False
    if len(starts) == 1 and len(ends) == 1 and starts[0] < ends[0]:
        return True
    raise HostsCorrupt(
        f"Marcas rotas en hosts: {len(starts)} '{START}' y {len(ends)} '{END}'."
    )


def strip_block(text: str, nl: str) -> str:
    if not has_block(text):
        return text
    lines = text.splitlines()
    starts, ends = _marker_lines(lines)
    s, e = starts[0], ends[0]
    # quitar también la línea en blanco que añadimos antes del bloque
    if s > 0 and lines[s - 1].strip() == "":
        s -= 1
    kept = lines[:s] + lines[e + 1:]
    return nl.join(kept) + (nl if kept else "")


def add_block(text: str, domains, nl: str) -> str:
    base = strip_block(text, nl)
    if base and not base.endswith(("\n", "\r")):
        base += nl
    block = [START]
    for d in clean_domains(domains):
        block.append(f"127.0.0.1 {d}")
        block.append(f"::1 {d}")
    block.append(END)
    return base + nl + nl.join(block) + nl


# ---- acceso al archivo ------------------------------------------------------------
class HostsFile:
    def __init__(self, path=None, backup_path=None, flush=flush_dns):
        self.path = path or default_hosts_path()
        self.backup_path = backup_path or default_backup_path()
        self.flush = flush

    def _read(self):
        try:
            with open(self.path, "rb") as f:
                raw = f.read()
        except OSError as e:
            raise HostsError(f"No se puede leer {self.path}: {e}") from e
        if raw.startswith(b"\xef\xbb\xbf"):
            enc = "utf-8-sig"
        else:
            try:
                raw.decode("utf-8")
                enc = "utf-8"
            except UnicodeDecodeError:
                enc = "cp1252"
        text = raw.decode(enc)
        nl = "\r\n" if "\r\n" in text or not text else "\n"
        return text, enc, nl

    def _write(self, text: str, enc: str):
        tmp = self.path + ".aguacate.tmp"
        try:
            with open(tmp, "w", encoding=enc, newline="") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except OSError as e:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise HostsError(
                f"No se puede escribir {self.path}: {e}. "
                "¿Falta el permiso de administrador, el archivo es de solo lectura "
                "o el antivirus lo está bloqueando?"
            ) from e

    def _backup_once(self):
        if os.path.exists(self.backup_path):
            return
        os.makedirs(os.path.dirname(self.backup_path), exist_ok=True)
        shutil.copy2(self.path, self.backup_path)

    # ---- API ----
    def is_blocked(self) -> bool:
        text, _, _ = self._read()
        return has_block(text)

    def block(self, domains):
        text, enc, nl = self._read()
        has_block(text)                       # valida marcas antes de tocar nada
        self._backup_once()
        new = add_block(text, domains, nl)
        if new != text:
            self._write(new, enc)
        self.flush()

    def unblock(self) -> bool:
        """Quita el bloque si existe. Devuelve True si había algo que quitar."""
        text, enc, nl = self._read()
        if not has_block(text):
            return False
        self._write(strip_block(text, nl), enc)
        self.flush()
        return True
