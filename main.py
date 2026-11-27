"""Aguacate Pomodoro – punto de entrada.

    python main.py               # normal (25 / 5 minutos), pide permisos para bloquear webs
    python main.py --demo        # pruebas: 10 s trabajo / 5 s descanso
    python main.py --sin-admin   # no pedir permisos (solo temporizador)
    python main.py --desbloquear # quitar el bloqueo del hosts y salir (emergencia)

Variable de entorno para desarrollo:
    AGUACATE_HOSTS=ruta\\a\\hosts_de_prueba   # usa ese archivo en vez del hosts real
"""
import atexit
import os
import signal
import sys
import tempfile

from aguacate import admin, config
from aguacate.blocker import HostsCorrupt, HostsError, HostsFile

TITLE = "Aguacate Pomodoro"
MANUAL_HELP = ("Para quitarlo a mano, mira la sección «Desbloquear webs a mano» "
               "del README.")


def install_error_log():
    """Con pythonw.exe no hay consola: los errores se guardan en
    %TEMP%\\aguacate\\errores.log para poder verlos."""
    import traceback
    path = os.path.join(tempfile.gettempdir(), "aguacate", "errores.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    def hook(exc_type, exc, tb):
        with open(path, "a", encoding="utf-8") as f:
            traceback.print_exception(exc_type, exc, tb, file=f)
        if sys.__stderr__:
            traceback.print_exception(exc_type, exc, tb)
    sys.excepthook = hook


def make_hosts():
    """Devuelve (HostsFile o None, puede_escribir)."""
    test_path = os.environ.get("AGUACATE_HOSTS")
    if test_path:
        backup = os.path.join(os.path.dirname(os.path.abspath(test_path)), "hosts.backup")
        return HostsFile(test_path, backup), True
    if sys.platform != "win32":
        return None, False
    return HostsFile(), admin.is_admin()


def run_unblock_only() -> int:
    """--desbloquear: limpia el hosts y sale, sin abrir el aguacate."""
    hosts, can_write = make_hosts()
    if hosts is None:
        print("El bloqueo solo existe en Windows.")
        return 0
    if not can_write:
        if admin.ELEVATED_FLAG not in sys.argv and admin.relaunch_as_admin(console=True):
            return 0
        print("Hacen falta permisos de administrador. " + MANUAL_HELP)
        return 1
    try:
        removed = hosts.unblock()
    except HostsError as e:
        print(f"Error: {e}\n{MANUAL_HELP}")
        input("Pulsa Intro para cerrar…") if admin.ELEVATED_FLAG in sys.argv else None
        return 1
    msg = "Bloqueo quitado." if removed else "No había ningún bloqueo. Nada que hacer."
    print(msg)
    if admin.ELEVATED_FLAG in sys.argv:          # ventana nueva: que dé tiempo a leerlo
        input("Pulsa Intro para cerrar…")
    return 0


def main() -> int:
    argv = sys.argv
    install_error_log()
    if "--desbloquear" in argv:
        return run_unblock_only()

    # 1) Pedir permisos de administrador (UAC) relanzándose. Si se rechaza, seguimos.
    uac_declined = False
    if (sys.platform == "win32" and not os.environ.get("AGUACATE_HOSTS")
            and not admin.is_admin()
            and admin.ELEVATED_FLAG not in argv and "--sin-admin" not in argv):
        if admin.relaunch_as_admin():
            return 0                    # la copia con permisos toma el relevo
        uac_declined = True

    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox
    from aguacate.window import AvocadoWindow

    app = QApplication(argv)
    app.setApplicationName(TITLE)

    # 2) Solo un aguacate a la vez (dos copias se pelearían por el hosts)
    lock = QLockFile(os.path.join(tempfile.gettempdir(), "aguacate-pomodoro.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(200):
        QMessageBox.information(None, TITLE, "Ya hay un aguacate abierto.")
        return 0

    # 3) Preparar el bloqueo y limpiar restos de una sesión anterior que se cerró mal
    hosts, can_write = make_hosts()
    notices = []
    if hosts is not None and can_write:
        try:
            if hosts.unblock():
                notices.append("La última vez la app no se cerró bien y dejó webs "
                               "bloqueadas. Ya lo he limpiado.")
        except HostsCorrupt as e:
            notices.append(f"{e}\nNo toco el hosts para no estropearlo. "
                           f"Bloqueo desactivado.\n{MANUAL_HELP}")
            hosts = None
        except HostsError as e:
            notices.append(f"{e}\nBloqueo desactivado.")
            hosts = None
    elif hosts is not None:
        try:
            leftover = hosts.is_blocked()
        except HostsError:
            leftover = False
        if leftover:
            notices.append("Hay webs bloqueadas de una sesión anterior y sin permisos "
                           "de administrador no puedo quitarlas.\nCierra y vuelve a abrir "
                           f"aceptando el permiso. {MANUAL_HELP}")
        motivo = "has rechazado el permiso" if uac_declined else "no tengo permisos de administrador"
        notices.append(f"El bloqueo de webs está desactivado porque {motivo}.\n"
                       "El aguacate funciona como temporizador normal.")
        hosts = None

    cfg = config.load()
    demo = "--demo" in argv
    if demo:
        cfg["work_minutes"], cfg["break_minutes"] = 10, 5

    win = AvocadoWindow(cfg, demo=demo, hosts=hosts)
    win.show()
    win.place_bottom_right()
    for n in notices:
        QMessageBox.warning(win, TITLE, n)

    # 4) Quitar el bloqueo pase lo que pase al salir
    app.aboutToQuit.connect(win.release_block)
    app.commitDataRequest.connect(lambda *_: win.release_block())   # apagar / cerrar sesión
    atexit.register(win.release_block)
    signal.signal(signal.SIGINT, lambda *_: app.quit())              # Ctrl+C en la consola
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, lambda *_: app.quit())

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
