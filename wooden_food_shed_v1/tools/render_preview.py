#!/usr/bin/env python3
"""CPU raster previews of the ACTUAL delivered mesh, not generated illustrations.
Dependencies: numpy, numba, scipy, Pillow. Ground and lights are preview-only.
"""
from pathlib import Path
import json, math, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter
from numba import njit
ROOT=Path(__file__).resolve().parents[1]

def unit(v):v=np.array(v,float);return v/np.linalg.norm(v)

def project(p,eye,target,width,height,scale):
    f=unit(np.array(target)-eye);r=unit(np.cross(f,[0,0,1]));u=np.cross(r,f)
    q=np.array(p)-np.array(target)
    out=np.stack([q@r*width/scale+width/2,-q@u*width/scale+height/2,q@f],-1)
    mat=np.stack([r,u,f]);return out.astype(np.float32),mat.astype(np.float32)

@njit(cache=True)
def raster(v,tri,width,height,cull):
    z=np.full((height,width),1e9,np.float32);ids=np.full((height,width),-1,np.int32)
    weights=np.zeros((height,width,2),np.float32)
    for i in range(len(tri)):
        ia,ib,ic=tri[i];a=v[ia];b=v[ib];c=v[ic]
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-7 or (cull and den>0):continue
        xa=max(0,int(math.floor(min(a[0],b[0],c[0]))));xb=min(width-1,int(math.ceil(max(a[0],b[0],c[0]))))
        ya=max(0,int(math.floor(min(a[1],b[1],c[1]))));yb=min(height-1,int(math.ceil(max(a[1],b[1],c[1]))))
        for y in range(ya,yb+1):
            for x in range(xa,xb+1):
                w0=((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/den
                w1=((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/den
                w2=1-w0-w1
                if min(w0,w1,w2)<-.0001:continue
                zz=w0*a[2]+w1*b[2]+w2*c[2]
                if zz<z[y,x]:z[y,x]=zz;ids[y,x]=i;weights[y,x,0]=w0;weights[y,x,1]=w1
    return z,ids,weights

@njit(cache=True)
def sample(im,u,v):
    h,w,ch=im.shape;x=min(w-1,max(0,u*(w-1)));y=min(h-1,max(0,(1-v)*(h-1)))
    x0=int(x);y0=int(y);x1=min(x0+1,w-1);y1=min(y0+1,h-1);a=x-x0;b=y-y0
    return im[y0,x0]*(1-a)*(1-b)+im[y0,x1]*a*(1-b)+im[y1,x0]*(1-a)*b+im[y1,x1]*a*b

@njit(cache=True)
def visibility(point,normal,shadow,mat,target,span):
    n=shadow.shape[0];q=point-target
    sx=(q[0]*mat[0,0]+q[1]*mat[0,1]+q[2]*mat[0,2])*n/span+n/2
    sy=-(q[0]*mat[1,0]+q[1]*mat[1,1]+q[2]*mat[1,2])*n/span+n/2
    depth=q[0]*mat[2,0]+q[1]*mat[2,1]+q[2]*mat[2,2]
    count=0.;total=0.
    for oy in range(-2,3):
        for ox in range(-2,3):
            x=int(sx+ox*3.4);y=int(sy+oy*3.4)
            if 0<=x<n and 0<=y<n:
                count+=1
                nf=normal[0]*mat[2,0]+normal[1]*mat[2,1]+normal[2]*mat[2,2]
                plane_delta=0.
                if abs(nf)>.12:
                    nr=normal[0]*mat[0,0]+normal[1]*mat[0,1]+normal[2]*mat[0,2]
                    nu=normal[0]*mat[1,0]+normal[1]*mat[1,1]+normal[2]*mat[1,2]
                    plane_delta=-(nr*(x+.5-sx)-nu*(y+.5-sy))*span/n/nf
                if depth+plane_delta<=shadow[y,x]+.006:total+=1
    return total/count if count>0 else 1.

@njit(cache=True)
def shade(ids,weights,tri,p,normals,tans,uvs,lods,base,orm,emit,nmap,shadows,smats,starget,sspan,dirs,eye):
    H,W=ids.shape;rgb=np.zeros((H,W,3),np.float32);glow=np.zeros_like(rgb)
    for y in range(H):
        for x in range(W):
            face=ids[y,x]
            if face<0:
                t=y/H;rgb[y,x]=np.array([.072+.018*t,.085+.02*t,.091+.024*t]);continue
            a,b,c=tri[face];w0,w1=weights[y,x];w2=1-w0-w1
            pnt=p[a]*w0+p[b]*w1+p[c]*w2
            n=normals[a]*w0+normals[b]*w1+normals[c]*w2
            n=n/max(np.sqrt((n*n).sum()),1e-7)
            uv=uvs[a]*w0+uvs[b]*w1+uvs[c]*w2
            if uv[0]<-1:
                albedo=np.array([.205,.23,.228]);rough=.92;metal=0.;ao=1.;em=np.zeros(3)
            else:
                albedo=sample(base[lods[face]],uv[0],uv[1])**2.2
                props=sample(orm[lods[face]],uv[0],uv[1]);ao=props[0];rough=props[1];metal=props[2]
                em=sample(emit[lods[face]],uv[0],uv[1])**2.2*2.3
                ts=sample(nmap[lods[face]],uv[0],uv[1])*2-1
                ts[:2]*=.40
                t=tans[a,:3];bvec=np.array([n[1]*t[2]-n[2]*t[1],n[2]*t[0]-n[0]*t[2],n[0]*t[1]-n[1]*t[0]])
                nn=t*ts[0]+bvec*ts[1]+n*ts[2];n=nn/max(np.sqrt((nn*nn).sum()),1e-7)
            vis0=visibility(pnt,normals[a],shadows[0],smats[0],starget,sspan)
            vis1=visibility(pnt,normals[a],shadows[1],smats[1],starget,sspan)
            vis2=visibility(pnt,normals[a],shadows[2],smats[2],starget,sspan)
            nd0=max(0.,(n*dirs[0]).sum());nd1=max(0.,(n*dirs[1]).sum());nd2=max(0.,(n*dirs[2]).sum())
            ambient=(.17+.18*max(0.,n[2]))*(.60+.40*(vis1+vis2)/2)
            light=np.array([1.10,1.02,.85])*nd0*vis0*1.00+np.array([.82,.92,1.07])*nd1*vis1*.26+np.array([.92,1.00,.99])*nd2*vis2*.23+ambient
            col=albedo*light*ao
            # Modest rough Fresnel lobe; weathered timber should not look wet.
            view=eye-pnt;view/=max(np.sqrt((view*view).sum()),1e-6)
            halfv=view+dirs[0];halfv/=max(np.sqrt((halfv*halfv).sum()),1e-6)
            spec=max(0.,(n*halfv).sum())**(8.+(1-rough)*40)
            col+=np.array([1.,.95,.81])*spec*vis0*(.017+metal*.16)
            # Preview-only point light behind amber panes.
            lp=np.array([1.47,-1.53,2.075])-pnt;dist=np.sqrt((lp*lp).sum());lp/=max(dist,.01)
            col+=albedo*np.array([1.,.48,.12])*max(0.,(n*lp).sum())*.16/(.12+dist*dist)
            col+=em
            rgb[y,x]=col;glow[y,x]=em
    return rgb,glow

def load_geometry(exclude_roof=False,closed=False):
    data=json.loads((ROOT/'source/mesh_payload.json').read_text());P=[];N=[];U=[];T=[];F=[];groups=[]
    for o in data['objects']:
        if exclude_roof and o['name'].startswith('Roof_'):continue
        p=np.array(o['positions']);n=np.array(o['normals']);t=np.array(o['tangents'])
        if closed and o['name'].startswith(('Door_','Handle_')):
            side=o['name'].split('_',1)[1];angle=math.radians(105 if side=='Left' else -100)
            r=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
            hinge=np.array([-1.355 if side=='Left' else 1.355,-1.205,.37]);p=(p-hinge)@r.T+hinge;n=n@r.T;t[:,:3]=t[:,:3]@r.T
        off=len(P);P.extend(p);N.extend(n);U.extend(o['uvs']);T.extend(t);F.extend(np.array(o['triangles'])+off);groups.extend([o['name']]*len(o['triangles']))
    asset_faces=len(F)
    off=len(P);P.extend([[-200,-200,-.006],[200,-200,-.006],[200,200,-.006],[-200,200,-.006]]);N.extend([[0,0,1]]*4);U.extend([[-2,-2]]*4);T.extend([[1,0,0,1]]*4);F.extend([[off,off+1,off+2],[off,off+2,off+3]])
    return [np.array(a,np.float32) for a in [P,N,U,T]]+[np.array(F,np.int32),asset_faces,groups]

def render(view='hero',width=1440,height=1200):
    cut=view=='interior';closed=view=='closed';p,n,uv,t,tri,asset_faces,groups=load_geometry(cut,closed)
    views={
        'hero':([6.0,-11.5,5.8],[.15,-.25,1.42],6.35),
        'topdown':([7,-10,12.5],[.18,-.15,1.28],6.5),
        'interior':([5,-8,8],[.05,-.06,1.25],5.8),
        'closed':([6.0,-11.5,5.8],[.15,-.25,1.42],6.35),
        'rear':([-6,10,6.5],[.10,-.02,1.50],6.0),
        'front':([0,-14,4.6],[.12,-.20,1.47],6.10),
    }
    eye,target,scale=views[view];eye=np.array(eye,np.float32)
    proj,mat=project(p,eye,target,width,height,scale)
    # Fit the actual asset bounds, excluding the infinite preview ground.
    ids_used=np.unique(tri[:asset_faces])
    q=proj[ids_used,:2];lo=q.min(0);hi=q.max(0);center=(lo+hi)/2
    offset=mat[0]*((center[0]-width/2)*scale/width)-mat[1]*((center[1]-height/2)*scale/width)
    target=np.array(target)+offset;eye=eye+offset
    scale*=max(1.,(hi[0]-lo[0])/(width*.88),(hi[1]-lo[1])/(height*.88))
    proj,mat=project(p,eye,target,width,height,scale)
    depth,ids,weights=raster(proj,tri,width,height,False)
    print('view raster',view,flush=True)
    dirs=np.array([unit([-3.6,-5.3,8]),unit([5,-1.5,7]),unit([-3,5,8])],np.float32)
    starget=np.array([0,0,1.3],np.float32);span=8.4;sh=[];sm=[]
    for d in dirs:
        v,m=project(p,d*10+starget,starget,1400,1400,span);z,_,_=raster(v,tri[:asset_faces],1400,1400,False);sh.append(z);sm.append(m)
    from numba.typed import List
    tex=[]
    for filename in ['T_Shed_BaseColor.png','T_Shed_ORM.png','T_Shed_Emissive.png','T_Shed_Normal_GL.png']:
        image=Image.open(ROOT/'textures'/filename).convert('RGB')
        levels=List()
        for level in range(6):
            size=4096//(2**level)
            levels.append(np.array(image.resize((size,size),Image.Resampling.BOX),np.float32)/255)
        tex.append(levels)
    lods=np.zeros(len(tri),np.int32)
    for i,f in enumerate(tri[:asset_faces]):
        a=proj[f,:2];v=uv[f]
        try:
            gradient=np.linalg.solve(np.stack([a[1]-a[0],a[2]-a[0]]),np.stack([v[1]-v[0],v[2]-v[0]]))
            rho=float(np.max(np.linalg.norm(gradient,axis=1)))*4096
            lods[i]=min(5,max(0,int(math.log2(max(1.,rho))+.25)))
        except np.linalg.LinAlgError:lods[i]=0
    print('mipmap LOD range',int(lods.min()),int(lods.max()),flush=True)
    rgb,glow=shade(ids,weights,tri,p,n,t,uv,lods,*tex,np.array(sh),np.array(sm),starget,span,dirs,eye)
    rgb+=gaussian_filter(glow,(7,7,0))*.24+gaussian_filter(glow,(22,22,0))*.14
    # Smooth highlight roll-off, then linear-to-display conversion.
    rgb=np.clip(rgb,0,None);rgb=rgb/(1+rgb*.26);rgb=np.clip(rgb,0,1)**(1/2.2)
    im=Image.fromarray((rgb*255).astype('uint8'))
    im.save(ROOT/f'previews/{view}.png')
    if view=='hero':
        wire=im.copy();dr=ImageDraw.Draw(wire)
        for i,f in enumerate(tri[:asset_faces]):
            a=proj[f];mid=a.mean(0);x,y=int(mid[0]),int(mid[1])
            if 0<=x<width and 0<=y<height and mid[2]<depth[y,x]+.035:
                pts=[(float(q[0]),float(q[1])) for q in a];dr.line(pts+[pts[0]],fill=(84,225,210),width=1)
        wire.save(ROOT/'previews/wireframe.png')
    print('saved',ROOT/f'previews/{view}.png',flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--view',default='hero');a.add_argument('--width',type=int,default=1440);a.add_argument('--height',type=int,default=1200);o=a.parse_args();render(o.view,o.width,o.height)
