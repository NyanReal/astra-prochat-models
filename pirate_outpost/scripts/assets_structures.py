"""Readable structural meshes: timber joints, plank walls, braces and cloth roofs."""
import math, numpy as np
from meshcore import *
from asset_parts import *
PI=math.pi

def watchtower(b):
 # Splayed bearing posts and actual cross bracing.
 for sx in [-1,1]:
  for sy in [-1,1]:
   b.box((sx*1.05,sy*1.05,.13),(.52,.5,.26),'stone',.08)
   log(b,(sx*1.05,sy*1.05,.2),(sx*.88,sy*.88,3.48),.16,r2=.14)
   for z in [.55,2.65]:
    t=(z-.2)/3.28;p=(sx*(1.05-.17*t),sy*(1.05-.17*t),z)
    with b.at(trans(*p)):b.lathe([(-.09,.174),(.09,.174)],'metal',12,False)
 for sy in [-1,1]:
  b.beam((-.97,sy*.97,.65),(.91,sy*.91,2.95),.16,.14,'wood_dark',.035)
  b.beam((.97,sy*.97,.65),(-.91,sy*.91,2.95),.16,.14,'wood',.035)
 for sx in [-1,1]:
  b.beam((sx*.97,-.97,.65),(sx*.91,.91,2.95),.16,.14,'wood',.035)
 for y in [-.9,.9]:b.beam((-1.4,y,3.2),(1.4,y,3.2),.2,.23,'wood_dark')
 plank_floor(b,2.72,2.72,3.49,.18)
 for x in [-1.26,1.26]:
  for y in [-1.26,1.26]:
   log(b,(x,y,3.42),(x,y,5.2),.115)
   lash(b,(x,y,4.14),.13);lash(b,(x,y,5.04),.14)
 for y in [-1.28,1.28]:
  log(b,(-1.4,y,4.13),(1.4,y,4.13),.085)
  for x in [-.9,-.45,0,.45,.9]:
   if y<0 and abs(x)<.5:continue
   log(b,(x,y,3.52),(x,y,4.12),.045)
 for x in [-1.28,1.28]:
  log(b,(x,-1.4,4.13),(x,1.4,4.13),.085)
  for y in [-.9,-.45,0,.45,.9]:log(b,(x,y,3.52),(x,y,4.12),.045)
 # Hipped canvas roof: four curved panels, no unconnected floating awning.
 corners=[(-1.62,-1.62),(1.62,-1.62),(1.62,1.62),(-1.62,1.62)]
 for k in range(4):
  a=np.array(corners[k]);c=np.array(corners[(k+1)%4])
  def panel(u,v,a=a,c=c):
   xy=(a*(1-u)+c*u)*(1-v*.98)
   z=5.14+.9*v-.09*math.sin(PI*u)*(1-v)
   return xy[0],xy[1],z
  b.surface(panel,10,6,'cloth_red' if k%2==0 else 'canvas')
  log(b,(*a,5.15),(*c,5.15),.085)
 log(b,(0,0,4.9),(0,0,6.78),.07,r2=.05)
 b.sphere((0,0,6.79),.085,'wood',12,7)
 with b.at(trans(.04,0,6.38)):flag_cloth(b,1.05,.63)
 # Long exterior ladder; leaves the entry gap in the guardrail clear.
 for x in [-.36,.36]:log(b,(x,-1.95,.06),(x,-1.29,3.68),.06)
 for i in range(11):
  z=.22+i*.315;y=-1.95+(z/3.68)*.66
  log(b,(-.36,y,z),(.36,y,z),.045,'wood_pale')
 log(b,(-1.26,-1.26,4.76),(-.7,-1.26,4.76),.045)
 use(b,lantern,(-.78,-1.27,4.08),s=.85)


def wall_planks(b,w,h,y,zbase=.2,window=False,door=False):
 n=round(w/.22);pw=w/n
 for i in range(n):
  x=-w/2+(i+.5)*pw
  ranges=[(zbase,h)]
  if door and abs(x)<.48:ranges=[(2.2,h)]
  if window and -1.48<x<-.78:ranges=[(zbase,1.15),(1.9,h)]
  for z0,z1 in ranges:
   if z1>z0:b.box((x,y,(z0+z1)/2),(pw-.012,.1,z1-z0),'wood_teal' if i%4 else 'wood_dark',.018)


