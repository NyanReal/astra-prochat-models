"""Independent checks on the exported asset bytes, not only authoring summaries."""
import unittest, sys, json, hashlib, io
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'source'))
from glb_io import read_glb,accessor,world_matrices,triangles,bounds,DT,NC

def trs(value):
    out=np.eye(4);out[:3,:3]=Rotation.from_quat(value.get('rotation_xyzw',value.get('rotation',[0,0,0,1]))).as_matrix()@np.diag(value.get('scale',[1,1,1]));out[:3,3]=value.get('translation',[0,0,0]);return out

def image_bytes(g,b,idx):
    v=g['bufferViews'][g['images'][idx]['bufferView']];return b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]

class Model(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
    cls.mods={s:read_glb(R/f'models/HOPPER_03_Arm_{s}_M1.glb') for s in 'LR'}
    cls.base=read_glb(R/'reference/HOPPER_03_Legs_v4.glb');cls.fit=read_glb(R/'preview/FitCheck.glb')
    cls.spec=json.loads((R/'docs/socket_spec.json').read_text());cls.report=json.loads((R/'docs/asset_report.json').read_text())
 def test_all_file_headers_and_no_external_resources(self):
    for g,b in self.mods.values():
        self.assertEqual(g['asset']['version'],'2.0');self.assertTrue(all('uri' not in x for x in g['buffers']+g['images']))
 def test_triangle_budget_from_indices(self):
    self.assertEqual(triangles(self.base[0]),25058)
    for g,b in self.mods.values():self.assertEqual(triangles(g),2406)
    self.assertEqual(triangles(self.fit[0]),29870);self.assertLess(triangles(self.fit[0]),30000)
 def test_independent_identity_roots(self):
    for s,(g,b) in self.mods.items():
        self.assertEqual(len(g['scenes'][0]['nodes']),1);root=g['nodes'][g['scenes'][0]['nodes'][0]]
        self.assertEqual(root['name'],f'Arm_{s}_M1_Root');np.testing.assert_allclose(trs(root),np.eye(4))
 def test_rigid_parts_and_tool_attachment(self):
    for s,(g,b) in self.mods.items():
        names=[n['name'] for n in g['nodes']];self.assertIn(f'Arm_{s}_09_ToolPort',names)
        self.assertTrue(any('Elbow_Pivot' in n for n in names));self.assertTrue(any('Wrist_Pivot' in n for n in names))
        self.assertFalse(g.get('skins'));self.assertFalse(g.get('animations'))
 def test_acyclic_hierarchy_all_nodes_reachable(self):
    for g,b in self.mods.values():
        seen=set()
        def visit(i):
            self.assertNotIn(i,seen);seen.add(i)
            for child in g['nodes'][i].get('children',[]):visit(child)
        for root in g['scenes'][0]['nodes']:visit(root)
        self.assertEqual(len(seen),len(g['nodes']))
 def test_no_negative_scale(self):
    for g,b in self.mods.values():
        self.assertTrue(all(np.linalg.det(m[:3,:3])>0 for m in world_matrices(g).values()))
 def test_accessor_ranges_and_finite_values(self):
    for g,b in self.mods.values():
        for i,a in enumerate(g['accessors']):
            v=g['bufferViews'][a['bufferView']];step=NC[a['type']]*np.dtype(DT[a['componentType']]).itemsize
            last=a.get('byteOffset',0)+(a['count']-1)*v.get('byteStride',step)+step
            self.assertLessEqual(last,v['byteLength']);self.assertLessEqual(v.get('byteOffset',0)+v['byteLength'],len(b))
            self.assertTrue(np.isfinite(accessor(g,b,i)).all())
 def test_indices_triangle_areas(self):
    for g,b in self.mods.values():
        for mesh in g['meshes']:
            for p in mesh['primitives']:
                pos=accessor(g,b,p['attributes']['POSITION']);ind=accessor(g,b,p['indices']).ravel()
                self.assertEqual(len(ind)%3,0);self.assertLess(int(ind.max()),len(pos));f=pos[ind.reshape(-1,3)]
                areas=np.linalg.norm(np.cross(f[:,1]-f[:,0],f[:,2]-f[:,0]),axis=1)*.5
                self.assertTrue((areas>1e-10).all(),mesh['name'])
 def test_normal_and_tangent_frames(self):
    for g,b in self.mods.values():
        for mesh in g['meshes']:
            for p in mesh['primitives']:
                n=accessor(g,b,p['attributes']['NORMAL']);t=accessor(g,b,p['attributes']['TANGENT'])
                np.testing.assert_allclose(np.linalg.norm(n,axis=1),1,atol=1e-5)
                np.testing.assert_allclose(np.linalg.norm(t[:,:3],axis=1),1,atol=1e-5)
                self.assertLess(float(np.abs((n*t[:,:3]).sum(1)).max()),1e-5)
                self.assertTrue(np.isin(t[:,3],[-1,1]).all())
 def test_uv_bounds(self):
    for g,b in self.mods.values():
        for mesh in g['meshes']:
            for p in mesh['primitives']:
                uv=accessor(g,b,p['attributes']['TEXCOORD_0']);self.assertGreaterEqual(float(uv.min()),0);self.assertLessEqual(float(uv.max()),1)
 def test_shared_atlas_embedded_identically(self):
    l,lb=self.mods['L'];r,rb=self.mods['R'];self.assertEqual(len(l['images']),3);self.assertEqual(len(r['images']),3)
    for i in range(3):
        data=image_bytes(l,lb,i);self.assertEqual(data,image_bytes(r,rb,i));self.assertEqual(Image.open(io.BytesIO(data)).size,(2048,2048))
 def test_allocation_regions_disjoint_including_left_right(self):
    regs=json.loads((R/'textures/HOPPER_Arms_UV_Islands.json').read_text());self.assertEqual(len(regs),450)
    sides={r['name'][0] for r in regs};self.assertEqual(sides,{'L','R'})
    for i,a in enumerate(regs):
        x,y,w,h=a['outer_rect'];self.assertGreaterEqual(min(x,y),0);self.assertLessEqual(max(x+w,y+h),2048);self.assertEqual(a['padding'],6)
        for other in regs[i+1:]:
            xx,yy,ww,hh=other['outer_rect'];self.assertFalse(x<xx+ww and xx<x+w and y<yy+hh and yy<y+h,(a['name'],other['name']))
 def test_armor_density_priority(self):
    uv=self.report['uv'];self.assertGreater(uv['armor_to_frame_linear_density_ratio'],4.5);self.assertGreater(uv['groups']['armor']['used_uv_share'],.85)
 def test_mirrored_world_geometry(self):
    clouds={}
    for s,(g,b) in self.mods.items():
        mats=world_matrices(g);ps=[]
        for i,n in enumerate(g['nodes']):
            if 'mesh' in n:
                for p in g['meshes'][n['mesh']]['primitives']:
                    a=accessor(g,b,p['attributes']['POSITION']);ps.extend((a@mats[i][:3,:3].T+mats[i][:3,3]).tolist())
        a=np.round(np.array(ps),5)
        if s=='L':a[:,0]*=-1
        clouds[s]=sorted(map(tuple,a.tolist()))
    self.assertEqual(clouds['L'],clouds['R'])
 def test_original_base_hash_and_binary_prefix_preserved(self):
    self.assertEqual(hashlib.sha256((R/'reference/HOPPER_03_Legs_v4.glb').read_bytes()).hexdigest(),self.spec['source_sha256'])
    bg,bb=self.base;fg,fb=self.fit;n=bg['buffers'][0]['byteLength'];self.assertEqual(bb[:n],fb[:n])
 def test_original_nodes_meshes_materials_accessors_unchanged(self):
    bg,bb=self.base;fg,fb=self.fit
    for k in ['nodes','meshes','materials','images','textures','bufferViews','accessors']:
        self.assertEqual(bg[k],fg[k][:len(bg[k])],k)
 def test_original_cockpit_clips_unchanged(self):
    bg,bb=self.base;fg,fb=self.fit;self.assertEqual(bg['animations'],fg['animations']);self.assertEqual(len(fg['animations']),3)
 def test_manifest_matches_fitcheck_root_transforms(self):
    fg,fb=self.fit
    for s in 'LR':
        n=next(n for n in fg['nodes'] if n['name']==f'Arm_{s}_M1_Root')
        np.testing.assert_allclose(trs(n),trs(self.spec['sockets'][s]['scene_mount']),atol=1e-7)
 def test_source_socket_parent_scale_compensation(self):
    bg,bb=self.base;mats=world_matrices(bg)
    for s,sp in self.spec['sockets'].items():
        actual=mats[sp['source_node_index']]@trs(sp['under_source_socket_node'])
        np.testing.assert_allclose(actual,trs(sp['scene_mount']),atol=1e-7)
 def test_measured_register_and_floor_clearance(self):
    sp=self.spec;old=sp['existing_interface_m'];new=sp['module_interface_m']
    self.assertGreater(new['register_inner_diameter'],old['lip_max_outer_diameter'])
    self.assertAlmostEqual((new['register_inner_diameter']-old['lip_max_outer_diameter'])/2,new['radial_register_clearance'])
    self.assertEqual(new['minimum_cup_floor_clearance_to_existing_cap'],.014)
 def test_model_manifest_sha_matches_final_bytes(self):
    for s in 'LR':
        data=(R/f'models/HOPPER_03_Arm_{s}_M1.glb').read_bytes();rep=self.report['module_files'][s]
        self.assertEqual(len(data),rep['bytes']);self.assertEqual(hashlib.sha256(data).hexdigest(),rep['sha256'])
if __name__=='__main__':unittest.main()
