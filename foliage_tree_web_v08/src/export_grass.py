"""Export the exact production grass mesh to GLB, retaining wind inputs in UV sets."""
from pathlib import Path
import subprocess,json,struct
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
script="const E=require('./src/environment.js'),s=require('./assets/scene.json');process.stdout.write(JSON.stringify(E.buildGrass(s.trunk)));"
m=json.loads(subprocess.check_output(['node','-e',script],cwd=ROOT,text=True))
(ROOT/'assets/root_grass.json').write_text(json.dumps(m,separators=(',',':')))
binary=bytearray();views=[];access=[]
def attribute(data,components,kind='f',target=34962):
 a=np.asarray(data,dtype='<f4' if kind=='f' else '<u4').reshape(-1,components)
 while len(binary)%4:binary.append(0)
 off=len(binary);binary.extend(a.tobytes());views.append({'buffer':0,'byteOffset':off,'byteLength':a.nbytes,'target':target})
 item={'bufferView':len(views)-1,'componentType':5126 if kind=='f' else 5125,'count':len(a),'type':{1:'SCALAR',2:'VEC2',3:'VEC3',4:'VEC4'}[components]}
 item['min']=a.min(0).tolist();item['max']=a.max(0).tolist();access.append(item);return len(access)-1
p=np.asarray(m['position']).reshape(-1,3);n=np.asarray(m['normal']).reshape(-1,3);n/=np.linalg.norm(n,axis=1)[:,None]
c=np.asarray(m['color']).reshape(-1,3);c=np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
r=np.asarray(m['pivot']).reshape(-1,3);height=np.asarray(m['proxyNormal']).reshape(-1,3)[:,0]
attrs={'POSITION':attribute(p,3),'NORMAL':attribute(n,3),'COLOR_0':attribute(c,3),'TEXCOORD_0':attribute(m['uv'],2),
 'TEXCOORD_1':attribute(r[:,[0,2]],2),'TEXCOORD_2':attribute(np.stack([m['phase'],height],axis=1),2),
 'TEXCOORD_3':attribute(np.stack([r[:,1],m['bunchIndex']],axis=1),2)}
idx=attribute(m['indices'],1,'i',34963)
extras={'units':'metres','axes':'RH Y up','wind':{'TEXCOORD_0':'across blade, height weight (root=0 tip=1)','TEXCOORD_1':'root X, root Z in web local metres','TEXCOORD_2':'phase radians, full blade height metres','TEXCOORD_3':'root Y metres, tuft ID'},'grass':m['meta'],'warning':'Static export. Apply GrassWind.hlsl or the documented equivalent to animate.'}
gltf={'asset':{'version':'2.0','generator':'foliage-tree-web-v08/export_grass.py'},'extensionsUsed':['KHR_materials_unlit'],'scene':0,'scenes':[{'nodes':[0]}],
 'nodes':[{'name':'Root_Grass_v08','mesh':0}],'meshes':[{'name':'Root_Grass_v08','primitives':[{'attributes':attrs,'indices':idx,'material':0}],'extras':extras}],
 'materials':[{'name':'Grass_Vertex_Color','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'metallicFactor':0,'roughnessFactor':1},'doubleSided':True,'extensions':{'KHR_materials_unlit':{}}}],
 'bufferViews':views,'accessors':access,'buffers':[{'byteLength':len(binary)}]}
j=json.dumps(gltf,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary+=b'\0'*((-len(binary))%4)
body=struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\0')+binary
out=ROOT/'models/root_grass_v08.glb';out.write_bytes(struct.pack('<4sII',b'glTF',2,12+len(body))+body)
print(json.dumps({'file':str(out),'vertices':len(p),'triangles':len(m['indices'])//3,'tufts':m['meta']['tufts'],'bytes':out.stat().st_size},indent=2))
