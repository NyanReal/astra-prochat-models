"""Industrial ruins, catwalks, signage, and latticework."""
import math
import numpy as np
from mesh_core import Mesh,unit


def tank_arc(name,seed,radius=7.,height=6.5):
    rng=np.random.default_rng(seed);m=Mesh(name,'architecture')
    n=12;t=np.linspace(-np.pi/12,np.pi/12,n+1)
    tops=height+rng.uniform(-.13,.09,n+1)
    if seed%2:tops[4:7]-=.23
    for r,key,tint,reverse in [(radius,'concrete',(1,1,1),False),(radius-.42,'concrete',(.46,.52,.48),True)]:
        v=[];uv=[]
        for row in (0,1):
            for i,a in enumerate(t):v.append([r*np.cos(a),r*np.sin(a),tops[i] if row else 0]);uv.append([i/n,row])
        f=[]
        for i in range(n):f.extend([(i,i+1,i+n+2),(i,i+n+2,i+n+1)])
        if reverse:f=[x[::-1] for x in f]
        m.add(v,f,uv,(radius*np.pi/6,height),key,tint,smooth=True,exact=True)
    for i in range(n):
        a,b=t[i:i+2]
        m.poly([[ (radius-.42)*np.cos(a),(radius-.42)*np.sin(a),tops[i]],
                [radius*np.cos(a),radius*np.sin(a),tops[i]],
                [radius*np.cos(b),radius*np.sin(b),tops[i+1]],
                [(radius-.42)*np.cos(b),(radius-.42)*np.sin(b),tops[i+1]]], 'broken_concrete',(1.02,1.04,.98))
    # Closed seams are separately modelled even though neighbouring arc assets overlap slightly.
    for i in (0,n):
        a=t[i];p=[[radius*np.cos(a),radius*np.sin(a),0],[(radius-.42)*np.cos(a),(radius-.42)*np.sin(a),0],
                 [(radius-.42)*np.cos(a),(radius-.42)*np.sin(a),tops[i]],[radius*np.cos(a),radius*np.sin(a),tops[i]]]
        m.poly(p if i==0 else p[::-1],'concrete')
    return m


def tank_marking():
    m=Mesh('Tank_D3_Marking','architecture');n=24;t=np.radians(np.linspace(-75,-32,n+1));v=[];uv=[]
    for row in (0,1):
        for i,a in enumerate(t):v.append([7.018*np.cos(a),7.018*np.sin(a),1.0+row*3.9]);uv.append([i/n,row])
    f=[]
    for i in range(n):f.extend([(i,i+1,i+n+2),(i,i+n+2,i+n+1)])
    m.add(v,f,uv,(5.25,3.9),'d3_text',smooth=True,exact=True)
    return m


def catwalk():
    m=Mesh('Catwalk_Deck_3m','architecture')
    for k in range(5):m.box((0,-.56+k*.28,0),(3.04,.26,.14),'broken_concrete',(.85,.87,.82))
    for y in (-.68,.68):m.box((0,y,-.17),(3.07,.11,.26),'rust')
    for x in (-1.40,0,1.40):m.box((x,0,-.25),(.12,1.45,.13),'rust')
    return m


def railing(name='Railing_3m',broken=False):
    m=Mesh(name,'architecture')
    for i,x in enumerate((-1.5,0,1.5)):
        tip=[x+(.17 if broken and i==2 else 0),.08 if broken and i==2 else 0,1.05-(.25 if broken and i==2 else 0)]
        m.cylinder([x,0,0],tip,.027,'rust',sides=6)
    for z in (.48,1.05):
        m.cylinder([-1.5,0,z],[1.5,.04 if broken else 0,z-(.25 if broken else 0)],.025,'rust',sides=6)
    return m


def stairs():
    m=Mesh('Stairs_Industrial','architecture')
    run,height,n=4.6,4.5,17
    for i in range(n):
        x=(i+.5)*run/n;z=(i+1)*height/n
        m.box((x,0,z),(run/n+.055,1.35,.105),'steel',(.57,.66,.58))
        m.box((x-run/n/2,0,z-.06),(.055,1.4,.16),'rust',(.75,.78,.70))
    for y in (-.68,.68):
        m.cylinder([0,y,.08],[run,y,height-.10],.095,'rust',sides=4)
        for i in (0,4,8,12,17):
            x=i*run/n;z=i*height/n;m.cylinder([x,y,z],[x,y,z+1.0],.025,'rust',sides=6)
        m.cylinder([0,y,1],[run,y,height+1],.024,'rust',sides=6)
        m.cylinder([0,y,.48],[run,y,height+.48],.020,'rust',sides=6)
    return m


def bunker():
    m=Mesh('Utility_Bunker_Bay','architecture')
    m.box((0,.55,2.08),(5.8,1.25,4.16),'concrete',(.77,.82,.77))
    # A recessed dark entrance, supported by a concrete lintel and jambs.
    m.box((-.95,-.105,1.40),(1.5,.065,2.8),'rubber',(.56,.62,.52))
    for x in (-1.83,-.06):m.box((x,-.17,1.5),(.24,.24,3.0),'concrete',(.83,.86,.77))
    m.box((-.95,-.17,3.02),(2.03,.26,.3),'broken_concrete')
    for x in (.4,1.6,2.5):m.box((x,-.102,2.1),(.045,.025,4.0),'rust',(.67,.69,.65))
    return m


