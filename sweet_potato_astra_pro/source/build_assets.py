"""Fresh procedural sweet potato meshes with image-derived laminae and weighted UVs.
Run: python source/prepare_textures.py && python source/build_assets.py
All geometry is authored in meters, Z-up, and explicitly converted to glTF Y-up.
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import json, math
import numpy as np
from PIL import Image
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual.texture import TextureVisuals
ROOT=Path(__file__).resolve().parents[1]
TAU=math.tau

class Batch:
    def __init__(self): self.vertices=[]; self.faces=[]; self.uv=[]
    def add(self,vertices,faces,uv):
        if len(faces)==0:return
        off=len(self.vertices)
        self.vertices.extend(np.asarray(vertices,dtype=float).tolist())
        self.faces.extend((np.asarray(faces,dtype=int)+off).tolist())
        self.uv.extend(np.asarray(uv,dtype=float).tolist())
    def mesh(self,material):
        m=trimesh.Trimesh(vertices=self.vertices,faces=self.faces,process=False)
        # Degenerate geometry must be removed before calculating normals/export.
        keep=m.area_faces>1.e-12
        if not keep.all():m.update_faces(keep)
        m.visual=TextureVisuals(uv=np.asarray(self.uv),material=material)
        return m

def norm(v):
    a=np.asarray(v,float);return a/max(1.e-9,np.linalg.norm(a))
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def bezier(p,n=6):
    p=np.asarray(p);t=np.linspace(0,1,n)[:,None]
    return (1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3]
def tube(batch,path,radius=.01,endratio=.55,sides=6,slot=0):
    path=np.asarray(path);v=[];uv=[];f=[]
    for i,p in enumerate(path):
        tangent=norm(path[min(i+1,len(path)-1)]-path[max(0,i-1)])
        e1=norm(np.cross(tangent,[0,0,1] if abs(tangent[2])<.93 else [1,0,0]));e2=np.cross(tangent,e1)
        r=radius*(1-(1-endratio)*i/(len(path)-1))
        for j in range(sides):
            a=TAU*j/sides;v.append(p+r*(np.cos(a)*e1+np.sin(a)*e2))
            uv.append(((slot+.2+.6*j/sides)/4.,.12+.75*i/(len(path)-1)))
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides;c=i*sides+j;d=i*sides+(j+1)%sides
                f.extend([(a,b,c),(b,d,c)])
    # Closed tips, distinct vertices avoid zero-area closures.
    for ring,reverse in [(0,True),(len(path)-1,False)]:
        k=len(v);v.append(path[ring]);uv.append(((slot+.5)/4,.2))
        for j in range(sides):
            a=ring*sides+j;b=ring*sides+(j+1)%sides
            f.append((k,b,a) if reverse else (k,a,b))
    batch.add(v,f,uv)

class Builder:
    def __init__(self,kind,lod=0):
        self.kind=kind;self.lod=lod;self.rng=np.random.default_rng(261117 if kind=='wild' else 261118)
        self.batches=defaultdict(Batch);self.leaf_count=0
        c=np.load(ROOT/'source'/'leaf_boundary.npy')
        # Even arc-length contour, with interpolation for stable round silhouettes.
        c=np.vstack([c,c[0]]);dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(c,axis=0),axis=1))]
        count=24 if lod==0 else 12
        t=np.linspace(0,dist[-1],count,endpoint=False)
        self.boundary=np.column_stack([np.interp(t,dist,c[:,k]) for k in [0,1]])
        self.center=self.boundary.mean(axis=0)
        # Notch is the attachment point of the generated leaf, not its centroid.
        self.attach_uv=np.array([.55,.29])
    def leaf(self,root,heading,length=.30,pitch=0,variant=0,width=1.):
        b=self.boundary;center=self.center
        uv=np.vstack([center,center+(b-center)*.53,b]) if not self.lod else np.vstack([center,b])
        n=len(b);f=[]
        for i in range(n):
            j=(i+1)%n
            f.append((0,1+i,1+j))
            if not self.lod:f.extend([(1+i,n+1+i,n+1+j),(1+i,n+1+j,1+j)])
        # Leaf uv coordinates come from the generated leaf image exactly.
        rel=(uv-self.attach_uv)/.67
        x=rel[:,0]*length*width;y=rel[:,1]*length
        yn=rel[:,1];xn=rel[:,0]
        z=length*(.07*np.sin(np.pi*np.clip(yn,0,1))-.11*yn**2-.065*np.abs(xn)**1.35+.018*xn*np.sin(4*yn))
        co,si=math.cos(heading),math.sin(heading);cp,sp=math.cos(pitch),math.sin(pitch)
        side=np.array([-si,co,0]);along=np.array([co*cp,si*cp,sp]);up=np.array([-co*sp,-si*sp,cp])
        vertices=np.asarray(root)+x[:,None]*side+y[:,None]*along+z[:,None]*up
        faces=np.asarray(f)
        normal=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]]).mean(axis=0)
        if np.dot(normal,up)<0:faces=faces[:,::-1]
        texuv=np.column_stack([(uv[:,0]+variant%2)/2.,1-(uv[:,1]+variant//2)/2.])
        self.batches['foliage'].add(vertices,faces,texuv);self.leaf_count+=1
    def height(self,x,y):
        if self.kind=='wild':
            r=min(1.,np.sqrt((x/1.02)**2+(y/.85)**2))
            return .052+.065*(1-r*r)+.009*np.sin(x*10+.7)*np.cos(y*13)
        edge=smooth(0,.22,1.58-abs(x))*smooth(0,.28,1.83-abs(y))
        ridges=sum(.205*np.exp(-((x-c)/.335)**2) for c in [-1.04,0,1.04])
        return .052+(ridges+ .007*np.sin(x*17+y*8)*np.cos(y*14))*edge
    def wild_ground(self):
        n=56 if not self.lod else 28;rings=6 if not self.lod else 4
        v=[[0,0,self.height(0,0)]];uv=[[1.5,1.5]];f=[]
        def radius(a):return 1.+.055*math.sin(3*a+.4)+.038*math.sin(7*a)+.026*math.cos(11*a)
        for ring in range(1,rings+1):
            rr=ring/rings
            for j in range(n):
                a=j*TAU/n;r=radius(a)*rr;x=1.02*r*math.cos(a);y=.85*r*math.sin(a)
                v.append([x,y,self.height(x,y)]);uv.append([1.5+1.15*x,1.5+1.15*y])
            if ring==1:
                f.extend([(0,1+j,1+(j+1)%n) for j in range(n)])
            else:
                for j in range(n):
                    a=1+(ring-2)*n+j;b=1+(ring-2)*n+(j+1)%n;c=1+(ring-1)*n+j;d=1+(ring-1)*n+(j+1)%n
                    f.extend([(a,c,b),(b,c,d)])
        top=list(range(1+(rings-1)*n,1+rings*n))
        prev=top
        for scale,z in [(1.012,.019),(.975,0)]:
            now=[]
            for j in range(n):
                a=j*TAU/n;r=radius(a)*scale;x=1.02*r*math.cos(a);y=.85*r*math.sin(a)
                now.append(len(v));v.append([x,y,z]);uv.append([1.5+1.15*x,1.5+1.15*y])
            for j in range(n):
                a,b=prev[j],prev[(j+1)%n];c,d=now[j],now[(j+1)%n]
                f.extend([(a,b,c),(b,d,c)])
            prev=now
        k=len(v);v.append([0,0,0]);uv.append([.5,.5])
        f.extend([(k,prev[(j+1)%n],prev[j]) for j in range(n)])
        # Normalize top normals; bottom and perimeter remain outward.
        mesh=trimesh.Trimesh(v,f,process=False)
        trimesh.repair.fix_normals(mesh,multibody=True)
        self.batches['soil'].add(mesh.vertices,mesh.faces,uv)
    def field_ground(self):
        nx,ny=(28,34) if not self.lod else (16,20)
        v=[];uv=[];f=[]
        for j in range(ny+1):
            y=-1.83+3.66*j/ny
            d=max(0,abs(y)-(1.83-.22));span=1.58-.22+np.sqrt(max(0,.22**2-d*d))
            for i in range(nx+1):
                x=(-1+2*i/nx)*span
                v.append([x,y,self.height(x,y)]);uv.append([.5+x*1.6,.5+y*1.6])
        for j in range(ny):
            for i in range(nx):
                a=j*(nx+1)+i;b=a+1;c=a+nx+1;d=c+1
                f.extend([(a,b,c),(b,d,c)])
        border=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
        lower=[]
        for idx in border:
            x,y,z=v[idx];lower.append(len(v));v.append([x*.986,y*.989,0]);uv.append([.5+x*1.6,.5+y*1.6])
        for j in range(len(border)):
            k=(j+1)%len(border);f.extend([(border[j],lower[j],border[k]),(border[k],lower[j],lower[k])])
        center=len(v);v.append([0,0,0]);uv.append([.5,.5])
        f.extend([(center,lower[(j+1)%len(lower)],lower[j]) for j in range(len(lower))])
        m=trimesh.Trimesh(v,f,process=False);trimesh.repair.fix_normals(m,multibody=True)
        self.batches['soil'].add(m.vertices,m.faces,uv)
    def crown(self,x,y,scale=1.,count=13,phase=0.):
        ground=self.height(x,y);base=np.array([x,y,ground+.018]);r=self.rng
        nsides=5 if not self.lod else 4;npath=4 if not self.lod else 3
        # A short central shoot unifies the plant: every leaf has a connected petiole.
        tube(self.batches['stems'],bezier([base,base+[0,0,.06*scale],base+[.008,0,.15*scale],base+[.014,.007,.26*scale]],npath),.016*scale,.5,nsides,0)
        outer=count-5
        for i in range(count):
            upper=i>=outer;young=i>=count-2
            k=i if not upper else i-outer
            a=phase+(k*TAU/(outer if not upper else 5))+r.uniform(-.12,.12)+(0.39 if upper else 0)
            d=np.array([np.cos(a),np.sin(a),0.])
            start=base+[.005,.004,(.055 if not upper else .15)*scale]
            radius=(r.uniform(.09,.17) if not upper else r.uniform(.04,.105))*scale
            h=(r.uniform(.16,.23) if not upper else r.uniform(.29,.36))*scale
            if young:h+=.04*scale
            endpoint=base+d*radius+[0,0,h]
            controls=[start,start+d*(radius*.25)+[0,0,.055*scale],endpoint-d*(radius*.17)-[0,0,.045*scale],endpoint]
            tube(self.batches['stems'],bezier(controls,npath),(.009 if not young else .006)*scale,.62,nsides,1 if not young else 3)
            length=(r.uniform(.25,.34) if not upper else r.uniform(.20,.28))*scale
            if young:length*=.64
            variant=(0 if r.random()<.7 else 2) if not upper else (1 if young or r.random()<.65 else 0)
            self.leaf(endpoint,a+r.uniform(-.1,.1),length,r.uniform(-.13,.13) if not upper else r.uniform(.04,.29),variant,r.uniform(.93,1.08))
    def runner(self,controls,leaves=3,scale=1.):
        controls=np.asarray(controls,float)
        n=18 if not self.lod else 10
        xy=bezier(np.column_stack([controls,np.zeros(4)]),n)
        xy[:,2]=[self.height(p[0],p[1])+.016 for p in xy]
        tube(self.batches['stems'],xy,.013*scale,.16,6 if not self.lod else 4,2)
        for k,t in enumerate(np.linspace(.25,.87,leaves)):
            j=round(t*(n-1));start=xy[j];tan=norm(xy[min(j+1,n-1)]-xy[max(j-1,0)])
            a=np.arctan2(tan[1],tan[0])+((-1)**k)*1.12
            d=np.array([np.cos(a),np.sin(a),0.])
            end=start+d*.055*scale+[0,0,.075*scale]
            tube(self.batches['stems'],bezier([start,start+[0,0,.025*scale],end-d*.018,end],4 if not self.lod else 3),.006*scale,.6,5 if not self.lod else 3,1)
            self.leaf(end,a,(.17+.035*self.rng.random())*scale,.10,1 if k%3==0 else 0)
    def stone(self,x,y,size=.05):
        mesh=trimesh.creation.icosphere(subdivisions=1 if size>.075 and not self.lod else 0,radius=1)
        v=np.array(mesh.vertices)*np.array([size,size*.78,size*.58]);v[:,2]+=self.height(x,y)+size*.24;v[:,:2]+=[x,y]
        u=(mesh.vertices[:,0]+1)/2;vv=(mesh.vertices[:,2]+1)/2
        self.batches['stone'].add(v,mesh.faces,np.column_stack([u,vv]))
    def grass(self,x,y,scale=1.):
        root=np.array([x,y,self.height(x,y)+.002]);r=self.rng
        for j in range(5 if not self.lod else 3):
            a=j*2.4+r.uniform(-.2,.2);d=np.array([np.cos(a),np.sin(a),0]);s=np.array([-np.sin(a),np.cos(a),0])
            height=r.uniform(.09,.16)*scale;width=r.uniform(.012,.020)*scale
            v=[root-s*width,root+s*width,root+d*.022*scale+[0,0,height*.62]-s*width*.62,root+d*.022*scale+[0,0,height*.62]+s*width*.62,root+d*.073*scale+[0,0,height*.90]]
            uv=[[.70,.72],[.76,.72],[.71,.78],[.75,.78],[.73,.84]]
            self.batches['foliage'].add(v,[(0,1,2),(1,3,2),(2,3,4)],uv)
    def build(self):
        if self.kind=='wild':
            self.wild_ground()
            self.crown(-.39,-.25,.90,11,.24);self.crown(.29,.28,1.03,12,.91)
            for points,n in [([[-.39,-.25],[-.82,-.36],[-.72,-.68],[-.12,-.65]],3),([[-.39,-.25],[-.83,-.05],[-.86,.28],[-.52,.52]],3),([[.29,.28],[.68,.22],[.84,-.02],[.72,-.36]],3),([[.29,.28],[.07,.11],[.27,-.24],[.49,-.48]],2),([[.29,.28],[.46,.67],[.10,.72],[-.13,.62]],2)]:self.runner(points,n,.90)
            for x,y,sz in [(-.69,.40,.043),(-.16,.1,.052),(.60,.05,.035),(.04,-.45,.044),(.76,.22,.048),(-.66,-.5,.027),(-.37,.56,.032),(.22,-.65,.035),(-.89,-.03,.04),(.52,.50,.041),(-.08,.37,.028)]:self.stone(x,y,sz)
            for x,y,s in [(-.81,.18,.82),(.76,.39,.80),(.17,-.70,.72),(-.43,.59,.63)]:self.grass(x,y,s)
        else:
            self.field_ground()
            for col,x in enumerate([-1.04,0,1.04]):
                for row,y in enumerate([-1.26,-.42,.42,1.26]):
                    self.crown(x+self.rng.uniform(-.025,.025),y+self.rng.uniform(-.025,.025),self.rng.uniform(1.02,1.14),13,.38*row+.72*col)
            for x in [-1.04,0,1.04]:
                self.runner([[x,-1.26],[x-.19,-1.42],[x+.22,-1.52],[x+.22,-1.64]],2,.88)
                self.runner([[x,.42],[x+.15,.66],[x-.20,.75],[x-.18,.94]],2,.78)
        return self

MATERIALS={
 'foliage':('foliage_basecolor_1024.png',.91,True),
 'soil':('soil_basecolor_256.png',1.,False),
 'stems':('stem_basecolor_128.png',.91,False),
 'stone':('stone_basecolor_128.png',.96,False),
}
def export(builder,name):
    scene=trimesh.Scene();records={}
    rot=trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0])
    for key,batch in builder.batches.items():
        if not batch.faces:continue
        filename,rough,two=MATERIALS[key]
        material=PBRMaterial(name=key,baseColorTexture=Image.open(ROOT/'textures'/filename).convert('RGB'),baseColorFactor=[1,1,1,1],metallicFactor=0.,roughnessFactor=rough,doubleSided=two,alphaMode='OPAQUE')
        mesh=batch.mesh(material)
        mesh.apply_transform(rot)
        records[key]={'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'texture':filename}
        scene.add_geometry(mesh,geom_name=key,node_name=key)
    scene.metadata={'asset':'fresh_astra_pro_rebuild','units':'meters','up_axis':'Y','leaf_count':builder.leaf_count,'variant':builder.kind,'lod':builder.lod}
    output=ROOT/'models'/f'{name}.glb'
    output.write_bytes(trimesh.exchange.gltf.export_glb(scene,include_normals=True))
    records={'mesh_parts':records,'triangles':sum(v['triangles'] for v in records.values()),'vertices':sum(v['vertices'] for v in records.values()),'leaves':builder.leaf_count,'bounds_m':scene.bounds.tolist(),'size_bytes':output.stat().st_size}
    print(name,records['triangles'],'triangles',records['leaves'],'leaves',records['size_bytes'],'bytes')
    return records

def main():
    report={}
    for kind,name in [('wild','wild_sweet_potato'),('field','cultivated_sweet_potato')]:
        for lod in [0,1]:
            file=name+('_LOD1' if lod else '')
            report[file]=export(Builder(kind,lod).build(),file)
    (ROOT/'validation'/'asset_metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':main()
