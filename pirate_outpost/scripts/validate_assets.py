"""Validate every shipped GLB and produce a machine-readable evidence report."""
from pathlib import Path
import json,hashlib,io,sys
import numpy as np
from PIL import Image
from meshcore import ROOT,read_glb,read_accessor,GLTF_BASIS

def main():
 manifest=json.loads((ROOT/'asset_manifest.json').read_text());results=[];errors=[]
 for asset in manifest['assets']:
  path=ROOT/asset['file'];doc,bb=read_glb(path);p=doc['meshes'][0]['primitives'][0]
  v=read_accessor(doc,bb,p['attributes']['POSITION']);n=read_accessor(doc,bb,p['attributes']['NORMAL']);uv=read_accessor(doc,bb,p['attributes']['TEXCOORD_0']);f=read_accessor(doc,bb,p['indices']).reshape(-1,3)
  fail=[]
  for label,array in [('vertices',v),('normals',n),('uv',uv)]:
   if not np.isfinite(array).all():fail.append(label+' contains non-finite data')
  if f.max()>=len(v):fail.append('Index out of range')
  if not ((uv>=0)&(uv<=1)).all():fail.append('UV outside atlas')
  nlen=np.linalg.norm(n,axis=1)
  if np.any(abs(nlen-1)>1e-3):fail.append('Non-unit vertex normals')
  cr=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);area=np.linalg.norm(cr,axis=1)/2
  if np.any(area<1e-12):fail.append('Zero-area triangle')
  original=v@GLTF_BASIS
  if asset['pivot']=='ground_base' and abs(original[:,2].min())>1e-4:fail.append('Ground pivot not at base')
  if len(f)!=asset['triangles']:fail.append('Triangle count mismatch')
  sizes=[]
  for image in doc['images']:
   view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0)
   with Image.open(io.BytesIO(bb[start:start+view['byteLength']])) as im:sizes.append(im.size)
   if max(sizes[-1])>1024:fail.append('Texture over 1024')
  if any('normalTexture' in m for m in doc['materials']):fail.append('Forbidden normal map')
  if len(doc['meshes'])!=1 or len(doc['nodes'])!=1:fail.append('Not a standalone one-mesh asset')
  # Back-facing authored normals are reported, not silently claimed to be manifold.
  dots=np.sum(cr*n[f].mean(1),axis=1)
  reverse=int(np.sum(dots< -1e-8))
  r={'id':asset['id'],'pass':not fail,'errors':fail,'triangles':len(f),'vertices':len(v),'min_area_m2':float(area.min()),'texture_sizes':sizes,'reverse_normal_triangles':reverse,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  results.append(r)
  if fail:errors.extend([asset['id']+': '+q for q in fail])
 # Ensure the scene references real, unique asset identifiers.
 names={x['id'] for x in manifest['assets']}
 for file in ['harbor_layout.json','gallery_layout.json']:
  doc=json.loads((ROOT/'layout'/file).read_text());labels=set()
  for item in doc['instances']:
   if item['asset'] not in names:errors.append(file+' unknown asset '+item['asset'])
   if item['name'] in labels:errors.append(file+' duplicate instance label '+item['name'])
   labels.add(item['name'])
 report={'all_passed':not errors,'asset_count':len(results),'total_triangles_unique_assets':sum(x['triangles'] for x in results),'total_vertices_unique_assets':sum(x['vertices'] for x in results),'errors':errors,'assets':results,'not_tested':['Blender runtime execution','Unreal Editor runtime execution','Target game performance','Baked lightmap unwrap','Animated interactions'],'method':'Custom GLB buffer/geometry validator plus separate actual-mesh VTK previews. Not the official Khronos validator.'}
 (ROOT/'reports'/'validation.json').write_text(json.dumps(report,indent=2))
 print('PASS' if not errors else 'FAIL','assets=',len(results),'triangles=',report['total_triangles_unique_assets'])
 for e in errors:print(e)
 rev=[(x['id'],x['reverse_normal_triangles']) for x in results if x['reverse_normal_triangles']]
 print('Authored-normal winding review:',rev)
 return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
