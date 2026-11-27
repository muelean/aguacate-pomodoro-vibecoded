"""Genera build/aguacate.ico a partir del dibujo del aguacate (sin imágenes externas).

El .ico lleva varios tamaños (16–256 px) guardados como PNG, que es lo que
Windows usa para el icono del .exe, del escritorio y de la barra de tareas.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QBuffer, QIODevice  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from aguacate.painter import icon_image  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_bytes(size: int) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    icon_image(size).save(buf, "PNG")
    return bytes(buf.data())


def write_ico(path: str):
    images = [png_bytes(s) for s in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))          # reservado, tipo=icono, nº
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for size, png in zip(SIZES, images):
        dim = 0 if size == 256 else size                       # 0 significa 256
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
        data += png
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(header + entries + data)


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join("build", "aguacate.ico")
    write_ico(out)
    print(f"Icono creado: {out}")
