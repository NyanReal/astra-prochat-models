"""Deterministic, editable ATV geometry. Requires NumPy (bundled with Blender).
Model space: +X nose, +Y left, +Z up; metres. No repeated/mirrored UVs.
Each Chart is packed once. Adjacent triangles share edges, never texture area.
"""
from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass, field

PALETTE = {
 'teal': ((111,151,153), .73, .00),
 'cream': ((223,211,179), .67, .00),
 'rubber': ((62,65,66), .94, .00),
 'tread': ((70,73,74), .94, .00),
 'frame': ((55,60,61), .76, .15),
 'seat': ((67,67,65), .87, .00),
 'bumper': ((100,104,102), .77, .08),
 'orange': ((220,133,56), .53, .00),
 'rim': ((211,203,176), .48, .25),
 'steel': ((125,127,120), .47, .45),
 'lamp': ((255,235,181), .29, .00),
 'screen': ((42,54,55), .40, .00),
 'grille': ((39,44,44), .84, .00),
}

def unit(v):
 v=np.asarray(v,dtype=float); return v / max(float(np.linalg.norm(v)),1e-12)

def basis(axis):
 w=unit(axis); ref=np.array((0.,0.,1.)) if abs(w[2])<.9 else np.array((0.,1.,0.))
 u=unit(np.cross(ref,w)); v=np.cross(w,u); return u,v,w

@dataclass
class Chart:
 name: str
 material: str
 width: float
 height: float
 importance: float=1.0
 triangles: list=field(default_factory=list)
 rect: tuple|None=None

class Model:
 def __init__(self):
  self.vertices=[]; self.normals=[]; self.uv_local=[]; self.faces=[]
  self.charts=[]; self.face_chart=[]; self.face_part=[]; self.parts={}
 def chart(self,name,material,width,height,importance=1):
  c=Chart(name,material,max(width,.006),max(height,.006),importance)
  self.charts.append(c); return len(self.charts)-1
 def patch(self, verts, faces, uv, cid, part, normals=None):
  verts=np.asarray(verts,float); faces=np.asarray(faces,int); uv=np.asarray(uv,float)
  if normals is None:
   normals=np.zeros_like(verts)
   for f in faces:
    n=np.cross(verts[f[1]]-verts[f[0]],verts[f[2]]-verts[f[0]])
    for j in f: normals[j]+=n
   normals=np.array([unit(n) for n in normals])
  off=len(self.vertices); start=len(self.faces)
  self.vertices.extend(verts.tolist()); self.normals.extend(np.asarray(normals).tolist()); self.uv_local.extend(uv.tolist())
  self.faces.extend((faces+off).tolist()); self.face_chart.extend([cid]*len(faces)); self.face_part.extend([part]*len(faces))
  self.charts[cid].triangles.extend(range(start,len(self.faces)))
  self.parts.setdefault(part,[]).extend(range(start,len(self.faces)))
 def polygon(self,pts,cid,part,uv=None,normals=None):
  pts=np.asarray(pts,float); n=unit(np.cross(pts[1]-pts[0],pts[2]-pts[0]))
  if uv is None:
   u=unit(pts[1]-pts[0]); v=np.cross(n,u)
   xy=np.column_stack((pts@u,pts@v)); lo=xy.min(0); d=np.maximum(xy.max(0)-lo,1e-8)
   uv=(xy-lo)/d
  fs=[[0,i,i+1] for i in range(1,len(pts)-1)]
  self.patch(pts,fs,uv,cid,part,np.tile(n,(len(pts),1)) if normals is None else normals)
 def arrays(self):
  return np.asarray(self.vertices,np.float32), np.asarray(self.faces,np.uint32),np.asarray(self.normals,np.float32)

