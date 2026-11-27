"""Dibujo del aguacate con QPainter.

- Cuerpo (cáscara y pulpa) en pixel art: se rasteriza la silueta Bézier sobre una
  rejilla de celdas de PIXEL px y cada celda se pinta de un color plano.
- Hueso liso (no pixelado). Se borra con un barrido en sentido horario desde las 12.
- Contador MM:SS con una fuente de píxeles 5x7 definida aquí mismo (sin archivos).
"""
import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QImage, QPainter, QPainterPath, QRadialGradient, QTransform,
)

PIXEL = 8           # tamaño de cada "píxel" del aguacate
FONT_PIXEL = 3      # tamaño de cada píxel de la fuente del contador

# Paleta (pocos colores, como en pixel art)
OUTLINE = QColor("#14240B")
SKIN = QColor("#2F5418")
SKIN_SHINE = QColor("#4A7A26")
FLESH_RIM = QColor("#9CC447")
FLESH_1 = QColor("#C4DE6A")
FLESH_2 = QColor("#DDEB8E")
FLESH_3 = QColor("#EEF4B4")
CAVITY = QColor("#D2E48C")
PIT_DARK = QColor("#5A3416")
PIT_LIGHT = QColor("#A8693A")
TEXT_WORK = QColor("#1F3A12")
TEXT_BREAK = QColor("#1D6A7A")
TEXT_SHADOW = QColor(255, 255, 255, 110)

# Fuente 5x7: cada carácter son 7 filas de 5 bits
FONT = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ":": ["0", "1", "1", "0", "1", "1", "0"],
}
ICON_PLAY = ["10000", "11000", "11100", "11110", "11100", "11000", "10000"]
ICON_PAUSE = ["11011", "11011", "11011", "11011", "11011", "11011", "11011"]


@dataclass
class Geometry:
    width: float
    height: float

    @property
    def avocado_rect(self) -> QRectF:
        return QRectF(4, 4, self.width - 8, self.height - 8)

    @property
    def pit_center(self) -> QPointF:
        r = self.avocado_rect
        return QPointF(r.center().x(), r.top() + r.height() * 0.66)

    @property
    def pit_radius(self) -> float:
        return self.avocado_rect.width() * 0.22

    @property
    def text_top(self) -> float:
        r = self.avocado_rect
        return r.top() + r.height() * 0.27


def skin_path(r: QRectF) -> QPainterPath:
    """Contorno de pera: estrecho arriba, ancho abajo (curvas Bézier cúbicas)."""
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    cx = x + w / 2

    def p(fx, fy):
        return QPointF(x + fx * w, y + fy * h)

    path = QPainterPath(QPointF(cx, y))
    path.cubicTo(p(0.74, 0.00), p(0.83, 0.15), p(0.85, 0.32))
    path.cubicTo(p(0.88, 0.44), p(1.00, 0.54), p(1.00, 0.70))
    path.cubicTo(p(1.00, 0.90), p(0.78, 1.00), QPointF(cx, y + h))
    path.cubicTo(p(0.22, 1.00), p(0.00, 0.90), p(0.00, 0.70))
    path.cubicTo(p(0.00, 0.54), p(0.12, 0.44), p(0.15, 0.32))
    path.cubicTo(p(0.17, 0.15), p(0.26, 0.00), QPointF(cx, y))
    path.closeSubpath()
    return path


def flesh_path(skin: QPainterPath, r: QRectF) -> QPainterPath:
    c = r.center()
    t = QTransform()
    t.translate(c.x(), c.y() + r.height() * 0.015)
    t.scale(0.80, 0.85)
    t.translate(-c.x(), -c.y())
    return t.map(skin)


# ---- cuerpo pixelado (se calcula una vez por tamaño y se guarda) -------------
_body_cache: dict = {}


