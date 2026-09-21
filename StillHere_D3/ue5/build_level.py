"""Build a new UE5 editor level from Still Here D3.

Required: Python Editor Script Plugin, Editor Scripting Utilities, glTF/Interchange import.
Run in the editor via Tools > Execute Python Script, or runpy.run_path(...,run_name='__main__').
All repeated actors share StaticMesh assets. No user actors are deleted.
UE execution was unavailable in the delivery environment; see VALIDATION.md.
"""
from __future__ import annotations
from pathlib import Path
import json,sys,datetime,hashlib,math
import unreal

PACKAGE_ROOT=''                    # Optional. Usually inferred from this script's location.
CONTENT_ROOT='/Game/StillHere_D3'
REIMPORT_ASSETS=False               # Keep False to preserve manual asset edits on subsequent builds.
REBUILD_MATERIALS=False
CONFIRM_AND_SAVE_CURRENT_LEVEL=True
WARNINGS=[]

ROOT=Path(PACKAGE_ROOT).expanduser().resolve() if PACKAGE_ROOT else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ue5'))
from stillhere_environment import validate_api
API_PREFLIGHT=validate_api()
from stillhere_transform_math import calibrate,convert_instance,camera_transform,mv,WORLD_BASIS,unit
from stillhere_ue_materials import build_material,set_optional
EAL=unreal.EditorAssetLibrary
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(text):unreal.log('[StillHere] '+str(text))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe_content_root():
    if not CONTENT_ROOT.startswith('/Game/') or CONTENT_ROOT.rstrip('/')=='/Game':raise ValueError('CONTENT_ROOT must be a dedicated subfolder under /Game')


def check_files():
    scene=json.loads((ROOT/'data/scene.json').read_text(encoding='utf8'));assets={a['id']:a for a in json.loads((ROOT/'data/assets.json').read_text(encoding='utf8'))['assets']}
    used={i['asset_id'] for i in scene['instances']}|{'Axis_Probe_X','Axis_Probe_Y','Axis_Probe_Z'}
    for aid in used:
        if aid not in assets:raise KeyError('Unknown asset: '+aid)
        for role in ('glb','base_color','normal','orm'):
            if not (ROOT/assets[aid][role]).is_file():raise FileNotFoundError(ROOT/assets[aid][role])
    return scene,assets,sorted(used)


def confirm_save():
    if not CONFIRM_AND_SAVE_CURRENT_LEVEL:
        raise RuntimeError('Safety stop: open/save your current map and keep CONFIRM_AND_SAVE_CURRENT_LEVEL=True before creating a new map.')
    answer=unreal.EditorDialog.show_message(
        'Still Here D3',
        '현재 레벨을 저장한 뒤, 별도의 새 D3 레벨을 생성합니다. 기존 액터는 삭제하지 않습니다. 계속하시겠습니까?',
        unreal.AppMsgType.YES_NO,
        default_value=unreal.AppReturnType.NO)
    if answer!=unreal.AppReturnType.YES:return False
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError('Current level was not saved. Build stopped before any new level was loaded.')
    return True


def find_static_mesh(folder):
    found=[]
    for path in EAL.list_assets(folder,recursive=True,include_folder=False):
        obj=EAL.load_asset(path)
        if isinstance(obj,unreal.StaticMesh):found.append(obj)
    if len(found)==1:return found[0]
    if len(found)>1:raise RuntimeError('Ambiguous imported StaticMesh folder: '+folder)
    return None


def import_mesh(asset):
    aid=asset['id'];folder=CONTENT_ROOT+'/Imported/'+aid
    existing=find_static_mesh(folder) if EAL.does_directory_exist(folder) else None
    if existing and not REIMPORT_ASSETS:
        previous=EAL.get_metadata_tag(existing,'StillHereSourceSHA256')
        if previous and previous!=sha(ROOT/asset['glb']):WARNINGS.append(aid+': source GLB changed; existing asset preserved. Set REIMPORT_ASSETS=True to update it.')
        return existing
    task=unreal.AssetImportTask();task.filename=str(ROOT/asset['glb']);task.destination_path=folder
    task.destination_name=aid # Interchange may ignore this; returned object paths are authoritative.
    task.automated=True;task.replace_existing=REIMPORT_ASSETS;task.replace_existing_settings=False;task.save=True;task.async_=False
    TOOLS.import_asset_tasks([task])
    objects=list(task.get_objects());meshes=[x for x in objects if isinstance(x,unreal.StaticMesh)]
    if not meshes:
        for path in list(task.imported_object_paths):
            obj=EAL.load_asset(path)
            if isinstance(obj,unreal.StaticMesh):meshes.append(obj)
    if len(meshes)!=1:
        fallback=find_static_mesh(folder)
        if fallback:meshes=[fallback]
    if len(meshes)!=1:raise RuntimeError(f'{aid}: glTF import produced {len(meshes)} StaticMeshes. Enable Interchange glTF import and use default transforms.')
    mesh=meshes[0]
    EAL.set_metadata_tag(mesh,'StillHereAssetID',aid)
    EAL.set_metadata_tag(mesh,'StillHereSourceSHA256',sha(ROOT/asset['glb']))
    return mesh


