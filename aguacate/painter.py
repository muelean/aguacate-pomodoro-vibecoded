"""Dibujo del aguacate con QPainter, todo en pixel art.

- La silueta Bézier se rasteriza sobre una rejilla de celdas de PIXEL px.
- El hueso usa la misma rejilla. Se borra celda a celda con un barrido en sentido
  horario desde las 12; donde ya no hay hueso se ve el hueco de la pulpa.
- Contador MM:SS en un recuadro propio, con una fuente de píxeles 5x7 definida aquí.
"""
import math
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QTransform

PIXEL = 8           # tamaño de cada "píxel" del aguacate y del hueso
FONT_PIXEL = 3      # tamaño de cada píxel de la fuente del contador

# Paleta
OUTLINE = QColor("#14240B")
SKIN = QColor("#2F5418")
SKIN_SHINE = QColor("#4A7A26")
FLESH_RIM = QColor("#9CC447")
FLESH_1 = QColor("#C4DE6A")
FLESH_2 = QColor("#DDEB8E")
FLESH_3 = QColor("#EEF4B4")
CAVITY = QColor("#D4E591")
CAVITY_RIM = QColor("#B9D271")
PIT_OUTLINE = QColor("#3A1F0B")
PIT_DARK = QColor("#6B3E1A")
PIT_MID = QColor("#8A5227")
PIT_LIGHT = QColor("#AC6C3A")
PIT_SHINE = QColor("#D29A68")
BOX_BG = QColor("#1F3A12")
BOX_BORDER = QColor("#14240B")
TEXT_WORK = QColor("#EEF4B4")
TEXT_BREAK = QColor("#8FE3F0")
ICON_WORK = QColor("#1F3A12")
ICON_BREAK = QColor("#1D6A7A")

# Fuente 5x7: cada carácter son 7 filas de bits
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
ICON_PLAY = ["1000", "1100", "1110", "1111", "1110", "1100", "1000"]
ICON_PAUSE = ["11011", "11011", "11011", "11011", "11011", "11011", "11011"]
ICON_LOCK = ["01110", "10001", "10001", "11111", "11011", "11011", "11111"]


@dataclass
class Geometry:
    width: float
    height: float

    @property
    def avocado_rect(self) -> QRectF:
        return QRectF(4, 4, self.width - 8, self.height - 8)

    @property
    def grid(self):
        """(columnas, filas, desplazamiento x, desplazamiento y) de la rejilla."""
        cols, rows = int(self.width) // PIXEL, int(self.height) // PIXEL
        return cols, rows, (self.width - cols * PIXEL) / 2, (self.height - rows * PIXEL) / 2

    @property
    def pit_center(self) -> QPointF:
        """Centro del hueso, ajustado a una esquina de celda para que sea simétrico."""
        cols, rows, ox, oy = self.grid
        r = self.avocado_rect
        cx = ox + round((r.center().x() - ox) / PIXEL) * PIXEL
        cy = oy + round((r.top() + r.height() * 0.66 - oy) / PIXEL) * PIXEL
        return QPointF(cx, cy)

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


# ---- elementos precalculados (una vez por tamaño de ventana) -----------------
@dataclass
class _Cache:
    body: QImage
    cavity: QImage
    pit_cells: list = field(default_factory=list)   # (ángulo, QRectF, QColor)


_cache: dict = {}


