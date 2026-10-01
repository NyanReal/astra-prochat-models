"""Area-weighted, unique UV atlas authoring. No mirrored/reused UV islands.
Paint, numbers, service marks, color, surface roughness and tiny bevel detail are
independent per island. Texel density is a deliberate authoring priority.
"""
from pathlib import Path
import json, math, hashlib
from collections import defaultdict
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SIZE=2048; PAD=6
DENSITY={'armor':1.,'frame':.22,'interior':.38,'pilot':.85,'accent':.55,'glass':.24}
COLORS={'armor':'#ddd0a8','frame':'#4a646e','interior':'#73847b','pilot':'#d29d59','accent':'#cfb858','glass':'#77bbbc'}
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def coverage(p):
    uv=p.uv[p.faces];a=uv[:,1]-uv[:,0];b=uv[:,2]-uv[:,0]
    return max(float(np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0]).sum()*.5),1e-5)

def pack_rects(items,size):
    # Disjoint guillotine rectangles: bounded free list, no quadratic containment pruning.
    free=[(0,0,size,size)];placed={}
    for idx,w,h in sorted(items,key=lambda q:(max(q[1:]),q[1]*q[2]),reverse=True):
        choices=[]
        for k,(x,y,fw,fh) in enumerate(free):
            if w<=fw and h<=fh:choices.append((min(fw-w,fh-h),max(fw-w,fh-h),k))
        if not choices:return None
        _,_,k=min(choices);x,y,fw,fh=free.pop(k);placed[idx]=(x,y,w,h)
        dw,dh=fw-w,fh-h
        if dw>dh:
            if dw:free.append((x+w,y,dw,fh))
            if dh:free.append((x,y+h,w,dh))
        else:
            if dh:free.append((x,y+h,fw,dh))
            if dw:free.append((x+w,y,dw,h))
    return placed

def allocate(patches):
    infos=[]
    for p in patches:
        a=p.area/coverage(p);aspect=max(.025,min(40.,p.aspect));fac=DENSITY[p.category]
        infos.append((math.sqrt(a*aspect)*fac,math.sqrt(a/aspect)*fac))
    def attempt(density):
        sizes=[(i,max(6,int(w*density))+PAD*2,max(6,int(h*density))+PAD*2) for i,(w,h) in enumerate(infos)]
        return pack_rects(sizes,SIZE)
    lo,hi=80.,6000.;best=None
    for _ in range(11):
        mid=(lo+hi)/2;res=attempt(mid)
        if res is None:hi=mid
        else:lo=mid;best=res
    if best is None:raise RuntimeError('Cannot pack atlas at minimum density')
    for i,p in enumerate(patches):
        x,y,w,h=best[i];p.rect=(x,y,w,h)
    return lo

def font(size,bold=True):
    try:return ImageFont.truetype(FONT if bold else REG,max(5,int(size)))
    except OSError:return ImageFont.load_default()