def command_hut(b):
 plank_floor(b,4.2,3.5,.24,.18)
 wall_planks(b,3.9,2.8,-1.62,window=True,door=True)
 wall_planks(b,3.9,2.8,1.62)
 for x in [-1.95,1.95]:
  with b.at(trans(x,0,0)@rz(PI/2)):wall_planks(b,3.25,2.8,0)
 for x in [-1.97,1.97]:
  for y in [-1.65,1.65]:
   log(b,(x,y,.1),(x,y,2.88),.12)
   lash(b,(x,y,.58),.13);lash(b,(x,y,2.64),.13)
 for y in [-1.7,1.7]:
  b.beam((-2.02,y,.64),(2.02,y,.64),.12,.16,'wood_dark')
  b.beam((-2.02,y,2.74),(2.02,y,2.74),.13,.16)
 # Gable ends, vertically boarded to the sloping roofline.
 for y in [-1.62,1.62]:
  for i in range(17):
   x=-1.86+i*.2325;zt=3.98-abs(x)/2.1*1.2
   if zt>2.75:b.box((x,y,(zt+2.75)/2),(.22,.1,zt-2.75),'wood_teal',.018)
 roof_gable(b,4.65,4.05,2.82,1.22,'wood_red')
 # Closed planked door and brass ring pull.
 for i in range(5):b.box((-.4+i*.2,-1.7,1.24),(.19,.1,1.96),'wood_dark',.02)
 for z in [.45,1.95]:b.box((0,-1.77,z),(.94,.055,.09),'metal',.018)
 b.torus((.28,-1.83,1.22),.065,.014,'gold','y',16,5)
 for x in [-.56,.56]:b.box((x,-1.78,1.27),(.13,.16,2.18),'wood_pale',.025)
 b.box((0,-1.78,2.34),(1.25,.16,.13),'wood_pale')
 # Actual recessed window, shutter and sill.
 b.box((-1.15,-1.59,1.53),(.72,.03,.78),'black',.01)
 for x in [-1.52,-.78]:b.box((x,-1.76,1.53),(.08,.13,.86),'wood_pale',.02)
 for z in [1.1,1.95]:b.box((-1.15,-1.79,z),(.91,.22,.09),'wood_pale',.02)
 b.box((-1.15,-1.78,1.52),(.05,.08,.8),'wood',.012)
 b.box((-1.15,-1.78,1.52),(.7,.08,.05),'wood',.012)
 with b.at(trans(-1.7,-1.76,1.5)@rz(-.25)):
  b.box((0,0,0),(.28,.07,.8),'wood_teal',.016)
 # Porch with two posts, short stairs and curved sail awning.
 with b.at(trans(0,-2.2,0)):plank_floor(b,3.65,1.15,.29,.14)
 for x in [-1.65,1.65]:
  log(b,(x,-2.72,.28),(x,-2.72,2.43),.095)
  lash(b,(x,-2.72,2.27),.11)
  b.beam((x,-2.72,1.95),(x,-2.24,2.43),.085,.085)
 def aw(u,v):return ((u-.5)*3.9,-1.73-v*1.2,2.64-.27*v-.16*math.sin(PI*u)*math.sin(PI*v))
 b.surface(aw,14,8,'canvas',True)
 log(b,(-1.93,-2.93,2.37),(1.93,-2.93,2.37),.075)
 for i in range(3):
  b.box((0,-2.9-.22*i,.24-.08*i),(1.6,.32,.16),'wood',.035)
 # Front hanging emblem; fittings are geometry, insignia comes from the generated image.
 with b.at(trans(.95,-1.84,2.09)):
  b.surface(lambda u,v:((u-.5)*.55,0,(v-.5)*.5),1,1,'flag_dark')
 use(b,lantern,(.9,-2.7,1.72),s=.8)


def supply_shed(b):
 plank_floor(b,3.5,2.6,.14,.14)
 for x in [-1.56,1.56]:
  for y in [-1.15,1.15]:
   log(b,(x,y,0),(x,y,2.5),.13)
   lash(b,(x,y,2.24),.15)
 for i in range(14):
  x=-1.5+i*3/13;b.box((x,1.16,.96),(.22,.1,1.65),'wood',.02)
 for x in [-1.55,1.55]:
  for i in range(10):b.box((x,-1.05+i*.23,.62),(.1,.21,1.0),'wood_dark' if i%4==0 else 'wood',.018)
 for y in [-1.2,1.2]:log(b,(-1.75,y,2.38),(1.75,y,2.38),.1)
 roof_gable(b,3.95,3.05,2.48,.74,'canvas',True)
 # Decorative teal repair strip on the sail.
 b.surface(lambda u,v:(.2+u*.28,(v-.5)*2.98,3.22-(.2+u*.28)/1.975*.74+.012),2,10,'wood_teal')
 for x in [-1.55,1.55]:
  b.beam((x,-1.15,1.9),(x,-.6,2.42),.09,.09)


def rest_canopy(b):
 for x in [-1.4,1.4]:
  for y in [-1.15,1.15]:
   log(b,(x,y,0),(x,y,2.46),.08)
   lash(b,(x,y,2.28),.1,turns=2)
 for y in [-1.18,1.18]:log(b,(-1.6,y,2.43),(1.6,y,2.43),.07)
 def surface(u,v):
  return ((u-.5)*3.3,(v-.5)*2.8,2.53-.22*math.sin(PI*u)*math.sin(PI*v)+.08*math.sin(v*PI))
 b.surface(surface,16,14,'canvas')
 for sy in [-1,1]:
  b.surface(lambda u,v,sy=sy:((u-.5)*3.3,sy*1.4,2.5-.22*v-.06*math.sin(u*6*PI)*v),18,3,'cloth_red')


