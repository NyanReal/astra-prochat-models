"""Artifact-level tests: run from any working directory with python test_assets.py."""
from pathlib import Path
import unittest, json, struct
import numpy as np
import trimesh
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
NAMES = ['wild_sweet_potato', 'cultivated_sweet_potato']
def glb_json(path):
    data=path.read_bytes()
    magic,version,total=struct.unpack_from('<III',data)
    assert magic==0x46546c67 and version==2 and total==len(data)
    size,kind=struct.unpack_from('<II',data,12)
    assert kind==0x4e4f534a
    return json.loads(data[20:20+size])
class Assets(unittest.TestCase):
    def test_models_exist(self):
        for name in NAMES:
            for suffix in ['', '_LOD1']:
                self.assertTrue((ROOT/'models'/f'{name}{suffix}.glb').is_file(), name+suffix)
    def test_meshes(self):
        for path in (ROOT/'models').glob('*.glb'):
            scene=trimesh.load(path,force='scene',process=False)
            self.assertGreater(len(scene.geometry),0)
            count=0
            for mesh in scene.geometry.values():
                count+=len(mesh.faces)
                self.assertTrue(np.isfinite(mesh.vertices).all())
                self.assertTrue(np.isfinite(mesh.vertex_normals).all())
                self.assertTrue((mesh.area_faces>1e-12).all(),path.name)
                self.assertIsNotNone(mesh.visual.uv)
                self.assertTrue(np.isfinite(mesh.visual.uv).all())
            self.assertLess(count,26000)
            self.assertGreater(scene.bounds[1,1],.2)
            self.assertGreaterEqual(scene.bounds[0,1],-.005)
    def test_materials(self):
        for path in (ROOT/'models').glob('*.glb'):
            gltf=glb_json(path)
            for mat in gltf.get('materials',[]):
                self.assertNotIn('normalTexture',mat)
                self.assertEqual(mat['pbrMetallicRoughness']['metallicFactor'],0)
                self.assertIn('baseColorTexture',mat['pbrMetallicRoughness'])
            for image in gltf['images']:
                self.assertIn('bufferView',image)
                self.assertNotIn('uri',image)
    def test_texture_ceiling(self):
        paths=list((ROOT/'textures').glob('*.png'))
        self.assertTrue(paths)
        for p in paths:
            with Image.open(p) as image:
                self.assertLessEqual(max(image.size),1024)
    def test_lod_is_smaller(self):
        for name in NAMES:
            paths=[ROOT/'models'/f'{name}{s}.glb' for s in ['', '_LOD1']]
            if not all(p.exists() for p in paths):
                self.fail('Missing LOD deliverables')
            tris=[sum(len(m.faces) for m in trimesh.load(p,force='scene',process=False).geometry.values()) for p in paths]
            self.assertLess(tris[1],tris[0]*.7)
if __name__=='__main__': unittest.main(verbosity=2)
