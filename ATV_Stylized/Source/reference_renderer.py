"""Optional CPU reference renderer. Uses delivered mesh data; not an Unreal/Blender screenshot.
Dependencies: numpy, Pillow, numba. Built-in ray-traced shadows/contact AO.
"""
import os, sys, math, time
from pathlib import Path
import numpy as np
from PIL import Image
from numba import njit, prange, set_num_threads, config
set_num_threads(min(5, config.NUMBA_NUM_THREADS))
ROOT=Path(__file__).resolve().parents[1]
D=np.load(ROOT/'Source/mesh_data.npz')
V=D['vertices'].astype(np.float64);F=D['faces'];N=D['normals'].astype(np.float64);UV=D['uv'].astype(np.float64)

def unit(x):return np.array(x)/np.linalg.norm(x)

@njit
def raster(v,f,n,uv,proj,tex,orm,outp,outn,outc,outr,zbuf):
 H,W=zbuf.shape;TH,TW=tex.shape[:2]
 for k in range(len(f)):
  a,b,c=f[k];pa,pb,pc=proj[a],proj[b],proj[c]
  minx=max(0,int(math.floor(min(pa[0],pb[0],pc[0]))));maxx=min(W-1,int(math.ceil(max(pa[0],pb[0],pc[0]))))
  miny=max(0,int(math.floor(min(pa[1],pb[1],pc[1]))));maxy=min(H-1,int(math.ceil(max(pa[1],pb[1],pc[1]))))
  den=(pb[1]-pc[1])*(pa[0]-pc[0])+(pc[0]-pb[0])*(pa[1]-pc[1])
  if abs(den)<1e-12:continue
  for y in range(miny,maxy+1):
   for x in range(minx,maxx+1):
    px=x+.5;py=y+.5
    w0=((pb[1]-pc[1])*(px-pc[0])+(pc[0]-pb[0])*(py-pc[1]))/den
    w1=((pc[1]-pa[1])*(px-pc[0])+(pa[0]-pc[0])*(py-pc[1]))/den
    w2=1-w0-w1
    if w0<-.000001 or w1<-.000001 or w2<-.000001:continue
    z=w0*pa[2]+w1*pb[2]+w2*pc[2]
    if z<=zbuf[y,x]:continue
    zbuf[y,x]=z
    outp[y,x]=v[a]*w0+v[b]*w1+v[c]*w2
    nor=n[a]*w0+n[b]*w1+n[c]*w2;ln=math.sqrt((nor*nor).sum())
    if ln>1e-10:nor/=ln
    outn[y,x]=nor
    u=uv[a,0]*w0+uv[b,0]*w1+uv[c,0]*w2;vv=uv[a,1]*w0+uv[b,1]*w1+uv[c,1]*w2
    tx=min(TW-1,max(0,int(u*TW)));ty=min(TH-1,max(0,int((1-vv)*TH)))
    outc[y,x]=tex[ty,tx];outr[y,x]=orm[ty,tx]/255.

# Compact median-split triangle BVH used for real cast shadows and contact AO.
T=V[F]
lo=[];hi=[];left=[];right=[];starts=[];counts=[];order=[]
def node(ids):
 i=len(lo);lo.append(T[ids].min((0,1)));hi.append(T[ids].max((0,1)));left.append(-1);right.append(-1);starts.append(-1);counts.append(0)
 if len(ids)<=8:starts[i]=len(order);counts[i]=len(ids);order.extend(ids);return i
 cen=T[ids].mean(1);axis=np.ptp(cen,axis=0).argmax();ids=ids[np.argsort(cen[:,axis])];mid=len(ids)//2
 left[i]=node(ids[:mid]);right[i]=node(ids[mid:]);return i
node(np.arange(len(F)))
LO=np.array(lo);HI=np.array(hi);LEFT=np.array(left);RIGHT=np.array(right);START=np.array(starts);COUNT=np.array(counts);TRIS=T[np.array(order)]
E1=TRIS[:,1]-TRIS[:,0];E2=TRIS[:,2]-TRIS[:,0];T0=TRIS[:,0]

@njit(inline='always')
def boxhit(o,d,lo,hi,maxdist):
 tmin=.0003;tmax=maxdist
 for k in range(3):
  if abs(d[k])<1e-12:
   if o[k]<lo[k] or o[k]>hi[k]:return False
  else:
   a=(lo[k]-o[k])/d[k];b=(hi[k]-o[k])/d[k]
   if a>b:a,b=b,a
   tmin=max(tmin,a);tmax=min(tmax,b)
   if tmax<tmin:return False
 return True

@njit(inline='always')
def trihit(o,d,p,e1,e2,maxdist):
 px=d[1]*e2[2]-d[2]*e2[1];py=d[2]*e2[0]-d[0]*e2[2];pz=d[0]*e2[1]-d[1]*e2[0]
 det=e1[0]*px+e1[1]*py+e1[2]*pz
 if abs(det)<1e-10:return False
 inv=1/det;sx=o[0]-p[0];sy=o[1]-p[1];sz=o[2]-p[2];u=(sx*px+sy*py+sz*pz)*inv
 if u<0 or u>1:return False
 qx=sy*e1[2]-sz*e1[1];qy=sz*e1[0]-sx*e1[2];qz=sx*e1[1]-sy*e1[0];v=(d[0]*qx+d[1]*qy+d[2]*qz)*inv
 if v<0 or u+v>1:return False
 t=(e2[0]*qx+e2[1]*qy+e2[2]*qz)*inv
 return t>.0003 and t<maxdist