def banner():
    m=Mesh('Banner_Still_Here','architecture',double_sided=True)
    nx,nz=10,18;v=[];uv=[]
    for j in range(nz+1):
        q=j/nz
        for i in range(nx+1):
            t=i/nx;x=(t-.5)*1.85;y=-.075*math.sin(t*5*np.pi)*(q*.6+.4)-.12*q*q;z=-4.05*q-.04*math.sin(t*8)*(q**6)
            v.append([x,y,z]);uv.append([t,1-q])
    f=[]
    for j in range(nz):
        for i in range(nx):
            a=j*(nx+1)+i;f.extend([(a,a+1,a+nx+2),(a,a+nx+2,a+nx+1)])
    m.add(v,f,uv,(1.85,4.05),'banner_text',smooth=True,exact=True)
    m.cylinder([-1,0,.035],[1,0,.035],.025,'rust',sides=6)
    for x in (-.76,.76):m.cylinder([x,0,.08],[x,0,.24],.020,'rust',sides=5)
    return m


def bridge_deck():
    m=Mesh('Bridge_Deck_Broken','architecture')
    outline=[[-2.6,-1.2,.0],[1.9,-1.2,0],[2.25,-.76,0],[1.81,-.40,0],[2.65,-.12,0],[2.21,.22,0],[2.5,.61,0],[2.1,1.2,0],[-2.6,1.2,0]]
    m.poly(outline,'broken_concrete',(1.1,1.1,1.02))
    for i,a in enumerate(outline):
        b=outline[(i+1)%len(outline)];aa=np.array(a)-[0,0,.6];bb=np.array(b)-[0,0,.6]
        m.poly([b,a,aa,bb],'concrete',(.92,.95,.91))
    m.poly((np.asarray(outline)-[0,0,.6])[::-1],'concrete',(.62,.69,.66))
    for x in (-2.1,-.6,.8):
        m.box((x,.88,.22),(.8,.48,.43),'broken_concrete',(1.12,1.12,1.04))
    for y in (-.8,-.34,.3,.8):m.cylinder([1.8,y,-.21],[2.9,y+.08,-.34],.027,'rust',sides=5)
    return m


def bridge_pier():
    m=Mesh('Bridge_Pier','architecture')
    m.box((0,0,.18),(1.8,1.5,.36),'rock',(1.18,1.20,1.12))
    m.box((0,0,2.20),(.87,.95,4.15),'concrete',(.86,.91,.80))
    m.box((0,0,4.33),(1.52,1.35,.27),'broken_concrete')
    return m


def ruined_wall():
    m=Mesh('Concrete_Wall_Ruined','architecture')
    profile=[[-2.2,0],[2.2,0],[2.2,4.9],[1.55,4.9],[1.55,4.42],[.96,4.42],[.96,4.83],[.2,4.83],[.2,4.56],[-.5,4.56],[-.5,4.85],[-2.2,4.85]]
    # Use independent vertical blocks so missing top pieces are true geometry.
    widths=[(-2.2,-.5,4.85),(-.5,.2,4.56),(.2,.96,4.83),(.96,1.55,4.42),(1.55,2.2,4.9)]
    for a,b,h in widths:m.box(((a+b)/2,0,h/2),(b-a,.55,h),'concrete',(.84,.90,.84))
    return m


def nature_sign():
    m=Mesh('Wall_Marking_Nature','architecture')
    v=[[-1.15,-.312,.22],[1.15,-.312,.22],[1.15,-.312,4.32],[-1.15,-.312,4.32]]
    m.add(v,[(0,1,2),(0,2,3)],[[0,0],[1,0],[1,1],[0,1]],(2.3,4.1),'nature_text',(.90,.94,.91),exact=True)
    return m


def pylon():
    m=Mesh('Lattice_Pylon','architecture');h=6.8
    def corner(i,z):
        r=1.14-(z/h)*.86;return np.array([r*(1 if i%2 else -1),r*(1 if i//2 else -1),z])
    for i in range(4):m.cylinder(corner(i,0),corner(i,h),.082,'rust',sides=4)
    rings=[.3,1.8,3.3,4.8,6.3]
    edges=[(0,1),(1,3),(3,2),(2,0)]
    for z in rings:
        for a,b in edges:m.cylinder(corner(a,z),corner(b,z),.056,'rust',sides=4)
    for k,(za,zb) in enumerate(zip(rings[:-1],rings[1:])):
        for a,b in edges:
            m.cylinder(corner(a,za),corner(b,zb),.036,'rust',sides=4)
            if k<2:m.cylinder(corner(b,za),corner(a,zb),.031,'rust',sides=4)
    m.box((0,0,h),(.7,.7,.13),'rust')
    m.cylinder([-.5,0,h+.1],[.5,0,h+.1],.037,'rust',sides=6)
    return m