# Each polyhedron has a locally unwrapped, non-overlapping set of planar faces.
# Big display faces get their own large chart; bevels are collected per object.
def polyhedron(m,name,vertices,polys,material,importance=1,face_materials=None,feature_faces=None,smooth=False):
 vs=np.asarray(vertices,float); center=vs.mean(0); pinfo=[]
 weighted=np.zeros_like(vs)
 for k,ids0 in enumerate(polys):
  ids=list(ids0); pts=vs[ids]
  n=unit(np.cross(pts[1]-pts[0],pts[2]-pts[0]))
  if np.dot(n,pts.mean(0)-center)<0: ids=ids[::-1];pts=vs[ids];n=-n
  u=unit(pts[1]-pts[0]); v=np.cross(n,u)
  xy=np.column_stack((pts@u,pts@v)); lo=xy.min(0); wh=np.maximum(xy.max(0)-lo,.002)
  ar=sum(np.linalg.norm(np.cross(pts[i]-pts[0],pts[i+1]-pts[0]))*.5 for i in range(1,len(pts)-1))
  for j in ids: weighted[j]+=n*ar
  pinfo.append((ids,pts,n,(xy-lo)/wh,wh,ar))
 weighted=np.array([unit(n) for n in weighted])
 # Pack each material's polygon rectangles in a simple local shelf.
 # Separate six major panels only when explicitly requested.
 groups={}
 for k,p in enumerate(pinfo):
  mat=face_materials.get(k,material) if face_materials else material
  key=(mat,k if feature_faces and k in feature_faces else -1)
  groups.setdefault(key,[]).append(k)
 for (mat,feature),ks in groups.items():
  area=sum(float(np.prod(pinfo[k][4])) for k in ks)
  maxw=max(pinfo[k][4][0] for k in ks)
  shelfw=max(maxw,math.sqrt(area)*1.25)
  gap=.025 if importance>=1 else .025
  placements={}; x=0.;y=0.;rowh=0.;usedw=0.
  for k in sorted(ks,key=lambda k: -pinfo[k][4][1]):
   w,h=pinfo[k][4]
   if x+w>shelfw+1e-8 and x>0: y+=rowh+gap;x=0;rowh=0
   placements[k]=(x,y,w,h);x+=w+gap;rowh=max(rowh,h);usedw=max(usedw,x-gap)
  totalh=y+rowh
  cname=name+(f'_panel_{feature}' if feature>=0 else '_unwrap')
  cid=m.chart(cname,mat,usedw,totalh,importance)
  for k in ks:
   ids,pts,n,uv,wh,ar=pinfo[k];xx,yy,w,h=placements[k]
   tuv=(uv*np.array([w,h])+[xx,yy])/[usedw,totalh]
   m.polygon(pts,cid,name,tuv,weighted[ids] if smooth else None)


def bevel_box(m,name,center,dims,bevel,material,importance=1,rotation=None,feature=False):
 h=np.array(dims,float)/2;b=min(bevel,float(h.min())*.8)
 verts=[]
 for axis in range(3):
  for sx in [-1,1]:
   for sy in [-1,1]:
    for sz in [-1,1]:
     signs=np.array([sx,sy,sz]);p=(h-b)*signs;p[axis]=h[axis]*signs[axis];verts.append(p)
 vs=np.array(verts);polys=[]
 planes=[]
 for axis in range(3):
  for s in [-1,1]:
   n=np.eye(3)[axis]*s;planes.append((n,h[axis]))
 for a,baxis in [(0,1),(0,2),(1,2)]:
  for s in [-1,1]:
   for t in [-1,1]:
    n=np.zeros(3);n[a]=s;n[baxis]=t;planes.append((n,h[a]+h[baxis]-b))
 for sx in [-1,1]:
  for sy in [-1,1]:
   for sz in [-1,1]: planes.append((np.array([sx,sy,sz]),h.sum()-2*b))
 for n,d in planes:
  ids=np.where(abs(vs@n-d)<1e-6)[0]; nn=unit(n);u,v,_=basis(nn);c=vs[ids].mean(0)
  ids=ids[np.argsort(np.arctan2((vs[ids]-c)@v,(vs[ids]-c)@u))];polys.append(ids)
 if rotation is not None: vs=vs@np.asarray(rotation).T
 vs+=center
 polyhedron(m,name,vs,polys,material,importance,feature_faces=set(range(6)) if feature else None,smooth=True)


