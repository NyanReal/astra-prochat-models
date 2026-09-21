"""Deterministic camera-fitted modular scene placement. Does not regenerate meshes."""
from pathlib import Path
import json,math
from collections import Counter
import numpy as np
from mesh_core import ROOT,euler_matrix
from scene_math import CAMERA,pixel_to_world,world_to_pixel,ground_at_pixel,terrain_height,matrix_quaternion

SEED=20260921
RNG=np.random.default_rng(SEED)
INSTANCES=[];COUNTS=Counter();ANCHORS=[]
YS=np.array([-180,0,120,240,330,400,500,620,760,900,1160],float)
LEFT=np.array([1180,1180,1165,1080,1100,1010,965,1050,1120,1200,1320],float)
RIGHT=np.array([1380,1380,1390,1520,1540,1440,1300,1360,1390,1420,1630],float)
PATH=np.array([[745,-80],[694,96],[619,266],[500,422],[608,535],[664,652],[754,774],[858,916],[946,1110]],float)

def bank(y,side='left'):return float(np.interp(y,YS,LEFT if side=='left' else RIGHT))
def path_x(y):return float(np.interp(y,PATH[:,1],PATH[:,0]))

def add(asset,loc,rotation=(0,0,0),scale=(1,1,1),group=None,note=None):
    if isinstance(scale,(float,int)):scale=(scale,scale,scale)
    COUNTS[asset]+=1;ident=f'{asset}__{COUNTS[asset]:04d}'
    r=euler_matrix(*rotation)
    obj={'id':ident,'asset_id':asset,'position_m':[round(float(x),6) for x in loc],
         'rotation_euler_xyz_deg':[round(float(x),6) for x in rotation],
         'rotation_quat_xyzw':[round(float(x),8) for x in matrix_quaternion(r)],
         'scale':[round(float(x),6) for x in scale],'group':group or 'Scene'}
    if note:obj['note']=note
    INSTANCES.append(obj);return obj

def at(asset,x,y,z=None,rotation=(0,0,0),scale=1.,group=None,anchor=None,offset=.0):
    loc=ground_at_pixel(x,y,offset) if z is None else pixel_to_world(x,y,z)
    out=add(asset,loc,rotation,scale,group)
    if anchor:ANCHORS.append({'name':anchor,'instance_id':out['id'],'reference_anchor_px':[x,y],'world_anchor_m':list(loc),'anchor_kind':'object origin / foot point'})
    return out

def path_distance(px,py):return abs(px-path_x(py))

def build_ground():
    centres=[]
    # Dense overlap avoids holes even where the irregular module outlines differ.
    for j,y in enumerate(np.arange(-25,24,3.8)):
        for i,x in enumerate(np.arange(-24,26,3.8)):
            xx=x+(.45 if j%2 else 0);z=terrain_height(xx,y);px,py=world_to_pixel((xx,y,z))
            if not (-220<py<1270 and -280<px<1820):continue
            left=px<bank(py)-115;right=px>bank(py,'right')+105
            tank_xy=pixel_to_world(-20,335,1.55)[:2]
            if np.linalg.norm(np.array([xx,y])-tank_xy)<10.45:continue
            if not (left or right):continue
            group='Ground/Mainland' if left else 'Ground/RightBank'
            idx=(i+j*3)%4;rot=RNG.uniform(0,360)
            add('Ground_Meadow_'+'ABCD'[idx],(xx,y,z),rotation=(0,0,rot),scale=(1.08,1.02,1),group=group)
            centres.append((xx,y,z,group))
    # Every pair of adjoining rows gets a real transition island, not just a material blend.
    for i,(x,y,z,group) in enumerate(centres):
        for dx,dy in [(1.9,0),(0,1.9)]:
            p=(x+dx,y+dy,terrain_height(x+dx,y+dy)+.10);px,py=world_to_pixel(p)
            is_land=px<bank(py)-105 or px>bank(py,'right')+85
            if is_land and -120<py<1140:
                add('Transition_Moss_'+'ABC'[i%3],p,rotation=(0,0,RNG.uniform(0,360)),scale=(1.25,.80,1),group='Ground/SeamTransitions')
    # The winding open path is built from separate, overlapping earth modules.
    for i,y in enumerate(np.arange(-60,1180,64)):
        x=path_x(y);dx=path_x(y+10)-path_x(y-10)
        angle=-math.degrees(math.atan2(dx,20/.743))
        at('Ground_Dirt_'+'AB'[i%2],x,y,rotation=(0,0,angle),scale=(.64,.88,.35),group='Ground/Path',offset=.060)
        for side in (-1,1):
            # Variable silhouettes keep module intersections from becoming circular seams.
            at('Transition_Moss_'+'ABC'[i%3],x+side*RNG.uniform(49,66),y+RNG.uniform(-15,15),rotation=(0,0,RNG.uniform(0,360)),scale=(.63,.73,1),group='Ground/SeamTransitions',offset=.075)
    for i in range(90):
        y=RNG.uniform(-20,1110);x=path_x(y)+RNG.normal(0,40)
        if 0<x<bank(y)-30:
            at('Paving_Broken_'+'ABC'[i%3],x,y,rotation=(RNG.uniform(-3,3),RNG.uniform(-3,3),RNG.uniform(-15,50)),scale=RNG.uniform(.5,.95),group='Ground/BrokenPaving',offset=.10)


