"""Build real connected trunk geometry and portable leaf cards. No render mockups.
Coordinates: RH / Y-up / metres. Dependencies: numpy, scipy, scikit-image, Pillow, trimesh.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt, sobel
from scipy.interpolate import PchipInterpolator
from skimage.measure import marching_cubes
from PIL import Image, ImageDraw
import trimesh, json, math, struct, io, base64
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'assets';A.mkdir(exist_ok=True);(ROOT/'models').mkdir(exist_ok=True)
SOURCE=ROOT/'assets/bark_source.png'
# Curving, tapering skeleton. Daughter branches meet the main stem in 3D.
raw=[
 [[0,-.06,0,.31],[.025,.38,.025,.245],[-.10,.9,.015,.195],[-.12,1.27,-.005,.173],[.055,1.82,-.04,.145],[.14,2.28,-.10,.11],[-.05,2.8,-.17,.075],[-.12,3.35,-.20,.045],[-.02,3.96,-.19,.014]],
 [[-.10,1.12,.01,.146],[-.43,1.52,.03,.125],[-.88,1.88,.06,.092],[-1.19,2.25,.015,.069],[-1.41,2.64,-.04,.038],[-1.51,3.02,-.07,.013]],
 [[-.80,1.83,.055,.079],[-1.19,2.08,.16,.065],[-1.53,2.26,.20,.04],[-1.84,2.62,.16,.011]],
 [[-.85,1.9,.04,.075],[-.92,2.39,-.11,.054],[-1.15,2.86,-.13,.034],[-1.08,3.47,-.18,.012]],
 [[.015,1.66,-.035,.13],[.44,2.01,.02,.105],[.91,2.34,.07,.077],[1.21,2.73,.04,.044],[1.28,3.2,0,.014]],
 [[.82,2.27,.05,.063],[1.30,2.40,.11,.052],[1.64,2.69,.06,.028],[1.8,3.15,-.02,.011]],
 [[.13,2.20,-.1,.095],[.54,2.74,-.13,.067],[.77,3.18,-.13,.037],[.64,3.69,-.17,.012]],
 [[-.03,2.73,-.17,.07],[-.52,3.05,-.04,.049],[-.83,3.49,.035,.023],[-.87,3.79,0,.009]],
 [[-.09,.90,.005,.15],[-.14,1.48,-.33,.105],[.24,2.07,-.49,.075],[.34,2.65,-.58,.041],[.13,3.2,-.51,.011]],
]
# Root flare: real depth, not a screen-space ellipse or stroke.
for k in range(6):
 t=k*math.tau/6+.20
 raw.append([[.01,.24,0,.18],[.32*math.cos(t),.12,.32*math.sin(t),.135],[.62*math.cos(t),.035,.60*math.sin(t),.065],[.81*math.cos(t),.005,.77*math.sin(t),.01]])
branches=[]
for bi,r in enumerate(raw):
 r=np.asarray(r,dtype=float); d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(r[:,:3],axis=0),axis=1))]
 t=np.linspace(0,d[-1],max(8,int(d[-1]/.10)+1))
 pts=PchipInterpolator(d,r,axis=0)(t)
 tangent=np.gradient(pts[:,:3],axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 # Parallel-transported transverse frame prevents UV twists.
 e=[];last=np.array([0.,0.,1.])
 for tang in tangent:
  f=last-tang*np.dot(last,tang)
  if np.linalg.norm(f)<.001:f=np.cross(tang,[1.,0.,0.])
  last=f/np.linalg.norm(f);e.append(last.copy())
 branches.append(dict(p=pts,t=t,tan=tangent,e=np.array(e),r=pts[:,3]))
# Signed-distance union with mild smoothing to blend the forks.
h=.026;lo=np.array([-2.13,-.42,-1.05]);hi=np.array([2.14,4.22,1.04]);axes=[np.arange(lo[i],hi[i]+h,h) for i in range(3)]
field=np.full(tuple(len(x) for x in axes),3,dtype=np.float32)
for b in branches:
 p=b['p']
 for a,z in zip(p[:-1],p[1:]):
  mn=np.minimum(a[:3],z[:3])-max(a[3],z[3])-.10;mx=np.maximum(a[:3],z[:3])+max(a[3],z[3])+.10
  il=np.maximum(0,np.floor((mn-lo)/h).astype(int));iu=np.minimum(field.shape,np.ceil((mx-lo)/h).astype(int)+1)
  sl=tuple(slice(il[k],iu[k]) for k in range(3))
  x,y,zz=np.meshgrid(*[axes[k][il[k]:iu[k]] for k in range(3)],indexing='ij')
  q=np.stack([x,y,zz],-1);v=z[:3]-a[:3]
  t=np.clip(np.sum((q-a[:3])*v,-1)/np.dot(v,v),0,1)
  dist=np.linalg.norm(q-a[:3]-t[...,None]*v,axis=-1)-(a[3]+t*(z[3]-a[3]))
  np.minimum(field[sl],dist,out=field[sl])
field=gaussian_filter(field,.72)
verts,faces,_,_=marching_cubes(field,0,spacing=(h,h,h),allow_degenerate=False);verts+=lo
mesh=trimesh.Trimesh(verts,faces,process=True);mesh.fix_normals()
components=mesh.split(only_watertight=False);mesh=max(components,key=lambda x:len(x.faces))
verts=np.asarray(mesh.vertices);faces=np.asarray(mesh.faces);normals=np.asarray(mesh.vertex_normals)
print('trunk geometry',len(verts),'vertices',len(faces),'triangles','watertight',mesh.is_watertight,flush=True)
# Project samples to a branch's arc and angle, with radius-aware metric UV scale.
def project(q,b):
 p=b['p'];a=p[:-1,:3];v=np.diff(p[:,:3],axis=0)
 t=np.clip(np.sum((q[:,None,:]-a[None])*v[None],-1)/np.sum(v*v,-1),0,1)
 near=a[None]+t[...,None]*v[None];vec=q[:,None,:]-near
 rad=p[:-1,3][None]+t*np.diff(p[:,3])[None]
 signed=np.linalg.norm(vec,axis=-1)-rad
 k=np.argmin(signed,axis=1);ii=np.arange(len(q));tt=t[ii,k];delta=vec[ii,k]
 e=b['e'][k]*(1-tt[:,None])+b['e'][k+1]*tt[:,None];e/=np.linalg.norm(e,axis=1)[:,None]
 tang=v[k]/np.linalg.norm(v[k],axis=1)[:,None];e2=np.cross(tang,e)
 angle=np.arctan2(np.sum(delta*e2,1),np.sum(delta*e,1))
 arc=b['t'][k]+tt*np.diff(b['t'])[k];radius=rad[ii,k]
 return signed[ii,k],angle,arc,radius
cent=verts[faces].mean(axis=1)
D=np.array([project(cent,b)[0] for b in branches]);labels=np.argmin(D,axis=0)
# Non-overlapping rectangular chart allocation. Longitudinal direction uses arc length.
charts=[];faceUV=np.zeros((len(faces),3,2),float)
for bi,b in enumerate(branches):
 ids=np.where(labels==bi)[0]
 if not len(ids):continue
 q=verts[faces[ids]].reshape(-1,3);_,ang,arc,rr=project(q,b)
 ang=ang.reshape(-1,3);arc=arc.reshape(-1,3);rr=rr.reshape(-1,3)
 wrap=np.ptp(ang,axis=1)>math.pi
 ang[wrap]=np.where(ang[wrap]<0,ang[wrap]+math.tau,ang[wrap])
 uv=np.stack([ang*rr,arc],-1)
 mn=uv.min(axis=(0,1));mx=uv.max(axis=(0,1));uv-=mn
 faceUV[ids]=uv;charts.append(dict(id=bi,faces=ids,extent=mx-mn,min=mn))
# Area check detects the rare cap/fork fold. Such faces receive separate metric charts.
# This makes UV islands strictly unique, instead of hiding intersections with a tiled texture.
iso=[]
for ch in charts:
 ids=ch['faces'];uv=faceUV[ids]
 a=uv[:,1]-uv[:,0];b=uv[:,2]-uv[:,0];area=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])*.5
 bad=(area<np.asarray(mesh.area_faces)[ids]*.18)|(area>np.asarray(mesh.area_faces)[ids]*3.8)
 for fi in ids[bad]:iso.append(int(fi))
 ch['faces']=ids[~bad]
# Raster chart overlap test at 330 texels/metre. Move only secondary overlapping faces.
for ch in charts:
 den=330.;size=np.ceil(ch['extent']*den).astype(int)+4
 occ=np.full((max(1,size[1]),max(1,size[0])),-1,np.int32)
 good=[]
 for fi in ch['faces']:
  uv=faceUV[fi]*den+1
  mn=np.maximum(0,np.floor(uv.min(0)).astype(int));mx=np.minimum(size-1,np.ceil(uv.max(0)).astype(int))
  xx,yy=np.meshgrid(np.arange(mn[0],mx[0]+1)+.5,np.arange(mn[1],mx[1]+1)+.5)
  a,b,c=uv;det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
  if abs(det)<1e-8:iso.append(int(fi));continue
  w1=((xx-a[0])*(c[1]-a[1])-(yy-a[1])*(c[0]-a[0]))/det
  w2=((b[0]-a[0])*(yy-a[1])-(b[1]-a[1])*(xx-a[0]))/det
  mask=(w1>.025)&(w2>.025)&(w1+w2<.975)
  view=occ[mn[1]:mx[1]+1,mn[0]:mx[0]+1]
  if np.count_nonzero(mask&(view>=0))>1:iso.append(int(fi));continue
  view[mask]=fi;good.append(fi)
 ch['faces']=np.asarray(good,dtype=int)
# Join neighbouring repair faces into small near-planar patches, instead of wasting
# the texture on thousands of one-triangle islands. Normal-cone growth keeps low distortion.
adj={fi:[] for fi in set(iso)}
for fa,fb in mesh.face_adjacency:
 if int(fa) in adj and int(fb) in adj:
  adj[int(fa)].append(int(fb));adj[int(fb)].append(int(fa))
remaining=set(iso);patch_id=100000
while remaining:
 start=min(remaining);ref=np.asarray(mesh.face_normals)[start];stack=[start];group=[];remaining.remove(start)
 while stack:
  fi=stack.pop();group.append(fi)
  for nb in adj[fi]:
   if nb in remaining and np.dot(np.asarray(mesh.face_normals)[nb],ref)>.90 and len(group)+len(stack)<200:
    remaining.remove(nb);stack.append(nb)
 ids=np.asarray(group);ns=np.asarray(mesh.face_normals)[ids].mean(0);ns/=np.linalg.norm(ns)
 axis=np.array([0.,1.,0.]) if abs(ns[1])<.9 else np.array([1.,0.,0.])
 axis-=ns*np.dot(axis,ns);axis/=np.linalg.norm(axis);side=np.cross(ns,axis)
 q=verts[faces[ids]];uv=np.stack([np.einsum('ijk,k->ij',q,side),np.einsum('ijk,k->ij',q,axis)],-1)
 mn=uv.min(axis=(0,1));uv-=mn;faceUV[ids]=uv
 charts.append(dict(id=patch_id,faces=ids,extent=uv.max(axis=(0,1)),min=mn));patch_id+=1
charts=[c for c in charts if len(c['faces'])]
# Shelf pack without rotating long trunk charts; equal metric density except inherent unwrap distortion.
T=2048;pad=5
def pack(den):
 dims=[np.maximum(1,np.ceil(c['extent']*den).astype(int))+2*pad for c in charts]
 order=sorted(range(len(charts)),key=lambda i:-dims[i][1]);x=y=rowh=0;pos={}
 for i in order:
  w,hh=dims[i]
  if w>T:return None
  if x+w>T:y+=rowh;x=0;rowh=0
  if y+hh>T:return None
  pos[i]=(x+pad,y+pad);x+=w;rowh=max(rowh,hh)
 return pos
DEN=385.
while (packing:=pack(DEN)) is None:DEN*=.91
uvOut=np.zeros_like(faceUV)
for i,ch in enumerate(charts):uvOut[ch['faces']]=(faceUV[ch['faces']]*DEN+packing[i])/T
# Bake existing image-generated bark into unique UVs, following the local branch direction.
source=np.asarray(Image.open(SOURCE).convert('RGB'),float)/255
sH,sW=source.shape[:2]
albedo=np.full((T,T,3),[.32,.25,.18],np.float32);height=np.zeros((T,T),np.float32);used=np.zeros((T,T),bool)
# Source coordinates measured in metres, independent of chart packing.
srcUV=np.zeros_like(faceUV)
for bi,b in enumerate(branches):
 ids=np.where(labels==bi)[0];q=verts[faces[ids]].reshape(-1,3);_,ang,arc,rr=project(q,b)
 ang=ang.reshape(-1,3);rr=rr.reshape(-1,3);arc=arc.reshape(-1,3)
 wrap=np.ptp(ang,axis=1)>math.pi;ang[wrap]=np.where(ang[wrap]<0,ang[wrap]+math.tau,ang[wrap])
 srcUV[ids,:,0]=ang*rr*.92+bi*.197;srcUV[ids,:,1]=-arc*.58+bi*.137
for fi,uvw in enumerate(uvOut):
 uv=uvw*T;mn=np.maximum(0,np.floor(uv.min(0)).astype(int));mx=np.minimum(T-1,np.ceil(uv.max(0)).astype(int))
 if (mx<mn).any():continue
 xx,yy=np.meshgrid(np.arange(mn[0],mx[0]+1)+.5,np.arange(mn[1],mx[1]+1)+.5)
 a,b,c=uv;det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 if abs(det)<1e-9:continue
 w1=((xx-a[0])*(c[1]-a[1])-(yy-a[1])*(c[0]-a[0]))/det
 w2=((b[0]-a[0])*(yy-a[1])-(b[1]-a[1])*(xx-a[0]))/det
 mask=(w1>=-.001)&(w2>=-.001)&(w1+w2<=1.001)
 tuv=(1-w1-w2)[...,None]*srcUV[fi,0]+w1[...,None]*srcUV[fi,1]+w2[...,None]*srcUV[fi,2]
 # Mirrored sampling avoids any dark seams in the source image.
 suv=1-np.abs((tuv%2)-1);ix=np.minimum(sW-1,(suv[...,0]*sW).astype(int));iy=np.minimum(sH-1,(suv[...,1]*sH).astype(int))
 color=source[iy,ix]
 view=albedo[mn[1]:mx[1]+1,mn[0]:mx[0]+1];view[mask]=color[mask]
 used[mn[1]:mx[1]+1,mn[0]:mx[0]+1]|=mask
# Padding the atlas in pixel space prevents black edge bleed.
_,nearest=distance_transform_edt(~used,return_indices=True)
albedo[~used]=albedo[nearest[0][~used],nearest[1][~used]]
height=np.dot(albedo,[.2126,.7152,.0722]);height=gaussian_filter(height,.6)
gx=sobel(height,axis=1)*.95;gy=sobel(height,axis=0)*.95
normal=np.stack([-gx,gy,np.ones_like(gx)],-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
rough=np.clip(.88-(height-.35)*.14,.68,.96)
Image.fromarray(np.uint8(np.clip(albedo,0,1)*255)).save(A/'trunk_basecolor.png')
Image.fromarray(np.uint8((normal*.5+.5)*255)).save(A/'trunk_normal_gl.png')
dx=np.uint8((normal*.5+.5)*255);dx[:,:,1]=255-dx[:,:,1];Image.fromarray(dx).save(A/'trunk_normal_dx.png')
Image.fromarray(np.uint8(rough*255)).save(A/'trunk_roughness.png')
uvimg=Image.new('RGB',(T,T),(24,29,28));dr=ImageDraw.Draw(uvimg)
for u in uvOut:dr.polygon([tuple(x) for x in u*T],outline=(125,162,135))
uvimg.save(A/'trunk_uv_layout.png')
# Discontinuities receive separate vertices. Optimise by exact key after creating unique charts.
uvverts=verts[faces].reshape(-1,3);uvnorm=normals[faces].reshape(-1,3);uvs=uvOut.reshape(-1,2)
keys=np.round(np.column_stack([uvverts,uvnorm,uvs]),7)
_,keep,inverse=np.unique(keys,axis=0,return_index=True,return_inverse=True)
trunk=dict(position=uvverts[keep],normal=uvnorm[keep],uv=uvs[keep],indices=inverse.astype(np.uint32))
print('UV',len(charts),'charts,',len(iso),'repair faces grouped into charts,',round(DEN),'texels/m','occupied',round(used.mean(),3),flush=True)
# Leaf atlas: each card carries a compact cluster of irregular, blunt leaves.
# Vector-authored alpha, no invented photo/image-generation claim.
S=1024;tile=256;sup=2
atlas=Image.new('RGBA',(S*sup,S*sup),(255,255,255,0));d=ImageDraw.Draw(atlas)
def leaf_poly(cx,cy,w,hh,ang,rng):
 # Curved pointed tip, broad shoulders, subtly lobed margins; no veins.
 outline=[(0,-.56),(.29,-.40),(.49,-.11),(.44,.17),(.26,.35),(.06,.46),(0,.59),(-.08,.43),(-.31,.30),(-.46,.04),(-.34,-.27)]
 pts=[]
 # Chaikin smoothing preserves the hand-painted leaf silhouette without hard polygons.
 for x,y in outline:pts.append(np.array([x*w,y*hh]))
 for _ in range(2):pts=[p*.75+q*.25 for p,q in zip(pts,pts[1:]+pts[:1]) for p,q in [(p,q),(q,p)]]
 ca,sa=math.cos(ang),math.sin(ang)
 return [(cx+(p[0]*ca-p[1]*sa),cy+(p[0]*sa+p[1]*ca)) for p in pts]
for k in range(16):
 rng=np.random.default_rng(1024+k);tx=k%4*tile*sup;ty=k//4*tile*sup
 for j in range(25):
  an=j*2.39996+rng.uniform(-.4,.4);rr=math.sqrt((j+.4)/25)*.38
  x=.5+math.cos(an)*rr;y=.5+math.sin(an)*rr*.94
  w=rng.uniform(.14,.21)*tile*sup;hh=rng.uniform(.18,.245)*tile*sup
  points=leaf_poly(tx+x*tile*sup,ty+y*tile*sup,w,hh,rng.uniform(-1.4,1.4),rng)
  val=int(rng.uniform(.91,1)*255);d.polygon(points,fill=(val,val,val,255))
atlas=atlas.resize((S,S),Image.Resampling.LANCZOS);atlas.save(A/'leaves_rgba.png')
# Existing v04 retained crown: IDs 909 and 1001 removed, upper centre lowered.
bunches0=[[-1.28,.62,.00,.76,101],[0,.88,-.20,.80,202],[1.22,.68,-.03,.76,303],[-.70,1.42,-.08,.79,404],[.68,1.44,.02,.79,505],[0,1.87,-.10,.73,606],[-1.46,1.38,-.15,.59,707],[1.45,1.34,-.10,.59,808],[0,1.44,.24,.72,1102],[-.05,.26,.05,.60,1203]]
# Balanced subdivision of six cube faces -> near-uniform rounded proxy, no pole concentration.
def sphere_cube(q):
 x,y,z=q
 return np.array([x*math.sqrt(max(0,1-y*y/2-z*z/2+y*y*z*z/3)),y*math.sqrt(max(0,1-z*z/2-x*x/2+z*z*x*x/3)),z*math.sqrt(max(0,1-x*x/2-y*y/2+x*x*y*y/3))])
L=np.array([-.54,.78,.32]);L/=np.linalg.norm(L)
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def ramp(N,seed,ao):
 n=smooth(.08,.96,np.dot(N,L)*.5+.5)
 dark=np.array([.075,.285,.255]);mid=np.array([.235,.515,.325]);bright=np.array([.73,.865,.39])
 c=dark*(1-smooth(.08,.6,n))+mid*smooth(.08,.6,n)
 c=c*(1-smooth(.55,.94,n))+bright*smooth(.55,.94,n)
 return np.clip((c+(seed-.5)*.045)*ao,0,1)
f={k:[] for k in ['position','normal','uv','color','proxyNormal','pivot','phase','bunchIndex','indices']};cards=[];bunches=[]
for bi,(x,y,z,s,bid) in enumerate(bunches0):
 center=np.array([x,y+2,z]);radii=np.array([s*1.03,s*(.68 if bid==606 else .81),s*.94]);rng=np.random.default_rng(bid)
 bunches.append(dict(id=bid,center=center.tolist(),radii=radii.tolist()))
 points=[]
 for ax in range(3):
  others=[a for a in range(3) if a!=ax]
  for sign in [-1,1]:
   for i in range(6):
    for j in range(6):
     q=np.zeros(3);q[ax]=sign;q[others[0]]=-1+2*(i+.5+rng.uniform(-.22,.22))/6;q[others[1]]=-1+2*(j+.5+rng.uniform(-.22,.22))/6
     points.append((sphere_cube(q),rng.uniform(.86,1),False))
 for k in range(72):
  N=rng.normal(size=3);N/=np.linalg.norm(N);points.append((N,rng.uniform(.16,.71),True))
 for n,rad,core in points:
  pivot=center+n*radii*rad;N=n/radii;N/=np.linalg.norm(N)
  # Fixed camera-facing cards: their geometry normal is deliberately NOT the proxy normal.
  a=rng.uniform(-.60,.60);ca,sa=math.cos(a),math.sin(a)
  R=np.array([ca,sa,0]);U=np.array([-sa,ca,0])
  size=s*rng.uniform(.48,.59)*( .91 if core else 1)
  seed=float(rng.random());tileid=int(rng.integers(0,16));ao=.76 if core else .97
  color=ramp(N,seed,ao);phase=seed*math.tau
  ci=len(cards);base=len(f['position'])//3
  for qx,qy in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]:
   p=pivot+(R*qx+U*qy)*size;f['position'].extend(p);f['normal'].extend([0,0,1]);f['proxyNormal'].extend(N)
   f['pivot'].extend(pivot);f['color'].extend(color);f['uv'].extend([(tileid%4+qx+.5)/4,(tileid//4+.5-qy)/4]);f['phase'].append(phase);f['bunchIndex'].append(bi)
  f['indices'].extend([base,base+1,base+2,base,base+2,base+3]);cards.append(dict(pivot=pivot.tolist(),proxyNormal=N.tolist(),right=R.tolist(),up=U.tolist(),size=float(size),phase=phase,bunchIndex=bi,atlasTile=tileid,core=core))
def serial(m):
 return {k:(np.asarray(v).astype(int).reshape(-1).tolist() if k in ['indices','bunchIndex'] else np.round(np.asarray(v).reshape(-1),6).tolist()) for k,v in m.items()}
meta=dict(version='05',trunkIsReal3D=True,wholeTreeGradient=False,removedBunchIds=[909,1001],groundOffset=2,cardLinearScaleVersusV03=.70,cardsPerBunch=288,cards=len(cards),lightDirection=L.tolist(),barkSource='image-generated texture supplied in conversation',normalSource='derived from bark luminance; not a scanned geometric normal',trunkTriangles=len(trunk['indices'])//3,leafTriangles=len(f['indices'])//3,uvCharts=len(charts),uvTexelsPerMetre=round(DEN),uvCoverage=float(used.mean()),trunkWatertight=bool(mesh.is_watertight),units='metres',axes='right handed Y up')
scene=dict(meta=meta,trunk=serial(trunk),foliage=serial(f),bunches=bunches)
(A/'scene.json').write_text(json.dumps(scene,separators=(',',':')))
(A/'cards.json').write_text(json.dumps(cards,separators=(',',':')))
(A/'branch_skeleton.json').write_text(json.dumps(raw))
# glTF 2.0 binary writer. Same geometry, colours and alpha as the web assets.
blob=bytearray();g=dict(asset=dict(version='2.0',generator='Tree static-web correction v05'),scene=0,scenes=[dict(nodes=[0,1])],nodes=[dict(name='Trunk_UniqueUV',mesh=0),dict(name='Foliage_Cards',mesh=1)],meshes=[],materials=[],accessors=[],bufferViews=[],buffers=[],images=[],textures=[],samplers=[dict(magFilter=9729,minFilter=9987,wrapS=33071,wrapT=33071)],extensionsUsed=['KHR_materials_unlit'])
def view(data,target=None):
 while len(blob)%4:blob.append(0)
 o=len(blob);blob.extend(data);i=len(g['bufferViews']);v=dict(buffer=0,byteOffset=o,byteLength=len(data))
 if target:v['target']=target
 g['bufferViews'].append(v);return i
def acc(data,width,kind='float',minmax=False):
 ar=np.asarray(data,dtype='<u4' if kind=='uint' else '<f4').reshape(-1,width);bv=view(ar.tobytes(),34963 if kind=='uint' else 34962)
 a=dict(bufferView=bv,componentType=5125 if kind=='uint' else 5126,count=len(ar),type={1:'SCALAR',2:'VEC2',3:'VEC3',4:'VEC4'}[width])
 if minmax:a.update(min=ar.min(0).tolist(),max=ar.max(0).tolist())
 i=len(g['accessors']);g['accessors'].append(a);return i
def tex(path):
 bv=view(path.read_bytes());i=len(g['images']);g['images'].append(dict(bufferView=bv,mimeType='image/png'));g['textures'].append(dict(source=i,sampler=0));return i
btx=tex(A/'trunk_basecolor.png');ntx=tex(A/'trunk_normal_gl.png');ltx=tex(A/'leaves_rgba.png')
g['materials']=[dict(name='Bark_UniqueUV',pbrMetallicRoughness=dict(baseColorTexture=dict(index=btx),metallicFactor=0,roughnessFactor=.86),normalTexture=dict(index=ntx,scale=.5)),dict(name='Leaves_ProxyColor_Masked',pbrMetallicRoughness=dict(baseColorTexture=dict(index=ltx),metallicFactor=0,roughnessFactor=1),alphaMode='MASK',alphaCutoff=.48,doubleSided=True,extensions=dict(KHR_materials_unlit={}))]
for i,m in enumerate([scene['trunk'],scene['foliage']]):
 attrs=dict(POSITION=acc(m['position'],3,minmax=True),NORMAL=acc(m['normal'],3),TEXCOORD_0=acc(m['uv'],2))
 if i:
  # glTF vertex colours are linear; web carries display-space artistic colours explicitly.
  c=np.asarray(m['color']);linear=np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4);attrs['COLOR_0']=acc(linear,3)
  attrs['_PIVOT']=acc(m['pivot'],3);attrs['_PROXY_NORMAL']=acc(m['proxyNormal'],3);attrs['_WIND_PHASE']=acc(m['phase'],1)
  piv=np.asarray(m['pivot']).reshape(-1,3);attrs['TEXCOORD_1']=acc(piv[:,:2],2);attrs['TEXCOORD_2']=acc(np.column_stack([piv[:,2],m['phase']]),2)
  attrs['TEXCOORD_3']=acc(np.column_stack([m['bunchIndex'],np.ones(len(m['phase']))]),2)
 g['meshes'].append(dict(name=['Trunk','Foliage'][i],primitives=[dict(attributes=attrs,indices=acc(m['indices'],1,'uint'),material=i)]))
while len(blob)%4:blob.append(0)
g['buffers']=[dict(byteLength=len(blob))];j=json.dumps(g,separators=(',',':')).encode();j+=b' '*((-len(j))%4)
out=struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(blob))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(blob),b'BIN\x00')+blob
(ROOT/'models/tree_v05.glb').write_bytes(out)
(A/'meta.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(meta,indent=2),flush=True)