def simple_box(m,name,center,dims,material,rotation=None,importance=.7):
 h=np.array(dims)/2;vs=np.array([[x,y,z] for x in [-h[0],h[0]] for y in [-h[1],h[1]] for z in [-h[2],h[2]]])
 if rotation is not None:vs=vs@np.asarray(rotation).T
 vs+=center
 ps=[[0,4,6,2],[1,3,7,5],[0,1,5,4],[2,6,7,3],[0,2,3,1],[4,5,7,6]]
 polyhedron(m,name,vs,ps,material,importance)


def tube(m,name,points,radius,material,sides=8,closed=False,importance=.65,caps=True,section=None):
 pts=np.asarray(points,float);n=len(pts);lens=np.linalg.norm(np.diff(pts,axis=0),axis=1);cum=np.r_[0,np.cumsum(lens)]
 total=cum[-1]+(np.linalg.norm(pts[0]-pts[-1]) if closed else 0)
 tang=[]
 for i in range(n):
  t=pts[(i+1)%n]-pts[(i-1)%n] if closed else pts[min(i+1,n-1)]-pts[max(0,i-1)]
  tang.append(unit(t))
 base=unit(np.cross(tang[0],np.array([0.,0.,1.])))
 if np.linalg.norm(base)<.01:base=unit(np.cross(tang[0],np.array([0.,1.,0.])))
 frames=[base]
 for ii in range(1,n):
  previous=tang[ii-1];current=tang[ii];axis=np.cross(previous,current);sn=float(np.linalg.norm(axis));cs=float(np.dot(previous,current));uu=frames[-1]
  if sn>1e-10:
   axis/=sn;uu=uu*cs+np.cross(axis,uu)*sn+axis*np.dot(axis,uu)*(1-cs)
  frames.append(unit(uu-current*np.dot(uu,current)))
 if section is None: section=[(radius*math.cos(2*math.pi*j/sides),radius*math.sin(2*math.pi*j/sides)) for j in range(sides)]
 sides=len(section);section=np.asarray(section); perimeter=sum(np.linalg.norm(section[(j+1)%sides]-section[j]) for j in range(sides))
 cu=np.r_[0,np.cumsum([np.linalg.norm(section[(j+1)%sides]-section[j]) for j in range(sides)])]/perimeter
 verts=[];norms=[];uv=[]
 for i in range(n+(1 if closed else 0)):
  ii=i%n;t=tang[ii];u=frames[ii];v=np.cross(t,u)
  for j in range(sides+1):
   a,b=section[j%sides];off=a*u+b*v
   verts.append(pts[ii]+off);norms.append(unit(off));uv.append((cu[j],(total if i==n else cum[ii])/total))
 faces=[];rows=n if closed else n-1
 for i in range(rows):
  for j in range(sides):
   a=i*(sides+1)+j;b=a+sides+1;faces.extend([[a,a+1,b+1],[a,b+1,b]])
 cid=m.chart(name+'_tube',material,perimeter,total,importance);m.patch(verts,faces,uv,cid,name,norms)
 if not closed and caps:
  for i,s in [(0,-1),(n-1,1)]:
   inds=[i*(sides+1)+j for j in range(sides)]
   pp=np.array(verts)[inds]
   if np.dot(np.cross(pp[1]-pp[0],pp[2]-pp[0]),s*tang[i])<0:pp=pp[::-1]
   cc=m.chart(name+f'_cap_{i}',material,radius*2,radius*2,importance)
   m.polygon(pp,cc,name)


def lathe(m,name,center,axis,profile,material,segments=24,importance=1):
 # Profile = [(axis-distance, radius), ...]. Surface never overlaps in UV.
 center=np.asarray(center);u,v,w=basis(axis);profile=np.array(profile,float)
 d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(profile,axis=0),axis=1))];dist=max(d[-1],.001)
 verts=[];norms=[];uv=[]
 for i,(a,r) in enumerate(profile):
  dp=profile[min(i+1,len(profile)-1)]-profile[max(i-1,0)]
  for j in range(segments+1):
   t=2*math.pi*j/segments;rad=math.cos(t)*u+math.sin(t)*v
   verts.append(center+a*w+r*rad);norms.append(unit(dp[0]*rad-dp[1]*w));uv.append((j/segments,d[i]/dist))
 faces=[]
 for i in range(len(profile)-1):
  for j in range(segments):
   a=i*(segments+1)+j;b=a+segments+1;faces.extend([[a,a+1,b],[a+1,b+1,b]])
 cid=m.chart(name+'_shell',material,2*math.pi*max(profile[:,1]),dist,importance)
 m.patch(verts,faces,uv,cid,name,norms)


