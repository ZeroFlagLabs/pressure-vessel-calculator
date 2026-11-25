"""Pressure Vessel Calculator main interface."""
import sys
from pathlib import Path
from decimal import Decimal as D
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile,QIODevice,QTimer,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtGui import QIcon, QFont, QColor, QPainter, QPen, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import *
from cases import calculate_case
from input_validation import validate_inputs
from geometry_selection import select_geometry
from app_info import APP_TITLE,APP_VERSION,GITHUB_URL
from spin_suffix import protect_suffix
from update_checker import UpdateChecker
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
ICONS=HERE/"resources/icons"
# Fusion renders text 4 px nearer the border than the approved Windows 11 O-Ring style.
INPUT_TEXT_INSET=4
STYLE="""
QWidget#surface {background:#f3f7fb;color:#1b3452;}
QLabel {color:#1b3452;}
QGroupBox {background:#ffffff;border:1px solid #d8e4f0;border-radius:6px;margin-top:13px;padding:5px 7px 5px;font-weight:600;color:#174675;}
QGroupBox::title {subcontrol-origin:margin;subcontrol-position:top left;left:10px;top:2px;padding:0 4px;color:#164f8a;}
QLineEdit,QDoubleSpinBox,QAbstractSpinBox,QComboBox {background:white;border:1px solid #b9cce1;border-radius:4px;min-height:26px;padding:1px 4px;color:#243d58;}
QDoubleSpinBox:disabled {background:#e3e8ee;border-color:#c4cdd8;color:#8190a1;}
QLineEdit:focus,QDoubleSpinBox:focus,QAbstractSpinBox:focus,QComboBox:focus {border:2px solid #258aca;}
QAbstractSpinBox {padding-right:18px;}
QAbstractSpinBox::up-button,QAbstractSpinBox::down-button {subcontrol-origin:padding;width:14px;background:transparent;border:none;right:3px;}
QAbstractSpinBox::up-button {subcontrol-position:top right;top:1px;}
QAbstractSpinBox::down-button {subcontrol-position:bottom right;bottom:1px;}
QDoubleSpinBox#geometry_spin::up-button,QDoubleSpinBox#geometry_spin::down-button {right:1px;}
QAbstractSpinBox::up-arrow {image:url(@ICONS@/spin-chevron-up.png);width:12px;height:8px;}
QAbstractSpinBox::down-arrow {image:url(@ICONS@/spin-chevron-down.png);width:12px;height:8px;}
QAbstractSpinBox::up-arrow:disabled {image:url(@ICONS@/spin-chevron-up-disabled.png);}
QAbstractSpinBox::down-arrow:disabled {image:url(@ICONS@/spin-chevron-down-disabled.png);}
QPushButton {outline:0;background:#eaf3fc;color:#144b83;border:1px solid #9ebfe2;border-radius:5px;min-height:24px;padding:2px 8px;font-weight:600;}
QPushButton:hover {background:#d9ecff;}
QPushButton:disabled {color:#8795a5;background:#eff2f5;}
QPushButton#settings_button {background:transparent;border:1px solid transparent;border-radius:5px;min-height:0px;padding:0px;}
QPushButton#settings_button:hover {background:#e5f1fc;border:1px solid #bfd4e9;}
QPushButton#mode {border-radius:3px;min-height:0;padding:0;font-size:10px;font-weight:600;}
QPushButton:focus {border:1px solid #258aca;}
QPushButton#mode:focus {border:1px solid #258aca;}
QPushButton#mode:checked {background:#176bc0;color:white;border-color:#176bc0;}
QPushButton#mode:disabled {background:#e3e8ee;color:#8190a1;border-color:#c4cdd8;}
QRadioButton#case_radio {color:#1b3452;spacing:5px;}
QLabel#title {font-size:19px;font-weight:700;color:#123b6c;}
QLabel#version {font-size:11px;color:#6c7e94;}
QLabel#muted {font-size:11px;color:#667c94;}
QLabel#metric {font-size:13px;font-weight:600;color:#164f8a;}
QTabBar::tab {padding:6px 10px;background:#eaf3fc;border:1px solid #d8e4f0;}
QTabBar::tab:selected {background:white;color:#123b6c;font-weight:600;}
QTextBrowser {background:white;border:1px solid #d8e4f0;padding:8px;}
""".replace("@ICONS@",ICONS.as_posix())

