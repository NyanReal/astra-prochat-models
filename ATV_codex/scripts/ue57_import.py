"""Run from UE 5.7: Tools > Execute Python Script.
Enable Python Editor Script Plugin and Editor Scripting Utilities, restart.
Uses the provided FBX companion of the GLB for deterministic centimetre import.
Writes only to /Game/ATV_Trail; does not modify a level or project settings.
"""
import sys, json, importlib.util, hashlib
from datetime import datetime, timezone
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[1]
DEST = '/Game/ATV_Trail'

def import_file(filename, name, options=None):
    path = ROOT / 'assets' / filename
    if not path.is_file(): raise FileNotFoundError(path)
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(path))
    task.set_editor_property('destination_path', DEST)
    task.set_editor_property('destination_name', name)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    if options:
        task.set_editor_property('options', options)
        task.set_editor_property('factory', unreal.FbxFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    loaded = [unreal.load_asset(p) for p in task.get_editor_property('imported_object_paths')]
    return [a for a in loaded if a is not None]

def main():
    # UE 5.7 defaults to Interchange FBX. Use the stable legacy FBX Python options
    # for this import and restore the previous cvar value afterward.
    cvar = 'Interchange.FeatureFlags.Import.FBX'
    previous = unreal.SystemLibrary.get_console_variable_int_value(cvar)
    unreal.SystemLibrary.execute_console_command(None, cvar + ' 0')
    try:
        options = unreal.FbxImportUI()
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_as_skeletal', False)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('automated_import_should_detect_type', False)
        options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
        data = options.get_editor_property('static_mesh_import_data')
        data.set_editor_property('combine_meshes', True)
        data.set_editor_property('generate_lightmap_u_vs', True)
        data.set_editor_property('auto_generate_collision', True)
        data.set_editor_property('convert_scene', True)
        data.set_editor_property('convert_scene_unit', True)
        data.set_editor_property('force_front_x_axis', True)
        data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        meshes = [a for a in import_file('atv.fbx', 'SM_ATV_Trail', options) if isinstance(a, unreal.StaticMesh)]
    finally:
        unreal.SystemLibrary.execute_console_command(None, cvar + ' ' + str(previous))
    if len(meshes) != 1: raise RuntimeError('Expected one imported static mesh, got '+str(len(meshes)))
    textures = [a for a in import_file('atv_basecolor.png', 'T_ATV_BaseColor') if isinstance(a, unreal.Texture2D)]
    if not textures: raise RuntimeError('Base color texture import failed')
    texture = textures[0]
    texture.set_editor_property('srgb', True)
    texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    unreal.EditorAssetLibrary.save_loaded_asset(texture)
    spec = importlib.util.spec_from_file_location('atv_materials', str(ROOT/'scripts'/'ue57_materials.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    materials = module.build_materials(texture, DEST)
    mesh = meshes[0]
    assigned = []
    for i, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = str(slot.get_editor_property('imported_material_slot_name'))
        if name not in materials: name = str(slot.get_editor_property('material_slot_name'))
        if name not in materials: raise RuntimeError('Unexpected material slot: ' + name)
        mesh.set_material(i, materials[name]); assigned.append(name)
    if len(assigned) != 8: raise RuntimeError('Expected eight material slots')
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    bounds = mesh.get_bounds()
    expected=json.loads((ROOT/'assets'/'model-stats.json').read_text())
    if mesh.get_num_triangles(0)!=expected['triangles']: raise RuntimeError('UE triangle count differs from exported mesh')
    if not 50 < bounds.box_extent.x < 200: raise RuntimeError('Unexpected import scale in centimetres')
    report = {'engine': unreal.SystemLibrary.get_engine_version(), 'mesh':mesh.get_path_name(),
              'materialSlots':assigned, 'lod0Triangles':mesh.get_num_triangles(0),
              'boundsExtentCentimetres': [bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z],
              'result':'PASS', 'pipeline':'FBX companion + explicit Python materials',
              'verifiedAt':datetime.now(timezone.utc).isoformat(),
              'inputSHA256':{name:hashlib.sha256((ROOT/'assets'/name).read_bytes()).hexdigest() for name in ['atv.fbx','atv_basecolor.png']},
              'note':'Static mesh only; no vehicle rig, physics driving system, or level changes.'}
    (ROOT/'docs'/'ue57-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('ATV_IMPORT_PASS ' + json.dumps(report))

if __name__ == '__main__': main()
