import math,numpy as np
from meshcore import *
from asset_parts import *
PI=math.pi

def palisade(b):
 for i in range(8):
  x=-.875+i*.25;h=2.1+[.06,-.03,.02,.1,-.02,.04,-.01,.07][i]
  with b.at(trans(x,0,0)):
   b.lathe([(0,.12),(.1,.125),(h-.32,.125),(h-.04,.035),(h,.027)],'wood' if i%3 else 'wood_pale',8)
 for z in [.5,1.47]:
  b.box((0,-.15,z),(2.,.12,.15),'wood_dark',.025)
  for x in [-.75,-.25,.25,.75]:bolt(b,(x,-.22,z),r=.027)


def gate_doors(b,opened=False,w=3.35,h=2.34):
 for side in [-1,1]:
  hinge=side*w/2;angle=-side*math.radians(78 if opened else 0)
  with b.at(trans(hinge,0,0)@rz(angle)):
   for i in range(7):
    x=-side*(i+.5)*(w/2)/7
    top=h-.13*(i/6)**2
    b.box((x,0,top/2),((w/2)/7-.012,.14,top),'wood' if i%3 else 'wood_pale',.025)
   for z in [.38,h-.38]:
    b.box((-side*w/4,-.095,z),(w/2-.08,.055,.11),'metal',.018)
    for i in [1,3,5]:bolt(b,(-side*(i+.5)*(w/2)/7,-.13,z),r=.025)
   b.torus((-side*(w/2-.23),-.17,1.08),.11,.022,'metal','y',20,6)


def wooden_gate(b,opened=False):
 for x in [-1.87,1.87]:
  log(b,(x,0,0),(x,0,2.83),.18)
  b.box((x,0,.12),(.58,.56,.24),'stone',.075)
  lash(b,(x,0,2.5),.2)
 path=[(x,0,2.56+.33*math.cos((x/1.95)*PI/2)) for x in np.linspace(-1.95,1.95,9)]
 b.tube(path,.16,'wood',8)
 gate_doors(b,opened)


def stone_gate(b,opened=True):
 for x in [-2.03,2.03]:
  for k in range(8):
   z=.19+k*.36
   b.box((x,0,z),(.82,.9,.34),'stone' if k%3 else 'stone_dark',.065)
  b.box((x,0,2.98),(1.02,1.08,.22),'stone_dark',.055)
  with b.at(trans(x,0,3.09)@scale(.55)):torch(b,tripod=False)
 # Voussoirs form a real arch opening.
 for k in range(13):
  a=PI*k/13;c=PI*(k+1)/13
  p=[(1.63*math.cos(a),1.63*math.sin(a)),(1.94*math.cos(a),1.94*math.sin(a)),(1.94*math.cos(c),1.94*math.sin(c)),(1.63*math.cos(c),1.63*math.sin(c))]
  with b.at(trans(0,0,1.63)@rx(PI/2)):b.extrude(p,.66,'stone' if k%3 else 'stone_dark')
 gate_doors(b,opened,w=3.15,h=2.34)
 with b.at(trans(0,-.39,3.07)):
  b.surface(lambda u,v:((u-.5)*.95,.025*math.sin(u*5),.75*(v-.5)),8,6,'flag_dark')


def barricade(b):
 b.beam((-1.35,0,.67),(1.35,0,.67),.18,.18,'wood_dark')
 for x in [-.95,0,.95]:
  for side in [-1,1]:
   a=(x,-side*.45,.02);c=(x,side*.38,1.55)
   log(b,a,c,.1,r2=.035)
  lash(b,(x,0,.7),.14,axis='x')


def cannon(b):
 for x in [-.43,.43]:
  # Carriage cheek profile extruded in its local thickness direction.
  poly=[(-.85,.27),(.68,.27),(.7,.72),(.2,.85),(-.45,.7),(-.85,.43)]
  with b.at(trans(x,0,0)@rz(PI/2)@rx(PI/2)):
   b.extrude(poly,.2,'wood')
 for y in [-.55,.55]:
  b.cylinder((-.85,y,.3),(.85,y,.3),.07,'metal',segments=10)
  for x in [-.67,.67]:
   with b.at(trans(x,y,.3)@ry(PI/2)):
    b.lathe([(-.07,.26),(-.05,.3),(.05,.3),(.07,.26)],'wood_dark',16)
    b.lathe([(-.08,.1),(.08,.1)],'metal',12)
    for t in np.linspace(0,TAU,8,endpoint=False):
     b.beam((.08*math.cos(t),.08*math.sin(t),.081),(.24*math.cos(t),.24*math.sin(t),.081),.045,.035,'wood_pale',.01)
 b.beam((-.48,-.55,.42),(.48,-.55,.42),.18,.16,'wood_dark')
 b.beam((-.48,.55,.42),(.48,.55,.42),.18,.16,'wood_dark')
 # Full hollow muzzle and inset bore, with trunnions resting in the carriage.
 with b.at(trans(0,.55,.92)@rx(PI/2-.12)):
  b.lathe([(0,.18),(.06,.25),(.23,.28),(.55,.27),(1.38,.21),(1.49,.26),(1.6,.26),(1.64,.23),(1.64,.155),(1.35,.145),(1.28,0)],'metal',24,False)
  for z,r in [(.26,.29),(.6,.28),(1.46,.245)]:b.lathe([(z-.025,r),(z+.025,r)],'metal',24,False)
  b.sphere((0,0,-.065),.11,'metal',12,8)
 b.cylinder((-.5,.05,.96),(.5,.05,.96),.095,'metal',segments=12)
