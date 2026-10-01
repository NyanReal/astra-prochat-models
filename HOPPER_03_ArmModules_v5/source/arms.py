"""Detachable industrial arms with real shell thickness and canonical connector axes.
Authoring frame +X outward, +Y up, +Z front. Bake L mirror and connector frame,
then joint-local vertices; exported root has identity TRS, with no negative scale.
"""
from math import pi,cos,sin
from collections import Counter
import numpy as np
from scipy.spatial.transform import Rotation
from geometry import Scene,quadgrid,lathe,align_y
CREAM=(219,213,194);LIGHT=(231,225,208);TEAL=(65,87,83)
DARK=(46,52,53);METAL=(112,123,121);STEEL=(174,186,184);GOLD=(202,147,52);RUBBER=(28,33,34)

def shell_parts(rows,segments=10,angle=112,thickness=.008):
    rows=np.asarray(rows,float);ts=np.linspace(-np.deg2rad(angle),np.deg2rad(angle),segments+1);p=[]
    for x,y,z,rx,rz in rows:
        xx=np.sign(np.sin(ts))*np.abs(np.sin(ts))**.82;zz=np.sign(np.cos(ts))*np.abs(np.cos(ts))**.85
        p.append(np.c_[x+rx*xx,np.full(len(ts),y),z+rz*zz])
    p=np.array(p);n=np.cross(np.gradient(p,axis=1),np.gradient(p,axis=0));n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12)
    if n[len(rows)//2,segments//2,2]<0:n=-n
    f=quadgrid(segments+1,len(rows));pp=p.reshape(-1,3);nn=n.reshape(-1,3)
    uv=np.array([(j/segments,1-i/(len(rows)-1)) for i in range(len(rows)) for j in range(segments+1)])
    inner=pp-nn*thickness;aspect=2*np.deg2rad(angle)*np.mean(rows[:,3])/np.ptp(rows[:,1])
    outer=[('surface',pp,nn,uv,f,aspect)];inside=[('inside',inner,-nn,uv.copy(),f[:,[0,2,1]],aspect)];rims=[]
    edges=[list(range(segments+1)),list(range((len(rows)-1)*(segments+1),len(pp))),[i*(segments+1) for i in range(len(rows))],[i*(segments+1)+segments for i in range(len(rows))]]
    for k,ids in enumerate(edges):
        pos=[];norm=[];uu=[];ff=[];ll=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pp[ids],axis=0),axis=1))]
        for j in range(len(ids)-1):
            a,b=ids[j:j+2];q=np.array([pp[a],pp[b],inner[b],inner[a]]);no=np.cross(q[1]-q[0],q[2]-q[0]);no/=max(np.linalg.norm(no),1e-12)
            off=len(pos);pos.extend(q);norm.extend([no]*4);uu.extend([(ll[j]/ll[-1],0),(ll[j+1]/ll[-1],0),(ll[j+1]/ll[-1],1),(ll[j]/ll[-1],1)]);ff.extend([(off,off+1,off+2),(off,off+2,off+3)])
        rims.append((f'return_{k}',np.array(pos),np.array(norm),np.array(uu),np.array(ff,np.uint32),ll[-1]/thickness))
    return outer,inside,rims

