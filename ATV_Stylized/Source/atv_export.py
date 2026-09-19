"""UV atlas packing and dependency-light GLB 2.0 writer, used in the delivered build.
No network dependency. Python + NumPy; Pillow needed only for guide generation.
"""
from __future__ import annotations
import json, math, struct
from pathlib import Path
import numpy as np
from atv_geometry import PALETTE, build_model

ATLAS_SIZE=2048
GUTTER=5


def try_pack(items, size):
 free=[(0,0,size,size)]; placed={}
 for key,ww,hh in sorted(items,key=lambda p: (-max(p[1:]),-min(p[1:]))):
  best=None
  for i,(x,y,w,h) in enumerate(free):
   for rot,(rw,rh) in enumerate([(ww,hh),(hh,ww)]):
    if rw<=w and rh<=h:
     score=(min(w-rw,h-rh),max(w-rw,h-rh),y,x)
     if best is None or score<best[0]:best=(score,x,y,rw,rh,rot)
  if best is None:return None
  _,x,y,w,h,rot=best;placed[key]=(x,y,w,h,bool(rot))
  new=[]
  for fx,fy,fw,fh in free:
   if x>=fx+fw or x+w<=fx or y>=fy+fh or y+h<=fy:new.append((fx,fy,fw,fh));continue
   if x>fx:new.append((fx,fy,x-fx,fh))
   if x+w<fx+fw:new.append((x+w,fy,fx+fw-x-w,fh))
   if y>fy:new.append((fx,fy,fw,y-fy))
   if y+h<fy+fh:new.append((fx,y+h,fw,fy+fh-y-h))
  new=list(dict.fromkeys(new));free=[]
  for i,a in enumerate(new):
   ax,ay,aw,ah=a
   if not any(j!=i and ax>=b[0] and ay>=b[1] and ax+aw<=b[0]+b[2] and ay+ah<=b[1]+b[3] for j,b in enumerate(new)):
    free.append(a)
 return placed


def pack_uv(m,size=ATLAS_SIZE):
 # A fixed deterministic binary search gives consistent topology/UVs in Blender.
 lo,hi=5.,600.
 best=None
 for _ in range(17):
  scale=(lo+hi)/2
  items=[(i,max(8,math.ceil(c.width*scale*math.sqrt(c.importance)))+GUTTER*2,max(8,math.ceil(c.height*scale*math.sqrt(c.importance)))+GUTTER*2) for i,c in enumerate(m.charts)]
  r=try_pack(items,size)
  if r is None:hi=scale
  else:lo=scale;best=r
 if best is None:raise RuntimeError('Atlas pack failed')
 uv=np.zeros((len(m.vertices),2),np.float32);local=np.asarray(m.uv_local)
 for i,c in enumerate(m.charts):
  x,y,w,h,rot=best[i];c.rect=best[i]
  inds=np.unique(np.asarray(m.faces)[c.triangles].ravel());q=local[inds].copy()
  if rot:q=np.column_stack((q[:,1],1-q[:,0]))
  # Array coordinates are top-left; runtime UVs are bottom-left.
  q=q*np.array([w-GUTTER*2,h-GUTTER*2])+[x+GUTTER,y+GUTTER]
  uv[inds,0]=q[:,0]/size;uv[inds,1]=1-q[:,1]/size
 return uv,lo


def save_glb(m,uv,path,texture_dir):
 verts,faces,normals=m.arrays()
 # Exactly the same axis conversion as Blender's glTF export: X,Y,Z -> X,Z,-Y.
 rot=np.array([[1,0,0],[0,0,1],[0,-1,0]],np.float32)
 verts=verts@rot.T;normals=normals@rot.T
 # glTF image convention is top-left, unlike Blender's UV display.
 texcoord=np.asarray(uv).copy();texcoord[:,1]=1-texcoord[:,1]
 blob=bytearray();views=[];accessors=[]
 def view(data,target=None):
  while len(blob)%4:blob.append(0)
  index=len(views);v={'buffer':0,'byteOffset':len(blob),'byteLength':len(data)}
  if target is not None:v['target']=target
  blob.extend(data);views.append(v);return index
 def accessor(arr,ctype,kind,limits=False,target=34962):
  idx=len(accessors);a={'bufferView':view(arr.tobytes(),target),'componentType':ctype,'count':len(arr),'type':kind}
  if limits:a.update(min=arr.min(0).tolist(),max=arr.max(0).tolist())
  accessors.append(a);return idx
 pidx=accessor(verts.astype('<f4'),5126,'VEC3',True)
 nidx=accessor(normals.astype('<f4'),5126,'VEC3')
 uidx=accessor(texcoord.astype('<f4'),5126,'VEC2')
 fidx=accessor(faces.astype('<u4').ravel(),5125,'SCALAR',False,34963)
 images=[]
 for filename in ['T_ATV_BaseColor.png','T_ATV_ORM.png','T_ATV_Emissive.png']:
  data=(Path(texture_dir)/filename).read_bytes();images.append({'name':filename[:-4],'bufferView':view(data),'mimeType':'image/png'})
 material={'name':'M_ATV_UniqueAtlas','doubleSided':False,'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'baseColorTexture':{'index':0},'metallicRoughnessTexture':{'index':1},'metallicFactor':1.,'roughnessFactor':1.},'occlusionTexture':{'index':1,'strength':.65},'emissiveTexture':{'index':2},'emissiveFactor':[.55,.55,.55]}
 doc={'asset':{'version':'2.0','generator':'ATV unique-UV parametric build 1.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'name':'SM_ATV_Stylized','mesh':0}],'meshes':[{'name':'SM_ATV_Stylized','primitives':[{'attributes':{'POSITION':pidx,'NORMAL':nidx,'TEXCOORD_0':uidx},'indices':fidx,'material':0,'mode':4}]}],'materials':[material],'textures':[{'source':i,'sampler':0} for i in range(3)],'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071}],'images':images,'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(blob)}],'extras':{'units':'metres','forwardAxis':'+X','upAxis':'+Y','triangleCount':len(faces),'uniqueUV':True,'rigged':False}}
 js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);blob+=b'\0'*((-len(blob))%4)
 total=12+8+len(js)+8+len(blob)
 data=struct.pack('<4sII',b'glTF',2,total)+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(blob),b'BIN\0')+blob
 Path(path).write_bytes(data)
 return doc


