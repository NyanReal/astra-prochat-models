#!/usr/bin/env python3
"""Deterministic shed construction + non-overlapping, area-proportional UV atlas.
Requires numpy, scipy, Pillow. No Blender dependency and no tiled shaders.
AI-authored source artwork is supplied in source/; this script only crops,
rectifies, resamples and composites that artwork onto distinct face islands.
"""
from __future__ import annotations
import io, json, math, struct, hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from scipy.spatial import ConvexHull
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[1]
S=4096
PAD=6
SURFACES=[]
COUNTS=defaultdict(int)


def norm(v):
    v=np.array(v,dtype=float);return v/max(float(np.linalg.norm(v)),1e-12)

def matrix_yaw(deg):
    a=math.radians(deg);return np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])

def face(name, verts, style='beam', grain=None, transform=None, meta=None):
    p=np.asarray(verts,float)
    n=norm(np.cross(p[1]-p[0],p[2]-p[0]))
    if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))<1e-9:return
    if grain is None:
        if abs(n[2])>.8: grain=[1,0,0]
        elif abs(n[0])>.8: grain=[0,1,0]
        else: grain=[1,0,0]
    u=np.array(grain,float);u=u-n*np.dot(u,n)
    if np.linalg.norm(u)<1e-5:
        u=p[1]-p[0];u=u-n*np.dot(u,n)
    u=norm(u);v=norm(np.cross(n,u))
    # Prefer vertical upward on wall panels; positive local y on horizontal panels.
    if abs(n[2])<.8 and v[2]<-.001: u=-u;v=-v
    elif abs(n[2])>.8 and np.dot(v,[0,1,0])<-.001:u=-u;v=-v
    uv=np.array([[np.dot(q,u),np.dot(q,v)] for q in p]);mn=uv.min(0);mx=uv.max(0)
    wh=mx-mn
    if min(wh)<1e-7:return
    uv=(uv-mn)/wh
    if transform:
        r,t=transform;p=p@r.T+t;n=r@n;u=r@u;v=r@v
    COUNTS[name]+=1
    SURFACES.append(dict(name=name,id=f'{name}__{COUNTS[name]:03d}',p=p,n=n,t=u,b=v,uv=uv,w=float(wh[0]),h=float(wh[1]),style=style,meta=meta or {}))

def hull_faces(points):
    p=np.asarray(points,float);h=ConvexHull(p);groups={}
    for tri,eq in zip(h.simplices,h.equations):
        key=tuple(np.round(eq,6));groups.setdefault(key,set()).update(int(i) for i in tri)
    faces=[]
    for eq,ids in groups.items():
        n=np.array(eq[:3]);ids=list(ids);cen=p[ids].mean(0);u=norm(p[ids[0]]-cen);v=np.cross(n,u)
        ids.sort(key=lambda i:math.atan2(np.dot(p[i]-cen,v),np.dot(p[i]-cen,u)))
        poly=p[ids]
        if np.dot(np.cross(poly[1]-poly[0],poly[2]-poly[0]),n)<0:poly=poly[::-1]
        faces.append(poly)
    return faces

def box(name, center, size, style='beam', bevel=0., yaw=0., styles=None, transform=None):
    c=np.array(center,float);d=np.array(size,float)/2;points=[]
    if bevel>0:
        b=min(bevel,float(d.min())*.35)
        for sx in [-1,1]:
            for sy in [-1,1]:
                for sz in [-1,1]:
                    sig=np.array([sx,sy,sz])
                    for axis in range(3):
                        q=d-b;q[axis]=d[axis];points.append(q*sig)
    else:
        points=[np.array([sx,sy,sz])*d for sx in [-1,1] for sy in [-1,1] for sz in [-1,1]]
    rot=matrix_yaw(yaw)
    R,T=(rot,c) if transform is None else (transform[0]@rot,transform[0]@c+transform[1])
    grain=np.eye(3)[int(np.argmax(size))] if style in ['beam','beam_dark','woodedge'] else None
    for poly in hull_faces(points):
        n=norm(np.cross(poly[1]-poly[0],poly[2]-poly[0]))
        st=style
        if styles:
            a=int(np.argmax(abs(n)));key=['x','y','z'][a]+('+' if n[a]>0 else '-')
            st=styles.get(key,style)
        face(name,poly,st,grain=grain if st in ('beam','beam_dark','woodedge') else None,transform=(R,T))

