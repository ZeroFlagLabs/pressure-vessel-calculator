"""Generate original pressure-vessel schematics (not copied publication art)."""
from pathlib import Path
import math
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QImage,QPainter,QPainterPath,QPen,QColor,QFont
from PySide6.QtWidgets import QApplication

def draw(thick,path):
    im=QImage(480,420,QImage.Format.Format_ARGB32_Premultiplied);im.fill(Qt.GlobalColor.transparent)
    p=QPainter(im);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen=QPen(QColor("#243d58"),3);p.setPen(pen);p.setBrush(Qt.BrushStyle.NoBrush)
    cx,cy=228,80;rx,ry=155,55;h=245
    # Cylinder section: annular top and front half of base ellipse.
    p.drawEllipse(QRectF(cx-rx,cy-ry,2*rx,2*ry))
    k=.48 if thick else .91
    p.drawEllipse(QRectF(cx-rx*k,cy-ry*k,2*rx*k,2*ry*k))
    p.drawLine(QPointF(cx-rx,cy),QPointF(cx-rx,cy+h))
    p.drawLine(QPointF(cx+rx,cy),QPointF(cx+rx,cy+h))
    p.drawArc(QRectF(cx-rx,cy+h-ry,2*rx,2*ry),180*16,180*16)
    # Surface element on the front: longitudinal/hoop directions.
    p.setBrush(QColor("white"));p.drawRect(QRectF(197,201,62,46));p.setBrush(Qt.BrushStyle.NoBrush)
    def arrow(x1,y1,x2,y2):
        p.drawLine(QPointF(x1,y1),QPointF(x2,y2))
        a=math.atan2(y2-y1,x2-x1)
        for d in (-.48,.48):
            p.drawLine(QPointF(x2,y2),QPointF(x2-11*math.cos(a+d),y2-11*math.sin(a+d)))
    arrow(228,201,228,157);arrow(228,247,228,291)
    arrow(197,224,148,224);arrow(259,224,308,224)
    font=QFont("Segoe UI");font.setPixelSize(23);p.setFont(font)
    p.drawText(QPointF(238,166),"σ₁");p.drawText(QPointF(310,215),"σ₂")
    if thick:
        # Radial direction along the top annulus, distinct from front element.
        arrow(308,81,364,81);p.drawText(QPointF(398,88),"σ₃")
    p.end()
    assert im.save(str(path))
if __name__=="__main__":
    a=QApplication([])
    dest=Path(__file__).resolve().parents[1]/"src/resources/images"
    draw(False,dest/"thin.png");draw(True,dest/"thick.png")
