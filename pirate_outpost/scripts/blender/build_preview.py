"""Pirate Outpost — build a NEW Blender preview scene with linked mesh instances.

Target: Blender 4.2+ (bpy). No third-party Python packages are required in Blender.
Editor runtime not tested in the asset-generation environment; see README_KO.md.

Text Editor: open this file and Run Script. Set PACK_ROOT below only if necessary.
CLI:
  blender --background --python build_preview.py -- --pack "D:/PirateOutpost" \
      --layout harbor --save "D:/Pirate_preview.blend" --render "D:/preview.png"

Existing scenes/objects are never cleared. Saving requires an explicit path.
A .blend save contains the whole current Blender file, including existing scenes;
use a fresh Blender file when you only want the generated preview.
"""
from pathlib import Path
import argparse
import json
import math
import os
import sys

PACK_ROOT = ""  # Optional: e.g. r"D:\Assets\pirate_outpost". Empty = auto-detect.
DEFAULT_LAYOUT = "harbor"  # "harbor" or "gallery"


def resolve_root(explicit=None):
    candidates=[]
    if explicit:candidates.append(Path(explicit))
    if PACK_ROOT:candidates.append(Path(PACK_ROOT))
    if os.environ.get('PIRATE_PACK_ROOT'):candidates.append(Path(os.environ['PIRATE_PACK_ROOT']))
    if '__file__' in globals():candidates.append(Path(__file__).resolve().parents[2])
    try:
        import bpy
        text=getattr(bpy.context.space_data,'text',None)
        if text and text.filepath:candidates.append(Path(bpy.path.abspath(text.filepath)).resolve().parents[2])
    except (ImportError,AttributeError):
        pass
    for root in candidates:
        root=root.expanduser().resolve()
        if (root/'asset_manifest.json').is_file():return root
    raise FileNotFoundError('Cannot locate asset_manifest.json. Set PACK_ROOT at the top of this script.')


def make_material(bpy,root):
    material=bpy.data.materials.new('M_PirateAtlas_Preview')
    material.use_nodes=True;material.use_backface_culling=False
    nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
    out=nodes.new('ShaderNodeOutputMaterial');out.location=(620,80)
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');bsdf.location=(330,80)
    base=nodes.new('ShaderNodeTexImage');base.location=(-620,240)
    base.image=bpy.data.images.load(str(root/'textures/T_Pirate_BaseColor.png'),check_existing=True)
    base.image.colorspace_settings.name='sRGB'
    rm=nodes.new('ShaderNodeTexImage');rm.location=(-620,-120)
    rm.image=bpy.data.images.load(str(root/'textures/T_Pirate_RoughMetal.png'),check_existing=True)
    rm.image.colorspace_settings.name='Non-Color'
    separate=nodes.new('ShaderNodeSeparateColor');separate.mode='RGB';separate.location=(-230,-120)
    links.new(base.outputs['Color'],bsdf.inputs['Base Color'])
    links.new(rm.outputs['Color'],separate.inputs['Color'])
    links.new(separate.outputs['Green'],bsdf.inputs['Roughness']);links.new(separate.outputs['Blue'],bsdf.inputs['Metallic'])
    links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    for image in (base.image,rm.image):image.pack()
    return material


def import_prototype(bpy,filepath,library,material,name):
    from mathutils import Matrix
    before_objects=set(bpy.data.objects);before_materials=set(bpy.data.materials);before_images=set(bpy.data.images)
    bpy.ops.import_scene.gltf(filepath=str(filepath))
    created=list(set(bpy.data.objects)-before_objects);meshes=[o for o in created if o.type=='MESH']
    if len(meshes)!=1:
        raise RuntimeError(f'{filepath.name}: expected 1 mesh, imported {len(meshes)}')
    obj=meshes[0]
    # Bake importer root transforms while retaining the authored object origin.
    # Do not centre origins: dock connection planes depend on their precise pivots.
    world=obj.matrix_world.copy();obj.parent=None;obj.data.transform(world);obj.matrix_world=Matrix.Identity(4)
    obj.name=name;obj.data.name=name+'_Mesh';obj.data.materials.clear();obj.data.materials.append(material)
    for col in list(obj.users_collection):col.objects.unlink(obj)
    library.objects.link(obj)
    for other in created:
        if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
    # Only remove unused resources created by THIS GLB import, never global orphans.
    for mat in set(bpy.data.materials)-before_materials:
        if mat!=material and mat.users==0:bpy.data.materials.remove(mat)
    for image in set(bpy.data.images)-before_images:
        if image.users==0:bpy.data.images.remove(image)
    return obj