def pirate_tent(b):
 # A circular, sailcloth tent with a genuinely open front entrance.
 profiles=np.array([[0,1.52],[.3,1.68],[1.0,1.5],[1.85,.95],[2.6,.12]])
 for j in range(12):
  a=TAU*j/12;c=TAU*(j+1)/12
  # Front entrance centered on -Y; omit lower sections of the front two panels.
  front=j in (8,9)
  def fn(u,v,a=a,c=c,front=front):
   q=(.66+v*.34) if front else v
   z=np.interp(q,np.linspace(0,1,5),profiles[:,0]);r=np.interp(q,np.linspace(0,1,5),profiles[:,1])
   t=a+(c-a)*u;r+=.045*math.sin(PI*u)*math.sin(PI*v)
   return (r*math.cos(t),r*math.sin(t),z)
  b.surface(fn,4,10,'cloth_red' if j%3==0 else 'canvas',True)
  path=[]
  for z,r in profiles:path.append((r*math.cos(a),r*math.sin(a),z))
  b.tube(path,.018,'rope',5)
 log(b,(0,0,0),(0,0,2.8),.07)
 b.sphere((0,0,2.82),.09,'wood',12,7)
 # Recessed front flaps, tied to either side of the doorway.
 for s in [-1,1]:
  b.surface(lambda u,v,s=s:(s*(.72+.22*u-.18*v),-1.26+.18*v+.12*math.sin(PI*u),.07+1.52*v),5,8,'cloth_red' if s<0 else 'canvas')
  lash(b,(s*.78,-1.26,.72),.07,axis='x',turns=2,height=.06)
 with b.at(trans(0,-1.12,1.78)):
  b.surface(lambda u,v:((u-.5)*1.26,.13*v,(v-.5)*.68),8,4,'flag_cream')
 for t in [.1,2.6,3.65,5.85]:
  p=(2.04*math.cos(t),2.04*math.sin(t),0)
  log(b,p,(p[0]+.06,p[1]+.02,.35),.045)
  b.tube([(1.3*math.cos(t),1.3*math.sin(t),1.3),(1.8*math.cos(t),1.8*math.sin(t),.52),(p[0],p[1],.2)],.022,'rope',5)


def anvil(b):
 b.lathe([(0,.24),(.5,.21)],'wood_dark',12)
 for z in [.1,.41]:b.lathe([(z-.025,.235),(z+.025,.235)],'metal',12,False)
 b.box((0,0,.54),(.62,.4,.12),'metal',.04)
 b.box((-.04,0,.72),(.34,.24,.3),'metal',.035)
 b.box((0,0,.89),(.66,.35,.12),'metal',.035)
 b.cylinder((.3,0,.88),(.72,0,.86),.13,'metal',r2=.02,segments=10)
 b.box((-.37,0,.87),(.16,.34,.14),'metal',.02)


def forge(b):
 # A lean-to workshop with a visible masonry firebox and chimney.
 for x in [-1.6,1.6]:
  for y in [-1.2,1.2]:log(b,(x,y,0),(x,y,2.6),.13)
 for i in range(12):b.box((-1.49+i*.27,1.19,1.1),(.25,.12,2.0),'wood_teal',.025)
 roof_gable(b,3.85,2.95,2.62,.8,'wood_red')
 for x in [-1.6,1.6]:
  b.beam((x,-1.25,2.0),(x,-.7,2.6),.12,.12)
  lash(b,(x,-1.2,2.43),.15)
 # Furnace at the right; leave the front opening as negative space.
 for x in [.55,1.7]:
  for z in [.2,.55,.9]:b.box((x,.0,z),(.42,1.1,.34),'stone',.05)
 b.box((1.12,.48,.65),(1.05,.24,1.3),'stone_dark',.04)
 b.box((1.12,0,.08),(1.5,1.25,.16),'stone',.04)
 for j in range(9):
  a=PI*j/9;c=PI*(j+1)/9
  p=[(.42*math.cos(a),.42*math.sin(a)),(.68*math.cos(a),.68*math.sin(a)),(.68*math.cos(c),.68*math.sin(c)),(.42*math.cos(c),.42*math.sin(c))]
  with b.at(trans(1.12,-.5,.98)@rx(PI/2)):b.extrude(p,.5,'stone' if j%3 else 'stone_dark')
 b.box((1.12,.05,1.65),(1.3,1.14,.35),'stone',.06)
 for k in range(8):
  z=1.98+.27*k
  b.box((1.12,.25,z),(.73+(.05 if k%3==0 else 0),.71,.25),'stone' if k%3 else 'stone_dark',.045)
 b.box((1.12,.25,4.12),(.95,.93,.17),'stone_dark',.04)
 b.box((1.12,.25,4.21),(.57,.55,.025),'black',.005)
 use(b,flame,(1.12,-.12,.19),s=1.3,h=.51)
 for i in range(5):b.sphere((.83+i*.14,-.23,.16),.09,'coal',10,6)
 use(b,anvil,(-.75,-.75,0),yaw=-10)
 # Hanging forge sign.
 with b.at(trans(-1.1,-1.5,1.6)):
  b.surface(lambda u,v:((u-.5)*.58,0,(v-.5)*.75),2,2,'flag_dark')
