"""Pressure vessel inspector. Qt rich text format adapted from the ZFL O-ring inspector."""
from html import escape
from dataclasses import dataclass
import math
from pathlib import Path
from dialog_theme import apply_dialog_theme, return_focus_after_selection
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile,QIODevice
from PySide6.QtWidgets import QTextBrowser,QComboBox,QPushButton,QLabel,QTabWidget
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

def _math(text):
    """Escaped, readable equation text; fractions use Qt's HTML table engine."""
    return escape(text).replace('  ', '&nbsp;&nbsp;')


def _math_equation(expression, fraction):
    """Use 10 pt for equations and fractions, matching the dimension inputs."""
    if fraction is None:
        return ('<p style="margin:3px 0 3px 14px;font-size:10pt;color:#242424;">'
                + _math(expression) + '</p>')
    lhs, numer, denom, suffix = fraction
    return ('<table cellspacing="0" cellpadding="0" style="margin-left:13px;">'
            '<tr><td rowspan="3" valign="middle" style="font-size:10pt;">'
            + _math(lhs) + '&nbsp;=&nbsp;</td>'
            '<td align="center" style="font-size:10pt;padding:0 5px;">'
            + _math(numer) + '</td>'
            '<td rowspan="3" valign="middle" style="font-size:10pt;">'
            + '&nbsp;' + _math(suffix) + '</td></tr>'
            '<tr><td><hr style="height:1px;color:#385a78;"/></td></tr>'
            '<tr><td align="center" style="font-size:10pt;padding:0 5px;">'
            + _math(denom) + '</td></tr></table>')


def _section_rule():
    """An understated divider separating the three Inspector sections."""
    return '<hr style="color:#D8E1EA;background-color:#D8E1EA;height:1px;"/>'



@dataclass
class Step:
    title:str
    symbolic:str
    numeric:str
    result:float
    unit:str=""
    symbol_fraction:tuple|None=None
    numeric_fraction:tuple|None=None
    note:str=""