def beam_between(name,a,b,width,depth=None,style='beam',bevel=0.):
    a=np.array(a,float);b=np.array(b,float);z=norm(b-a)
    helper=np.array([0,0,1.]) if abs(z[2])<.8 else np.array([1.,0,0])
    x=norm(np.cross(helper,z));y=np.cross(z,x);r=np.column_stack([x,y,z])
    box(name,[0,0,0],[width,depth or width,np.linalg.norm(b-a)],style,bevel=bevel,transform=(r,(a+b)/2))

def wall_side(name,x,inner):
    lo=-1.03;hi=1.18;bottom=.29
    # Slightly thick wedge, genuinely sloping at the top.
    points=[]
    for xx in [x-.065,x+.065]:
        for y,z in [(lo,bottom),(hi,bottom),(hi,2.59),(lo,3.035)]: points.append([xx,y,z])
    for poly in hull_faces(points):
        n=norm(np.cross(poly[1]-poly[0],poly[2]-poly[0]));out=(n[0]*x)>0
        face(name,poly,'wall_outer' if abs(n[0])>.9 and out else ('wall_inner' if abs(n[0])>.9 else 'woodedge'))

def cylinder(name,center,rings,segments=10,style='barrel',cap='lid',offset=0.,scale=(1,1),yaw=0):
    c=np.array(center,float);R=matrix_yaw(yaw);ringpts=[]
    for z,r in rings:
        ringpts.append(np.array([[r*math.cos(2*math.pi*i/segments+offset)*scale[0],r*math.sin(2*math.pi*i/segments+offset)*scale[1],z] for i in range(segments)]))
    height=rings[-1][0]-rings[0][0]
    for j in range(len(rings)-1):
        for i in range(segments):
            k=(i+1)%segments
            p=np.array([ringpts[j][i],ringpts[j][k],ringpts[j+1][k],ringpts[j+1][i]])
            tang=norm(p[1]-p[0])
            face(name,p,style,grain=tang,transform=(R,c),meta={'sector':i,'segments':segments,'row':j,'rows':len(rings)-1,'z0':(rings[j][0]-rings[0][0])/height,'z1':(rings[j+1][0]-rings[0][0])/height})
    face(name,ringpts[0][::-1],cap,transform=(R,c))
    face(name,ringpts[-1],cap,transform=(R,c))

def crate(name,center,size,yaw=0):
    box(name,center,size,'crate',bevel=.012,yaw=yaw,styles={'z+':'crate_top','z-':'woodedge'})

