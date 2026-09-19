"""Reproducible delivery checks. Dependencies: numpy, Pillow, shapely, trimesh.
This is a structural/geometry validator, NOT the Khronos official validator.
Blender and Unreal execution status is deliberately reported separately.
"""
from __future__ import annotations
import hashlib,io,json,struct,py_compile
from pathlib import Path
import numpy as np
from PIL import Image
from shapely.geometry import Polygon
from shapely.strtree import STRtree
import shapely
import trimesh

ROOT=Path(__file__).resolve().parents[1]

def check(condition,message):
 if not condition:raise AssertionError(message)


def main():
 glb=ROOT/'Model/SM_ATV_Stylized.glb';data=glb.read_bytes()
 magic,version,total=struct.unpack_from('<4sII',data)
 check(magic==b'glTF' and version==2 and total==len(data),'GLB header')
 off=12;chunks=[]
 while off<len(data):
  n,kind=struct.unpack_from('<I4s',data,off);off+=8;check(n%4==0,'GLB chunk alignment')
  chunks.append((kind,data[off:off+n]));off+=n
 check(off==len(data) and len(chunks)==2,'GLB chunks length')
 check(chunks[0][0]==b'JSON' and chunks[1][0]==b'BIN\x00','GLB chunk types')
 doc=json.loads(chunks[0][1]);blob=chunks[1][1]
 check(doc['asset']['version']=='2.0','glTF version')
 for v in doc['bufferViews']:
  check(v.get('byteOffset',0)+v['byteLength']<=len(blob),'Buffer view range')
 def acc(index):
  a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
  types={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'};cols={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
  offset=v.get('byteOffset',0)+a.get('byteOffset',0);arr=np.frombuffer(blob,dtype=types[a['componentType']],count=a['count']*cols,offset=offset)
  check(arr.nbytes<=v['byteLength'],'Accessor range')
  return arr.reshape(a['count'],cols)
 check(len(doc['meshes'])==1 and len(doc['materials'])==1,'Single mesh/material')
 primitive=doc['meshes'][0]['primitives'][0];check(len(doc['meshes'][0]['primitives'])==1,'Single primitive')
 v=acc(primitive['attributes']['POSITION']);n=acc(primitive['attributes']['NORMAL']);uv=acc(primitive['attributes']['TEXCOORD_0']);f=acc(primitive['indices']).reshape(-1,3)
 check(len(v)==len(n)==len(uv),'Attribute counts')
 check(f.max()<len(v),'Index bounds')
 check(0<len(f)<10000,'Triangle budget')
 check(np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all(),'Finite values')
 check(np.all(abs(np.linalg.norm(n,axis=1)-1)<1e-4),'Unit vertex normals')
 check(uv.min()>=0 and uv.max()<=1,'UV range')
 cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
 areas=np.linalg.norm(cross,axis=1)*.5
 check(areas.min()>1e-10,'Nondegenerate geometry')
 check(np.all(np.sum(cross*n[f].mean(1),axis=1)>0),'Winding/normal consistency')
 # Confirm previews/source use the exact exported geometry and UVs.
 mesh=np.load(ROOT/'Source/mesh_data.npz');rot=np.array([[1,0,0],[0,0,1],[0,-1,0]],np.float32)
 check(np.array_equal(f,mesh['faces']),'Exported indices match source')
 check(np.allclose(v,mesh['vertices']@rot.T,atol=1e-7),'Exported positions match source')
 check(np.allclose(n,mesh['normals']@rot.T,atol=1e-7),'Exported normals match source')
 check(np.allclose(uv[:,0],mesh['uv'][:,0]) and np.allclose(uv[:,1],1-mesh['uv'][:,1]),'Exported UVs match source')
 # Test actual triangle areas; shared edges are allowed, shared texture area is not.
 polygons=np.array([Polygon(t) for t in uv[f]],dtype=object)
 uvareas=shapely.area(polygons);check(uvareas.min()>1e-14,'Nondegenerate UV triangles')
 tree=STRtree(polygons);pairs=tree.query(polygons,predicate='intersects');pairs=pairs[:,pairs[0]<pairs[1]]
 intersections=shapely.intersection(polygons[pairs[0]],polygons[pairs[1]])
 overlap_areas=shapely.area(intersections)
 overlaps=overlap_areas>1e-11
 check(not overlaps.any(),f'Overlapping UV triangle pairs: {int(overlaps.sum())}')
 image_checks=[]
 for i,filename in enumerate(['T_ATV_BaseColor.png','T_ATV_ORM.png','T_ATV_Emissive.png']):
  view=doc['bufferViews'][doc['images'][i]['bufferView']];start=view.get('byteOffset',0);imagebytes=blob[start:start+view['byteLength']]
  check(imagebytes==(ROOT/'Textures'/filename).read_bytes(),'Embedded texture matches external file: '+filename)
  image=Image.open(io.BytesIO(imagebytes));check(image.size==(2048,2048),'Texture dimensions')
  image_checks.append({'file':filename,'size':list(image.size),'sha256':hashlib.sha256(imagebytes).hexdigest()})
 check(all('uri' not in image for image in doc['images']),'No external GLB image dependencies')
 check(all(s['wrapS']==33071 and s['wrapT']==33071 for s in doc['samplers']),'Clamp, no UV tiling')
 loaded=trimesh.load(str(glb),force='scene',process=False)
 check(sum(len(g.faces) for g in loaded.geometry.values())==len(f),'Independent trimesh import')
 for file in ROOT.rglob('*.py'):py_compile.compile(str(file),doraise=True)
 charts=json.loads((ROOT/'Source/UV_Charts.json').read_text())
 extent=np.ptp(mesh['vertices'],axis=0)
 report={
  'status':'PASS', 'model_file':'Model/SM_ATV_Stylized.glb',
  'triangles':int(len(f)), 'triangle_limit_exclusive':10000,'triangle_budget_remaining_to_10000':int(10000-len(f)),
  'vertices_with_uv_and_normal_seams':int(len(v)), 'meshes':1,'material_slots':1,'render_primitives':1,
  'uv_channels_in_glb':1,'uv_charts':len(charts),'uv_range':[float(uv.min()),float(uv.max())],
  'uv_positive_area_overlap_pairs':int(overlaps.sum()),'uv_area_overlap_tolerance':1e-11,
  'uv_triangle_area_coverage_percent':round(float(uvareas.sum())*100,3),
  'uv_sharing':'No stacked/mirrored-overlapping islands; adjacent triangles may share UV edges.',
  'degenerate_geometry_triangles':0,'degenerate_uv_triangles':0,'normal_winding_inconsistencies':0,
  'dimensions_metres_blender_xyz':[round(float(x),6) for x in extent],
  'ground_pivot_z_metres':float(mesh['vertices'][:,2].min()),'source_forward':'+X','blender_up':'+Z','glb_up':'+Y',
  'pbr_textures':image_checks,'base_color_source':'Source/AI_Painted_Source.png; image-generated and reprojected into unique UV regions',
  'periodic_texture_patterns':False,'normal_map':False,'ao_method':'Mesh ray-traced bake; packed in ORM.R',
  'rigged':False,'animation_clips':0,'single_closed_printable_solid':'Not a target: game mesh uses intersecting/disconnected part shells.',
  'independent_glb_import':'PASS: trimesh', 'source_and_preview_geometry_equals_glb':True,
  'python_syntax_check':'PASS', 'geometry_kernel_executed':True,
  'blender_bpy_adapter_executed':False,'unreal_5_7_editor_executed':False,
  'official_khronos_validator_executed':False,
  'limitations':['Reconstructed from a reference image, not a scan or exact CAD match.','Blender/Unreal wrappers were not run inside those editors in this environment.','Preview files are CPU reference renders of the delivered geometry, not UE screenshots.']
 }
 (ROOT/'Validation/asset_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print(json.dumps(report,indent=2))

if __name__=='__main__':main()
