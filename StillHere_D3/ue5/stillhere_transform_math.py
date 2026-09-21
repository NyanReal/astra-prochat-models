"""Pure-Python coordinate conversion, independently testable without Unreal.

Canonical scene = RH metres/Z-up. Target world = UE centimetres, X,-Y,Z.
Actual GLB import basis is measured from three offset calibration meshes.
"""
import math

WORLD_BASIS=[[100.,0.,0.],[0.,-100.,0.],[0.,0.,100.]]

def transpose(a):return [list(x) for x in zip(*a)]
def mm(a,b):return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def mv(a,v):return [sum(a[i][j]*v[j] for j in range(3)) for i in range(3)]
def norm(v):return math.sqrt(sum(x*x for x in v))
def unit(v):
    n=norm(v)
    if n<1e-12:raise ValueError('Zero-length direction')
    return [x/n for x in v]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def det(a):return a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])-a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])+a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0])
def inverse(a):
    d=det(a)
    if abs(d)<1e-10:raise ValueError('Singular import calibration')
    # Explicit adjugate avoids cyclic-minor sign mistakes.
    return [[(a[1][1]*a[2][2]-a[1][2]*a[2][1])/d,(a[0][2]*a[2][1]-a[0][1]*a[2][2])/d,(a[0][1]*a[1][2]-a[0][2]*a[1][1])/d],
            [(a[1][2]*a[2][0]-a[1][0]*a[2][2])/d,(a[0][0]*a[2][2]-a[0][2]*a[2][0])/d,(a[0][2]*a[1][0]-a[0][0]*a[1][2])/d],
            [(a[1][0]*a[2][1]-a[1][1]*a[2][0])/d,(a[0][1]*a[2][0]-a[0][0]*a[2][1])/d,(a[0][0]*a[1][1]-a[0][1]*a[1][0])/d]]

def rotation(euler):
    a,b,c=[math.radians(x) for x in euler];ca,sa=math.cos(a),math.sin(a);cb,sb=math.cos(b),math.sin(b);cc,sc=math.cos(c),math.sin(c)
    return mm(mm([[cc,-sc,0],[sc,cc,0],[0,0,1]],[[cb,0,sb],[0,1,0],[-sb,0,cb]]),[[1,0,0],[0,ca,-sa],[0,sa,ca]])

def quaternion(m):
    trace=sum(m[i][i] for i in range(3))
    if trace>0:
        s=math.sqrt(trace+1.)*2;q=[(m[2][1]-m[1][2])/s,(m[0][2]-m[2][0])/s,(m[1][0]-m[0][1])/s,.25*s]
    else:
        i=max(range(3),key=lambda i:m[i][i])
        if i==0:
            s=math.sqrt(1.+m[0][0]-m[1][1]-m[2][2])*2;q=[.25*s,(m[0][1]+m[1][0])/s,(m[0][2]+m[2][0])/s,(m[2][1]-m[1][2])/s]
        elif i==1:
            s=math.sqrt(1.+m[1][1]-m[0][0]-m[2][2])*2;q=[(m[0][1]+m[1][0])/s,.25*s,(m[1][2]+m[2][1])/s,(m[0][2]-m[2][0])/s]
        else:
            s=math.sqrt(1.+m[2][2]-m[0][0]-m[1][1])*2;q=[(m[0][2]+m[2][0])/s,(m[1][2]+m[2][1])/s,.25*s,(m[1][0]-m[0][1])/s]
    n=norm(q);return [x/n for x in q]

def quaternion_matrix(q):
    x,y,z,w=q
    return [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
            [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
            [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]

def calibrate(probe_centres):
    if len(probe_centres)!=3:raise ValueError('Exactly three probe centres are required')
    raw=transpose(probe_centres);lengths=[norm(c) for c in probe_centres]
    if min(lengths)<.01:raise ValueError('Importer recentered a calibration mesh. Disable pivot recentering and retry.')
    scale=sum(lengths)/3
    if max(abs(x-scale) for x in lengths)>scale*.002:raise ValueError('Non-uniform import unit scale')
    for col in probe_centres:
        if sum(abs(x/scale)>1e-3 for x in col)!=1:raise ValueError('Importer applied a non-axis-aligned rotation; use default glTF import transforms.')
    inv=inverse(raw)
    return {'import_basis':raw,'inverse_import_basis':inv,'world_basis':WORLD_BASIS,
            'import_units_per_metre':scale,'target_centimetres_per_metre':100.,'import_determinant':det(raw)}

def convert_instance(rec,calibration):
    r=rotation(rec['rotation_euler_xyz_deg']);s=rec['scale'];rs=[[r[i][j]*s[j] for j in range(3)] for i in range(3)]
    linear=mm(mm(WORLD_BASIS,rs),calibration['inverse_import_basis'])
    scales=[norm([linear[i][j] for i in range(3)]) for j in range(3)]
    if min(scales)<1e-8:raise ValueError('Zero instance scale: '+rec.get('id','unknown'))
    if det(linear)<0:scales[1]*=-1
    rot=[[linear[i][j]/scales[j] for j in range(3)] for i in range(3)]
    check=mm(transpose(rot),rot)
    if max(abs(check[i][j]-(1 if i==j else 0)) for i in range(3) for j in range(3))>1e-4:raise ValueError('Transform requires shear; source import axes are unsupported')
    return {'position_cm':mv(WORLD_BASIS,rec['position_m']),'quaternion_xyzw':quaternion(rot),'scale':scales}

def camera_transform(camera):
    f=unit([b-a for a,b in zip(camera['position_m'],camera['target_m'])]);r=unit(cross(f,camera['up']));up=unit(cross(r,f))
    cols=[unit(mv(WORLD_BASIS,v)) for v in (f,r,up)];rot=transpose(cols)
    if det(rot)<.99:raise ValueError('Camera basis is not a proper Unreal rotation')
    return {'position_cm':mv(WORLD_BASIS,camera['position_m']),'quaternion_xyzw':quaternion(rot),'ortho_width_cm':camera['ortho_width_m']*100.}
