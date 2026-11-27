"""Permisos de administrador en Windows.

Al arrancar sin permisos, la app se vuelve a lanzar a sí misma pidiéndolos (UAC).
Si el usuario dice «No», sigue funcionando como temporizador sin bloqueo.
"""
import os
import sys

IS_WINDOWS = sys.platform == "win32"
ELEVATED_FLAG = "--elevado"     # evita bucles: el proceso relanzado no vuelve a pedir


def is_admin() -> bool:
    if not IS_WINDOWS:
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    import ctypes
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def relaunch_as_admin(console: bool = False) -> bool:
    """Muestra el aviso de UAC y lanza otra copia con permisos.
    Devuelve True si se ha lanzado (esta copia debe cerrarse) y False si el
    usuario lo ha rechazado o ha fallado.
    console=False usa pythonw.exe para que no aparezca una ventana negra que,
    si se cerrara, mataría la app sin limpiar el hosts."""
    if not IS_WINDOWS:
        return False
    import ctypes
    import subprocess

    if getattr(sys, "frozen", False):            # .exe de PyInstaller
        exe, args = sys.executable, sys.argv[1:]
    else:                                        # python main.py
        exe, args = sys.executable, [os.path.abspath(sys.argv[0])] + sys.argv[1:]
        pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if not console and os.path.exists(pythonw):
            exe = pythonw
    params = subprocess.list2cmdline(args + [ELEVATED_FLAG])
    cwd = os.path.dirname(os.path.abspath(sys.argv[0]))
    # ShellExecuteW devuelve > 32 si ha ido bien; <= 32 si se rechaza (UAC «No» = 5)
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, cwd, 1)
    return rc > 32