def probe_calibration(meshes):
    centres=[]
    for axis in 'XYZ':
        bounds=meshes['Axis_Probe_'+axis].get_bounding_box()
        a=bounds.min;b=bounds.max
        centres.append([(a.x+b.x)*.5,(a.y+b.y)*.5,(a.z+b.z)*.5])
    result=calibrate(centres);log('Measured import basis: '+str(result['import_basis']));return result


def transform(converted):
    result=unreal.Transform()
    result.set_editor_property('translation',unreal.Vector(*converted['position_cm']))
    result.set_editor_property('rotation',unreal.Quat(*converted['quaternion_xyzw']))
    result.set_editor_property('scale3d',unreal.Vector(*converted.get('scale',[1.,1.,1.])))
    return result


def make_camera(scene):
    converted=camera_transform(scene['camera'])
    camera=ACTORS.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(),unreal.Rotator())
    if camera is None:raise RuntimeError('Camera actor creation failed')
    camera.set_actor_label('SH_Camera_Reference');camera.set_actor_transform(transform(converted),False,True)
    camera.set_folder_path('StillHere_D3/Camera_Lighting')
    component=camera.get_component_by_class(unreal.CameraComponent)
    component.set_editor_property('projection_mode',unreal.CameraProjectionMode.ORTHOGRAPHIC)
    component.set_editor_property('ortho_width',converted['ortho_width_cm'])
    component.set_editor_property('aspect_ratio',scene['camera']['resolution'][0]/scene['camera']['resolution'][1])
    component.set_editor_property('constrain_aspect_ratio',True)
    set_optional(component,'auto_calculate_ortho_planes',False,WARNINGS)
    set_optional(component,'ortho_near_clip_plane',5.,WARNINGS)
    set_optional(component,'ortho_far_clip_plane',25000.,WARNINGS)
    return camera


def set_pp(settings,name,value):
    settings.set_editor_property('override_'+name,True);settings.set_editor_property(name,value)