def case_steps(inputs,output,key,places=3):
    c=output[key]
    working=key=="working"
    thick=output["wall_type"]=="Thick Wall"
    external=inputs["pressure_type"]=="external"
    capped=inputs["end_condition"]=="capped"
    od,idd=inputs["od"],inputs["id"]
    ro,ri=od/2,idd/2
    t=ro-ri;R=(ro+ri)/2
    denom=ro**2-ri**2;area=math.pi*denom
    p=c["pressure"];sy=inputs["yield_strength"];F=inputs.get("axial_load",0)
    k=2/3 if working else .9
    d=inputs["derating_factor"] if working else 1.
    n=lambda x:f"{x:.{places}f}"
    # Use exact engine intermediates for the trace. Rounded substitutions
    # are presentation only; result values are checked against the engine.
    steps=[]
    def add(title,sym,num,value,unit="",sf=None,nf=None,note=""):
        steps.append(Step(title,sym,num,value,unit,sf,nf,note))
    def frac(title,lhs,num,den,nnum,nden,value,unit="",suffix="",nsuffix="",note=""):
        add(title,"","",value,unit,(lhs,num,den,suffix),(lhs,nnum,nden,nsuffix),note)
    def check(name,value):
        actual=c[name]
        if actual is None or not math.isclose(value,actual,rel_tol=1e-12,abs_tol=1e-8):
            raise ValueError("Inspector trace does not match calculation: "+name)
        return actual
    dims=[("Outer diameter used",n(od),"in"),
          ("Inner diameter used",n(idd),"in"),
          ("Material yield strength",n(sy),"psi"),("Pressure",n(p),"psi"),
          ("Temperature derating factor (applied)",n(d),""),
          ("Allowable factor","2/3" if working else "0.9",""),
          ("Axial load",n(F),"lbf"),("Pressure direction",inputs["pressure_type"].capitalize(),""),
          ("End configuration",inputs["end_condition"].capitalize(),"")]
    frac("Outer radius","rₒ","OD","2",n(od),"2",ro,"in")
    frac("Inner radius","rᵢ","ID","2",n(idd),"2",ri,"in")
    add("Wall thickness","t = rₒ − rᵢ",f"t = {n(ro)} − {n(ri)}",t,"in")
    frac("Mean radius","R","rₒ + rᵢ","2",f"{n(ro)} + {n(ri)}","2",R,"in")
    frac("Wall ratio and method selection","R/t","R","t",n(R),n(t),output["ratio"],note="Thin wall if R/t > 10; otherwise thick wall. Method selected using the unrounded ratio.")
    if thick:
        add("Lamé denominator","D = rₒ² − rᵢ²",f"D = {n(ro)}² − {n(ri)}²",denom,"in²")
    add("Metal cross-sectional area","A = π × (rₒ² − rᵢ²)",f"A = π × ({n(ro)}² − {n(ri)}²)",area,"in²")
    signed=-p if external else p
    if capped:
        if thick:
            r=ro if external else ri
            z=signed*r**2/denom
            frac("Longitudinal pressure stress","σ₁,P","−P × rₒ²" if external else "P × rᵢ²","D",f"{n(signed)} × {n(r)}²",n(denom),z,"psi")
        else:
            z=signed*R/(2*t)
            frac("Longitudinal pressure stress","σ₁,P","−P × R" if external else "P × R","2 × t",f"{n(signed)} × {n(R)}",f"2 × {n(t)}",z,"psi")
    else:
        z=0.
        add("Longitudinal pressure stress","σ₁,P = 0","σ₁,P = 0",z,"psi",note="Open ends: no longitudinal pressure contribution.")
    axial=F/area
    frac("Axial load stress","σ₁,F","F","A",n(F),n(area),axial,"psi")
    long=check("sigma_long",z+axial)
    add("Total longitudinal stress","σ₁ = σ₁,P + σ₁,F",f"σ₁ = {n(z)} + ({n(axial)})",long,"psi")
    if thick:
        if external:
            hoop=-p*2*ro**2/denom
            frac("Hoop stress (at bore)","σ₂","−2 × P × rₒ²","D",f"−2 × {n(p)} × {n(ro)}²",n(denom),check("sigma_hoop",hoop),"psi")
        else:
            hoop=p*(ro**2+ri**2)/denom
            frac("Hoop stress (at bore)","σ₂","P × (rₒ² + rᵢ²)","D",f"{n(p)} × ({n(ro)}² + {n(ri)}²)",n(denom),check("sigma_hoop",hoop),"psi")
        radial=0. if external else -p
        add("Radial stress (at bore)","σ₃ = 0" if external else "σ₃ = −P","σ₃ = 0" if external else f"σ₃ = −{n(p)}",check("sigma_radial",radial),"psi")
    else:
        hoop=signed*R/t;radial=0.
        frac("Hoop stress","σ₂","−P × R" if external else "P × R","t",f"{n(signed)} × {n(R)}",n(t),check("sigma_hoop",hoop),"psi")
    delta=(long-hoop,hoop-radial,radial-long)
    vm=check("sigma_vm",math.sqrt(.5*sum(v*v for v in delta)))
    add("Von Mises equivalent stress","σᵥ = √[½ × ((σ₁ − σ₂)² + (σ₂ − σ₃)² + (σ₃ − σ₁)²)]",
        f"σᵥ = √[½ × (({n(delta[0])})² + ({n(delta[1])})² + ({n(delta[2])})²)]",vm,"psi",
        note="Substitution uses the three principal-stress differences." if thick else "Radial stress is neglected (σ₃ = 0) in the membrane calculation.")
    av=check("allowable_vm",k*sy*d)
    factor="(2/3)" if working else "0.9"
    add("Allowable Von Mises stress","Sᵥ = k × Sᵧ × f",f"Sᵥ = {factor} × {n(sy)} × {n(d)}",av,"psi",
        note="Temperature derating applies to working pressure only." if working else "Test pressure uses a derating factor of 1.000.")
    uv=check("uf_vm",vm/av)
    frac("Von Mises utilisation","Uᵥ","σᵥ","Sᵥ",n(vm),n(av),uv,note="PASS" if uv<=1 else "FAIL")
    if thick:
        mx,mn=max(long,hoop,radial),min(long,hoop,radial)
        tau=check("tau",(mx-mn)/2)
        frac("Maximum shear stress","τ","σₘₐₓ − σₘᵢₙ","2",f"{n(mx)} − ({n(mn)})","2",tau,"psi")
        at=check("allowable_tau",k*.6*sy*d)
        add("Allowable shear stress","Sτ = k × 0.6 × Sᵧ × f",f"Sτ = {factor} × 0.6 × {n(sy)} × {n(d)}",at,"psi")
        ut=check("uf_tau",tau/at)
        frac("Shear utilisation","Uτ","τ","Sτ",n(tau),n(at),ut,note="PASS" if ut<=1 else "FAIL")
    else:
        assert c["tau"] is None and c["uf_tau"] is None
    return dims,steps

