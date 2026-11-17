"""Rebuild all individual GLBs; no 3D service or Blender is required for this generator."""
from functools import partial
import json,csv
from meshcore import Builder,write_glb,ROOT
import asset_parts as p
import assets_structures as s
import assets_defense as d
import assets_harbor as h
import assets_props as a
CATALOG=[]
def asset(id,label,category,fn,collision='complex',pivot='ground_base',**meta):
 CATALOG.append(dict(id='SM_'+id,label_ko=label,category=category,fn=fn,collision=collision,pivot=pivot,**meta))
for id,label,fn in [('Watchtower','망루',s.watchtower),('CommandHut','지휘소',s.command_hut),('Forge','대장간',s.forge),('SupplyShed','보급 창고 쉘',s.supply_shed),('PirateTent','해적 텐트',s.pirate_tent),('RestCanopy','휴식 차양',s.rest_canopy)]:asset(id,label,'Structures',fn)
asset('Palisade','목책 2m','Defense',d.palisade,grid_m=2)
for name,label,fn in [('WoodGate','목재 대문',d.wooden_gate),('StoneGate','석조 정문',d.stone_gate)]:
 for opened in [False,True]:asset(name+('_Open' if opened else '_Closed'),label+(' 열림' if opened else ' 닫힘'),'Defense',partial(fn,opened=opened))
asset('Barricade','목재 바리케이드','Defense',d.barricade)
asset('Cannon','소형 대포','Defense',d.cannon,'convex')
connections={'straight':['N','S'],'corner':['N','E'],'t':['N','E','W'],'cross':['N','E','S','W'],'end':['N']}
positions={'N':[0,1,0],'E':[1,0,0],'S':[0,-1,0],'W':[-1,0,0]}
for kind,title,label in [('straight','Straight','직선'),('corner','Corner','코너'),('t','T','T자'),('cross','Cross','십자'),('end','End','끝막음')]:
 asset('Dock_'+title,'부두 '+label,'Harbor',partial(h.dock_tile,kind=kind),pivot='deck_surface_center',grid_m=2,sockets={k:positions[k] for k in connections[kind]})
asset('Dock_Platform','작업 데크 4m','Harbor',h.dock_platform,pivot='deck_surface_center',grid_m=2,sockets={k:[v*2 for v in q] for k,q in positions.items()})
asset('Dock_Stairs','부두 계단','Harbor',h.dock_stairs,pivot='upper_deck_edge',sockets={'upper':[0,0,0],'lower':[0,-2,-1]})
asset('Gangway','로프 난간 경사교','Harbor',h.gangway,pivot='low_center_plane',sockets={'low':[0,-1,0],'high':[0,1,.28]})
for id,label,fn,col in [('RopeRail','독립 로프 난간',h.rope_rail,'complex'),('Bollard','계선주',h.bollard,'convex'),('FloatingPlatform','부잔교',h.floating_platform,'complex'),('LoadingCrane','하역 크레인',h.loading_crane,'complex'),('Winch','수동 권양기',h.winch,'convex'),('SmallSailboat','소형 돛배',h.sailboat,'complex')]:asset(id,label,'Harbor',fn,col)
for id,label,fn,col in [
 ('Barrel_Large','큰 나무통',p.barrel,'convex'),('Barrel_Small','작은 나무통',partial(p.barrel,h=.6,r=.24),'convex'),
 ('Crate_Large','큰 보급 상자',p.crate,'box'),('Crate_Small','작은 보급 상자',partial(p.crate,w=.55,d=.5,h=.5),'box'),('Sack','보급 자루',p.sack,'convex'),
 ('SupplyShelf','식품·물품 선반',a.storage_shelf,'complex'),('StorageShelf_Empty','빈 수납 선반',partial(a.storage_shelf,filled=False),'complex'),
 ('TreasureChest_Closed','보물상자 닫힘',partial(a.chest,opened=False),'box'),('TreasureChest_Open','보물상자 열림',partial(a.chest,opened=True),'complex'),('CargoNet','그물 화물',h.cargo_net,'convex')]:asset(id,label,'Storage',fn,col)
