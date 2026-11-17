"""Individual camp, storage and maritime dressing props."""
import math,numpy as np
from meshcore import *
from asset_parts import *
PI=math.pi

def chest(b,opened=False):
 w,d,h=1.12,.68,.59
 # Hollow timber box: useful for the open variant, not a solid block hidden under a lid.
 b.box((0,0,.06),(w,d,.12),'wood_dark',.025)
 for y in [-d/2,d/2]:
  for i in range(3):b.box((0,y,.17+i*.17),(w,.08,.16),'wood',.025)
 for x in [-w/2,w/2]:b.box((x,0,.34),(.08,d,.56),'wood_dark',.03)
 for x in [-.43,.43]:
  for y in [-.389,.389]:
   b.box((x,y,.3),(.085,.04,.57),'gold',.014)
   for z in [.12,.48]:bolt(b,(x,y-.015 if y<0 else y+.015,z),r=.02,metal='gold')
 # Lid rotates about the rear hinge; its upper surface is segmented curved timber.
 with b.at(trans(0,d/2,h)@rx(math.radians(-105 if opened else 0))@trans(0,-d/2,0)):
  for i in range(7):
   x=-w/2+(i+.5)*w/7
   b.surface(lambda u,v,x=x: (x+(u-.5)*(w/7-.008),-.36*math.cos(PI*v),.32*math.sin(PI*v)),2,12,'wood')
  for x in [-.43,.43]:
   b.surface(lambda u,v,x=x:(x+(u-.5)*.08,-.367*math.cos(PI*v),.325*math.sin(PI*v)+.004),1,14,'gold')
  for x in [-w/2,w/2]:
   # Curved end plate, closed with a simple extrusion.
   poly=[(-.35,0)]+[(.35*math.cos(t),.32*math.sin(t)) for t in np.linspace(0,PI,13)]+[(.35,0)]
   # Order the semicircle directly to avoid crossing the bottom edge.
   poly=[(.35*math.cos(t),.32*math.sin(t)) for t in np.linspace(0,PI,13)]
   with b.at(trans(x,0,0)@rz(PI/2)@rx(PI/2)):b.extrude(poly,.055,'wood_dark')
  b.box((0,-.382,.035),(.16,.05,.2),'gold',.025)
  b.box((0,-.415,.02),(.03,.014,.07),'black',.008)
 if opened:
  rng=np.random.default_rng(10)
  for i in range(33):
   x=rng.uniform(-.41,.41);y=rng.uniform(-.23,.23);z=.2+rng.uniform(0,.11)
   with b.at(trans(x,y,z)@rx(rng.uniform(-.3,.3))@ry(rng.uniform(-.3,.3))):
    b.lathe([(0,.065),(.025,.065)],'gold',10)


def storage_shelf(b,filled=True):
 w,d,h=1.75,.66,1.7
 for x in [-w/2,w/2]:
  for y in [-d/2,d/2]:
   log(b,(x,y,0),(x,y,h),.065)
   lash(b,(x,y,h-.15),.08,turns=2,height=.07)
 for z in [.15,.79,1.44]:
  with b.at(trans(0,0,z)):plank_floor(b,w+.1,d+.1,0,.08,spacing=.25)
  b.beam((-w/2,d/2,z+.1),(w/2,d/2,z+.1),.07,.08,'wood_dark')
 b.beam((-w/2,d/2,.2),(w/2,d/2,1.6),.065,.07,'wood_dark')
 if filled:
  for i,x in enumerate([-.6,-.25,.1,.45]):use(b,bottle,(x,-.03,1.45),s=1.0 if i%2 else .85,mat='green_glass' if i%2 else 'glass')
  for x in [-.5,.0,.5]:
   b.sphere((x,-.04,.91),.14,'bread',12,7,squash=(1,.8,.65))
   b.sphere((x,.13,.99),.12,'bread',12,7,squash=(1,.8,.65))
  use(b,sack,(-.48,0,.17),s=.66)
  use(b,crate,(.37,0,.17),s=.48)