def make_lighting(scene):
    # A physically exposed daylight starting point; engine tone mapping is not pixel-identical to VTK.
    d=unit(mv(WORLD_BASIS,scene['lighting']['sun_direction_to_light']))
    sun=ACTORS.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(),unreal.Rotator())
    sun.set_actor_label('SH_Sun');sun.set_folder_path('StillHere_D3/Camera_Lighting')
    sun.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*d),unreal.Vector()),True)
    light=sun.get_component_by_class(unreal.DirectionalLightComponent)
    light.set_intensity(65000.);light.set_light_color(unreal.LinearColor(1.,.95,.84,1.),False)
    set_optional(light,'light_source_angle',3.0,WARNINGS);set_optional(light,'atmosphere_sun_light',True,WARNINGS)
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky=ACTORS.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,2000),unreal.Rotator())
    sky.set_actor_label('SH_SkyLight');sky.set_folder_path('StillHere_D3/Camera_Lighting')
    skycomp=sky.get_component_by_class(unreal.SkyLightComponent);skycomp.set_intensity(1.)
    skycomp.set_mobility(unreal.ComponentMobility.MOVABLE);set_optional(skycomp,'real_time_capture',True,WARNINGS)
    atmosphere=ACTORS.spawn_actor_from_class(unreal.SkyAtmosphere,unreal.Vector(),unreal.Rotator())
    atmosphere.set_actor_label('SH_SkyAtmosphere');atmosphere.set_folder_path('StillHere_D3/Camera_Lighting')
    volume=ACTORS.spawn_actor_from_class(unreal.PostProcessVolume,unreal.Vector(),unreal.Rotator())
    volume.set_actor_label('SH_Exposure_And_Grade');volume.set_folder_path('StillHere_D3/Camera_Lighting');volume.set_editor_property('unbound',True)
    pp=volume.get_editor_property('settings')
    set_pp(pp,'auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL)
    set_pp(pp,'auto_exposure_apply_physical_camera_exposure',True)
    set_pp(pp,'camera_iso',100.);set_pp(pp,'camera_shutter_speed',125.);set_pp(pp,'depth_of_field_fstop',11.)
    set_pp(pp,'auto_exposure_bias',.5);set_pp(pp,'bloom_intensity',.12);set_pp(pp,'vignette_intensity',.10)
    set_pp(pp,'ambient_occlusion_intensity',.65);set_pp(pp,'ambient_occlusion_radius',45.)
    set_pp(pp,'motion_blur_amount',0.);set_pp(pp,'depth_of_field_focal_distance',0.);set_pp(pp,'depth_of_field_scale',0.)
    volume.set_editor_property('settings',pp)
    try:skycomp.recapture_sky()
    except Exception as exc:WARNINGS.append('Sky capture: '+str(exc))


def unique_map_path():
    base=CONTENT_ROOT+'/Maps/L_StillHere_D3'
    if not EAL.does_asset_exist(base):return base
    suffix=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');path=base+'_'+suffix
    i=2
    while EAL.does_asset_exist(path):path=base+'_'+suffix+'_'+str(i);i+=1
    return path


def main():
    safe_content_root();scene,assets,used=check_files()
    if LEVELS.is_in_play_in_editor():raise RuntimeError('Stop Play In Editor before running this script.')
    if not confirm_save():log('Cancelled; no scene changes made.');return
    meshes={};native_materials={}
    with unreal.ScopedSlowTask(len(used)*2,'Still Here: GLB import and native materials') as slow:
        slow.make_dialog(True)
        for aid in used:
            if slow.should_cancel():raise RuntimeError('Build cancelled during asset import; previous level remains loaded.')
            slow.enter_progress_frame(1,aid);meshes[aid]=import_mesh(assets[aid])
        calibration=probe_calibration(meshes)
        for aid in used:
            if slow.should_cancel():raise RuntimeError('Build cancelled during material setup; previous level remains loaded.')
            slow.enter_progress_frame(1,'Material '+aid)
            if assets[aid]['category']=='calibration':continue
            mat=build_material(assets[aid],ROOT,CONTENT_ROOT,REBUILD_MATERIALS,WARNINGS);native_materials[aid]=mat
            previous_path=EAL.get_metadata_tag(meshes[aid],'StillHereNativeMaterial')
            current=meshes[aid].get_material(0)
            if previous_path and current and current.get_path_name()!=previous_path and not REBUILD_MATERIALS:
                WARNINGS.append(aid+': manually changed material slot preserved.')
            else:
                meshes[aid].set_material(0,mat);EAL.set_metadata_tag(meshes[aid],'StillHereNativeMaterial',mat.get_path_name())
            if not EAL.save_loaded_asset(meshes[aid],only_if_is_dirty=False):raise RuntimeError('StaticMesh could not be saved: '+meshes[aid].get_path_name())
    map_path=unique_map_path()
    if not LEVELS.new_level(map_path,is_partitioned_world=False):raise RuntimeError('Unable to create new level: '+map_path)
    placed=[]
    with unreal.ScopedSlowTask(len(scene['instances']),'Still Here: shared mesh actor placement') as slow:
        slow.make_dialog(True)
        for rec in scene['instances']:
            if slow.should_cancel():raise RuntimeError('Placement cancelled; the new level is partially built, previous level was preserved.')
            slow.enter_progress_frame(1,rec['id'])
            actor=ACTORS.spawn_actor_from_object(meshes[rec['asset_id']],unreal.Vector(),unreal.Rotator())
            if actor is None:raise RuntimeError('StaticMeshActor spawn failed: '+rec['id'])
            actor.set_actor_transform(transform(convert_instance(rec,calibration)),False,True)
            actor.set_actor_label(rec['id']);actor.set_folder_path('StillHere_D3/'+rec['group'])
            actor.set_editor_property('tags',['StillHere_D3','AssetID:'+rec['asset_id'],'InstanceID:'+rec['id']])
            category=assets[rec['asset_id']]['category']
            if category in ('trees','shrubs','groundcover','vines','water','wildlife','character'):actor.set_actor_enable_collision(False)
            component=actor.get_component_by_class(unreal.StaticMeshComponent)
            if component:component.set_mobility(unreal.ComponentMobility.STATIC)
            placed.append(actor)
    camera=make_camera(scene);make_lighting(scene)
    ACTORS.set_selected_level_actors([camera])
    try:LEVELS.pilot_level_actor(camera)
    except Exception as exc:WARNINGS.append('Pilot camera manually: '+str(exc))
    if not LEVELS.save_current_level():raise RuntimeError('Scene built, but saving the newly created level failed.')
    out=Path(unreal.Paths.project_saved_dir())/'StillHere_D3';out.mkdir(parents=True,exist_ok=True)
    receipt={'api_preflight':API_PREFLIGHT,'engine_version':unreal.SystemLibrary.get_engine_version(),'map_path':map_path,'instances_created':len(placed),
             'meshes':{aid:mesh.get_path_name() for aid,mesh in meshes.items()},'calibration':calibration,
             'source_manifest':str(ROOT/'data/scene.json'),'source_manifest_sha256':sha(ROOT/'data/scene.json'),'warnings':WARNINGS,
             'reuse_mode':'StaticMesh assets shared by separate editable StaticMeshActors; not automatically converted to HISM.'}
    (out/'build_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    for warning in WARNINGS:unreal.log_warning('[StillHere] '+warning)
    log(f'Built {len(placed)} actors. Map: {map_path}. Receipt: {out / "build_receipt.json"}')

if __name__=='__main__':main()