def build_river():
    # Wider overlapping water sheets run beneath the bank rocks.
    points=[]
    for py in np.arange(160,1300,105):
        px=(bank(py)+bank(py,'right'))*.5
        points.append(pixel_to_world(px,py,-.09))
    for i,(a,b) in enumerate(zip(points[:-1],points[1:])):
        center=(a+b)*.5;vec=b-a;ln=np.linalg.norm(vec[:2]);py=world_to_pixel(center)[1]
        width=(bank(py,'right')-bank(py))/42.6667+1.6
        angle=math.degrees(math.atan2(-vec[0],vec[1]))
        if i==0:add('River_Main',[10.5,0.,-.09],group='Water/LowerRiver')
        for j in range(1):
            p=center+RNG.uniform(-.8,.8,3);p[2]=-.047
            add('Foam_Generated_Eddies',p,rotation=(0,0,RNG.uniform(-180,180)),scale=(.70,.90,1),group='Water/Foam')
    # Waterfall origin is the foot of the drop; upper water begins exactly at its crest.
    foot=pixel_to_world(1256,264,-.08)
    add('Waterfall',foot,rotation=(0,0,0),group='Water/Waterfall')
    for i in range(3):
        p=foot+np.array([0,3.45+i*6.3,5.5]);add('River_Surface_A',p,scale=(.5,1.,1),group='Water/UpperRiver')
    add('Foam_Ring',foot+[0,-.35,.05],scale=(1.25,.70,1),group='Water/Foam')
    add('Foam_Ring',foot+[0,0,5.56],scale=(1.,.20,1),group='Water/CrestFoam')
    for jj,py in enumerate((-20,24,64,100)):
        for xx in (1195,1320):
            at('Rock_Bank_'+'ABC'[jj%3],xx,py,z=5.38,rotation=(0,0,jj*51),scale=(.42,.58,.40),group='Rocks/UpperRiverEdges')
            at('Grass_A',xx+(-15 if xx<1256 else 15),py-5,z=5.65,scale=.65,group='Vegetation/UpperRiverEdges')
    # Continuous overlap underlayer closes narrow voids between the main ground grid and the banks.
    for side in ('left','right'):
        for i,py in enumerate(np.arange(285,1140,48)):
            px=bank(py,side)+(-78 if side=='left' else 78)
            at('Ground_Meadow_'+'ABCD'[i%4],px,py,z=1.47,rotation=(0,0,RNG.uniform(-15,15)),scale=(.57,.77,.4),group='Ground/BankUnderlap')
            at('Grass_A',px,py-8,z=1.52,scale=.65,group='Vegetation/BankStitchTufts')
            at('Transition_Moss_'+'ABC'[i%3],bank(py,side)+(-30 if side=='left' else 30),py-8,z=1.53,rotation=(0,0,RNG.uniform(0,360)),scale=(.62,.74,1),group='Ground/BankStitchMoss')
            if side=='left' and i%3==0:
                at('Bush_'+'ABC'[i%3],bank(py)-44,py+5,z=1.54,scale=.66,group='Vegetation/BankStitchShrubs')
    # Bank rocks connect topsoil to water, with separate low moss caps at their upper edges.
    for side in ('left','right'):
        for i,py in enumerate(np.arange(295,1140,48)):
            px=bank(py,side)+RNG.uniform(-22,22)
            at('Rock_Bank_'+'ABC'[i%3],px,py,z=-.05,rotation=(0,RNG.uniform(-9,9),RNG.uniform(0,360)),scale=(RNG.uniform(.80,1.15),RNG.uniform(.70,1.0),RNG.uniform(.9,1.3)),group='Rocks/Banks')
            if i%2==0:
                at('Transition_Moss_'+'ABC'[i%3],px+(-20 if side=='left' else 20),py-30,rotation=(0,0,RNG.uniform(0,360)),scale=.63,group='Ground/BankTransitions',offset=.03)
    for i,(x,y,s) in enumerate([(1183,664,1.10),(1041,508,.62),(1105,431,.57),(1381,370,.90),(1285,341,.42),(1276,850,.55),(1335,930,.58)]):
        rock_inst=at('Rock_Hero_Island' if i==0 else 'Rock_River_'+'ABC'[i%3],x,y,z=-.11,rotation=(0,0,RNG.uniform(0,360)),scale=1.0 if i==0 else s,group='Rocks/River')
        if i==0:
            rp=np.asarray(rock_inst['position_m'])
            add('Grass_A',rp+[0,0,1.72],scale=.55,group='Vegetation/IslandTufts')
            for jj,offset in enumerate(([1.35,0,0],[-1.1,-.6,0],[0,-1.1,0])):
                add('Foam_Generated_Eddies',rp+offset+[0,0,.08],rotation=(0,0,jj*83),scale=.88,group='Water/IslandFoam')
        at('Foam_Ring',x,y,z=-.027,rotation=(0,0,RNG.uniform(0,360)),scale=(1.55,1.30,1) if i==0 else (s*1.10,s*.93,1),group='Water/Foam')
    for i,(x,y,sx,sz) in enumerate([(1134,271,.62,.95),(1376,300,.90,1.18),(1470,270,1.2,1.10),(1550,228,1.1,1.20),(1135,145,.80,.83)]):
        at('Cliff_Block_'+'AB'[i%2],x,y,z=-.10,rotation=(0,0,RNG.uniform(-12,35)),scale=(sx,.9,sz),group='Rocks/WaterfallCliffs')
    for i,(x,y) in enumerate([(1440,75),(1550,15)]):
        at('Ground_Meadow_'+'ABCD'[i%4],x,y,z=5.0,rotation=(0,0,i*39),scale=(.79,.8,.45),group='Ground/UpperLedges')


