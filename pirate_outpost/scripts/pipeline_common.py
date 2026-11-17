"""Pure-stdlib data validation and coordinate conversion shared by editor scripts.
Authoring coordinates: metres, X right / Y back / Z up. Front is -Y.
No bpy/unreal imports: this module is independently unit-tested.
"""
from pathlib import Path
from itertools import permutations
import hashlib
import json
import math
import re


def read_json(path):
    with Path(path).open('r',encoding='utf-8') as stream:
        return json.load(stream)


def pack_file(root, relative):
    root=Path(root).expanduser().resolve()
    path=(root/relative).resolve()
    if path!=root and root not in path.parents:
        raise ValueError('Path escapes the asset pack: '+str(relative))
    return path


def manifest_hash(root):
    return hashlib.sha256(pack_file(root,'asset_manifest.json').read_bytes()).hexdigest()


def content_root(path):
    path=str(path).rstrip('/')
    if not re.fullmatch(r'/Game/[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*',path):
        raise ValueError('Use a dedicated content path such as /Game/PirateOutpost')
    return path


def finite_vec(value, label, positive=False):
    if not isinstance(value,(list,tuple)) or len(value)!=3:
        raise ValueError(label+' must contain three numbers')
    v=[float(x) for x in value]
    if not all(math.isfinite(x) and (not positive or x>0) for x in v):
        raise ValueError(label+' contains an invalid number')
    return v


def validate_layout(layout, manifest):
    if layout.get('units')!='metres':
        raise ValueError('Layout units must be metres')
    known={a['id'] for a in manifest['assets']};seen=set()
    if not isinstance(layout.get('instances'),list):
        raise ValueError('Layout instances are missing')
    for o in layout['instances']:
        if o.get('asset') not in known:
            raise ValueError('Unknown layout asset: '+str(o.get('asset')))
        name=o.get('name')
        if not isinstance(name,str) or not name or name in seen:
            raise ValueError('Missing or duplicate instance name: '+str(name))
        seen.add(name)
        finite_vec(o['position_m'],name+' position');finite_vec(o.get('scale',[1,1,1]),name+' scale',True)
        if not math.isfinite(float(o.get('yaw_degrees',0))):
            raise ValueError(name+' yaw is not finite')
    return layout


def infer_basis(bounds_min, bounds_max, tolerance=0.002):
    """Recover a signed axis permutation and engine units/metre from the probe.

    SM_AxisProbe is exactly [0,1] x [0,2] x [0,3] metres in authoring space.
    A centred/reoriented/non-uniformly scaled import is rejected, never guessed.
    """
    lo=finite_vec(list(bounds_min),'probe min');hi=finite_vec(list(bounds_max),'probe max')
    spans=[hi[i]-lo[i] for i in range(3)]
    if min(spans)<=0:
        raise ValueError('Probe has a non-positive extent')
    candidates=[]
    for perm in permutations(range(3)):
        ratios=[spans[i]/(perm[i]+1) for i in range(3)]
        units=sum(ratios)/3
        error=max(abs(x-units)/units for x in ratios)
        candidates.append((error,perm,units))
    error,perm,units=min(candidates)
    if error>tolerance or not .001<=units<=100000:
        raise ValueError('Probe dimensions do not match a uniform 1 x 2 x 3 metre import')
    basis=[[0,0,0] for _ in range(3)]
    for i in range(3):
        eps=max(spans[i]*tolerance,1e-5)
        if abs(lo[i])<=eps and hi[i]>eps:sign=1
        elif abs(hi[i])<=eps and lo[i]<-eps:sign=-1
        else:raise ValueError('Probe pivot was recentered or translated; disable that import option')
        basis[i][perm[i]]=sign
    return {'basis':basis,'units_per_metre':units,'relative_error':error}


def matmul(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def matrix_quaternion(m):
    """Proper 3x3 rotation matrix -> normalized (x,y,z,w), no engine dependency."""
    trace=sum(m[i][i] for i in range(3))
    if trace>0:
        s=math.sqrt(trace+1)*2
        q=[(m[2][1]-m[1][2])/s,(m[0][2]-m[2][0])/s,(m[1][0]-m[0][1])/s,.25*s]
    else:
        i=max(range(3),key=lambda j:m[j][j]);j=(i+1)%3;k=(i+2)%3
        s=math.sqrt(max(0,1+m[i][i]-m[j][j]-m[k][k]))*2
        if s<1e-12:raise ValueError('Invalid rotation matrix')
        q=[0.,0.,0.,0.];q[i]=.25*s;q[j]=(m[j][i]+m[i][j])/s;q[k]=(m[k][i]+m[i][k])/s;q[3]=(m[k][j]-m[j][k])/s
    length=math.sqrt(sum(v*v for v in q));q=[v/length for v in q]
    return q if q[3]>=0 else [-v for v in q]


def to_unreal_transform(position_m, yaw_degrees, scale, calibration):
    p=finite_vec(position_m,'position');s=finite_vec(scale,'scale',True);yaw=float(yaw_degrees)
    if not math.isfinite(yaw):raise ValueError('Yaw must be finite')
    f=calibration['basis'];units=float(calibration['units_per_metre'])
    if units<=0 or not math.isfinite(units):raise ValueError('Invalid calibrated scale')
    if len(f)!=3 or any(len(row)!=3 or sum(abs(x) for x in row)!=1 for row in f) or any(sum(abs(f[i][j]) for i in range(3))!=1 for j in range(3)):
        raise ValueError('Calibration basis is not a signed permutation')
    position=[100*sum(f[i][j]*p[j] for j in range(3)) for i in range(3)]
    c,si=math.cos(math.radians(yaw)),math.sin(math.radians(yaw))
    rz=[[c,-si,0],[si,c,0],[0,0,1]]
    rot=matmul(matmul(f,rz),[list(x) for x in zip(*f)])
    actor_scale=[100/units*sum(abs(f[i][j])*s[j] for j in range(3)) for i in range(3)]
    return {'position_cm':position,'quaternion_xyzw':matrix_quaternion(rot),'scale':actor_scale}


def expected_bounds(source_bounds, basis, units_per_metre=100.):
    lo,hi=source_bounds
    corners=[[units_per_metre*sum(basis[i][j]*p[j] for j in range(3)) for i in range(3)]
             for p in ((x,y,z) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]])]
    return ([min(p[i] for p in corners) for i in range(3)],
            [max(p[i] for p in corners) for i in range(3)])
