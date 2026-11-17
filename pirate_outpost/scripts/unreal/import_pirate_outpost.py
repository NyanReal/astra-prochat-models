"""Pirate Outpost: deterministic GLB -> UE5 Static Mesh import, shared atlas material.

Target API: Unreal Engine 5.6 editor Python/Interchange. Newer builds are capability-
checked, not assumed tested. This script has NOT been executed in Unreal here.
Enable Python Editor Script Plugin, Editor Scripting Utilities and Interchange.
Run through File > Execute Python Script, or import this module and call run().

Default behavior is additive: never overwrite existing assets. Only assets tagged
as owned by this pack can be explicitly replaced with REIMPORT_OWNED=True.
No project settings are changed and no level is created/saved/deleted.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib
import math
import os
import sys
import traceback

PACK_ROOT = ""  # Optional r"D:\Assets\pirate_outpost"; empty = script location.
DESTINATION = "/Game/PirateOutpost"
REIMPORT_OWNED = False
GENERATE_LIGHTMAP_UV = False  # UV0 is an overlapping atlas; see the lightmap caveat.
BUILD_COLLISION = True
PACK_TAG = "PirateOutpost_v1"
OWNER_KEY = "PirateOutpost.Owner"
ASSET_KEY = "PirateOutpost.AssetID"
READY_KEY = "PirateOutpost.ImportComplete"
SOURCE_KEY = "PirateOutpost.SourceSHA256"


def resolve_root(explicit=None):
    value=explicit or PACK_ROOT or os.environ.get('PIRATE_PACK_ROOT')
    root=Path(value).expanduser().resolve() if value else Path(__file__).resolve().parents[2]
    if not (root/'asset_manifest.json').is_file():raise FileNotFoundError('Set PACK_ROOT to the extracted pirate_outpost folder.')
    return root


def run(pack_root=None,destination=DESTINATION,reimport_owned=REIMPORT_OWNED):
    import unreal
    root=resolve_root(pack_root);sys.path.insert(0,str(root/'scripts'))
    from pipeline_common import read_json,pack_file,content_root,manifest_hash,infer_basis,expected_bounds
    dest=content_root(destination);manifest=read_json(root/'asset_manifest.json')
    # Fail before asset writes when mandatory modules/capabilities are unavailable.
    required=['InterchangeManager','InterchangeGenericAssetsPipeline','ImportAssetParameters','StaticMeshEditorSubsystem',
              'EditorAssetLibrary','AssetImportTask','MaterialEditingLibrary','MaterialFactoryNew']
    missing=[name for name in required if not hasattr(unreal,name)]
    if missing:raise RuntimeError('Missing UE Python APIs/plugins: '+', '.join(missing))
    for a in manifest['assets']:
        if not pack_file(root,a['file']).is_file():raise FileNotFoundError(a['file'])
    eal=unreal.EditorAssetLibrary;tools=unreal.AssetToolsHelpers.get_asset_tools()
    mesh_editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    manager=unreal.InterchangeManager.get_interchange_manager_scripted()
    report={
        'pack':PACK_TAG,'engine_version':unreal.SystemLibrary.get_engine_version(),
        'started_utc':datetime.now(timezone.utc).isoformat(),'destination':dest,
        'manifest_sha256':manifest_hash(root),'assets':{},'warnings':[],
        'status':'running','editor_runtime_result':'This report is produced only when run in Unreal.'}
    report_path=root/'reports/ue_import_report.json';report_path.parent.mkdir(parents=True,exist_ok=True)

    def write_report():
        temporary=report_path.with_suffix('.json.tmp');temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(report_path)

    def warning(message):
        unreal.log_warning('[PirateOutpost] '+message);report['warnings'].append(message)

    def own(obj,asset_id):
        eal.set_metadata_tag(obj,OWNER_KEY,PACK_TAG);eal.set_metadata_tag(obj,ASSET_KEY,asset_id)

    def existing_owned(path,asset_id,cls):
        if not eal.does_asset_exist(path):return None
        obj=eal.load_asset(path)
        if not isinstance(obj,cls):raise RuntimeError('Existing asset has a different class: '+path)
        if str(eal.get_metadata_tag(obj,OWNER_KEY))!=PACK_TAG or str(eal.get_metadata_tag(obj,ASSET_KEY))!=asset_id:
            raise RuntimeError('Refusing to touch an unowned asset at '+path+'. Use a different DESTINATION.')
        return obj

    def save(obj):
        if not eal.save_loaded_asset(obj,only_if_is_dirty=False):raise RuntimeError('Could not save '+obj.get_path_name())

    def set_required(obj,key,value):
        try:obj.set_editor_property(key,value)
        except Exception as exc:raise RuntimeError(f'Required UE API property {obj.get_class().get_name()}.{key} is unavailable: {exc}') from exc

    def set_optional(obj,key,value):
        try:obj.set_editor_property(key,value)
        except Exception as exc:warning(f'Optional property {key} not applied: {exc}')

    def pipeline(asset_id,uniform_scale):
        p=unreal.InterchangeGenericAssetsPipeline()
        for key,value in [('asset_name',asset_id),('asset_type_sub_folders',False),('scene_name_sub_folder',False),
                          ('use_source_name_for_asset',True),('import_offset_uniform_scale',uniform_scale),
                          ('import_offset_translation',unreal.Vector(0,0,0)),('import_offset_rotation',unreal.Rotator(0,0,0))]:set_required(p,key,value)
        mp=p.get_editor_property('mesh_pipeline')
        for key,value in [('import_static_meshes',True),('import_skeletal_meshes',False),('combine_static_meshes',True),
                          ('build_nanite',False),('collision',False),('generate_lightmap_u_vs',GENERATE_LIGHTMAP_UV)]:set_required(mp,key,value)
        cp=p.get_editor_property('common_meshes_properties')
        set_required(cp,'recompute_normals',False);set_optional(cp,'recompute_tangents',True);set_optional(cp,'remove_degenerates',True)
        set_required(cp,'bake_meshes',True);set_optional(cp,'bake_pivot_meshes',False)
        matp=p.get_editor_property('material_pipeline');set_required(matp,'import_materials',False)
        txp=matp.get_editor_property('texture_pipeline');set_required(txp,'import_textures',False)
        # Retain the Python/UObject reference until synchronous import_asset returns.
        return p

    def import_mesh(asset_id,source,dest_folder,uniform_scale):
        expected_path=dest_folder+'/'+asset_id
        old=existing_owned(expected_path,asset_id,unreal.StaticMesh)
        source_hash=hashlib.sha256(Path(source).read_bytes()).hexdigest()
        if old and not reimport_owned:
            if str(eal.get_metadata_tag(old,SOURCE_KEY))!=source_hash:
                raise RuntimeError('Source GLB changed for '+asset_id+'; enable REIMPORT_OWNED explicitly or use a new destination.')
            ready=str(eal.get_metadata_tag(old,READY_KEY))=='1'
            return old,'skipped_existing' if ready else 'resumed_unfinished'
        p=pipeline(asset_id,uniform_scale)
        params=unreal.ImportAssetParameters();params.set_editor_property('is_automated',True);params.set_editor_property('replace_existing',bool(old));params.set_editor_property('destination_name',asset_id)
        params.set_editor_property('override_pipelines',[unreal.SoftObjectPath(p.get_path_name())])
        source_data=unreal.InterchangeManager.create_source_data(str(source))
        if not manager.can_translate_source_data(source_data):raise RuntimeError('No GLB translator is enabled for '+str(source))
        objects=manager.import_asset(dest_folder,source_data,params)
        meshes=[o for o in (objects or []) if isinstance(o,unreal.StaticMesh)]
        if len(meshes)!=1:raise RuntimeError(f'{asset_id}: Interchange returned {len(meshes)} StaticMeshes; expected one.')
        mesh=meshes[0]
        if mesh.get_path_name().split('.')[0]!=expected_path:
            raise RuntimeError(f'Unexpected imported path {mesh.get_path_name()}; expected {expected_path}. No automatic rename/delete was attempted.')
        own(mesh,asset_id);eal.set_metadata_tag(mesh,READY_KEY,'0');eal.set_metadata_tag(mesh,SOURCE_KEY,source_hash)
        return mesh,'reimported' if old else 'imported'

    def vec(v):return [float(v.x),float(v.y),float(v.z)]
    def bounds(mesh):
        box=mesh.get_bounding_box();return vec(box.min),vec(box.max)

    def check_bounds(mesh,source_bounds,calibration):
        actual=bounds(mesh);expected=expected_bounds(source_bounds,calibration['basis'],100)
        extent=max(expected[1][i]-expected[0][i] for i in range(3));tol=max(.05,extent*.003)
        error=max(abs(actual[j][i]-expected[j][i]) for j in range(2) for i in range(3))
        if error>tol:raise RuntimeError(f'{mesh.get_name()}: imported size/pivot differs by {error:.3f} cm; tolerance {tol:.3f} cm.')
        return actual

    def import_texture(filename,linear):
        asset_id=Path(filename).stem;folder=dest+'/Shared';path=folder+'/'+asset_id
        old=existing_owned(path,asset_id,unreal.Texture2D)
        if old and not reimport_owned:return old
        task=unreal.AssetImportTask()
        for k,v in [('filename',str(root/'textures'/filename)),('destination_path',folder),('destination_name',asset_id),('automated',True),('replace_existing',bool(old)),('save',False)]:task.set_editor_property(k,v)
        tools.import_asset_tasks([task]);objects=list(task.get_objects());textures=[o for o in objects if isinstance(o,unreal.Texture2D)]
        if len(textures)!=1:raise RuntimeError('Texture import failed: '+filename)
        tex=textures[0]
        if tex.get_path_name().split('.')[0]!=path:raise RuntimeError('Texture importer used an unexpected path: '+tex.get_path_name())
        own(tex,asset_id);tex.set_editor_property('srgb',not linear)
        tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS if linear else unreal.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('max_texture_size',1024);save(tex);return tex

    def shared_material(base,rm):
        asset_id='M_PirateAtlas';folder=dest+'/Shared';path=folder+'/'+asset_id
        mat=existing_owned(path,asset_id,unreal.Material)
        if mat and not reimport_owned:return mat
        if mat is None:mat=tools.create_asset(asset_id,folder,unreal.Material,unreal.MaterialFactoryNew())
        if mat is None:raise RuntimeError('Could not create '+path)
        lib=unreal.MaterialEditingLibrary
        if reimport_owned:lib.delete_all_material_expressions(mat)
        mat.set_editor_property('two_sided',True)
        color=lib.create_material_expression(mat,unreal.MaterialExpressionTextureSampleParameter2D,-500,-100)
        color.set_editor_property('parameter_name','BaseColor');color.set_editor_property('texture',base);color.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        masks=lib.create_material_expression(mat,unreal.MaterialExpressionTextureSampleParameter2D,-500,230)
        masks.set_editor_property('parameter_name','RoughMetal');masks.set_editor_property('texture',rm);masks.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        links=[lib.connect_material_property(color,'RGB',unreal.MaterialProperty.MP_BASE_COLOR),
               lib.connect_material_property(masks,'G',unreal.MaterialProperty.MP_ROUGHNESS),
               lib.connect_material_property(masks,'B',unreal.MaterialProperty.MP_METALLIC)]
        if not all(links):raise RuntimeError('Could not wire the atlas material outputs.')
        own(mat,asset_id);lib.recompile_material(mat);save(mat);return mat

    def collision(mesh,kind):
        if not BUILD_COLLISION:return 'not_requested'
        if not mesh_editor.remove_collisions(mesh):warning('remove_collisions returned false for '+mesh.get_name())
        # Opening-bearing structures use static triangle collision, NOT a solid hull.
        if kind=='box':
            result=mesh_editor.add_simple_collisions(mesh,unreal.ScriptCollisionShapeType.BOX)
            if result<0:raise RuntimeError('Box collision generation failed')
        elif kind=='convex':
            if not mesh_editor.set_convex_decomposition_collisions(mesh,4,16,10000):raise RuntimeError('Convex collision generation failed')
        elif kind not in ('complex','none'):raise ValueError('Unknown collision policy '+kind)
        body=mesh.get_editor_property('body_setup')
        if body is None:
            # Some engine builds omit BodySetup when the Interchange collision flag is off.
            if mesh_editor.add_simple_collisions(mesh,unreal.ScriptCollisionShapeType.BOX)<0:
                raise RuntimeError('Could not initialize BodySetup')
            mesh_editor.remove_collisions(mesh);body=mesh.get_editor_property('body_setup')
        if body is None:raise RuntimeError('Mesh BodySetup was not created')
        body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if kind=='complex' else unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        body.set_editor_property('double_sided_geometry',kind=='complex')
        if kind=='none':
            # Prevent complex traces as well; placement also disables the component.
            mesh_editor.enable_section_collision(mesh,False,0,0)
        mesh.set_editor_property('customized_collision',True)
        return kind

    write_report()
    try:
        # Measure the engine's actual glTF basis and scale; never assume -Y or 100x.
        probe,probe_status=import_mesh('SM_AxisProbe',root/'technical/SM_AxisProbe.glb',dest+'/Technical',1.0)
        raw=infer_basis(*bounds(probe));eal.set_metadata_tag(probe,READY_KEY,'1');save(probe)
        if raw['basis'][2]!=[0,0,1]:raise RuntimeError('The GLB translator did not map source +Z to Unreal +Z; stop rather than place a sideways scene.')
        uniform=100.0/raw['units_per_metre']
        calibration=dict(raw);calibration['probe_units_per_metre']=raw['units_per_metre'];calibration['units_per_metre']=100.;calibration['import_offset_uniform_scale']=uniform
        report['calibration']=calibration;report['probe']=probe.get_path_name()
        base=import_texture('T_Pirate_BaseColor.png',False);rm=import_texture('T_Pirate_RoughMetal.png',True);material=shared_material(base,rm)
        report['shared_material']=material.get_path_name();report['shared_textures']=[base.get_path_name(),rm.get_path_name()]
        with unreal.ScopedSlowTask(len(manifest['assets']),'Importing Pirate Outpost GLBs') as progress:
            progress.make_dialog(True)
            for a in manifest['assets']:
                if progress.should_cancel():report['status']='cancelled';break
                progress.enter_progress_frame(1,a['id'])
                try:
                    mesh,status=import_mesh(a['id'],pack_file(root,a['file']),dest+'/Meshes/'+a['category'],uniform)
                    actual=check_bounds(mesh,a['bounds_m_source'],calibration)
                    collision_status='unchanged_existing'
                    if status!='skipped_existing':
                        mesh.set_material(0,material);collision_status=collision(mesh,a['collision']);eal.set_metadata_tag(mesh,READY_KEY,'1');save(mesh)
                    report['assets'][a['id']]={'status':status,'path':mesh.get_path_name(),'bounds_cm':actual,'collision':collision_status}
                except Exception as exc:
                    report['assets'][a['id']]={'status':'failed','error':str(exc)};unreal.log_error('[PirateOutpost] '+a['id']+': '+str(exc))
                write_report()
        if report['status']=='running':report['status']='failed' if any(a['status']=='failed' for a in report['assets'].values()) else 'complete'
    except Exception as exc:
        report['status']='failed';report['fatal_error']=str(exc);report['traceback']=traceback.format_exc();unreal.log_error('[PirateOutpost] '+str(exc))
        raise
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat();write_report()
    unreal.log('[PirateOutpost] '+report['status']+' — report: '+str(report_path))
    if report['status']!='complete':raise RuntimeError('Import was not complete. Read reports/ue_import_report.json; successful assets were retained.')
    return report

if __name__=='__main__':run()
