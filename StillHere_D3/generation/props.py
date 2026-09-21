"""Camera-scale prop meshes: damaged truck, crates, cloth, log, traveller, gull."""
import math
import numpy as np
from mesh_core import Mesh,unit


def ellipsoid(mesh,center,scale,key,nu=14,nv=9,tint=(1,1,1),rotation=(0,0,0)):
    from mesh_core import transform_points
    v=[];uv=[]
    for j in range(nv+1):
        theta=.008+(np.pi-.016)*j/nv
        for i in range(nu+1):
            a=i/nu*2*np.pi;v.append([np.sin(theta)*np.cos(a),np.sin(theta)*np.sin(a),np.cos(theta)]);uv.append([i/nu,1-j/nv])
    v=transform_points(v,center,rotation,scale);f=[]
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i;f.extend([(a,a+nu+2,a+1),(a,a+nu+1,a+nu+2)])
    mesh.add(v,f,uv,(2*np.pi*max(scale[:2]),np.pi*scale[2]),key,tint,smooth=True)


def wheel(mesh,x,y,z):
    # Four-piece radial tyre profile with rounded shoulders.
    n=16;profile=[(-.13,.30),(-.12,.40),(-.075,.445),(.075,.445),(.12,.40),(.13,.30)]
    v=[];uv=[]
    for j,(dy,r) in enumerate(profile):
        for i in range(n+1):
            a=i/n*2*np.pi;v.append([x+r*np.cos(a),y+dy,z+r*np.sin(a)]);uv.append([i/n,j/(len(profile)-1)])
    f=[]
    for j in range(len(profile)-1):
        for i in range(n):
            a=j*(n+1)+i;f.extend([(a,a+1,a+n+2),(a,a+n+2,a+n+1)])
    mesh.add(v,f,uv,(2*np.pi*.445,.45),'rubber',smooth=True)
    mesh.cylinder([x,y-.132,z],[x,y+.132,z],.278,'steel',tint=(.56,.6,.56),sides=12)
    mesh.cylinder([x,y-.15,z],[x,y+.15,z],.085,'rust',sides=8)


def truck():
    m=Mesh('Truck_Abandoned','props')
    m.box((0,0,.55),(4.65,1.57,.22),'rust',(.7,.76,.7))
    m.box((.63,0,1.80),(2.95,1.90,1.86),'paint',(.99,1.0,.94))
    m.box((.63,0,2.76),(3.02,1.97,.12),'paint',(1.05,1.05,.98))
    # Cargo rails, edge seams and rear split doors.
    for y in (-.976,.976):
        for z in (.90,2.71):m.box((.63,y,z),(3.08,.055,.065),'steel',(.51,.61,.55))
        for x in (-.83,2.1):m.box((x,y,1.8),(.066,.062,1.93),'steel',(.57,.62,.55))
        m.box((.65,y,1.57),(2.9,.031,.035),'rust',(.76,.77,.68))
    for y in (-.88,0,.88):m.box((2.127,y,1.78),(.026,.045,1.78),'rust',(.68,.7,.60))
    for y in (-.72,.72):
        m.box((2.15,y,1.75),(.035,.045,1.5),'steel',(.53,.58,.50))
        for z in (1.13,2.33):m.box((2.17,y,z),(.07,.18,.065),'rust')
    # Cab lower body and a slanted windshield frame, silhouette is not a plain box.
    m.box((-1.66,0,.95),(1.75,1.80,.82),'paint',(.88,.91,.84))
    m.box((-1.48,0,2.10),(1.42,1.86,.11),'paint',(.85,.87,.80))
    # Front windshield (faces camera when the vehicle is rotated into the reference).
    front=[[-2.50,-.81,1.31],[-2.50,.81,1.31],[-2.15,.81,2.07],[-2.15,-.81,2.07]]
    m.poly(front,'glass')
    for y in (-.85,.85):
        m.cylinder([-2.5,y,1.3],[-2.15,y,2.12],.053,'steel',sides=4)
        m.cylinder([-2.15,y,2.1],[-.81,y,2.1],.043,'steel',sides=4)
        m.cylinder([-.83,y,1.27],[-.83,y,2.1],.058,'paint',sides=4)
        side=[[-2.12,y,1.33],[-.86,y,1.33],[-.86,y,2.03],[-2.12,y,2.03]]
        m.poly(side if y<0 else side[::-1],'glass',(.89,.93,.87))
        m.box((-1.45,y*1.07,1.00),(1.3,.035,.57),'paint',(.93,.94,.86))
        m.box((-1.0,y*1.10,1.26),(.18,.035,.033),'rust')
        m.cylinder([-2.10,y,1.65],[-2.1,y*1.32,1.75],.023,'rust',sides=5)
        m.box((-2.1,y*1.35,1.77),(.08,.17,.24),'rubber')
    m.box((-2.555,0,.82),(.10,1.8,.20),'rust',(.68,.70,.66))
    m.box((-2.59,0,1.04),(.035,.78,.23),'rubber')
    for y in (-.61,.61):m.box((-2.596,y,1.04),(.04,.28,.20),'hair',(.89,.89,.74))
    for y in (-.35,-.12,.12,.35):m.box((-2.62,y,1.04),(.018,.035,.22),'steel',(.48,.53,.47))
    m.cylinder([-2.50,-.06,1.31],[-2.155,-.06,2.06],.022,'rust',sides=4)
    for y in (-.39,.39):m.cylinder([-2.5,y,1.37],[-2.40,y+.22,1.53],.010,'rubber',sides=4)
    for x in (-1.64,1.42):
        for y in (-.96,.96):wheel(m,x,y,.46)
    m.description='Static damaged delivery truck with cargo seams, slanted cab, glazing, mirrors, grille and tyres; vines are separate reused objects.'
    return m