def build_geometry():
    # Floor, stone feet and principal frame.
    box('Floor',[0,.07,.28],[3.34,2.40,.16],'floor',bevel=.025)
    for x in [-1.54,1.54]:
        for y in [-1.07,1.13]:
            box('StoneFoot', [x,y,.12],[.38,.37,.24],'stone',bevel=.032,yaw=(-2 if x<0 else 3))
            h=3.08 if y<0 else 2.65
            box('Frame_Post',[x,y,(h+.23)/2],[.23,.23,h-.23],'beam',bevel=.022)
    wall_side('Wall_Left',-1.58,True);wall_side('Wall_Right',1.58,True)
    box('Wall_Back',[0,1.18,1.45],[3.17,.13,2.34],'wall_outer',styles={'y-':'wall_inner'})
    box('Front_Transom',[0,-1.07,2.775],[2.92,.12,.47],'vertical',styles={'y+':'wall_inner'})
    box('Frame_Header',[0,-1.19,2.525],[3.28,.28,.235],'beam',bevel=.023)
    box('Frame_Sill',[0,-1.15,.335],[3.30,.20,.16],'beam_dark',bevel=.012)
    box('Frame_RearBeam',[0,1.17,2.555],[3.43,.23,.20],'beam',bevel=.017)
    for x in [-1.53,1.53]:
        beam_between('Frame_SideRail',[x,-1.10,.46],[x,1.18,.46],.14,.15,style='beam_dark')
        beam_between('Brace_Knee',[x,-1.08,2.53],[x,-1.49,3.06],.12,.13,bevel=.008)
    # Roof: low-polygon broad planks; all grooves and nails are painted, not modeled.
    slope=-.205
    def rz(y):return 3.13+slope*(y+1.08)
    ys=[-1.57,1.43];xs=[-1.99,-1.63,-1.30,-.96,-.63,-.31,.04,.39,.72,1.08,1.42,1.73,1.99]
    jitter=[.0,.014,-.008,.007,-.018,.012,-.004,.014,-.012,.011,-.003,.006]
    for i in range(len(xs)-1):
        xa,xb=xs[i],xs[i+1];ya=ys[0]+jitter[i];yb=ys[1]+jitter[-i-1]*.6
        pts=[[x,y,rz(y)+z] for x in [xa,xb] for y in [ya,yb] for z in [-.078,0]]
        for poly in hull_faces(pts):
            n=norm(np.cross(poly[1]-poly[0],poly[2]-poly[0]))
            face('Roof_Deck',poly,'roof' if n[2]>.7 else ('roof_under' if n[2]<-.7 else 'woodedge'),meta={'roof_panel':i,'panels':len(xs)-1})
    beam_between('Roof_FasciaFront',[-2.04,-1.60,rz(-1.6)-.055],[2.04,-1.60,rz(-1.6)-.055],.135,.18,bevel=.016)
    beam_between('Roof_FasciaBack',[-2.04,1.43,rz(1.43)-.045],[2.04,1.43,rz(1.43)-.045],.12,.16,bevel=.012)
    for x in [-2.01,2.01]:
        beam_between('Roof_FasciaSide',[x,-1.61,rz(-1.61)-.033],[x,1.45,rz(1.45)-.033],.13,.16,bevel=.012)
    for x in [-1.49,-.77,0,.77,1.49]:
        beam_between('Roof_Rafter',[x,-1.50,rz(-1.50)-.155],[x,1.34,rz(1.34)-.155],.12,.17)
    # Low porch landing and two foot blocks. Side boards remain one planar polygon.
    box('Porch_Landing',[0,-1.68,.22],[2.39,1.02,.145],'floor',bevel=.023)
    for x in [-.87,.87]:box('Porch_Feet',[x,-1.86,.084],[.20,.27,.168],'beam_dark',bevel=.015)
    # Separate hinge transforms survive in the source payload. Main GLB is a merged static snapshot.
    for side,angle in [('Left',-105.),('Right',100.)]:
        sign=1 if side=='Left' else -1
        hinge=np.array([-1.355 if sign==1 else 1.355,-1.205,.37])
        T=(matrix_yaw(angle),hinge)
        box('Door_'+side,[sign*.667,0,1.052],[1.334,.11,2.104],'woodedge',bevel=.009,transform=T,styles={'y-':'door_'+side.lower(),'y+':'door_'+('right' if side=='Left' else 'left')})
        # Silhouette handles only. Hinge straps/rivets/Z-bracing are painted on each panel.
        localx=sign*1.19
        beam_between('Handle_'+side,T[0]@np.array([localx,-.10,.92])+hinge,T[0]@np.array([localx,-.10,1.15])+hinge,.035,.038,style='iron')
    # Shelving with visible negative spaces: not a single fake interior billboard.
    for x in [-1.23,.0,1.23]:box('Shelf_Upright',[x,.73,1.38],[.105,.10,2.06],'beam_dark')
    for z in [.48,1.21,1.94]:box('Shelf_Plank',[0,.77,z],[2.73,.62,.09],'beam_dark',bevel=.009)
    # L-shaped storage read, like the reference: two broad left-side shelves.
    for z in [1.21,1.94]:box('Shelf_LeftPlank',[-1.19,-.12,z],[.60,1.72,.085],'beam_dark',bevel=.009)
    box('Shelf_LeftFrontPost',[-1.37,-.91,1.37],[.10,.105,2.05],'beam_dark')
    crate('Prop_LeftShelfCrate',[-1.18,-.52,1.49],[.48,.60,.47])
    for i,y in enumerate([-.60,-.14]):
        cylinder('Prop_LeftPot',[-1.15,y,1.985],[(0,.12),(.035,.155),(.23,.15),(.29,.11)],segments=8,style='pot',cap='pot_lid')
    # Large reads: grain sacks, crates, barrels and grouped pantry pots.
    box('Prop_GrainSack',[-.83,-.23,.785],[.56,.46,.83],'sack_plain',bevel=.09,styles={'y-':'sack_front'})
    cylinder('Prop_SackTie',[-.83,-.23,1.18],[(0,.195),(.09,.175)],segments=8,style='sack_plain',cap='sack_plain',scale=(1.,.8))
    crate('Prop_ProduceCrate',[.89,-.51,.60],[.77,.61,.48],yaw=-4)
    crate('Prop_ShelfCrate',[-.80,.73,1.49],[.72,.45,.48])
    crate('Prop_LowCrate',[.27,.83,.73],[.54,.47,.42],yaw=3)
    crate('Prop_ExteriorCrate',[2.02,-.83,.32],[.56,.51,.60],yaw=-8)
    # External barrel: barrel hoops authored in its unique material panels, not repeated trim strips.
    cylinder('Prop_ExteriorBarrel',[2.07,.05,.03],[(0,.31),(.11,.34),(.49,.395),(.91,.35),(1.04,.31)],segments=12,style='barrel',cap='lid',offset=math.pi/12)
    for j,(x,z,r,h) in enumerate([(.22,1.26,.22,.42),(.87,1.26,.245,.43)]):
        cylinder('Prop_PantryKeg',[x,.78,z],[(0,r*.89),(.07,r),(h*.6,r*1.03),(h,r*.90)],segments=8,style='barrel',cap='lid')
    for i,x in enumerate([-.99,-.49,.06,.57,1.04]):
        r=[.145,.125,.16,.14,.13][i];h=[.29,.25,.30,.25,.28][i]
        cylinder('Prop_ClayPot',[x,.78,1.985],[(0,r*.77),(.04,r),(h*.65,r),(h*.91,r*.74),(h,r*.70)],segments=8,style='pot',cap='pot_lid')
    # Six deliberately large produce pieces, with no stems or tiny leaf meshes.
    for i,(x,y,r) in enumerate([(.63,-.65,.106),(.86,-.68,.11),(1.05,-.52,.12),(.72,-.39,.125),(.96,-.33,.12),(1.12,-.71,.108)]):
        cylinder('Prop_Produce',[x,y,.83],[(0,r*.6),(.07,r),(.15,r*.65)],segments=6,style='produce_red' if i<3 else 'produce_green',cap='produce_red' if i<3 else 'produce_green')
    # One four-sided lantern. Opaque emissive amber panes are appropriate at top-down distance.
    lx,ly,lz=1.47,-1.40,2.075
    box('Lantern_Glass',[lx,ly,lz],[.18,.17,.265],'glass')
    box('Lantern_Base',[lx,ly,lz-.155],[.265,.24,.065],'iron',bevel=.012)
    cylinder('Lantern_Cap',[lx,ly,lz+.13],[(0,.19),(.13,.075)],segments=4,style='iron',cap='iron',offset=math.pi/4,scale=(1.,.92))
    for dx in [-.107,.107]:
        for dy in [-.102,.102]:box('Lantern_Frame',[lx+dx,ly+dy,lz],[.026,.026,.30],'iron')
    beam_between('Lantern_Bracket',[lx,-1.08,2.46],[lx,-1.42,2.46],.035,.04,style='iron')
    beam_between('Lantern_Hanger',[lx,-1.42,2.46],[lx,-1.42,2.35],.028,.028,style='iron')
    # Flattened rear vent accent, completely painted.
    box('Vent_Right',[1.655,.20,2.115],[.014,.44,.31],'iron',styles={'x+':'vent'})