def roark_case_reference(inputs,output):
    capped=inputs["end_condition"]=="capped"
    external=inputs["pressure_type"]=="external"
    if output["wall_type"]=="Thick Wall":
        table=32
        case={(False,False):"1a",(False,True):"1b",(True,False):"1c",(True,True):"1d"}[(external,capped)]
    else:
        table=28
        case="1c" if capped else "1b"
    return f"Roark, 6th Edition, Table {table}, Case {case}"


def html_breakdown(inputs,output,key,places):
    c=output[key];dims,steps=case_steps(inputs,output,key,places)
    status="PASS" if c["uf_vm"]<=1 and (c["uf_tau"] is None or c["uf_tau"]<=1) else "FAIL"
    colour="#18805b" if status=="PASS" else "#bb2b23"
    heading=("Working pressure" if key=="working" else "Test pressure")+": "+f"{c['pressure']:.0f} psi"
    lines=['<html><body style="font-family:Segoe UI,Arial,sans-serif;color:#242424;font-size:10pt;">',
        '<table width="100%" cellspacing="0" cellpadding="0" style="margin:0;">',
        '<tr><td width="78%" valign="middle"><p style="font-size:12pt;color:#164f8a;margin:3px 0 4px 0;"><b>'+escape(heading)+'</b></p></td>',
        '<td align="right" valign="middle"><p style="font-size:12pt;color:'+colour+';margin:3px 0 4px 0;"><b>'+status+'</b></p></td></tr></table>',
        '<p style="font-size:9pt;color:#667c94;margin:4px 0 0 0;">'+escape(output["wall_type"]+(" (Lamé)" if output["wall_type"]=="Thick Wall" else " (Membrane)")+f" | VM utilisation: {c['uf_vm']:.2f}"+(f" | Shear utilisation: {c['uf_tau']:.2f}" if c["uf_tau"] is not None else ""))+'</p>',
        '<p style="font-size:9pt;color:#667c94;margin:0 0 12px 0;">Calculation basis: '+escape(roark_case_reference(inputs,output))+'</p>',
        _section_rule(),'<p style="font-size:10pt;margin:13px 0 18px 0;color:#164f8a;"><b>Input Values</b></p>',
        '<p style="font-size:1pt;margin:0 0 12px 0;">&nbsp;</p>',
        '<table cellspacing="0" cellpadding="3" width="100%" style="font-size:10pt;">']
    for label,value,unit in dims:
        lines.append('<tr><td style="font-size:10pt;">'+escape(label)+'</td><td style="font-size:10pt;" align="right">'+escape(value+(" "+unit if unit else ""))+'</td></tr>')
    lines += ['</table>','<p style="font-size:1pt;margin:0 0 12px 0;">&nbsp;</p>',_section_rule(),
              '<p style="font-size:10pt;margin:13px 0 13px 0;color:#164f8a;"><b>Calculation Breakdown</b></p>']
    for i,s in enumerate(steps,1):
        lines += ['<p style="font-size:10pt;margin:18px 0 7px 0;color:#164f8a;"><b>'+str(i)+'. '+escape(s.title)+'</b></p>',
                  _math_equation(s.symbolic,s.symbol_fraction),
                  '<p style="font-size:9pt;color:#667c94;margin:6px 0 4px 13px;">Substitution</p>',
                  _math_equation(s.numeric,s.numeric_fraction),
                  '<p style="font-size:10pt;margin:7px 0 3px 13px;color:#164f8a;"><b>Result: '+f'{s.result:.{places}f}'+(' '+escape(s.unit) if s.unit else '')+'</b></p>']
        if s.note:
            lines.append('<p style="font-size:9pt;margin:5px 0 12px 13px;color:#667c94;">'+escape(s.note)+'</p>')
    if output["wall_type"]=="Thin Wall":
        lines.append('<p style="font-size:9pt;color:#667c94;margin:12px 0 8px 13px;">Separate shear assessment is not calculated by the existing thin-wall method.</p>')
    if inputs["pressure_type"]=="external":
        lines.append('<p style="font-size:9pt;color:#667c94;margin:12px 0 8px 13px;">External-pressure buckling is not assessed.</p>')
    lines.append('</body></html>')
    return '\n'.join(lines)

