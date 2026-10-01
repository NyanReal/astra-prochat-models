"""Rebuild separate modules, textures, manifest and fit-check without editing v4."""
from pathlib import Path
import json,base64,hashlib
import numpy as np
from interface import measure
from arms import build_arm
from atlas import write_atlas
from module_export import export_modules
from glb_io import read_glb,triangles,bounds
ROOT=Path(__file__).resolve().parents[1]

def main():
    spec=measure(ROOT/'reference/HOPPER_03_Legs_v4.glb');scenes={};parts={}
    for side in 'LR':scenes[side],parts[side]=build_arm(side,spec)
    count=sum(r['triangles'] for r in parts.values())
    assert spec['base_triangles']+count<30000,'Hard triangle budget exceeded'
    patches=[p for s in scenes.values() for p in s.patches]
    for p in patches:
        assert np.isfinite(p.positions).all() and np.isfinite(p.normals).all()
        assert np.allclose(np.linalg.norm(p.normals,axis=1),1,atol=1e-5)
    print('Geometry:',count,'pair triangles /',len(patches),'atlas regions',flush=True)
    uv=write_atlas(patches,ROOT/'textures');uv['scope']='Independent arm modules only; shared atlas, separate non-overlapping L/R allocations.'
    integrity=export_modules(scenes,spec,ROOT)
    bg,bb=read_glb(ROOT/'preview/FitCheck.glb')
    report={'asset':'HOPPER 03 detachable arm modules v5','interface':'H03-M1','base_triangles':spec['base_triangles'],
            'module_triangles':{k:v['triangles'] for k,v in parts.items()},'pair_triangles':count,'assembled_triangles':triangles(bg),
            'triangles':count,'remaining_below_30000':29999-triangles(bg),'assembly_parts':parts,'units':'meters','uv':uv,'integrity':integrity,
            'fitcheck_bounds_m':bounds(bg,bb).tolist(),'module_bounds_m':{},'glb_bytes':(ROOT/'preview/FitCheck.glb').stat().st_size,
            'module_files':{},'animations':'None in separate arm modules. Original 3 cockpit clips remain in fit-check scene.',
            'limitations':['Rigid reference-pose arms, not an actuated arm rig or range-of-motion solver.','New project connector convention, not a manufacturing standard.',
                          'Painted procedural PBR atlas; not a newly image-generated texture.','iPad/Safari and Blender/Unreal native application tests not performed.']}
    for side in 'LR':
        f=ROOT/f'models/HOPPER_03_Arm_{side}_M1.glb';g,b=read_glb(f);report['module_bounds_m'][side]=bounds(g,b).tolist()
        report['module_files'][side]={'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    for name,obj in [('socket_spec.json',spec),('asset_report.json',report)]:
        (ROOT/'docs'/name).write_text(json.dumps(obj,indent=2),encoding='utf8')
    (ROOT/'preview/asset-info.js').write_text('window.HOPPER_INFO='+json.dumps(report,separators=(',',':'))+';\nwindow.HOPPER_SOCKET_SPEC='+json.dumps(spec,separators=(',',':'))+';\n')
    (ROOT/'preview/model-data.js').write_text('window.HOPPER_GLB_BASE64="'+base64.b64encode((ROOT/'preview/FitCheck.glb').read_bytes()).decode()+'";\n')
    print(json.dumps({k:report[k] for k in ['module_triangles','pair_triangles','assembled_triangles','remaining_below_30000']},indent=2),flush=True)
    print('UV armor/frame density',uv['armor_to_frame_linear_density_ratio'],flush=True)
if __name__=='__main__':main()
