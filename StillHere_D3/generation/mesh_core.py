"""Small deterministic mesh/UV/GLB pipeline. Canonical coordinates: metres, Z up.

Charts are packed into disjoint pixel rectangles. Texture pixels originate from
source/generated_surfaces.png; no repeat sampling or world-space tiling is used.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import io, json, math, struct, hashlib, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from scipy.ndimage import sobel

ROOT = Path(__file__).resolve().parents[1]
MATERIAL_KEYS = ['concrete','broken_concrete','rock','moss','dirt','paving','meadow','forest_floor',
                 'bark','wood','rust','paint','banner','canvas','steel','rubber']
ROUGH = dict(zip(MATERIAL_KEYS, [.88,.94,.92,.97,.98,.93,.98,.98,.96,.94,.82,.67,.98,.97,.68,.92]))
METAL = dict(zip(MATERIAL_KEYS, [0,0,0,0,0,0,0,0,0,0,.32,.2,0,0,.75,0]))
SOURCE_CACHE: dict[str, Image.Image] = {}

def unit(a):
    a = np.asarray(a, dtype=float)
    return a / max(float(np.linalg.norm(a)), 1e-12)

def stable_seed(name: str) -> int:
    return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)

def rot_z(angle_deg):
    a=math.radians(angle_deg); c=math.cos(a); s=math.sin(a)
    return np.array([[c,-s,0],[s,c,0],[0,0,1.]])

def euler_matrix(x=0.,y=0.,z=0.):
    a,b,c=np.radians([x,y,z]);ca,sa=np.cos(a),np.sin(a);cb,sb=np.cos(b),np.sin(b);cc,sc=np.cos(c),np.sin(c)
    return np.array([[cc,-sc,0],[sc,cc,0],[0,0,1.]]) @ np.array([[cb,0,sb],[0,1,0],[-sb,0,cb]]) @ np.array([[1,0,0],[0,ca,-sa],[0,sa,ca]])

def transform_points(points, loc=(0,0,0), rotation=(0,0,0), scale=(1,1,1)):
    return (np.asarray(points)*np.asarray(scale)) @ euler_matrix(*rotation).T + np.asarray(loc)

def source_images():
    if SOURCE_CACHE: return SOURCE_CACHE
    cache_root=ROOT/'source/processed_surfaces'
    cache_meta=cache_root/'materials.json'
    if cache_meta.is_file() and not os.environ.get('STILLHERE_REPROCESS_SOURCE'):
        cached=json.loads(cache_meta.read_text(encoding='utf8'))
        if cached.get('source_pipeline_version')==2 and all((cache_root/(k+'.png')).is_file() for k in cached['keys']):
            for key in cached['keys']:SOURCE_CACHE[key]=Image.open(cache_root/(key+'.png')).convert('RGB')
            ROUGH.update(cached['roughness']);METAL.update(cached['metallic']);return SOURCE_CACHE
    image=Image.open(ROOT/'source/generated_surfaces.png').convert('RGB')
    w,h=image.size
    for i,key in enumerate(MATERIAL_KEYS):
        c,r=i%4,i//4
        # Keep generated boundaries out of the working material crops.
        SOURCE_CACHE[key]=image.crop((int(c*w/4)+4,int(r*h/4)+4,int((c+1)*w/4)-4,int((r+1)*h/4)-4))
    # Art-direction pass: suppress oversized source features on metre-scale surfaces.
    # This is colour/contrast processing of the generated image, not a repeating pattern.
    surface_grades={
        'meadow':((135,149,78),.58,4.5),
        'moss':((124,145,77),.56,3.0),
        'dirt':((177,155,120),.68,1.6),
        'rock':((150,157,152),.50,1.8),
        'concrete':((151,148,135),.83,.45),
    }
    for key,(target,contrast,blur) in surface_grades.items():
        im=SOURCE_CACHE[key].filter(ImageFilter.GaussianBlur(blur))
        a=np.asarray(im,dtype=float);mean=a.mean(axis=(0,1));a=(a-mean)*contrast+np.array(target)
        SOURCE_CACHE[key]=Image.fromarray(np.clip(a,0,255).astype('uint8'))
    # Tinted surface derivatives retain generated brushwork.
    moss=SOURCE_CACHE['meadow'].resize((512,512))
    def colorize(im, rgb, contrast=.30):
        a=np.asarray(im.convert('L'),dtype=float)/255
        a=(a-a.mean())*contrast+1
        out=np.clip(a[...,None]*np.asarray(rgb),0,255).astype('uint8')
        return Image.fromarray(out)
    for key,color in [('leaf_lime',(148,170,65)),('leaf_olive',(101,132,54)),('leaf_teal',(55,99,79)),
                      ('leaf_dark',(46,76,57)),('pine',(61,85,64)),('leaf_light',(172,182,81)),
                      ('flower_white',(231,224,195)),('flower_pink',(188,129,146)),
                      ('flower_yellow',(216,183,63)),('hair',(222,216,200)),('skin',(195,153,126)),
                      ('coat',(56,51,46)),('leather',(103,79,59)),('glass',(45,66,67)),
                      ('foam',(214,239,232)),('water',(25,123,152)),('water_deep',(17,82,111)),('tank_dark',(25,35,29))]:
        SOURCE_CACHE[key]=colorize(moss,color,.36 if key.startswith('leaf') or key=='pine' else .17)
        ROUGH[key] = .90 if key not in ('glass','water','water_deep','foam') else .20
        METAL[key] = 0.0
    water_source=ROOT/'source/generated_water_crop.png'
    if water_source.exists():
        wim=Image.open(water_source).convert('RGB').filter(ImageFilter.GaussianBlur(1.6))
        wa=np.asarray(wim,dtype=float);wa=(wa-wa.mean(axis=(0,1)))*.52+np.array([24,153,183])
        SOURCE_CACHE['water']=Image.fromarray(np.clip(wa,0,255).astype('uint8'))
        SOURCE_CACHE['water_deep']=ImageEnhance.Brightness(SOURCE_CACHE['water']).enhance(.74)
    # A vertically resampled, lightened derivative of the generated water source.
    fall=SOURCE_CACHE['water'].resize((512,32)).resize((512,1024),Image.Resampling.BILINEAR)
    a=np.asarray(fall,dtype=float);q=np.linspace(0,1,1024)[:,None,None]
    whiten=.30+.42*q**3;a=a*(1-whiten)+np.array([208,239,231])*whiten
    SOURCE_CACHE['waterfall']=Image.fromarray(np.clip(a,0,255).astype('uint8'))
    ROUGH['waterfall']=.22;METAL['waterfall']=0.
    # Exact typography is composited over generated surfaces, not fabricated by OCR.
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf'
    if not Path(font_path).exists(): font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    def lettering(base,key,lines,size,color,ys):
        out=base.resize((512,1024));d=ImageDraw.Draw(out)
        font=ImageFont.truetype(font_path,size)
        for text,y in zip(lines,ys):
            bbox=d.textbbox((0,0),text,font=font); x=(512-(bbox[2]-bbox[0]))/2
            d.text((x,y),text,font=font,fill=color,stroke_width=0)
        SOURCE_CACHE[key]=out;ROUGH[key]=.94;METAL[key]=0.
    banner=SOURCE_CACHE['banner'].resize((512,1024))
    # Existing generated emblem at the top; paint text only in the lower panel.
    lettering(banner,'banner_text',['STILL','HERE'],103,(211,196,164),[625,770])
    lettering(SOURCE_CACHE['concrete'],'nature_text',['ONCE','HUMAN','ALWAYS','NATURE'],94,(215,216,197),[155,315,475,635])
    out=SOURCE_CACHE['concrete'].resize((1024,512));d=ImageDraw.Draw(out);font=ImageFont.truetype(font_path,430)
    d.text((45,0),'D-3',font=font,fill=(225,219,196))
    SOURCE_CACHE['d3_text']=out;ROUGH['d3_text']=.9;METAL['d3_text']=0.
    return SOURCE_CACHE

def triangulate_polygon(vertices):
    """Ear-clip a simple 3D polygon in one consistent projected UV plane.

    A triangle fan is not valid for concave module perimeters. The same
    projection is used for triangulation and UVs, preventing UV self-overlap.
    """
    v=np.asarray(vertices,float);n=len(v)
    normal=np.sum(np.cross(v,np.roll(v,-1,axis=0)),axis=0)
    if np.linalg.norm(normal)<1e-10:
        normal=np.cross(v[1]-v[0],v[2]-v[0])
    normal=unit(normal);edges=np.roll(v,-1,axis=0)-v
    u=unit(edges[np.argmax(np.linalg.norm(edges,axis=1))]);vv=unit(np.cross(normal,u))
    p=np.column_stack((v@u,v@vv));lo=p.min(0);sz=np.maximum(p.max(0)-lo,1e-5);uv=(p-lo)/sz
    signed=np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))
    orient=1. if signed>=0 else -1.
    def cross(a,b,c):
        x=b-a;y=c-a;return x[0]*y[1]-x[1]*y[0]
    remaining=list(range(n));faces=[]
    while len(remaining)>3:
        clipped=False
        for jj in range(len(remaining)):
            ia=remaining[jj-1];ib=remaining[jj];ic=remaining[(jj+1)%len(remaining)]
            a,b,c=p[ia],p[ib],p[ic]
            if orient*cross(a,b,c)<=1e-11:continue
            inside=False
            for ii in remaining:
                if ii in (ia,ib,ic):continue
                q=p[ii]
                if all(orient*val>=-1e-11 for val in (cross(a,b,q),cross(b,c,q),cross(c,a,q))):inside=True;break
            if inside:continue
            faces.append((ia,ib,ic));remaining.pop(jj);clipped=True;break
        if not clipped:
            # Collinear boundary vertices can be removed without losing area.
            drop=None
            for jj in range(len(remaining)):
                a,b,c=(p[remaining[jj-1]],p[remaining[jj]],p[remaining[(jj+1)%len(remaining)]])
                if abs(cross(a,b,c))<1e-9:drop=jj;break
            if drop is not None:remaining.pop(drop);continue
            raise ValueError('Non-simple polygon; cannot create a non-overlapping UV triangulation')
    if len(remaining)==3:faces.append(tuple(remaining))
    return faces,uv,sz

@dataclass
class Chart:
    vertices: np.ndarray
    faces: np.ndarray
    uv: np.ndarray
    size: tuple[float,float]
    key: str
    tint: tuple[float,float,float]=(1,1,1)
    smooth: bool=False
    exact: bool=False
    density_weight: float=1.0
    rect: tuple[int,int,int,int]|None=None

@dataclass
class Mesh:
    name: str
    category: str='props'
    charts: list[Chart]=field(default_factory=list)
    double_sided: bool=False
    surface_type: str='opaque'
    description: str=''

    def add(self, vertices, faces, uv=None, size=None, key='concrete', tint=(1,1,1), smooth=False, exact=False, density_weight=1.):
        v=np.asarray(vertices,dtype=float);f=np.asarray(faces,dtype=np.int32).reshape(-1,3)
        if len(v)<3 or len(f)==0:return self
        cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
        keep=np.linalg.norm(cross,axis=1)>1e-10
        f=f[keep]
        if not len(f):return self
        if uv is None:
            n=unit(cross[np.argmax(np.linalg.norm(cross,axis=1))]);u=unit(v[1]-v[0]); vv=unit(np.cross(n,u))
            p=np.column_stack((v@u,v@vv));lo=p.min(0);sz=np.maximum(p.max(0)-lo,1e-4);uv=(p-lo)/sz
            if size is None:size=tuple(sz)
        if size is None:size=(1,1)
        self.charts.append(Chart(v,f,np.asarray(uv,float),tuple(size),key,tuple(tint),smooth,exact,density_weight))
        return self

    def poly(self, vertices, key='concrete', tint=(1,1,1), **kw):
        faces,uv,size=triangulate_polygon(vertices)
        return self.add(vertices,faces,uv,size,key=key,tint=tint,**kw)

    def box(self, center, size, key='concrete', tint=(1,1,1), rotation=(0,0,0), face_keys=None):
        x,y,z=np.array(size)*.5
        verts=np.array([[-x,-y,-z],[x,-y,-z],[x,y,-z],[-x,y,-z],[-x,-y,z],[x,-y,z],[x,y,z],[-x,y,z]])
        verts=transform_points(verts,center,rotation)
        polys=[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
        for i,ids in enumerate(polys):self.poly(verts[list(ids)],key=(face_keys or {}).get(i,key),tint=tint)
        return self

    def cylinder(self, a, b, radius, key='bark', tint=(1,1,1), radius2=None, sides=10, caps=True, rough=0., rng=None):
        a=np.asarray(a,float);b=np.asarray(b,float);direction=unit(b-a);length=np.linalg.norm(b-a)
        if length<1e-8:return self
        u=unit(np.cross(direction,[0,0,1] if abs(direction[2])<.95 else [0,1,0]));v=np.cross(direction,u)
        radius2=radius if radius2 is None else radius2
        rng=np.random.default_rng(0) if rng is None else rng
        angles=np.linspace(0,2*np.pi,sides+1)
        jitter=1+rng.uniform(-rough,rough,sides);jitter=np.r_[jitter,jitter[0]]
        dirs=np.cos(angles)[:,None]*u+np.sin(angles)[:,None]*v
        lower=a+dirs*radius*jitter[:,None];upper=b+dirs*radius2*jitter[:,None]
        verts=np.vstack([lower,upper]);uv=np.array([[i/sides,j] for j in (0,1) for i in range(sides+1)])
        faces=[]
        for i in range(sides):faces.extend([(i,i+1,i+sides+2),(i,i+sides+2,i+sides+1)])
        # side normals point outwards for basis(u,v,direction).
        self.add(verts,faces,uv,(2*np.pi*max(radius,radius2),length),key,tint,True)
        if caps:
            self.poly(lower[:-1][::-1],key,tint)
            self.poly(upper[:-1],key,tint)
        return self

    def leaf(self, center, length=.28, width=.14, rotation=(0,0,0), key='leaf_olive', tint=(1,1,1), bend=.06):
        # A folded, tapered six-vertex leaf, not a round decimated blob.
        v=np.array([[0,-length*.5,0],[-width*.5,-length*.16,0],[-width*.42,length*.23,0],[0,length*.5,0],
                    [width*.42,length*.23,0],[width*.5,-length*.16,0],[0,0,bend*width]])
        uv=np.column_stack((v[:,0]/width+.5,v[:,1]/length+.5))
        v=transform_points(v,center,rotation)
        self.add(v,[((i+1)%6,i,6) for i in range(6)],uv,(width,length),key,tint,True)
        return self

    def merge(self, other, loc=(0,0,0), rotation=(0,0,0), scale=(1,1,1)):
        for c in other.charts:
            v=transform_points(c.vertices,loc,rotation,scale)
            self.add(v,c.faces,c.uv,np.asarray(c.size)*np.mean(scale),c.key,c.tint,c.smooth,c.exact,c.density_weight)
        return self

    def bounds(self):
        v=np.vstack([c.vertices for c in self.charts]);return [v.min(0).tolist(),v.max(0).tolist()]

    @property
    def triangles(self):return sum(len(c.faces) for c in self.charts)


def shelf_pack(sizes, resolution, padding):
    order=sorted(range(len(sizes)),key=lambda i:(-sizes[i][1],-sizes[i][0]))
    shelves=[];rects=[None]*len(sizes);maxy=0
    for idx in order:
        w,h=sizes[idx];w+=padding*2;h+=padding*2
        if w>resolution or h>resolution:return None
        best=None
        for j,(sy,sh,sx) in enumerate(shelves):
            if h<=sh and sx+w<=resolution:
                score=(sh-h)*resolution+(resolution-sx-w)
                if best is None or score<best[0]:best=(score,j)
        if best is None:
            if maxy+h>resolution:return None
            j=len(shelves);shelves.append([maxy,h,0]);maxy+=h
        else:j=best[1]
        sy,sh,sx=shelves[j];rects[idx]=(sx+padding,sy+padding,w-2*padding,h-2*padding);shelves[j][2]+=w
    return rects


def pack_charts(charts, texel_density=72., max_size=2048, padding=3):
    total=sum(max(c.size[0]*texel_density*c.density_weight,3)*max(c.size[1]*texel_density*c.density_weight,3) for c in charts)
    res=128
    while res<max_size and res*res<total*1.8:res*=2
    density=float(texel_density)
    while True:
        sizes=[(max(3,int(math.ceil(c.size[0]*density*c.density_weight))),max(3,int(math.ceil(c.size[1]*density*c.density_weight)))) for c in charts]
        rects=shelf_pack(sizes,res,padding)
        if rects is not None:return res,density,rects
        if res<max_size:res*=2
        else:density*=.88
        if density<.1:raise ValueError('UV atlas cannot be packed within the resolution limit')


def _normals(v,faces,smooth):
    n=np.zeros_like(v);cross=np.cross(v[faces[:,1]]-v[faces[:,0]],v[faces[:,2]]-v[faces[:,0]])
    for j in range(3):np.add.at(n,faces[:,j],cross)
    n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    return n


def bake(mesh:Mesh, texel_density=72., max_size=2048, write=True):
    sources=source_images();rng=np.random.default_rng(stable_seed(mesh.name))
    res,density,rects=pack_charts(mesh.charts,texel_density,max_size)
    base=Image.new('RGB',(res,res),(42,48,37));orm=Image.new('RGB',(res,res),(255,240,0));normal=Image.new('RGB',(res,res),(128,128,255))
    outv=[];outn=[];outuv=[];outf=[];offset=0;chart_records=[]
    surface_area=0.; uv_area=0.
    for idx,(c,rect) in enumerate(zip(mesh.charts,rects)):
        c.rect=rect;x,y,w,h=rect;src=sources[c.key]
        if not c.exact:
            sw,sh=src.size
            # Random source windows, never wrap/tiling; each destination chart is unique.
            frac=rng.uniform(.50,1.) if max(c.size)<2 else 1.
            cw=max(8,int(sw*frac));ch=max(8,int(sh*frac));ox=int(rng.integers(0,sw-cw+1));oy=int(rng.integers(0,sh-ch+1))
            src=src.crop((ox,oy,ox+cw,oy+ch))
            if c.key not in ('bark','wood','concrete','paint','canvas','banner','water') and rng.random()<.5:src=src.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        tile=np.asarray(src.resize((w,h),Image.Resampling.BILINEAR),dtype=float)*np.asarray(c.tint)[None,None,:]
        tile=np.clip(tile,0,255).astype(np.uint8)
        gray=np.mean(tile.astype(float),axis=2)/255.
        rr=np.clip(ROUGH.get(c.key,.9)*255+(gray-gray.mean())*12,0,255).astype(np.uint8)
        oo=np.stack([np.full_like(rr,255),rr,np.full_like(rr,int(METAL.get(c.key,0)*255))],axis=2)
        amp=.09 if c.key not in ('glass','hair','skin','foam') else .015
        nx=-sobel(gray,axis=1)*amp;ny=-sobel(gray,axis=0)*amp
        nn=np.stack([nx,ny,np.ones_like(nx)],axis=2);nn/=np.linalg.norm(nn,axis=2,keepdims=True)
        nn=np.clip((nn*.5+.5)*255,0,255).astype(np.uint8)
        # Two-pixel dilated gutters protect mip filtering at all chart edges.
        p=3
        for atlas,data in [(base,tile),(orm,oo),(normal,nn)]:
            atlas.paste(Image.fromarray(np.pad(data,((p,p),(p,p),(0,0)),mode='edge')),(x-p,y-p))
        uv=np.empty_like(c.uv)
        uv[:,0]=(x+.5+c.uv[:,0]*(w-1))/res
        # glTF UV starts at image top; canonical storage uses top-left as well.
        uv[:,1]=(y+.5+(1-c.uv[:,1])*(h-1))/res
        outv.append(c.vertices);outn.append(_normals(c.vertices,c.faces,c.smooth));outuv.append(uv);outf.append(c.faces+offset);offset+=len(c.vertices)
        area=np.linalg.norm(np.cross(c.vertices[c.faces[:,1]]-c.vertices[c.faces[:,0]],c.vertices[c.faces[:,2]]-c.vertices[c.faces[:,0]]),axis=1).sum()*.5
        uvtris=uv[c.faces];ab=uvtris[:,1]-uvtris[:,0];ac=uvtris[:,2]-uvtris[:,0];ua=np.abs(ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]).sum()*.5
        surface_area+=float(area);uv_area+=float(ua)
        chart_records.append({'rect_pixels':list(rect),'surface':c.key,'area_m2':round(float(area),6),'size_m':list(c.size),'exact_source':c.exact})
    vertices=np.vstack(outv).astype('float32');normals=np.vstack(outn).astype('float32');uvs=np.vstack(outuv).astype('float32');faces=np.vstack(outf).astype('uint32')
    meta={'id':mesh.name,'category':mesh.category,'triangles':len(faces),'vertices':len(vertices),'charts':len(mesh.charts),
          'atlas_size':res,'requested_texel_density_px_m':texel_density,'packing_texel_density_px_m':round(density,2),
          'effective_texel_density_px_m':round(math.sqrt(uv_area*res*res/max(surface_area,1e-9)),2),
          'surface_area_m2':round(surface_area,4),'uv_coverage':round(uv_area,4),'bounds_m':mesh.bounds(),
          'double_sided':mesh.double_sided,'surface_type':mesh.surface_type,'description':mesh.description,
          'glb':f'assets/glb/{mesh.name}.glb','mesh_data':f'data/meshes/{mesh.name}.npz',
          'base_color':f'assets/textures/{mesh.name}_BaseColor.png','normal':f'assets/textures/{mesh.name}_Normal.png','orm':f'assets/textures/{mesh.name}_ORM.png'}
    if write:
        for suffix,im in [('BaseColor',base),('Normal',normal),('ORM',orm)]:im.save(ROOT/f'assets/textures/{mesh.name}_{suffix}.png',optimize=True)
        (ROOT/'data/meshes').mkdir(exist_ok=True)
        np.savez_compressed(ROOT/meta['mesh_data'],vertices=vertices,normals=normals,uv=uvs,faces=faces)
        (ROOT/'data/uv').mkdir(exist_ok=True)
        (ROOT/f'data/uv/{mesh.name}.json').write_text(json.dumps({'resolution':res,'padding':3,'charts':chart_records},ensure_ascii=False,separators=(',',':')),encoding='utf8')
        write_glb(ROOT/meta['glb'],mesh.name,vertices,normals,uvs,faces,base,normal,orm,mesh.double_sided,mesh.surface_type)
    return meta,(vertices,normals,uvs,faces),(base,normal,orm)


def write_glb(path, name, vertices,normals,uv,faces,base,normal,orm,double_sided=False,surface_type='opaque'):
    # Blender Z-up to glTF Y-up is a proper rotation, not a reflection.
    g=np.asarray(vertices)[:,[0,2,1]].copy();g[:,2]*=-1
    gn=np.asarray(normals)[:,[0,2,1]].copy();gn[:,2]*=-1
    binary=bytearray();views=[];accessors=[]
    def blob(data,target=None):
        while len(binary)%4:binary.append(0)
        start=len(binary);binary.extend(data);v={'buffer':0,'byteOffset':start,'byteLength':len(data)}
        if target:v['target']=target
        views.append(v);return len(views)-1
    def accessor(a,typ,comp=5126,target=34962,minimum=False):
        a=np.asarray(a,dtype='<f4' if comp==5126 else '<u4');vi=blob(a.tobytes(),target)
        d={'bufferView':vi,'componentType':comp,'count':len(a),'type':typ}
        if minimum:d['min']=a.min(axis=0).tolist();d['max']=a.max(axis=0).tolist()
        accessors.append(d);return len(accessors)-1
    pos=accessor(g,'VEC3',minimum=True);nor=accessor(gn,'VEC3');tex=accessor(uv,'VEC2');ind=accessor(faces.reshape(-1),'SCALAR',5125,34963)
    images=[]
    for suffix,im in [('BaseColor',base),('Normal',normal),('ORM',orm)]:
        buf=io.BytesIO();im.save(buf,format='PNG',optimize=True);vi=blob(buf.getvalue());images.append({'name':name+'_'+suffix,'bufferView':vi,'mimeType':'image/png'})
    mat={'name':'M_'+name,'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicRoughnessTexture':{'index':2},'metallicFactor':1.,'roughnessFactor':1.},
         'normalTexture':{'index':1,'scale':.6},'occlusionTexture':{'index':2},'doubleSided':bool(double_sided),'alphaMode':'OPAQUE'}
    if surface_type=='foam':mat['emissiveFactor']=[.10,.13,.13]
    if surface_type=='water':mat['pbrMetallicRoughness']['roughnessFactor']=.3
    doc={'asset':{'version':'2.0','generator':'StillHere D3 deterministic mesh + unique UV pipeline'},'scene':0,
         'scenes':[{'nodes':[0]}],'nodes':[{'name':name,'mesh':0,'extras':{'asset_id':name,'source_space':'RH_Z_UP_METRES'}}],
         'meshes':[{'name':name,'primitives':[{'attributes':{'POSITION':pos,'NORMAL':nor,'TEXCOORD_0':tex},'indices':ind,'material':0,'mode':4}]}],
         'materials':[mat],'textures':[{'sampler':0,'source':i} for i in range(3)],'images':images,
         'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071}],
         'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(binary)}]}
    j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary.extend(b'\0'*((-len(binary))%4))
    total=12+8+len(j)+8+len(binary)
    with open(path,'wb') as f:
        f.write(struct.pack('<4sII',b'glTF',2,total));f.write(struct.pack('<I4s',len(j),b'JSON'));f.write(j);f.write(struct.pack('<I4s',len(binary),b'BIN\0'));f.write(binary)


def read_glb(path):
    data=Path(path).read_bytes();magic,version,length=struct.unpack_from('<4sII',data,0)
    if magic!=b'glTF' or version!=2 or length!=len(data):raise ValueError('Invalid GLB header')
    n,tag=struct.unpack_from('<I4s',data,12)
    if tag!=b'JSON':raise ValueError('Missing JSON chunk')
    doc=json.loads(data[20:20+n]);offset=20+n
    size,tag=struct.unpack_from('<I4s',data,offset)
    if tag!=b'BIN\0':raise ValueError('Missing binary chunk')
    return doc,data[offset+8:offset+8+size]
