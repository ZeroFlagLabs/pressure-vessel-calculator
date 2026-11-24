"""Check physical geometry selection against an independent dense grid."""
from pathlib import Path
import sys, math, random, unittest
from decimal import Decimal as D
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from geometry_selection import select_geometry
from cases import calculate_case

def score(res):
    return max(v for k in ("working","test") for v in (res[k]["uf_vm"],res[k]["uf_tau"]) if v is not None)

class GeometrySelectionTests(unittest.TestCase):
    def test_grid(self):
        rng=random.Random(20261124)
        base=dict(yield_strength=75000,working_pressure=10000,test_pressure=15000,derating_factor=.85,axial_load=0,pressure_type="internal",end_condition="capped")
        count=0
        for kind in ("od","id"):
            for i in range(100):
                tlo=rng.uniform(.05,2);thi=tlo*rng.uniform(1,2)
                dlo=rng.uniform(2.01*thi,45*thi) if kind=="od" else rng.uniform(.1,45*thi)
                dhi=dlo*rng.uniform(1,2)
                p=rng.uniform(0,15000);F=rng.uniform(-1e6,1e6)
                loading=dict(base,working_pressure=p,test_pressure=p*rng.uniform(1,2),axial_load=F,pressure_type=rng.choice(("internal","external")),end_condition=rng.choice(("open","capped")),derating_factor=rng.uniform(.1,1))
                bounds={kind:(D(str(dlo)),D(str(dhi))),"t":(D(str(tlo)),D(str(thi)))}
                raw,res,_=select_geometry(bounds,"id" if kind=="od" else "od",loading)
                gscore=score(res)
                self.assertGreaterEqual((raw["od"]-raw["id"])/2,tlo-1e-10)
                self.assertLessEqual((raw["od"]-raw["id"])/2,thi+1e-10)
                self.assertEqual(calculate_case(raw),res)
                for j in range(31):
                    d=dlo+(dhi-dlo)*j/30
                    for k in range(31):
                        t=tlo+(thi-tlo)*k/30
                        od,idd=(d,d-2*t) if kind=="od" else (d+2*t,d)
                        test=score(calculate_case(dict(loading,od=od,id=idd)))
                        self.assertGreaterEqual(gscore+1e-9*max(gscore,1),test,(kind,i,j,k,raw,loading))
                        count+=1
        print("Independent dense grid:",count,"physical geometries, 200 tolerance rectangles")
    def test_legacy(self):
        loading=dict(yield_strength=75000,working_pressure=10000,test_pressure=15000,derating_factor=1,axial_load=0,pressure_type="internal",end_condition="capped")
        bounds={"od":(D("9.99"),D("10.01")),"id":(D("7.98"),D("8.02"))}
        raw,res,_=select_geometry(bounds,"t",loading)
        self.assertEqual((raw["od"],raw["id"]),(9.99,8.02))
        self.assertEqual(res,calculate_case(dict(loading,od=9.99,id=8.02)))
    def test_correlation(self):
        loading=dict(yield_strength=75000,working_pressure=10000,test_pressure=15000,derating_factor=1,axial_load=0,pressure_type="internal",end_condition="capped")
        for kind,derived,dim in (("od","id",10),("id","od",8)):
            raw,res,_=select_geometry({kind:(D(str(dim-.01)),D(str(dim+.01))),"t":(D(".995"),D("1.005"))},derived,loading)
            self.assertAlmostEqual((raw["od"]-raw["id"])/2,.995)
            self.assertGreaterEqual(raw[kind],dim-.01000000001)
            self.assertLessEqual(raw[kind],dim+.01000000001)
    def test_boundary(self):
        loading=dict(yield_strength=75000,working_pressure=10000,test_pressure=15000,derating_factor=.85,axial_load=-100000,pressure_type="internal",end_condition="capped")
        for kind,derived,d in (("od","id",21),("id","od",19)):
            bounds={kind:(D(str(d-.1)),D(str(d+.1))),"t":(D(".99"),D("1.01"))}
            raw,res,_=select_geometry(bounds,derived,loading)
            self.assertEqual(res,calculate_case(raw))
            for x in (d-.1,d,d+.1):
                for t in (.99,1,1.01,x/(21 if kind=="od" else 19)):
                    if not .99<=t<=1.01:continue
                    od,idd=(x,x-2*t) if kind=="od" else (x+2*t,x)
                    self.assertGreaterEqual(score(res)+1e-9,score(calculate_case(dict(loading,od=od,id=idd))))
if __name__=="__main__":unittest.main()
