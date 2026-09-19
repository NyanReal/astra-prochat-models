"""Blender 4.5+: blender -b --python scripts/build_atv.py
Creates a dedicated scene; does not clear the user's existing scenes.
All outputs stay in this script's parent atv directory. Front = -Y, up = Z, metres.
"""
import bpy, bmesh, math, json, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True)
scene = bpy.data.scenes.new('ATV_Production')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
groups = [[] for _ in range(8)]
names = ['Teal_Panels','Ivory_Body','Rubber_Tires','Graphite_Seat', 'Steel_Racks','Amber_Accents','Headlamps','Chassis']
roughness = [.62,.57,.91,.84,.72,.47,.28,.84]

def register(o, name, group, smooth=False):
    o.name = name
    groups[group].append(o)
    for p in o.data.polygons: p.use_smooth = smooth
    return o

def apply(o, mod):
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_apply(modifier=mod.name)

def box(name, loc, size, group, bevel=.025, segments=1, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object
    o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=o.modifiers.new('Soft silhouette','BEVEL'); m.width=bevel; m.segments=min(segments,2) if name in ['Cream body tub','Fuel tank','Saddle','Raised front hood','Saddle raised rear'] else 1
        apply(o,m)
    if rot: o.rotation_euler=rot
    register(o,name,group,True)
    m=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL'); m.keep_sharp=True; m.weight=40
    apply(o,m)
    return o

def mesh(name, verts, faces, group, smooth=False):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); scene.collection.objects.link(o)
    return register(o,name,group,smooth)

def rod(name,a,b,r,group,vertices=10):
    a,b=Vector(a),Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=(b-a).length,location=(a+b)*.5)
    o=bpy.context.object; o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return register(o,name,group,True)

def tube_path(name, points, radius, group):
    # Straight cylindrical segments are deliberate low-poly silhouette blocks.
    for i in range(len(points)-1): rod(name+str(i),points[i],points[i+1],radius,group,8)

# Cream central silhouette, saddle and lowered foot wells.
box('Lower chassis',(0,0,.44),(.65,1.50,.24),7,.09,2)
box('Cream body tub',(0,.04,.68),(.85,1.53,.45),1,.14,3)
box('Raised front hood',(0,-.61,.88),(1.10,.62,.30),1,.12,3)
box('Rear cream deck',(0,.70,.87),(1.14,.43,.25),1,.09,2)
box('Fuel tank',(0,-.17,1.00),(.56,.62,.42),1,.14,3)
box('Tank teal insert',(0,-.26,1.205),(.35,.29,.045),0,.025,2)
box('Saddle',(0,.30,1.00),(.56,.79,.21),3,.09,3,(-.08,0,0))
box('Saddle raised rear',(0,.61,1.025),(.57,.28,.20),3,.085,3)
for s in [-1,1]:
    box('Foot well', (s*.50,.05,.42),(.26,.65,.105),4,.03,1)
    box('Heel guard', (s*.49,.34,.56),(.19,.10,.34),7,.03,1,(-.15,0,0))
    for j in range(3): box('Foot grip',(s*.51,-.12+j*.13,.48),(.22,.028,.025),7,.007)

# Four arch-shaped fenders: broad continuous teal upper shells.
for s in [-1,1]:
    for cy in [-.65,.65]:
        verts=[]; faces=[]; n=9
        # Cross-section across the fender with rolled outer edge.
        section=[(.34,.515),(.53,.56),(.80,.53),(.86,.47),(.80,.43),(.53,.47),(.34,.435)]
        for i in range(n):
            t=math.radians(13+154*i/(n-1))
            for x,r in section: verts.append((s*x,cy+math.cos(t)*r,.40+math.sin(t)*r))
        k=len(section)
        for i in range(n-1):
            for j in range(k):
                faces.append((i*k+j,i*k+(j+1)%k,(i+1)*k+(j+1)%k,(i+1)*k+j))
        faces.extend([tuple(reversed(range(k))),tuple((n-1)*k+j for j in range(k))])
        o=mesh('Swept teal fender',verts,faces,0,True)
        # Recalculate normals independently of mirrored side.
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')

