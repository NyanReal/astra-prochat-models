"""Engine-independent regression tests. These do NOT pretend to run Blender/UE."""
from pathlib import Path
import importlib, json, math, sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

class PipelineMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module_path=ROOT/'scripts/pipeline_common.py'
    def module(self):
        self.assertTrue(self.module_path.is_file(),'Shared importer math is not implemented')
        return importlib.import_module('pipeline_common')
    def test_all_signed_axis_permutations_and_units(self):
        from itertools import permutations,product
        p=self.module()
        for perm in permutations(range(3)):
            for signs in product([-1,1],repeat=3):
                for unit in [1.,100.]:
                    lo=[min(0,signs[i]*(perm[i]+1)*unit) for i in range(3)]
                    hi=[max(0,signs[i]*(perm[i]+1)*unit) for i in range(3)]
                    got=p.infer_basis(lo,hi)
                    want=[[signs[i] if j==perm[i] else 0 for j in range(3)] for i in range(3)]
                    self.assertEqual(got['basis'],want)
                    self.assertAlmostEqual(got['units_per_metre'],unit)
    def test_probe_recentering_is_rejected(self):
        p=self.module()
        with self.assertRaises(ValueError):p.infer_basis([-.5,-1,-1.5],[.5,1,1.5])
    def test_nonsquare_scale_matches_rotated_geometry(self):
        p=self.module();basis=[[0,-1,0],[1,0,0],[0,0,1]];cal={'basis':basis,'units_per_metre':1.}
        t=p.to_unreal_transform([1,2,3],90,[2,3,4],cal)
        self.assertEqual(t['position_cm'],[-200,100,300]);self.assertEqual(t['scale'],[300,200,400])
        q=t['quaternion_xyzw'];self.assertAlmostEqual(abs(q[2]),math.sqrt(.5));self.assertAlmostEqual(abs(q[3]),math.sqrt(.5))
    def test_reflection_reverses_yaw(self):
        p=self.module();c={'basis':[[1,0,0],[0,-1,0],[0,0,1]],'units_per_metre':100}
        q=p.to_unreal_transform([0,0,0],60,[1,1,1],c)['quaternion_xyzw']
        self.assertAlmostEqual(q[2],-.5);self.assertAlmostEqual(q[3],math.sqrt(3)/2)
    def test_paths_cannot_escape_pack(self):
        p=self.module()
        with self.assertRaises(ValueError):p.pack_file(ROOT,'../../outside.glb')
    def test_invalid_content_roots_rejected(self):
        p=self.module()
        for bad in ['/Engine/Pirates','/Game','/Game/Pirate../X','/Game/Has Space']:
            with self.assertRaises(ValueError):p.content_root(bad)
        self.assertEqual(p.content_root('/Game/PirateOutpost/'),'/Game/PirateOutpost')
    def test_missing_unknown_and_duplicate_layout_assets_rejected(self):
        p=self.module();m=json.loads((ROOT/'asset_manifest.json').read_text())
        good=json.loads((ROOT/'layout/harbor_layout.json').read_text());p.validate_layout(good,m)
        bad=json.loads(json.dumps(good));bad['instances'][0]['asset']='MISSING'
        with self.assertRaises(ValueError):p.validate_layout(bad,m)
        bad=json.loads(json.dumps(good));bad['instances'].append(bad['instances'][0])
        with self.assertRaises(ValueError):p.validate_layout(bad,m)
    def test_expected_bounds_respect_reflection(self):
        p=self.module();self.assertTrue(hasattr(p,'expected_bounds'),'Imported bounds verification missing')
        f=[[0,-1,0],[1,0,0],[0,0,1]]
        lo,hi=p.expected_bounds([[-1,-2,0],[3,4,5]],f,100)
        self.assertEqual(lo,[-400,-100,0]);self.assertEqual(hi,[200,300,500])
    def test_invalid_transforms_rejected(self):
        p=self.module();c={'basis':[[1,0,0],[0,1,0],[0,0,1]],'units_per_metre':100}
        with self.assertRaises(ValueError):p.to_unreal_transform([0,float('nan'),0],0,[1,1,1],c)
        with self.assertRaises(ValueError):p.to_unreal_transform([0,0,0],0,[1,-1,1],c)

if __name__=='__main__':unittest.main()