def cauldron(b):
 b.lathe([(0,.18),(.06,.29),(.18,.36),(.41,.34),(.49,.28),(.52,.3),(.54,.3),(.54,.24),(.46,.245),(.2,.28),(.1,.18)],'metal',20,False)
 b.lathe([(.35,.27),(.36,.27)],'stone_dark',20)
 for x in [-.32,.32]:b.torus((x,0,.43),.065,.019,'metal','y',16,6)
 ts=np.linspace(0,PI,21)
 b.tube([(.34*math.cos(t),0,.43+.42*math.sin(t)) for t in ts],.022,'metal',7)
 for x,y in [(-.18,-.14),(.18,-.14),(0,.18)]:b.cylinder((x,y,.04),(x*1.14,y*1.14,-.09),.035,'metal',segments=7)


def campfire(b):
 for j in range(10):
  t=TAU*j/10
  b.sphere((.59*math.cos(t),.59*math.sin(t),.12),.18,'stone' if j%3 else 'stone_dark',12,7,squash=(1,.8,.7))
 for ang in [0,PI/2]:
  with b.at(rz(ang)):log(b,(-.44,0,.12),(.44,0,.12),.095,'wood_dark')
 use(b,flame,(0,0,.18),s=1.4,h=.5)


def cooking_station(b):
 campfire(b)
 for sx in [-1,1]:
  log(b,(sx*.86,-.25,0),(sx*.62,0,1.65),.075)
  log(b,(sx*.86,.35,0),(sx*.62,0,1.65),.075)
  lash(b,(sx*.64,0,1.53),.1,axis='x',turns=3)
 log(b,(-.92,0,1.62),(.92,0,1.62),.075)
 b.tube([(0,0,1.6),(0,0,1.4),(0,0,1.3)],.018,'metal',7)
 use(b,cauldron,(0,0,.49))


def fish(b,h=.52):
 b.sphere((0,0,h*.38),h*.3,'fish',14,9,squash=(.48,.3,1.1))
 with b.at(trans(0,0,h*.73)@rx(PI/2)):
  b.extrude([(-h*.16,h*.2),(0,.01),(h*.16,h*.2),(0,h*.14)],.025,'silver')
 # Side fin and eye are deliberately readable, not photorealistic scales.
 with b.at(trans(0,-h*.097,h*.35)@rx(PI/2)):
  b.extrude([(0,0),(h*.18,h*.1),(h*.03,-h*.1)],.018,'silver')
 b.sphere((h*.065,-h*.075,h*.21),h*.027,'black',10,6)
 b.tube([(0,0,h*.94),(0,0,h*1.2)],.009,'rope',5)


def fish_rack(b):
 for x in [-.95,.95]:
  log(b,(x,0,0),(x,0,1.88),.07)
  log(b,(x,-.3,0),(x,.3,0),.06)
  lash(b,(x,0,1.65),.085,turns=2)
 log(b,(-1.12,0,1.75),(1.12,0,1.75),.07)
 for i,x in enumerate([-.68,-.23,.23,.67]):
  h=.65 if i%2 else .56
  use(b,fish,(x,0,1.73-h*1.2),h=h)


def saber(b):
 poly=[(-.025,0),(.03,0),(.055,.4),(.14,.71),(.18,.8),(.08,.75),(-.015,.44)]
 with b.at(rx(PI/2)):b.extrude(poly,.027,'silver')
 b.cylinder((0,0,-.24),(0,0,0),.036,'leather',segments=9)
 b.sphere((0,0,-.25),.045,'gold',10,7)
 b.tube([(-.08,0,-.02),(-.12,0,-.1),(-.08,0,-.25),(0,0,-.27)],.014,'gold',6)
 b.box((0,0,0),(.23,.055,.035),'gold',.014)


def spear(b):
 log(b,(0,0,0),(0,0,1.7),.023,'wood_dark')
 with b.at(trans(0,0,1.65)@rx(PI/2)):
  b.extrude([(-.075,.12),(-.02,0),(.02,0),(.075,.12),(.0,.35)],.025,'silver')
 lash(b,(0,0,1.65),.03,turns=2,height=.06)


