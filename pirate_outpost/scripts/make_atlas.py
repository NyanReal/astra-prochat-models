"""Create 1024px material atlases from the two supplied generated reference images.
No texture is fetched from an external asset library. See provenance JSON.
"""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image, ImageFilter, ImageOps
ROOT=Path(__file__).resolve().parents[1]
S=1024
REGIONS={
 'wood':(0,0,256,384), 'wood_dark':(256,0,384,384),
 'wood_pale':(384,0,512,384), 'wood_red':(512,0,640,384), 'wood_teal':(640,0,768,384),
 'canvas':(768,0,1024,256),'cloth_red':(768,256,896,384),'cloth_dark':(896,256,1024,384),
 'flag_dark':(0,384,256,640),'flag_cream':(256,384,512,640),
 'metal':(512,384,640,512),'gold':(640,384,768,512),
 'rope':(512,512,640,768),'stone':(640,512,768,768),
 'endgrain':(0,640,256,896),'leather':(256,640,384,768),'glass':(384,640,512,768),
 'water':(0,896,256,1024),'leaf':(256,768,512,1024),
}
# Small gradient regions are used by visually simple surfaces; most UV area is reserved for wood and insignia.
small=['bone','black','white','red','amber','yellow','grass','moss','sand','bread','fish','silver',
       'orange','stone_dark','coal','teal','wood_light','leaf_light','ceramic','green_glass']
