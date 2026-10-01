"""Small deterministic mesh-authoring kernel. Coordinates: +Y up, +Z forward (glTF).
Every patch receives its own UV island. No texture coordinates are shared by copies.
"""
from dataclasses import dataclass, field
from math import pi
import numpy as np
from scipy.spatial.transform import Rotation
from shapely.geometry import Polygon, LineString
from shapely.geometry.polygon import orient

@dataclass
class Patch:
    name: str
    positions: np.ndarray
    normals: np.ndarray
    uv: np.ndarray
    faces: np.ndarray
    category: str
    color: tuple
    material: str = 'Paint'
    detail: str = ''
    aspect: float = 1.
    rect: tuple | None = None
    node: int = 0
    @property
    def area(self):
        p=self.positions[self.faces]
        return float(np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1).sum()*.5)

class Scene:
    def __init__(self):
        self.nodes=[];self.patches=[]
        self.add_node('HOPPER_03_TORSO_v3',None)
    def add_node(self,name,parent=0,translation=(0,0,0),rotation=(0,0,0,1),scale=(1,1,1)):
        node={'name':name,'translation':list(translation),'rotation':list(rotation),'scale':list(scale)}
        idx=len(self.nodes);self.nodes.append(node)
        if parent is not None:self.nodes[parent].setdefault('children',[]).append(idx)
        return idx
    def add(self,name,parts,node=0,category='armor',color=(217,211,192),material='Paint',detail='',loc=(0,0,0),rot=(0,0,0),scale=(1,1,1)):
        r=Rotation.from_euler('xyz',rot,degrees=True).as_matrix()
        scale=np.array(scale,float);loc=np.array(loc,float)
        for side,p,n,uv,f,aspect in parts:
            p=np.asarray(p,dtype=float)*scale
            p=p@r.T+loc
            n=(np.asarray(n,dtype=float)/scale)@r.T
            n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
            f=np.asarray(f,dtype=np.uint32)
            a=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1)
            f=f[a>1e-11]
            cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
            bad=np.einsum('ij,ij->i',cross,n[f].mean(axis=1))<0
            f[bad]=f[bad][:,[0,2,1]]
            d=detail.get(side,'') if isinstance(detail,dict) else (detail if side in ('front','surface','+Z') else '')
            self.patches.append(Patch(name+'__'+side,p,n,np.asarray(uv,float),f,category,color,material,d,float(aspect),node=node))
    def box(self,name,size,radius=.08,**kw): self.add(name,rounded_box(size,radius),**kw)
    def ellipsoid(self,name,radii,segments=12,rings=8,**kw): self.add(name,ellipsoid(radii,segments,rings),**kw)
    def plate(self,name,outline,depth=.22,bevel=.065,N=16,**kw):
        bulge=min(.095,bevel*.72) if kw.get('category','armor')=='armor' else 0.
        self.add(name,plate(outline,depth,bevel,N=N,bulge=bulge),**kw)
    def cylinder(self,name,radius,length,segments=12,caps=2,**kw):
        parts=cylinder(radius,length,segments)
        if caps==0:parts=parts[:1]
        elif caps==1:parts=[parts[0],parts[2]]
        self.add(name,parts,**kw)
    def between(self,name,a,b,radius,segments=10,**kw):
        a=np.asarray(a);b=np.asarray(b);d=b-a;l=np.linalg.norm(d)
        q=align_y(d); rot=Rotation.from_quat(q).as_euler('xyz',degrees=True)
        self.cylinder(name,radius,l,segments,caps=0,loc=(a+b)*.5,rot=rot,**kw)
    def tube(self,name,points,radius=.035,sides=6,smooth=2,**kw):self.add(name,tube(points,radius,sides,smooth),**kw)

def quadgrid(nu,nv):
    fs=[]
    for j in range(nv-1):
        for i in range(nu-1):
            a=j*nu+i;b=a+1;c=a+nu;d=c+1
            fs.extend([(a,b,d),(a,d,c)])
    return np.array(fs,dtype=np.uint32)

