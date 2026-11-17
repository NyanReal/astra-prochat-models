"""A single layout manifest feeds Blender, Unreal and the local geometry renderer."""
import json,math
from pathlib import Path
import numpy as np
from meshcore import Builder,ROOT,write_glb,trans


def main():
 instances=[];counts={}
 def put(id,x,y,z=0,yaw=0,s=1):
  id='SM_'+id;counts[id]=counts.get(id,0)+1
  instances.append({'name':f'{id}__{counts[id]:03d}','asset':id,'position_m':[x,y,z],'yaw_degrees':yaw,'scale':[s,s,s]})
 put('CommandHut',0,8.5)
 put('Forge',-6,6.1)
 put('SupplyShed',7,2.6)
 put('PirateTent',-6,11.3,yaw=-12)
 put('PirateTent',7,11,yaw=15)
 put('RestCanopy',5.7,7.5)
 put('Table',5.7,7.5);put('Bench',5.7,6.72);put('Bench',5.7,8.28)
 put('Watchtower',-8.6,-.6)
 put('StoneGate_Open',0,-3)
 for x in [-10,-8,-6,-4,4,6,8,10]:put('Palisade',x,-3.15)
 for x in range(-10,11,2):put('Palisade',x,13.2,yaw=180)
 for x in [-11,11]:
  for y in [-1,1,3,5,7,9,11]:put('Palisade',x,y,yaw=90 if x<0 else -90)
 put('Cannon',7.2,-1.3,yaw=12);put('Cannon',9.2,-1.2,yaw=-9)
 put('Barricade',-5,-4.8);put('Barricade',4,-4.6,yaw=8)
 put('CookingStation',-3.3,3.4);put('FishRack',-5.25,3.1,yaw=6)
 put('WeaponRack',4.1,.3,yaw=-12);put('Target',-6.2,1.6,yaw=12)
 put('Stocks',-5.8,-1.2,yaw=3);put('Cage',9.1,5.2)
 put('SupplyShelf',7,3.48);put('StorageShelf_Empty',8.02,2.6,yaw=90)
 for id,x,y,z,ang in [
  ('Crate_Large',6.1,2.7,0,5),('Crate_Small',6.08,2.73,.87,-7),('Barrel_Large',5.8,1.4,0,0),('Sack',7.7,1.1,0,0),
  ('Barrel_Small',9.3,1.4,0,0),('Crate_Large',-2.2,7.4,0,0),('Sack',-2.5,6.2,0,8),('Barrel_Large',2.7,7.1,0,0),
  ('Barrel_Small',2.9,6.15,0,0),('TreasureChest_Open',.7,5.6,0,-7),('TreasureChest_Closed',1.95,5.7,0,5),
  ('Crate_Small',-4.5,10.3,0,16),('Sack',5.4,10.1,0,0),('Anvil',-7.5,4.4,0,-10)]:put(id,x,y,z,yaw=ang)
 for id,x,y in [('Torch_Tripod',-2.4,-1),('Torch_Tripod',2.5,-1),('Torch',-3.5,6.4),('Torch',3.5,6.4)]:put(id,x,y)
 put('Flag_Pirate',3.1,10.5,yaw=-8);put('Flag_Red',10,8.7,yaw=15)
 put('Skull',-5.8,-1.4,1.83);put('Chain',9.2,4.6,yaw=10)
 # Continuous, socket-aligned dock. All pier tops lie on z=.2 metres.
 for y in [-5,-7]:put('Dock_Straight',0,y,.2)
 put('Dock_T',0,-9,.2)
 put('Dock_Straight',-2,-9,.2,yaw=90)
 put('Dock_End',-4,-9,.2,yaw=-90)
 put('Dock_Straight',2,-9,.2,yaw=90)
 put('Dock_Platform',5,-9,.2)
 put('Gangway',5,-12,-.08)
 put('FloatingPlatform',5,-14.025,-.91)
 put('Dock_Stairs',7,-9,.2,yaw=90)
 put('SmallSailboat',-6.1,-9.8,-.62)
 put('LoadingCrane',4.8,-8.5,.2)
 put('CargoNet',6.71,-8.5,.55)
 put('Winch',3.8,-10,.2,yaw=0)
 for x,y in [(-4.4,-8.5),(-2.6,-9.7),(6.5,-10.6),(3.4,-7.5)]:put('Bollard',x,y,.2)
 for id,x,y,z,ang in [
  ('Crate_Large',3.8,-8,.2,0),('Crate_Small',3.8,-8,1.06,12),('Barrel_Large',5.7,-7.7,.2,0),('Barrel_Small',6.4,-7.7,.2,0),
  ('Sack',5.6,-10,.2,0),('CargoNet',-.5,-4.4,.2,0),('RopeCoil',-4,-9.3,.2,0),('RopeCoil',6.4,-10,.2,5),
  ('Anchor',-3.5,-8.7,.2,0),('Lifebuoy',-2.8,-9.8,.2,0),('Lantern',3.6,-7.4,.2,0),('Helm',1.5,-4,0,20)]:put(id,x,y,z,yaw=ang)
 put('BoneRibs',-11.9,-4.9,yaw=45,s=.8)
 put('Skull',-11.2,-5.7,s=1.3)
 for x,y,ang,s in [(-13,-.3,15,1.12),(12.6,3.4,3,1.12),(11.5,15,60,1.18),(-12.7,12,-20,1.1),(-12,7,35,.85)]:put('Palm',x,y,yaw=ang,s=s)
 for x,y,ang,s in [(-12,-4.3,25,1.35),(-10.8,-5.4,10,.8),(11.6,-4.2,65,1.2),(12.7,-2.9,22,.8),(12.4,12.8,15,1.4),(-12.5,13,5,1.1),(-13,7,20,.8)]:put('RockCluster',x,y,yaw=ang,s=s)
 rng=np.random.default_rng(12)
 for i in range(24):
  side=-1 if i%2 else 1;x=side*rng.uniform(11.5,13.2);y=rng.uniform(-2.5,13.7)
  put('Grass',round(x,3),round(y,3),yaw=round(float(rng.uniform(0,360)),2),s=round(float(rng.uniform(.8,1.5)),2))
 # Render-only environment; kept outside models/ and not counted as a gameplay prop.
 env=ROOT/'previews'/'environment';env.mkdir(exist_ok=True)
 ground=Builder('Preview_Terrain')
 outline=[(-14,-3.2),(-12.6,-5.1),(-9.5,-5.7),(-6.8,-4.7),(-3.8,-4.8),(-1,-4.4),(2.5,-4.5),(5,-4.8),(8,-4.2),(11.7,-4.6),(14,-2.2),(14.7,4),(14.2,10),(13.4,15.4),(7,16.7),(-1,16.5),(-8,16.1),(-13.7,14.4),(-14.6,8.3)]
 with ground.at(trans(0,0,-.45)):ground.extrude(outline,.9,'sand')
 write_glb(env/'Preview_Terrain.glb',ground,{'preview_only':True})
 water=Builder('Preview_Water')
 water.surface(lambda u,v:((u-.5)*39,(v-.5)*40-1,-.85+.018*math.sin(u*37+v*19)+.01*math.sin(v*61)),50,50,'water')
 write_glb(env/'Preview_Water.glb',water,{'preview_only':True})
 environment=[{'file':'previews/environment/Preview_Terrain.glb','position_m':[0,0,0],'yaw_degrees':0,'scale':[1,1,1]}, {'file':'previews/environment/Preview_Water.glb','position_m':[0,0,0],'yaw_degrees':0,'scale':[1,1,1]}]
 doc={'layout':'harbor','units':'metres','source_axes':'RH_Z_UP','instances':instances,'environment':environment,
  'camera':{'position_m':[27,-36,29],'target_m':[0,.5,1.4],'orthographic_scale':41},'notes':['Water and island are preview dressing, not production terrain.','Repeated asset IDs reference a single mesh datablock / StaticMesh.','Open gates are static variants, not animated actors.']}
 (ROOT/'layout'/'harbor_layout.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2))
 assets=json.loads((ROOT/'asset_manifest.json').read_text())['assets'];gallery=[]
 for i,asset in enumerate(assets):gallery.append({'name':asset['id']+'__gallery','asset':asset['id'],'position_m':[(i%8)*7,(i//8)*8,0],'yaw_degrees':0,'scale':[1,1,1]})
 (ROOT/'layout'/'gallery_layout.json').write_text(json.dumps({'layout':'gallery','units':'metres','source_axes':'RH_Z_UP','instances':gallery,'environment':[],'camera':{'position_m':[70,-50,70],'target_m':[24,30,1],'orthographic_scale':85}},indent=2))
 print('Harbor layout:',len(instances),'instances,',len({x['asset'] for x in instances}),'unique meshes')
if __name__=='__main__':main()
