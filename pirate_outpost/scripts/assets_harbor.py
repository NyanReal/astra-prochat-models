"""Grid-snapping pier pieces, mooring hardware, cargo crane and small sailboat."""
import math, numpy as np
from meshcore import *
from asset_parts import *
PI=math.pi

def dock_tile(b,kind='straight'):
 # Every tile has identical 2m footprint and deck-plane pivot (z=0).
 # Edge codes are N(+Y), E(+X), S(-Y), W(-X). Open edges are connection sockets.
 connections={'straight':['N','S'],'corner':['N','E'],'t':['N','E','W'],'cross':['N','E','S','W'],'end':['N']}
 openings=connections[kind]
 plank_floor(b,2,2,0,.16,spacing=.22)
 for x in [-.72,.72]:
  b.beam((x,-1,-.24),(x,1,-.24),.16,.2,'wood_dark')
 for y in [-.73,.73]:
  b.beam((-1,y,-.34),(1,y,-.34),.15,.18,'wood_dark')
  for x in [-.74,.74]:
   log(b,(x,y,-1.45),(x,y,-.1),.12,r2=.1)
 for side in ['N','E','S','W']:
  if side in openings:continue
  with b.at(rz({'S':0,'E':PI/2,'N':PI,'W':-PI/2}[side])):
   for x in [-.78,.78]:
    log(b,(x,-.9,-.4),(x,-.9,.7),.09,r2=.085)
    lash(b,(x,-.9,.48),.1,turns=2,height=.08)
   b.tube([(-.78,-.9,.49),(-.39,-.9,.4),(0,-.9,.36),(.39,-.9,.4),(.78,-.9,.49)],.03,'rope',6)
 # Nails and two compact edge clamps are visible on top, kept away from sockets.
 for x in [-.77,.77]:
  for y in [-.67,.67]:bolt(b,(x,y,.008),axis='z',r=.018)


def dock_platform(b):
 plank_floor(b,4,4,0,.17,spacing=.23)
 for x in [-1.6,0,1.6]:
  b.beam((x,-2,-.26),(x,2,-.26),.18,.24,'wood_dark')
  for y in [-1.6,0,1.6]:log(b,(x,y,-1.5),(x,y,-.12),.14,r2=.12)
 for y in [-1.7,1.7]:
  b.beam((-2,y,-.37),(2,y,-.37),.17,.2)
 for x,y in [(-1.85,-1.85),(1.85,-1.85),(-1.85,1.85),(1.85,1.85)]:
  log(b,(x,y,-.3),(x,y,.55),.11);lash(b,(x,y,.37),.12,turns=3,height=.1)


def dock_stairs(b):
 # Upper edge at local y=0,z=0. Lower landing extends toward -Y.
 n=6;run=2.;rise=1.
 for k in range(n):
  y=-(k+.5)*run/n;z=-k*rise/n
  b.box((0,y,z-.07),(1.6,run/n+.035,.14),'wood',.026)
 for x in [-.64,.64]:b.beam((x,.02,-.15),(x,-run,-rise-.15),.13,.17,'wood_dark')
 for x in [-.77,.77]:
  for y,z in [(0,0),(-run,-rise)]:
   log(b,(x,y,z-.1),(x,y,z+.75),.075)
   lash(b,(x,y,z+.52),.085,turns=2,height=.08)
  b.tube([(x,0,.54),(x,-1,-.04),(x,-2,-.46)],.026,'rope',6)


def gangway(b):
 for i in range(10):
  y=-1+(i+.5)*.2;z=.14*(y+1)
  b.box((0,y,z-.065),(1.6,.187,.13),'wood' if i%3 else 'wood_pale',.022)
 for x in [-.63,.63]:b.beam((x,-1,-.12),(x,1,.16),.12,.16,'wood_dark')
 for x in [-.76,.76]:
  for y in [-.94,.94]:
   z=.14*(y+1);log(b,(x,y,z-.1),(x,y,z+.68),.07)
   lash(b,(x,y,z+.48),.08,turns=2,height=.07)
  b.tube([(x,-.94,.49),(x,0,.48),(x,.94,.75)],.027,'rope',6)