def disk(m,name,center,axis,radius,material,segments=24,importance=1,rings=None):
 center=np.asarray(center);u,v,w=basis(axis)
 if rings is None: rings=[(radius,0.)]
 verts=[center];uv=[(.5,.5)];norms=[w]
 for r,h in rings:
  for j in range(segments):
   t=2*math.pi*j/segments;rad=u*math.cos(t)+v*math.sin(t)
   verts.append(center+r*rad+h*w);uv.append((.5+.5*r/radius*math.cos(t),.5+.5*r/radius*math.sin(t)));norms.append(unit(w+.08*rad))
 faces=[]
 for j in range(segments):faces.append([0,1+j,1+(j+1)%segments])
 for k in range(len(rings)-1):
  for j in range(segments):
   a=1+k*segments+j;b=1+k*segments+(j+1)%segments;c=a+segments;d=b+segments;faces.extend([[a,c,d],[a,d,b]])
 cid=m.chart(name+'_face',material,radius*2,radius*2,importance);m.patch(verts,faces,uv,cid,name,norms)


def rounded_loop(cx,cy,sx,sy,z,corner=.09):
 pts=[]
 for x,y,start in [(cx+sx/2-corner,cy+sy/2-corner,0),(cx-sx/2+corner,cy+sy/2-corner,90),(cx-sx/2+corner,cy-sy/2+corner,180),(cx+sx/2-corner,cy-sy/2+corner,270)]:
  for a in [start,start+45,start+90]:
   t=math.radians(a);pts.append((x+corner*math.cos(t),y+corner*math.sin(t),z))
 return pts


def fender(m,name,xc,side):
 # Wide, squared molded wheel arch, rather than a stack of little boxes.
 path=np.array([[-.545,.69],[-.49,.965],[-.36,1.09],[-.12,1.145],[.17,1.145],[.39,1.06],[.49,.90],[.52,.73]])
 # x,z path from rear to nose. Rail section: y offset, radial offset.
 width=.43;thick=.15;b=.038
 sec=np.array([[-width/2+b,-thick/2],[width/2-b,-thick/2],[width/2,-thick/2+b],[width/2,thick/2-b],[width/2-b,thick/2],[-width/2+b,thick/2],[-width/2,thick/2-b],[-width/2,-thick/2+b]])
 # bottom and top sides are all separately covered once by one strip chart.
 length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
 perim=np.r_[0,np.cumsum([np.linalg.norm(sec[(i+1)%8]-sec[i]) for i in range(8)])]
 verts=[];norms=[];uv=[]
 for i,p in enumerate(path):
  tan=unit(path[min(i+1,len(path)-1)]-path[max(0,i-1)]);out=np.array([-tan[1],tan[0]])
  for j in range(9):
   s=sec[j%8];q=p+out*s[1];verts.append([xc+q[0],side*(.64+s[0]),q[1]])
   # chamfer-weighted normals make the broad top read as a soft solid shell.
   ni=unit([out[0]*(s[1]/thick),side*(s[0]/width),out[1]*(s[1]/thick)])
   norms.append(ni);uv.append((perim[j]/perim[-1],length[i]/length[-1]))
 faces=[]
 for i in range(len(path)-1):
  for j in range(8):
   a=i*9+j;b=a+9; f=[[a,a+1,b+1],[a,b+1,b]]
   for tri in f:
    pp=np.array(verts)[tri]; n=np.cross(pp[1]-pp[0],pp[2]-pp[0]); ref=np.array(norms)[tri].mean(0)
    if np.dot(n,ref)<0:tri=tri[::-1]
    faces.append(tri)
 cid=m.chart(name+'_continuous', 'teal',perim[-1],length[-1],1.25)
 m.patch(verts,faces,uv,cid,name,norms)
 for i in [0,len(path)-1]:
  pp=np.array(verts)[i*9:i*9+8]; cid=m.chart(name+f'_end_{i}','teal',width,thick,.75)
  n=unit(np.array([path[min(i+1,len(path)-1),0]-path[max(0,i-1),0],0,path[min(i+1,len(path)-1),1]-path[max(0,i-1),1]]))*(1 if i else -1)
  if np.dot(np.cross(pp[1]-pp[0],pp[2]-pp[0]),n)<0:pp=pp[::-1]
  m.polygon(pp,cid,name)