def line_rails(a,b,width=0.,group='Architecture/Railings',broken=False):
    a=np.asarray(a);b=np.asarray(b);vec=b-a;ln=np.linalg.norm(vec[:2]);ang=math.degrees(math.atan2(vec[1],vec[0]));n=max(1,int(round(ln/3)))
    for i in range(n):
        c=a+(b-a)*(i+.5)/n
        add('Railing_Broken' if broken and i==n-1 else 'Railing_3m',c,rotation=(0,0,ang),scale=(ln/n/3,1,1),group=group)


def build_ruins():
    tank=pixel_to_world(-20,335,1.55)
    for i in range(12):add('Tank_Arc_'+'ABC'[i%3],tank,rotation=(0,0,i*30),group='Architecture/Tank')
    add('Tank_D3_Marking',tank,group='Architecture/Tank')
    add('Tank_Interior_Floor',tank-[0,0,.14],group='Architecture/Tank')
    for ii,aa in enumerate(np.linspace(0,2*np.pi,26,endpoint=False)):
        p=tank+np.array([8.50*math.cos(aa),8.50*math.sin(aa),0])
        add('Ground_Meadow_'+'ABCD'[ii%4],p,rotation=(0,0,math.degrees(aa)),scale=(.51,.51,.4),group='Ground/TankPerimeter')
    ANCHORS.append({'name':'tank centre at floor','reference_anchor_px':[-20,335],'world_anchor_m':tank.tolist(),'anchor_kind':'tank pivot'})
    # Catwalk centreline fitted to the image, deck and rails remain reusable modules.
    a=pixel_to_world(222,266,6.08);b=pixel_to_world(615,120,6.08);vec=b-a;ln=np.linalg.norm(vec[:2]);ang=math.degrees(math.atan2(vec[1],vec[0]));side=np.array([-vec[1],vec[0],0])/ln
    n=4
    for i in range(n):add('Catwalk_Deck_3m',a+vec*(i+.5)/n,rotation=(0,0,ang),scale=(ln/n/3,1,1),group='Architecture/Catwalk')
    line_rails(a-side*.65,b-side*.65,group='Architecture/CatwalkRails')
    line_rails(a+side*.65,b+side*.65,group='Architecture/CatwalkRails')
    mid=a+vec*.55
    base_bunker=mid.copy();base_bunker[2]=1.62
    add('Utility_Bunker_Bay',base_bunker,rotation=(0,0,ang),scale=(1.25,.94,1.03),group='Architecture/Bunker')
    stair_bottom=pixel_to_world(428,443,1.64);stair_top=pixel_to_world(330,278,6.14);sv=stair_top-stair_bottom
    add('Stairs_Industrial',stair_bottom,rotation=(0,0,math.degrees(math.atan2(sv[1],sv[0]))),scale=(np.linalg.norm(sv[:2])/4.6,1,(sv[2])/4.5),group='Architecture/Stairs')
    at('Banner_Still_Here',487,206,z=6.13,rotation=(0,0,ang),scale=(1.,1.,1.),group='Architecture/Banner',anchor='banner top')
    at('Crate_Wood',625,328,rotation=(0,0,ang),scale=(1.3,1.3,1.45),group='Props/UtilityCorner')
    at('Drum_Aged',672,322,rotation=(0,0,-14),scale=1.08,group='Props/UtilityCorner')
    for i,t in enumerate(np.linspace(.1,.98,13)):
        top=a+(b-a)*t-side*.74+np.array([0,0,-.02])
        if .40<t<.70:continue
        add('Ivy_Long' if i%3==0 else 'Ivy_Short',top,rotation=(0,0,ang),scale=RNG.uniform(.75,1.08),group='Vegetation/CatwalkVines')
    for i,angle in enumerate(np.radians(np.arange(-95,125,15))):
        if -68<math.degrees(angle)<-37:continue
        point=tank+[7.045*math.cos(angle),7.045*math.sin(angle),6.4]
        add('Ivy_Long' if i%3 else 'Ivy_Short',point,rotation=(0,0,math.degrees(angle)+90),scale=(.85,.85,RNG.uniform(.8,1.45)),group='Vegetation/TankVines')
    # Cantilevered concrete bridge remnant and its still-standing pier.
    deck=at('Bridge_Deck_Broken',1191,208,z=4.40,rotation=(0,0,-28),scale=(1.05,1.05,1.0),group='Architecture/Bridge',anchor='broken bridge deck')
    dp=np.asarray(deck['position_m']);add('Bridge_Pier',(dp[0]+.25,dp[1]+.1,-.08),rotation=(0,0,-28),scale=(.95,.95,.91),group='Architecture/Bridge')
    rot=euler_matrix(0,0,-28)
    for y in (-1.16,1.16):
        p=dp+rot@np.array([-.5,y,.02]);add('Railing_Broken',p,rotation=(0,0,-28),scale=(1.25,1,1),group='Architecture/BridgeRails')
    for k,x in enumerate((-1.8,-.6,.8)):
        p=dp+rot@np.array([x,-1.2,-.22]);add('Ivy_Long',p,rotation=(0,0,-28),scale=(.75,.75,.82+k*.1),group='Vegetation/BridgeVines')
    # Fallen timber is a separate bridge-sized prop between the rocky banks.
    la=pixel_to_world(1012,390,1.56);lb=pixel_to_world(1285,495,1.65);lv=lb-la
    add('Log_Fallen_Bridge',(la+lb)/2,rotation=(0,-math.degrees(math.atan2(lv[2],np.linalg.norm(lv[:2]))),math.degrees(math.atan2(lv[1],lv[0]))),scale=(np.linalg.norm(lv)/8.1,1,1),group='Props/FallenLog')
    wall=at('Concrete_Wall_Ruined',1425,718,z=-.04,rotation=(0,0,-32),scale=(1.1,1.1,1.22),group='Architecture/RightWall')
    add('Wall_Marking_Nature',wall['position_m'],rotation=(0,0,-32),scale=(1.1,1.1,1.22),group='Architecture/RightWall')
    wp=np.asarray(wall['position_m']);wr=euler_matrix(0,0,-32)
    for k,x in enumerate((-1.94,1.94)):
        add('Ivy_Long',wp+wr@np.array([x,-.30,5.70]),rotation=(0,0,-32),scale=(.9,.9,1.2),group='Vegetation/RightWallVines')
    # Foreground lattice tower supports the small gull, without covering the river centre.
    py=at('Lattice_Pylon',1410,1090,z=-.10,rotation=(0,0,20),scale=(1.5,1.5,1.95),group='Architecture/Pylon')
    add('Gull_Perched',np.asarray(py['position_m'])+[0,0,6.86*1.95],rotation=(0,0,-30),scale=1.18,group='Wildlife/Gull')
    line_rails(pixel_to_world(964,716,1.7),pixel_to_world(898,582,1.7),group='Architecture/PathRails',broken=True)
    line_rails(pixel_to_world(1050,882,1.5),pixel_to_world(1305,989,1.5),group='Architecture/ForegroundRails',broken=True)


