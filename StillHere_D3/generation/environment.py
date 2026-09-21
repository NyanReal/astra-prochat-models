"""Reusable ground, bank, rock, paving, and water modules."""
import math
import numpy as np
from scipy.spatial import ConvexHull
from mesh_core import Mesh, unit


def ground(name, seed, key='meadow', radius=3.4, depth=.65, transition=False):
    rng=np.random.default_rng(seed);m=Mesh(name,'ground')
    n=18;theta=np.arange(n)*2*np.pi/n
    r=radius*rng.uniform(.78,1.06,n)
    border=np.column_stack((np.cos(theta)*r,np.sin(theta)*r*rng.uniform(.77,1.0),rng.uniform(-.06,-.025,n)))
    inner=border.copy();inner[:,:2]*=.52;inner[:,2]=rng.uniform(.015,.04,n)
    v=np.vstack([[0,0,.04],inner,border]);f=[]
    for i in range(n):
        j=(i+1)%n
        f.extend([(0,1+i,1+j),(1+i,1+n+i,1+n+j),(1+i,1+n+j,1+j)])
    if transition:
        v[:,2]*=1.3;v[-n:,2]=-.11
    lo=v[:,:2].min(0);sz=v[:,:2].max(0)-lo;uv=(v[:,:2]-lo)/sz
    m.add(v,f,uv,sz,key,tint=(1,1,.98),smooth=True)
    if not transition:
        for i in range(n):
            j=(i+1)%n;a=border[i].copy();b=border[j].copy();aa=a.copy();bb=b.copy();aa[2]=-depth;bb[2]=-depth
            m.poly([b,a,aa,bb],'forest_floor',tint=(.83,.9,.80))
        bot=border.copy();bot[:,2]=-depth;m.poly(bot[::-1],'dirt')
    m.description='Irregular overlapping surface module with a lowered feathered perimeter; separate seam-cover meshes are placed in the scene.'
    return m


def paving(name,seed,number=3):
    rng=np.random.default_rng(seed);m=Mesh(name,'ground')
    for k in range(number):
        cx=(k-(number-1)/2)*.72;cy=rng.uniform(-.13,.13);w=rng.uniform(.31,.39);h=rng.uniform(.37,.48)
        corners=np.array([[-w+.07,-h], [w-.06,-h], [w,-h+.06], [w,h-.08], [w-.08,h], [-w+.05,h], [-w,h-.05], [-w,-h+.07]])
        corners+=rng.uniform(-.025,.025,corners.shape)
        v=np.column_stack((corners[:,0]+cx,corners[:,1]+cy,np.full(8,.045)))
        m.poly(v,'broken_concrete',(.93,.97,.96))
        for i in range(8):
            j=(i+1)%8;a=v[i].copy();b=v[j].copy();aa=a.copy();bb=b.copy();aa[2]=-.035;bb[2]=-.035
            m.poly([b,a,aa,bb],'concrete',(.74,.78,.75))
    return m


def rock(name,seed,scale=(1.,.85,1.1),moss=True,cliff=False):
    rng=np.random.default_rng(seed);m=Mesh(name,'rocks')
    n=13
    t=np.arange(n)*2*np.pi/n
    verts=[]
    if cliff:
        for z,r in [(-.25,.9),(.35,1.),(.85,.95),(1.0,.73)]:
            for a in t:
                verts.append([math.cos(a)*r*rng.uniform(.8,1.1),math.sin(a)*r*rng.uniform(.8,1.1),z+rng.uniform(-.045,.045)])
    else:
        for z,r in [(-.16,.7),(.15,1.),(.66,.92),(1.0,.55)]:
            for a in t:
                verts.append([math.cos(a)*r*rng.uniform(.72,1.13),math.sin(a)*r*rng.uniform(.75,1.1),z+rng.uniform(-.10,.10)])
    v=np.asarray(verts)*scale;hull=ConvexHull(v);center=v.mean(0)
    for ids in hull.simplices:
        p=v[ids];normal=np.cross(p[1]-p[0],p[2]-p[0])
        if np.dot(normal,p.mean(0)-center)<0:p=p[::-1];normal=-normal
        normal=unit(normal)
        top=normal[2]>.48 and p.mean(0)[2]>.5*scale[2]
        key='moss' if moss and top and rng.random()<.83 else 'rock'
        tint=(1.22,1.23,1.13) if key=='rock' else (1.12,1.1,.94)
        m.poly(p,key,tint)
    return m


