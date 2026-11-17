"""Second-loader GLB verification with trimesh (not the custom meshcore reader)."""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1]

def main():
    manifest=json.loads((ROOT/'asset_manifest.json').read_text());results=[]
    for a in manifest['assets']:
        item={'id':a['id'],'pass':False}
        try:
            scene=trimesh.load(ROOT/a['file'],file_type='glb',force='scene',process=False)
            if len(scene.geometry)!=1:raise AssertionError('Expected exactly one geometry')
            mesh=next(iter(scene.geometry.values()))
            if len(mesh.faces)!=a['triangles']:raise AssertionError('Face count differs')
            if not np.isfinite(mesh.vertices).all():raise AssertionError('Non-finite vertex')
            lo,hi=a['bounds_m_source'];expected=np.array([[lo[0],lo[2],-hi[1]],[hi[0],hi[2],-lo[1]]])
            if not np.allclose(scene.bounds,expected,atol=2e-5):raise AssertionError('glTF coordinate bounds differ')
            material=mesh.visual.material
            if material.baseColorTexture.size!=(1024,1024):raise AssertionError('Base-color image missing/incorrect')
            if material.metallicRoughnessTexture.size!=(1024,1024):raise AssertionError('Rough-metal image missing/incorrect')
            if mesh.visual.uv is None or len(mesh.visual.uv)!=len(mesh.vertices):raise AssertionError('UVs missing')
            item.update({'pass':True,'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'glb_bounds_m':scene.bounds.tolist(),'textures_loaded':2})
        except Exception as exc:item['error']=str(exc)
        results.append(item)
    report={'all_passed':all(x['pass'] for x in results),'loader':'trimesh','version':trimesh.__version__,'assets':results,
            'boundary':'Independent file reader only. Not Blender/UE runtime verification or official Khronos validation.'}
    (ROOT/'reports/independent_readback.json').write_text(json.dumps(report,indent=2))
    print(('PASS' if report['all_passed'] else 'FAIL')+f' — {sum(x["pass"] for x in results)}/{len(results)} GLBs read with trimesh {trimesh.__version__}')
    for x in results:
        if not x['pass']:print(x)
    return 0 if report['all_passed'] else 1
if __name__=='__main__':sys.exit(main())