# Low-poly balloon tires and chunky silhouette tread. No array/instanced UV reuse.
for s in [-1,1]:
    for cy in [-.65,.65]:
        cx=s*.66; cz=.415; n=20
        profile=[(-.19,.175),(-.195,.28),(-.16,.355),(-.105,.397),(.105,.397),(.16,.355),(.195,.28),(.19,.175)]
        verts=[]; faces=[]
        for x,r in profile:
            for i in range(n):
                t=2*math.pi*i/n
                verts.append((cx+x,cy+math.cos(t)*r,cz+math.sin(t)*r))
        for j in range(len(profile)):
            for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i))
        tire=mesh('Balloon tire',verts,faces,2,True)
        for row in [-1,1]:
            for i in range(12):
                t=2*math.pi*(i+(0.26 if row==1 else 0))/12
                # Cuboid tread aligned to radius with a beveled silhouette.
                o=box('Broad tread lug',(cx+row*.105,cy+math.cos(t)*.401,cz+math.sin(t)*.401),(.175,.12,.06),2,0,1)
                o.rotation_euler=(t-math.pi/2,0,row*.22)
        outside=cx+s*.197
        rod('Ivory wheel rim',(outside-s*.027,cy,cz),(outside+s*.008,cy,cz),.205,1,20)
        rod('Dark inset hub',(outside+s*.010,cy,cz),(outside+s*.018,cy,cz),.137,4,16)
        rod('Ivory hub face',(outside+s*.020,cy,cz),(outside+s*.026,cy,cz),.105,1,16)
        rod('Amber hub cap',(outside+s*.028,cy,cz),(outside+s*.048,cy,cz),.064,5,12)
        rod('Axle',(0,cy,cz),(cx,cy,cz),.055,7,10)
        # Simplified orange shock stacks, readable from a top-down camera.
        a=Vector((s*.33,cy,.38)); b=Vector((s*.43,cy-.06,.75))
        rod('Shock core',a,b,.042,4,8)
        for i in range(4):
            p=a.lerp(b,.16+i*.20); q=a.lerp(b,.25+i*.20)
            rod('Orange shock collar',p,q,.066,5,10)
        rod('Suspension arm',(s*.18,cy,.31),(s*.54,cy,.41),.039,4,8)

# Face, round lamps, inset grille and protective bumper.
box('Front mask',(0,-.925,.78),(.82,.16,.34),1,.065,2)
box('Recessed grille',(0,-1.023,.715),(.29,.055,.22),7,.045,2)
for z in [.68,.73,.78]: box('Grille rib',(0,-1.055,z),(.21,.025,.025),4,.008)
for s in [-1,1]:
    rod('Lamp bezel',(s*.31,-1.02,.84),(s*.31,-1.069,.84),.132,4,20)
    rod('Ivory lamp rim',(s*.31,-1.07,.84),(s*.31,-1.084,.84),.108,1,20)
    rod('Warm headlamp',(s*.31,-1.085,.84),(s*.31,-1.099,.84),.083,6,20)
    box('Front amber indicator',(s*.67,-1.03,.795),(.10,.055,.125),5,.023,2)
    box('Rear amber lamp',(s*.58,1.00,.81),(.21,.06,.12),5,.028,2)
    tube_path('Front bumper upright',[(s*.38,-1.06,.34),(s*.43,-1.12,.57),(s*.32,-1.14,.62)],.047,4)
tube_path('Front bumper bar',[(-.32,-1.14,.62),(.32,-1.14,.62)],.047,4)
box('Front skid plate',(0,-1.07,.40),(.38,.09,.23),4,.05,2)
box('Rear dark fascia',(0,.98,.73),(.40,.095,.25),7,.045,2)
box('Rear tow block',(0,1.045,.48),(.22,.12,.18),4,.04,2)
rod('Tow socket',(0,1.11,.48),(0,1.13,.48),.049,7,12)

