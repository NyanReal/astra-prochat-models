import json, struct, unittest, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

class ContractTests(unittest.TestCase):
    def test_asset_manifest_exists(self):
        self.assertTrue((ROOT/'asset_manifest.json').is_file(), 'Final asset manifest is required')
    def test_expected_assets_are_present(self):
        p=ROOT/'asset_manifest.json'
        self.assertTrue(p.is_file(), 'Asset catalog not yet exported')
        data=json.loads(p.read_text()); assets=data['assets']
        names={a['id'] for a in assets}
        self.assertGreaterEqual(len(names),60)
        for n in ['SM_Watchtower','SM_Dock_Straight','SM_Dock_Corner','SM_Dock_T','SM_Dock_Cross','SM_LoadingCrane','SM_CommandHut','SM_Cannon','SM_Anchor']:
            self.assertIn(n,names)
        self.assertEqual(len(names),len(assets))
        for a in assets:
            self.assertTrue((ROOT/a['file']).is_file(),a['file'])
            self.assertGreater(a['triangles'],0)
    def test_textures(self):
        from PIL import Image
        for name in ['T_Pirate_BaseColor.png','T_Pirate_RoughMetal.png']:
            p=ROOT/'textures'/name
            self.assertTrue(p.is_file(),name)
            with Image.open(p) as im:
                self.assertLessEqual(max(im.size),1024)
    def test_layout_references(self):
        p=ROOT/'layout'/'harbor_layout.json'
        self.assertTrue(p.is_file(),'Shared scene layout is required')
        names={a['id'] for a in json.loads((ROOT/'asset_manifest.json').read_text())['assets']}
        d=json.loads(p.read_text()); ids=set()
        for o in d['instances']:
            self.assertIn(o['asset'],names)
            self.assertNotIn(o['name'],ids); ids.add(o['name'])
            self.assertTrue(np.isfinite(o['position_m']).all())
    def test_layout_camera_schema(self):
        for name in ['harbor','gallery']:
            camera=json.loads((ROOT/'layout'/f'{name}_layout.json').read_text())['camera']
            self.assertIn('position_m',camera)
            self.assertIn('target_m',camera)
            self.assertEqual(len(camera['position_m']),3)
    def test_editor_scripts_syntax(self):
        paths=['scripts/blender/build_preview.py','scripts/unreal/import_pirate_outpost.py','scripts/unreal/place_pirate_outpost.py']
        for p in paths:
            f=ROOT/p
            self.assertTrue(f.is_file(),p)
            compile(f.read_text(encoding='utf-8'),str(f),'exec')

if __name__=='__main__': unittest.main()
