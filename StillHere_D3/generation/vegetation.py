"""Leaf silhouettes and branching foliage. No low-resolution sphere canopy."""
import math
import numpy as np
from mesh_core import Mesh,unit

LEAF_KEYS=['leaf_olive','leaf_lime','leaf_teal','leaf_dark','leaf_light']

def broadleaf(name,seed,variant=0):
    rng=np.random.default_rng(seed);m=Mesh(name,'trees',double_sided=True)
    base=[0,0,0];p1=[.08,-.03,1.1];p2=[-.07,.07,2.3];p3=[.21,.1,3.6]
    for a,b,r1,r2 in [(base,p1,.23,.20),(p1,p2,.20,.15),(p2,p3,.15,.09)]:m.cylinder(a,b,r1,'bark',radius2=r2,sides=10,rough=.08,rng=rng)
    for k in range(5):
        a=k*2*np.pi/5+.25;m.cylinder([0,0,.28],[.64*np.cos(a),.64*np.sin(a),.01],.12,'bark',radius2=.025,sides=7)
    centers=[]
    for k in range(9):
        a=k*2.4+.6*variant;radius=1.4+rng.uniform(-.3,.45);z=3.35+rng.uniform(-.28,.60)
        endpoint=np.array([radius*np.cos(a),radius*np.sin(a),z]);mid=endpoint*.55;mid[2]=2.8+rng.uniform(-.2,.5)
        m.cylinder(p2,mid,.09,'bark',radius2=.052,sides=7)
        m.cylinder(mid,endpoint,.052,'bark',radius2=.012,sides=6)
        centers.append(endpoint+np.array([0,0,.4]))
    centers += [np.array([rng.uniform(-.8,.8),rng.uniform(-.8,.8),rng.uniform(4.3,5.05)]) for _ in range(6)]
    key_base=['leaf_olive','leaf_teal','leaf_lime'][variant%3]
    for k,c in enumerate(centers):
        rad=np.array([rng.uniform(.70,1.02),rng.uniform(.65,1.02),rng.uniform(.62,.82)])
        key=key_base if rng.random()<.65 else ('leaf_lime' if variant!=1 else 'leaf_olive')
        for j in range(68):
            direction=unit(rng.normal(size=3));p=c+direction*rad*rng.uniform(.4,1.)**.45
            ln=rng.uniform(.23,.39);wd=ln*rng.uniform(.50,.75)
            # Coherent lighting variation at cluster scale instead of pointillist noise.
            lum=np.clip(.91+.12*(p[2]-3.7),.84,1.12)
            m.leaf(p,ln,wd,(rng.uniform(-50,50),rng.uniform(-50,50),rng.uniform(0,360)),key,(lum,lum,lum*.98))
    m.description='Bent trunk and radial branch structure with individual folded six-point leaves; reusable canopy silhouette.'
    return m


def pine(name,seed,variant=0):
    rng=np.random.default_rng(seed);m=Mesh(name,'trees',double_sided=True)
    h=8.+variant*.9;m.cylinder((0,0,0),(.1,0,h),.18,'bark',radius2=.018,sides=10)
    for layer in range(10):
        z=1.65+layer*(h-1.9)/10;radius=2.05*(1-layer/11)**.90
        for k in range(8):
            a=k*2*np.pi/8+layer*.75+rng.uniform(-.11,.11);d=np.array([math.cos(a),math.sin(a),0.]);s=np.array([-d[1],d[0],0])
            base=np.array([0.,0.,z]);tip=base+d*radius;tip[2]-=.32+.05*radius
            m.cylinder(base,tip,.04*(1-layer/13),'bark',radius2=.008,sides=5)
            # Dense hanging side sprays produce a tiered, serrated fir silhouette.
            for j in range(1,9):
                q=j/9;c=base+(tip-base)*q;w=radius*.42*(1-q)+.12
                for side in (-1,1):
                    end=c+s*side*w+d*.13;end[2]-=.24*(1-q)+.06
                    mid=(c+end)*.5;mid[2]+=.025
                    v=[c-d*.06,mid-d*.12,end,mid+d*.14,c+d*.07]
                    m.poly(v,'pine',tint=(1+layer*.017,1+layer*.017,.98+layer*.014))
                    for jj in range(1):
                        cc=c+(end-c)*(jj+1)/4
                        m.leaf(cc,.26*(1-q*.4),.07,(55+rng.uniform(-8,8),rng.uniform(-30,30),math.degrees(a)+side*58),'pine')
    return m


