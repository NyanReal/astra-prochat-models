"""Run with: python validation/test_asset.py. Standard library only."""
import json, math, struct, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def read_glb(path):
    data=path.read_bytes()
    magic,version,total=struct.unpack_from('<4sII',data,0)
    if (magic,version,total)!=(b'glTF',2,len(data)): raise ValueError('Invalid GLB header')
    n,tag=struct.unpack_from('<I4s',data,12)
    return json.loads(data[20:20+n]), data

class AssetTests(unittest.TestCase):
    def setUp(self):
        self.payload=json.loads((ROOT/'source/mesh_payload.json').read_text())
    def test_triangle_budget_and_finite_data(self):
        count=0
        for obj in self.payload['objects']:
            self.assertTrue(all(math.isfinite(v) for p in obj['positions'] for v in p))
            for f in obj['triangles']:
                self.assertEqual(len(f),3)
                self.assertEqual(len(set(f)),3)
                self.assertTrue(all(0<=i<len(obj['positions']) for i in f))
            count+=len(obj['triangles'])
        self.assertLess(count,4000)
        self.assertGreater(count,500)
    def test_uvs_are_unique_and_in_bounds(self):
        islands=self.payload['islands']
        for island in islands:
            x,y,w,h=island['rect']
            self.assertGreaterEqual(min(x,y),0)
            self.assertLessEqual(max(x+w,y+h),self.payload['atlas_size'])
        rects=sorted([i['rect'] for i in islands])
        for a,(x,y,w,h) in enumerate(rects):
            for X,Y,W,H in rects[a+1:]:
                if X>=x+w: break
                self.assertFalse(y<Y+H and Y<y+h, 'UV island bounding boxes overlap')
        for obj in self.payload['objects']:
            self.assertTrue(all(0<=u<=1 and 0<=v<=1 for u,v in obj['uvs']))
    def test_texel_density(self):
        target=self.payload['pixels_per_meter']
        for i in self.payload['islands']:
            dx,dy=i['density']
            self.assertLess(abs(dx/target-1),0.07)
            self.assertLess(abs(dy/target-1),0.07)
    def test_glb_self_contained_and_budget(self):
        doc,data=read_glb(ROOT/'models/wooden_food_shed.glb')
        self.assertEqual(len(doc['meshes']),1)
        self.assertEqual(len(doc['materials']),1)
        count=0
        for mesh in doc['meshes']:
            for prim in mesh['primitives']:
                count+=doc['accessors'][prim['indices']]['count']//3
                self.assertIn('TEXCOORD_0',prim['attributes'])
                self.assertIn('NORMAL',prim['attributes'])
        self.assertLess(count,4000)
        self.assertEqual(count,sum(len(o['triangles']) for o in self.payload['objects']))
        for im in doc['images']:
            self.assertIn('bufferView',im)
            self.assertNotIn('uri',im)
        self.assertNotIn('uri',doc['buffers'][0])
    def test_required_deliverables(self):
        for p in ['blender/create_wooden_food_shed.py','unreal/import_wooden_food_shed_ue57.py','textures/T_Shed_BaseColor.png','textures/T_Shed_Normal_GL.png','textures/T_Shed_ORM.png','textures/T_Shed_Emissive.png','README.ko.md']:
            self.assertTrue((ROOT/p).is_file(),p)
if __name__=='__main__': unittest.main(verbosity=2)