def crate(name='Crate_Wood',open_top=False):
    m=Mesh(name,'props')
    if not open_top:m.box((0,0,.55),(1.08,1.0,1.1),'wood',(.62,.67,.55))
    else:
        m.box((0,0,.075),(1.08,1.0,.15),'wood',(.59,.61,.52))
        for y in (-.46,.46):m.box((0,y,.54),(1.08,.08,.94),'wood',(.65,.64,.53))
        for x in (-.5,.5):m.box((x,0,.54),(.08,.92,.94),'wood',(.69,.69,.60))
    for x in (-.53,.53):
        for y in (-.51,.51):m.box((x,y,.56),(.07,.07,1.14),'rust',(.72,.80,.70))
    for z in (.06,1.05):
        for y in (-.52,.52):m.box((0,y,z),(1.1,.05,.06),'rust',(.70,.75,.65))
        for x in (-.56,.56):m.box((x,0,z),(.05,1.06,.06),'rust',(.70,.75,.65))
    if not open_top:
        m.cylinder([-.5,-.52,.04],[.5,-.52,1.07],.037,'steel',(.58,.63,.52),sides=4)
        m.cylinder([-.5,-.49,1.12],[.5,.49,1.12],.035,'rust',sides=4)
    return m


def tarp_stack():
    m=Mesh('Tarp_Covered_Stack','props',double_sided=True)
    m.box((0,0,.57),(1.65,1.4,1.14),'wood',(.48,.56,.43))
    # Drape a single connected cloth sheet across the top and both hanging sides.
    nx,ny=16,14;v=[];uv=[]
    for j in range(ny+1):
        y=-.8+1.6*j/ny
        for i in range(nx+1):
            t=i/nx;x=-1.05+2.1*t
            z=1.22-.99*max((abs(x)-.74)/.31,0)+.065*math.sin(t*8*np.pi)*(abs(x)/1.05)+.035*math.sin(y*5)
            v.append([x,y,z]);uv.append([t,j/ny])
    f=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;f.extend([(a,a+1,a+nx+2),(a,a+nx+2,a+nx+1)])
    m.add(v,f,uv,(2.4,1.6),'canvas',smooth=True,exact=True)
    for x in (-.65,.65):m.cylinder([x,-.85,1.24],[x,.85,1.24],.019,'bark',sides=4)
    return m


def drum():
    m=Mesh('Drum_Aged','props');m.cylinder((0,0,.015),(0,0,1.1),.36,'steel',(.73,.79,.77),sides=18)
    for z in (.06,.38,.75,1.05):m.cylinder((0,0,z-.025),(0,0,z+.025),.378,'steel',(.55,.62,.59),sides=18)
    m.cylinder((.14,.10,1.10),(.14,.10,1.12),.055,'rubber',sides=10)
    return m


