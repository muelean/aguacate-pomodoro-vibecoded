"""Dibujo del aguacate con QPainter. Todo se calcula a partir de la geometría
para poder cambiar el tamaño de la ventana sin tocar nada más.

Disposición (de arriba abajo):
  [ pastilla con MM:SS y estado ]
  [ aguacate: cáscara > pulpa > anillo de progreso > hueso (se encoge) ]
"""
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient, QTransform,
)

# Paleta
SKIN_DARK = QColor("#1F3A12")
SKIN_LIGHT = QColor("#3F6B22")
FLESH_EDGE = QColor("#A9CF54")
FLESH_CENTER = QColor("#F1F5B4")
PIT_DARK = QColor("#5A3416")
PIT_LIGHT = QColor("#A8693A")
RING_WORK = QColor("#4E7A1F")
RING_BREAK = QColor("#2E8FA3")
RING_TRACK = QColor(0, 0, 0, 28)
PILL_BG = QColor(25, 35, 20, 215)
PILL_TEXT = QColor("#F4F8E0")
PILL_SUB = QColor("#C7DB8E")


@dataclass
class Geometry:
    width: float
    height: float
    pill_h: float = 58.0

    @property
    def avocado_rect(self) -> QRectF:
        top = self.pill_h + 8
        return QRectF(6, top, self.width - 12, self.height - top - 6)

    @property
    def pit_center(self) -> QPointF:
        r = self.avocado_rect
        return QPointF(r.center().x(), r.top() + r.height() * 0.63)

    @property
    def ring_radius(self) -> float:
        return self.avocado_rect.width() * 0.30

    @property
    def pit_radius(self) -> float:
        return self.avocado_rect.width() * 0.21


def skin_path(r: QRectF) -> QPainterPath:
    """Contorno de pera: estrecho arriba, ancho abajo (curvas Bézier cúbicas)."""
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    cx = x + w / 2

    def p(fx, fy):
        return QPointF(x + fx * w, y + fy * h)

    path = QPainterPath(QPointF(cx, y))                               # punta superior
    path.cubicTo(p(0.70, 0.00), p(0.76, 0.18), p(0.80, 0.33))         # hombro dcho.
    path.cubicTo(p(0.86, 0.45), p(1.00, 0.55), p(1.00, 0.70))         # barriga dcha.
    path.cubicTo(p(1.00, 0.90), p(0.78, 1.00), QPointF(cx, y + h))    # base dcha.
    path.cubicTo(p(0.22, 1.00), p(0.00, 0.90), p(0.00, 0.70))         # base izda.
    path.cubicTo(p(0.00, 0.55), p(0.14, 0.45), p(0.20, 0.33))         # barriga izda.
    path.cubicTo(p(0.24, 0.18), p(0.30, 0.00), QPointF(cx, y))        # hombro izdo.
    path.closeSubpath()
    return path


def flesh_path(skin: QPainterPath, r: QRectF) -> QPainterPath:
    """La pulpa es la cáscara encogida un 10 % hacia su centro."""
    c = r.center()
    t = QTransform()
    t.translate(c.x(), c.y() + r.height() * 0.015)
    t.scale(0.89, 0.91)
    t.translate(-c.x(), -c.y())
    return t.map(skin)


def fmt_time(seconds: float) -> str:
    s = int(seconds + 0.999)          # redondeo hacia arriba: 0.2 s -> 00:01
    return f"{s // 60:02d}:{s % 60:02d}"


def draw(p: QPainter, g: Geometry, *, remaining: float, fraction: float,
         is_break: bool, status_text: str):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = g.avocado_rect

    # --- Cáscara ---
    skin = skin_path(r)
    grad = QRadialGradient(r.center().x() - r.width() * 0.2, r.top() + r.height() * 0.35,
                           r.width() * 0.9)
    grad.setColorAt(0, SKIN_LIGHT)
    grad.setColorAt(1, SKIN_DARK)
    p.setPen(QPen(QColor(0, 0, 0, 90), 1.5))
    p.setBrush(QBrush(grad))
    p.drawPath(skin)

    # --- Pulpa ---
    flesh = flesh_path(skin, r)
    pc = g.pit_center
    fgrad = QRadialGradient(pc, r.width() * 0.6)
    fgrad.setColorAt(0, FLESH_CENTER)
    fgrad.setColorAt(1, FLESH_EDGE)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(fgrad))
    p.drawPath(flesh)

    # --- Anillo de progreso (pista + arco restante) ---
    rr = g.ring_radius
    ring_w = r.width() * 0.055
    ring_rect = QRectF(pc.x() - rr, pc.y() - rr, 2 * rr, 2 * rr)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(RING_TRACK, ring_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
    p.drawEllipse(ring_rect)
    if fraction > 0:
        color = RING_BREAK if is_break else RING_WORK
        p.setPen(QPen(color, ring_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # Qt: ángulos en 1/16 de grado; 90° = arriba; negativo = sentido horario
        p.drawArc(ring_rect, 90 * 16, int(-360 * 16 * fraction))

    # --- Hueso: su radio es proporcional al tiempo que queda ---
    pr = g.pit_radius * fraction
    if pr > 0.5:
        pgrad = QRadialGradient(pc.x() - pr * 0.35, pc.y() - pr * 0.35, pr * 1.3)
        pgrad.setColorAt(0, PIT_LIGHT)
        pgrad.setColorAt(1, PIT_DARK)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(pgrad))
        p.drawEllipse(pc, pr, pr)
        # brillo
        p.setBrush(QColor(255, 255, 255, 60))
        p.drawEllipse(QPointF(pc.x() - pr * 0.35, pc.y() - pr * 0.4), pr * 0.22, pr * 0.15)

    # --- Pastilla con el contador ---
    pill = QRectF(g.width * 0.04, 2, g.width * 0.92, g.pill_h)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PILL_BG)
    p.drawRoundedRect(pill, 16, 16)

    f = QFont("Segoe UI")
    f.setPixelSize(int(g.pill_h * 0.48))
    f.setBold(True)
    p.setFont(f)
    p.setPen(PILL_TEXT)
    p.drawText(QRectF(pill.x(), pill.y() + 2, pill.width(), pill.height() * 0.64),
               Qt.AlignmentFlag.AlignCenter, fmt_time(remaining))

    f2 = QFont("Segoe UI")
    f2.setPixelSize(int(g.pill_h * 0.2))
    p.setFont(f2)
    p.setPen(PILL_SUB)
    p.drawText(QRectF(pill.x(), pill.y() + pill.height() * 0.60, pill.width(),
                      pill.height() * 0.36),
               Qt.AlignmentFlag.AlignCenter, status_text)