def maxrect_pack(density):
    """Non-overlapping best-area guillotine rectangles; no rotations or UV stacking."""
    rects=[]
    for i,s in enumerate(SURFACES):
        w=max(2,int(math.ceil(s['w']*density))+1);h=max(2,int(math.ceil(s['h']*density))+1)
        rects.append((i,w+PAD*2,h+PAD*2,w,h))
    rects.sort(key=lambda v:(-max(v[1],v[2]),-v[1]*v[2]))
    free=[(0,0,S,S)];packed={}
    for i,w,h,cw,ch in rects:
        choices=[(W*H-w*h,min(W-w,H-h),y,x,j) for j,(x,y,W,H) in enumerate(free) if W>=w and H>=h]
        if not choices:return None
        *_,j=min(choices);x,y,W,H=free.pop(j)
        # Split through the longer leftover direction. These regions are disjoint.
        if W-w>H-h:
            new=[(x+w,y,W-w,H),(x,y+h,w,H-h)]
        else:
            new=[(x+w,y,W-w,h),(x,y+h,W,H-h)]
        free.extend(q for q in new if q[2]>0 and q[3]>0)
        packed[i]=(x+PAD,y+PAD,cw,ch)
    return packed


def load_art():
    a=Image.open(ROOT/'source/generated_architecture.png').convert('RGB')
    source={
        'roof':a.crop((3,3,765,508)),
        'wall_outer':a.crop((776,3,1532,507)),
        'wall_inner':a.crop((5,516,763,1018)),
        'door_left':a.crop((778,517,1140,1018)),
        'door_right':a.crop((1159,517,1531,1018)),
        'iron':a.crop((841,565,967,587)),
        'beam':a.crop((795,73,1460,125)),
    }
    for key in ['sack','crate','stone','barrel','glass','pot']:
        p=ROOT/f'source/prop_{key}.png'
        if p.exists():source[key]=Image.open(p).convert('RGB')
    return source