for id,label,fn,col in [('CookingStation','가마솥 취사대',a.cooking_station,'complex'),('Campfire','돌 화덕 모닥불',a.campfire,'none'),('Cauldron','가마솥 단품',a.cauldron,'convex'),('FishRack','생선 건조대',a.fish_rack,'complex'),('WeaponRack','무기 거치대',a.weapon_rack,'complex'),('Table','목재 식탁',p.table,'complex'),('Bench','목재 벤치',p.bench,'complex'),('Anvil','받침 포함 모루',s.anvil,'convex')]:asset(id,label,'Camp',fn,col)
for id,label,fn,col in [
 ('Anchor','닻',a.anchor,'convex'),('Helm','배 키와 받침',a.helm,'convex'),('RopeCoil','감은 로프',h.rope_coil,'none'),('Lifebuoy','구명환',a.lifebuoy,'convex'),('Lantern','휴대 랜턴',p.lantern,'none'),
 ('Torch','기둥 횃불',p.torch,'none'),('Torch_Tripod','삼발 횃불',partial(p.torch,tripod=True),'none'),('Cage','철제 우리',a.cage,'complex'),('Stocks','형틀',a.stocks,'complex'),('Chain','사슬',a.chain,'none'),('Target','훈련 표적',a.target,'convex'),
 ('Flag_Pirate','해적 깃발',p.flagpole,'none'),('Flag_Red','붉은 깃발',partial(p.flagpole,red=True),'none'),('Banner_Pirate','해적 현수막',a.banner,'none'),('Banner_Red','붉은 현수막',partial(a.banner,mat='cloth_red'),'none'),('Banner_Canvas','무지 현수막',partial(a.banner,mat='canvas'),'none'),('BoneRibs','갈비뼈 잔해',a.bone_ribs,'complex'),('Skull','해골 소품',a.skull,'none')]:asset(id,label,'Dressing',fn,col)
for id,label,fn,col in [('RockCluster','바위 군집',a.rock_cluster,'convex'),('Palm','야자수',a.palm,'convex'),('Grass','풀 군락',a.grass,'none')]:asset(id,label,'Environment',fn,col)

def main():
 results=[]
 for e in CATALOG:
  b=Builder(e['id']);e['fn'](b);offset=0.
  if e['pivot']=='ground_base':
   offset=float(min(v[:,2].min() for v in b.v))
   for v in b.v:v[:,2]-=offset
  rel='models/'+e['id']+'.glb';stats=write_glb(ROOT/rel,b,{'asset_id':e['id'],'pivot':e['pivot']})
  r={k:v for k,v in e.items() if k!='fn'};r.update(stats);r.update(file=rel,material='M_PirateAtlas',material_slots=1,authoring_ground_offset_m=round(offset,6));results.append(r)
  print(f"{e['id']:<29} {stats['triangles']:>6} tris  {stats['vertices']:>6} vertices",flush=True)
 probe=Builder('SM_AxisProbe');probe.box((.5,1,1.5),(1,2,3),'wood_teal',.02)
 write_glb(ROOT/'technical'/'SM_AxisProbe.glb',probe,{'purpose':'axis_and_unit_calibration','source_bounds_m':[[0,0,0],[1,2,3]]})
 manifest={'pack':'Pirate Outpost','version':'1.0','units':'metres','source_axes':'X-right Y-back Z-up; front=-Y','glb_axes':'standard glTF Y-up','texture_limit':1024,'atlas_material':'M_PirateAtlas','uv0':'overlapping trim/atlas UV; not a unique lightmap UV','assets':results,'validation_boundary':'GLB geometry and VTK renders executed; Blender and Unreal scripts are not editor-runtime-tested here.'}
 (ROOT/'asset_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 with (ROOT/'docs'/'asset_catalog.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);keys=['id','label_ko','category','triangles','vertices','pivot','collision','file'];w.writerow(keys)
  for x in results:w.writerow([x[k] for k in keys])
 print('TOTAL',len(results),'ASSETS;',sum(x['triangles'] for x in results),'triangles')
if __name__=='__main__':main()