def guide_images(m,uv,root,size=ATLAS_SIZE):
 from PIL import Image,ImageDraw
 root=Path(root);atlas=Image.new('RGB',(size,size),(31,34,34));draw=ImageDraw.Draw(atlas)
 masks=Image.new('I',(size,size),0);md=ImageDraw.Draw(masks)
 wire=Image.new('RGB',(size,size),(245,244,238));wd=ImageDraw.Draw(wire)
 # The guide has per-surface reference colors. It is not the painted deliverable.
 va=np.asarray(m.vertices);norm=np.asarray(m.normals);faces=np.asarray(m.faces)
 for i,f in enumerate(faces):
  cid=m.face_chart[i];c=m.charts[cid];color=np.array(PALETTE[c.material][0],float)
  # Just enough orientation cue to make the texture-paint template legible.
  n=norm[f].mean(0);fac=.92+.08*max(0,n[2])
  color=np.clip(color*fac,0,255).astype(int)
  pts=[(float(uv[j,0]*size),float((1-uv[j,1])*size)) for j in f]
  draw.polygon(pts,fill=tuple(color));md.polygon(pts,fill=cid+1);wd.line(pts+[pts[0]],fill=(89,112,113),width=1)
 atlas.save(root/'Source'/'UV_Paint_Template.png')
 masks.save(root/'Source'/'UV_Chart_IDs.tiff')
 wire.save(root/'Textures'/'ATV_UV_Wire.png')
 # Material maps use non-color linear values; generated painted variation is added later.
 ids=np.array(masks);orm=np.zeros((size,size,3),np.uint8);orm[:,:,0]=255;orm[:,:,1]=220
 em=np.zeros_like(orm)
 for i,c in enumerate(m.charts):
  sel=ids==i+1;_,rough,metal=PALETTE[c.material];orm[sel,1]=round(rough*255);orm[sel,2]=round(metal*255)
  if c.material=='lamp':em[sel]=[255,224,164]
  if c.material=='screen':em[sel]=[3,8,8]
 Image.fromarray(orm).save(root/'Textures'/'T_ATV_ORM.png');Image.fromarray(em).save(root/'Textures'/'T_ATV_Emissive.png')
 atlas.save(root/'Textures'/'T_ATV_BaseColor.png')
 np.savez_compressed(root/'Source'/'mesh_data.npz',vertices=va.astype(np.float32),normals=norm.astype(np.float32),faces=faces.astype(np.int32),uv=uv,face_chart=np.array(m.face_chart,np.int32))
 chartdata=[{'id':i+1,'name':c.name,'material':c.material,'rectangle':c.rect,'triangles':len(c.triangles)} for i,c in enumerate(m.charts)]
 (root/'Source'/'UV_Charts.json').write_text(json.dumps(chartdata,indent=2),encoding='utf8')

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description='Rebuild GLB, or explicitly reset guides/maps for a new paint layout.')
 parser.add_argument('--reset-paint-layout',action='store_true',help='DESTRUCTIVE to package textures: repacks UVs and replaces painted PNGs with flat guides. Back up first, then run reproject_paint.py and bake_ao.py.')
 args=parser.parse_args()
 if args.reset_paint_layout:
  root=Path(__file__).resolve().parents[1];m=build_model();uv,density=pack_uv(m)
  guide_images(m,uv,root)
  print('New UV template created. Run reproject_paint.py, bake_ao.py, then rebuild_glb.py.')
 else:
  from rebuild_glb import rebuild
  m,uv,out=rebuild()
  print(str(out),len(m.faces),'triangles')
