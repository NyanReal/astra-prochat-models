"""Convert the generated ground-only crop into a repeating, soft-painted albedo.
Input pixels are from image generation, not from the browser preview.
The generated showcase itself is not used as a backdrop or a fake render.
"""
from pathlib import Path
from PIL import Image,ImageEnhance,ImageFilter
import numpy as np,json,shutil
ROOT=Path(__file__).resolve().parents[1]
rng=np.random.default_rng(20261008)
# Saved independently so this conversion is reproducible without the original showcase.
src=ROOT/'assets/forest_floor_source_crop.png'
if not src.exists():
 im=Image.open('/mnt/data/a_wide_stylized_painterly_3d_rendered_screenshot.png')
 im.crop((875,780,1200,925)).save(src)
im=Image.open(src).convert('RGB').resize((600,420),Image.Resampling.LANCZOS)
im=ImageEnhance.Color(im).enhance(.68)
s=np.asarray(im,dtype=float)
# Gentle local illumination flattening. Stylized albedo still has painted detail.
low=np.asarray(im.filter(ImageFilter.GaussianBlur(34)),float)
s=np.clip(s*.78+(s-low+low.mean((0,1)))*.22,0,255)
# Image quilting with minimum error overlap seams, using only generated floor pixels.
P,O=168,36;STEP=P-O;N=1056
canvas=np.zeros((N+P,N+P,3),float)
def seam(err):
 h,w=err.shape;acc=err.copy();back=np.zeros((h,w),int)
 for y in range(1,h):
  opts=np.stack([np.r_[np.inf,acc[y-1,:-1]],acc[y-1],np.r_[acc[y-1,1:],np.inf]])
  delta=opts.argmin(0)-1;back[y]=np.arange(w)+delta;acc[y]+=opts.min(0)
 out=np.empty(h,int);out[-1]=acc[-1].argmin()
 for y in range(h-2,-1,-1):out[y]=back[y+1,out[y+1]]
 return out
for y in range(0,N,STEP):
 for x in range(0,N,STEP):
  candidates=[]
  for c in range(24):
   xx=int(rng.integers(0,s.shape[1]-P));yy=int(rng.integers(0,s.shape[0]-P))
   p=s[yy:yy+P,xx:xx+P].copy();p=np.rot90(p,int(rng.integers(0,4)))
   if rng.random()<.5:p=p[:,::-1]
   cost=0.
   if x:cost+=np.mean((canvas[y:y+P,x:x+O]-p[:,:O])**2)
   if y:cost+=np.mean((canvas[y:y+O,x:x+P]-p[:O])**2)
   candidates.append((cost,p))
  p=min(candidates,key=lambda a:a[0])[1]
  mask=np.ones((P,P),bool)
  if x:
   edge=seam(np.sum((canvas[y:y+P,x:x+O]-p[:,:O])**2,axis=2))
   for row,e in enumerate(edge):mask[row,:e]=False
  if y:
   edge=seam(np.sum((canvas[y:y+O,x:x+P]-p[:O])**2,axis=2).T)
   for col,e in enumerate(edge):mask[:e,col]=False
  old=canvas[y:y+P,x:x+P];canvas[y:y+P,x:x+P]=np.where(mask[:,:,None],p,old)
u=canvas[:1024,:1024]
# Periodic/smooth decomposition (FFT Poisson solve), removes large edge jumps.
h,w=u.shape[:2];v=np.zeros_like(u)
v[0]+=u[-1]-u[0];v[-1]+=u[0]-u[-1];v[:,0]+=u[:,-1]-u[:,0];v[:,-1]+=u[:,0]-u[:,-1]
den=2*np.cos(2*np.pi*np.arange(h)/h)[:,None]+2*np.cos(2*np.pi*np.arange(w)/w)[None,:]-4;den[0,0]=1
smooth=np.fft.fft2(v,axes=(0,1))/den[:,:,None];smooth[0,0]=0
u-=np.fft.ifft2(smooth,axes=(0,1)).real
# A little less contrast than a hero texture so the canopy remains the focus.
u=(u-u.mean((0,1)))*.82+u.mean((0,1));u=u*.90+np.array([175,178,119])*.10
out=Image.fromarray(np.uint8(np.clip(u,0,255)))
out.save(ROOT/'assets/forest_floor_basecolor.jpg',quality=94,subsampling=0)
(ROOT/'assets/forest_floor_provenance.json').write_text(json.dumps({
 'source':'Image-generated forest artwork, isolated floor-only crop',
 'processing':'crop, local contrast moderation, deterministic image quilting, periodic edge correction',
 'basecolor':'forest_floor_basecolor.jpg','size':[1024,1024],
 'not_used':'No generated whole-scene image or generated UI is used as the web scene',
 'note':'An artistic color texture, not measured scan data; fine painted shading remains.'},indent=2))