def build_inspect_results(inputs,output,parent):
    f=QFile(str(Path(__file__).parent/"ui/inspect_results.ui"))
    if not f.open(QIODevice.OpenModeFlag.ReadOnly):raise RuntimeError("Inspector form missing")
    loader=QUiLoader()
    try:dialog=loader.load(f,parent)
    finally:f.close()
    dialog.setParent(parent,dialog.windowFlags())
    dialog.setWindowIcon(parent.windowIcon())
    dialog.setFont(QFont("Segoe UI",9))
    dialog.setStyleSheet("""
        QPushButton {background:#eaf3fc;color:#144b83;border:1px solid #9ebfe2;border-radius:5px;min-height:24px;padding:2px 8px;font-weight:600;}
        QPushButton:hover {background:#d9ecff;}
        QFrame#inspect_heading_rule {color:#858585;}
        QTabWidget::pane {background:white;border:1px solid #e7e7e7;border-radius:4px;}
        QTabBar::tab {background:#f1f1f1;border:1px solid #e5e5e5;border-top-left-radius:5px;border-top-right-radius:4px;padding:4px 11px;color:#344556;}
        QTabBar::tab:selected {background:white;color:#1b3452;border-bottom-color:white;}
        QTextBrowser {background:white;border:1px solid #e7e7e7;border-radius:4px;color:#242424;}
        QComboBox {background:white;border:1px solid #b9cce1;border-radius:4px;min-height:22px;padding:1px 4px;color:#243d58;}
        QComboBox:focus {border:2px solid #258aca;padding:0px 3px;}
        """)
    controls={}
    for key in ("working","test"):
        precision=dialog.findChild(QComboBox,key+"_precision")
        browser=dialog.findChild(QTextBrowser,key+"_text")
        precision.setMaxVisibleItems(7)
        precision.setFixedSize(210,26)
        precision.addItems([f"{x} DP" for x in range(7)])
        precision.setCurrentIndex(3)
        browser.setOpenExternalLinks(False)
        controls[key]=(precision,browser)
    def redraw(places):
        for precision,browser in controls.values():
            blocked=precision.blockSignals(True);precision.setCurrentIndex(places);precision.blockSignals(blocked)
        for key,(_,browser) in controls.items():
            pos=browser.verticalScrollBar().value()
            html=html_breakdown(inputs,output,key,places)
            basis=getattr(parent,"geometry_basis","")
            if basis.startswith("Physical"):
                note="For diameter/thickness input, both tabs show the same physical geometry governing maximum utilisation. Individual criteria are evaluated at that geometry, not separately maximised."
                html=html.replace("</body>",'<p style="font-size:9pt;color:#667c94;margin:12px 0 8px 13px;">'+escape(note)+'</p></body>')
            browser.setHtml(html)
            browser.verticalScrollBar().setValue(pos)
    for combo, browser in controls.values():
        combo.currentIndexChanged.connect(redraw)
        return_focus_after_selection(combo, browser)
    close=dialog.findChild(QPushButton,"close_inspection")
    close.setFixedSize(106,30);close.clicked.connect(dialog.accept)
    redraw(3)
    apply_dialog_theme(dialog)
    return dialog