for k,n in enumerate(small):
 x=768+(k%4)*64; y=384+(k//4)*128
 REGIONS[n]=(x,y,x+64,y+128)

SOURCES={
 'wood':('reference_02.png',(1301,912,1351,999)),
 'rope':('reference_02.png',(1366,915,1412,999)),
 'metal':('reference_02.png',(1428,918,1470,998)),
 'canvas':('reference_01.png',(1225,184,1262,231)),
 'stone':('reference_01.png',(312,743,354,775)),
 'skull':('reference_01.png',(1316,158,1397,218)),
 'leaf':('reference_02.png',(883,902,911,942)),
}

def patch(key,size,target,contrast=.38):
 file,bbox=SOURCES[key]
 im=Image.open(ROOT/'references'/file).convert('RGB').crop(bbox)
 if key=='wood':
  # Remove dark plank-boundary pixels from the source swatch before sampling it on solid beams.
  # These are image-space seams, not timber grain, and would incorrectly repeat around logs.
  import cv2
  src=np.array(im); l=src.mean(2); seam=(l<np.median(l)*.66).astype('uint8')*255
  seam=cv2.dilate(seam,np.ones((3,3),np.uint8),iterations=1)
  im=Image.fromarray(cv2.inpaint(src,seam,3,cv2.INPAINT_TELEA))
  # Rotate the diagonal swatch grain toward the long plank direction; crop away rotated corners.
  im=im.resize((160,256),Image.Resampling.LANCZOS).rotate(-31,resample=Image.Resampling.BICUBIC,expand=True)
  w,h=im.size; im=im.crop((w//2-40,h//2-76,w//2+40,h//2+76))
 im=im.resize(size,Image.Resampling.LANCZOS)
 a=np.asarray(im,dtype=float)
 # Neutralise the source render's low-frequency lighting while retaining painted grain.
 blur=np.asarray(im.filter(ImageFilter.GaussianBlur(max(size)/12)),dtype=float)
 lum=a.mean(2); bl=blur.mean(2)
 detail=(lum-bl)*contrast + (bl-bl.mean())*.12
 if key=='wood':detail=np.clip(detail,-18,18)
 target=np.asarray(target,float)
 out=np.clip(target[None,None,:]+detail[:,:,None],0,255).astype('uint8')
 return Image.fromarray(out)

def main():
 atlas=Image.new('RGB',(S,S),(110,76,50)); mr=Image.new('RGB',(S,S),(255,225,0))
 cfg={
  'wood':('wood',(164,104,61),.65,.84,0),
  'wood_dark':('wood',(102,65,42),.55,.9,0),
  'wood_pale':('wood',(191,144,91),.6,.86,0),
  'wood_red':('wood',(157,68,49),.6,.88,0),
  'wood_teal':('wood',(78,122,116),.6,.9,0),
  'canvas':('canvas',(222,198,155),.6,.96,0),
  'cloth_red':('canvas',(176,67,46),.65,.97,0),
  'cloth_dark':('canvas',(49,49,45),.6,.94,0),
  'flag_dark':('canvas',(43,45,43),.6,.95,0),
  'flag_cream':('canvas',(224,202,161),.6,.96,0),
  'metal':('metal',(86,88,90),.4,.58,.78),
  'gold':('metal',(201,146,62),.4,.42,.8),
  'rope':('rope',(190,151,98),.6,.98,0),
  'stone':('stone',(151,146,128),.45,.97,0),
  'endgrain':('wood',(158,110,69),.5,.9,0),
  'leather':('canvas',(111,63,36),.4,.85,0),
  'glass':('canvas',(239,175,61),.25,.25,0),
  'water':('canvas',(46,131,142),.2,.33,0),
  'leaf':('leaf',(80,123,56),.4,.92,0),
 }
 colors=[(223,210,173),(34,32,31),(233,225,205),(182,60,44),(247,139,35),(255,208,73),
  (91,129,61),(102,119,68),(192,166,117),(193,127,58),(78,123,144),(146,164,162),
  (211,107,43),(103,106,100),(48,43,39),(65,118,112),(186,128,77),(126,156,65),
  (207,184,142),(58,103,69)]
 for n,c in zip(small,colors): cfg[n]=('canvas',c,.25,.9,0)
 cfg['silver']=('metal',colors[11],.3,.48,.7)
 cfg['green_glass']=('canvas',colors[-1],.22,.28,0)
 for n,rect in REGIONS.items():
  x,y,x1,y1=rect; key,c,contrast,rough,met=cfg[n]
  tile=patch(key,(x1-x,y1-y),c,contrast)
  if n=='endgrain':
   # Use the generated source's timber texture; no procedural wood shader required.
   tile=tile.rotate(90)
  atlas.paste(tile,(x,y))
  mr.paste((255,int(255*rough),int(255*met)),rect)
 # Extract, clean, and upscale the generated emblem. The empty eye sockets are preserved.
 file,bb=SOURCES['skull']; logo=Image.open(ROOT/'references'/file).convert('RGB').crop(bb)
 a=np.asarray(logo,float); lum=a.mean(2)
 mask=np.clip((153-lum)/32,0,1)
 mask=Image.fromarray((mask*255).astype('uint8')).resize((190,140),Image.Resampling.LANCZOS)
 for region,color in [('flag_dark',(232,220,188)),('flag_cream',(66,55,45))]:
  x,y,x1,y1=REGIONS[region]
  atlas.paste(Image.new('RGB',mask.size,color),(x+33,y+55),mask)
 out=ROOT/'textures';out.mkdir(exist_ok=True)
 atlas.save(out/'T_Pirate_BaseColor.png',optimize=True)
 mr.save(out/'T_Pirate_RoughMetal.png',optimize=True)
 (out/'atlas_regions.json').write_text(json.dumps(REGIONS,indent=2))
 prov={'method':'Material pixels extracted and colour-corrected from user-approved generated reference sheets; skull emblem extracted from reference_01.',
  'source_crops':{k:{'file':'references/'+f,'pixel_box_xyxy':b} for k,(f,b) in SOURCES.items()},
  'source_sha256':{f:hashlib.sha256((ROOT/'references'/f).read_bytes()).hexdigest() for f in ['reference_01.png','reference_02.png']},
  'base_color':'sRGB', 'rough_metal':'linear; R=1, G=roughness, B=metallic',
  'normal_map':None, 'uv_note':'Overlapping trim/atlas UVs; not unique lightmap UVs.'}
 (out/'provenance.json').write_text(json.dumps(prov,indent=2))
 print('Atlas generated:',atlas.size,'regions:',len(REGIONS))
if __name__=='__main__': main()
