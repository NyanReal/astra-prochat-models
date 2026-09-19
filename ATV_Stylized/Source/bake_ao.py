"""Optional deterministic geometric AO bake into ORM.R, not a texture pattern.
Dependencies: NumPy, Pillow, SciPy, Numba. Uses delivered Source/mesh_data.npz.
1024-square geometric sampling, resampled into the final 2048-square ORM map.
"""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from numba import njit,prange
import reference_renderer as rr
ROOT=Path(__file__).resolve().parents[1]

@njit(parallel=True)
def bake(pos,nor,valid,lo,hi,left,right,start,count,t0,e1,e2,samples):
 h,w=valid.shape;out=np.ones((h,w),np.float64)
 for y in prange(h):
  for x in range(w):
   if not valid[y,x]:continue
   n=nor[y,x];o=pos[y,x]+n*.003
   if abs(n[2])<.95:u=np.array([-n[1],n[0],0.]);u/=max(np.linalg.norm(u),1e-12)
   else:u=np.array([1.,0.,0.])
   v=np.cross(n,u);occ=0.
   phase=((x*1973+y*9277)%1009)/1009*6.283185
   for s in range(samples):
    q=(s+.5)/samples;theta=s*2.39996323+phase
    d=(u*math.cos(theta)+v*math.sin(theta))*math.sqrt(q)+n*math.sqrt(1-q)
    if rr.blocked(o,d,.38,lo,hi,left,right,start,count,t0,e1,e2):occ+=1
   out[y,x]=1-.72*occ/samples
 return out


def main():
 size=1024;samples=24
 pos=np.zeros((size,size,3));nor=pos.copy();col=pos.copy();rough=pos.copy();z=np.full((size,size),-1e6)
 proj=np.column_stack((rr.UV[:,0]*size,(1-rr.UV[:,1])*size,np.zeros(len(rr.UV))))
 tex=np.array(Image.open(ROOT/'Textures/T_ATV_BaseColor.png').convert('RGB')).astype(float)
 orm=np.array(Image.open(ROOT/'Textures/T_ATV_ORM.png').convert('RGB'))
 rr.raster(rr.V,rr.F,rr.N,rr.UV,proj,tex,orm.astype(float),pos,nor,col,rough,z)
 valid=z>-1e5
 ao=bake(pos,nor,valid,rr.LO,rr.HI,rr.LEFT,rr.RIGHT,rr.START,rr.COUNT,rr.T0,rr.E1,rr.E2,samples)
 near=ndi.distance_transform_edt(~valid,return_distances=False,return_indices=True)
 ao=ao[tuple(near)]
 # Mild anti-noise reconstruction. No color information is synthesized here.
 ao=ndi.gaussian_filter(ao,.40)
 image=Image.fromarray(np.clip(ao*255,0,255).astype(np.uint8)).resize((2048,2048),Image.Resampling.BILINEAR)
 orm[:,:,0]=np.array(image);Image.fromarray(orm).save(ROOT/'Textures/T_ATV_ORM.png')
 image.save(ROOT/'Textures/T_ATV_AO.png')
 (ROOT/'Validation/AO_Bake.json').write_text(json.dumps({'method':'mesh ray-traced hemisphere occlusion','ray_distance_metres':.38,'sample_resolution':size,'output_resolution':2048,'rays_per_sample':samples,'valid_samples':int(valid.sum()),'periodic_noise_texture':False},indent=2))
 print('AO complete:',int(valid.sum()),'samples',flush=True)

if __name__=='__main__':main()