# Front and rear racks: open interior rather than a heavy filled rectangle.
for cy,width,depth,z in [(-.68,1.13,.38,1.085),(.72,1.06,.31,1.10)]:
    for s in [-1,1]:
        for y in [cy-depth*.36,cy+depth*.36]:
            box('Rack foot',(s*width*.36,y,z-.075),(.065,.075,.13),4,.012)
    pts=[(-width/2,cy-depth/2,z),(width/2,cy-depth/2,z),(width/2,cy+depth/2,z),(-width/2,cy+depth/2,z),(-width/2,cy-depth/2,z)]
    for i in range(4):
        a,b=Vector(pts[i]),Vector(pts[i+1]); middle=(a+b)/2
        size=(abs(b.x-a.x)+.045,abs(b.y-a.y)+.045,.065)
        box('Rack perimeter',middle,size,4,.02,2)
    for x in [-.24,0,.24]: box('Rack cross support',(x,cy,z-.015),(.042,depth,.045),4,.01)

# Swept handlebar, grips and instrument pod.
rod('Steering column',(0,-.33,1.04),(0,-.36,1.30),.045,7)
tube_path('Handlebar',[(-.57,-.31,1.39),(-.27,-.34,1.39),(-.16,-.38,1.28),(.16,-.38,1.28),(.27,-.34,1.39),(.57,-.31,1.39)],.034,4)
for s in [-1,1]:
    rod('Rubber hand grip',(s*.34,-.328,1.391),(s*.56,-.31,1.39),.047,2,12)
    rod('Orange grip cap',(s*.56,-.31,1.39),(s*.593,-.307,1.39),.049,5,12)
    box('Control housing',(s*.30,-.334,1.388),(.095,.105,.10),7,.028,2)
box('Instrument ivory shell',(0,-.414,1.325),(.285,.12,.175),1,.034,2,(-.20,0,0))
box('Instrument dark display',(0,-.480,1.33),(.215,.016,.10),7,.016,2,(-.20,0,0))