def build_arm(side,spec):
    sign=1 if side=='R' else -1;s=Scene();s.nodes[0]['name']=f'Arm_{side}_M1_Root';pivots={0:np.zeros(3)};parents={0:None}
    def nd(label,parent=0,point=(0,0,0)):
        i=s.add_node(f'Arm_{side}_{label}',parent=parent);pivots[i]=np.array(point,float);parents[i]=parent;return i
    mount=nd('01_Interface_Cup');H=np.array([.175,-.030,0]);E=np.array([.268,-.369,.032]);W=np.array([.297,-.665,.137])
    shoulder=nd('02_Shoulder_Pivot',point=H);upper=nd('03_Upper_Frame',shoulder,H);uparmor=nd('04_Shoulder_Armor',shoulder,H)
    elbow=nd('05_Elbow_Pivot',shoulder,E);fore=nd('06_Forearm_Frame',elbow,E);forearmor=nd('07_Forearm_Armor',elbow,E)
    wrist=nd('08_Wrist_Pivot',elbow,W);tool=nd('09_ToolPort',wrist,W+[0,-.018,0]);hand=nd('10_Hand_Frame',tool,W+[0,-.018,0]);handarmor=nd('11_Hand_Armor',tool,W+[0,-.018,0])
    def box(name,size,loc,node,rad=.009,col=DARK,cat='frame',mat='Metal',rot=(0,0,0),detail=''):
        s.box(f'{side}_{name}',size,rad,loc=loc,node=node,color=col,category=cat,material=mat,rot=rot,detail=detail)
    def cyl(name,r,l,loc,node,seg=10,col=METAL,cat='frame',mat='Metal',caps=2,rot=(0,0,-90),detail=''):
        s.cylinder(f'{side}_{name}',r,l,segments=seg,caps=caps,loc=loc,node=node,color=col,category=cat,material=mat,rot=rot,detail=detail)
    def prof(name,profile,loc,node,seg=12,col=METAL,cat='frame'):
        s.add(f'{side}_{name}',lathe(profile,seg),node=node,loc=loc,rot=(0,0,-90),category=cat,color=col,material='Metal')
    def beam(name,a,b,width,depth,node,col=DARK,rad=.004):
        a=np.array(a);b=np.array(b);rot=Rotation.from_quat(align_y(b-a)).as_euler('xyz',degrees=True)
        box(name,(width,np.linalg.norm(b-a),depth),(a+b)*.5,node,rad=rad,col=col,rot=rot)
    def shell(name,rows,node,detail,segments=14,angle=112,cap=False):
        o,i,r=shell_parts(rows,segments,angle)
        s.add(f'{side}_{name}',o,node=node,category='armor',color=CREAM,material='Paint',detail=detail)
        s.add(f'{side}_{name}_inner',i,node=node,category='frame',color=TEAL,material='Metal')
        s.add(f'{side}_{name}_rims',r,node=node,category='armor',color=LIGHT,material='Paint')
        if cap:
            top=o[0][1][-(segments+1):];bottom=i[0][1][-(segments+1):]
            for layer,pts,sgn in [('roof',top,1),('roof_inner',bottom,-1)]:
                center=pts.mean(0);center[1]+=.006*sgn
                pp=np.vstack([center,pts]);f=np.array([(0,j+1,(j+1)%len(pts)+1) for j in range(len(pts))],np.uint32)
                normal=np.tile([0,sgn,0],(len(pp),1));xz=pp[:,[0,2]];uv=(xz-xz.min(0))/np.maximum(np.ptp(xz,axis=0),1e-8)
                s.add(f'{side}_{name}_{layer}',[(layer,pp,normal,uv,f,1.4)],node=node,category='armor' if sgn==1 else 'frame',color=CREAM if sgn==1 else TEAL,material='Paint' if sgn==1 else 'Metal')
            pp=np.array([top[-1],top[0],bottom[0],bottom[-1]]);no=np.cross(pp[1]-pp[0],pp[2]-pp[0]);no/=np.linalg.norm(no)
            s.add(f'{side}_{name}_roof_rear_edge',[('edge',pp,np.tile(no,(4,1)),np.array([[0,0],[1,0],[1,1],[0,1]]),np.array([[0,1,2],[0,2,3]],np.uint32),12)],node=node,category='armor',color=LIGHT,material='Paint')
    # Register sleeve encloses the original lip/cap, not a solid intersecting disk.
    prof('M1_female_register',[(.161,-.046),(.178,-.046),(.188,-.030),(.188,.017),(.171,.036),(.066,.036),(.066,.014),(.161,.014),(.161,-.046)],(0,0,0),mount,seg=24,col=DARK)
    cyl('shoulder_output_journal',.064,.077,(.061,0,0),mount,seg=12,col=TEAL,caps=1)
    cyl('shoulder_index_disc',.094,.014,(.099,0,0),upper,seg=12,col=METAL,caps=1,detail={'cap_top':'socket_face'})
    bcd=spec['existing_interface_m']['bolt_circle_diameter']
    for k in range(6):
        a=2*pi*k/6;cyl(f'M1_fastener_{k:02}',.009,.012,(.042,bcd*.5*cos(a),bcd*.5*sin(a)),mount,seg=6,caps=1)
    box('M1_top_index',(.052,.020,.040),(-.014,.185,0),mount,rad=0,col=GOLD,cat='accent',mat='Paint')
    box('M1_service_key',(.048,.044,.065),(.005,-.151,-.116),mount,rad=0,col=TEAL,detail={'+Z':'port'})
    # Continuous upper channel with two load webs and rear crossmember.
    beam('upper_main_spar',[.12,.025,-.008],E+[0,.062,0],.105,.084,upper,rad=.010)
    beam('upper_front_web',[.14,-.07,.059],E+[0,.07,.045],.044,.025,upper,col=METAL,rad=0)
    beam('upper_rear_web',[.14,-.07,-.072],E+[0,.07,-.043],.044,.025,upper,col=METAL,rad=0)
    box('upper_rear_bridge',(.152,.065,.045),(.225,-.22,-.094),upper,rad=.008,col=TEAL)
    shell('shoulder_cowling',[(.241,-.277,.012,.120,.104),(.226,-.223,.004,.147,.134),(.204,-.040,0,.160,.162),(.194,.128,0,.149,.141),(.194,.180,0,.105,.094)],uparmor,'shoulder'+side,cap=True)
    box('shoulder_lower_trim',(.176,.042,.030),(.24,-.255,.125),uparmor,rad=.009,col=TEAL,cat='armor',mat='Paint')
    # Forked clevis, through-pin and machined bearing.
    for xoff in [-.074,.074]:beam('elbow_fork_'+str(xoff),E+[xoff,.087,-.005],E+[xoff,-.023,-.002],.027,.089,upper,rad=0)
    cyl('elbow_through_pin',.031,.207,E,elbow,seg=10,caps=0)
    cyl('elbow_drum',.071,.119,E,elbow,seg=12,col=DARK,caps=0)
    prof('elbow_outer_race',[(.033,-.016),(.063,-.016),(.074,0),(.065,.020),(.033,.020)],E+[.093,0,0],elbow,seg=12)
    cyl('elbow_axis_cap',.027,.025,E+[.126,0,0],elbow,seg=10,col=GOLD,caps=1)
    # Forearm structure and rear-mounted damper.
    beam('forearm_backbone',E+[0,-.035,.009],W+[0,.015,-.006],.093,.070,fore,rad=.009)
    box('forearm_rear_bracket',(.157,.058,.038),(.286,-.519,-.020),fore,rad=0,col=METAL)
    A=np.array([.308,-.430,-.041]);B=np.array([.327,-.612,.070]);delta=B-A;L=np.linalg.norm(delta);v=delta/L;q=Rotation.from_quat(align_y(delta)).as_euler('xyz',degrees=True);length=.118
    cyl('damper_barrel',.025,length,A+v*length*.5,fore,seg=10,col=GOLD,caps=0,rot=q)
    cyl('damper_gland',.030,.023,A+v*length,fore,seg=10,caps=0,rot=q)
    cyl('damper_rod',.011,L-length+.012,A+v*(length+(L-length)*.5),fore,seg=8,col=STEEL,caps=0,rot=q)
    for k,p in enumerate([A,B]):
        cyl('damper_eye_'+str(k),.022,.048,p,fore,seg=8,col=DARK,caps=1)
        cyl('damper_pin_'+str(k),.010,.065,p,fore,seg=6,caps=0)
    s.tube(f'{side}_forearm_service_hose',[(.237,-.427,-.038),(.209,-.469,-.066),(.214,-.576,-.012),(.250,-.617,.058)],.008,sides=6,smooth=1,node=fore,color=RUBBER,material='Rubber',category='frame')
    shell('forearm_gauntlet',[(.296,-.638,.126,.094,.082),(.286,-.595,.112,.136,.135),(.271,-.490,.066,.151,.130),(.263,-.447,.048,.119,.100)],forearmor,'forearm'+side,angle=117)
    box('forearm_ochre_service',(.023,.092,.059),(.421,-.551,.055),forearmor,rad=.005,col=GOLD,cat='accent',mat='Paint',detail={'+X':'latch'})
    # Wrist, independent hand/tool attachment boundary, blunt four fingers plus thumb.
    q=Rotation.from_quat(align_y(W-(E+[0,-.035,.009]))).as_euler('xyz',degrees=True)
    cyl('wrist_core_shaft',.028,.123,W,wrist,seg=8,col=STEEL,rot=q,caps=0)
    cyl('wrist_housing',.061,.065,W,wrist,seg=12,col=DARK,rot=q,caps=0)
    cyl('wrist_seal',.052,.018,W+[0,-.030,.010],wrist,seg=12,rot=q,caps=0)
    box('palm_carrier',(.161,.124,.102),(.297,-.737,.145),hand,rad=.015,col=DARK)
    box('backhand_plate',(.147,.089,.025),(.297,-.734,.208),handarmor,rad=.011,col=TEAL,cat='armor',mat='Paint',detail={'+Z':'hand'})
    for j,x in enumerate(np.linspace(.236,.358,4)):
        cyl(f'finger_{j}_knuckle',.021,.027,(x,-.793,.149),hand,seg=6,caps=0)
        box(f'finger_{j}_proximal',(.032,.060,.047),(x,-.812,.162),hand,rad=.006,col=DARK,rot=(-9,0,0))
        box(f'finger_{j}_distal',(.031,.041,.040),(x,-.858,.178),hand,rad=.006,col=RUBBER,mat='Rubber',rot=(-28,0,0))
    box('thumb_proximal',(.046,.076,.048),(.190,-.773,.165),hand,rad=.008,col=DARK,rot=(0,0,-28))
    box('thumb_distal',(.042,.052,.043),(.214,-.816,.187),hand,rad=.008,col=RUBBER,mat='Rubber',rot=(-17,0,28))
    # Joint-local vertices and right-handed connector basis.
    mount_rot=Rotation.from_euler('y',sign*90,degrees=True).as_matrix();convert=mount_rot.T@np.diag([sign,1,1])
    for p in s.patches:
        p.positions=(p.positions-pivots[p.node])@convert.T;p.normals=p.normals@convert.T
        if np.linalg.det(convert)<0:
            p.faces=p.faces[:,[0,2,1]];p.uv[:,0]=1-p.uv[:,0]
    for i,n in enumerate(s.nodes):
        parent=parents[i];n['translation']=(convert@(pivots[i]-(pivots[parent] if parent is not None else 0))).tolist()
        n['scale']=[1,1,1];n['rotation']=[0,0,0,1];n['extras']={'module':side,'rigid_reference_pose':True}
    s.nodes[0]['extras']={'module':side,'interface':'H03-M1','units':'meters','outward_axis':'+Z','index_up_axis':'+Y','scope':'Independent arm only; no base meshes.','scene_mount':spec['sockets'][side]['scene_mount']}
    s.nodes[tool]['extras'].update({'role':'Future hand/tool attachment datum','not_an_industrial_standard':True})
    counts=Counter()
    for p in s.patches:counts[s.nodes[p.node]['name']]+=len(p.faces)
    return s,{'side':side,'triangles':sum(counts.values()),'by_assembly':dict(counts),'damper_reference_length_m':float(L),'joint_motion':'Reference pose only; no arm animation or mechanism solver.'}