def weapon_rack(b):
 for x in [-.9,.9]:
  log(b,(x,-.28,0),(x,0,1.55),.07)
  log(b,(x,.28,0),(x,0,1.55),.07)
  lash(b,(x,0,1.3),.08,turns=2)
 for z in [.2,1.34]:log(b,(-1,0,z),(1,0,z),.065)
 for x in [-.57,-.18,.2]:
  with b.at(trans(x,-.08,1.25)@rx(PI)):saber(b)
 for x in [.59,.8]:
  with b.at(trans(x,.04,.05)@ry(-.05)):spear(b)


def anchor(b):
 # Shank, stock, ring, curved arms and flukes are independent solid geometry.
 b.beam((0,0,.15),(0,0,1.38),.105,.11,'metal',.027)
 b.beam((-.52,0,1.12),(.52,0,1.12),.115,.13,'wood_dark',.025)
 for x in [-.47,.47]:b.box((x,0,1.12),(.12,.16,.14),'metal',.025)
 b.torus((0,0,1.55),.13,.035,'metal','y',20,7)
 for side in [-1,1]:
  path=[(side*x,0,z) for x,z in [(0,.18),(.18,.13),(.37,.2),(.54,.39),(.63,.63)]]
  b.tube(path,.06,'metal',8)
  poly=[(side*.42,.54),(side*.64,.76),(side*.73,.47),(side*.61,.52),(side*.51,.4)]
  with b.at(rx(PI/2)):b.extrude(poly,.12,'metal')


def helm(b):
 # Display stand is included so its pivot is ground-friendly.
 b.box((0,0,.08),(.62,.5,.16),'wood_dark',.04)
 b.beam((0,0,.15),(0,0,1.0),.15,.18,'wood_dark')
 center=(0,-.13,1.04)
 b.torus(center,.46,.047,'wood','y',28,7)
 b.torus(center,.38,.018,'gold','y',28,6)
 with b.at(trans(*center)@rx(PI/2)):
  b.lathe([(-.07,.12),(.07,.12)],'gold',14)
  for t in np.linspace(0,TAU,8,endpoint=False):
   log(b,(.1*math.cos(t),.1*math.sin(t),0),(.62*math.cos(t),.62*math.sin(t),0),.03)
   b.sphere((.62*math.cos(t),.62*math.sin(t),0),.043,'wood_pale',10,6)


def lifebuoy(b):
 with b.at(trans(0,0,.52)@rx(PI/2)):
  for j in range(8):
   a=TAU*j/8;c=TAU*(j+1)/8
   path=[(.36*math.cos(t),.36*math.sin(t),0) for t in np.linspace(a,c,9)]
   b.tube(path,.092,'red' if j%2==0 else 'white',9)
  b.torus((0,0,0),.49,.018,'rope',segments=40,sides=6)
  for t in np.linspace(0,TAU,4,endpoint=False):
   log(b,(.4*math.cos(t),.4*math.sin(t),0),(.51*math.cos(t),.51*math.sin(t),0),.026,'rope')


def cage(b):
 b.lathe([(0,.39),(.055,.43),(.11,.43)],'metal',20)
 for t in np.linspace(0,TAU,12,endpoint=False):
  b.tube([(.4*math.cos(t),.4*math.sin(t),.08),(.4*math.cos(t),.4*math.sin(t),1.0),(.28*math.cos(t),.28*math.sin(t),1.18),(0,0,1.28)],.021,'metal',6)
 for z in [.13,.95]:b.torus((0,0,z),.4,.03,'metal',segments=28,sides=6)
 b.torus((0,0,1.4),.1,.026,'metal','y',20,6)
 b.box((0,-.43,.55),(.1,.06,.16),'gold',.02)


