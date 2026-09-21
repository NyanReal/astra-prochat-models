"""Reconstruct Still Here D3 in a NEW Blender scene without clearing existing work.

UI: Scripting > Open this file > Run Script.
CLI: blender --background --python blender/build_scene.py -- --render --engine cycles
Default: import shipped GLBs, link mesh data, fit camera, save a new .blend.
Set IMPORT_MODE='MESH_DATA' as an independent fallback if glTF import is unavailable.
Editor execution was not possible in the delivery environment; see VALIDATION.md.
"""
from __future__ import annotations
from pathlib import Path
import sys,os,json,math,argparse
import bpy
from mathutils import Matrix,Vector,Quaternion

IMPORT_MODE='GLB'                 # 'GLB' or 'MESH_DATA'; the fallback uses the same exported arrays.
SAVE_BLEND=True
PACKAGE_ROOT=''                   # Usually leave empty. Optional absolute path to StillHere_D3.


def root_path():
    if PACKAGE_ROOT:return Path(PACKAGE_ROOT).expanduser().resolve()
    env=os.environ.get('STILLHERE_ROOT')
    if env:return Path(env).expanduser().resolve()
    script=globals().get('__file__')
    if not script:
        space=bpy.context.space_data
        if space and getattr(space,'text',None):script=space.text.filepath
    if not script:raise RuntimeError('Open the supplied .py file from disk, or set PACKAGE_ROOT at the top of this script.')
    return Path(script).resolve().parents[1]


def unique_file(path):
    if not path.exists():return path
    i=2
    while path.with_name(f'{path.stem}_{i:02d}{path.suffix}').exists():i+=1
    return path.with_name(f'{path.stem}_{i:02d}{path.suffix}')


def create_collections(scene):
    root=bpy.data.collections.new('StillHere_D3');scene.collection.children.link(root)
    library=bpy.data.collections.new('_AssetLibrary');root.children.link(library);library.hide_render=True;library.hide_viewport=True
    cache={'':root}
    def group(path):
        if path in cache:return cache[path]
        parent,name=path.rsplit('/',1) if '/' in path else ('',path)
        col=bpy.data.collections.new(name);group(parent).children.link(col);cache[path]=col;return col
    return library,group


def load_prototype(asset,root,library,make_material,refine_material):
    if IMPORT_MODE=='MESH_DATA':
        import numpy as np
        d=np.load(root/asset['mesh_data']);mesh=bpy.data.meshes.new(asset['id'])
        mesh.from_pydata(d['vertices'].tolist(),[],d['faces'].tolist());mesh.update()
        uv=d['uv'].copy();uv[:,1]=1-uv[:,1];layer=mesh.uv_layers.new(name='UVMap')
        loop_uv=uv[d['faces'].reshape(-1)].astype('float32').reshape(-1)
        layer.data.foreach_set('uv',loop_uv)
        for poly in mesh.polygons:poly.use_smooth=True
        try:mesh.normals_split_custom_set_from_vertices(d['normals'].tolist())
        except (AttributeError,RuntimeError):pass
        proto=bpy.data.objects.new('LIB_'+asset['id'],mesh);library.objects.link(proto)
        mesh.materials.append(make_material(asset,root))
    else:
        before=set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(root/asset['glb']))
        created=set(bpy.data.objects)-before;meshes=[o for o in created if o.type=='MESH']
        if len(meshes)!=1:raise RuntimeError(f'{asset["id"]}: expected one mesh object from GLB, received {len(meshes)}')
        proto=meshes[0]
        # Normalize any importer-created root transform exactly once.
        world=proto.matrix_world.copy();proto.parent=None;proto.data.transform(world);proto.matrix_world=Matrix.Identity(4);proto.data.update()
        for collection in list(proto.users_collection):collection.objects.unlink(proto)
        library.objects.link(proto);proto.name='LIB_'+asset['id']
        for obj in created:
            if obj!=proto:bpy.data.objects.remove(obj,do_unlink=True)
        for mat in proto.data.materials:refine_material(mat,asset)
    verts=proto.data.vertices
    lo=[min(v.co[k] for v in verts) for k in range(3)];hi=[max(v.co[k] for v in verts) for k in range(3)]
    expected=asset['bounds_m'];error=max(abs(a-b) for a,b in zip(lo+hi,expected[0]+expected[1]))
    if error>.005:
        raise RuntimeError(f'{asset["id"]}: imported bounds differ by {error:.4f} m. Try IMPORT_MODE="MESH_DATA"; no incorrect placement was accepted.')
    proto['asset_id']=asset['id'];proto['uv_density_px_m']=asset['effective_texel_density_px_m'];proto.hide_render=True
    return proto