def seat(m):
 # Elliptic/chamfered saddle: wider and higher at the rear; no tiny upholstery geometry.
 outline=np.array([[-.70,-.23],[-.64,-.315],[-.38,-.33],[.03,-.255],[.28,-.175],[.32,.175],[.03,.255],[-.38,.33],[-.64,.315],[-.70,.23]])
 center=np.array([-.20,0.]);verts=[]
 for scale,drop in [(1.,.14),(1.015,.07),(.95,.01),(.77,-.016)]:
  for x,y in (outline-center)*scale+center:
   z=1.32-.10*(x+.5);verts.append([x,y,z-drop])
 polys=[];N=len(outline)
 polys.append(list(range(N-1,-1,-1)))
 for k in range(3):
  for j in range(N):polys.append([k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j])
 polys.append(list(range(3*N,4*N)))
 polyhedron(m,'Seat_Saddle',verts,polys,'seat',1.5,feature_faces={len(polys)-1},smooth=True)


def body_shell(m):
 # Cross-sectional loft for cream waist, fuel-tank and broad front shoulder.
 sections=[(-.93,.39,.69,1.095),(-.69,.43,.59,1.19),(-.30,.35,.55,1.20),(.12,.35,.55,1.24),(.40,.39,.71,1.41),(.64,.46,.79,1.24),(.94,.52,.81,1.16),(1.12,.51,.81,1.105)]
 verts=[]
 for x,w,bottom,top in sections:
  # octagonal vertical section around YZ.
  for y,z in [(-w+.055,bottom), (w-.055,bottom),(w,bottom+.085),(w,top-.085),(w-.095,top),(-w+.095,top),(-w,top-.085),(-w,bottom+.085)]:verts.append([x,y,z])
 # Treat long panels as coherent UV strips, one per octagonal side.
 vs=np.array(verts);N=8;count=len(sections)
 smooth_n=np.zeros_like(vs)
 for ii in range(count-1):
  for jj in range(N):
   kk=(jj+1)%N;ix=[ii*N+jj,ii*N+kk,(ii+1)*N+kk,(ii+1)*N+jj];pp=vs[ix]
   nn=np.cross(pp[1]-pp[0],pp[2]-pp[0])+np.cross(pp[2]-pp[0],pp[3]-pp[0])
   wanted=pp.mean(0)-np.array([pp[:,0].mean(),0,.98])
   if np.dot(nn,wanted)<0:nn=-nn
   for vid in ix:smooth_n[vid]+=nn
 smooth_n=np.array([unit(nn) for nn in smooth_n])
 for j in range(N):
  vv=[];uv=[];ns=[]
  for i in range(count):
   for jj in [j,(j+1)%N]:
    vv.append(vs[i*N+jj]);uv.append((i/(count-1),0. if jj==j else 1.));ns.append(smooth_n[i*N+jj])
  fs=[]
  for i in range(count-1):fs.extend([[i*2,i*2+1,i*2+3],[i*2,i*2+3,i*2+2]])
  pp=np.array(vv);check=np.cross(pp[1]-pp[0],pp[3]-pp[0]);want=pp[:4].mean(0)-np.array([pp[:4,0].mean(),0,.98])
  if np.dot(check,want)<0:fs=[t[::-1] for t in fs]
  l=sum(np.linalg.norm((vs[i*N+j]+vs[i*N+(j+1)%N])*.5-(vs[(i-1)*N+j]+vs[(i-1)*N+(j+1)%N])*.5) for i in range(1,count))
  w=np.mean([np.linalg.norm(vs[i*N+j]-vs[i*N+(j+1)%N]) for i in range(count)])
  cid=m.chart(f'Body_Cream_Panel_{j}','cream',l,w,1.35 if j in [2,3,4,5,6] else .8)
  m.patch(vv,fs,uv,cid,'Body_Cream',ns)
 for i in [0,count-1]:
  pp=vs[i*N:(i+1)*N]
  if np.dot(np.cross(pp[1]-pp[0],pp[2]-pp[0]),[(-1 if i==0 else 1),0,0])<0:pp=pp[::-1]
  cid=m.chart('Body_'+('Rear' if i==0 else 'Front'),'cream',sections[i][1]*2,sections[i][3]-sections[i][2],1.35)
  m.polygon(pp,cid,'Body_Cream')


