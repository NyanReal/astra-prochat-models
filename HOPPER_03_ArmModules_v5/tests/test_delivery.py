import unittest,sys,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'source'))
from glb_io import read_glb,triangles
class Delivery(unittest.TestCase):
 def test_separate_modules(self):
  for s in 'LR':self.assertTrue((R/f'models/HOPPER_03_Arm_{s}_M1.glb').exists(),f'Arm {s} GLB missing')
 def test_combined_budget(self):
  f=R/'preview/FitCheck.glb';self.assertTrue(f.exists(),'Fit check GLB missing');self.assertLess(triangles(read_glb(f)[0]),30000)
 def test_manifest(self):self.assertTrue((R/'docs/socket_spec.json').exists(),'Socket manifest missing')
if __name__=='__main__':unittest.main()