def add_camera_and_lights(bpy,scene,collection,layout):
    from mathutils import Vector
    cam_data=bpy.data.cameras.new('PiratePreview_Camera');cam=bpy.data.objects.new('PiratePreview_Camera',cam_data);collection.objects.link(cam)
    settings=layout['camera'];cam.location=settings['position_m'];target=Vector(settings['target_m'])
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam_data.type='ORTHO';cam_data.ortho_scale=settings['orthographic_scale'];cam_data.clip_end=1000;scene.camera=cam
    for name,pos,energy,size,color in [
        ('Key',(-12,-16,24),3300,12,(1,.86,.68)),
        ('Fill',(14,-4,17),2100,10,(.73,.85,1)),
        ('Rim',(0,16,22),2800,11,(1,.97,.87))]:
        data=bpy.data.lights.new('PiratePreview_'+name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(data.name,data);collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((0,1,0))-obj.location).to_track_quat('-Z','Y').to_euler()
    sun_data=bpy.data.lights.new('PiratePreview_Sun','SUN');sun_data.energy=1.8;sun_data.angle=math.radians(18)
    sun=bpy.data.objects.new(sun_data.name,sun_data);collection.objects.link(sun);sun.rotation_euler=(math.radians(25),math.radians(-18),math.radians(-28))
    world=bpy.data.worlds.new('PiratePreview_World');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.30,.36,.44,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45;scene.world=world


def build_preview(pack_root=None,layout_name='harbor',save_path=None,render_path=None,overwrite=False):
    import bpy
    from mathutils import Matrix
    if bpy.app.version<(4,2,0):raise RuntimeError('This script targets Blender 4.2 or later.')
    root=resolve_root(pack_root);sys.path.insert(0,str(root/'scripts'))
    from pipeline_common import read_json,validate_layout,pack_file
    manifest=read_json(root/'asset_manifest.json');layout=read_json(root/'layout'/f'{layout_name}_layout.json');validate_layout(layout,manifest)
    for a in manifest['assets']:
        if not pack_file(root,a['file']).is_file():raise FileNotFoundError(a['file'])
    # Refuse accidental file replacement before creating anything.
    for target in (save_path,render_path):
        if target and Path(target).expanduser().exists() and not overwrite:
            raise FileExistsError(str(target)+' already exists; pass --overwrite explicitly.')
    scene=bpy.data.scenes.new('PirateOutpost_'+layout_name);scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
    if bpy.context.window:bpy.context.window.scene=scene
    visible=bpy.data.collections.new('PirateOutpost_Instances');scene.collection.children.link(visible)
    library=bpy.data.collections.new('PirateOutpost_SourceMeshes');scene.collection.children.link(library)
    environment=bpy.data.collections.new('PirateOutpost_PreviewEnvironment');scene.collection.children.link(environment)
    stage=bpy.data.collections.new('PirateOutpost_CameraLights');scene.collection.children.link(stage)
    material=make_material(bpy,root);prototypes={}
    with bpy.context.temp_override(scene=scene,view_layer=scene.view_layers[0],collection=visible):
        for a in manifest['assets']:
            obj=import_prototype(bpy,pack_file(root,a['file']),library,material,a['id'])
            obj['asset_id']=a['id'];obj['collision_policy']=a['collision'];obj['source_file']=a['file'];prototypes[a['id']]=obj
        for o in layout['instances']:
            obj=bpy.data.objects.new(o['name'],prototypes[o['asset']].data);visible.objects.link(obj)
            obj.location=o['position_m'];obj.rotation_euler=(0,0,math.radians(o.get('yaw_degrees',0)));obj.scale=o.get('scale',[1,1,1]);obj['source_asset']=o['asset']
        for i,o in enumerate(layout.get('environment',[])):
            obj=import_prototype(bpy,pack_file(root,o['file']),environment,material,'PreviewOnly_'+str(i))
            obj.location=o['position_m'];obj.rotation_euler=(0,0,math.radians(o.get('yaw_degrees',0)));obj.scale=o.get('scale',[1,1,1]);obj['preview_only']=True
    library.hide_render=True;library.hide_viewport=True
    add_camera_and_lights(bpy,scene,stage,layout)
    scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
    scene.render.resolution_x=1920;scene.render.resolution_y=1440;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    try:scene.view_settings.view_transform='AgX'
    except (TypeError,ValueError):pass
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.type='MATERIAL'
    scene['pack_root']=str(root);scene['layout']=layout_name;scene['shared_mesh_count']=len(prototypes);scene['instance_count']=len(layout['instances'])
    if save_path:
        target=Path(save_path).expanduser().resolve();target.parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=not overwrite)
    if render_path:
        target=Path(render_path).expanduser().resolve();target.parent.mkdir(parents=True,exist_ok=True);scene.render.filepath=str(target)
        bpy.ops.render.render(write_still=True,scene=scene.name)
    print(f'Pirate Outpost: created NEW scene {scene.name!r}; {len(prototypes)} linked mesh sources / {len(layout["instances"])} instances.')
    return scene


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pack');parser.add_argument('--layout',choices=['harbor','gallery'],default=DEFAULT_LAYOUT);parser.add_argument('--save');parser.add_argument('--render');parser.add_argument('--overwrite',action='store_true')
    options=parser.parse_args(args)
    build_preview(options.pack,options.layout,options.save,options.render,options.overwrite)

if __name__=='__main__':main()