def text(s="",name=None):
    w=QLabel(s)
    if name:w.setObjectName(name)
    return w

def group(title):
    g=QGroupBox(title); l=QVBoxLayout(g); l.setContentsMargins(8,7,8,7); l.setSpacing(4); return g,l

def nice(n,minimum=3):
    s=format(n,"f")
    if "." not in s:s+="."
    a,b=s.split("."); b=b.rstrip("0")
    return a+"."+b.ljust(minimum,"0")

def format_ratio(value):
    return f'{value:.3f}'

class DimSpin(QDoubleSpinBox):
    def __init__(self):
        super().__init__(); self.setObjectName('geometry_spin'); self.setDecimals(12); self.setRange(0,1000000); self.setSingleStep(.001)
        self.setSuffix(" in"); self.setFixedSize(106,30); self.setKeyboardTracking(True)
        protect_suffix(self)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.lineEdit().setTextMargins(INPUT_TEXT_INSET,0,0,0)
    def wheelEvent(self,event):
        event.ignore()
    def textFromValue(self,v):
        return format(v,".3f") if getattr(self,"derived_display",False) else nice(D(format(v,f'.{self.decimals()}f')))
    def decimal(self):
        return D(str(self.value()))

class LoadSpin(QDoubleSpinBox):
    """Native suffix handling identical to the geometry spin boxes."""
    def __init__(self,unit,step,minimum,maximum,decimals):
        super().__init__()
        self.setDecimals(decimals);self.setRange(-1e12,1e12)
        self.setSingleStep(step);self.setSuffix(" "+unit if unit else "")
        protect_suffix(self)
        self.setFixedSize(106,30);self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.lineEdit().setTextMargins(INPUT_TEXT_INSET,0,0,0)
        self._minimum_display=2 if not unit else 0
        self.setKeyboardTracking(True)
        self.valueChanged.connect(self.inputChanged)
        self.lineEdit().textEdited.connect(self.inputChanged)
        self.editingFinished.connect(self.inputChanged)
    def textFromValue(self,v):
        places=getattr(self,"_minimum_display",0)
        return nice(D(format(v,f".{self.decimals()}f")),places).rstrip(".")
    def wheelEvent(self,event):
        event.ignore()
    def inputChanged(self,*args):
        if hasattr(self,"notify"):self.notify()
    def setText(self,s):
        self.setValue(float(s) if s.strip() else 0)
    def rawText(self):
        return self.cleanText().strip()

class Choice(QWidget):
    def __init__(self,items,changed):
        super().__init__();self.setFixedSize(171,30);self.buttons=QButtonGroup(self);self.buttons.setExclusive(True);self.options={}
        l=QHBoxLayout(self);l.setContentsMargins(0,0,0,0);l.setSpacing(0)
        for i,key in enumerate(items):
            b=CaseRadio(key.capitalize());b.setObjectName("case_radio")
            self.buttons.addButton(b);self.options[key]=b
            if i:
                l.addStretch();b.setFixedWidth(65)
            l.addWidget(b,0,Qt.AlignmentFlag.AlignRight if i else Qt.AlignmentFlag.AlignLeft)
            b.clicked.connect(changed)
            b.toggled.connect(self.update_focus)
    def update_focus(self,*args):
        for b in self.options.values():
            b.setFocusPolicy(Qt.FocusPolicy.StrongFocus if b.isChecked() else Qt.FocusPolicy.ClickFocus)
    def currentText(self):
        return next((k for k,b in self.options.items() if b.isChecked()),"")
    def setCurrentText(self,key):
        self.options[key].click()