def tire(m,label,x,y,z):
 axis=[0,1,0];c=np.array([x,y,z]);outer=1 if y>0 else -1
 # 6-ring radial carcass; coarse tread is real silhouette geometry.
 profile=[(-.19,.225),(-.218,.31),(-.175,.397),(-.115,.425),(.115,.425),(.175,.397),(.218,.31),(.19,.225)]
 lathe(m,'Wheel_'+label+'_Rubber',c,axis,profile,'rubber',20,.8)
 # Actual topological surfaces for both sidewalls; radial disk/annulus for rims.
 for side in [-1,1]:
  surf=c+np.array([0,side*.195,0]);ax=[0,side,0]
  lathe(m,'Wheel_'+label+f'_Rim_{side}',surf,ax,[(0.,.218),(.022,.22),(.035,.194),(.023,.163),(.01,.15)],'rim',16,.8)
  disk(m,'Wheel_'+label+f'_Well_{side}',surf+np.array([0,side*.012,0]),ax,.163,'frame',16,.65)
  disk(m,'Wheel_'+label+f'_Hub_{side}',surf+np.array([0,side*.027,0]),ax,.062,'orange',12,1.)
 # Eighteen broad, alternating asymmetric chevron lugs. Each has its own unwrap.
 for row in [-1,1]:
  for k in range(9):
   t=2*math.pi*(k/9+(0.025 if row>0 else 0))
   rad=np.array([math.cos(t),0.,math.sin(t)]);tan=np.array([-math.sin(t),0.,math.cos(t)]);across=np.array([0.,float(row),0.])
   # 6-sided footprint, clipped corners, slanted toward the centerline.
   outline=np.array([[-.080,-.088],[.048,-.088],[.092,-.025],[.082,.089],[-.045,.11],[-.091,.049]])
   vs=[]
   for scale,height in [(1.,.408),(.91,.463)]:
    for q,r in outline*scale:
     lateral=.099+r
     rr=height-.62*max(0.,lateral-.105)
     vs.append(c+rad*rr+tan*(q*1.16+.35*r)+across*lateral)
   N=6;ps=[list(range(N-1,-1,-1)),list(range(N,2*N))]
   for j in range(N):ps.append([j,(j+1)%N,(j+1)%N+N,j+N])
   polyhedron(m,f'Wheel_{label}_Lug_{row}_{k:02}',vs,ps,'tread',.45,smooth=False)


