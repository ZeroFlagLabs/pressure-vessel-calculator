from pathlib import Path
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QDialog
from PySide6.QtTest import QTest

def measure(w,cases):
    w.show();QTest.qWait(80)
    screen=w.screen().availableGeometry()
    print("screen",screen.getRect(),"DPR",w.devicePixelRatioF(),flush=True)
    failures=[];count=0
    for px,py in ((.5,.5),(.27,.36),(.73,.66),(0,0),(1,1)):
        wg=w.frameGeometry()
        x=round(screen.left()+px*screen.width()-wg.width()/2)
        y=round(screen.top()+py*screen.height()-wg.height()/2)
        w.move(max(screen.left(),min(x,screen.right()-wg.width()+1)),max(screen.top(),min(y,screen.bottom()-wg.height()+1)))
        QTest.qWait(60)
        for name,fn in cases:
            closed=[]
            def capture():
                d=app.activeModalWidget()
                if not isinstance(d,QDialog):
                    ds=[z for z in app.topLevelWidgets() if isinstance(z,QDialog) and z.isVisible()]
                    d=ds[-1] if ds else None
                if d is None:
                    failures.append((name,"NO DIALOG"));return
                try:
                    a=w.frameGeometry();b=d.frameGeometry()
                    tx=max(screen.left(),min(a.x()+(a.width()-b.width())//2,screen.right()+1-b.width()))
                    ty=max(screen.top(),min(a.y()+(a.height()-b.height())//2,screen.bottom()+1-b.height()))
                    dx=b.x()-tx;dy=b.y()-ty
                    print(name,"parent",a.getRect(),"dialog",b.getRect(),"target error",dx,dy,"onscreen",screen.contains(b),flush=True)
                    if abs(dx)>1 or abs(dy)>1 or not screen.contains(b):failures.append((name,dx,dy))
                finally:
                    closed.append(d); d.reject()
            QTimer.singleShot(120,capture)
            fn();count+=1
            for d in closed: d.deleteLater()
            QTest.qWait(20)
    w.close()

    assert not failures,failures
    print("PASS:",count,"dialogue placements",flush=True)

if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
    from main import MainWindow
    app=QApplication([]);app.setStyle("Fusion");w=MainWindow()
    w.sample()
    measure(w,[("Settings",w.settings),("Inspect results",w.inspect)])
