import hashlib,json,random,unittest,sys
from pathlib import Path
from itertools import product
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import cases

class LegacyEquivalence(unittest.TestCase):
    def test_v13_packaged_engine(self):
        digest=hashlib.sha256()
        base=dict(od=10,id=8,working_pressure=10000,test_pressure=15000,yield_strength=75000,derating_factor=1,axial_load=0,pressure_type="internal",end_condition="capped")
        rng=random.Random(20261124)
        engine_count=0
        branches=set()
        for (od,id_),pt,ends,F,d,(wp,tp),sy in product(
            [(2,1),(10,8),(21,19),(21,18.999),(21,19.001),(10,9.8),(100,99.9),(0.01,0.008)],
            ("internal","external"),("capped","open"),(-100000,0,100000),(.25,.85,1),
            [(0,0),(0,15000),(10000,10000),(10000,15000)],(36000,75000,120000)):
            data=dict(base,od=od,id=id_,pressure_type=pt,end_condition=ends,axial_load=F,derating_factor=d,working_pressure=wp,test_pressure=tp,yield_strength=sy)
            actual=cases.calculate_case(data)
            digest.update(json.dumps(actual,sort_keys=True,separators=(',',':')).encode())
            branches.add((actual["wall_type"],pt,ends));engine_count+=1
        for i in range(1000):
            od=rng.uniform(.01,1000);id_=od*rng.uniform(.01,.999)
            data=dict(base,od=od,id=id_,pressure_type=rng.choice(["internal","external"]),end_condition=rng.choice(["open","capped"]),axial_load=rng.uniform(-1e7,1e7),derating_factor=rng.uniform(.01,1),yield_strength=rng.uniform(1000,200000),working_pressure=rng.uniform(0,30000))
            data["test_pressure"]=data["working_pressure"]*rng.uniform(1,2)
            digest.update(json.dumps(cases.calculate_case(data),sort_keys=True,separators=(',',':')).encode())
            engine_count+=1
        assert len(branches)==8
        self.assertEqual(digest.hexdigest(), '5c057a1a2e92be16c728822db583ba19b24aa37eeb02f7a39475ba6baaaa55ca')
        self.assertEqual(engine_count,4456)