def build_model():
 m=Model();body_shell(m);seat(m)
 bevel_box(m,'Chassis_Core',(0,0,.63),(1.48,.58,.27),.065,'frame',.6)
 bevel_box(m,'Engine_Block',(-.02,0,.66),(.50,.67,.34),.065,'bumper',.65)
 for side in [-1,1]:
  s='L' if side>0 else 'R'
  fender(m,'Fender_Front_'+s,.70,side);fender(m,'Fender_Rear_'+s,-.72,side)
  bevel_box(m,'Footwell_'+s,(-.02,side*.52,.545),(.72,.37,.085),.025,'bumper',1.)
  bevel_box(m,'Footwell_Outer_'+s,(-.02,side*.687,.59),(.68,.065,.12),.021,'frame',.8)
  # Rear side cream tip peeking beyond the teal shell.
  bevel_box(m,'Rear_Cream_Tip_'+s,(-1.05,side*.52,.975),(.19,.29,.26),.055,'cream',.95)
 for label,x,y in [('FL',.70,.69),('FR',.70,-.69),('RL',-.72,.69),('RR',-.72,-.69)]:tire(m,label,x,y,.465)
 # Undercarriage: simple arms, stout shafts and four orange suspension coils.
 for end,x in [('Front',.70),('Rear',-.72)]:
  tube(m,end+'_Axle',[(x,-.63,.45),(x,.63,.45)],.054,'frame',8)
  bevel_box(m,end+'_Diff',(x,0,.465),(.26,.27,.24),.049,'bumper',.7)
  for side in [-1,1]:
   s='L' if side>0 else 'R'
   for dx in [-.16,.16]:tube(m,end+'_Wishbone_'+s+str(dx),[(x+dx,side*.18,.50),(x,side*.56,.47)],.034,'frame',6)
   p0=np.array([x+.05,side*.48,.53]);p1=np.array([x-.075,side*.405,.925])
   tube(m,end+'_Shock_'+s,[p0,p1],.029,'steel',8)
   u,v,w=basis(p1-p0);coil=[]
   for j in range(25):
    t=j/24;ang=2*math.pi*3.4*t
    coil.append(p0+(p1-p0)*(.12+.78*t)+.064*(u*math.cos(ang)+v*math.sin(ang)))
   tube(m,end+'_Spring_'+s,coil,.020,'orange',5,importance=.65)
 # Front face and headlights, distinctive circular light signature.
 bevel_box(m,'Front_Cream_Fascia',(1.075,0,.995),(.21,1.15,.35),.065,'cream',1.4)
 for side in [-1,1]:
  s='L' if side>0 else 'R';c=np.array([1.181,side*.345,1.005])
  lathe(m,'Headlight_'+s+'_Bezel',c,[1,0,0],[(0,.148),(.025,.148),(.041,.13),(.037,.112)],'rim',24,1.2)
  lathe(m,'Headlight_'+s+'_Gasket',c+[.035,0,0],[1,0,0],[(0,.12),(.009,.117),(.012,.10)],'grille',24,1.)
  disk(m,'Headlight_'+s+'_Lens',c+[.049,0,0],[1,0,0],.106,'lamp',24,1.6,rings=[(.084,.003),(.106,-.009)])
  bevel_box(m,'Front_Indicator_'+s,(1.123,side*.64,1.025),(.066,.102,.133),.025,'orange',1.2)
 bevel_box(m,'Front_Grille',(1.203,0,.935),(.037,.275,.221),.022,'grille',1.7,feature=True)
 # Bumper frame with large readable opening, not a solid rectangle.
 bumper=[(1.255,-.32,.40),(1.275,-.40,.45),(1.285,-.43,.60),(1.26,-.38,.675),(1.26,.38,.675),(1.285,.43,.60),(1.275,.40,.45),(1.255,.32,.40)]
 section=[(-.061,-.045),(.061,-.045),(.078,-.028),(.078,.028),(.061,.045),(-.061,.045),(-.078,.028),(-.078,-.028)]
 tube(m,'Front_Bumper',bumper,.07,'bumper',8,section=section,importance=1.)
 bevel_box(m,'Front_Skid',(1.231,0,.505),(.1,.37,.265),.040,'frame',1.1)
 bevel_box(m,'Front_Tow_Socket',(1.292,0,.507),(.025,.093,.076),.015,'grille',1.)
 # Rear lamps/valance/exhaust mirror the major features of the supplied rear view.
 bevel_box(m,'Rear_Valance',(-1.15,0,1.012),(.17,.61,.30),.055,'frame',1.2)
 for side in [-1,1]:
  s='L' if side>0 else 'R'
  bevel_box(m,'Rear_Lamp_Housing_'+s,(-1.146,side*.47,1.03),(.105,.26,.20),.046,'teal',1.3)
  bevel_box(m,'Rear_Amber_Lens_'+s,(-1.211,side*.47,1.044),(.027,.211,.137),.027,'orange',1.5,feature=True)
 bevel_box(m,'Rear_Exhaust_Box',(-1.135,0,.777),(.25,.246,.20),.043,'bumper',1.)
 lathe(m,'Rear_Exhaust_Rim',(-1.264,0,.777),[-1,0,0],[(0,.061),(.010,.061),(.016,.043)],'steel',16,.9)
 disk(m,'Rear_Exhaust_Dark',(-1.28,0,.777),[-1,0,0],.043,'grille',16,.9)
 bevel_box(m,'Rear_Tow_Recess',(-1.244,0,1.037),(.015,.12,.053),.014,'grille',.9)
 # Cargo racks: square-section black rails and sparse structural slats.
 section=[(-.033,-.022),(.033,-.022),(.043,-.012),(.043,.012),(.033,.022),(-.033,.022),(-.043,.012),(-.043,-.012)]
 for end,x,z in [('Front',.835,1.275),('Rear',-.865,1.318)]:
  tube(m,end+'_Rack_Rail',rounded_loop(x,0,.54,1.22,z,.11),.04,'frame',8,True,1.1,section=section)
  for yi in [-.23,.23]:bevel_box(m,end+f'_Rack_Slat_{yi}',(x,yi,z-.011),(.50,.058,.055),.013,'frame',.8)
  for xx in [x-.18,x+.18]:
   for yy in [-.585,.585]:simple_box(m,end+f'_Rack_Post_{xx}_{yy}',(xx,yy,z-.090),(.07,.065,.145),'frame',importance=.55)
 # Handlebar, collars and orange-ended grips.
 tube(m,'Steering_Stem',[(.405,0,1.345),(.38,0,1.553)],.06,'frame',8)
 points=[(.36,-.54,1.741),(.35,-.36,1.73),(.33,-.27,1.62),(.32,-.14,1.578),(.32,.14,1.578),(.33,.27,1.62),(.35,.36,1.73),(.36,.54,1.741)]
 tube(m,'Handlebar',points,.043,'frame',8,importance=1.)
 for side in [-1,1]:
  s='L' if side>0 else 'R';axis=[0,side,0]
  lathe(m,'Grip_'+s,(.36,side*.43,1.741),axis,[(0,.057),(.026,.062),(.25,.06),(.276,.05)],'rubber',12,1.3)
  disk(m,'Grip_'+s+'_End',(.36,side*.709,1.741),axis,.057,'orange',12,1.2)
  lathe(m,'Grip_'+s+'_Collar',(.36,side*.385,1.741),axis,[(0,.065),(.02,.086),(.073,.086),(.085,.066)],'frame',12,.9)
  disk(m,'Grip_'+s+'_CollarSide',(.36,side*.385,1.741),[0,-side,0],.066,'frame',12,.7)
 # Console has large unwrapped front/back surfaces; small symbols live in texture.
 ry=.18;rot=np.array([[math.cos(ry),0,math.sin(ry)],[0,1,0],[-math.sin(ry),0,math.cos(ry)]])
 bevel_box(m,'Console_Case',(.40,0,1.578),(.13,.345,.242),.037,'frame',1.4,rotation=rot)
 bevel_box(m,'Console_Cream_Face',(.474,0,1.583),(.018,.28,.184),.012,'cream',2.,rotation=rot,feature=True)
 bevel_box(m,'Console_Rear_Teal',(.328,0,1.594),(.022,.29,.190),.015,'teal',1.4,rotation=rot)
 bevel_box(m,'Console_Rear_Display',(.309,0,1.603),(.012,.224,.130),.005,'screen',2.,rotation=rot,feature=True)
 # Ground pivot: centre of the vehicle footprint, bottom at Z=0.
 zmin=min(v[2] for v in m.vertices)
 m.ground_shift=-zmin
 for v in m.vertices: v[2]-=zmin
 return m

if __name__=='__main__':
 m=build_model(); print('triangles',len(m.faces),'charts',len(m.charts),'parts',len(m.parts))