def build_props():
    truck=at('Truck_Abandoned',492,804,rotation=(0,0,29),scale=1.10,group='Props/Truck',anchor='truck ground pivot')
    p=np.asarray(truck['position_m']);r=euler_matrix(0,0,29)
    for j in range(5):
        loc=p+r@np.array([-.4+j*.53,-1.08,2.95]);add('Ivy_Short',loc,rotation=(0,0,29),scale=(.55,.55,.80),group='Vegetation/TruckVines')
    for i,(x,y,s) in enumerate([(321,704,.95),(368,688,1.03),(331,793,1.1)]):at('Crate_Open' if i==2 else 'Crate_Wood',x,y,rotation=(0,0,25+i*8),scale=s,group='Props/Crates')
    at('Tarp_Covered_Stack',420,678,rotation=(0,0,28),scale=1.17,group='Props/Crates')
    at('Bush_A',554,889,scale=1.12,group='Vegetation/TruckForeground',offset=.06)
    at('Bush_C',359,870,scale=.95,group='Vegetation/TruckForeground',offset=.06)
    at('Traveller_Static',631,585,rotation=(0,0,-22),scale=1.47,group='Character',anchor='traveller feet')


def build_vegetation():
    # Hand-fitted trees preserve the visible path, architecture and river.
    trees=[('Broadleaf_A',821,374,1.10),('Pine_A',958,310,1.07),('Pine_B',851,165,.63),
           ('Broadleaf_B',339,172,1.20),('Broadleaf_C',482,92,1.0),('Broadleaf_A',611,111,.83),
           ('Broadleaf_C',688,10,1.0),('Broadleaf_B',744,105,.79),('Broadleaf_A',1063,88,1.0),
           ('Pine_A',171,762,1.02),('Pine_B',29,811,.90),('Broadleaf_B',55,1020,1.12),
           ('Broadleaf_C',250,1120,1.30),('Broadleaf_A',450,1082,1.10),('Broadleaf_A',605,1120,1.22),
           ('Broadleaf_B',1118,835,1.04),('Broadleaf_C',109,666,.66),('Broadleaf_A',302,611,.71),
           ('Broadleaf_B',42,638,.88),('Broadleaf_C',1520,497,.93),('Broadleaf_A',1555,996,1.04),
           ('Pine_B',1187,147,.60),('Broadleaf_C',1355,53,.77),('Broadleaf_A',1517,139,.83)]
    for i,(asset,x,y,s) in enumerate(trees):
        z=5.0 if (x>1280 and y<150) else None
        at(asset,x,y,z=z,rotation=(0,0,RNG.uniform(0,360)),scale=(s,s,s*RNG.uniform(.98,1.04)*(1.24 if i==0 else 1.30 if i==1 else 1.)),group='Vegetation/Trees',anchor='central broadleaf base' if i==0 else None)
    # Layered shrubs follow bank edges and groups rather than an indiscriminate full-screen scatter.
    for i,py in enumerate(np.arange(290,990,32)):
        for j in range(2):
            px=bank(py)-RNG.uniform(38,130)-j*35
            if path_distance(px,py)<88:continue
            at('Bush_'+'ABC'[(i+j)%3],px,py,rotation=(0,0,RNG.uniform(0,360)),scale=RNG.uniform(.70,1.18),group='Vegetation/BankShrubs',offset=.10)
    for i in range(132):
        px=RNG.uniform(-60,1590);py=RNG.uniform(-70,1120)
        land=px<bank(py)-60 or px>bank(py,'right')+25
        if not land or path_distance(px,py)<103:continue
        # Keep tank/catwalk silhouettes legible; foliage attaches as vines instead.
        if px<610 and 170<py<500:continue
        if 340<px<620 and 650<py<875:continue
        at('Bush_'+'ABC'[i%3],px,py,rotation=(0,0,RNG.uniform(0,360)),scale=RNG.uniform(.58,1.00),group='Vegetation/ShrubGroups',offset=.09)
    for i in range(600):
        py=RNG.uniform(-20,1110);px=RNG.uniform(-60,1620)
        if not (px<bank(py)-35 or px>bank(py,'right')+20):continue
        if px<270 and 100<py<540:continue
        dist=path_distance(px,py)
        if dist<35 and RNG.random()<.91:continue
        if 340<px<620 and 720<py<865:continue
        asset='Fern' if i%8==0 else 'Grass_'+'AB'[i%2]
        at(asset,px,py,rotation=(0,0,RNG.uniform(0,360)),scale=RNG.uniform(.40,.84),group='Vegetation/Groundcover',offset=.16)
    for i in range(82):
        py=RNG.uniform(315,1050);side=-1 if i%2 else 1;px=path_x(py)+side*RNG.uniform(55,123)
        if px>bank(py)-22:continue
        at('Flowers_White' if i%3 else 'Flowers_Pink',px,py,rotation=(0,0,RNG.uniform(0,360)),scale=RNG.uniform(.55,.90),group='Vegetation/Flowers',offset=.18)
    # Upper ledge plants / bridge tufts make structural-to-natural junctions explicit.
    for i,(px,py,z) in enumerate([(1150,170,4.42),(1230,211,4.42),(1355,86,5.0),(1430,123,5.0),(1133,65,5.0)]):
        at('Grass_A',px,py,z=z,scale=.7,group='Vegetation/LedgeTufts')
        at('Bush_C',px+18,py-9,z=z,scale=.48,group='Vegetation/LedgeShrubs')


