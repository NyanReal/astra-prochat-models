"""Reproject the delivered image-generated artwork into the exact unique UV atlas.
This is image resampling/masking/color correction, NOT a tiling/noise material.
Dependencies for this optional source step: numpy, Pillow, scipy.
The Blender build uses the completed PNG maps and does not need SciPy/Pillow.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1]
S=np.array(Image.open(ROOT/'Source/AI_Painted_Source.png').convert('RGB'))
s=S.astype(int);r,g,b=s.transpose(2,0,1)
COLOR_MASKS={
 'teal':(g-r>7)&(b-r>5)&(g>55)&(g<210),
 'cream':(r>135)&(g>125)&(b>70)&(r-b>18)&(r-g<48)&(g-b>8),
 'gray':(s.max(2)-s.min(2)<17)&(r>39)&(r<154),
 'orange':(r>125)&(r-g>40)&(g-b>25),
}

def components(mask):
 labels,n=ndi.label(mask);out=[]
 for i,sl in enumerate(ndi.find_objects(labels)):
  cm=labels[sl]==i+1;area=int(cm.sum())
  if area<55:continue
  # Preserve enclosed painted details, e.g. tan stitching in the dark seat.
  cm=ndi.binary_fill_holes(cm)
  out.append({'area':area,'bbox':(sl[1].start,sl[0].start,sl[1].stop,sl[0].stop),'mask':cm,'image':S[sl].copy()})
 return sorted(out,key=lambda c:-c['area'])

COMP={k:components(v) for k,v in COLOR_MASKS.items()}

def fill_piece(piece):
 im=piece['image'];mask=piece['mask']
 if not mask.any():return im.copy()
 idx=ndi.distance_transform_edt(~mask,return_distances=False,return_indices=True)
 return im[tuple(idx)]

def dense_piece(piece):
 """Flatten the painted silhouette to a rectangle, without copying edge pixels into the interior."""
 im=fill_piece(piece);mask=piece['mask'];h,w=mask.shape
 out=np.empty_like(im)
 for y in range(h):
  valid=np.where(mask[y])[0]
  if len(valid)<2:
   vy=np.where(mask.any(1))[0];row=vy[np.argmin(abs(vy-y))];valid=np.where(mask[row])[0]
  x=np.linspace(valid[0],valid[-1],w)
  for c in range(3):out[y,:,c]=np.interp(x,np.arange(w),im[y,:,c])
 return out


def source_rect(bbox,kind=None):
 x0,y0,x1,y1=bbox;im=S[y0:y1,x0:x1].copy()
 mask=np.ones(im.shape[:2],bool) if kind is None else COLOR_MASKS[kind][y0:y1,x0:x1]
 if kind is not None:mask=ndi.binary_fill_holes(mask)
 return {'image':im,'mask':mask,'bbox':bbox,'area':int(mask.sum())}


def resized(patch,w,h):return np.array(Image.fromarray(patch).resize((w,h),Image.Resampling.BICUBIC))

def warp_to_silhouette(dense,target):
 h,w=target.shape;src=resized(dense,w,h);out=src.copy();ys=np.where(target.any(1))[0]
 if not len(ys):return out
 for y in ys:
  xs=np.where(target[y])[0]
  sy=int(np.clip((y-ys[0])/max(ys[-1]-ys[0],1)*(h-1),0,h-1))
  row=src[sy]
  u=np.linspace(0,w-1,len(xs))
  for c in range(3):out[y,xs,c]=np.interp(u,np.arange(w),row[:,c])
 return out


def make_pools(kind,skip=0):
 # Each crop in this pool is consumed ONCE. No repeated UV swatches/patterns.
 out=[]
 comps=COMP[kind][skip:]
 for i,comp in enumerate(comps):
  dense=dense_piece(comp);h,w=dense.shape[:2]
  # More, smaller unique source crops for the many tiny structural surfaces.
  nx=2 if w>=42 else 1;ny=2 if h>=42 else 1
  for yy in range(ny):
   for xx in range(nx):
    y0=yy*h//ny;y1=(yy+1)*h//ny;x0=xx*w//nx;x1=(xx+1)*w//nx
    if min(x1-x0,y1-y0)<3:continue
    out.append({'patch':dense[y0:y1,x0:x1], 'source_bbox':comp['bbox'],'subcrop':[x0,y0,x1,y1],'source_kind':kind})
 return sorted(out,key=lambda p:-p['patch'].shape[0]*p['patch'].shape[1])


def main():
 from atv_geometry import PALETTE
 charts=json.loads((ROOT/'Source/UV_Charts.json').read_text());ids=np.array(Image.open(ROOT/'Source/UV_Chart_IDs.tiff'));size=ids.shape[0]
 base=np.full((size,size,3),[31,34,34],dtype=np.uint8);orm=np.array(Image.open(ROOT/'Textures/T_ATV_ORM.png'))
 pools={'gray':make_pools('gray',2),'cream':make_pools('cream'),'teal':make_pools('teal',4),'orange':make_pools('orange')}
 counters={k:0 for k in pools};provenance=[]
 fenderindex=0
 # Largest surface charts get first choice of large source crops.
 ordered=sorted(charts,key=lambda c: -(c['rectangle'][2]*c['rectangle'][3]))
 for c in ordered:
  cid=c['id'];name=c['name'];mat=c['material'];x,y,w,h,rot=c['rectangle'];mask=ids[y:y+h,x:x+w]==cid
  if not mask.any():continue
  specific=None;feature=False;info={}
  if name.startswith('Fender_') and name.endswith('_continuous'):
   comp=COMP['teal'][fenderindex];fenderindex+=1;specific=dense_piece(comp);info={'source_bbox':comp['bbox'],'method':'single painted fender flatten'}
  elif name=='Seat_Saddle_panel_31':
   comp=COMP['gray'][0];specific=dense_piece(comp);feature=True;info={'source_bbox':comp['bbox'],'method':'stitched seat silhouette warp'}
  elif name=='Seat_Saddle_unwrap':
   comp=COMP['gray'][1];specific=dense_piece(comp);info={'source_bbox':comp['bbox'],'method':'separate seat underside artwork'}
  elif 'Headlight_' in name and '_Lens_' in name:
   bbox=(610,959,700,1050) if '_R_' in name else (748,959,838,1050)
   specific=dense_piece(source_rect(bbox));feature=True;info={'source_bbox':bbox,'method':'generated lamp lens'}
  elif name=='Front_Grille_panel_1':
   bbox=(1137,1004,1227,1037);specific=dense_piece(source_rect(bbox));feature=True;info={'source_bbox':bbox,'method':'generated inset grille'}
  elif name=='Console_Rear_Display_panel_0':
   bbox=(647,270,732,318);specific=dense_piece(source_rect(bbox));feature=True;info={'source_bbox':bbox,'method':'generated dark dashboard'}
  elif name in ['Rear_Amber_Lens_L_panel_0','Rear_Amber_Lens_R_panel_0']:
   bbox=(1126,1068,1195,1128) if '_L_' in name else (915,1068,982,1128)
   specific=dense_piece(source_rect(bbox,'orange'));feature=True;info={'source_bbox':bbox,'method':'generated amber lens'}
  if specific is None:
   kind='teal' if mat=='teal' else 'cream' if mat in ['cream','rim','lamp'] else 'orange' if mat=='orange' else 'gray'
   i=counters[kind];counters[kind]+=1
   if i>=len(pools[kind]):raise RuntimeError(f'Not enough distinct generated source crops: {kind}')
   p=pools[kind][i];specific=p['patch'];info={k:v for k,v in p.items() if k!='patch'};info['method']='unique nonrepeating source crop'
  patch=warp_to_silhouette(specific,mask) if feature else resized(specific,w,h)
  source_float=patch.astype(np.float32);median=np.median(source_float[mask],axis=0)
  target=np.array(PALETTE[mat][0],np.float32)
  contrast= .92 if feature else .78 if mat=='teal' else .63 if mat in ['cream','rim','seat','orange'] else .32 if mat in ['rubber','tread'] else .48
  ratio=(source_float-np.maximum(median,1))/np.maximum(median,32)
  ratio=np.clip(ratio,-.72,.7)
  corrected=np.clip(target*(1+contrast*ratio),0,255)
  base[y:y+h,x:x+w][mask]=corrected[mask].astype(np.uint8)
  # A small roughness response comes from the generated paint's luminance.
  variation=np.mean(ratio,axis=2)
  rough=np.clip(round(PALETTE[mat][1]*255)-variation*12,10,250).astype(np.uint8)
  orm[y:y+h,x:x+w,1][mask]=rough[mask]
  provenance.append({'chart_id':cid,'chart':name,**info})
 # Bleed texels into padding without altering island interiors. No tiling sampler.
 mask=ids>0;near=ndi.distance_transform_edt(~mask,return_distances=False,return_indices=True)
 base=base[tuple(near)];orm=orm[tuple(near)]
 em=np.zeros_like(base)
 for c in charts:
  mask=ids==c['id']
  if c['material']=='lamp':em[mask]=base[mask]
  elif c['material']=='screen':em[mask]=np.clip(base[mask].astype(float)*.035,0,255)
 em=em[tuple(near)]
 Image.fromarray(base).save(ROOT/'Textures/T_ATV_BaseColor.png');Image.fromarray(orm).save(ROOT/'Textures/T_ATV_ORM.png');Image.fromarray(em).save(ROOT/'Textures/T_ATV_Emissive.png')
 (ROOT/'Source/Paint_Projection.json').write_text(json.dumps({'source':'AI_Painted_Source.png','source_resolution':list(S.shape[:2][::-1]),'atlas_resolution':[size,size],'uv_tiling':False,'mirrored_uv':False,'charts':sorted(provenance,key=lambda p:p['chart_id'])},indent=2),encoding='utf8')
 print('Image-generated painting projected:',len(provenance),'unique UV charts. Crop use:',counters)

if __name__=='__main__':main()