@njit
def blocked(o,d,maxdist,lo,hi,left,right,start,count,t0,e1,e2):
 stack=np.empty(64,np.int64);sp=1;stack[0]=0
 while sp:
  sp-=1;i=stack[sp]
  if not boxhit(o,d,lo[i],hi[i],maxdist):continue
  if count[i]>0:
   for j in range(start[i],start[i]+count[i]):
    if trihit(o,d,t0[j],e1[j],e2[j],maxdist):return True
  else:
   stack[sp]=left[i];sp+=1;stack[sp]=right[i];sp+=1
 return False

@njit(parallel=True)
def shade(pos,nor,col,rough,view,zbuf,lo,hi,left,right,start,count,t0,e1,e2,samples):
 H,W=zbuf.shape;out=np.zeros((H,W,3),np.float64)
 key=np.array([2.0,-3.5,6.0]);fill=np.array([-3.,2.,4.]);fill/=np.linalg.norm(fill)
 for y in prange(H):
  for x in range(W):
   p=pos[y,x];n=nor[y,x];o=p+n*.003
   material=col[y,x];r=rough[y,x,1];metal=rough[y,x,2]
   base=np.empty(3)
   for cc in range(3):
    b=material[cc]/255.;base[cc]=b/12.92 if b<=.04045 else ((b+.055)/1.055)**2.4
   # orient sample basis
   if abs(n[2])<.95:u=np.array([-n[1],n[0],0.]);u/=max(np.linalg.norm(u),1e-12)
   else:u=np.array([1.,0.,0.])
   v=np.cross(n,u);ao=0.;diff=0.;spec=0.
   phase=((x*1973+y*9277)%1009)/1009*6.283185
   for s in range(samples):
    q=(s+.5)/samples;theta=s*2.39996323+phase
    d=(u*math.cos(theta)+v*math.sin(theta))*math.sqrt(q)+n*math.sqrt(1-q)
    if blocked(o,d,.34,lo,hi,left,right,start,count,t0,e1,e2):ao+=1
    # broad area key, physically traced against the asset
    lp=key+np.array([math.cos(theta)*.95*math.sqrt(q),math.sin(theta)*.95*math.sqrt(q),0.])
    ld=lp-p;dist=np.linalg.norm(ld);ld/=dist
    ndl=max(0.,np.dot(n,ld))
    if ndl>0 and not blocked(o,ld,dist,lo,hi,left,right,start,count,t0,e1,e2):
     diff+=ndl
     h=ld+view;h/=max(np.linalg.norm(h),1e-10)
     power=10+90*(1-r)**2
     spec+=(max(0.,np.dot(n,h))**power)*(.035+.10*(1-r)+metal*.15)
   ao=1-.64*ao/samples;diff/=samples;spec/=samples
   # Ground plane is almost-white rather than a white clipping background.
   illum=(.42+.13*max(0.,n[2]))*ao+.68*diff+.17*max(0.,np.dot(n,fill))*ao
   rgb=base*illum+spec
   if material[0]>235 and material[1]>195 and r<.35:rgb+=base*.17
   # Inverse sRGB display transfer, no artificial color grading.
   for cc in range(3):
    val=max(0.,rgb[cc]);val=12.92*val if val<=.0031308 else 1.055*val**(1/2.4)-.055
    out[y,x,cc]=min(1.,max(0.,val))
 return out

def render(name,cam=(3.5,-4.4,3.),target=(0,0,.80),scale=3.4,W=1100,H=1000,samples=8):
 toward=unit(np.array(cam)-target);right=unit(np.cross([0,0,1],toward));up=np.cross(toward,right)
 proj=np.column_stack(((V-target)@right,(V-target)@up,(V-target)@toward));ppu=W/scale
 proj[:,0]=proj[:,0]*ppu+W/2;proj[:,1]=H/2-proj[:,1]*ppu
 yy,xx=np.mgrid[:H,:W];pos=np.empty((H,W,3),np.float64)
 anchors=np.array(target)+(xx[:,:,None]+.5-W/2)/ppu*right+(H/2-yy[:,:,None]-.5)/ppu*up
 # Orthographic ray-plane intersection for floor (Z = -.012)
 tt=(anchors[:,:,2]+.012)/toward[2]
 pos[:]=anchors-tt[:,:,None]*toward
 nor=np.zeros_like(pos);nor[:,:,2]=1
 col=np.full_like(pos,246.);rough=np.ones_like(pos);rough[:,:,2]=0
 zbuf=np.full((H,W),-1e6,np.float64)
 tex=np.array(Image.open(ROOT/'Textures/T_ATV_BaseColor.png').convert('RGB')).astype(np.float64)
 orm=np.array(Image.open(ROOT/'Textures/T_ATV_ORM.png').convert('RGB')).astype(np.float64)
 raster(V,F,N,UV,proj,tex,orm,pos,nor,col,rough,zbuf)
 out=shade(pos,nor,col,rough,toward,zbuf,LO,HI,LEFT,RIGHT,START,COUNT,T0,E1,E2,samples)
 # Slightly supersample in the final production passes instead of fake contours.
 im=Image.fromarray((out*255+.5).astype(np.uint8));im.save(ROOT/'Preview'/name)
 print(name,flush=True)

if __name__=='__main__':
 name=sys.argv[1] if len(sys.argv)>1 else 'Front_Test.png'
 view=sys.argv[2] if len(sys.argv)>2 else 'front'
 if view=='rear':render(name,(-3.8,-4.4,3.),samples=12)
 elif view=='top':render(name,(2.,-2.5,6.),target=(0,0,.7),scale=3.55,samples=12)
 elif view=='side':render(name,(0,-5,2.2),target=(0,0,.85),scale=3.45,samples=12)
 else:render(name,samples=12)
