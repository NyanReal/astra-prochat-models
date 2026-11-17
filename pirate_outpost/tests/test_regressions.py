import unittest,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from meshcore import Builder
from assets_props import grass,stocks
class RegressionTests(unittest.TestCase):
 def test_collapsed_leaf_tips_do_not_export_unused_normals(self):
  b=Builder('grass');grass(b);v,f,n,uv=b.arrays()
  self.assertEqual(len(np.unique(f)),len(v),'Unused collapsed tip vertices must be removed')
  self.assertTrue(np.allclose(np.linalg.norm(n,axis=1),1,atol=1e-4))
 def test_stock_board_faces_match_normals(self):
  b=Builder('stocks');stocks(b);v,f,n,uv=b.arrays()
  cr=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
  self.assertEqual(int(np.sum(np.sum(cr*n[f].mean(1),axis=1)<-1e-8)),0)
 def test_barrel_lid_boards_cover_radial_end_caps(self):
  from asset_parts import barrel
  b=Builder('barrel');barrel(b,h=.9,r=.34);v,f,n,uv=b.arrays()
  tri=v[f];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(normal,axis=1)/2
  above=(tri[:,:,2].min(1)>.905)&(normal[:,2]>0)
  self.assertGreater(area[above].sum(),.90*np.pi*(.34*.79)**2,'Lid must visibly cover the radial stave end caps')
 def test_generated_wood_has_no_black_source_seams(self):
  from PIL import Image
  arr=np.array(Image.open(ROOT/'textures'/'T_Pirate_BaseColor.png'))[:384,:256].mean(2)
  self.assertGreater(np.percentile(arr,1),90)
if __name__=='__main__':unittest.main()