def cliff_block(name,seed):
    rng=np.random.default_rng(seed);m=Mesh(name,'architecture')
    xy=np.array([[-1.70,-1.20],[-.78,-1.55],[1.45,-1.38],[2.06,-.66],[2.12,.88],[1.07,1.50],[-1.55,1.39],[-2.1,.30]])
    top=np.column_stack((xy*rng.uniform(.90,1.04,(8,1)),5.05+rng.uniform(-.16,.18,8)))
    mid=np.column_stack((xy*rng.uniform(.95,1.02,(8,1)),np.full(8,2.35)))
    bottom=np.column_stack((xy*.93,np.full(8,-.30)))
    for ring_a,ring_b in [(bottom,mid),(mid,top)]:
        for i in range(8):
            j=(i+1)%8;m.poly([ring_a[i],ring_a[j],ring_b[j],ring_b[i]],'concrete',(1.04,1.08,1.07))
    m.poly(top,'moss',(1.06,1.08,1.01));m.poly(bottom[::-1],'rock')
    return m


def water_strip(name,seed,width=5.,length=7.):
    rng=np.random.default_rng(seed);m=Mesh(name,'water',surface_type='water')
    nx,ny=6,20;v=[];uv=[]
    for j in range(ny+1):
        y=-length/2+j*length/ny
        for i in range(nx+1):
            x=-width/2+i*width/nx
            z=.015*math.sin(y*2.7+x*1.6)+.008*math.sin(x*5-y*3)
            v.append([x,y,z]);uv.append([i/nx,j/ny])
    f=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;f.extend([(a,a+1,a+nx+2),(a,a+nx+2,a+nx+1)])
    m.add(v,f,uv,(width,length),'water',smooth=True,exact=True)
    m.description='Opaque stylised water base; engine scripts add time-dependent normal ripples, foam geometry remains separate.'
    return m


def waterfall(name):
    m=Mesh(name,'water',double_sided=True,surface_type='waterfall')
    cols,rows=14,22;v=[];uv=[]
    for j in range(rows+1):
        q=j/rows
        for i in range(cols+1):
            t=i/cols;x=(t-.5)*2.5*(1.+.035*math.sin(q*8)+.04*q)
            y=.15*math.cos(t*11)+.38*q*q
            z=5.5*(1-q)
            v.append([x,y,z]);uv.append([t,1-q])
    f=[]
    for j in range(rows):
        for i in range(cols):
            a=j*(cols+1)+i;f.extend([(a,a+cols+2,a+1),(a,a+cols+1,a+cols+2)])
    m.add(v,f,uv,(2.5,5.5),'waterfall',smooth=True,exact=True)
    # Uneven foam strands are real geometry, not an opaque white rectangle.
    for k in range(17):
        x=-1.17+k*.144;points=[]
        for j in range(13):
            q=j/12;points.append([x+.025*math.sin(q*17+k),-.05+.4*q*q,5.5*(1-q)])
        for a,b in zip(points[:-1],points[1:]):m.cylinder(a,b,.027+.026*(k%3==0),'foam',sides=4,caps=False)
    return m


def foam_ring(name,seed):
    rng=np.random.default_rng(seed);m=Mesh(name,'water',double_sided=True,surface_type='foam')
    # Broken arcs leave open water between foam filaments.
    for j in range(8):
        start=rng.uniform(0,2*np.pi);span=rng.uniform(.3,1.5);radius=rng.uniform(.65,1.35);n=12
        p=[]
        for i in range(n+1):
            a=start+span*i/n;r=radius+.035*math.sin(a*17+j)
            p.append([math.cos(a)*r,math.sin(a)*r*.82,.035+j*.0008])
        for i in range(n):
            a=np.asarray(p[i]);b=np.asarray(p[i+1]);d=unit(b-a);side=np.array([-d[1],d[0],0])*(.021+.020*rng.random())
            m.poly([a-side,b-side,b+side,a+side],'foam',tint=(1,1,1))
    return m


