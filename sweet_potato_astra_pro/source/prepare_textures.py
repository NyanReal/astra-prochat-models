"""Prepare textures from NEW image-generated reference crops (no prior assets)."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageEnhance
from scipy import ndimage
import cv2
ROOT=Path(__file__).resolve().parents[1]

def main():
    raw=Image.open(ROOT/'reference'/'generated_leaf_source.png').convert('RGB')
    a=np.array(raw)
    mask=(a[:,:,1]>a[:,:,0]*1.01)&(a[:,:,1]>a[:,:,2]*1.5)&(a[:,:,1]>50)
    labels,num=ndimage.label(mask)
    counts=np.bincount(labels.ravel()); counts[0]=0
    mask=labels==counts.argmax()
    mask=ndimage.binary_fill_holes(ndimage.binary_closing(mask,iterations=1))
    y,x=np.where(mask); box=(max(0,x.min()-7),max(0,y.min()-7),min(a.shape[1],x.max()+8),min(a.shape[0],y.max()+8))
    a=a[box[1]:box[3],box[0]:box[2]]
    mask=mask[box[1]:box[3],box[0]:box[2]]
    # Padding is filled with the closest leaf color: no white halo or alpha sorting.
    valid=ndimage.binary_erosion(mask & (a[:,:,0]<220) & (a[:,:,2]<a[:,:,1]*.75),iterations=1)
    nearest=ndimage.distance_transform_edt(~valid,return_distances=False,return_indices=True)
    ext=a[nearest[0],nearest[1]]
    rgb=np.asarray(Image.fromarray(ext).resize((512,512),Image.Resampling.LANCZOS),dtype=float)
    m=np.asarray(Image.fromarray((mask*255).astype('uint8')).resize((512,512),Image.Resampling.LANCZOS))>160
    atlas=Image.new('RGB',(1024,1024))
    variants=[((.88,.96,1.06),(8,5,12)),((1.04,1.05,.95),(8,8,18)),((.73,.87,1.20),(8,6,13)),((1.05,.98,1.05),(10,7,15))]
    for k,(factor,offset) in enumerate(variants):
        out=np.clip(rgb*np.array(factor)+np.array(offset),0,255).astype('uint8')
        atlas.paste(Image.fromarray(out),((k%2)*512,(k//2)*512))
    atlas.save(ROOT/'textures'/'foliage_basecolor_1024.png')
    Image.fromarray((m*255).astype('uint8')).save(ROOT/'source'/'leaf_silhouette_mask.png')
    contour=cv2.findContours(m.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)[0]
    c=max(contour,key=cv2.contourArea)[:,0,:].astype(float)/511.
    # Store only shape data; used directly to derive lamina geometry and exact UVs.
    np.save(ROOT/'source'/'leaf_boundary.npy',c)
    im=Image.open(ROOT/'reference'/'reference_selected.png').convert('RGB')
    crop=im.crop((500,300,565,360)).resize((128,128),Image.Resampling.LANCZOS)
    tile=Image.new('RGB',(256,256)); tile.paste(crop,(0,0));tile.paste(crop.transpose(Image.Transpose.FLIP_LEFT_RIGHT),(128,0));tile.paste(crop.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(0,128));tile.paste(crop.transpose(Image.Transpose.ROTATE_180),(128,128))
    tile=ImageEnhance.Color(tile).enhance(.82)
    tile=ImageEnhance.Brightness(tile).enhance(.88)
    tile.save(ROOT/'textures'/'soil_basecolor_256.png')
    stone=np.asarray(tile.resize((128,128)),dtype=float)*np.array([.92,1.02,1.15])+np.array([17,18,18])
    Image.fromarray(np.clip(stone,0,255).astype('uint8')).save(ROOT/'textures'/'stone_basecolor_128.png')
    # Image-derived low-detail gradient strips; stems need little texel density.
    a=np.array(atlas.crop((100,100,180,450)).resize((32,128)),dtype=float)
    stem=np.zeros((128,128,3))
    lum=np.mean(a,axis=2); lum=lum/np.mean(lum)
    colors=[(125,85,55),(115,137,54),(144,94,64),(145,161,67)]
    for k,color in enumerate(colors): stem[:,k*32:(k+1)*32]=lum[:,:,None]*np.array(color)
    Image.fromarray(np.clip(stem,0,255).astype('uint8')).save(ROOT/'textures'/'stem_basecolor_128.png')
    (ROOT/'source'/'texture_provenance.json').write_text(json.dumps({
      'all_source_images':'Generated afresh in this rebuild; previous asset pack was not used.',
      'leaf_source_crop_on_new_board':[1519,61,1650,192],
      'soil_crop_on_selected_reference':[500,300,565,360],
      'processing':['crop','green silhouette extraction','nearest-edge RGB dilation','resample','color variants','mirrored soil tiling'],
      'note':'1024 is the final atlas size, not the native resolution of each source crop. Textures are image-derived, not independently generated 1024-pixel leaves.'
    },ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
