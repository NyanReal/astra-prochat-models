from pathlib import Path
import importlib.util
ROOT = Path(__file__).resolve().parents[1]
def test_core_module_exists():
    assert (ROOT / 'generation' / 'mesh_core.py').is_file(), 'Mesh/UV/export core has not been implemented'

def test_cube_geometry_uv_and_embedded_glb(tmp_path):
    import sys, numpy as np
    sys.path.insert(0,str(ROOT/'generation'))
    from mesh_core import Mesh,bake,read_glb,write_glb
    m=Mesh('test_cube');m.box((0,0,.5),(1,1,1))
    meta,arrays,images=bake(m,texel_density=32,max_size=256,write=False)
    v,n,uv,f=arrays
    assert len(f)==12
    assert np.all(np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)>0)
    assert (uv>=0).all() and (uv<=1).all()
    for i,a in enumerate(m.charts):
        x,y,w,h=a.rect
        for b in m.charts[i+1:]:
            xx,yy,ww,hh=b.rect
            assert x+w<=xx or xx+ww<=x or y+h<=yy or yy+hh<=y
    p=tmp_path/'cube.glb'
    write_glb(p,'cube',*arrays,*images)
    d,bin=read_glb(p)
    assert d['accessors'][0]['min']==[-.5,0.,-.5]
    assert len(d['images'])==3
    assert all('bufferView' in i for i in d['images'])
    assert d['samplers'][0]['wrapS']==33071

def test_leaf_front_normals_face_up():
    import sys,numpy as np
    sys.path.insert(0,str(ROOT/'generation'))
    from mesh_core import Mesh
    m=Mesh('leaf');m.leaf((0,0,0))
    c=m.charts[0];v=c.vertices;f=c.faces
    n=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    assert (n[:,2]>0).all(), 'Leaf front faces point below the canopy'

def test_waterfall_source_available():
    import sys
    sys.path.insert(0,str(ROOT/'generation'))
    from mesh_core import source_images
    assert 'waterfall' in source_images()

def test_scene_math_module_exists():
    assert (ROOT/'generation'/'scene_math.py').is_file(), 'Camera/space conversion contract missing'

def test_camera_round_trip():
    import sys,numpy as np
    sys.path.insert(0,str(ROOT/'generation'))
    from scene_math import pixel_to_world,world_to_pixel
    for x,y,z in [(0,0,0),(768,512,1.55),(1250,230,4.7),(630,585,1.7)]:
        assert np.allclose(world_to_pixel(pixel_to_world(x,y,z)),[x,y],atol=1e-8)

def test_irregular_ground_has_no_self_overlapping_uv_faces():
    import sys
    sys.path.insert(0,str(ROOT/'generation'))
    from environment import ground
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    m=ground('test_ground',110)
    for c in m.charts:
        polys=[Polygon(c.uv[f]) for f in c.faces]
        assert sum(p.area for p in polys)-unary_union(polys).area < 1e-10

def test_scene_rebuild_is_deterministic_even_in_the_same_python_process(tmp_path,monkeypatch):
    import sys,shutil
    sys.path.insert(0,str(ROOT/'generation'))
    import build_scene
    (tmp_path/'data').mkdir()
    shutil.copyfile(ROOT/'data/assets.json',tmp_path/'data/assets.json')
    monkeypatch.setattr(build_scene,'ROOT',tmp_path)
    build_scene.main();first=(tmp_path/'data/scene.json').read_bytes()
    build_scene.main();second=(tmp_path/'data/scene.json').read_bytes()
    assert first==second, 'Scene state leaked across rebuilds'
