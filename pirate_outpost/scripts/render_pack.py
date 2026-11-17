"""Render actual exported GLBs: thumbnails, asset sheets and assembled scenes.
Not required by the Blender or Unreal scripts. Dependencies: numpy, vtk, Pillow.
"""
from pathlib import Path
import argparse, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from render_preview import ROOT, setup, texture, mesh_actor, make_floor, save_render


def frame_actor(renderer, actor, width, height, azimuth=-48, elevation=24, padding=1.15):
    bounds=np.array(actor.GetBounds()).reshape(3,2)
    mn,mx=bounds[:,0],bounds[:,1];center=(mn+mx)/2;size=max(mx-mn)
    az,el=math.radians(azimuth),math.radians(elevation)
    direction=np.array([math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)])
    right=np.cross(direction,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,direction)
    corners=np.array([[x,y,z] for x in [mn[0],mx[0]] for y in [mn[1],mx[1]] for z in [mn[2],mx[2]]])-center
    cam=renderer.GetActiveCamera();cam.SetFocalPoint(*center);cam.SetPosition(*(center+direction*max(size*3,3)));cam.SetViewUp(0,0,1);cam.ParallelProjectionOn()
    cam.SetParallelScale(max(np.ptp(corners@up)/2,np.ptp(corners@right)/(2*width/height))*padding)
    renderer.ResetCameraClippingRange()
    return mn,size


def thumbnails(start=0,end=None,size=640):
    assets=json.loads((ROOT/'asset_manifest.json').read_text())['assets'][start:end]
    out=ROOT/'previews/thumbnails';out.mkdir(parents=True,exist_ok=True)
    r,w,ss=setup(size,size);tx={'base':texture(ROOT/'textures/T_Pirate_BaseColor.png')}
    for a in assets:
        r.RemoveAllViewProps();actor=mesh_actor(ROOT/a['file'],textures=tx);r.AddActor(actor)
        mn,sz=frame_actor(r,actor,size,size)
        r.AddActor(make_floor(mn[2]-.018,max(sz*10,10)));ss.SetRadius(min(.4,sz*.12));r.ResetCameraClippingRange()
        save_render(w,out/(a['id']+'.png'));print('rendered',a['id'],flush=True)
    w.Finalize()


def scene(layout='harbor',output=None,width=2400,height=1800,angle='front'):
    data=json.loads((ROOT/'layout'/f'{layout}_layout.json').read_text())
    r,w,ss=setup(width,height);tx={'base':texture(ROOT/'textures/T_Pirate_BaseColor.png')}
    for o in data['instances']:
        r.AddActor(mesh_actor(ROOT/'models'/f"{o['asset']}.glb",o['position_m'],o['yaw_degrees'],o['scale'],tx))
    for o in data.get('environment',[]):
        r.AddActor(mesh_actor(ROOT/o['file'],o['position_m'],o['yaw_degrees'],o['scale'],tx))
    cam=r.GetActiveCamera();camera=data.get('camera',{})
    if layout=='harbor':
        if angle=='front': pos=(26,-36,30);target=(0,1,1.6);span=17.4
        elif angle=='back': pos=(-27,34,28);target=(0,2.0,1.6);span=17.4
        elif angle=='dock': pos=(16,-26,15);target=(1,-8,1.0);span=9.5
        else: pos=(0,-1,55);target=(0,1,0);span=19
    else:
        pos=camera['position_m'];target=camera['target_m'];span=camera['orthographic_scale']/2
        r.AddActor(make_floor(-2.2,200))
    cam.SetPosition(*pos);cam.SetFocalPoint(*target);cam.SetViewUp(0,0,1);cam.ParallelProjectionOn();cam.SetParallelScale(span)
    ss.SetRadius(.42);r.ResetCameraClippingRange();output=Path(output or ROOT/'previews'/f'{layout}_{angle}.png');save_render(w,output);w.Finalize()


def sheets():
    assets=json.loads((ROOT/'asset_manifest.json').read_text())['assets']
    fp='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    fb='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    def font(size,bold=False):return ImageFont.truetype(fb if bold else fp,size)
    groups={'01_Structures':['Structures'],'02_Harbor':['Harbor'],'03_Defense':['Defense'],'04_Storage_Camp':['Storage','Camp'],'05_Props_Nature':['Dressing','Environment']}
    for label,categories in groups.items():
        selected=[a for a in assets if a['category'] in categories];cols=4 if len(selected)>8 else 3;rows=math.ceil(len(selected)/cols)
        tilew,tileh=430,450;header=130
        sheet=Image.new('RGB',(cols*tilew,header+rows*tileh),(247,242,231));d=ImageDraw.Draw(sheet)
        title=label.split('_',1)[1].replace('_',' + ').upper();d.text((28,22),'PIRATE OUTPOST / '+title,font=font(32,True),fill=(57,52,43))
        d.text((28,75),f'{len(selected)} individual GLBs  |  Actual exported geometry  |  Thumbnail scales vary',font=font(19),fill=(100,91,74))
        for i,a in enumerate(selected):
            x=(i%cols)*tilew;y=header+(i//cols)*tileh
            im=Image.open(ROOT/'previews/thumbnails'/(a['id']+'.png')).convert('RGB');im=im.resize((410,375),Image.Resampling.LANCZOS)
            sheet.paste(im,(x+10,y));d.text((x+18,y+380),a['id'].removeprefix('SM_'),font=font(20,True),fill=(57,52,43))
            d.text((x+18,y+412),f"{a['triangles']:,} triangles",font=font(17),fill=(107,97,77))
        sheet.save(ROOT/'previews'/(label+'.jpg'),quality=94)
    # Compact overview sheet of all models, directly from the exported assets.
    cols=8;rows=math.ceil(len(assets)/cols);tw,th=270,293
    sheet=Image.new('RGB',(cols*tw,rows*th+125),(247,242,231));d=ImageDraw.Draw(sheet)
    d.text((25,20),'PIRATE OUTPOST / 66 INDIVIDUAL GAME ASSETS',font=font(35,True),fill=(57,52,43))
    d.text((25,75),'Actual GLB geometry renders  |  One shared 1024px material atlas  |  Thumbnail scales vary',font=font(22),fill=(100,91,74))
    for i,a in enumerate(assets):
        x=(i%cols)*tw;y=125+(i//cols)*th
        im=Image.open(ROOT/'previews/thumbnails'/(a['id']+'.png')).convert('RGB').resize((262,250),Image.Resampling.LANCZOS);sheet.paste(im,(x+4,y))
        d.text((x+9,y+253),a['id'].removeprefix('SM_'),font=font(15,True),fill=(57,52,43))
        d.text((x+9,y+275),f"{a['triangles']:,} tris",font=font(13),fill=(100,91,74))
    sheet.save(ROOT/'previews/All_66_Assets.jpg',quality=94)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['thumbnails','scene','sheets']);ap.add_argument('--start',type=int,default=0);ap.add_argument('--end',type=int);ap.add_argument('--size',type=int,default=640);ap.add_argument('--layout',default='harbor');ap.add_argument('--angle',default='front');a=ap.parse_args()
    if a.mode=='thumbnails':thumbnails(a.start,a.end,a.size)
    elif a.mode=='scene':scene(a.layout,angle=a.angle)
    else:sheets()