def rounded_box(size,radius,steps=1):
    """44-triangle chamfer box, flat main faces and smooth bevel normals.
    Six planar face islands plus disjoint local UVs for the 20 bevel faces.
    Unlike a subdivided cube, broad flat surfaces get exactly two triangles.
    """
    import itertools
    h=np.array(size,float)*.5;r=min(float(radius),float(h.min())*.94)
    plain=radius<=0
    r=max(r,1e-6);b=h if plain else h-r
    def pt(sign,axis):
        pp=np.array(sign)*b;pp[axis]=sign[axis]*h[axis]
        nn=np.zeros(3);nn[axis]=sign[axis]
        return pp,nn
    out=[];edgeparts=[]
    for axis in range(3):
        axes=[i for i in range(3) if i!=axis]
        for sign in [-1,1]:
            positions=[];normals=[]
            for a,c in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                ss=[0,0,0];ss[axis]=sign;ss[axes[0]]=a;ss[axes[1]]=c
                pp,nn=pt(ss,axis);positions.append(pp);normals.append(nn)
            pp=np.array(positions);nn=np.array(normals)
            side=('+' if sign>0 else '-')+'XYZ'[axis]
            uv=np.array([[0,1],[1,1],[1,0],[0,0]],float)
            # Mirror physical horizontal coordinate on back-facing views.
            if (axis==2 and sign<0) or (axis==0 and sign>0):uv[:,0]=1-uv[:,0]
            out.append((side,pp,nn,uv,np.array([[0,1,2],[0,2,3]],dtype=np.uint32),max(1e-4,b[axes[0]])/max(1e-4,b[axes[1]])))
    if plain:return out
    # 12 bevel edge quads.
    for free_axis in range(3):
        aa,bb=[a for a in range(3) if a!=free_axis]
        for sa,sb in itertools.product([-1,1],repeat=2):
            ps=[];ns=[]
            for sf,face in [(-1,aa),(1,aa),(1,bb),(-1,bb)]:
                sign=[0,0,0];sign[aa]=sa;sign[bb]=sb;sign[free_axis]=sf
                pp,nn=pt(sign,face);ps.append(pp);ns.append(nn)
            edgeparts.append((ps,ns,[[0,0],[1,0],[1,1],[0,1]],[[0,1,2],[0,2,3]]))
    # 8 trihedral corner triangles.
    for ss in itertools.product([-1,1],repeat=3):
        ps=[];ns=[]
        for ax in range(3):
            pp,nn=pt(ss,ax);ps.append(pp);ns.append(nn)
        edgeparts.append((ps,ns,[[0,0],[1,0],[.5,1]],[[0,1,2]]))
    ps=[];ns=[];uv=[];ff=[]
    for i,(pp,nn,uu,faces) in enumerate(edgeparts):
        offset=len(ps);ps.extend(pp);ns.extend(nn)
        # Non-overlapping internal tiles, with a small separation for gutters.
        uv.extend((np.array(uu)*.90+.05+np.array([i%5,i//5]))/np.array([5,4]))
        ff.extend(np.array(faces)+offset)
    out.append(('bevels',np.array(ps),np.array(ns),np.array(uv),np.array(ff,dtype=np.uint32),1.25))
    return out

def ellipsoid(radii,segments=24,rings=14):
    r=np.array(radii);p=[];n=[];uv=[]
    for j in range(rings+1):
        phi=pi*j/rings
        for i in range(segments+1):
            theta=2*pi*i/segments
            d=np.array([np.sin(phi)*np.sin(theta),np.cos(phi),np.sin(phi)*np.cos(theta)])
            p.append(d*r);nn=d/r;nn/=np.linalg.norm(nn);n.append(nn);uv.append((i/segments,j/rings))
    f=quadgrid(segments+1,rings+1)
    # The increasing longitude / latitude convention has outward winding.
    pp=np.array(p);nn=np.array(n)
    fc=f[len(f)//2];cross=np.cross(pp[fc[1]]-pp[fc[0]],pp[fc[2]]-pp[fc[0]])
    if np.dot(cross,nn[fc].mean(axis=0))<0:f=f[:,[0,2,1]]
    return [('surface',pp,nn,np.array(uv),f,2*(r[0]+r[2])/(2*r[1]))]

def cylinder(radius,length,segments=24):
    p=[];n=[];uv=[]
    for j,y in enumerate([-length*.5,length*.5]):
        for i in range(segments+1):
            t=i*2*pi/segments;d=np.array([np.sin(t),0,np.cos(t)])
            p.append(d*radius+[0,y,0]);n.append(d);uv.append((i/segments,1-j))
    out=[('side',np.array(p),np.array(n),np.array(uv),quadgrid(segments+1,2),2*pi*radius/length)]
    for top in [False,True]:
        y=(.5 if top else -.5)*length;d=1 if top else -1
        pp=[[0,y,0]];uu=[(.5,.5)];ff=[]
        for i in range(segments):
            t=i*2*pi/segments;pp.append([radius*np.sin(t),y,radius*np.cos(t)]);uu.append((.5+.5*np.sin(t),.5+.5*np.cos(t)))
        for i in range(segments):
            tri=(0,i+1,(i+1)%segments+1)
            ff.append(tri if top else (tri[0],tri[2],tri[1]))
        out.append(('cap_top' if top else 'cap_bottom',np.array(pp),np.tile([0,d,0],(len(pp),1)),np.array(uu),np.array(ff),1))
    return out

def _radial_outline(poly,angles):
    c=np.array(poly.centroid.coords[0]);R=max(np.ptp(np.array(poly.exterior.coords),axis=0))*3
    pts=[]
    for t in angles:
        endpoint=c+R*np.array([np.cos(t),np.sin(t)])
        line=LineString([c,endpoint]);hit=poly.intersection(line)
        coords=np.array(hit.coords);pts.append(coords[-1])
    return np.array(pts)

def plate(outline,depth,bevel,N=16,bulge=0.):
    poly=orient(Polygon(outline),sign=1.0)
    r=min(bevel,depth*.45);h=depth*.5
    angles=np.linspace(0,2*pi,N,endpoint=False)
    alpha=[0,pi/2,pi/2,pi]
    rings=[];norms=[];xy0=None
    for k,a in enumerate(alpha):
        off=-r+r*np.sin(a);q=poly.buffer(off,join_style=1,quad_segs=3)
        if q.is_empty:q=poly
        xy=_radial_outline(q,angles)
        tangent=np.roll(xy,-1,axis=0)-np.roll(xy,1,axis=0)
        outward=np.c_[tangent[:,1],-tangent[:,0]];outward/=np.linalg.norm(outward,axis=1,keepdims=True)
        z=(h-r+r*np.cos(a)) if k<2 else (-h+r+r*np.cos(a))
        rings.append(np.c_[xy,np.full(N,z)])
        norms.append(np.c_[outward*np.sin(a),np.full(N,np.cos(a))])
    out=[];b=np.array(poly.bounds);extent=b[2:]-b[:2]
    for front,idx in [(True,0),(False,-1)]:
        ring=rings[idx];center=ring.mean(axis=0);sgn=1 if front else -1
        puff=bulge*(1. if front else .55)
        if puff>0 and front:
            points=[center.copy()];faces=[]
            for k in range(1,3):
                rr=k/2
                layer=center+(ring-center)*rr;points.extend(layer)
            for j in range(N):faces.append((0,1+j,1+(j+1)%N))
            for k in range(1):
                aa=1+k*N;bb=aa+N
                for j in range(N):
                    nj=(j+1)%N;faces.extend([(aa+j,bb+j,bb+nj),(aa+j,bb+nj,aa+nj)])
            p=np.array(points);f=np.array(faces,dtype=np.uint32)
            if not front:f=f[:,[0,2,1]]
            n=np.tile([0.,0.,float(sgn)],(len(p),1))
        else:
            p=np.vstack([center,ring]);n=np.tile([0,0,sgn],(len(p),1));f=[]
            for j in range(N):
                tri=(0,j+1,(j+1)%N+1);f.append(tri if front else (tri[0],tri[2],tri[1]))
            f=np.array(f)
        uv=(p[:,:2]-b[:2])/extent;uv[:,1]=1-uv[:,1]
        out.append(('front' if front else 'back',p,n,uv,f,extent[0]/extent[1]))
    p=[];n=[];uv=[]
    for k,(ring,ns) in enumerate(zip(rings,norms)):
        for j in range(N+1):p.append(ring[j%N]);n.append(ns[j%N]);uv.append((j/N,k/(len(rings)-1)))
    f=quadgrid(N+1,len(rings))
    # Ring direction is counterclockwise; from front to back => outward.
    out.append(('beveled_edge',np.array(p),np.array(n),np.array(uv),f,poly.length/(depth+pi*r)))
    if bulge>0:
        # A smooth quadratic bow, not a polygon-normalized pillow. Apply the same
        # deformation to every patch and inverse-transpose its Jacobian to normals.
        cx,cy=(b[:2]+b[2:])*.5;ax,ay=extent*.5
        curved=[]
        for name,pp,nn,uu,ff,aspect in out:
            pp=pp.copy();nn=nn.astype(float).copy();dx=pp[:,0]-cx;dy=pp[:,1]-cy
            pp[:,2]+=bulge*(1-(dx/ax)**2-(dy/ay)**2)
            gx=-2*bulge*dx/(ax*ax);gy=-2*bulge*dy/(ay*ay)
            nn[:,0]-=gx*nn[:,2];nn[:,1]-=gy*nn[:,2];nn/=np.linalg.norm(nn,axis=1,keepdims=True)
            curved.append((name,pp,nn,uu,ff,aspect))
        out=curved
    return out

def smooth_path(points,steps=2):
    pts=np.array(points,float)
    if steps<=1:return pts
    closed=np.allclose(pts[0],pts[-1],atol=1e-9)
    base=pts[:-1] if closed else pts;n=len(base);out=[]
    count=n if closed else n-1
    for i in range(count):
        p0=base[(i-1)%n] if closed else base[max(0,i-1)]
        p1=base[i];p2=base[(i+1)%n];p3=base[(i+2)%n] if closed else base[min(n-1,i+2)]
        for j in range(steps):
            t=j/steps
            out.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    out.append(base[0] if closed else base[-1])
    return np.array(out)

def tube(points,radius=.035,sides=6,smooth=2):
    """Parallel-transport tube frames; cyclic splines meet without twist/cracks."""
    path=smooth_path(points,smooth);closed=np.allclose(path[0],path[-1],atol=1e-9)
    tangents=[]
    for j in range(len(path)):
        if closed:
            jj=j%(len(path)-1);t=path[(jj+1)%(len(path)-1)]-path[(jj-1)%(len(path)-1)]
        else:t=path[min(j+1,len(path)-1)]-path[max(j-1,0)]
        tangents.append(t/max(np.linalg.norm(t),1e-12))
    tangents=np.array(tangents);ref=np.eye(3)[np.argmin(np.abs(tangents[0]))]
    u=np.cross(tangents[0],ref);u/=np.linalg.norm(u);frames=[u.copy()]
    for j in range(1,len(path)):
        old=tangents[j-1];new=tangents[j];axis=np.cross(old,new);sn=np.linalg.norm(axis);cs=np.dot(old,new)
        if sn>1e-10:
            axis/=sn
            u=u*cs+np.cross(axis,u)*sn+axis*np.dot(axis,u)*(1-cs)
        u-=new*np.dot(new,u);u/=max(np.linalg.norm(u),1e-12);frames.append(u.copy())
    lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))];L=lengths[-1]
    frames=np.array(frames)
    if closed:
        # Remove accumulated holonomy continuously, rather than forcing a final twist.
        a=frames[-1];b=frames[0];axis=tangents[0]
        angle=np.arctan2(np.dot(axis,np.cross(a,b)),np.dot(a,b))
        for j in range(len(path)):
            t=angle*lengths[j]/L;axis=tangents[j];u=frames[j]
            frames[j]=u*np.cos(t)+np.cross(axis,u)*np.sin(t)+axis*np.dot(axis,u)*(1-np.cos(t))
        frames[-1]=frames[0];tangents[-1]=tangents[0]
    p=[];n=[];uv=[]
    for j,point in enumerate(path):
        u=frames[j];v=np.cross(u,tangents[j])
        for i in range(sides+1):
            a=2*pi*i/sides;d=u*np.cos(a)+v*np.sin(a)
            p.append(point+d*radius);n.append(d);uv.append((i/sides,lengths[j]/L))
    p=np.array(p);n=np.array(n);f=quadgrid(sides+1,len(path))
    return [('surface',p,n,np.array(uv),f,2*pi*radius/L)]

def align_y(direction):
    d=np.array(direction,float);d/=np.linalg.norm(d);y=np.array([0.,1,0]);dot=float(np.dot(y,d))
    if dot<-.999999:return np.array([1.,0,0,0])
    q=np.r_[np.cross(y,d),1+dot];q/=np.linalg.norm(q);return q


def lathe(profile,segments=16):
    """Revolve (radius, Y) profile, preserving profile creases and UV uniqueness."""
    out=[]
    for k,((r0,y0),(r1,y1)) in enumerate(zip(profile,profile[1:])):
        p=[];n=[];uv=[];dr=r1-r0;dy=y1-y0
        length=np.hypot(dr,dy)
        if length<1e-8:continue
        for j,(radius,yy) in enumerate([(r0,y0),(r1,y1)]):
            for i in range(segments+1):
                t=2*pi*i/segments;rad=np.array([np.sin(t),0,np.cos(t)])
                p.append(rad*radius+[0,yy,0]);n.append((rad*dy+[0,-dr,0])/length);uv.append([i/segments,j])
        out.append(('ring_'+str(k),np.array(p),np.array(n),np.array(uv),quadgrid(segments+1,2),max(2*pi*(r0+r1)/2,1e-4)/length))
    return out
