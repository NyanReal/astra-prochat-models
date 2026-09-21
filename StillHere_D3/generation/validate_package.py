"""Validate exported files, meshes, UVs, transforms and script syntax.

This does NOT run Blender or Unreal. Those boundaries are written into the report.
Dependencies: numpy, Pillow, scipy, shapely, trimesh (validation-only extras).
"""
from pathlib import Path
from collections import Counter
import json,ast,hashlib,io,time
import numpy as np
from PIL import Image
from shapely.geometry import Polygon
from shapely.ops import unary_union
import trimesh
from mesh_core import ROOT,read_glb
from scene_math import world_to_pixel


def require(value,message):
    if not value:raise AssertionError(message)


def validate_asset(asset):
    aid=asset['id'];d=np.load(ROOT/asset['mesh_data']);v=d['vertices'];f=d['faces'];uv=d['uv'];n=d['normals']
    for key in ('glb','mesh_data','base_color','normal','orm'):
        path=(ROOT/asset[key]).resolve();path.relative_to(ROOT.resolve());require(path.is_file(),f'{aid}: missing {key}')
    require(len(f)==asset['triangles'],aid+': triangle count')
    require(all(np.isfinite(a).all() for a in [v,uv,n]),aid+': non-finite values')
    require(int(f.max())<len(v),aid+': invalid indices')
    require((uv>=0).all() and (uv<=1).all(),aid+': UV outside unique atlas')
    area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)*.5
    require(float(area.min())>1e-11,aid+': degenerate triangle')
    require(np.max(np.abs(np.linalg.norm(n,axis=1)-1))<.0002,aid+': non-unit normals')
    chart_doc=json.loads((ROOT/f'data/uv/{aid}.json').read_text());res=chart_doc['resolution'];pad=chart_doc['padding'];occupied=np.zeros((res,res),np.uint8)
    for c in chart_doc['charts']:
        x,y,w,h=c['rect_pixels'];require(x>=pad and y>=pad and x+w+pad<=res and y+h+pad<=res,aid+': chart padding outside atlas')
        region=occupied[y-pad:y+h+pad,x-pad:x+w+pad];require(not np.any(region),aid+': chart or gutter overlap');region[:]=1
    polys=[Polygon(t) for t in uv[f]];summed=sum(p.area for p in polys);union=unary_union(polys).area;overlap=max(0.,summed-union)
    require(overlap<1e-7,f'{aid}: UV self-overlap {overlap}')
    glb,binary=read_glb(ROOT/asset['glb']);require(glb['nodes'][0]['extras']['asset_id']==aid,aid+': GLB ID mismatch')
    require(len(glb['images'])==3,aid+': missing embedded texture')
    require(glb['samplers'][0]['wrapS']==33071 and glb['samplers'][0]['wrapT']==33071,aid+': repeat sampler')
    for image,role in zip(glb['images'],['base_color','normal','orm']):
        view=glb['bufferViews'][image['bufferView']];data=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
        im=Image.open(io.BytesIO(data));require(im.size==(res,res),aid+': embedded texture size')
        external=Image.open(ROOT/asset[role]);require(np.array_equal(np.asarray(im),np.asarray(external)),aid+': GLB/external texture pixels differ')
    # Independent import through trimesh, not our own GLB decoder.
    imported=trimesh.load_scene(ROOT/asset['glb'],process=False)
    require(sum(len(g.faces) for g in imported.geometry.values())==len(f),aid+': independent GLB import triangle mismatch')
    gv=v[:,[0,2,1]].copy();gv[:,2]*=-1
    require(np.allclose(imported.bounds,np.vstack([gv.min(0),gv.max(0)]),atol=1e-5),aid+': independent GLB bounds mismatch')
    return {'id':aid,'triangles':len(f),'vertices':len(v),'uv_charts':len(chart_doc['charts']),'atlas_resolution':res,
            'uv_overlap_area':float(overlap),'minimum_triangle_area_m2':float(area.min()),'independent_glb_import':'pass','embedded_external_texture_match':'pass'}


def main():
    t0=time.time();assets=json.loads((ROOT/'data/assets.json').read_text())['assets'];lookup={a['id']:a for a in assets};scene=json.loads((ROOT/'data/scene.json').read_text())
    results=[]
    for i,a in enumerate(assets):
        print(f'Validate {i+1}/{len(assets)} {a["id"]}',flush=True);results.append(validate_asset(a))
    ids=set();counts=Counter()
    for rec in scene['instances']:
        require(rec['id'] not in ids,'Duplicate instance ID: '+rec['id']);ids.add(rec['id']);require(rec['asset_id'] in lookup,'Missing referenced asset')
        require(len(rec['position_m'])==3 and len(rec['scale'])==3,'Malformed instance transform')
        require(min(rec['scale'])>0,'Non-positive source scale');require(np.isfinite(rec['position_m']+rec['scale']+rec['rotation_quat_xyzw']).all(),'Non-finite instance')
        require(abs(np.linalg.norm(rec['rotation_quat_xyzw'])-1)<1e-5,'Non-unit instance quaternion');counts[rec['asset_id']]+=1
    residuals=[]
    for anchor in scene['reference_anchors']:
        residual=float(np.linalg.norm(world_to_pixel(anchor['world_anchor_m'])-anchor['reference_anchor_px']));require(residual<1e-5,'Camera anchor round trip');residuals.append(residual)
    scripts=[]
    for folder in ('generation','blender','ue5'):
        for path in (ROOT/folder).glob('*.py'):
            ast.parse(path.read_text(encoding='utf8'),filename=str(path));scripts.append(str(path.relative_to(ROOT)))
    report={'status':'pass','assets_checked':len(assets),'scene_assets_used':len(counts),'instances_checked':len(ids),
            'unique_asset_triangles':sum(a['triangles'] for a in assets),'placed_triangles_before_culling':sum(lookup[k]['triangles']*v for k,v in counts.items()),
            'maximum_uv_overlap_area':max(r['uv_overlap_area'] for r in results),'maximum_camera_anchor_round_trip_error_px':max(residuals),
            'camera_check_scope':'Projection mathematics only; not a pixel similarity score against the original illustration.',
            'editor_execution':{'blender':'not executed — executable unavailable','unreal':'not executed — executable unavailable'},
            'preview_renderer':'VTK offscreen OpenGL; actual exported geometry and placements, not generated artwork',
            'script_syntax_checked':scripts,'asset_results':results,'elapsed_seconds':round(time.time()-t0,3)}
    (ROOT/'validation/report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('asset_results','script_syntax_checked')},indent=2),flush=True)

if __name__=='__main__':main()