def main():
    global RNG
    INSTANCES.clear();COUNTS.clear();ANCHORS.clear();RNG=np.random.default_rng(SEED)
    build_ground();build_river();build_ruins();build_props();build_vegetation()
    catalog_path=ROOT/'data/assets.json'
    if catalog_path.exists():
        assets={a['id']:a for a in json.loads(catalog_path.read_text())['assets']}
        missing=set(i['asset_id'] for i in INSTANCES)-set(assets)
        if missing:raise RuntimeError('Assets still missing: '+', '.join(sorted(missing)))
    groups=Counter(i['group'].split('/')[0] for i in INSTANCES)
    doc={'schema_version':1,'title':'Still Here — D3','seed':SEED,'coordinate_system':'RH_Z_UP_METRES',
         'camera':CAMERA,'lighting':{'sun_direction_to_light':[-.55,-.85,1.35],'sun_energy_blender':2.2,'sun_angle_degrees':5.0,
                                  'world_strength_blender':.45,'world_color_linear':[.28,.38,.45]},
         'instances':INSTANCES,'reference_anchors':ANCHORS,'group_counts':dict(groups),
         'notes':['No background plane contains the reference image.','Source camera is fitted, not recovered from calibration metadata.','Ground seam transitions and bank rocks are separate mesh instances.']}
    (ROOT/'data/scene.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False),encoding='utf8')
    (ROOT/'data/camera.json').write_text(json.dumps(CAMERA,indent=2),encoding='utf8')
    print('Instances:',len(INSTANCES),'unique placed assets:',len(COUNTS),'groups:',dict(groups))

if __name__=='__main__':main()