def _body_image(g: Geometry) -> QImage:
    key = (int(g.width), int(g.height))
    if key in _body_cache:
        return _body_cache[key]

    r = g.avocado_rect
    skin, flesh = skin_path(r), flesh_path(skin_path(r), r)
    cols, rows = int(g.width) // PIXEL, int(g.height) // PIXEL
    off_x = (g.width - cols * PIXEL) / 2
    off_y = (g.height - rows * PIXEL) / 2

    def center(c, rw):
        return QPointF(off_x + (c + 0.5) * PIXEL, off_y + (rw + 0.5) * PIXEL)

    in_skin = [[skin.contains(center(c, rw)) for c in range(cols)] for rw in range(rows)]
    in_flesh = [[flesh.contains(center(c, rw)) for c in range(cols)] for rw in range(rows)]

    def is_skin(c, rw):
        return 0 <= c < cols and 0 <= rw < rows and in_skin[rw][c]

    def is_flesh(c, rw):
        return 0 <= c < cols and 0 <= rw < rows and in_flesh[rw][c]

    pc, pr = g.pit_center, g.pit_radius
    img = QImage(key[0], key[1], QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    for rw in range(rows):
        for c in range(cols):
            if not in_skin[rw][c]:
                continue
            neigh = [(c + 1, rw), (c - 1, rw), (c, rw + 1), (c, rw - 1)]
            if not all(is_skin(*n) for n in neigh):
                color = OUTLINE
            elif not in_flesh[rw][c]:
                # brillo en la cáscara del lado izquierdo-superior
                color = SKIN_SHINE if (c < cols * 0.32 and rw < rows * 0.6) else SKIN
            elif not all(is_flesh(*n) for n in neigh):
                color = FLESH_RIM
            else:
                pt = center(c, rw)
                d = math.hypot(pt.x() - pc.x(), pt.y() - pc.y()) / pr
                color = FLESH_3 if d < 1.45 else FLESH_2 if d < 2.1 else FLESH_1
            p.fillRect(QRectF(off_x + c * PIXEL, off_y + rw * PIXEL, PIXEL, PIXEL), color)
    p.end()
    _body_cache[key] = img
    return img


# ---- texto en píxeles ---------------------------------------------------------
def _glyph_width(ch: str) -> int:
    return len(FONT[ch][0])


def _draw_bitmap(p: QPainter, rows, x: float, y: float, px: float, color: QColor):
    for j, row in enumerate(rows):
        for i, bit in enumerate(row):
            if bit == "1":
                p.fillRect(QRectF(x + i * px, y + j * px, px, px), color)


def _draw_pixel_text(p: QPainter, text: str, cx: float, top: float, color: QColor):
    px = FONT_PIXEL
    width = sum(_glyph_width(ch) + 1 for ch in text) - 1
    x = cx - width * px / 2
    for ch in text:
        _draw_bitmap(p, FONT[ch], x + 1, top + 1, px, TEXT_SHADOW)   # sombra clara
        _draw_bitmap(p, FONT[ch], x, top, px, color)
        x += (_glyph_width(ch) + 1) * px


def fmt_time(seconds: float) -> str:
    s = int(seconds + 0.999)          # redondeo hacia arriba: 0.2 s -> 00:01
    return f"{s // 60:02d}:{s % 60:02d}"


# ---- dibujo principal ---------------------------------------------------------
def draw(p: QPainter, g: Geometry, *, remaining: float, fraction: float,
         is_break: bool, icon: str | None, show_time: bool = True):
    """icon: "play", "pause" o None."""
    p.drawImage(0, 0, _body_image(g))
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Hueco donde va el hueso (se ve cuando el barrido lo va borrando)
    pc, pr = g.pit_center, g.pit_radius
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(CAVITY)
    p.drawEllipse(pc, pr + 3, pr + 3)

    # Hueso: solo la parte que queda. El barrido empieza a las 12 y avanza
    # en sentido horario; queda el sector que va del borde del barrido a las 12.
    if fraction > 0:
        rect = QRectF(pc.x() - pr, pc.y() - pr, 2 * pr, 2 * pr)
        swept = 360.0 * (1.0 - fraction)
        sector = QPainterPath(pc)
        sector.arcTo(rect, 90.0 - swept, -360.0 * fraction)   # Qt: negativo = horario
        sector.closeSubpath()
        p.save()
        p.setClipPath(sector)
        grad = QRadialGradient(pc.x() - pr * 0.35, pc.y() - pr * 0.35, pr * 1.3)
        grad.setColorAt(0, PIT_LIGHT)
        grad.setColorAt(1, PIT_DARK)
        p.setBrush(QBrush(grad))
        p.drawEllipse(pc, pr, pr)
        p.setBrush(QColor(255, 255, 255, 60))
        p.drawEllipse(QPointF(pc.x() - pr * 0.35, pc.y() - pr * 0.4), pr * 0.22, pr * 0.15)
        p.restore()

    # Contador y estado, dentro de la pulpa
    color = TEXT_BREAK if is_break else TEXT_WORK
    top = g.text_top
    if show_time:
        _draw_pixel_text(p, fmt_time(remaining), g.width / 2, top, color)
    bitmap = {"play": ICON_PLAY, "pause": ICON_PAUSE}.get(icon)
    if bitmap:
        px = 3
        _draw_bitmap(p, bitmap, g.width / 2 - 2.5 * px, top + 9 * FONT_PIXEL, px, color)
