import unittest, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
class GeometryTests(unittest.TestCase):
 def test_core_available(self):
  self.assertTrue((ROOT/'scripts'/'meshcore.py').is_file(),'Mesh implementation is required')
 def test_primitives_finite(self):
  self.assertTrue((ROOT/'scripts'/'meshcore.py').is_file(),'Mesh implementation is required')
  from meshcore import Builder
  b=Builder('test');b.box((0,0,.5),(1,2,1),'wood',bevel=.08)
  b.lathe([(0,.3),(.2,.4),(.8,.4),(1,.3)],'wood',segments=12)
  b.tube([(0,0,0),(.5,0,.5),(1,.5,1)],.05,'rope')
  v,f,n,uv=b.arrays()
  self.assertTrue(np.isfinite(v).all());self.assertTrue(np.isfinite(n).all())
  self.assertGreater(len(f),50);self.assertTrue(((uv>=0)&(uv<=1)).all())
  self.assertTrue(np.allclose(np.linalg.norm(n,axis=1),1,atol=1e-4))
 def test_axis_rotation_preserves_handedness(self):
  self.assertTrue((ROOT/'scripts'/'meshcore.py').is_file(),'Mesh implementation is required')
  from meshcore import GLTF_BASIS
  self.assertAlmostEqual(np.linalg.det(GLTF_BASIS),1)
  np.testing.assert_allclose(GLTF_BASIS@np.array([0,0,1]),[0,1,0])
if __name__=='__main__':unittest.main()
