"""Regression gates for the requested static-web tree, not a painted substitute."""
import os,json,unittest
from pathlib import Path
import numpy as np
ROOT=Path(os.environ.get('TREE_ROOT',Path(__file__).resolve().parents[1]))
class AssetTests(unittest.TestCase):
 def test_trunk_is_geometry_not_screen_space_strokes(self):
  html=(ROOT/'index.html').read_text()
  self.assertNotIn('strokeTexturedBranch',html,'2D painted branch substitute is still present')
  self.assertTrue((ROOT/'assets/scene.json').is_file(),'No indexed trunk mesh asset exists')
 def test_mesh_has_finite_positions_uv_and_depth(self):
  self.assertTrue((ROOT/'assets/scene.json').exists(),'No 3D scene to validate')
  s=json.loads((ROOT/'assets/scene.json').read_text());m=s['trunk']
  p=np.asarray(m['position']).reshape(-1,3); uv=np.asarray(m['uv']).reshape(-1,2); idx=np.asarray(m['indices'])
  self.assertTrue(np.isfinite(p).all());self.assertEqual(len(p),len(uv))
  self.assertGreater(np.ptp(p[:,2]),.5);self.assertGreater(np.ptp(p[:,1]),3)
  self.assertTrue((uv>=0).all() and (uv<=1).all());self.assertLess(idx.max(),len(p))
  self.assertGreater(len(idx)//3,1000)
 def test_crown_and_gradient_contract(self):
  self.assertTrue((ROOT/'assets/scene.json').exists(),'No crown data')
  s=json.loads((ROOT/'assets/scene.json').read_text());meta=s['meta']
  self.assertEqual(len(s['bunches']),10)
  self.assertEqual(meta['removedBunchIds'],[909,1001])
  self.assertFalse(meta['wholeTreeGradient']);self.assertLess(meta['cardLinearScaleVersusV03'],1)
  self.assertGreater(meta['cardsPerBunch'],90)
  self.assertLess(s['bunches'][5]['center'][1]-meta['groundOffset'],2.30)
 def test_all_card_uvs_cover_full_tile_and_lighting_is_upward(self):
  self.assertTrue((ROOT/'assets/scene.json').exists(),'No leaf mesh')
  s=json.loads((ROOT/'assets/scene.json').read_text());m=s['foliage']
  self.assertEqual(len(m['position'])//3,len(m['proxyNormal'])//3)
  uv=np.asarray(m['uv']).reshape(-1,4,2);self.assertTrue((np.ptp(uv,axis=1)>.24).all())
  L=np.asarray(s['meta']['lightDirection']);self.assertGreater(L[1],0)
 def test_self_contained_web_and_exchange_asset(self):
  html=(ROOT/'index.html').read_text()
  self.assertNotIn('src="http',html)
  self.assertTrue((ROOT/'models/tree_v05.glb').exists(),'Mesh export is missing')
  self.assertIn('data:image/',html,'Embedded textures required for direct-file preview')
if __name__=='__main__':unittest.main(verbosity=2)
