"""Small deterministic mesh kernel and self-contained glTF 2.0 binary writer.
Authoring coordinates: metres, RH Z up. Export: RH glTF Y up.
Dependencies for rebuilding only: numpy, scipy, Pillow.
"""
from __future__ import annotations
import json, math, struct
from pathlib import Path
from contextlib import contextmanager
import numpy as np
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[1]
REGIONS=json.loads((ROOT/'textures'/'atlas_regions.json').read_text())
GLTF_BASIS=np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
TAU=2*math.pi

def normalized(a):
 a=np.asarray(a,float);return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-12)
def trans(x=0,y=0,z=0):
 m=np.eye(4);m[:3,3]=[x,y,z];return m
def scale(x=1,y=None,z=None):
 if y is None:y=z=x
 m=np.eye(4);m[0,0]=x;m[1,1]=y;m[2,2]=z;return m
def rx(a):
 c,s=math.cos(a),math.sin(a);m=np.eye(4);m[1:3,1:3]=[[c,-s],[s,c]];return m
def ry(a):
 c,s=math.cos(a),math.sin(a);m=np.eye(4);m[0,0]=c;m[0,2]=s;m[2,0]=-s;m[2,2]=c;return m
def rz(a):
 c,s=math.cos(a),math.sin(a);m=np.eye(4);m[0:2,0:2]=[[c,-s],[s,c]];return m

def basis_z(direction):
 z=normalized(direction);up=np.array([0.,0.,1.])
 if abs(z@up)>.98:up=np.array([0.,1.,0.])
 x=normalized(np.cross(up,z));y=np.cross(z,x)
 m=np.eye(4);m[:3,:3]=np.column_stack([x,y,z]);return m

def uv_atlas(uv,region):
 uv=np.asarray(uv,float);x,y,x1,y1=REGIONS[region];pad=3
 out=np.empty_like(uv)
 out[:,0]=(x+pad+uv[:,0]*(x1-x-2*pad))/1024
 out[:,1]=(y+pad+(1-uv[:,1])*(y1-y-2*pad))/1024
 return out

def face_normals(v,f):return normalized(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]))

