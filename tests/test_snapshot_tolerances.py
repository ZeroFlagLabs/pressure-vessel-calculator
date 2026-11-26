"""Preserve exact dimensional bounds in exported report text."""
from pathlib import Path
import sys,unittest
from decimal import Decimal as D
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from snapshot import geometry_rows
class SnapshotToleranceTests(unittest.TestCase):
    def test_modes_and_derived(self):
        for mode in ("pm","limits"):
            for derived in (False,True):
                for lo,hi,expected in [
                    ("0.248","0.252","0.250 ± 0.002 in"),
                    ("10","10","10.000 in"),
                    ("1.000001","1.000002","1.0000015 ± 0.0000005 in")]:
                    row=SimpleNamespace(name="Outer diameter",derived=derived,mode=mode,bounds=lambda:(D(lo),D(hi)))
                    self.assertEqual(geometry_rows(SimpleNamespace(dims={"od":row})),[("Outer diameter"+(" (derived)" if derived else ""),expected)])