def rope_rail(b):
 for x in [-.88,.88]:
  log(b,(x,0,0),(x,0,1),.09)
  lash(b,(x,0,.76),.105,turns=3,height=.11)
 b.tube([(-.88,0,.8),(-.44,0,.66),(0,0,.6),(.44,0,.66),(.88,0,.8)],.032,'rope',6)


def bollard(b):
 b.box((0,0,.055),(.62,.59,.11),'metal',.06)
 b.lathe([(.1,.2),(.14,.22),(.47,.18),(.5,.27),(.58,.27),(.61,.22)],'wood_dark',16)
 b.lathe([(.47,.275),(.59,.275)],'metal',16,False)
 lash(b,(0,0,.25),.23,turns=3,height=.13)
 for x in [-.24,.24]:
  for y in [-.22,.22]:bolt(b,(x,y,.11),'z',.025)


def rope_coil(b):
 ts=np.linspace(0,TAU*3.7,150)
 path=[]
 for t in ts:
  r=.18+.024*t/TAU;path.append((r*math.cos(t),r*math.sin(t),.035+.013*t/TAU))
 b.tube(path,.027,'rope',7)
 b.tube([path[-1],(.33,-.14,.06),(.48,-.21,.03),(.56,-.15,.03)],.027,'rope',7)


def winch(b):
 for x in [-.58,.58]:
  b.box((x,0,.065),(.35,.7,.13),'wood_dark',.035)
  b.beam((x,-.25,.12),(x,0,.8),.13,.15)
  b.beam((x,.25,.12),(x,0,.8),.13,.15)
 b.cylinder((-.8,0,.7),(.8,0,.7),.075,'metal',segments=12)
 with b.at(trans(-.4,0,.7)@ry(PI/2)):
  b.lathe([(0,.24),(.8,.24)],'wood',16)
  for z in [0,.8]:b.lathe([(z-.04,.32),(z+.04,.32)],'metal',16)
  ts=np.linspace(0,TAU*8,140)
  b.tube([(.265*math.cos(t),.265*math.sin(t),.07+.66*t/(TAU*8)) for t in ts],.035,'rope',6)
 b.beam((.82,0,.7),(.82,0,1.06),.055,.055,'metal',.012)
 b.cylinder((.8,0,1.06),(1.05,0,1.06),.043,'wood',segments=10)


def loading_crane(b):
 plank_floor(b,1.6,1.45,.16,.16)
 for x in [-.6,.6]:
  for y in [-.5,.5]:bolt(b,(x,y,.17),'z',.035)
 b.box((0,0,.28),(.58,.58,.25),'metal',.06)
 b.beam((0,0,.2),(0,0,3.3),.29,.3,'wood',.055)
 b.beam((-.43,0,3.23),(2.1,0,3.23),.28,.27,'wood',.045)
 b.beam((.06,0,1.65),(1.51,0,3.12),.18,.17,'wood_dark',.03)
 for z in [.55,2.8]:
  b.box((0,0,z),(.32,.34,.16),'metal',.025)
  bolt(b,(0,-.18,z),r=.045)
 for x in [.0,1.6,2.0]:bolt(b,(x,-.15,3.22),r=.04)
 with b.at(trans(1.85,0,3.08)@rx(PI/2)):
  b.lathe([(-.045,.13),(.045,.13)],'metal',16)
 b.tube([(0,-.2,.85),(.18,-.2,2.7),(1.85,-.04,3.19),(1.91,0,2.85),(1.91,0,1.8)],.022,'rope',6)
 # Open hook, separate from a cargo bundle so the prop remains reusable.
 ts=np.linspace(-PI/2,PI*1.2,16)
 b.tube([(1.91+.12*math.cos(t),0,1.66+.14*math.sin(t)) for t in ts],.027,'metal',7)
 with b.at(trans(-.38,-.2,.53)@scale(.63)):winch(b)


def cargo_net(b):
 use(b,crate,(-.12,.03,.02),s=.76)
 use(b,sack,(.26,-.13,.06),s=.73)
 # Cargo net encloses the bundle with real crossing ropes and a gathered top loop.
 h=1.2
 def radius(z):return .52*(1-(max(z-.55,0)/.68)**1.2) if z>.55 else .5
 for j in range(10):
  a=TAU*j/10;path=[]
  for z in np.linspace(.04,1.16,18):
   r=max(.035,radius(z));path.append((r*math.cos(a),r*math.sin(a),z))
  b.tube(path,.022,'rope',5)
 for z in [.14,.34,.54,.74,.92]:
  rr=max(.05,radius(z));b.torus((0,0,z),rr,.022,'rope',segments=24,sides=5)
 b.torus((0,0,1.25),.085,.025,'rope','y',16,5)


