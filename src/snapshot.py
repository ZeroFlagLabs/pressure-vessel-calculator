"""Printable report, concept B. No screen captures or recalculation."""
from datetime import datetime
from app_info import APP_VERSION
from pathlib import Path
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QColor,QFont,QFontMetrics,QPainter,QPen,QPixmap
WIDTH,HEIGHT=1472,912
W,H=966,599
GEOMETRY_X,MATERIAL_X,INPUT_WIDTH=28,364,308
INK,MUTED,BLUE,RULE="#243D58","#657A91","#164F8A","#D8E1EA"
GREEN,RED="#18744F","#B42318"

def fmt_dimension(value):
    places=max(3,-value.normalize().as_tuple().exponent)
    return f"{value:.{places}f}"


def geometry_rows(window):
    rows=[]
    for dim in window.dims.values():
        lo,hi=dim.bounds()
        nominal,tolerance=(lo+hi)/2,(hi-lo)/2
        a,b=fmt_dimension(nominal),fmt_dimension(tolerance)
        value=f"{a} in" if tolerance==0 else f"{a} \u00b1 {b} in"
        rows.append((dim.name+(" (derived)" if dim.derived else ""),value))
    return rows


def report_data(window):
    if window.result is None:raise ValueError("A valid calculation is required.")
    raw=window.raw;res=window.result
    geom=geometry_rows(window)
    material=[("Material yield",f"{window.fields['yield_strength'].rawText()} psi"),
        ("Temperature derating",window.fields["derating_factor"].rawText()),
        ("Working pressure",f"{window.fields['working_pressure'].rawText()} psi"),
        ("Test pressure",f"{window.fields['test_pressure'].rawText()} psi"),
        ("Axial load",f"{window.fields['axial_load'].rawText()} lbf"),
        ("Pressure direction",raw["pressure_type"].capitalize()),
        ("End configuration",raw["end_condition"].capitalize())]
    method=res["wall_type"]+(" (Lamé)" if res["wall_type"]=="Thick Wall" else " (Membrane)")
    analysis=[("R/t",f"{res['ratio']:.3f}")]
    return geom,material,method,analysis

def original_illustration(window):
    name="thick.png" if window.result["wall_type"]=="Thick Wall" else "thin.png"
    source=QPixmap(str(Path(__file__).resolve().parent/"resources/images"/name))
    if source.isNull():raise ValueError("Method illustration missing: "+name)
    img=source.toImage()
    if img.hasAlphaChannel():
        x0,y0,x1,y1=img.width(),img.height(),-1,-1
        for y in range(img.height()):
            for x in range(img.width()):
                if img.pixelColor(x,y).alpha()>16:
                    x0=min(x0,x);y0=min(y0,y);x1=max(x1,x);y1=max(y1,y)
        if x1>=x0 and y1>=y0:source=source.copy(x0,y0,x1-x0+1,y1-y0+1)
    return source