class Builder:
 def __init__(self,name):
  self.name=name;self.v=[];self.f=[];self.n=[];self.uv=[];self.count=0;self.matrix=np.eye(4);self.parts=[]
 @contextmanager
 def at(self,m):
  old=self.matrix;self.matrix=old@m
  try:yield self
  finally:self.matrix=old
 def add(self,v,f,uv=None,n=None,region='wood',label=''):
  v=np.asarray(v,float);f=np.asarray(f,np.int32)
  if not len(f):return
  area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)
  f=f[area>1e-11]
  if not len(f):return
  if uv is None:uv=np.zeros((len(v),2))+.5
  if n is None:
   fn=face_normals(v,f);n=np.zeros_like(v)
   for k in range(3):np.add.at(n,f[:,k],fn)
   n=normalized(n)
  v=v@self.matrix[:3,:3].T+self.matrix[:3,3]
  n=normalized(np.asarray(n)@np.linalg.inv(self.matrix[:3,:3]))
  if np.linalg.det(self.matrix[:3,:3])<0:f=f[:,::-1]
  self.v.append(v);self.f.append(f+self.count);self.n.append(n);self.uv.append(uv_atlas(uv,region));self.count+=len(v)
  if label:self.parts.append(label)
 def box(self,center,size,mat='wood',bevel=.025,grain=True):
  c=np.asarray(center,float);h=np.asarray(size,float)/2
  r=min(float(bevel),min(h)*.48)
  if r<1e-5:r=1e-5
  pts=[]
  for sx in [-1,1]:
   for sy in [-1,1]:
    for sz in [-1,1]:
     sg=np.array([sx,sy,sz]);inner=h-r
     for axis in range(3):
      p=inner.copy();p[axis]+=r;pts.append(p*sg)
  pts=np.array(pts);hull=ConvexHull(pts);faces=hull.simplices.copy()
  for i,tri in enumerate(faces):
   fn=np.cross(pts[tri[1]]-pts[tri[0]],pts[tri[2]]-pts[tri[0]])
   if fn@pts[tri].mean(0)<0:faces[i]=tri[::-1]
  norms=normalized(pts-np.clip(pts,-(h-r),h-r))
  # Each face gets a planar UV chart; seams share texture regions intentionally.
  vv=[];nn=[];uv=[];ff=[]
  for tri in faces:
   p=pts[tri];fn=np.cross(p[1]-p[0],p[2]-p[0]);axis=int(np.argmax(abs(fn)))
   tang=[k for k in range(3) if k!=axis];vaxis=max(tang,key=lambda k:h[k]);uaxis=next(k for k in tang if k!=vaxis)
   loc=np.column_stack([(p[:,uaxis]+h[uaxis])/(2*h[uaxis]),(p[:,vaxis]+h[vaxis])/(2*h[vaxis])])
   # Low-priority underside uses a smaller shared portion of the atlas.
   if axis==2 and fn[2]<0:loc=.2+loc*.28
   offset=len(vv);vv.extend(p+c);nn.extend(norms[tri]);uv.extend(loc);ff.append([offset,offset+1,offset+2])
  self.add(vv,ff,uv,nn,mat)
 def beam(self,a,b,width,depth=None,mat='wood',bevel=.025):
  a,b=np.array(a,float),np.array(b,float);d=b-a
  if depth is None:depth=width
  with self.at(trans(*((a+b)/2))@basis_z(d)):
   self.box((0,0,0),(width,depth,np.linalg.norm(d)),mat,bevel)
 def lathe(self,profile,mat='wood',segments=16,caps=True,start=0,end=TAU):
  prof=np.asarray(profile,float);nr=len(prof);seg=int(segments);theta=np.linspace(start,end,seg+1)
  dz=np.gradient(prof[:,0]);dr=np.gradient(prof[:,1]);den=np.maximum(np.sqrt(dz*dz+dr*dr),1e-12)
  vv=[];nn=[];uv=[];ff=[];zmin=prof[:,0].min();zrange=max(np.ptp(prof[:,0]),1e-6)
  for i,(z,r) in enumerate(prof):
   for j,t in enumerate(theta):
    vv.append((r*math.cos(t),r*math.sin(t),z));nn.append((dz[i]/den[i]*math.cos(t),dz[i]/den[i]*math.sin(t),-dr[i]/den[i]));uv.append((j/seg,(z-zmin)/zrange))
  for i in range(nr-1):
   for j in range(seg):
    a=i*(seg+1)+j;b=a+seg+1;ff.extend([(a,a+1,b+1),(a,b+1,b)])
  if caps:
   for i,sgn in [(0,-1),(nr-1,1)]:
    z,r=prof[i];base=len(vv);vv.append((0,0,z));nn.append((0,0,sgn));uv.append((.5,.5))
    for j,t in enumerate(theta):
     vv.append((r*math.cos(t),r*math.sin(t),z));nn.append((0,0,sgn));uv.append((.5+.47*math.cos(t),.5+.47*math.sin(t)))
    for j in range(seg):
     tri=(base,base+j+1,base+j+2);ff.append(tri if sgn>0 else tri[::-1])
  # Close the radial cut faces of an individual stave/sector.
  if end-start<TAU-.001:
   for t,sgn in [(start,-1),(end,1)]:
    side_n=np.array([-math.sin(t),math.cos(t),0])*sgn
    base=len(vv)
    for i,(z,r) in enumerate(prof):
     vv.extend([(0,0,z),(r*math.cos(t),r*math.sin(t),z)]);nn.extend([side_n,side_n]);uv.extend([(.05,(z-zmin)/zrange),(.95,(z-zmin)/zrange)])
    for i in range(nr-1):
     q=[base+2*i,base+2*i+1,base+2*i+3,base+2*i+2]
     if sgn>0:q=q[::-1]
     ff.extend([(q[0],q[1],q[2]),(q[0],q[2],q[3])])
  self.add(vv,ff,uv,nn,mat)
 def cylinder(self,a,b,r,mat='wood',r2=None,segments=12):
  a,b=np.asarray(a,float),np.asarray(b,float);d=b-a;length=np.linalg.norm(d)
  if r2 is None:r2=r
  with self.at(trans(*a)@basis_z(d)):
   edge=min(.025,length*.06,r*.12)
   self.lathe([(0,r*.9),(edge,r),(length-edge,r2),(length,r2*.9)],mat,segments)
 def sphere(self,center,radius,mat='stone',segments=16,rings=10,squash=None):
  with self.at(trans(*center)@(scale(*squash) if squash is not None else np.eye(4))):
   ts=np.linspace(-math.pi/2,math.pi/2,rings+1)
   self.lathe([(radius*math.sin(t),max(0,radius*math.cos(t))) for t in ts],mat,segments,False)
 def tube(self,path,radius,mat='rope',sides=6,closed=False):
  path=np.asarray(path,float)
  if len(path)<2:return
  if closed and np.linalg.norm(path[0]-path[-1])>1e-6:path=np.vstack([path,path[0]])
  tangent=normalized(np.gradient(path,axis=0));dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))];length=max(dist[-1],1e-8)
  vv=[];nn=[];uv=[];ff=[];prev=None
  for i,(p,t) in enumerate(zip(path,tangent)):
   ref=np.array([0.,0.,1.]) if abs(t[2])<.9 else np.array([0.,1.,0.])
   x=normalized(np.cross(t,ref)) if prev is None else normalized(prev-t*np.dot(prev,t))
   if np.linalg.norm(x)<.5:x=normalized(np.cross(t,ref))
   y=np.cross(t,x);prev=x
   for j in range(sides+1):
    th=TAU*j/sides;n=x*math.cos(th)+y*math.sin(th)
    rr=radius[i] if hasattr(radius,'__len__') else radius
    vv.append(p+n*rr);nn.append(n);uv.append((j/sides,dist[i]/length))
  for i in range(len(path)-1):
   for j in range(sides):
    a=i*(sides+1)+j;b=a+sides+1;ff.extend([(a,b,b+1),(a,b+1,a+1)])
  # Tube frame orientation above uses tangent-cross-reference; verify outer winding.
  arr=np.asarray(vv);fac=np.asarray(ff);nor=np.asarray(nn)
  if len(fac) and np.mean(np.sum(face_normals(arr,fac)*nor[fac].mean(1),axis=1))<0:fac=fac[:,::-1]
  ff=fac.tolist()
  if not closed:
   for idx,sgn in [(0,-1),(len(path)-1,1)]:
    base=len(vv);vv.append(path[idx]);nn.append(tangent[idx]*sgn);uv.append((.5,.5))
    for j in range(sides+1):
     vid=idx*(sides+1)+j;vv.append(vv[vid]);nn.append(tangent[idx]*sgn);uv.append((.5,.5))
    for j in range(sides):
     tri=[base,base+j+1,base+j+2]
     q=np.asarray(vv)[tri]
     if np.dot(np.cross(q[1]-q[0],q[2]-q[0]),tangent[idx]*sgn)<0:tri.reverse()
     ff.append(tri)
  self.add(vv,ff,uv,nn,mat)
 def torus(self,center,major,minor,mat='metal',axis='z',segments=24,sides=7):
  m=trans(*center)
  if axis=='x':m=m@ry(math.pi/2)
  elif axis=='y':m=m@rx(math.pi/2)
  with self.at(m):
   ts=np.linspace(0,TAU,segments+1);self.tube([(major*math.cos(t),major*math.sin(t),0) for t in ts],minor,mat,sides,True)
 def surface(self,func,nu,nv,mat='canvas',flip=False):
  vv=np.array([func(u/nu,v/nv) for v in range(nv+1) for u in range(nu+1)],float);ff=[]
  uv=np.array([(u/nu,v/nv) for v in range(nv+1) for u in range(nu+1)])
  for v in range(nv):
   for u in range(nu):
    a=v*(nu+1)+u;b=a+nu+1;ff.extend([(a,a+1,b+1),(a,b+1,b)])
  f=np.array(ff)
  if flip:f=f[:,::-1]
  self.add(vv,f,uv,None,mat)
 def extrude(self,polygon,depth,mat='metal'):
  p=np.asarray(polygon,float)
  area=np.sum(p[:,0]*np.roll(p[:,1],-1)-np.roll(p[:,0],-1)*p[:,1])
  if area<0:p=p[::-1]
  # Ear clipping, sufficient for the simple outlines authored in this pack.
  ids=list(range(len(p)));tri=[]
  def cross(a,b,c):return np.cross(b-a,c-a).item()
  while len(ids)>3:
   found=False
   for j,k in enumerate(ids):
    a,b,c=ids[j-1],k,ids[(j+1)%len(ids)]
    if cross(p[a],p[b],p[c])<=1e-9:continue
    other=[q for q in ids if q not in [a,b,c]]
    inside=any(cross(p[a],p[b],p[q])>=-1e-10 and cross(p[b],p[c],p[q])>=-1e-10 and cross(p[c],p[a],p[q])>=-1e-10 for q in other)
    if inside:continue
    tri.append((a,b,c));ids.remove(b);found=True;break
   if not found:raise ValueError('Non-simple polygon in '+self.name)
  tri.append(tuple(ids));count=len(p)
  for z,sgn in [(-depth/2,-1),(depth/2,1)]:
   v=np.column_stack([p,np.full(count,z)]);f=np.array(tri)
   if sgn<0:f=f[:,::-1]
   uv=(p-p.min(0))/np.maximum(np.ptp(p,axis=0),1e-6)
   self.add(v,f,uv,np.tile((0,0,sgn),(count,1)),mat)
  for i in range(count):
   a=p[i];b=p[(i+1)%count];v=np.array([[*a,-depth/2],[*b,-depth/2],[*b,depth/2],[*a,depth/2]])
   n=normalized([b[1]-a[1],a[0]-b[0],0]);self.add(v,[[0,1,2],[0,2,3]],[[0,0],[1,0],[1,1],[0,1]],np.tile(n,(4,1)),mat)
 def arrays(self,optimize=True):
  if not self.v:raise ValueError('Empty asset '+self.name)
  v=np.concatenate(self.v);f=np.concatenate(self.f);n=normalized(np.concatenate(self.n));uv=np.concatenate(self.uv)
  # Degenerate tip triangles were filtered on insertion. Remove their now-unused vertices too.
  used=np.unique(f);remap=np.full(len(v),-1,dtype=np.int64);remap[used]=np.arange(len(used))
  v,n,uv=v[used],n[used],uv[used];f=remap[f]
  if optimize:
   packed=np.round(np.column_stack([v,n,uv]),7)
   _,ix,inv=np.unique(packed,axis=0,return_index=True,return_inverse=True)
   v,n,uv=v[ix],n[ix],uv[ix];f=inv[f]
  return v.astype('float32'),f.astype('uint32'),n.astype('float32'),uv.astype('float32')