def floating_platform(b):
 for x in [-.85,0,.85]:
  with b.at(trans(x,.85,.3)@rx(PI/2)):
   b.lathe([(0,.22),(.14,.28),(.85,.31),(1.56,.28),(1.7,.22)],'wood_dark',14)
   for z in [.25,1.45]:b.lathe([(z-.05,.29),(z+.05,.29)],'metal',14,False)
 with b.at(trans(0,0,.83)):plank_floor(b,2.6,2.05,0,.14)
 for x in [-1.12,1.12]:
  for y in [-.84,.84]:
   log(b,(x,y,.6),(x,y,1.32),.075)
   lash(b,(x,y,1.12),.09,turns=2,height=.07)
 for y in [-.84,.84]:b.tube([(-1.12,y,1.14),(0,y,1.0),(1.12,y,1.14)],.027,'rope',6)


def sailboat(b):
 # Open hull: longitudinal stations and a U-shaped transverse section.
 L=4.7
 def hull(u,v,inner=False):
  y=(u-.5)*L;theta=(v-.5)*PI
  beam=(.05+.97*math.sin(PI*u)**.62)
  top=1.05+.28*(abs(2*u-1)**3)
  depth=.89 if not inner else .78
  x=(beam-(.065 if inner else 0))*math.sin(theta)
  z=top-depth*math.cos(theta)
  return x,y,z
 b.surface(lambda u,v:hull(u,v),20,12,'wood',True)
 b.surface(lambda u,v:hull(u,v,True),20,12,'wood_dark')
 for side in [0,1]:
  path=[hull(u,side) for u in np.linspace(0,1,28)]
  b.tube(path,.065,'wood_pale',7)
 # Fine wale follows the hull rather than floating as a straight beam.
 for side in [.16,.84]:
  b.tube([hull(u,side) for u in np.linspace(.025,.975,26)],.035,'metal',6)
 for i in range(18):
  y=-2.05+(i+.5)*4.1/18;u=y/L+.5;half=.84*math.sin(PI*u)**.65
  b.box((0,y,.62),(max(.18,half*2),4.1/18-.014,.07),'wood_pale' if i%4==0 else 'wood',.015)
 # Seats, mast, yard and curved sail.
 for y in [-1.2,.9]:
  half=.88*math.sin(PI*(y/L+.5))**.65
  b.box((0,y,.93),(2*half,.3,.085),'wood_dark',.02)
 log(b,(0,.0,.45),(0,0,4.35),.085,r2=.055)
 log(b,(-1.28,0,3.91),(1.28,0,3.91),.055)
 log(b,(-1.06,0,1.75),(1.06,0,1.75),.05)
 def sail(u,v):
  width=2.14+.3*v
  x=(u-.5)*width;y=-.32*math.sin(PI*u)*math.sin(PI*v)
  z=1.78+2.13*v+.1*math.sin(PI*u)*(1-v)
  return x,y,z
 b.surface(sail,16,16,'flag_cream')
 for x in [-1,1]:b.tube([(x*1.23,0,3.9),(x*.85,.05,2.8),(x*.72,.35,1.03)],.022,'rope',5)
 b.tube([(0,0,4.2),(0,-1.3,2.5),(0,-2.1,1.28)],.022,'rope',5)
 b.tube([(0,0,4.2),(0,1.1,2.6),(0,2.1,1.25)],.022,'rope',5)
 with b.at(trans(.03,0,4.12)@scale(.42)):flag_cloth(b,1.2,.65,'cloth_red')
 # Stern rudder, tiller and one compact mooring ring.
 b.box((0,2.32,.49),(.12,.5,.85),'wood_dark',.035)
 b.beam((0,2.27,1.1),(0,1.65,1.3),.065,.065)
 b.torus((0,-2.35,1.15),.075,.018,'metal','y',16,5)