class Dimension:
    def __init__(self,name,changed):
        self.name=name; self.mode="pm"; self.derived=False; self._derived_bounds=None; self.changed=changed
        self.label=text(name); self.label.setFixedWidth(100)
        self.a=DimSpin(); self.b=DimSpin()
        self.tags=[]
        for spin,word in ((self.a,"MIN"),(self.b,"MAX")):
            tag=QLabel(word,spin);tag.setGeometry(59,7,28,16)
            tag.setStyleSheet("QLabel { background: transparent; color: #8795a7; border: none; padding: 0px; font-size: 11px; font-weight: 600; }")
            tag.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
            tag.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True);tag.setFocusPolicy(Qt.FocusPolicy.NoFocus);tag.hide();self.tags.append(tag)
        self.a.setAccessibleName(name+" nominal or minimum"); self.b.setAccessibleName(name+" tolerance or maximum")
        self.pm=QPushButton("±"); self.limits=QPushButton("Limits")
        self.buttons=QButtonGroup(); self.buttons.setExclusive(True)
        for w in [self.pm,self.limits]:
            w.setObjectName("mode"); w.setFixedSize(46,26); w.setCheckable(True); w.setFocusPolicy(Qt.FocusPolicy.NoFocus); self.buttons.addButton(w)
        self.pm.setChecked(True)
        self.pm.clicked.connect(lambda:self.select_mode("pm")); self.limits.clicked.connect(lambda:self.select_mode("limits"))
        self.a.valueChanged.connect(changed); self.b.valueChanged.connect(changed)
        self.widget=QWidget(); l=QHBoxLayout(self.widget); l.setContentsMargins(0,0,0,0); l.setSpacing(5)
        l.addWidget(self.label); l.addWidget(self.a)
        mid=QHBoxLayout(); mid.setSpacing(0); mid.addWidget(self.pm); mid.addWidget(self.limits); l.addLayout(mid); l.addWidget(self.b); l.addStretch()
        self.tooltips()
    def tooltips(self):
        self.a.setToolTip("Nominal dimension" if self.mode=="pm" else "Minimum dimension")
        self.b.setToolTip("Symmetrical tolerance" if self.mode=="pm" else "Maximum dimension")
        for spin,tag in zip((self.a,self.b),self.tags):
            spin.lineEdit().setTextMargins(INPUT_TEXT_INSET,0,21 if self.mode=="limits" else 0,0)
            tag.setVisible(self.mode=="limits");tag.raise_()
    def present(self):return self.a.value()!=0 or self.b.value()!=0
    def bounds(self):
        if self.derived and self._derived_bounds is not None:return self._derived_bounds
        a,b=self.a.decimal(),self.b.decimal()
        if not self.present():return None
        if self.mode=="pm":
            if a<=0 or a-b<=0:raise ValueError(self.name+": nominal minus tolerance must be positive.")
            return a-b,a+b
        if a<=0 or b<a:raise ValueError(self.name+": enter positive minimum and maximum ≥ minimum.")
        return a,b
    def put(self,a,b):
        self.a.blockSignals(True);self.b.blockSignals(True);self.a.setValue(float(a));self.b.setValue(float(b));self.a.blockSignals(False);self.b.blockSignals(False)
    def put_bounds(self,lo,hi):
        self.put((lo+hi)/2,(hi-lo)/2) if self.mode=="pm" else self.put(lo,hi)
    def select_mode(self,mode):
        """A mouse mode selection ends editing and clears the input highlight."""
        window=self.a.window()
        focused=QApplication.focusWidget()
        if focused is not None and focused.window() is window:
            focused.clearFocus()
        self.switch(mode)
        for editor in window.findChildren(QLineEdit):
            editor.deselect()
    def switch(self,mode):
        if mode==self.mode:return
        try:
            # In positive-only geometry fields, a single zero endpoint is
            # an incomplete entry. Normalise only when explicitly switching.
            a,b=self.a.decimal(),self.b.decimal()
            if self.mode=="limits" and mode=="pm" and not self.derived and ((a==0 and b>0) or (b==0 and a>0)):
                entered=max(a,b);bounds=(entered,entered)
            else:
                bounds=self.bounds()
        except ValueError:
            (self.pm if self.mode=="pm" else self.limits).setChecked(True);return
        if bounds and not self.derived:
            vals=((bounds[0]+bounds[1])/2,(bounds[1]-bounds[0])/2) if mode=="pm" else bounds
            # Refuse conversions that would silently clip or lose precision.
            if any(v<0 or v>D(str(spin.maximum())) or D(str(round(float(v),spin.decimals())))!=v for v,spin in zip(vals,(self.a,self.b))):
                (self.pm if self.mode=="pm" else self.limits).setChecked(True)
                self.a.window().statusBar().showMessage("Dimension conversion exceeds supported input range or precision.")
                return
        self.mode=mode;(self.pm if mode=="pm" else self.limits).setChecked(True);self.tooltips()
        if bounds:self.put_bounds(*bounds)
        self.changed()
    def lock(self,state):
        self.derived=state
        if not state:self._derived_bounds=None
        for spin in (self.a,self.b):
            spin.derived_display=state
            spin.lineEdit().setText(spin.textFromValue(spin.value())+spin.suffix())
        self.label.setText(self.name+(" *" if state else ""))
        self.label.setToolTip("Automatically derived; clear an entered dimension to edit this one." if state else "")
        for w in [self.a,self.b]:
            w.setEnabled(not state)
            if state:
                lo,hi=self._derived_bounds
                vals=((lo+hi)/2,(hi-lo)/2) if self.mode=="pm" else (lo,hi)
                w.setToolTip("Derived value (full precision): "+nice(vals[0 if w is self.a else 1])+" in")
        if not state:self.tooltips()
        for w in [self.pm,self.limits]:w.setEnabled(True)
    def clear(self):
        self.put(0,0);self.lock(False)