def foam_stream(name,seed):
    rng=np.random.default_rng(seed);m=Mesh(name,'water',double_sided=True,surface_type='foam')
    for k in range(18):
        x=rng.uniform(-1.8,1.8);y=rng.uniform(-2,2);ln=rng.uniform(.09,.36);w=rng.uniform(.014,.030)
        points=[[x+.06*math.sin(t*5+k),y+t*ln,.04+rng.uniform(0,.004)] for t in np.linspace(0,1,5)]
        for a,b in zip(points[:-1],points[1:]):
            a=np.array(a);b=np.array(b);s=np.array([w,0,0]);m.poly([a-s,b-s,b+s,a+s],'foam')
    return m


def river_main():
    from scene_math import pixel_to_world
    m=Mesh('River_Main','water',surface_type='water')
    ys=np.array([-180,0,120,240,330,400,500,620,760,900,1160],float)
    left=np.array([1180,1180,1165,1080,1100,1010,965,1050,1120,1200,1320],float)
    right=np.array([1380,1380,1390,1520,1540,1440,1300,1360,1390,1420,1630],float)
    pivot=np.array([10.5,0.,-.09]);v=[];nx=10;rows=np.linspace(190,1370,82)
    for j,py in enumerate(rows):
        le=float(np.interp(py,ys,left))-75;ri=float(np.interp(py,ys,right))+75
        for i in range(nx+1):
            px=le+(ri-le)*i/nx;p=pixel_to_world(px,py,-.09)
            p[2]+=.005*np.sin(p[1]*2.7+p[0]);v.append(p-pivot)
    v=np.array(v);lo=v[:,:2].min(0);sz=v[:,:2].max(0)-lo;uv=(v[:,:2]-lo)/sz;f=[]
    for j in range(len(rows)-1):
        for i in range(nx):
            a=j*(nx+1)+i
            # Pixel rows advance toward -Y; reverse their winding for +Z normals.
            f.extend([(a,a+nx+2,a+1),(a,a+nx+1,a+nx+2)])
    m.add(v,f,uv,sz,'water',smooth=True,exact=True)
    m.description='Continuous curved lower river with no overlapping water-sheet seams; placement pivot [10.5, 0, -0.09] metres.'
    return m


def hero_island():
    m=Mesh('Rock_Hero_Island','rocks');rng=np.random.default_rng(727)
    angles=np.arange(10)*2*np.pi/10;xy=np.column_stack((1.5*np.cos(angles),1.2*np.sin(angles)))*rng.uniform(.9,1.06,(10,1))
    base=np.column_stack((xy*.92,np.full(10,-.12)))
    mid=np.column_stack((xy*1.02,np.full(10,.35)))
    top=np.column_stack((xy*.79,1.65+rng.uniform(-.035,.025,10)))
    for aa,bb in [(base,mid),(mid,top)]:
        for i in range(10):
            j=(i+1)%10;m.poly([aa[i],aa[j],bb[j],bb[i]],'rock',(1.17,1.19,1.16))
    m.poly(top,'rock',(1.23,1.25,1.17));m.poly(base[::-1],'rock')
    cap=ground('island_moss',728,'moss',radius=.91,transition=True)
    m.merge(cap,loc=(-.22,.02,1.665),scale=(1.05,.84,1))
    m.description='Broad, flat-topped river island with bevelled rock faces and a separate feathered moss cap.'
    return m


def generated_foam():
    import json
    from mesh_core import ROOT
    data=json.loads((ROOT/'source/generated_foam_contours.json').read_text())
    m=Mesh('Foam_Generated_Eddies','water',double_sided=True,surface_type='foam')
    for xy in data['polygons_xy_m']:
        points=np.column_stack((xy,np.full(len(xy),.035)))
        # OpenCV source contours may be clockwise; face their front towards +Z.
        signed=np.sum(points[:,0]*np.roll(points[:,1],-1)-points[:,1]*np.roll(points[:,0],-1))
        if signed<0:points=points[::-1]
        m.poly(points,'foam',(.91,.98,1.))
    m.description='Actual silhouettes extracted from the image-generated water source; no rectangular transparent card and no procedural repeating foam texture.'
    return m
