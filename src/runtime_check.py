"""Runtime checks usable in the source app and the frozen EXE."""
import sys,json,traceback
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime
from decimal import Decimal as D
from unittest.mock import patch
from PySide6.QtCore import Qt,QEventLoop,QTimer,QSettings
from PySide6.QtWidgets import QApplication,QComboBox,QTextBrowser,QFileDialog
from PySide6.QtGui import QPixmap
from cases import calculate_case
from app_info import APP_VERSION
from inspect_results import case_steps
from snapshot import render_snapshot,report_data
import update_checker

def run(app,w):
    report={}
    output=Path(sys.argv[sys.argv.index("--self-test-output")+1]) if "--self-test-output" in sys.argv else None
    try:
        app.processEvents()
        assert (w.width(),w.height())==(920,471)
        assert w.result is None and not w.inspect_button.isEnabled()
        assert not w.windowIcon().isNull()
        expected_startup={"yield_strength":0,"working_pressure":0,"test_pressure":0,"derating_factor":1,"axial_load":0}
        assert all(w.fields[k].value()==v for k,v in expected_startup.items())
        assert w.has_startup_loads()
        assert all(not w.dims[k].present() for k in ("od","id","t"))
        assert not w.copy_button.isEnabled() and not w.save_button.isEnabled()
        assert "examples" not in w.statusBar().currentMessage()
        if output:w.grab().save(str(output.with_name(output.stem+"_startup.png")))
        w.dims["od"].a.setValue(10);w.dims["id"].a.setValue(8)
        assert w.result is None and not w.inspect_button.isEnabled()
        assert not w.copy_button.isEnabled() and not w.save_button.isEnabled()
        # Zero pressure remains a valid engineering input once yield and geometry are supplied.
        w.fields["yield_strength"].setValue(75000)
        assert w.result==calculate_case(dict(od=10,id=8,yield_strength=75000,working_pressure=0,test_pressure=0,derating_factor=1,axial_load=0,pressure_type="internal",end_condition="capped"))
        w.reset()
        assert w.fields["yield_strength"].value()==75000 and w.result is None
        report["startup_defaults"]="passed"
        # The effective extra inset must persist through conversions, derived
        # disabled fields and reset, while the right-hand tag space stays intact.
        def check_insets():
            for dim in w.dims.values():
                for spin in (dim.a,dim.b):
                    margins=spin.lineEdit().textMargins()
                    assert margins.left()==4 and margins.right()==(21 if dim.mode=="limits" else 0)
            for key in expected_startup:
                assert w.fields[key].lineEdit().textMargins().left()==4
        check_insets()
        w.sample()
        check_insets()
        for dim in w.dims.values():dim.switch("limits")
        check_insets()
        if output:w.grab().save(str(output.with_name(output.stem+"_limits.png")))
        for dim in w.dims.values():dim.switch("pm")
        check_insets()
        w.reset();check_insets()
        # Restore loading defaults before the existing sample and calculation checks.
        for key,value in expected_startup.items():w.fields[key].setValue(value)
        report["input_padding"]="passed"
        assert not (w.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint)
        with TemporaryDirectory() as tmp:
            temp=Path(tmp);w.update_checker.prefs=QSettings(str(temp/"settings.ini"),QSettings.Format.IniFormat)
            w.update_checker.set_enabled(False)
            assert not w.update_checker.enabled()
            w.update_checker.set_enabled(True)
            assert w.update_checker.enabled()
            w.sample()
            assert w.raw["od"]==5.997 and w.raw["id"]==4.002 and w.dims["t"].bounds()==(D(".9975"),D("1.0025"))
            assert w.result==calculate_case(w.raw)
            w.dims["t"].limits.click();assert w.dims["t"].bounds()==(D(".9975"),D("1.0025"))
            w.dims["od"].limits.click();assert w.dims["od"].bounds()==(D("5.997"),D("6.003"))
            w.dims["od"].pm.click();assert w.dims["od"].bounds()==(D("5.997"),D("6.003"))
            w.reset();w.dims["od"].limits.click();w.dims["od"].a.setValue(6);assert w.result is None
            w.dims["od"].pm.click();assert w.dims["od"].a.value()==6 and w.dims["od"].b.value()==0
            w.reset();w.dims["od"].a.setValue(10);w.dims["t"].a.setValue(1);w.dims["t"].b.setValue(.005)
            assert w.result and w.derived=="id" and abs((w.raw["od"]-w.raw["id"])/2-.995)<1e-12
            assert w.raw["od"]==10
            for key in ("working","test"):case_steps(w.raw,w.result,key)
            assert "Used OD" not in report_data(w)[0][0][0] # data remains geometry input, used pair separately printed
            assert not render_snapshot(w).isNull()
            w.reset();w.dims["id"].a.setValue(8);w.dims["t"].a.setValue(1);w.dims["t"].b.setValue(.005)
            assert w.result and w.derived=="od" and abs((w.raw["od"]-w.raw["id"])/2-.995)<1e-12
            count=0
            for od,id_ in ((10,8),(10,9.8),(21,19)):
                for pt in ("internal","external"):
                    for ends in ("open","capped"):
                        for load in (-25000,0,25000):
                            w.reset();w.ready=False
                            w.dims["od"].put(D(str(od)),0);w.dims["id"].put(D(str(id_)),0)
                            w.fields["pressure_type"].setCurrentText(pt);w.fields["end_condition"].setCurrentText(ends)
                            w.fields["axial_load"].setValue(load);w.fields["derating_factor"].setValue(.85)
                            w.ready=True;w.changed()
                            assert w.result==calculate_case(dict(od=od,id=id_,pressure_type=pt,end_condition=ends,axial_load=load,derating_factor=.85,yield_strength=75000,working_pressure=10000,test_pressure=15000))
                            for key in ("working","test"):case_steps(w.raw,w.result,key)
                            count+=1
            report["runtime_geometry_cases"]=count
            w.reset();w.dims["od"].a.setValue(10);w.dims["id"].a.setValue(8)
            w.fields["pressure_type"].setCurrentText("internal");w.fields["end_condition"].setCurrentText("capped")
            w.fields["derating_factor"].setValue(1);w.fields["axial_load"].setValue(0)
            pix=render_snapshot(w,datetime(2026,11,24,21))
            assert (pix.width(),pix.height())==(1472,912)
            dest=temp/"export.png"
            with patch("snapshot.datetime") as clock:
                clock.now.return_value=datetime(2026,11,24,21)
                w.copy_button.click();app.processEvents()
                assert QApplication.clipboard().pixmap().toImage()==pix.toImage()
                with patch.object(QFileDialog,"getSaveFileName",return_value=(str(dest.with_suffix("")),"PNG (*.png)")):
                    w.save_button.click()
            assert QPixmap(str(dest)).toImage()==pix.toImage()
            if output:pix.save(str(output.with_suffix(".png")))
            d=w.make_inspector();d.show();app.processEvents()
            assert (d.width(),d.height())==(700,600)
            tabs=d.findChild(type(d.result_tabs),"result_tabs")
            for i,key in enumerate(("working","test")):
                tabs.setCurrentIndex(i);app.processEvents()
                c=d.findChild(QComboBox,key+"_precision")
                assert c.width()==210
                for idx in (0,3,6):
                    c.setCurrentIndex(idx);c.showPopup();app.processEvents()
                    assert c.view().isVisible()
                    g=c.view().window().geometry();bottom=c.mapToGlobal(c.rect().bottomLeft())
                    assert abs(g.top()-bottom.y())<=3 or abs(g.bottom()-c.mapToGlobal(c.rect().topLeft()).y())<=3
                    c.hidePopup();app.processEvents()
                c.setCurrentIndex(5)
                assert d.findChild(QComboBox,("test" if i==0 else "working")+"_precision").currentIndex()==5
                assert "Calculation Breakdown" in d.findChild(QTextBrowser,key+"_text").toPlainText()
            d.close()
            d=w.make_settings();d.show();app.processEvents()
            assert [d.settings_tabs.tabText(i) for i in range(4)]==["Assumptions","References","Updates","About"]
            assert "PASS means the individual stress utilisation is no greater than 1.00." in d.assumptions_text_2.text()
            assert "buckling" not in d.assumptions_text_2.text().lower()
            assert "full code compliance" not in d.assumptions_text_2.text().lower()
            assert d.references_note.text()=="Reference publications are not distributed with the application."
            assert "radial stress is zero at the bore" in d.assumptions_text_1.text()
            assert "same radial location" in d.assumptions_text_1.text()
            assert "identical Von Mises and maximum shear" in d.assumptions_text_1.text()
            assert "must not" not in d.assumptions_text_1.text()
            assert "<table" not in d.references_text.text()
            for table_number in ("28","32"):
                assert f'<p style="margin:0 0 10px 8px;">- Table {table_number}:' in d.references_text.text()
            for expected in ("Table 28","Table 32","1a (internal, open)","1b (internal, capped)","1c (external, open)","1d (external, capped)"):
                assert expected in d.references_text.text(),expected
            report["settings_wording"]="passed"
            from inspect_results import html_breakdown
            from itertools import product
            references=0
            for thick,external,capped in product((False,True),repeat=3):
                inputs=dict(od=10,id=6 if thick else 9.8,working_pressure=500,test_pressure=750,yield_strength=60000,derating_factor=1,axial_load=0,pressure_type="external" if external else "internal",end_condition="capped" if capped else "open")
                result=calculate_case(inputs)
                table=32 if thick else 28
                case=({(False,False):"1a",(False,True):"1b",(True,False):"1c",(True,True):"1d"}[(external,capped)] if thick else "1c" if capped else "1b")
                for key in ("working","test"):
                    assert f"Calculation basis: Roark, 6th Edition, Table {table}, Case {case}" in html_breakdown(inputs,result,key,3)
                    references+=1
            report["roark_case_references"]=references
            assert "MIT Licence" in d.about_text.text()
            assert "v"+APP_VERSION in d.about_text.text() and d.current_version.text()=="Current version: v"+APP_VERSION
            assert d.github_link.openExternalLinks()
            assert d.check_on_launch.isChecked()
            if output:
                for i,k in enumerate(("assumptions","references","updates","about")):
                    d.settings_tabs.setCurrentIndex(i);app.processEvents();d.grab().save(str(output.with_name(output.stem+"_"+k+".png")))
            d.close()
            w.reset();assert not w.result and not w.copy_button.isEnabled()
            report["ui"]="passed"
            if "--live-update-test" in sys.argv:
                # Before publication, verify HTTPS against our own existing
                # stable release channel; after publication, use actual target.
                if "--reference-channel" in sys.argv:
                    update_checker.GITHUB_URL="https://github.com/ZeroFlagLabs/radial-oring-calculator"
                    update_checker.RELEASES_URL=update_checker.GITHUB_URL+"/releases/latest"
                loop=QEventLoop()
                def done():
                    if w.update_checker._reply is None:loop.quit()
                w.update_checker.state_changed.connect(done)
                w.update_checker.check()
                QTimer.singleShot(15000,loop.quit)
                if w.update_checker._reply is not None:loop.exec()
                status=w.update_checker.status;report["live_update"]=status
                if "--reference-channel" in sys.argv:
                    assert w.update_checker.release_url and status.endswith("Open GitHub to download."),status
                else:assert status=="Up to date.",status
        report["result"]="passed"
        return 0
    except Exception:
        report["result"]="failed";report["traceback"]=traceback.format_exc()
        print(report["traceback"],flush=True)
        return 1
    finally:
        if output:output.write_text(json.dumps(report,indent=2),encoding="utf8")
        print(json.dumps(report),flush=True)
        w.close()