def configure_camera_and_lights(scene,settings,groups):
    info=settings['camera'];data=bpy.data.cameras.new('SH_Camera');data.type='ORTHO';data.ortho_scale=info['ortho_width_m'];data.clip_start=.05;data.clip_end=250
    camera=bpy.data.objects.new('SH_Camera_Reference',data);groups('Camera_Lighting').objects.link(camera)
    camera.location=info['position_m'];camera.rotation_euler=(Vector(info['target_m'])-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
    scene.render.resolution_x,scene.render.resolution_y=info['resolution'];scene.render.resolution_percentage=100
    sun_data=bpy.data.lights.new('SH_Sun','SUN');sun_data.energy=settings['lighting']['sun_energy_blender'];sun_data.angle=math.radians(settings['lighting']['sun_angle_degrees']);sun_data.color=(1.,.94,.82)
    sun=bpy.data.objects.new('SH_Sun',sun_data);groups('Camera_Lighting').objects.link(sun)
    direction=Vector(settings['lighting']['sun_direction_to_light']);sun.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler();sun.location=(-15,-20,35)
    world=bpy.data.worlds.new('SH_ForestSky');world.use_nodes=True
    bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(*settings['lighting']['world_color_linear'],1)
    bg.inputs['Strength'].default_value=settings['lighting']['world_strength_blender'];scene.world=world
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    try:scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    except TypeError:pass
    scene.view_settings.exposure=.3;scene.view_settings.gamma=1.
    scene.frame_start=1;scene.frame_end=240;scene.render.fps=24
    return camera


def main():
    root=root_path();sys.path.insert(0,str(root/'blender'))
    from stillhere_blender_materials import make_material,refine_material
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('--render',action='store_true');parser.add_argument('--engine',choices=['cycles','eevee'],default='cycles');options,_=parser.parse_known_args(args)
    scene_file=root/'data/scene.json';asset_file=root/'data/assets.json'
    if not scene_file.is_file() or not asset_file.is_file():raise FileNotFoundError('data/scene.json or data/assets.json is missing. Extract the entire ZIP first.')
    settings=json.loads(scene_file.read_text(encoding='utf8'));assets={a['id']:a for a in json.loads(asset_file.read_text(encoding='utf8'))['assets']}
    used=sorted({i['asset_id'] for i in settings['instances']})
    for aid in used:
        if aid not in assets:raise KeyError('Unknown asset ID: '+aid)
        for key in ('glb','base_color','normal','orm','mesh_data'):
            if not (root/assets[aid][key]).is_file():raise FileNotFoundError(root/assets[aid][key])
    scene=bpy.data.scenes.new('StillHere_D3')
    if bpy.context.window:bpy.context.window.scene=scene
    else:raise RuntimeError('No active Blender window context; run via Blender UI or --background --python.')
    library,groups=create_collections(scene);prototypes={}
    for idx,aid in enumerate(used):
        print(f'[StillHere] Import {idx+1}/{len(used)}: {aid}',flush=True)
        prototypes[aid]=load_prototype(assets[aid],root,library,make_material,refine_material)
    for rec in settings['instances']:
        obj=bpy.data.objects.new(rec['id'],prototypes[rec['asset_id']].data);groups(rec['group']).objects.link(obj)
        obj.location=rec['position_m'];x,y,z,w=rec['rotation_quat_xyzw'];obj.rotation_mode='QUATERNION';obj.rotation_quaternion=Quaternion((w,x,y,z));obj.scale=rec['scale']
        obj['asset_id']=rec['asset_id'];obj['instance_id']=rec['id'];obj['source_group']=rec['group']
    configure_camera_and_lights(scene,settings,groups)
    if options.engine=='cycles':
        scene.render.engine='CYCLES';scene.cycles.samples=96;scene.cycles.use_denoising=True;scene.cycles.device='CPU'
    else:scene.render.engine='BLENDER_EEVEE_NEXT'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
    out=root/'output/blender';out.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(out/'reference_camera.png')
    saved=None
    if SAVE_BLEND:
        saved=unique_file(out/'StillHere_D3.blend');bpy.ops.wm.save_as_mainfile(filepath=str(saved))
    if options.render:bpy.ops.render.render(write_still=True,scene=scene.name)
    receipt={'scene':scene.name,'assets_loaded':len(used),'instances_created':len(settings['instances']),
             'linked_meshes':True,'import_mode':IMPORT_MODE,'blender_version':bpy.app.version_string,'saved_blend':str(saved) if saved else None,
             'render_requested':options.render,'source_manifest':'data/scene.json'}
    (out/'build_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('[StillHere] Scene ready:',saved or scene.name)

if __name__=='__main__':main()
