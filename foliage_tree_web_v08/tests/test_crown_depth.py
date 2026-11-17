"""Regression for flattened front/back crown. Operates on shipped mesh data."""
import json,os,unittest
from pathlib import Path
import numpy as np
ROOT=Path(os.environ.get('TREE_ROOT',Path(__file__).resolve().parents[1]))
class CrownDepthTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=json.loads((ROOT/'assets/scene.json').read_text())
  cls.raw=json.loads((ROOT/'assets/branch_skeleton.json').read_text())
 def test_bunch_centres_span_front_and_back_not_a_sheet(self):
  c=np.array([b['center'] for b in self.scene['bunches']]);e=np.ptp(c,axis=0)
  self.assertGreater(e[2]/e[0],.68,'Bunches still laid out in a thin XY sheet')
  self.assertGreater(np.count_nonzero(c[:,2]>.6),2)
  self.assertGreater(np.count_nonzero(c[:,2]<-.5),2)
 def test_visible_branch_mesh_has_depth_above_roots(self):
  p=np.asarray(self.scene['trunk']['position']).reshape(-1,3);p=p[p[:,1]>1.4];e=np.ptp(p,axis=0)
  self.assertGreater(e[2]/e[0],.6,'Only roots have depth: crown branches remain planar')
  self.assertGreater(p[:,2].max(),1.0);self.assertLess(p[:,2].min(),-1.0)
 def test_every_bunch_contains_a_real_branch_tip(self):
  tips=np.array([b[-1][:3] for b in self.raw if b[-1][1]>1.2])
  for b in self.scene['bunches']:
   dist=np.linalg.norm((tips-np.array(b['center']))/b['radii'],axis=1)
   self.assertLess(dist.min(),.9,f"Bunch {b['id']} has no supporting terminal branch")
 def test_crown_does_not_restore_deleted_top_or_grow_taller(self):
  self.assertEqual(len(self.scene['bunches']),10)
  ids={b['id'] for b in self.scene['bunches']};self.assertNotIn(909,ids);self.assertNotIn(1001,ids)
  p=np.array(self.scene['foliage']['pivot']).reshape(-1,3)
  self.assertLess(p[:,1].max(),4.45)
  self.assertFalse(self.scene['meta']['wholeTreeGradient'])
 def test_card_normals_are_unit_and_new_bunch_volume_not_stretched_billboards(self):
  m=self.scene['foliage'];n=np.array(m['proxyNormal']).reshape(-1,3)
  self.assertLess(np.max(abs(np.linalg.norm(n,axis=1)-1)),2e-6)
  p=np.asarray(m['position']).reshape(-1,4,3);piv=np.asarray(m['pivot']).reshape(-1,4,3)
  self.assertLess(abs((p-piv)[:,:,2]).max(),1e-6,'Rest cards must stay XY; shader handles view-facing')
  a=np.linalg.norm(p[:,1]-p[:,0],axis=1);b=np.linalg.norm(p[:,3]-p[:,0],axis=1)
  self.assertTrue(np.allclose(a,b,atol=3e-6),'Do not fix depth by distorting card geometry')
if __name__=='__main__':unittest.main(verbosity=2)