def paint_patch(p,w,h):
    seed=int.from_bytes(hashlib.sha256(p.name.encode()).digest()[:8],'little');rng=np.random.default_rng(seed)
    yy,xx=np.mgrid[0:h,0:w];u=xx/max(w-1,1);v=yy/max(h-1,1)
    c=np.array(p.color,float)
    grad=(.5-v)*2.0+np.sin(u*3.4+seed%10)*.8+rng.normal(0,.16,(h,w))
    # Extremely restrained wear: this is a smooth enamel mech, not a rust pile.
    if p.category=='armor':grad+=np.exp(-((u-.23)**2+(v-.2)**2)*3)*1.8
    rgb=np.clip(c[None,None,:]+grad[:,:,None],0,255).astype('uint8')
    img=Image.fromarray(rgb);draw=ImageDraw.Draw(img)
    height=Image.new('L',(w,h),128);hd=ImageDraw.Draw(height)
    dark=(76,82,78);muted=(137,140,124);cream=(238,230,207);gold=(193,139,52)
    W=min(w,h)
    def text(x,y,t,sz,col=dark,anchor=None,bold=True):draw.text((int(x*w),int(y*h)),t,font=font(sz*W,bold),fill=col,anchor=anchor,spacing=max(1,int(W*.015)))
    def line(coords,col=muted,width=.004,groove=False):
        xy=[(int(x*w),int(y*h)) for x,y in coords];ww=max(1,int(W*width));draw.line(xy,fill=col,width=ww,joint='curve')
        if groove:hd.line(xy,fill=116,width=ww)
    def triangle(x,y,r=.052,col=gold):
        pts=[(x*w,(y-r)*h),((x-r*.85)*w,(y+r*.6)*h),((x+r*.85)*w,(y+r*.6)*h)]
        draw.polygon(pts,fill=col)
        if W>80:draw.line([(x*w,(y-r*.35)*h),(x*w,(y+r*.08)*h)],fill=dark,width=max(1,int(W*.009)))
    def bolt(x,y):
        r=max(1,int(W*.009));cx=x*w;cy=y*h;draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(93,98,91));hd.ellipse((cx-r,cy-r,cx+r,cy+r),fill=112)
        draw.line((cx-r*.5,cy,cx+r*.5,cy),fill=(176,177,156),width=1)
    def rabbit_badge(x,y,r=.048):
        cx=x*w;cy=y*h;rr=r*W
        draw.ellipse((cx-rr,cy-rr*.55,cx+rr,cy+rr*1.15),fill=dark)
        for sign in [-1,1]:draw.rounded_rectangle((cx+sign*rr*.47-rr*.25,cy-rr*1.75,cx+sign*rr*.47+rr*.25,cy),radius=rr*.23,fill=dark)
    d=p.detail
    if d and W>35:
        if d=='socket_face':
            # Unique face map with radial grease holes, indexing marks and engraved rings.
            for rad in [.39,.44]:
                boxx=(w*(.5-rad),h*(.5-rad),w*(.5+rad),h*(.5+rad))
                draw.ellipse(boxx,outline=(90,109,105),width=max(1,int(W*.008)))
                hd.ellipse(boxx,outline=112,width=max(1,int(W*.007)))
            for k in range(12):
                a=2*math.pi*k/12;cx=.5+.34*math.cos(a);cy=.5+.34*math.sin(a)
                rr=W*.020
                draw.ellipse((cx*w-rr,cy*h-rr,cx*w+rr,cy*h+rr),fill=(18,23,24),outline=(116,127,122),width=max(1,int(W*.004)))
            line([(.47,.07),(.47,.14)],gold,.022)
            line([(.53,.07),(.53,.14)],gold,.022)
        elif d.startswith('cheek_'):
            # Each side is painted independently, including distinct serials and marks.
            text(.33,.29,'03',.18,dark)
            text(.29,.43,'POD / '+d[-1],.055,dark)
            line([(.30,.20),(.66,.20)],gold,.032)
            line([(.29,.55),(.31,.69),(.48,.75),(.65,.72)],muted,.007,True)
            triangle(.51,.81,.061)
            for x,y in [(.36,.60),(.63,.64)]:bolt(x,y)
        elif d.startswith('side_service_'):
            text(.23,.23,'ACCESS / '+d[-1],.080,dark)
            text(.23,.34,'H-03 / AUX BUS',.038,muted)
            line([(.20,.17),(.70,.17),(.79,.26),(.79,.68),(.68,.78),(.21,.78),(.20,.17)],muted,.007,True)
            for j in range(4):
                line([(.28,.46+j*.055),(.62,.46+j*.055)],dark,.021,True)
                line([(.28,.47+j*.055),(.62,.47+j*.055)],cream,.005)
            triangle(.68,.39,.035)
            for x,y in [(.25,.22),(.71,.70)]:bolt(x,y)
        elif d=='rear_cell':
            text(.22,.16,'POWER',.085,dark)
            text(.24,.27,'03',.19,dark)
            text(.21,.77,'FIELD CELL',.064,dark)
            text(.21,.86,'48 V / LOCKED',.035,muted)
            line([(.18,.66),(.71,.66)],gold,.035)
            line([(.18,.56),(.23,.60),(.78,.60)],muted,.006,True)
            for x,y in [(.18,.20),(.81,.20),(.22,.87),(.77,.87)]:bolt(x,y)
        elif d=='upper_visor':
            line([(.24,.56),(.72,.56)],gold,.045)
            text(.27,.24,'LIFT POINT',.072,dark)
        elif d=='liner':
            for j in range(3):
                line([(.12,.22+j*.24),(.21,.17+j*.24),(.79,.17+j*.24),(.88,.22+j*.24)],(78,82,74),.010,True)
            for x,y in [(.17,.17),(.83,.17),(.17,.83),(.83,.83)]:bolt(x,y)
        elif d=='hatch_inner':
            line([(.16,.20),(.22,.75),(.77,.75),(.84,.20)],(111,131,119),.018,True)
            text(.26,.12,'LOAD 120 kg',.070,(204,204,166))
            for x,y in [(.17,.25),(.83,.25),(.24,.70),(.76,.70)]:bolt(x,y)
        elif d=='port':
            draw.rounded_rectangle((w*.18,h*.18,w*.82,h*.82),radius=max(1,W*.10),fill=(33,44,44))
            hd.rectangle((w*.18,h*.18,w*.82,h*.82),fill=105)
            for j in range(3):
                for k in range(2):
                    x=(.32+j*.18)*w;y=(.38+k*.24)*h;rr=W*.040
                    draw.ellipse((x-rr,y-rr,x+rr,y+rr),fill=gold)
        elif d=='serial':
            text(.16,.23,'H-03 / POWER',.19,dark)
        elif d=='spine':
            for j in range(5):line([(.16,.18+j*.14),(.83,.18+j*.14)],(83,98,97),.018,True)
        elif d=='front_hatch':
            text(.32,.22,'03',.31,dark)
            text(.30,.63,'HOPPER',.062,dark)
            text(.30,.72,'FIELD UTILITY / 03',.026,muted)
            line([(.13,.31),(.15,.58),(.24,.78)],muted,.005,True)
            line([(.85,.31),(.84,.63),(.75,.78)],muted,.005,True)
            text(.30,.14,'FRONT ENTRY',.030,muted)
            text(.71,.49,'H',.14,dark);triangle(.19,.64,.044)
            line([(.18,.17),(.22,.17)],gold,.018)
            for x,y in [(.22,.27),(.81,.29),(.24,.73),(.77,.76)]:bolt(x,y)
        elif d.startswith('shoulder'):
            if d.endswith('R'):
                text(.30,.28,'03',.27);text(.29,.65,'UTILITY FRAME',.044);text(.29,.72,'HOPPER / 03',.026,muted)
            else:
                triangle(.45,.34,.12,dark);text(.30,.54,'FIELD',.083);text(.30,.65,'EXPLORATION UNIT',.033)
                line([(.32,.75),(.59,.75)],gold,.025)
            text(.28,.16,'H-03 / SHELL',.025,muted)
            line([(.18,.70),(.23,.76),(.26,.76)],muted,.005,True)
        elif d.startswith('forearm'):
            text(.24,.24,'L / M1' if d.endswith('L') else 'R / M1',.09)
            line([(.25,.48),(.25,.76),(.57,.76),(.65,.69)],muted,.004,True)
            triangle(.62,.35,.055);text(.26,.64,'SERVICE',.026,muted)
            for x,y in [(.25,.54),(.56,.69)]:bolt(x,y)
        elif d.startswith('thigh'):
            triangle(.51,.62,.063);text(.30,.25,'03',.08,muted)
            line([(.27,.35),(.33,.39),(.62,.39)],muted,.004,True)
        elif d.startswith('shin'):
            text(.28,.24,'HOPPER',.055);triangle(.58,.66,.068)
            line([(.23,.43),(.29,.40),(.63,.40)],muted,.004,True)
            text(.28,.53,'ACTUATOR / '+('L' if d.endswith('L') else 'R'),.027,muted)
        elif d=='cheek':
            text(.28,.60,'H-03',.055);triangle(.55,.76,.067)
            line([(.3,.26),(.42,.30),(.62,.30)],muted,.004,True)
        elif d=='backpack':
            text(.14,.11,'POWER UNIT',.067);text(.43,.68,'03',.17)
            text(.44,.88,'FIELD SYSTEMS',.023,muted)
            rabbit_badge(.81,.21,.048)
            for x,y in [(.12,.13),(.86,.13),(.12,.88),(.86,.88)]:bolt(x,y)
        elif d in ['service','panel','small_service']:
            line([(.19,.27),(.24,.23),(.79,.23),(.81,.28),(.81,.76),(.19,.76),(.19,.27)],muted,.004,True)
            text(.27,.38,'SERVICE',.060);text(.27,.50,'H-03 / '+str(seed%900+100),.031,muted)
            for x,y in [(.24,.29),(.76,.70)]:bolt(x,y)
            triangle(.69,.51,.037)
        elif d=='foot':
            text(.28,.47,'03',.14,muted);line([(.26,.75),(.65,.75)],muted,.008,True)
        elif d=='toe':
            text(.25,.36,'FIELD',.12,muted)
        elif d=='hand':
            text(.25,.35,'03',.18,muted)
        elif d=='belly':
            text(.18,.30,'CAUTION',.065,(146,158,148));line([(.17,.6),(.29,.69),(.65,.69)],(45,57,54),.008,True)
        elif d=='cushion':
            for x in [.2,.5,.8]:line([(x,.12),(x,.84)],(104,82,48),.008,True)
        elif d=='deck':
            for j in range(7):
                y=.14+j*.12;line([(.1,y),(.86-rng.uniform(0,.04),y)],(89,101,97),.022,True)
            text(.12,.04,'STEP / NON-SLIP',.045,(190,183,153))
        elif d=='stripe':
            for j in range(5):line([(.1+j*.17,.22),(.17+j*.17,.78)],dark,.045)
        elif d=='display':
            draw.rectangle((0,0,w,h),fill=(27,61,57))
            text(.10,.10,'READY',.18,(154,233,202));text(.10,.46,'03 / 100%',.10,(112,198,174),bold=False)
            line([(.10,.79),(.80,.79)],(135,218,184),.04)
        elif d=='latch':
            line([(.28,.38),(.72,.38)],dark,.04)
        # Sparse, unique edge scuffs only on selected enamel panels.
        if p.category=='armor':
            for k in range(5):
                x=float(rng.uniform(.20,.8));y=float(rng.choice([.19,.82])+rng.normal(0,.018))
                l=float(rng.uniform(.008,.026));line([(x,y),(x+l,y+.005)],(171,172,154),.002)
    # Roughness/metalness are encoded per island, not inferred from color at runtime.
    rough,metal,ao={
        'Paint':(.42,.10,.98),'Metal':(.34,.72,.94),'Rubber':(.82,.01,.94),
        'Fabric':(.82,0.,.98),'Eye':(.16,0.,1.),'Glass':(.10,0.,1.),
        'WarmLight':(.3,0.,1.),'CoolLight':(.30,0.,1.)}[p.material]
    if p.material=='Metal':
        rough,metal=(.48,.68) if np.mean(p.color)<100 else (.28,.82)
    height_arr=np.array(height,dtype=np.float32)
    rr=np.clip(rough*255+(128-height_arr)*.8+grad*.6,0,255).astype(np.uint8)
    orm=np.zeros((h,w,3),np.uint8);orm[:,:,0]=np.clip(ao*255-(128-height_arr)*.30,0,255);orm[:,:,1]=rr;orm[:,:,2]=int(metal*255)
    gy,gx=np.gradient(height_arr/255.) if w>1 and h>1 else (np.zeros((h,w)),np.zeros((h,w)))
    normals=np.stack([-gx*1.8,-gy*1.8,np.ones((h,w))],axis=-1);normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    normalmap=np.clip(np.rint(normals*127.5+127.5),0,255).astype(np.uint8)
    return img,Image.fromarray(orm),Image.fromarray(normalmap)

