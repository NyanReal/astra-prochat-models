"""Build the ATV from parametric geometry, not by importing the delivered GLB.
Target: Blender 4.2+ (4.5 LTS preferred). No third-party add-ons required.

GUI: Scripting > Open this file from disk > Run Script.
CLI: blender --background --python build_atv.py -- --out "D:/ATV_Build"
     Add --split-parts for independent body/wheels, or --render for 3 previews.

Only the named ATV_Generated / ATV_Preview collections are replaced on re-run.
Other scene objects and the supplied source GLB/textures are not overwritten.
The geometric kernel and UV data were tested outside Blender. This bpy adapter
was syntax-checked but NOT executed in Blender in the delivery environment.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SCRIPT_ROOT=Path(__file__).resolve().parents[1]


def arguments():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=SCRIPT_ROOT)
    parser.add_argument('--out',type=Path,default=None)
    parser.add_argument('--split-parts',action='store_true')
    parser.add_argument('--render',action='store_true')
    return parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def replace_collection(name):
    old=bpy.data.collections.get(name)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(old)
    collection=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def saved_uv_layout(model,root):
    # Keeping the delivered rectangle placement allows dimension edits to stretch
    # the existing paint rather than silently repacking every other island.
    records=json.loads((root/'Source/UV_Charts.json').read_text(encoding='utf-8'))
    layout={c['name']:c['rectangle'] for c in records}
    local=np.asarray(model.uv_local,dtype=np.float64)
    faces=np.asarray(model.faces,dtype=np.int32)
    uv=np.zeros((len(local),2),dtype=np.float32)
    for chart in model.charts:
        if chart.name not in layout:
            raise RuntimeError('New chart needs a repaint/repack: '+chart.name)
        x,y,w,h,rot=layout[chart.name]
        ids=np.unique(faces[chart.triangles].ravel())
        q=local[ids].copy()
        if rot:
            q=np.column_stack((q[:,1],1-q[:,0]))
        q=q*np.array([w-10,h-10])+[x+5,y+5]
        uv[ids,0]=q[:,0]/2048.0
        uv[ids,1]=1-q[:,1]/2048.0
    return uv


def make_material(root):
    name='M_ATV_UniqueAtlas'
    material=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes=True
    nodes=material.node_tree.nodes
    links=material.node_tree.links
    nodes.clear()
    out=nodes.new('ShaderNodeOutputMaterial');out.location=(720,100)
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');bsdf.location=(390,100)
    links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map='UV0_Unique';uvnode.location=(-920,120)
    def image_node(filename,position,noncolor=False):
        file=root/'Textures'/filename
        if not file.is_file():raise FileNotFoundError(file)
        image=bpy.data.images.load(str(file),check_existing=True)
        image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
        image.pack()
        node=nodes.new('ShaderNodeTexImage');node.image=image;node.location=position
        node.extension='EXTEND';node.interpolation='Linear'
        links.new(uvnode.outputs['UV'],node.inputs['Vector'])
        return node
    base=image_node('T_ATV_BaseColor.png',(-650,370))
    orm=image_node('T_ATV_ORM.png',(-650,40),True)
    em=image_node('T_ATV_Emissive.png',(-650,-290))
    links.new(base.outputs['Color'],bsdf.inputs['Base Color'])
    separate=nodes.new('ShaderNodeSeparateColor');separate.mode='RGB';separate.location=(-300,20)
    links.new(orm.outputs['Color'],separate.inputs['Color'])
    links.new(separate.outputs['Green'],bsdf.inputs['Roughness'])
    links.new(separate.outputs['Blue'],bsdf.inputs['Metallic'])
    emission_input=bsdf.inputs.get('Emission Color') or bsdf.inputs.get('Emission')
    if emission_input is None:raise RuntimeError('Principled BSDF emission socket unavailable')
    links.new(em.outputs['Color'],emission_input)
    if bsdf.inputs.get('Emission Strength'):bsdf.inputs['Emission Strength'].default_value=.55
    # Blender's glTF exporter recognizes this group/input as occlusionTexture.
    group_name='glTF Material Output'
    group=bpy.data.node_groups.get(group_name)
    if group is None:
        group=bpy.data.node_groups.new(group_name,'ShaderNodeTree')
        group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
    group_node=nodes.new('ShaderNodeGroup');group_node.node_tree=group;group_node.location=(60,-180)
    occlusion=group_node.inputs.get('Occlusion')
    if occlusion is not None:links.new(separate.outputs['Red'],occlusion)
    material.diffuse_color=(.40,.52,.53,1)
    return material


def add_mesh(name,vertices,faces,normals,uv,collection,material,pivot=(0,0,0)):
    # One UV coordinate per exported vertex; seam vertices are deliberately split.
    mesh=bpy.data.meshes.new(name+'_Mesh')
    verts=np.asarray(vertices)-np.asarray(pivot)
    mesh.from_pydata(verts.tolist(),[],np.asarray(faces).tolist())
    mesh.update()
    layer=mesh.uv_layers.new(name='UV0_Unique')
    loops=np.array([loop.vertex_index for loop in mesh.loops],dtype=np.int32)
    layer.data.foreach_set('uv',np.asarray(uv)[loops].astype(np.float32).ravel())
    for polygon in mesh.polygons:polygon.use_smooth=True
    mesh.normals_split_custom_set_from_vertices(np.asarray(normals).tolist())
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    obj.location=pivot;obj.data.materials.append(material)
    obj['UniqueUV']=True;obj['Units']='metres';obj['AuthoredFront']='+X'
    return obj


def make_studio():
    collection=replace_collection('ATV_Preview')
    scene=bpy.context.scene
    def area(name,location,energy,size,target=(0,0,.8)):
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.location=location
        obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    area('ATV_Key',(3,-4,6),850,5)
    area('ATV_Fill',(-3,4,4),550,4)
    area('ATV_Rim',(-3,-2,5),650,3)
    camera_data=bpy.data.cameras.new('ATV_Camera');camera_data.type='ORTHO';camera_data.ortho_scale=3.5
    camera=bpy.data.objects.new('ATV_Camera',camera_data);collection.objects.link(camera);scene.camera=camera
    # A floor is a helper only, never selected for export.
    mesh=bpy.data.meshes.new('ATV_Floor_Mesh');mesh.from_pydata([(-100,-100,-.018),(100,-100,-.018),(100,100,-.018),(-100,100,-.018)],[],[(0,1,2,3)])
    floor=bpy.data.objects.new('ATV_Floor',mesh);collection.objects.link(floor)
    mat=bpy.data.materials.get('M_ATV_PreviewFloor') or bpy.data.materials.new('M_ATV_PreviewFloor')
    mat.use_nodes=True;mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.83,.83,.80,1)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.9;floor.data.materials.append(mat)
    if scene.world is None:scene.world=bpy.data.worlds.new('ATV_World')
    scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.7,.74,.77,1)
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.4
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.render.resolution_x=1200;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    return camera


def main():
    args=arguments();root=args.root.resolve();out=(args.out or root/'Build_Blender').resolve();out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(root/'Source'))
    from atv_geometry import build_model
    model=build_model();vertices,faces,normals=model.arrays();uv=saved_uv_layout(model,root)
    if len(faces)>=10000:raise RuntimeError(f'Triangle budget exceeded: {len(faces)}')
    if not np.isfinite(vertices).all() or not np.isfinite(uv).all():raise RuntimeError('Nonfinite mesh data')
    collection=replace_collection('ATV_Generated');material=make_material(root)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
    objects=[]
    if args.split_parts:
        groups={'Body':[],'Wheel_FL':[],'Wheel_FR':[],'Wheel_RL':[],'Wheel_RR':[]}
        for i,part in enumerate(model.face_part):
            key=next((key for key in groups if key!='Body' and part.startswith(key+'_')),'Body')
            groups[key].append(i)
        wheel_z=.465+model.ground_shift
        wheel_centres={'Wheel_FL':(.70,.69,wheel_z),'Wheel_FR':(.70,-.69,wheel_z),'Wheel_RL':(-.72,.69,wheel_z),'Wheel_RR':(-.72,-.69,wheel_z)}
        for name,tri_ids in groups.items():
            fs=faces[tri_ids];used,inverse=np.unique(fs.ravel(),return_inverse=True)
            objects.append(add_mesh('ATV_'+name,vertices[used],inverse.reshape(-1,3),normals[used],uv[used],collection,material,wheel_centres.get(name,(0,0,0))))
    else:
        objects.append(add_mesh('SM_ATV_Stylized',vertices,faces,normals,uv,collection,material))
    # Select only asset objects. Other user-scene objects are never exported.
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    glb=out/('ATV_SplitParts.glb' if args.split_parts else 'SM_ATV_Stylized.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,export_normals=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_extras=True)
    if args.render:
        camera=make_studio()
        for name,location in [('Front_3Q',(3.7,4.8,3.05)),('Rear_3Q',(-3.7,-4.8,3.05)),('Top_Down',(2.5,3.4,7.))]:
            camera.location=location;camera.rotation_euler=(Vector((0,0,.78))-camera.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'ATV_Stylized.blend'),check_existing=False)
    report={'triangles':len(faces),'vertices_with_uv_seams':len(vertices),'uv_charts':len(model.charts),'objects':len(objects),'glb':str(glb),'blender_version':bpy.app.version_string,'execution':'completed in this Blender session'}
    (out/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
