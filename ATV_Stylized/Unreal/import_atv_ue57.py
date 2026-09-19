"""Import the included GLB and construct its material in Unreal Editor 5.7.

Enable Python Editor Script Plugin, Editor Scripting Utilities, and Interchange
Editor/glTF support; restart the editor after enabling plugins.
Use Tools > Execute Python Script, or the Output Log in Python mode:
    import runpy
    runpy.run_path(r'D:/ATV_Stylized/Unreal/import_atv_ue57.py', run_name='__main__')

The package is self-locating. No absolute user paths are baked into this script.
It does not edit project config or modify the current level by default.
Existing assets are protected unless REPLACE_EXISTING is explicitly enabled.

API contracts checked against Epic's versioned 5.7 documentation. Unreal was not
available in the delivery environment; engine execution remains unverified.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import unreal

PACKAGE_ROOT=Path(__file__).resolve().parents[1]
DESTINATION='/Game/ATV_Stylized'
REPLACE_EXISTING=False
SPAWN_PREVIEW_ACTOR=False
GENERATE_SIMPLE_COLLISION=True
IMPORT_YAW_DEGREES=0.0  # glTF source is +X nose / +Y up; adjust only for your project convention.
_KEEP_ALIVE=[]


def log(message):unreal.log('[ATV] '+message)


def require_api():
    needed=['InterchangeManager','InterchangeGenericAssetsPipeline','ImportAssetParameters','MaterialEditingLibrary','EditorAssetLibrary','StaticMeshEditorSubsystem']
    missing=[name for name in needed if not hasattr(unreal,name)]
    if missing:raise RuntimeError('Enable required editor/Interchange plugins and restart. Missing: '+', '.join(missing))
    version=unreal.SystemLibrary.get_engine_version()
    if not version.startswith('5.7'):
        unreal.log_warning('[ATV] Script targets UE 5.7; this editor reports '+version)
    return version


def import_texture(filename,name,is_mask=False):
    path=PACKAGE_ROOT/'Textures'/filename
    if not path.is_file():raise FileNotFoundError(path)
    task=unreal.AssetImportTask()
    task.set_editor_property('filename',str(path))
    task.set_editor_property('destination_path',DESTINATION+'/Textures')
    task.set_editor_property('destination_name',name)
    task.set_editor_property('automated',True)
    task.set_editor_property('async_',False)
    task.set_editor_property('replace_existing',REPLACE_EXISTING)
    task.set_editor_property('replace_existing_settings',REPLACE_EXISTING)
    task.set_editor_property('save',False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported=list(task.get_objects())  # Blocks if an import backend used async work.
    textures=[obj for obj in imported if isinstance(obj,unreal.Texture2D)]
    if not textures:
        textures=[unreal.EditorAssetLibrary.load_asset(p) for p in task.get_editor_property('imported_object_paths')]
        textures=[obj for obj in textures if isinstance(obj,unreal.Texture2D)]
    if len(textures)!=1:raise RuntimeError(f'Expected one texture from {filename}, got {len(textures)}')
    texture=textures[0]
    texture.set_editor_property('srgb',not is_mask)
    texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS if is_mask else unreal.TextureCompressionSettings.TC_DEFAULT)
    texture.set_editor_property('compression_no_alpha',True)
    texture.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('virtual_texture_streaming',False)
    unreal.EditorAssetLibrary.save_loaded_asset(texture,False)
    return texture


def import_mesh():
    path=PACKAGE_ROOT/'Model/SM_ATV_Stylized.glb'
    if not path.is_file():raise FileNotFoundError(path)
    manager=unreal.InterchangeManager.get_interchange_manager_scripted()
    source=unreal.InterchangeManager.create_source_data(str(path))
    if not manager.can_translate_source_data(source,False):
        raise RuntimeError('No GLB translator is registered. Enable the Interchange glTF/editor components and restart.')
    pipeline=unreal.InterchangeGenericAssetsPipeline()
    pipeline.set_editor_property('asset_name','SM_ATV_Stylized')
    pipeline.set_editor_property('use_source_name_for_asset',False)
    pipeline.set_editor_property('asset_type_sub_folders',False)
    pipeline.set_editor_property('scene_name_sub_folder',False)
    pipeline.set_editor_property('import_offset_uniform_scale',1.0)  # NOT 100: glTF metre conversion is the translator's job.
    pipeline.set_editor_property('import_offset_rotation',unreal.Rotator(0,IMPORT_YAW_DEGREES,0))
    mesh_options=pipeline.get_editor_property('mesh_pipeline')
    mesh_options.set_editor_property('import_static_meshes',True)
    mesh_options.set_editor_property('import_skeletal_meshes',False)
    mesh_options.set_editor_property('combine_static_meshes',True)
    mesh_options.set_editor_property('build_nanite',False)
    mesh_options.set_editor_property('collision',False)
    # UV0 is already unique. Create a separate lightmap channel without changing UV0.
    mesh_options.set_editor_property('generate_lightmap_u_vs',True)
    mesh_options.set_editor_property('src_lightmap_index',0)
    mesh_options.set_editor_property('dst_lightmap_index',1)
    common=pipeline.get_editor_property('common_meshes_properties')
    common.set_editor_property('recompute_normals',False)
    common.set_editor_property('recompute_tangents',True)
    common.set_editor_property('use_mikk_t_space',True)
    common.set_editor_property('use_full_precision_u_vs',True)
    common.set_editor_property('bake_meshes',True)
    mat_options=pipeline.get_editor_property('material_pipeline')
    mat_options.set_editor_property('import_materials',False)
    mat_options.get_editor_property('texture_pipeline').set_editor_property('import_textures',False)
    parameters=unreal.ImportAssetParameters()
    parameters.set_editor_property('is_automated',True)
    parameters.set_editor_property('replace_existing',REPLACE_EXISTING)
    parameters.set_editor_property('destination_name','SM_ATV_Stylized')
    # The override is an in-memory UObject path, kept alive through synchronous import.
    parameters.set_editor_property('override_pipelines',[unreal.SoftObjectPath(pipeline.get_path_name())])
    _KEEP_ALIVE.extend([pipeline,source,parameters])
    result=manager.import_asset(DESTINATION+'/Meshes',source,parameters)
    manager.wait_until_all_tasks_done(False)
    meshes=[obj for obj in (result or []) if isinstance(obj,unreal.StaticMesh)]
    if len(meshes)!=1:
        raise RuntimeError(f'Interchange should create one StaticMesh, created {len(meshes)}. Review the import log.')
    mesh=meshes[0]
    if mesh.get_name()!='SM_ATV_Stylized':
        new_path=DESTINATION+'/Meshes/SM_ATV_Stylized'
        if not unreal.EditorAssetLibrary.rename_asset(mesh.get_path_name(),new_path):
            raise RuntimeError('Mesh was imported but could not be renamed to '+new_path)
        mesh=unreal.EditorAssetLibrary.load_asset(new_path)
    return mesh


def main():
    engine=require_api()
    files=[PACKAGE_ROOT/'Model/SM_ATV_Stylized.glb']+[PACKAGE_ROOT/'Textures'/f'T_ATV_{suffix}.png' for suffix in ['BaseColor','ORM','Emissive']]
    for path in files:
        if not path.is_file():raise FileNotFoundError(path)
    EAL=unreal.EditorAssetLibrary
    if EAL.does_directory_exist(DESTINATION) and EAL.list_assets(DESTINATION,True,False) and not REPLACE_EXISTING:
        raise RuntimeError(DESTINATION+' is not empty. Choose a new DESTINATION or enable REPLACE_EXISTING.')
    for suffix in ['/Meshes','/Textures','/Materials']:EAL.make_directory(DESTINATION+suffix)
    mesh=import_mesh()
    base=import_texture('T_ATV_BaseColor.png','T_ATV_BaseColor')
    orm=import_texture('T_ATV_ORM.png','T_ATV_ORM',True)
    emissive=import_texture('T_ATV_Emissive.png','T_ATV_Emissive')
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import atv_materials_ue57
    material,instance=atv_materials_ue57.create_materials(DESTINATION+'/Materials',base,orm,emissive,REPLACE_EXISTING)
    slots=len(mesh.get_editor_property('static_materials'))
    if slots==0:mesh.add_material(instance)
    else:
        for i in range(slots):mesh.set_material(i,instance)
    mesh.set_editor_property('light_map_coordinate_index',1)
    mesh.set_editor_property('light_map_resolution',128)
    mesh.set_editor_property('allow_cpu_access',False)
    subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    if GENERATE_SIMPLE_COLLISION:
        subsystem.remove_collisions(mesh)
        collision_id=subsystem.add_simple_collisions(mesh,unreal.ScriptCollisionShapeType.NDOP26)
        if collision_id<0:unreal.log_warning('[ATV] Simplified collision creation failed; add project-specific collision manually.')
    triangles=mesh.get_num_triangles(0)
    if triangles<=0 or triangles>=10000:raise RuntimeError(f'Unexpected imported triangle count: {triangles}')
    ext=mesh.get_bounds().box_extent
    dimensions=[float(ext.x*2),float(ext.y*2),float(ext.z*2)]
    if not 240<max(dimensions)<310:
        raise RuntimeError('Unexpected unit conversion; expected longest dimension near 271 cm, got '+str(dimensions))
    EAL.save_loaded_asset(mesh,False)
    if SPAWN_PREVIEW_ACTOR:
        actor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,0),unreal.Rotator(0,0,0))
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.set_actor_label('ATV_Stylized_Preview')
        # Deliberately do not save or replace the user's current level.
    report={'engine':engine,'mesh':mesh.get_path_name(),'material_instance':instance.get_path_name(),'triangles_lod0':triangles,'dimensions_cm':dimensions,'textures':[t.get_path_name() for t in [base,orm,emissive]],'uv0':'delivered unique atlas','lightmap_uv':1,'normal_map':False,'nanite':False}
    report_path=Path(unreal.Paths.project_saved_dir())/'ATV_Import_Report.json'
    report_path.write_text(json.dumps(report,indent=2),encoding='utf8')
    log('Import complete: '+json.dumps(report))
    log('Runtime report: '+str(report_path))
    return report

if __name__=='__main__':
    try:main()
    except Exception as exc:
        unreal.log_error('[ATV] Import stopped: '+str(exc))
        raise