def log_bridge():
    m=Mesh('Log_Fallen_Bridge','props');rng=np.random.default_rng(554)
    segments=[([-4,0,.0],[-1.8,.12,.10],.51,.45),([-1.8,.12,.10],[1.1,-.04,.15],.45,.38),([1.1,-.04,.15],[4.1,.10,.05],.38,.26)]
    for a,b,r1,r2 in segments:m.cylinder(a,b,r1,'bark',radius2=r2,sides=14,rough=.15,rng=rng)
    for x,y,z in [(-2.6,.40,.43),(-.7,-.57,.30),(1.6,.43,.40),(2.8,-.4,.18)]:
        m.cylinder([x,0,.15],[x+.30,y,z],.11,'bark',radius2=.025,sides=7,rough=.1,rng=rng)
    # An irregular moss ribbon rides over the curved upper bark, not through it.
    for k in range(8):
        x=-3.7+k*.91;r=.47-k*.022;v=[];f=[];uv=[]
        for j in range(2):
            for i in range(7):
                a=-.62+i*.20;v.append([x+j*.99,np.sin(a)*r,np.cos(a)*r+.115]);uv.append([j,i/6])
        for i in range(6):f.extend([(i,i+7,i+8),(i,i+8,i+1)])
        m.add(v,f,uv,(.99,r*1.2),'moss',(1.02,1.04,.92),smooth=True)
    for k in range(6):
        a=k*np.pi/3;r=.29;m.cylinder([-4,r*np.cos(a),r*np.sin(a)],[-4-rng.uniform(.12,.42),r*np.cos(a)*.8,r*np.sin(a)*.8],.05,'wood',radius2=.001,sides=4)
    return m


def traveller():
    m=Mesh('Traveller_Static','character')
    for x in (-.12,.12):
        m.cylinder([x,0,.17],[x,.01,.71],.074,'coat',sides=8)
        m.box((x,-.065,.08),(.17,.32,.16),'rubber')
    m.cylinder([0,0,.57],[0,0,1.24],.31,'coat',radius2=.21,sides=12)
    m.cylinder([0,0,1.15],[0,0,1.33],.12,'skin',sides=10)
    ellipsoid(m,(0,0,1.47),(.24,.215,.26),'hair',nu=16,nv=10)
    # Bobbed ivory hair with a few broad locks visible from the reference camera.
    for k in range(10):
        a=k*2*np.pi/10;c=[.215*np.cos(a),.192*np.sin(a),1.36]
        m.cylinder([c[0]*.78,c[1]*.78,1.56],c,.067,'hair',radius2=.013,sides=5)
    for side in (-1,1):
        shoulder=[side*.23,0,1.17];elbow=[side*.36,-.025,.91];hand=[side*.39,.03,.71]
        m.cylinder(shoulder,elbow,.079,'coat',radius2=.067,sides=8)
        m.cylinder(elbow,hand,.067,'coat',radius2=.045,sides=7)
        ellipsoid(m,hand,(.05,.05,.066),'skin',nu=8,nv=5)
    # Backpack faces the viewing direction (-Y).
    m.box((0,-.23,.99),(.40,.17,.44),'leather')
    m.box((0,-.332,.91),(.30,.075,.18),'canvas',(.71,.66,.58))
    for x in (-.16,.16):m.box((x,-.341,1.02),(.025,.018,.40),'rust')
    m.cylinder([-.28,.05,.88],[.32,.08,1.06],.025,'leather',sides=5)
    return m


def gull():
    m=Mesh('Gull_Perched','wildlife')
    ellipsoid(m,(0,0,.35),(.19,.29,.23),'flower_white')
    ellipsoid(m,(0,.17,.65),(.12,.13,.14),'hair',nu=12,nv=7)
    m.cylinder([0,.22,.67],[0,.41,.64],.044,'flower_yellow',radius2=.009,sides=6)
    for x in (-.16,.16):ellipsoid(m,(x,0,.39),(.043,.23,.16),'steel',nu=10,nv=7,tint=(1.04,1.06,1.03))
    for x in (-.07,.07):
        m.cylinder([x,0,.21],[x,.025,.04],.016,'flower_yellow',sides=5)
        m.cylinder([x,-.02,.03],[x,.12,.03],.015,'flower_yellow',sides=5)
    ellipsoid(m,(.105,.20,.69),(.013,.014,.014),'rubber',nu=6,nv=4)
    return m