class MethodDiagram(QLabel):
    """Original method-specific stress schematics."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(150,122)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip("Method illustration only; not specific to pressure direction or end configuration. External-pressure buckling is not assessed.")
        self.method=None
        self.images={}
        for method,name in (("Thin Wall","thin.png"),("Thick Wall","thick.png")):
            source=QPixmap(str(HERE/"resources/images"/name))
            if source.isNull():
                raise RuntimeError("Missing method illustration: "+name)
            # Trim transparent margins while preserving the original artwork.
            img=source.toImage()
            if img.hasAlphaChannel():
                left,top,right,bottom=img.width(),img.height(),-1,-1
                for y in range(img.height()):
                    for x in range(img.width()):
                        if img.pixelColor(x,y).alpha()>16:
                            left=min(left,x);top=min(top,y);right=max(right,x);bottom=max(bottom,y)
                if right>=left and bottom>=top:
                    source=source.copy(left,top,right-left+1,bottom-top+1)
            self.images[method]=source.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    def set_method(self,method):
        if method==self.method:return
        self.method=method
        if method in self.images:
            self.setPixmap(self.images[method])
        else:self.clear()

class CaseRadio(QRadioButton):
    """No mouse-click focus rectangle; retain native keyboard focus cue."""
    def __init__(self,label):
        super().__init__(label)
        self.keyboard_focus=False
    def focusInEvent(self,event):
        self.keyboard_focus=event.reason() in (Qt.FocusReason.TabFocusReason,Qt.FocusReason.BacktabFocusReason,Qt.FocusReason.ShortcutFocusReason)
        super().focusInEvent(event)
    def keyPressEvent(self,event):
        self.keyboard_focus=True
        super().keyPressEvent(event)
        self.update()
    def mousePressEvent(self,event):
        self.keyboard_focus=False
        super().mousePressEvent(event)
        self.update()
    def paintEvent(self,event):
        option=QStyleOptionButton()
        self.initStyleOption(option)
        if not self.keyboard_focus:
            option.state &= ~QStyle.StateFlag.State_HasFocus
        painter=QStylePainter(self)
        painter.drawControl(QStyle.ControlElement.CE_RadioButton,option)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(str(ICONS/"icon.ico")))
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint,False)
        self.ready=False; self.result=None; self.raw=None; self.used=None;self.derived=None
        self.update_checker=UpdateChecker(self)
        surface=QWidget();surface.setObjectName("surface");surface.setStyleSheet(STYLE);self.setCentralWidget(surface)
        outer=QVBoxLayout(surface);outer.setContentsMargins(10,10,10,4);outer.setSpacing(4)
        header=QHBoxLayout();header.setSpacing(10);header.addWidget(text("Pressure Vessel Calculator","title"));header.addStretch();header.addWidget(text("v"+APP_VERSION,"version"))
        gear=QPushButton();gear.setObjectName("settings_button");gear.setFixedSize(27,27);gear.setIcon(QIcon(str(ICONS/"settings-gear.png")));gear.setIconSize(QSize(18,18));gear.setToolTip("Settings, engineering references and application information");gear.clicked.connect(self.settings);header.addWidget(gear);outer.addLayout(header)
        self.body=QWidget();body=QGridLayout(self.body);body.setContentsMargins(0,0,0,0);body.setHorizontalSpacing(8);body.setVerticalSpacing(4);outer.addWidget(self.body)
        geo,gl=group("Geometry");gl.setContentsMargins(8,7,4,7); self.dims={k:Dimension(n,self.changed) for k,n in [("od","Outer diameter"),("id","Inner diameter"),("t","Wall thickness")]}
        for row in self.dims.values():gl.addWidget(row.widget)
        self.geom_hint=text("Enter any two dimensions; the third is derived.","muted");self.geom_hint.setWordWrap(True);self.geom_hint.setFixedHeight(18);gl.addSpacing(4);gl.addWidget(self.geom_hint)
        self.analysis,al=group("Geometry and analysis")
        self.diagram=MethodDiagram()
        self.method=text("Analysis method: —","metric")
        self.thickness=text("Wall thickness used: —  |  R/t: —","muted")
        analysis_row=QHBoxLayout();analysis_row.setContentsMargins(0,0,0,0);analysis_row.setSpacing(8)
        analysis_text=QVBoxLayout();analysis_text.setSpacing(6);analysis_text.addStretch()
        analysis_text.addWidget(self.method);analysis_text.addWidget(self.thickness);analysis_text.addStretch()
        analysis_row.addLayout(analysis_text,1);analysis_row.addWidget(self.diagram,0,Qt.AlignmentFlag.AlignVCenter);al.addLayout(analysis_row)
        load,ll=group("Material and loading");ll.setContentsMargins(8,7,4,7);f=QFormLayout();f.setHorizontalSpacing(5);f.setVerticalSpacing(4);f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint);self.fields={}
        for key,name,unit,step,lo,hi,decimals in [
            ("yield_strength","Material yield","psi",1000,0,1e12,6),
            ("derating_factor","Temp. derating","",.01,0,1,9),
            ("working_pressure","Working pressure","psi",500,0,1e12,6),
            ("test_pressure","Test pressure","psi",500,0,1e12,6),
            ("axial_load","Axial load","lbf",1000,-1e12,1e12,6)]:
            w=LoadSpin(unit,step,lo,hi,decimals);w.notify=self.changed;self.fields[key]=w;lab=text(name);lab.setFixedWidth(100);holder=QWidget();holder.setFixedSize(108,30);hl=QHBoxLayout(holder);hl.setContentsMargins(0,0,2,0);hl.setSpacing(0);hl.addWidget(w);f.addRow(lab,holder)
            if key=="derating_factor":w.setToolTip("Temperature derating factor")
            if key=="axial_load":w.setToolTip("Positive: tension; negative: compression")
        for key,name,items in [("pressure_type","Pressure direction",["external","internal"]),("end_condition","End configuration",["capped","open"])]:
            w=Choice(list(reversed(items)) if key=="pressure_type" else items,self.changed);self.fields[key]=w
        panel=QHBoxLayout();panel.setContentsMargins(0,0,0,0);panel.setSpacing(5)
        left=QWidget();f.setContentsMargins(0,0,0,0);left.setLayout(f);panel.addWidget(left,0)
        rule=QFrame();rule.setFrameShape(QFrame.Shape.VLine);rule.setFixedWidth(1);rule.setStyleSheet("background:#e4ebf3;border:0;");panel.addSpacing(12);panel.addWidget(rule);panel.addSpacing(11)
        right=QVBoxLayout();right.setContentsMargins(0,0,0,0);right.setSpacing(2);right.addStretch()
        for key,title in [("pressure_type","Pressure direction"),("end_condition","End configuration")]:
            lab=text(title);lab.setStyleSheet("font-weight:600;color:#174675;")
            right.addWidget(lab);right.addWidget(self.fields[key])
            if key=="pressure_type":right.addSpacing(10)
        right.addStretch()
        panel.addLayout(right,0);panel.addStretch();ll.addLayout(panel);ll.addStretch()
        cards=QWidget();cl=QHBoxLayout(cards);cl.setContentsMargins(0,0,0,0);cl.setSpacing(8);self.card_values=[]
        for title in ["Working pressure","Test pressure"]:
            g,l=group(title);g.setMinimumWidth(183);form=QGridLayout();form.setHorizontalSpacing(4);form.setVerticalSpacing(0);vals=[]
            for i,name in enumerate(["Pressure","Longitudinal","Hoop","Radial","Von Mises","VM utilisation","Shear","Shear utilisation"]):
                x=text(name);v=text("—");v.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                form.addWidget(x,i,0);form.addWidget(v,i,1);form.setRowStretch(i,1);vals.append(v)
            form.setColumnStretch(1,1);l.addLayout(form,1);cl.addWidget(g);self.card_values.append(vals)
        body.addWidget(geo,0,0);body.addWidget(self.analysis,0,1);body.addWidget(load,1,0);body.addWidget(cards,1,1)
        body.setColumnStretch(0,1);body.setColumnStretch(1,1)
        for box in (geo,load,self.analysis,cards):box.setFixedWidth(446)
        self.frames=(geo,load,self.analysis,cards)
        self.statusBar().setSizeGripEnabled(False);self.statusBar().setFixedHeight(21);self.statusBar().setStyleSheet("QStatusBar {background:#f0f0f0;color:#000000;}");self.statusBar().setFont(QFont("Segoe UI",9))
        footer=QHBoxLayout();footer.setSpacing(8)
        self.inspect_button=QPushButton("Inspect results");self.inspect_button.clicked.connect(self.inspect)
        reset=QPushButton("Reset dimensions");reset.clicked.connect(self.reset)
        self.copy_button=QPushButton("Copy snapshot");self.copy_button.clicked.connect(self.copy)
        self.save_button=QPushButton("Save PNG...");self.save_button.clicked.connect(self.save)
        for w in [self.inspect_button,reset,self.copy_button,self.save_button]:w.setFixedWidth(112)
        footer.addWidget(self.inspect_button);footer.addWidget(reset);footer.addStretch();footer.addWidget(self.copy_button);footer.addWidget(self.save_button);outer.addLayout(footer)
        self.startup_loads={"yield_strength":"0","derating_factor":"1","working_pressure":"0","test_pressure":"0","axial_load":"0"}
        for k,v in self.startup_loads.items():self.fields[k].setText(v)
        self.fields["pressure_type"].setCurrentText("internal");self.fields["end_condition"].setCurrentText("capped")
        for button in self.findChildren(QPushButton):button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sequence=[spin for d in self.dims.values() for spin in (d.a,d.b)]
        sequence.extend(self.fields[k] for k in ("yield_strength","derating_factor","working_pressure","test_pressure","axial_load"))
        for key in ("pressure_type","end_condition"):sequence.extend(self.fields[key].options.values())
        for current,following in zip(sequence,sequence[1:]):self.setTabOrder(current,following)
        self.ready=True;self.changed();self.setFixedSize(self.sizeHint())
        self.update_checker.state_changed.connect(self.update_notice)
        # Action buttons are intentionally absent from the data-entry Tab chain.
        self.shortcuts=[]
        for key,action in (("Ctrl+I",self.inspect),("Ctrl+R",self.reset),("Ctrl+C",self.copy),("Ctrl+Shift+S",self.save),("Ctrl+,",self.settings)):
            if key=="Ctrl+C":continue # preserve native text copying
            sh=QShortcut(QKeySequence(key),self);sh.activated.connect(action);self.shortcuts.append(sh)
        sh=QShortcut(QKeySequence("Ctrl+Shift+C"),self);sh.activated.connect(self.copy);self.shortcuts.append(sh)
        self.inspect_button.setToolTip("Inspect results (Ctrl+I)")
        self.copy_button.setToolTip("Copy snapshot (Ctrl+Shift+C)")
        self.save_button.setToolTip("Save PNG (Ctrl+Shift+S)")
        reset.setToolTip("Reset dimensions (Ctrl+R)")
        gear.setToolTip("Settings (Ctrl+,)")

    def geometry_bounds(self):
        if self.derived:
            other=[k for k in self.dims if k!=self.derived]
            if not all(self.dims[k].present() for k in other):
                self.dims[self.derived].clear();self.derived=None
        active=[k for k,r in self.dims.items() if k!=self.derived and r.present()]
        if len(active)!=2:return None
        bounds={k:self.dims[k].bounds() for k in active}
        target=next(k for k in self.dims if k not in active)
        if target=="t":
            a,b=bounds["od"];c,d=bounds["id"];lo,hi=(a-d)/2,(b-c)/2
        elif target=="id":
            a,b=bounds["od"];c,d=bounds["t"];lo,hi=a-2*d,b-2*c
        else:
            a,b=bounds["id"];c,d=bounds["t"];lo,hi=a+2*c,b+2*d
        if lo<=0:raise ValueError("Derived "+self.dims[target].name+" is not positive.")
        if hi>D(str(self.dims[target].a.maximum())):raise ValueError("Derived dimension exceeds supported input range.")
        bounds[target]=(lo,hi);self.derived=target;self.dims[target]._derived_bounds=(lo,hi);self.dims[target].put_bounds(lo,hi);self.dims[target].lock(True)
        od,idd=bounds["od"][0],bounds["id"][1]
        if target=="t" and od<=idd:raise ValueError("OD min must exceed ID max on the v1.3 calculation basis.")
        return bounds,od,idd
    def changed(self,*args):
        if not self.ready:return
        self.result=None;self.raw=None;self.used=None
        self.diagram.set_method(None);self.thickness.setToolTip('')
        self.method.setText("Analysis method: —");self.thickness.setText("Wall thickness used: —  |  R/t: —")
        try:
            g=self.geometry_bounds()
            if not g:
                self.geom_hint.setText("Enter any two dimensions; the third is derived.")
                raise ValueError("Enter two geometry dimensions.")
            bounds,od,idd=g
            self.geom_hint.setText(f"* {self.dims[self.derived].name} automatically derived.")
            raw={k:(w.rawText() if isinstance(w,LoadSpin) else w.currentText()) for k,w in self.fields.items()}
            self.raw,self.result,self.geometry_basis=select_geometry(bounds,self.derived,raw)
            od,idd=self.raw["od"],self.raw["id"];self.used=(od,idd)
            self.thickness.setToolTip(f"Governing OD: {od:.9g} in; ID: {idd:.9g} in. "+self.geometry_basis)
            self.method.setText("Analysis method: "+self.result["wall_type"]+(" (Lamé)" if self.result["wall_type"]=="Thick Wall" else " (Membrane)"))
            self.diagram.set_method(self.result["wall_type"])
            self.thickness.setText(f"Wall thickness used: {(od-idd)/2:.3f} in  |  R/t: {format_ratio(self.result['ratio'])}")
            self.statusBar().showMessage("Calculation complete. Verify material and loading inputs.")
        except (ValueError,ArithmeticError) as e:
            self.statusBar().showMessage(str(e).replace("\n","  |  "))
            if self.used is None:
                if self.derived and not all(self.dims[k].present() for k in self.dims if k!=self.derived):self.dims[self.derived].put(0,0)
                self.geom_hint.setText("Enter any two dimensions; the third is derived." if not self.derived else "* Derived dimension • check entered dimensions")
        self.diagram.update();self.render()
    def has_startup_loads(self):
        return all(self.fields[k].value()==float(v) for k,v in self.startup_loads.items())
    def render(self):
        for idx,key in enumerate(["working","test"]):
            d=self.result[key] if self.result else None
            if d:
                state=lambda u:f"{u:.2f} ({'PASS' if u<=1 else 'FAIL'})"
                v=[f"{d['pressure']:.0f}",f"{d['sigma_long']:.0f}",f"{d['sigma_hoop']:.0f}",f"{d['sigma_radial']:.0f}" if self.result["wall_type"]=="Thick Wall" else "—",f"{d['sigma_vm']:.0f}",state(d["uf_vm"]),f"{d['tau']:.0f}" if d["tau"] is not None else "—",state(d["uf_tau"]) if d["tau"] is not None else "—"]
            else:v=["—"]*8
            if d:
                for i in (0,1,2,3,4,6):
                    if v[i]!="—":v[i]+=" psi"
            for w,s in zip(self.card_values[idx],v):
                w.setText(s);w.setMinimumWidth(72);w.setStyleSheet("color:#18763c;font-weight:600" if "PASS" in s else "color:#b32632;font-weight:600" if "FAIL" in s else "color:#1b3452")
        for w in [self.inspect_button,self.copy_button,self.save_button]:w.setEnabled(self.result is not None)
    def reset(self):
        self.ready=False
        try:
            for row in self.dims.values():
                row.clear()
                row.switch('pm')
            self.derived=None
        finally:
            self.ready=True
        self.changed()
    def sample(self):
        self.reset();self.dims["od"].put(D("6"),D(".003"));self.dims["id"].put(D("4"),D(".002"))
        for k,v in [("yield_strength","75000"),("working_pressure","10000"),("test_pressure","15000")]:self.fields[k].setText(v)
        self.fields["pressure_type"].setCurrentText("internal");self.fields["end_condition"].setCurrentText("capped");self.changed()
    def make_settings(self):
        f=QFile(str(HERE/"ui/settings_dialog.ui"))
        if not f.open(QIODevice.OpenModeFlag.ReadOnly):raise RuntimeError("Settings form missing")
        try:d=QUiLoader().load(f,self)
        finally:f.close()
        d.setWindowIcon(self.windowIcon())
        d.resize(526,552)
        d.setStyleSheet("""
            QPushButton { background:#eaf3fc; color:#144b83; border:1px solid #9ebfe2; border-radius:5px; min-height:24px; padding:2px 8px; font-weight:600; }
            QPushButton:hover { background:#d9ecff; }
            QPushButton:disabled { color:#8795a5; background:#eff2f5; }
            QFrame#settings_heading_rule { color:#858585; }
            QTabWidget::pane { background:white; border:1px solid #e7e7e7; border-radius:4px; }
            QTabBar::tab { background:#f1f1f1; border:1px solid #e5e5e5; border-top-left-radius:5px; border-top-right-radius:5px; padding:4px 11px; color:#344556; }
            QTabBar::tab:selected { background:white; color:#1b3452; border-bottom-color:white; }
        """)
        d.setWindowModality(Qt.WindowModality.ApplicationModal)
        d.buttons.button(QDialogButtonBox.StandardButton.Close).setFixedWidth(112)
        d.buttons.rejected.connect(d.reject)
        checker=self.update_checker
        d.check_on_launch.setChecked(checker.enabled())
        d.check_on_launch.toggled.connect(checker.set_enabled)
        d.check_now_button.clicked.connect(checker.check)
        d.github_link.setText(f'<a href="{GITHUB_URL}">Project on GitHub</a>')
        d.github_link.setOpenExternalLinks(True)
        def refresh():
            d.update_status.setText(checker.status)
            d.check_now_button.setEnabled(checker._reply is None)
            d.open_release_button.setEnabled(checker.release_url is not None)
        def open_release():
            if checker.release_url:QDesktopServices.openUrl(QUrl(checker.release_url))
        def disconnect(*_):
            try:checker.state_changed.disconnect(refresh)
            except (RuntimeError,TypeError):pass
        d.open_release_button.clicked.connect(open_release)
        checker.state_changed.connect(refresh);d.finished.connect(disconnect);refresh()
        return d
    def update_notice(self):
        if self.update_checker.release_url:self.statusBar().showMessage(self.update_checker.status)
    def settings(self):
        d=self.make_settings();d.exec()
    def make_inspector(self):
        if not self.result:return None
        from inspect_results import build_inspect_results
        return build_inspect_results(self.raw,self.result,self)
    def inspect(self):
        d=self.make_inspector()
        if d is not None:d.exec()
    def snapshot(self):
        from snapshot import render_snapshot
        return render_snapshot(self)
    def copy(self):
        if not self.result:return
        try:
            QApplication.clipboard().setPixmap(self.snapshot())
        except (ValueError,OSError,RuntimeError) as exc:
            QMessageBox.warning(self,"Copy snapshot",str(exc));return
        self.statusBar().showMessage("Calculation snapshot copied to clipboard.",5000)
    def save(self):
        if not self.result:return
        path,_=QFileDialog.getSaveFileName(self,"Save snapshot","Pressure Vessel Calculator.png","PNG (*.png)")
        if path:
            if not path.lower().endswith(".png"):path+=".png"
            try:
                if not self.snapshot().save(path,"PNG"):raise OSError("Unable to save image.")
            except (ValueError,OSError,RuntimeError) as exc:
                QMessageBox.warning(self,"Save PNG",str(exc));return
            self.statusBar().showMessage("Snapshot saved: "+path,5000)

def main():
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ZeroFlagLabs.PressureVesselCalculator")
    app=QApplication(sys.argv);app.setStyle("Fusion");app.setApplicationName(APP_TITLE)
    app.setWindowIcon(QIcon(str(ICONS/"icon.ico")))
    w=MainWindow();w.show()
    if "--self-test" in sys.argv:
        from runtime_check import run
        return run(app,w)
    QTimer.singleShot(0,w.update_checker.check_on_launch)
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