print('generated-floor crop -> 1024px periodic texture')
# The generated ground contains standing-plant silhouettes. Keep its painted
# micro-detail, but suppress those shapes with a broad moss/loam control layer.
# This processing is deliberately documented rather than calling it a raw image-gen tile.
from scipy.ndimage import gaussian_filter, map_coordinates
from PIL import ImageDraw
rng=np.random.default_rng(7117)
N=1024
Y,X=np.mgrid[:N,:N]
def noise(size):
 small=rng.random((size,size))
 return np.clip(map_coordinates(small,[Y*size/N,X*size/N],order=3,mode="grid-wrap"),0,1)
coarse=(noise(5)*.58+noise(11)*.28+noise(25)*.14)
fine=noise(90)
mask=np.clip((coarse-.40)/.22,0,1);mask=mask*mask*(3-2*mask)
baseLoam=np.array([185.,161.,119.]);baseMoss=np.array([107.,126.,69.])
palette=baseLoam[None,None,:]*(1-mask[:,:,None])+baseMoss[None,None,:]*mask[:,:,None]
gen=np.asarray(out,float);lum=gen.mean(2)
high=lum-gaussian_filter(lum,6,mode='wrap')
palette+=high[:,:,None]*.25+(fine[:,:,None]-.5)*12
# Low-opacity influence from the actual image-generated RGB material.
palette=palette*.88+gen*.12
tex=Image.fromarray(np.uint8(np.clip(palette,0,255)))
d=ImageDraw.Draw(tex,'RGBA')
# Sparse flat leaf litter and pebbles: details remain subordinate to 3D grasses.
for i in range(70):
 x=int(rng.integers(20,N-20));y=int(rng.integers(20,N-20));ang=float(rng.uniform(0,6.283))
 if mask[y,x]>.80 and rng.random()>.3:continue
 if i%4==0:
  w=int(rng.integers(3,8));h=int(rng.integers(3,6));d.ellipse((x-w,y-h,x+w,y+h),fill=(143,138,111,175))
  d.arc((x-w,y-h,x+w,y+h),180,270,fill=(193,187,151,160),width=2)
 else:
  le=float(rng.uniform(6,13));wi=float(rng.uniform(2,4));cs=np.cos(ang);sn=np.sin(ang)
  points=[(0,-le),(.75*wi,-.3*le),(wi,.2*le),(0,le),(-wi,.2*le),(-.7*wi,-.35*le)]
  pts=[(x+a*cs-b*sn,y+a*sn+b*cs) for a,b in points]
  d.polygon(pts,fill=(153+int(rng.integers(-12,15)),121+int(rng.integers(-8,14)),66,190))
  d.line([(x-le*.7*sn,y+le*.7*cs),(x+le*.7*sn,y-le*.7*cs)],fill=(114,107,62,105),width=1)
# Gentle wrapping crossfade only at the very edges, protects repeating sampling.
a=np.asarray(tex,float).copy()
for dim in [0,1]:
 if dim:a=np.swapaxes(a,0,1)
 b=a.copy();w=28
 for j in range(w):
  t=(w-j)/w*.5;avg=(b[j]+b[-j-1])*.5
  a[j]=b[j]*(1-t)+avg*t;a[-j-1]=b[-j-1]*(1-t)+avg*t
 a[0]=a[-1]=(a[0]+a[-1])*.5
 if dim:a=np.swapaxes(a,0,1)
Image.fromarray(np.uint8(np.clip(a,0,255))).save(ROOT/'assets/forest_floor_basecolor.jpg',quality=94,subsampling=0)
meta=json.loads((ROOT/'assets/forest_floor_provenance.json').read_text());meta['processing']+='; broad procedural moss/loam control layer to suppress perspective plants; sparse leaf-litter embellishment'
(ROOT/'assets/forest_floor_provenance.json').write_text(json.dumps(meta,indent=2))
print('Generated-image detail retained under simplified moss/loam control layer')