def render_snapshot(window,timestamp=None):
    geom,material,method,analysis=report_data(window)
    timestamp=timestamp or datetime.now()
    image=QPixmap(WIDTH,HEIGHT);image.fill(QColor("white"))
    p=QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.scale(WIDTH/W,966/634)  # preserve B23 typography and vertical positions
    def text(x,y,w,h,value,*,size=12,bold=False,colour=INK,align="left"):
        f=QFont("Segoe UI");f.setPixelSize(size)
        f.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        value=str(value)
        while QFontMetrics(f).horizontalAdvance(value)>w and f.pixelSize()>7:
            f.setPixelSize(f.pixelSize()-1)
        if QFontMetrics(f).horizontalAdvance(value)>w:raise ValueError("Report text too wide: "+value)
        p.setFont(f);p.setPen(QColor(colour))
        flags={"left":Qt.AlignmentFlag.AlignLeft,"right":Qt.AlignmentFlag.AlignRight,"center":Qt.AlignmentFlag.AlignHCenter}[align]|Qt.AlignmentFlag.AlignVCenter
        p.drawText(QRectF(x,y,w,h),int(flags),value)
    def line(y,x1=28,x2=938):
        p.setPen(QPen(QColor(RULE),.9));p.drawLine(QRectF(x1,y,x2-x1,0).topLeft(),QRectF(x1,y,x2-x1,0).topRight())
    def heading(x,y,w,value):text(x,y,w,22,value,size=14,bold=True,colour=BLUE)
    def pair(x,y,w,label,value,label_width):
        text(x,y,label_width,23,label,colour=MUTED)
        text(x+label_width+5,y,w-label_width-5,23,value,bold=True,align="right")
    def result_section(x,key,title):
        c=window.result[key];w=434
        heading(x,287,w,title)
        line(318,x,x+w)
        def stress(value):return "—" if value is None else f"{value:.0f} psi"
        def util(value):
            if value is None:return "—",MUTED
            passed=value<=1
            return f"{value:.2f} ({'PASS' if passed else 'FAIL'})",GREEN if passed else RED
        rows=[("Pressure",stress(c["pressure"]),False,INK),
            ("Longitudinal",stress(c["sigma_long"]),False,INK),
            ("Hoop",stress(c["sigma_hoop"]),False,INK),
            ("Radial",stress(c["sigma_radial"] if window.result["wall_type"]=="Thick Wall" else None),False,INK),
            ("Von Mises",stress(c["sigma_vm"]),False,INK),
            ("Von Mises utilisation",*util(c["uf_vm"])),
            ("Maximum shear",stress(c["tau"]),False,INK),
            ("Shear utilisation",*util(c["uf_tau"]))]
        for i,row in enumerate(rows):
            if len(row)==3:label,value,colour=row;bold=True
            else:label,value,bold,colour=row
            y=319+i*33
            text(x,y,212,32,label,size=14,bold=bold)
            text(x+217,y,w-217,32,value,size=14,bold=bold,colour=colour,align="right")
            if i<len(rows)-1:line(y+33,x,x+w)
    try:
        p.setPen(QPen(QColor("#9FBBD5"),1));p.drawRect(QRectF(5,5,W-11,H-11))
        text(28,14,620,40,"Pressure Vessel Calculator",size=23,bold=True,colour=BLUE)
        text(650,17,288,31,timestamp.strftime("%d %b %Y  %H:%M")+"  |  v"+APP_VERSION,size=11,colour=MUTED,align="right")
        line(61)
        heading(GEOMETRY_X,76,INPUT_WIDTH,"GEOMETRY")
        for i,(label,value) in enumerate(geom):pair(GEOMETRY_X,101+24*i,INPUT_WIDTH,label,value,130)
        if window.derived!="t" and any(window.dims[k].bounds()[0]!=window.dims[k].bounds()[1] for k in window.dims if k!=window.derived):
            text(GEOMETRY_X,174,INPUT_WIDTH,15,f"Used OD / ID: {window.raw['od']:.9g} / {window.raw['id']:.9g} in",size=10,colour=MUTED)
        heading(GEOMETRY_X,191,INPUT_WIDTH,"ANALYSIS")
        pair(GEOMETRY_X,221,INPUT_WIDTH,"Analysis method",method,120)
        for i,(label,value) in enumerate(analysis):pair(GEOMETRY_X,245+24*i,INPUT_WIDTH,label,value,146)
        heading(MATERIAL_X,76,INPUT_WIDTH,"MATERIAL AND LOADING")
        for i,(label,value) in enumerate(material):pair(MATERIAL_X,101+24*i,INPUT_WIDTH,label,value,160)
        heading(704,76,234,"ILLUSTRATION")
        pix=original_illustration(window)
        factor=min(170/pix.width(),144/pix.height())
        iw,ih=pix.width()*factor,pix.height()*factor
        p.drawPixmap(QRectF(704+(234-iw)/2,103+(150-ih)/2,iw,ih),pix,QRectF(pix.rect()))
        line(276)
        result_section(28,"working","WORKING PRESSURE")
        result_section(504,"test","TEST PRESSURE")
    finally:p.end()
    return image
