"""Reusable hand-authored construction details used across the asset library."""
import math, numpy as np
from meshcore import *
PI=math.pi

def use(b,fn,pos=(0,0,0),yaw=0,s=1,**kw):
 with b.at(trans(*pos)@rz(math.radians(yaw))@scale(s)):
  fn(b,**kw)

def bolt(b,p,axis='y',r=.025,metal='metal'):
 m=trans(*p)
 if axis=='y':m=m@rx(PI/2)
 if axis=='x':m=m@ry(PI/2)
 with b.at(m):b.lathe([(-.008,r*.8),(0,r),(.018,r*.85)],metal,6)

def lash(b,p,r=.14,axis='z',turns=3,height=.17):
 m=trans(*p)
 if axis=='x':m=m@ry(PI/2)
 if axis=='y':m=m@rx(PI/2)
 with b.at(m):
  ts=np.linspace(0,TAU*turns,turns*16+1)
  b.tube([(r*math.cos(t),r*math.sin(t),height*(t/(TAU*turns)-.5)) for t in ts],.027,'rope',5)
  b.sphere((0,-r-.025,0),.053,'rope',10,6,squash=(1,.7,.8))

def plank_floor(b,w,d,z=0,thickness=.13,mat='wood',spacing=.24):
 count=max(2,round(w/spacing));pw=w/count
 for i in range(count):
  b.box((-w/2+pw*(i+.5),0,z-thickness/2),(pw-.012,d,thickness),mat if i%4 else 'wood_pale',.022)

def log(b,a,c,r=.12,mat='wood',r2=None):b.cylinder(a,c,r,mat,r2,12)

def barrel(b,h=.9,r=.34):
 profiles=[(0,r*.82),(.06*h,r*.86),(.23*h,r*.98),(.5*h,r*1.05),(.77*h,r*.98),(.94*h,r*.86),(h,r*.82)]
 for i in range(14):
  a=TAU*i/14+.012;c=TAU*(i+1)/14-.012
  b.lathe(profiles,['wood','wood_pale','wood','wood_dark'][i%4],2,True,a,c)
 for z in [h*.17,h*.83]:
  rr=r*(.82+.23*math.sin(PI*z/h));t=.035
  b.lathe([(z-.045,rr),(z-.042,rr+t),(z+.042,rr+t),(z+.045,rr)],'metal',20,False)
  for j in range(7):
   t=TAU*j/7
   with b.at(trans((rr+.03)*math.cos(t),(rr+.03)*math.sin(t),z)@rz(t)@ry(PI/2)):
    b.lathe([(0,.015),(.015,.018),(.023,.01)],'silver',6)
 # Individually circle-clipped lid boards sit ABOVE stave end caps.
 # The former inset rectangles exposed pie-shaped cap triangles on the barrel top.
 R=r*.80;ns=5;pw=2*R/ns;circle=[(R*math.cos(t),R*math.sin(t)) for t in np.linspace(0,TAU,48,endpoint=False)]
 def clip(poly,bound,keep_greater):
  result=[]
  for a,c in zip(poly,poly[1:]+poly[:1]):
   ia=a[0]>=bound if keep_greater else a[0]<=bound
   ic=c[0]>=bound if keep_greater else c[0]<=bound
   if ia:result.append(a)
   if ia!=ic:
    t=(bound-a[0])/(c[0]-a[0]);result.append((bound,a[1]+t*(c[1]-a[1])))
  return result
 for i in range(ns):
  left=-R+i*pw+.003;right=-R+(i+1)*pw-.003
  polygon=clip(clip(circle,left,True),right,False)
  with b.at(trans(0,0,h+.022)):b.extrude(polygon,.035,'wood_pale' if i%2 else 'wood')
 b.torus((0,0,h+.013),r*.825,.012,'wood_dark',segments=28,sides=5)
 b.box((0,0,h+.052),(r*1.3,.045,.025),'wood_dark',.009)

def crate(b,w=.9,d=.8,h=.8):
 # Separate boards, bracing and corner hardware instead of a textured solid cube.
 for i in range(5):
  z=(i+.5)*h/5
  for y in [-d/2,d/2]:b.box((0,y,z),(w,.075,h/5-.012),'wood' if i%2 else 'wood_pale',.016)
  for x in [-w/2,w/2]:b.box((x,0,z),(.075,d,h/5-.012),'wood',.016)
 for i in range(5):b.box((-w/2+(i+.5)*w/5,0,h),(w/5-.012,d,.065),'wood_pale',.015)
 b.box((0,0,.04),(w,d,.08),'wood_dark',.015)
 for x in [-w/2,w/2]:
  for y in [-d/2-.04,d/2+.04]:
   b.box((x,y,h/2),(.11,.09,h+.06),'wood_dark',.025)
   for z in [.1,h-.1]:bolt(b,(x,y-.05 if y<0 else y+.05,z),r=.025)
 for y in [-d/2-.08,d/2+.08]:
  b.beam((-w*.41,y,.1),(w*.41,y,h-.1),.1,.06,'wood_pale',.018)
  b.beam((w*.41,y,.1),(-w*.41,y,h-.1),.1,.06,'wood_pale',.018)


def sack(b,h=.7,r=.28):
 profile=[(0,.55),(.04,.88),(.22,1.0),(.55,.95),(.78,.68),(.88,.26),(.96,.25),(1,.38)]
 for j in range(12):
  # Fluted contour creates cloth folds without a normal map.
  a=TAU*j/12;c=TAU*(j+1)/12
  b.lathe([(h*z,r*rr*(1+.035*math.sin(j*2.3))) for z,rr in profile],'canvas',2,True,a,c)
 lash(b,(0,0,h*.89),r*.28,turns=2,height=.045)
 b.tube([(r*.25,0,h*.9),(r*.45,-.04,h*.8),(r*.43,-.06,h*.7)],.018,'rope',5)