# Join by surface family, unwrap independently, then place in disjoint atlas regions.
image=bpy.data.images.load(str(ASSETS/'atv_generated_source.png'),check_existing=True)
image.colorspace_settings.name='sRGB'
all_parts=[]
for g,objects in enumerate(groups):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects: o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]; bpy.ops.object.join()
    o=bpy.context.object; o.name=names[g]
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    # Each final triangle gets its own non-overlapping island. Metric projection
    # and area-aware shelf packing preserve relative texel density within a region.
    tri=o.modifiers.new('UV triangulation','TRIANGULATE'); apply(o,tri)
    bm=bmesh.new(); bm.from_mesh(o.data)
    flat=[f for f in bm.faces if f.calc_area()<1e-8]
    if flat: bmesh.ops.delete(bm,geom=flat,context='FACES_ONLY')
    bm.to_mesh(o.data); bm.free(); o.data.update()
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.018,area_weight=.15,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    source_layer=o.data.uv_layers.active; source_layer.name='Source_Bake_Only'
    col=g%4; row=g//4
    for loop in source_layer.data:
        u,v=loop.uv; loop.uv=(col*.25+.0225+u*.205,(1-row)*.5+.045+v*.41)
    layer=o.data.uv_layers.new(name='UV0_Unique_Atlas')
    o.data.uv_layers.active=layer; layer.active_render=True
    projected=[]
    for p in o.data.polygons:
        loops=list(p.loop_indices)
        xyz=[o.data.vertices[o.data.loops[li].vertex_index].co for li in loops]
        longest=max(range(3),key=lambda i:(xyz[(i+1)%3]-xyz[i]).length)
        order=[longest,(longest+1)%3,(longest+2)%3]
        a,b,c=[xyz[i] for i in order]; edge=b-a; width=edge.length
        axis=edge.normalized(); x=(c-a).dot(axis); height=(c-a-axis*x).length
        assert width>1e-8 and height>1e-8, f'Degenerate geometric triangle: {g} {p.index} {width} {height} {list(map(tuple,xyz))}'
        projected.append((p.index,[loops[i] for i in order],width,height,x))
    padding=3/2048/.225
    minimum=3/2048/.225
    def packing(scale):
        rects=sorted(projected,key=lambda t:t[3],reverse=True)
        x=y=row_height=0.; placed={}
        for index,loops,w,h,tip in rects:
            rw=max(w*scale,minimum)+padding*2; rh=max(h*scale,minimum)+padding*2
            if rw>1: return None
            if x+rw>1: y+=row_height; x=0.; row_height=0.
            if y+rh>2: return None
            placed[index]=(x+padding,y+padding)
            x+=rw; row_height=max(row_height,rh)
        return placed
    low=0.; high=100.
    for _ in range(45):
        mid=(low+high)/2
        if packing(mid) is not None: low=mid
        else: high=mid
    placed=packing(low)
    assert placed is not None
    col=g%4; row=g//4
    for index,loops,w,h,tip in projected:
        x,y=placed[index]
        uw=max(w*low,minimum); vh=max(h*low,minimum)
        coords=[(x,y),(x+uw,y),(x+tip/w*uw,y+vh)]
        for li,(u,v) in zip(loops,coords):
            layer.data[li].uv=(col*.25+.0125+u*.225,(1-row)*.5+.025+v*.225)
    mat=bpy.data.materials.new('M_ATV_'+names[g]); mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=image; tex.extension='EXTEND'
    uv_node=mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_node.uv_map='Source_Bake_Only'
    mat.node_tree.links.new(uv_node.outputs['UV'],tex.inputs['Vector'])
    mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value=roughness[g]
    if g==6:
        mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Emission Color']); bsdf.inputs['Emission Strength'].default_value=.28
    o.data.materials.clear(); o.data.materials.append(mat)
    for p in o.data.polygons: p.material_index=0
    all_parts.append(o)

# One portable mesh; retained material slots supply per-surface roughness.
bpy.ops.object.select_all(action='DESELECT')
for o in all_parts: o.select_set(True)
bpy.context.view_layer.objects.active=all_parts[0]; bpy.ops.object.join()
atv=bpy.context.object; atv.name='SM_ATV_Trail'
scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
# Bake the coherent source mapping into unique, non-overlapping final UV0.
# This is a UV transfer of the generated painting, not a procedural pattern.
source_image=image
image=bpy.data.images.new('ATV_BaseColor_Unique',width=2048,height=2048,alpha=False)
image.colorspace_settings.name='sRGB'
restores=[]
for mat in atv.data.materials:
    tree=mat.node_tree; bsdf=tree.nodes.get('Principled BSDF'); output=tree.nodes.get('Material Output')
    source=next(n for n in tree.nodes if n.type=='TEX_IMAGE')
    emission=tree.nodes.new('ShaderNodeEmission'); tree.links.new(source.outputs['Color'],emission.inputs['Color'])
    tree.links.new(emission.outputs[0],output.inputs['Surface'])
    target=tree.nodes.new('ShaderNodeTexImage'); target.image=image; target.select=True; tree.nodes.active=target
    restores.append((tree,bsdf,output,source,emission,target))
atv.data.uv_layers.active=atv.data.uv_layers['UV0_Unique_Atlas']; atv.data.uv_layers.active.active_render=True
scene.render.engine='CYCLES'; scene.cycles.samples=1
scene.render.bake.margin=3; scene.render.bake.use_clear=True
bpy.ops.object.bake(type='EMIT')
image.filepath_raw=str(ASSETS/'atv_basecolor.png'); image.file_format='PNG'; image.save()
for tree,bsdf,output,source,emission,target in restores:
    tree.nodes.remove(emission); tree.nodes.remove(target)
    for link in list(source.inputs['Vector'].links): tree.links.remove(link)
    source.image=image
    tree.links.new(bsdf.outputs[0],output.inputs['Surface'])
    for node in list(tree.nodes):
        if node.type=='UVMAP': tree.nodes.remove(node)