def crop_fraction(im,x0,y0,x1,y1):
    w,h=im.size;return im.crop((int(x0*w),int(y0*h),max(int(x1*w),int(x0*w)+1),max(int(y1*h),int(y0*h)+1)))


def source_patch(s,art,w,h,index):
    style=s['style'];seed=int(hashlib.sha256(s['id'].encode()).hexdigest()[:8],16);rng=np.random.default_rng(seed)
    variation=.96+rng.random()*.075
    if style in ('door_left','door_right'):
        im=art[style];variation=1.
    elif style in ('roof','roof_under'):
        im=art['roof'];i=s['meta'].get('roof_panel',0);n=s['meta'].get('panels',12)
        im=crop_fraction(im,i/n,0,(i+1)/n,1)
        variation=1.02 if style=='roof' else .69
    elif style in ('wall_outer','wall_inner'):
        im=art[style];ox=(seed%79)/1000;oy=((seed//79)%43)/1000
        im=crop_fraction(im,ox,oy,.93+ox,.95+oy)
    elif style=='vertical':im=art['roof']
    elif style=='floor':
        im=art['roof'].transpose(Image.Transpose.ROTATE_90);variation=1.06
    elif style in ('beam','beam_dark','woodedge'):
        # Independently chosen continuous grain strip, stretched only along the grain.
        src=art['wall_outer'];yy=(index*61)%450
        im=src.crop((40+(index*17)%180,yy+4,690+(index*7)%40,min(506,yy+44)))
        variation=.78 if style=='beam_dark' else 1.02
        if w<h*.4:im=im.transpose(Image.Transpose.ROTATE_90)
    elif style in ('crate','crate_top'):
        im=art['crate'] if style=='crate' else art['roof']
    elif style=='barrel':
        im=art['barrel'];m=s['meta'];f=(m.get('sector',0)+.5)/m.get('segments',1)
        # A contiguous uniquely cropped strip per facet; metal hoops are part of this image.
        cx=.12+.74*f;dw=.08
        im=crop_fraction(im,max(0,cx-dw/2),1-m.get('z1',1),min(1,cx+dw/2),1-m.get('z0',0))
    elif style=='lid':
        im=art['roof'].crop((35,70,600,492));variation=.85
    elif style in ('sack','sack_plain','sack_front'):
        im=art['sack'];m=s['meta'];normal=s['n']
        if style=='sack_front':
            im=art['sack']
        elif style=='sack' and normal[1]<-.45:
            # Wheat marking belongs to front-facing sectors only, never wrapped around the sack.
            left=normal[0]<0
            im=crop_fraction(im,.04 if left else .49,1-m.get('z1',1),.51 if left else .96,1-m.get('z0',0))
        else:im=crop_fraction(im,0,.17,.23,.80)
        variation=1.04
    elif style=='stone':im=art['stone'];variation=1.02
    elif style in ('pot','pot_lid'):
        im=art['pot'];variation=.90+(index%5)*.045
    elif style in ('produce_red','produce_green'):
        im=art['pot'];arr=np.array(im).astype(float)/255
        gray=arr.mean(2,keepdims=True)
        tint=np.array([.68,.19,.055] if style=='produce_red' else [.39,.47,.10])
        arr=np.clip((gray*.72+.35)*tint,0,1);im=Image.fromarray((arr*255).astype('uint8'));variation=1.
    elif style=='glass':im=art['glass'];variation=1.1
    elif style=='vent':
        # Composite six broad iron louvers: not a repeating material sampler.
        im=art['iron'].resize((280,180));dr=ImageDraw.Draw(im)
        for yy in [25,49,73,97,121,145]:dr.rectangle((22,yy,258,yy+12),fill=(30,29,26));dr.line((22,yy,258,yy),fill=(108,101,83),width=2)
    else:im=art['iron']
    im=im.resize((w,h),Image.Resampling.LANCZOS)
    if abs(variation-1)>.001:im=ImageEnhance.Brightness(im).enhance(variation)
    return np.array(im).astype(np.float32)/255


def make_maps(packed):
    art=load_art();base=np.full((S,S,3),[.24,.15,.08],dtype=np.float32)
    normal=np.zeros((S,S,3),np.uint8);normal[:]=[128,128,255]
    orm=np.zeros((S,S,3),np.uint8);orm[:]=[255,220,0]
    emission=np.zeros((S,S,3),np.uint8)
    outline=Image.new('RGB',(S,S),(18,23,28));draw=ImageDraw.Draw(outline)
    for idx,s in enumerate(SURFACES):
        x,y,w,h=packed[idx];rgb=source_patch(s,art,w,h,idx)
        lum=rgb@np.array([.2126,.7152,.0722],np.float32)
        smooth=gaussian_filter(lum, max(.5,min(w,h)*.005))
        # Conservative relief reconstructed from image contrast; NOT a sculpt bake.
        gy,gx=np.gradient(smooth) if min(w,h)>1 else (smooth*0,smooth*0)
        strength=3.8 if s['style'] not in ('glass','sack','sack_plain') else 1.4
        nx=-gx*strength;ny=gy*strength;nz=np.ones_like(nx)
        den=np.sqrt(nx*nx+ny*ny+1);n=np.stack([nx/den,ny/den,nz/den],-1)
        nn=np.clip((n*.5+.5)*255,0,255).astype(np.uint8)
        metal=np.zeros((h,w),np.float32);rough=np.clip(.83-(lum-.34)*.14,.66,.94)
        if s['style'] in ('iron','vent'):
            metal[:]=.70;rough[:]=.62
        if s['style'].startswith('door_') or s['style']=='barrel':
            sat=rgb.max(2)-rgb.min(2)
            metal=np.clip((.15-sat)/.10,0,1)*.67
            rough=rough*(1-metal)+.61*metal
        if s['style'] in ('pot','pot_lid'):rough[:]=.68
        if s['style']=='glass':rough[:]=.30
        # Local artwork crevices only. Macro contact occlusion comes from renderer / game lighting.
        ao=np.clip(.89+lum*.22,.86,1)
        oo=np.stack([ao,rough,metal],-1);oo=np.clip(oo*255,0,255).astype('uint8')
        ee=np.zeros((h,w,3),np.uint8)
        if s['style']=='glass':ee=np.clip(rgb*np.array([1.0,.85,.55])*255,0,255).astype('uint8')
        for atlas,patch in [(base,rgb),(normal,nn),(orm,oo),(emission,ee)]:
            atlas[y-PAD:y+h+PAD,x-PAD:x+w+PAD]=np.pad(patch,((PAD,PAD),(PAD,PAD),(0,0)),mode='edge')
        shade=(55+(idx*53)%150,65+(idx*89)%140,60+(idx*23)%160)
        draw.rectangle((x,y,x+w-1,y+h-1),fill=shade)
        points=[(x+q[0]*(w-1),y+(1-q[1])*(h-1)) for q in s['uv']]
        draw.line(points+[points[0]],fill=(235,239,232),width=2)
    Image.fromarray(np.clip(base*255,0,255).astype('uint8')).quantize(colors=256,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).convert('RGB').save(ROOT/'textures/T_Shed_BaseColor.png',compress_level=9)
    normal=np.clip(np.round(normal.astype(np.float32)/4)*4,0,255).astype(np.uint8)
    normal[:,:,2]=np.maximum(normal[:,:,2],248)
    orm=np.clip(np.round(orm.astype(np.float32)/4)*4,0,255).astype(np.uint8)
    Image.fromarray(normal).save(ROOT/'textures/T_Shed_Normal_GL.png',compress_level=6)
    ndx=normal.copy();ndx[:,:,1]=255-ndx[:,:,1];Image.fromarray(ndx).save(ROOT/'textures/T_Shed_Normal_DX.png',compress_level=6)
    Image.fromarray(orm).save(ROOT/'textures/T_Shed_ORM.png',compress_level=6)
    Image.fromarray(emission).save(ROOT/'textures/T_Shed_Emissive.png',compress_level=6)
    outline.save(ROOT/'previews/UV_Layout_4096.png')
    return None


def assemble(packed,density):
    objs={};islands=[]
    for i,s in enumerate(SURFACES):
        o=objs.setdefault(s['name'],{'name':s['name'],'positions':[],'normals':[],'tangents':[],'uvs':[],'triangles':[],'face_islands':[]})
        start=len(o['positions']);p=s['p'];x,y,w,h=packed[i]
        for pos,uv in zip(p,s['uv']):
            o['positions'].append([round(float(v),7) for v in pos]);o['normals'].append(s['n'].round(7).tolist())
            o['tangents'].append([*s['t'].round(7).tolist(),1.0])
            # UVs in Blender convention (+V up). Texel center endpoints avoid bleeding.
            o['uvs'].append([(x+.5+uv[0]*(s['w']*density))/S,1-(y+.5+(1-uv[1])*(s['h']*density))/S])
        # Convex n-gon fan triangulation.
        for j in range(1,len(p)-1):
            o['triangles'].append([start,start+j,start+j+1]);o['face_islands'].append(i)
        islands.append({'id':s['id'],'object':s['name'],'style':s['style'],'rect':[x,y,w,h],'size_m':[s['w'],s['h']],'density':[density,density]})
    payload={'asset':'WoodenFoodShed','units':'meters','up':'Z','front':'-Y','atlas_size':S,'padding_px':PAD,'pixels_per_meter':density,'door_angles_deg':{'Left':-105,'Right':100},'objects':list(objs.values()),'islands':islands}
    (ROOT/'source/mesh_payload.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
    return payload


def write_glb(payload,filename,closed=False):
    pos=[];nrm=[];uv=[];tang=[];tris=[]
    for o in payload['objects']:
        p=np.array(o['positions']);n=np.array(o['normals']);ta=np.array(o['tangents']);off=len(pos)
        if closed and o['name'].startswith(('Door_','Handle_')):
            side=o['name'].split('_',1)[1];hinge=np.array([-1.355 if side=='Left' else 1.355,-1.205,.37])
            angle=105 if side=='Left' else -100;r=matrix_yaw(angle)
            p=(p-hinge)@r.T+hinge;n=n@r.T;ta[:,:3]=ta[:,:3]@r.T
        # Right-handed Z-up to glTF Y-up: (x,z,-y).
        pos.extend(p[:,[0,2,1]]*np.array([1,1,-1]));nrm.extend(n[:,[0,2,1]]*np.array([1,1,-1]))
        t=ta.copy();t[:,:3]=ta[:,[0,2,1]]*np.array([1,1,-1]);t[:,3]=-t[:,3];tang.extend(t)
        uu=np.array(o['uvs']);uu[:,1]=1-uu[:,1];uv.extend(uu)
        tris.extend(np.array(o['triangles'])+off)
    arrays=[np.array(pos,'<f4'),np.array(nrm,'<f4'),np.array(uv,'<f4'),np.array(tang,'<f4'),np.array(tris,'<u2').reshape(-1)]
    blob=bytearray();views=[];access=[]
    def add_bytes(data,target=None):
        while len(blob)%4:blob.append(0)
        vi=len(views);views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(data)})
        if target:views[-1]['target']=target
        blob.extend(data);return vi
    for k,a in enumerate(arrays):
        vi=add_bytes(a.tobytes(),34963 if k==4 else 34962)
        ac={'bufferView':vi,'componentType':5123 if k==4 else 5126,'count':len(a),'type':['VEC3','VEC3','VEC2','VEC4','SCALAR'][k]}
        if k==0:ac.update(min=a.min(0).astype(float).tolist(),max=a.max(0).astype(float).tolist())
        access.append(ac)
    images=[]
    for file in ['T_Shed_BaseColor.png','T_Shed_Normal_GL.png','T_Shed_ORM.png','T_Shed_Emissive.png']:
        images.append({'name':Path(file).stem,'mimeType':'image/png','bufferView':add_bytes((ROOT/'textures'/file).read_bytes())})
    material={'name':'M_WoodenFoodShed','pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicRoughnessTexture':{'index':2},'metallicFactor':1.,'roughnessFactor':1.},'normalTexture':{'index':1,'scale':.55},'occlusionTexture':{'index':2,'strength':.55},'emissiveTexture':{'index':3},'emissiveFactor':[1.,1.,1.],'extensions':{'KHR_materials_emissive_strength':{'emissiveStrength':2.3}},'doubleSided':False}
    doc={'asset':{'version':'2.0','generator':'WoodenFoodShed deterministic surface-atlas builder v1'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'name':'SM_WoodenFoodShed'+('_Closed' if closed else ''),'mesh':0}],'meshes':[{'name':'SM_WoodenFoodShed','primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'TEXCOORD_0':2,'TANGENT':3},'indices':4,'material':0,'mode':4}]}],'materials':[material],'textures':[{'source':i,'sampler':0} for i in range(4)],'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071}],'images':images,'accessors':access,'bufferViews':views,'buffers':[{'byteLength':len(blob)}],'extensionsUsed':['KHR_materials_emissive_strength'],'extras':{'triangles':len(tris),'unit':'meter','uv0':'Unique 0-1 non-overlapping; approximately uniform texel density','collision':'Not embedded; import script adds simple collision'}}
    js=json.dumps(doc,separators=(',',':')).encode();js+=b' ' *((-len(js))%4);blob+=b'\0'*((-len(blob))%4)
    data=struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(blob))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(blob),b'BIN\0')+blob
    (ROOT/'models'/filename).write_bytes(data)
    return doc


