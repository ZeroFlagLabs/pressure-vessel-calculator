from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from main import MainWindow
from PySide6.QtWidgets import QApplication,QAbstractSpinBox
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from decimal import Decimal as D
a=QApplication([]);a.setStyle("Fusion");w=MainWindow();w.show();w.activateWindow();QTest.qWait(100)
def chain():
    seq=[spin for k,d in w.dims.items() if k!=w.derived for spin in (d.a,d.b)]
    seq += [w.fields[k] for k in ("yield_strength","derating_factor","working_pressure","test_pressure","axial_load")]
    seq += [next(b for b in w.fields[k].options.values() if b.isChecked()) for k in ("pressure_type","end_condition")]
    def target():
        f=a.focusWidget()
        while f and f not in seq:f=f.parentWidget()
        return f
    seq[0].setFocus();a.processEvents()
    for i in range(len(seq)):
        assert target() is seq[i],(i,target(),seq[i],w.derived)
        QTest.keyClick(a.focusWidget(),Qt.Key.Key_Tab);a.processEvents()
    assert target() is seq[0]
    for i in reversed(range(len(seq))):
        QTest.keyClick(a.focusWidget(),Qt.Key.Key_Backtab,Qt.KeyboardModifier.ShiftModifier);a.processEvents()
        assert target() is seq[i],(i,target(),seq[i])
    return len(seq)
count=chain()
for pair in (("od","id"),("od","t"),("id","t")):
    w.reset();w.ready=False
    for k,v in (("yield_strength","75000"),("working_pressure","10000"),("test_pressure","15000")):w.fields[k].setText(v)
    vals={"od":D("10"),"id":D("8"),"t":D("1")}
    for k in pair:w.dims[k].put(vals[k],0)
    w.ready=True;w.changed()
    assert w.result
    for mode in ("pm","limits"):
        w.dims[pair[0]].switch(mode)
        w.dims[pair[1]].switch("limits" if mode=="pm" else "pm")
        count+=chain()
print("Forward and reverse real Tab events passed across 7 geometry/mode states:",count,"focus positions each direction.")
w.close()