atv.data.uv_layers.remove(atv.data.uv_layers['Source_Bake_Only'])
tri=atv.modifiers.new('Final triangulation','TRIANGULATE'); apply(atv,tri)
atv.data.calc_loop_triangles()
triangles=len(atv.data.loop_triangles)
assert triangles<10000, f'Triangle budget exceeded: {triangles}'
uv=atv.data.uv_layers.active.data
uv_triangles=[[[float(v) for v in uv[li].uv] for li in p.loop_indices] for p in atv.data.polygons]
(ASSETS/'uv_triangles.json').write_text(json.dumps(uv_triangles,separators=(',',':')))
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2048 2048"><rect width="2048" height="2048" fill="#101d23"/><g fill="none" stroke="#90e1ce" stroke-width="0.65">']
for t in uv_triangles: svg.append('<polygon points="'+' '.join(f'{u*2048:.2f},{(1-v)*2048:.2f}' for u,v in t)+'"/>')
svg.append('</g></svg>'); (ASSETS/'atv_uv.svg').write_text(''.join(svg))
stats={'triangles':triangles,'vertices':len(atv.data.vertices),'materialSlots':8,'textureWidth':image.size[0],'textureHeight':image.size[1],'generatedSourceSize':list(source_image.size),'textureProcess':'ImageGen source transferred by emission bake to unique UV atlas','dimensionsMetres':[round(v,3) for v in atv.dimensions], 'frontAxis':'-Y (Blender)','upAxis':'+Z (Blender)','uvPolicy':'Unique, non-overlapping UV0; no stacking, no mirroring, no tiling','blenderVersion':bpy.app.version_string}
(ASSETS/'model-stats.json').write_text(json.dumps(stats,indent=2))
bpy.ops.export_scene.gltf(filepath=str(ASSETS/'atv.glb'),export_format='GLB',use_selection=True,use_active_scene=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_yup=True)
bpy.ops.export_scene.fbx(filepath=str(ASSETS/'atv.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE')

# Soft studio preview. Ground/cameras/lights are excluded from both model exports.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025))
ground=bpy.context.object; ground.name='Preview_Ground'
mat=bpy.data.materials.new('Preview_Ground'); mat.diffuse_color=(.105,.14,.145,1); mat.use_nodes=True
mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.105,.14,.145,1)
mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.9
ground.data.materials.append(mat)
scene.world=bpy.data.worlds.new('ATV_Studio'); scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.28,.32,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,pos,power,size in [('Key',(-3,-4,6),500,4),('Fill',(4,-1,3),300,3),('Rim',(1,4,5),650,3)]:
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size
    ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob); ob.location=pos; ob.rotation_euler=(Vector((0,0,.6))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Preview_Camera'); camera=bpy.data.objects.new('Preview_Camera',data); scene.collection.objects.link(camera); scene.camera=camera
data.type='ORTHO'; data.ortho_scale=3.25
scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.use_denoising=True
scene.render.resolution_x=1200; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
for name,position in [('preview-front',(3,-4,2.9)),('preview-rear',(-3,4,2.7)),('preview-top',(2.4,-3.2,6.5))]:
    camera.location=position; camera.rotation_euler=(Vector((0,0,.65))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ASSETS/(name+'.png')); bpy.ops.render.render(write_still=True)
camera.location=(3,-4,2.9); camera.rotation_euler=(Vector((0,0,.65))-camera.location).to_track_quat('-Z','Y').to_euler()
image.pack()
bpy.ops.object.select_all(action='DESELECT'); atv.select_set(True); bpy.context.view_layer.objects.active=atv
bpy.ops.wm.save_as_mainfile(filepath=str(ASSETS/'atv.blend'))
print('ATV_BUILD_COMPLETE',json.dumps(stats))