def bottle(b,h=.32,mat='green_glass'):
 b.lathe([(0,.065),(.025,.075),(h*.56,.075),(h*.68,.035),(h*.9,.031),(h*.92,.04),(h,.04)],mat,12)
 b.lathe([(h,.032),(h+.025,.032)],'wood_pale',10)
 # Paper band, deliberately no tiny unreadable text.
 b.lathe([(h*.22,.076),(h*.45,.076)],'canvas',12,False)

def lantern(b):
 b.lathe([(0,.13),(.035,.17),(.07,.145),(.1,.13)],'metal',8)
 b.lathe([(.1,.115),(.38,.115)],'glass',8)
 for t in np.linspace(0,TAU,8,endpoint=False):
  p=(.135*math.cos(t),.135*math.sin(t))
  b.cylinder((*p,.075),(*p,.39),.018,'metal',segments=6)
 b.lathe([(.37,.14),(.41,.18),(.46,.11),(.49,.06)],'metal',8)
 b.torus((0,0,.57),.075,.014,'metal','y',16,5)

def flame(b,h=.5):
 for k,(dx,dy,s,mat) in enumerate([(-.1,0,.8,'orange'),(.1,.03,.72,'amber'),(0,-.04,1,'yellow')]):
  prof=[(0,.12),(.15,.15),(.35,.1),(.6,.07),(.9,.025),(1,0)]
  with b.at(trans(dx,dy,0)@ry((k-1)*.16)@scale(s)):
   b.lathe([(z*h,rr) for z,rr in prof],mat,9,False)

def torch(b,tripod=False):
 height=1.6
 if tripod:
  for t in np.linspace(0,TAU,3,endpoint=False):
   log(b,(.35*math.cos(t),.35*math.sin(t),0),(.07*math.cos(t),.07*math.sin(t),1.35),.065)
  lash(b,(0,0,.75),.13,turns=3)
 else:log(b,(0,0,0),(0,0,1.4),.075,r2=.1)
 b.lathe([(1.25,.1),(1.33,.17),(1.58,.22),(1.61,.2)],'metal',10,False)
 for t in np.linspace(0,TAU,6,endpoint=False):
  b.beam((.12*math.cos(t),.12*math.sin(t),1.3),(.22*math.cos(t),.22*math.sin(t),1.65),.035,.04,'metal',.008)
 b.torus((0,0,1.52),.2,.023,'metal',segments=16,sides=5)
 use(b,flame,(0,0,1.52),h=.48)

def flag_cloth(b,w=1.3,h=.8,mat='flag_dark',torn=True):
 def surf(u,v):
  edge=.08*math.sin(u*17.3)+.035*math.sin(u*37) if torn else 0
  return (w*u,.1*math.sin(u*7+v*1.5)*u,h*(v-.5)+edge*(1-v))
 b.surface(surf,16,8,mat)

def flagpole(b,h=3.4,red=False):
 log(b,(0,0,0),(0,0,h),.07,r2=.045)
 b.sphere((0,0,h+.035),.08,'wood_pale',12,7)
 b.box((0,0,.06),(.48,.44,.12),'stone',.065)
 with b.at(trans(.03,0,h-.6)):
  flag_cloth(b,w=1.25,h=.78,mat='cloth_red' if red else 'flag_dark')
 lash(b,(0,0,h-.95),.075,turns=2,height=.06)

def roof_gable(b,w,d,eave,rise,mat='wood_red',canvas=False):
 half=w/2;angle=math.atan2(rise,half);length=math.hypot(half,rise)
 if canvas:
  for sign in [-1,1]:
   def fn(u,v,s=sign):
    x=s*half*u;y=(v-.5)*d;z=eave+rise*(1-u)-.09*math.sin(PI*u)*math.sin(PI*v)
    return x,y,z
   b.surface(fn,8,12,mat,flip=sign<0)
 else:
  rows=5;cols=max(5,round(d/.37))
  for sign in [-1,1]:
   for i in range(rows):
    u=(i+.5)/rows
    for j in range(cols):
     y=-d/2+(j+.5)*d/cols
     x=sign*half*u;z=eave+rise*(1-u)+.024*(rows-i)
     with b.at(trans(x,y,z)@ry(sign*angle)):
      b.box((0,0,0),(length/rows+.07,d/cols-.018,.07),mat if (i*7+j)%7 else 'wood',.02)
 for x in [-half,half]:log(b,(x,-d/2-.05,eave),(x,d/2+.05,eave),.085)
 log(b,(0,-d/2-.1,eave+rise+.06),(0,d/2+.1,eave+rise+.06),.095)
 for y in [-d/2,d/2]:
  log(b,(-half,y,eave),(0,y,eave+rise),.08)
  log(b,(half,y,eave),(0,y,eave+rise),.08)


def table(b):
 plank_floor(b,1.6,.9,.86,.1)
 for x in [-.59,.59]:
  for y in [-.29,.29]:b.beam((x*1.1,y*1.2,0),(x,y,.82),.11,.11,'wood_dark')
 b.beam((-.6,0,.28),(.6,0,.28),.09,.1)

def bench(b):
 plank_floor(b,1.5,.38,.47,.09)
 for x in [-.55,.55]:
  for y in [-.12,.12]:b.beam((x,y*1.3,0),(x,y,.43),.09,.09,'wood_dark')
 b.beam((-.55,0,.23),(.55,0,.23),.08,.08)