def write_glb(path,builder,extras=None):
 path=Path(path);v,f,n,uv=builder.arrays();source_bounds=[v.min(0).round(5).tolist(),v.max(0).round(5).tolist()];v=v@GLTF_BASIS.T;n=n@GLTF_BASIS.T
 chunks=[];views=[];accessors=[];offset=0
 def blob(data,target=None):
  nonlocal offset
  pad=(-offset)%4
  if pad:chunks.append(bytes(pad));offset+=pad
  i=len(views);view={'buffer':0,'byteOffset':offset,'byteLength':len(data)}
  if target:view['target']=target
  views.append(view);chunks.append(data);offset+=len(data);return i
 def accessor(a,ctype,kind,target):
  ar=np.ascontiguousarray(a);bi=blob(ar.tobytes(),target)
  d={'bufferView':bi,'componentType':ctype,'count':len(ar),'type':kind}
  if kind=='VEC3' and target==34962:
   d['min']=ar.min(0).tolist();d['max']=ar.max(0).tolist()
  accessors.append(d);return len(accessors)-1
 pos=accessor(v.astype('<f4'),5126,'VEC3',34962);norm=accessor(n.astype('<f4'),5126,'VEC3',34962);tex=accessor(uv.astype('<f4'),5126,'VEC2',34962);ind=accessor(f.ravel().astype('<u4'),5125,'SCALAR',34963)
 imgs=[]
 for file in ['T_Pirate_BaseColor.png','T_Pirate_RoughMetal.png']:
  bi=blob((ROOT/'textures'/file).read_bytes());imgs.append({'bufferView':bi,'mimeType':'image/png','name':file[:-4]})
 document={'asset':{'version':'2.0','generator':'Pirate Outpost explicit mesh builder 1.0'},'scene':0,
  'scenes':[{'nodes':[0]}],'nodes':[{'name':builder.name,'mesh':0}],
  'meshes':[{'name':builder.name,'primitives':[{'attributes':{'POSITION':pos,'NORMAL':norm,'TEXCOORD_0':tex},'indices':ind,'material':0,'mode':4}]}],
  'materials':[{'name':'M_PirateAtlas','doubleSided':True,'alphaMode':'OPAQUE','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'baseColorTexture':{'index':0},'metallicRoughnessTexture':{'index':1},'metallicFactor':1.,'roughnessFactor':1.}}],
  'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071}],
  'textures':[{'sampler':0,'source':0},{'sampler':0,'source':1}],'images':imgs,'bufferViews':views,'accessors':accessors,'buffers':[{'byteLength':offset}],
  'extras':{'units':'metres','source_basis':'RH_Z_UP_FRONT_MINUS_Y','atlas_uv0_overlaps':True,**(extras or {})}}
 jb=json.dumps(document,separators=(',',':')).encode();jb+=b' '*((-len(jb))%4)
 bb=b''.join(chunks);bb+=bytes((-len(bb))%4)
 total=12+8+len(jb)+8+len(bb)
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(struct.pack('<4sII',b'glTF',2,total)+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(bb),0x004e4942)+bb)
 return {'vertices':len(v),'triangles':len(f),'bounds_m_source':source_bounds,'file_bytes':total}

def read_glb(path):
 data=Path(path).read_bytes();magic,ver,total=struct.unpack_from('<4sII',data)
 if magic!=b'glTF' or ver!=2 or total!=len(data):raise ValueError('Invalid GLB header')
 jl,jt=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+jl]);bl,bt=struct.unpack_from('<II',data,20+jl);binary=data[28+jl:28+jl+bl]
 return doc,binary

def read_accessor(doc,binary,index):
 a=doc['accessors'][index];view=doc['bufferViews'][a['bufferView']]
 dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
 offset=view.get('byteOffset',0)+a.get('byteOffset',0)
 out=np.frombuffer(binary,dtype=dtype,count=a['count']*n,offset=offset)
 return out.reshape(a['count'],n) if n>1 else out