def write_atlas(patches,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    density=allocate(patches)
    atlas=Image.new('RGB',(SIZE,SIZE),(25,28,28));orm=Image.new('RGB',(SIZE,SIZE),(255,180,0));normal=Image.new('RGB',(SIZE,SIZE),(128,128,255))
    layout=Image.new('RGB',(SIZE,SIZE),(24,30,32));ld=ImageDraw.Draw(layout)
    stats=defaultdict(lambda:dict(surface_area_m2=0.,uv_pixel_area=0.,islands=0));records=[]
    for idx,p in enumerate(patches):
        x,y,rw,rh=p.rect;w=rw-2*PAD;h=rh-2*PAD
        images=paint_patch(p,w,h)
        for target,img in zip([atlas,orm,normal],images):
            arr=np.pad(np.array(img),((PAD,PAD),(PAD,PAD),(0,0)),mode='edge');target.paste(Image.fromarray(arr),(x,y))
        c=COLORS[p.category];ld.rectangle((x+PAD,y+PAD,x+PAD+w-1,y+PAD+h-1),fill=c,outline=(245,241,223),width=2)
        if min(w,h)>42:ld.text((x+PAD+5,y+PAD+5),f'{idx:03d}  {p.name[:26]}',fill=(30,39,39),font=font(min(23,h*.18)))
        uv_cov=coverage(p);pixels=uv_cov*(w-1)*(h-1)
        stats[p.category]['surface_area_m2']+=p.area;stats[p.category]['uv_pixel_area']+=pixels;stats[p.category]['islands']+=1
        records.append(dict(id=idx,name=p.name,category=p.category,node=p.node,outer_rect=[x,y,rw,rh],padding=PAD,
                            surface_area_m2=p.area,uv_coverage=uv_cov,uv_pixel_area=pixels))
        p.uv=(p.uv*np.array([w-1,h-1])+np.array([x+PAD+.5,y+PAD+.5]))/SIZE
    atlas.save(out/'HOPPER_Arms_BaseColor_2K.png',optimize=True)
    orm.save(out/'HOPPER_Arms_ORM_2K.png',optimize=True)
    normal.save(out/'HOPPER_Arms_Normal_2K.png',optimize=True)
    layout.resize((2048,2048),Image.Resampling.LANCZOS).save(out/'HOPPER_Arms_UV_Islands_2K.png')
    (out/'HOPPER_Arms_UV_Islands.json').write_text(json.dumps(records,indent=2),encoding='utf8')
    # Check all outer rectangles, including gutters, not just sampled vertices.
    for i,a in enumerate(records):
        x,y,w,h=a['outer_rect']
        assert 0<=x and 0<=y and x+w<=SIZE and y+h<=SIZE
        for b in records[i+1:]:
            xx,yy,ww,hh=b['outer_rect']
            assert x+w<=xx or xx+ww<=x or y+h<=yy or yy+hh<=y,'Overlapping UV rectangles'
    total=sum(x['uv_pixel_area'] for x in stats.values())
    for st in stats.values():
        st['linear_px_per_m']=math.sqrt(st['uv_pixel_area']/st['surface_area_m2']);st['used_uv_share']=st['uv_pixel_area']/total
    ratio=stats['armor']['linear_px_per_m']/stats['frame']['linear_px_per_m']
    return dict(resolution=SIZE,padding_px=PAD,non_overlapping=True,unique_islands=len(records),target_armor_px_per_m=density,
                armor_to_frame_linear_density_ratio=ratio,groups=dict(stats),used_uv_coverage=total/SIZE**2)