def ring_board(b,cx,cz,halfw,halfh,hole,depth=.14):
 # A rectangular plank segment with a true circular hole, not a painted black disc.
 ts=np.linspace(0,TAU,25);outer=[];inner=[]
 for t in ts:
  co,si=math.cos(t),math.sin(t)
  rr=min(halfw/max(abs(co),1e-9),halfh/max(abs(si),1e-9))
  outer.append((cx+rr*co,cz+rr*si));inner.append((cx+hole*co,cz+hole*si))
 for sy in [-1,1]:
  vv=[];ff=[];uv=[]
  for o,i in zip(outer,inner):vv.extend([(o[0],sy*depth/2,o[1]),(i[0],sy*depth/2,i[1])]);uv.extend([(1,.5),(0,.5)])
  for j in range(24):
   q=[j*2,j*2+2,j*2+3,j*2+1]
   if sy>0:q=q[::-1]
   ff.extend([(q[0],q[1],q[2]),(q[0],q[2],q[3])])
  b.add(vv,ff,uv,np.tile((0,sy,0),(len(vv),1)),'wood')
 for contour,inside in [(outer,False),(inner,True)]:
  for j in range(24):
   a=contour[j];c=contour[j+1]
   vv=[(a[0],-.07,a[1]),(c[0],-.07,c[1]),(c[0],.07,c[1]),(a[0],.07,a[1])]
   ff=[[0,1,2],[0,2,3]]
   if inside:ff=[t[::-1] for t in ff]
   b.add(vv,ff,[[0,0],[1,0],[1,1],[0,1]],None,'wood_dark')


def stocks(b):
 for x in [-.98,.98]:
  b.box((x,0,.08),(.35,.75,.16),'wood_dark',.035)
  log(b,(x,0,.1),(x,0,1.85),.08)
 for cx,hw,hole in [(-.63,.3,.115),(0,.33,.21),(.63,.3,.115)]:ring_board(b,cx,1.5,hw,.32,hole)
 for x in [-.86,.86]:
  b.box((x,-.09,1.5),(.065,.04,.6),'metal',.012)
  for z in [1.27,1.73]:bolt(b,(x,-.12,z),r=.027)
 b.beam((-.93,0,.33),(.93,0,.33),.12,.13,'wood_dark')


def chain(b):
 for i in range(6):
  with b.at(trans(0,i*.19,.075)@(rx(PI/2) if i%2 else np.eye(4))@scale(.75,1.25,1)):
   b.torus((0,0,0),.11,.022,'metal',segments=18,sides=6)


def target(b):
 for x in [-.35,.35]:b.beam((x,-.22,0),(0,0,1.2),.085,.085,'wood_dark')
 b.beam((0,.45,0),(0,0,1.2),.08,.08,'wood_dark')
 with b.at(trans(0,0,1.35)@rx(PI/2)):
  b.lathe([(-.05,.48),(.05,.48)],'wood_pale',24)
  b.lathe([(.052,.4),(.055,.4)],'canvas',24)
  for radius in [.12,.27,.4]:b.torus((0,0,.061),radius,.022,'red',segments=32,sides=5)
  b.lathe([(.063,.07),(.067,.07)],'red',16)
 # Two visible practice arrows.
 for x,z in [(.1,1.38),(-.18,1.26)]:
  b.cylinder((x,-.05,z),(x+.08,-.6,z+.07),.009,'wood_dark',segments=6)


def banner(b,mat='flag_dark'):
 log(b,(-.7,0,1.45),(.7,0,1.45),.045)
 for x in [-.56,.56]:lash(b,(x,0,1.43),.055,axis='x',turns=2,height=.05)
 b.surface(lambda u,v:((u-.5)*1.1,.045*math.sin(u*8+v*3),.1+v*1.3+.07*math.sin(u*19)*(1-v)),16,12,mat)


def bone_ribs(b):
 b.tube([(0,-1.2,.1),(0,-.7,.12),(0,0,.14),(0,.7,.1),(0,1.2,.08)],.095,'bone',8)
 for j,y in enumerate(np.linspace(-.95,.95,6)):
  size=.72+.17*math.sin(j/5*PI)
  for side in [-1,1]:
   path=[]
   for t in np.linspace(0,PI*.72,14):
    path.append((side*size*math.sin(t),y,.12+size*(1-math.cos(t))))
   rad=np.linspace(.073,.025,len(path));b.tube(path,rad,'bone',7)