def bush(name,seed,variant=0):
    rng=np.random.default_rng(seed);m=Mesh(name,'shrubs',double_sided=True)
    for k in range(7):
        a=k*2.399;c=np.array([np.cos(a)*rng.uniform(.2,.48),np.sin(a)*rng.uniform(.2,.48),rng.uniform(.55,.98)])
        m.cylinder((0,0,.02),c,.025,'bark',radius2=.009,sides=5)
        for j in range(37):
            d=unit(rng.normal(size=3));p=c+d*np.array([.46,.44,.40])*rng.uniform(.4,1.)
            key=['leaf_lime','leaf_teal','leaf_olive'][variant%3]
            lum=rng.uniform(.95,1.06)
            m.leaf(p,rng.uniform(.17,.30),rng.uniform(.10,.18),(rng.uniform(-45,45),rng.uniform(-45,45),rng.uniform(0,360)),key,(lum,lum,lum))
    return m


def grass(name,seed,variant=0):
    rng=np.random.default_rng(seed);m=Mesh(name,'groundcover',double_sided=True)
    for k in range(64):
        a=rng.uniform(0,2*np.pi);r=.50*np.sqrt(rng.random());base=np.array([r*np.cos(a),r*np.sin(a),0.]);h=rng.uniform(.16,.52)
        d=np.array([math.cos(a),math.sin(a),0]);side=np.array([-d[1],d[0],0])*rng.uniform(.018,.044)
        middle=base+d*h*.25+np.array([0,0,h*.68]);tip=base+d*h*.65+np.array([0,0,h])
        m.poly([base-side,base+side,middle+side*.65,tip,middle-side*.65],['leaf_olive','leaf_lime','leaf_light'][(k+variant)%3])
    return m


def flowers(name,seed,pink=False):
    rng=np.random.default_rng(seed);m=Mesh(name,'groundcover',double_sided=True)
    for k in range(20):
        a=rng.uniform(0,2*np.pi);r=rng.uniform(0,.65);x,y=r*np.cos(a),r*np.sin(a);h=rng.uniform(.28,.7)
        m.cylinder([x,y,0],[x+.05,y,h],.008,'leaf_olive',radius2=.004,sides=4,caps=False)
        for j in range(2):m.leaf([x+(.04 if j else -.04),y,h*(j+1)/3],.22,.10,(0,45,30+j*170),'leaf_olive')
        c=np.array([x+.05,y,h]);key='flower_pink' if pink else 'flower_white'
        for j in range(5):
            t=j*2*np.pi/5;d=np.array([np.cos(t),np.sin(t),0]);s=np.array([-d[1],d[0],0])
            m.poly([c,c+d*.045+s*.027,c+d*.095,c+d*.045-s*.027],key)
        m.poly([c+[-.022,-.022,.006],c+[.022,-.022,.006],c+[.022,.022,.006],c+[-.022,.022,.006]],'flower_yellow')
    return m


def fern(name,seed):
    rng=np.random.default_rng(seed);m=Mesh(name,'groundcover',double_sided=True)
    for k in range(8):
        a=k*2.4;d=np.array([np.cos(a),np.sin(a),0]);s=np.array([-d[1],d[0],0]);ln=rng.uniform(.52,.86)
        for j in range(8):
            t=j/8;c=d*ln*t;c[2]=.16+.45*np.sin(t*2)
            w=.18*(1-t)+.025
            for side in (-1,1):m.leaf(c+s*side*w*.4,.20*(1-t)+.07,.055,(25,15,math.degrees(a)+side*55),'leaf_olive')
    return m


def ivy(name,seed,length=3.3):
    rng=np.random.default_rng(seed);m=Mesh(name,'vines',double_sided=True)
    for k in range(4):
        offset=(k-1.5)*.24;ln=length*rng.uniform(.6,1.0);previous=np.array([offset,0,0])
        for j in range(18):
            t=(j+1)/18;current=np.array([offset+.10*math.sin(t*9+k),.035*np.sin(t*7),-ln*t])
            m.cylinder(previous,current,.010,'bark',radius2=.007,sides=4,caps=False)
            for side in (-1,1):
                p=current+np.array([side*.10,-.025,.035]);m.leaf(p,rng.uniform(.18,.26),rng.uniform(.14,.21),(90+rng.uniform(-22,22),rng.uniform(-25,25),side*35),'leaf_lime' if k%2 else 'leaf_olive')
            previous=current
    return m