def _build(g: Geometry) -> _Cache:
    key = (int(g.width), int(g.height))
    if key in _cache:
        return _cache[key]

    r = g.avocado_rect
    skin = skin_path(r)
    flesh = flesh_path(skin, r)
    cols, rows, ox, oy = g.grid
    pc, pr = g.pit_center, g.pit_radius

    def center(c, rw):
        return QPointF(ox + (c + 0.5) * PIXEL, oy + (rw + 0.5) * PIXEL)

    def cell(c, rw):
        return QRectF(ox + c * PIXEL, oy + rw * PIXEL, PIXEL, PIXEL)

    def in_pit(c, rw):
        pt = center(c, rw)
        return math.hypot(pt.x() - pc.x(), pt.y() - pc.y()) <= pr

    in_skin = [[skin.contains(center(c, rw)) for c in range(cols)] for rw in range(rows)]
    in_flesh = [[flesh.contains(center(c, rw)) for c in range(cols)] for rw in range(rows)]

    def get(grid, c, rw):
        return 0 <= c < cols and 0 <= rw < rows and grid[rw][c]

    def neigh(c, rw):
        return [(c + 1, rw), (c - 1, rw), (c, rw + 1), (c, rw - 1)]

    # Cuerpo: cáscara y pulpa
    body = QImage(key[0], key[1], QImage.Format.Format_ARGB32_Premultiplied)
    body.fill(Qt.GlobalColor.transparent)
    p = QPainter(body)
    for rw in range(rows):
        for c in range(cols):
            if not in_skin[rw][c]:
                continue
            if not all(get(in_skin, *n) for n in neigh(c, rw)):
                color = OUTLINE
            elif not in_flesh[rw][c]:
                color = SKIN_SHINE if (c < cols * 0.32 and rw < rows * 0.6) else SKIN
            elif not all(get(in_flesh, *n) for n in neigh(c, rw)):
                color = FLESH_RIM
            else:
                pt = center(c, rw)
                d = math.hypot(pt.x() - pc.x(), pt.y() - pc.y()) / pr
                color = FLESH_3 if d < 1.45 else FLESH_2 if d < 2.1 else FLESH_1
            p.fillRect(cell(c, rw), color)
    p.end()

    # Hueco del hueso (lo que se ve cuando el barrido lo borra)
    cavity = QImage(key[0], key[1], QImage.Format.Format_ARGB32_Premultiplied)
    cavity.fill(Qt.GlobalColor.transparent)
    p = QPainter(cavity)
    pit_cells = []
    for rw in range(rows):
        for c in range(cols):
            if not in_pit(c, rw):
                continue
            edge = not all(in_pit(*n) for n in neigh(c, rw))
            p.fillRect(cell(c, rw), CAVITY_RIM if edge else CAVITY)

            # Color del hueso: luz desde arriba a la izquierda
            pt = center(c, rw)
            dx, dy = (pt.x() - pc.x()) / pr, (pt.y() - pc.y()) / pr
            light = -(dx + dy) / math.sqrt(2)          # 1 = arriba-izquierda
            if edge:
                color = PIT_OUTLINE
            elif -0.62 < dx < -0.28 and -0.62 < dy < -0.28:
                color = PIT_SHINE
            elif light > 0.25:
                color = PIT_LIGHT
            elif light > -0.35:
                color = PIT_MID
            else:
                color = PIT_DARK
            # ángulo en sentido horario desde las 12 (0–360)
            angle = math.degrees(math.atan2(pt.x() - pc.x(), -(pt.y() - pc.y()))) % 360
            pit_cells.append((angle, cell(c, rw), color))
    p.end()

    _cache[key] = _Cache(body, cavity, pit_cells)
    return _cache[key]


# ---- texto en píxeles ---------------------------------------------------------
def _draw_bitmap(p: QPainter, rows, x: float, y: float, px: float, color: QColor):
    for j, row in enumerate(rows):
        for i, bit in enumerate(row):
            if bit == "1":
                p.fillRect(QRectF(x + i * px, y + j * px, px, px), color)


def _text_width(text: str) -> int:
    """Ancho en píxeles de fuente (1 columna de separación entre caracteres)."""
    return sum(len(FONT[ch][0]) + 1 for ch in text) - 1


def _draw_box(p: QPainter, rect: QRectF, px: float):
    """Recuadro pixelado: borde de 1 px y esquinas recortadas en escalón."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    # borde (rectángulo exterior sin las esquinas)
    p.fillRect(QRectF(x + px, y, w - 2 * px, h), BOX_BORDER)
    p.fillRect(QRectF(x, y + px, w, h - 2 * px), BOX_BORDER)
    # relleno
    p.fillRect(QRectF(x + 2 * px, y + px, w - 4 * px, h - 2 * px), BOX_BG)
    p.fillRect(QRectF(x + px, y + 2 * px, w - 2 * px, h - 4 * px), BOX_BG)


def fmt_time(seconds: float) -> str:
    s = int(seconds + 0.999)          # redondeo hacia arriba: 0.2 s -> 00:01
    return f"{s // 60:02d}:{s % 60:02d}"


# ---- dibujo principal ---------------------------------------------------------
def draw(p: QPainter, g: Geometry, *, remaining: float, fraction: float,
         is_break: bool, icon: str | None, show_time: bool = True):
    """icon: "play", "pause", "lock" (webs bloqueadas) o None."""
    c = _build(g)
    p.drawImage(0, 0, c.body)
    p.drawImage(0, 0, c.cavity)

    # Hueso: quedan las celdas cuyo ángulo ya ha pasado el barrido
    swept = 360.0 * (1.0 - fraction)
    if fraction > 0:
        for angle, rect, color in c.pit_cells:
            if angle >= swept:
                p.fillRect(rect, color)

    # Recuadro del contador
    px = FONT_PIXEL
    text = fmt_time(remaining)
    tw, th = _text_width(text) * px, 7 * px
    pad = 3 * px
    box = QRectF(round(g.width / 2 - tw / 2 - pad), round(g.text_top - pad),
                 tw + 2 * pad, th + 2 * pad)
    _draw_box(p, box, px)
    if show_time:
        x = box.x() + pad
        for ch in text:
            _draw_bitmap(p, FONT[ch], x, box.y() + pad, px,
                         TEXT_BREAK if is_break else TEXT_WORK)
            x += (len(FONT[ch][0]) + 1) * px

    # Icono de estado debajo del recuadro
    bitmap = {"play": ICON_PLAY, "pause": ICON_PAUSE, "lock": ICON_LOCK}.get(icon)
    if bitmap:
        w = len(bitmap[0]) * px
        _draw_bitmap(p, bitmap, round(g.width / 2 - w / 2), box.bottom() + 2 * px, px,
                     ICON_BREAK if is_break else ICON_WORK)