def main():
    build_geometry();tri=sum(len(s['p'])-2 for s in SURFACES)
    print('surfaces',len(SURFACES),'triangles',tri,flush=True)
    if tri>=4000:raise RuntimeError(f'Triangle budget exceeded: {tri}')
    lo,hi=80.,450.;best=None
    for j in range(11):
        d=(lo+hi)/2;pack=maxrect_pack(d)
        if pack is None:hi=d
        else:lo=d;best=pack
    density=round(lo*.975,4);packed=maxrect_pack(density)
    if packed is None:raise RuntimeError('UV packing failed')
    print('density',density,'packing ready',flush=True)
    make_maps(packed);payload=assemble(packed,density)
    doc=write_glb(payload,'wooden_food_shed.glb');write_glb(payload,'wooden_food_shed_closed.glb',True)
    stats={'triangles':tri,'objects_in_blender_source':len(payload['objects']),'glb_meshes':1,'glb_materials':1,'export_vertices':doc['accessors'][0]['count'],'unique_surface_islands':len(SURFACES),'atlas_size':[S,S],'island_padding_px':PAD,'density_px_per_meter':density,'texture_rectangle_occupancy':sum(v[2]*v[3] for v in packed.values())/(S*S),'bounds_gltf_m':{'min':doc['accessors'][0]['min'],'max':doc['accessors'][0]['max']},'runtime_verified':{'GLB':'pending independent round-trip checks','Blender':False,'Unreal_5_7':False},'notes':['Base color authored with image generation; UVs never tile, stack or mirror.','Normal/ORM maps are conservative image-derived approximations, not sculpt-baked or measured PBR.','All source faces retain their own padded atlas allocation; sub-pixel rounding affects the smallest bevels.']}
    (ROOT/'validation/asset_stats.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    print(json.dumps(stats,indent=2),flush=True)

if __name__=='__main__':main()
