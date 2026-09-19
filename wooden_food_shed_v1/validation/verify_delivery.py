"""Independent binary, geometry, texture and round-trip checks.
Requires numpy, Pillow and trimesh. Does not execute Blender or Unreal.
"""
from pathlib import Path
import ast, hashlib, io, json, struct
import numpy as np
from PIL import Image
import trimesh
ROOT=Path(__file__).resolve().parents[1]

def glb(path):
    raw=path.read_bytes(); magic,ver,total=struct.unpack_from('<4sII',raw)
    assert magic==b'glTF' and ver==2 and total==len(raw)
    n,tag=struct.unpack_from('<I4s',raw,12);assert tag==b'JSON'
    doc=json.loads(raw[20:20+n]);length,tag=struct.unpack_from('<I4s',raw,20+n);assert tag==b'BIN\0'
    binary=raw[28+n:28+n+length]
    def acc(i):
        a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']]
        types={5126:'<f4',5123:'<u2',5125:'<u4'};dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        ar=np.frombuffer(binary,types[a['componentType']],count=a['count']*dim,offset=v.get('byteOffset',0)+a.get('byteOffset',0))
        return ar.reshape(-1,dim)
    return doc,binary,acc

def main():
    payload=json.loads((ROOT/'source/mesh_payload.json').read_text())
    results={}; density=payload['pixels_per_meter'];all_density=[]
    for obj in payload['objects']:
        p=np.array(obj['positions']);n=np.array(obj['normals']);uv=np.array(obj['uvs']);f=np.array(obj['triangles'])
        cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
        area=np.linalg.norm(cross,axis=1)/2
        assert area.min()>1e-9,(obj['name'],'degenerate triangle')
        align=(cross/np.linalg.norm(cross,axis=1)[:,None]*n[f[:,0]]).sum(1)
        assert align.min()>.9999,(obj['name'],'inconsistent winding')
        a=uv[f[:,1]]-uv[f[:,0]];b=uv[f[:,2]]-uv[f[:,0]]
        uvarea=(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
        assert uvarea.min()>0,(obj['name'],'mirrored/degenerate UV triangle')
        actual=np.sqrt(uvarea*4096**2/area);all_density.extend(actual)
    all_density=np.array(all_density)
    assert abs(all_density/density-1).max()<.002
    results['geometry']={'triangles':sum(len(o['triangles']) for o in payload['objects']),
        'degenerate_triangles':0,'winding_normal_mismatches':0,'mirrored_or_zero_area_uv_triangles':0,
        'actual_density_px_per_m_min':float(all_density.min()),'actual_density_px_per_m_max':float(all_density.max()),
        'actual_density_max_relative_error':float(abs(all_density/density-1).max())}
    models=[]
    for name in ['wooden_food_shed.glb','wooden_food_shed_closed.glb']:
        path=ROOT/'models'/name;doc,binary,acc=glb(path)
        pp=doc['meshes'][0]['primitives'][0];p=acc(pp['attributes']['POSITION']);n=acc(pp['attributes']['NORMAL']);uv=acc(pp['attributes']['TEXCOORD_0']);t=acc(pp['attributes']['TANGENT']);f=acc(pp['indices']).reshape(-1,3)
        assert len(f)==results['geometry']['triangles']<4000
        assert np.isfinite(p).all() and f.max()<len(p)
        assert np.max(np.abs(np.linalg.norm(n,axis=1)-1))<1e-5
        assert np.max(abs((t[:,:3]*n).sum(1)))<1e-5
        # All charts reverse V on glTF export, so tangent handedness must reverse.
        assert (t[:,3]==-1).all()
        for view in doc['bufferViews']:
            assert view.get('byteOffset',0)%4==0
            assert view.get('byteOffset',0)+view['byteLength']<=len(binary)
        image_info=[]
        for im in doc['images']:
            v=doc['bufferViews'][im['bufferView']];b=binary[v['byteOffset']:v['byteOffset']+v['byteLength']]
            image=Image.open(io.BytesIO(b));image.load();assert image.size==(4096,4096)
            assert image.mode in ('RGB','RGBA') and b[24]==8 and b[25] in (2,6)
            expected=ROOT/'textures'/(im['name']+'.png');assert hashlib.sha256(b).digest()==hashlib.sha256(expected.read_bytes()).digest()
            image_info.append({'name':im['name'],'size':list(image.size),'bytes':len(b)})
        loaded=trimesh.load(path,force='scene',process=False)
        assert len(loaded.geometry)==1 and sum(len(x.faces) for x in loaded.geometry.values())==len(f)
        if name=='wooden_food_shed.glb':
            original=np.concatenate([np.array(o['positions']) for o in payload['objects']])
            original=original[:,[0,2,1]]*np.array([1,1,-1])
            source_uv=np.concatenate([np.array(o['uvs']) for o in payload['objects']]);source_uv[:,1]=1-source_uv[:,1]
            assert np.allclose(original,p,atol=2e-6)
            assert np.allclose(source_uv,uv,atol=1e-7)
        models.append({'name':name,'bytes':path.stat().st_size,'triangles':len(f),'vertices':len(p),'embedded_images':image_info,'independent_trimesh_load':'PASS','single_mesh_single_material':len(doc['meshes'])==len(doc['materials'])==1})
    results['models']=models
    scripts=[]
    for file in sorted(ROOT.rglob('*.py')):
        if file.name.startswith('_debug'):continue
        ast.parse(file.read_text(encoding='utf-8'),filename=str(file));scripts.append(str(file.relative_to(ROOT)))
    results['python_syntax']={'status':'PASS','files':scripts}
    results['blender_editor_runtime']='NOT TESTED: Blender was unavailable in the execution environment.'
    results['unreal_5_7_editor_runtime']='NOT TESTED: Unreal Editor was unavailable. Official 5.7 API documentation was checked.'
    results['preview_source']='CPU rasterization of source mesh payload; positions/UVs independently matched against final open GLB binary.'
    (ROOT/'validation/verification_report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    stats=json.loads((ROOT/'validation/asset_stats.json').read_text());stats['runtime_verified']['GLB']='PASS: binary, embedded textures, source parity, independent trimesh round-trip';stats['actual_density_px_per_m_range']=[float(all_density.min()),float(all_density.max())]
    (ROOT/'validation/asset_stats.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