def skull(b):
 # Stylised cranial shell, recessed dark sockets and separated teeth.
 b.sphere((0,.03,.28),.27,'bone',20,12,squash=(1,.8,.94))
 b.sphere((0,-.04,.16),.19,'bone',16,10,squash=(.88,.82,.66))
 for x in [-.105,.105]:
  b.sphere((x,-.193,.29),.075,'black',14,8,squash=(1,.24,.95))
  b.tube([(x-.07,-.19,.32),(x-.05,-.22,.36),(x+.02,-.22,.37),(x+.065,-.19,.33)],.024,'bone',6)
 with b.at(trans(0,-.215,.19)@rx(PI/2)):
  b.extrude([(-.03,0),(.03,0),(0,.055)],.015,'black')
 for x in [-.09,-.045,0,.045,.09]:b.box((x,-.12,.075),(.036,.09,.08),'bone',.014)


def rock(b,r=1,h=1,seed=1):
 rng=np.random.default_rng(seed);pts=[]
 for z,rr in [(0,.67),(.13,.9),(.6,1),(.95,.5)]:
  for j in range(8):
   t=TAU*j/8+.12*z;v=rr*r*rng.uniform(.88,1.13);pts.append((v*math.cos(t),v*math.sin(t),z*h))
 v=np.array(pts);hull=ConvexHull(v);f=hull.simplices.copy()
 for i,t in enumerate(f):
  if np.dot(np.cross(v[t[1]]-v[t[0]],v[t[2]]-v[t[0]]),v[t].mean(0)-v.mean(0))<0:f[i]=t[::-1]
 uv=np.column_stack([(v[:,0]-v[:,0].min())/np.ptp(v[:,0]),v[:,2]/max(h,.001)])
 b.add(v,f,uv,None,'stone')


def rock_cluster(b):
 use(b,rock,(0,.15,0),r=.72,h=1.35,seed=7)
 use(b,rock,(-.55,-.23,0),r=.52,h=.57,seed=4)
 use(b,rock,(.57,-.18,0),r=.4,h=.7,seed=14)


def palm(b):
 path=[(0,0,0),(.04,0,.6),(.13,.03,1.2),(.25,.07,1.9),(.36,.08,2.55),(.42,.08,3.1)]
 b.tube(path,np.linspace(.18,.105,len(path)),'wood_dark',10)
 for z in np.linspace(.2,2.9,12):
  x=np.interp(z,[p[2] for p in path],[p[0] for p in path]);y=np.interp(z,[p[2] for p in path],[p[1] for p in path]);r=.18-z*.024
  b.torus((x,y,z),r,.018,'wood',segments=12,sides=5)
 crown=np.array(path[-1]);b.sphere(crown,.21,'leaf',12,8,squash=(1,1,.7))
 for j in range(10):
  angle=TAU*j/10;L=1.75+.25*math.sin(j*2.4);e=np.array([math.cos(angle),math.sin(angle),0]);cross=np.array([-e[1],e[0],0])
  def leaf(u,v,e=e,cross=cross,L=L):
   width=.26*math.sin(PI*v)**.65*(1+.13*math.sin(v*PI*24))
   p=crown+e*(L*v)+cross*((u-.5)*2*width)
   p[2]+=.47*math.sin(PI*v)-.74*v*v-.09*abs(u-.5)*math.sin(PI*v)
   return p
  b.surface(leaf,4,24,'leaf' if j%3 else 'leaf_light')
  mid=[leaf(.5,v) for v in np.linspace(0,1,22)];b.tube(mid,np.linspace(.027,.009,22),'leaf_light',5)
 for j in range(3):b.sphere(crown+np.array([.13*math.cos(j*2),.13*math.sin(j*2),-.15]),.11,'wood',12,8)


def grass(b):
 for j in range(13):
  t=TAU*j/13;h=.23+.17*(.5+.5*math.sin(j*1.7));rad=.14*(j%3)/2
  base=np.array([rad*math.cos(t),rad*math.sin(t),0])
  def blade(u,v,t=t,h=h,base=base):
   side=np.array([-math.sin(t),math.cos(t),0]);forward=np.array([math.cos(t),math.sin(t),0])
   return base+side*((u-.5)*.065*(1-v))+forward*(.2*v*v)+np.array([0,0,h*v])
  b.surface(blade,2,5,'grass' if j%3 else 'leaf_light')
