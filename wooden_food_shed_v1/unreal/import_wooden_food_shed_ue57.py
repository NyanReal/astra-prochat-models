"""Unreal Engine 5.7 EDITOR Python: import GLB, build PBR material and instance.

Enable Python Editor Script Plugin, Editor Scripting Utilities, Interchange
Editor and Interchange Framework. Use Tools > Execute Python Script.
Not for a packaged game's runtime. Editor execution has NOT been verified
in this delivery environment; API names were checked against Epic's 5.7 docs.

The destination folder is dedicated to this asset. Existing assets are not
replaced unless REPLACE_EXISTING is explicitly set True. No level is modified.
"""
from __future__ import annotations
import json
from pathlib import Path
import unreal

ASSET_ROOT = ""  # Normally auto-resolved; set only when pasting this script.
DESTINATION = '/Game/Generated/WoodenFoodShed_v1'
REPLACE_EXISTING = False
IMPORT_CLOSED_VARIANT = True
# none: decorative only. box: blocks the entire shed, including its doorway.
# complex: accurate static-mesh collision; do not use for simulated physics.
COLLISION_MODE = 'box'
# Default is dynamic/Lumen-friendly; no reliance on a low-resolution lightmap.
GENERATE_LIGHTMAP_UV = False
MAX_TEXTURE_SIZE = 4096


def log(text: str):
    unreal.log('[WoodenFoodShed] ' + text)


def fail(text: str):
    raise RuntimeError('[WoodenFoodShed] ' + text)


def source_root() -> Path:
    if ASSET_ROOT:
        return Path(ASSET_ROOT).expanduser().resolve()
    filename = globals().get('__file__')
    if filename:
        return Path(filename).resolve().parents[1]
    fail('Set ASSET_ROOT, or run the supplied .py file through Execute Python Script.')


def require_environment(root: Path):
    for name in ['AssetImportTask', 'AssetToolsHelpers', 'EditorAssetLibrary',
                 'MaterialEditingLibrary', 'InterchangeManager', 'StaticMeshEditorSubsystem']:
        if not hasattr(unreal, name):
            fail(f'Missing unreal.{name}. Enable the plugins listed in the README and restart the editor.')
    for rel in ['models/wooden_food_shed.glb', 'textures/T_Shed_BaseColor.png',
                'textures/T_Shed_Normal_DX.png', 'textures/T_Shed_ORM.png',
                'textures/T_Shed_Emissive.png', 'validation/asset_stats.json']:
        if not (root / rel).is_file():
            fail(f'Missing input file: {root / rel}')
    if not DESTINATION.startswith('/Game/'):
        fail('DESTINATION must be a project content path beginning with /Game/.')
    existing = (unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True, include_folder=False)
                if unreal.EditorAssetLibrary.does_directory_exist(DESTINATION) else [])
    if existing and not REPLACE_EXISTING:
        fail('Destination already contains assets. Choose a new DESTINATION or explicitly enable REPLACE_EXISTING. Nothing was overwritten.')


def import_file(path: Path, destination: str):
    if not path.is_file():
        fail(f'Import source does not exist: {path}')
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(path))
    task.set_editor_property('destination_path', destination)
    # Interchange ignores destination_name; never assume a generated mesh name.
    task.set_editor_property('automated', True)
    task.set_editor_property('async_', False)
    task.set_editor_property('replace_existing', REPLACE_EXISTING)
    task.set_editor_property('replace_existing_settings', REPLACE_EXISTING)
    task.set_editor_property('save', True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())  # documented blocking result retrieval
    for asset_path in task.get_editor_property('imported_object_paths'):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is not None and asset not in objects:
            objects.append(asset)
    if not objects:
        fail(f'No assets returned for {path.name}. Check the Output Log and the project Interchange pipeline. GLB requires a supported glTF pipeline.')
    return objects


def import_texture(root: Path, name: str, kind: str):
    objects = import_file(root / 'textures' / (name + '.png'), DESTINATION + '/Textures')
    textures = [o for o in objects if isinstance(o, unreal.Texture2D)]
    if len(textures) != 1:
        fail(f'Expected one Texture2D for {name}, got {len(textures)}.')
    texture = textures[0]
    texture.set_editor_property('srgb', kind in ('color', 'emissive'))
    if kind == 'normal':
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        # This script imports the pre-flipped DirectX file. Do NOT flip twice.
        texture.set_editor_property('flip_green_channel', False)
        texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
    elif kind == 'orm':
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    else:
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
    texture.set_editor_property('max_texture_size', MAX_TEXTURE_SIZE)
    texture.set_editor_property('never_stream', False)
    texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    unreal.EditorAssetLibrary.save_loaded_asset(texture)
    return texture


def get_or_create(name, cls, factory):
    path = DESTINATION + '/Materials/' + name
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is not None:
        if not REPLACE_EXISTING:
            fail('Material already exists: ' + path)
        if not isinstance(asset, cls):
            fail('An existing asset has the wrong type: ' + path)
        return asset
    obj = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, DESTINATION + '/Materials', cls, factory)
    if obj is None:
        fail('Could not create asset: ' + path)
    return obj


def create_material(textures):
    mel = unreal.MaterialEditingLibrary
    mat = get_or_create('M_WoodenFoodShed', unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided', False)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)

    def node(cls, x, y):
        obj = mel.create_material_expression(mat, cls, x, y)
        if obj is None:
            fail('Cannot create material node ' + cls.__name__)
        return obj

    def connect(a, output, b, input_name):
        if not mel.connect_material_expressions(a, output, b, input_name):
            fail(f'Material connection failed: {output} -> {input_name}')

    def output(a, pin, prop):
        if not mel.connect_material_property(a, pin, prop):
            fail('Material property connection failed: ' + str(prop))

    def scalar(name, value, x, y):
        obj = node(unreal.MaterialExpressionScalarParameter, x, y)
        obj.set_editor_property('parameter_name', name)
        obj.set_editor_property('default_value', value)
        obj.set_editor_property('group', 'Shed Controls')
        return obj

    def sample(name, texture, sampler, x, y):
        obj = node(unreal.MaterialExpressionTextureSampleParameter2D, x, y)
        obj.set_editor_property('parameter_name', name)
        obj.set_editor_property('texture', texture)
        obj.set_editor_property('sampler_type', sampler)
        obj.set_editor_property('const_coordinate', 0)
        obj.set_editor_property('group', 'Unique Atlas')
        return obj

    color = sample('BaseColor', textures['base'], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -1000, -500)
    normal = sample('Normal', textures['normal'], unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -1000, -120)
    orm = sample('ORM', textures['orm'], unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, -1000, 240)
    emissive = sample('Emissive', textures['emissive'], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -1000, 660)
    tint = node(unreal.MaterialExpressionVectorParameter, -760, -690)
    tint.set_editor_property('parameter_name', 'BaseColorTint')
    tint.set_editor_property('default_value', unreal.LinearColor(1., 1., 1., 1.))
    multiply = node(unreal.MaterialExpressionMultiply, -420, -470)
    connect(color, 'RGB', multiply, 'A'); connect(tint, 'RGB', multiply, 'B')
    output(multiply, '', unreal.MaterialProperty.MP_BASE_COLOR)

    # Blend the decoded tangent-space normal toward (0,0,1), then normalize.
    flat = node(unreal.MaterialExpressionConstant3Vector, -750, -260)
    flat.set_editor_property('constant', unreal.LinearColor(0., 0., 1., 1.))
    strength = scalar('NormalStrength', .55, -720, 40)
    lerp = node(unreal.MaterialExpressionLinearInterpolate, -410, -110)
    connect(flat, '', lerp, 'A'); connect(normal, 'RGB', lerp, 'B'); connect(strength, '', lerp, 'Alpha')
    normalize = node(unreal.MaterialExpressionNormalize, -160, -110)
    connect(lerp, '', normalize, '')
    output(normalize, '', unreal.MaterialProperty.MP_NORMAL)

    for pin, parameter, prop, y in [
        ('G', 'RoughnessScale', unreal.MaterialProperty.MP_ROUGHNESS, 250),
        ('B', 'MetallicScale', unreal.MaterialProperty.MP_METALLIC, 430),
    ]:
        value = scalar(parameter, 1., -730, y + 100)
        mul = node(unreal.MaterialExpressionMultiply, -400, y)
        connect(orm, pin, mul, 'A'); connect(value, '', mul, 'B'); output(mul, '', prop)
    output(orm, 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    power = scalar('EmissiveStrength', 2.3, -740, 850)
    mul = node(unreal.MaterialExpressionMultiply, -390, 700)
    connect(emissive, 'RGB', mul, 'A'); connect(power, '', mul, 'B')
    output(mul, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    spec = scalar('SpecularLevel', .35, -140, 500)
    output(spec, '', unreal.MaterialProperty.MP_SPECULAR)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    instance = get_or_create('MI_WoodenFoodShed', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(instance, mat)
    mel.update_material_instance(instance)
    unreal.EditorAssetLibrary.save_loaded_asset(instance)
    return mat, instance


def configure_mesh(mesh, instance, expected_triangles):
    mesh.set_material(0, instance)
    editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    options = editor.get_lod_build_settings(mesh, 0)
    options.set_editor_property('recompute_normals', False)
    # Recompute tangents from the actual imported UVs to avoid importer convention differences.
    options.set_editor_property('recompute_tangents', True)
    options.set_editor_property('use_mikk_t_space', True)
    options.set_editor_property('use_full_precision_u_vs', True)
    options.set_editor_property('generate_lightmap_u_vs', GENERATE_LIGHTMAP_UV)
    if GENERATE_LIGHTMAP_UV:
        options.set_editor_property('src_lightmap_index', 0)
        options.set_editor_property('dst_lightmap_index', 1)
        options.set_editor_property('min_lightmap_resolution', 512)
        mesh.set_editor_property('light_map_coordinate_index', 1)
        mesh.set_editor_property('light_map_resolution', 512)
    editor.set_lod_build_settings(mesh, 0, options)
    nanite = editor.get_nanite_settings(mesh)
    nanite.set_editor_property('enabled', False)
    editor.set_nanite_settings(mesh, nanite, True)
    if COLLISION_MODE == 'box':
        editor.remove_collisions(mesh)
        result = editor.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        if result < 0:
            fail('Simple collision generation failed for ' + mesh.get_name())
        unreal.log_warning('[WoodenFoodShed] Box collision blocks the open doorway. Use custom collision or complex mode for enterable buildings.')
    elif COLLISION_MODE == 'complex':
        editor.remove_collisions(mesh)
        body = mesh.get_editor_property('body_setup')
        body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    elif COLLISION_MODE == 'none':
        editor.remove_collisions(mesh)
    else:
        fail('COLLISION_MODE must be box, complex or none.')
    triangle_count = mesh.get_num_triangles(0)
    if triangle_count >= 4000:
        fail(f'Imported mesh exceeds the budget: {triangle_count} triangles.')
    if triangle_count != expected_triangles:
        unreal.log_warning(f'[WoodenFoodShed] Source has {expected_triangles} triangles, imported render data has {triangle_count}. Inspect importer welding/removal settings.')
    bounds = mesh.get_bounds()
    height_cm = float(bounds.box_extent.z) * 2.0
    if not 315.0 < height_cm < 345.0:
        fail(f'Unexpected imported height {height_cm:.2f} cm. Expected about 328 cm. Inspect the glTF coordinate/unit pipeline; do not blindly apply another 100x scale.')
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    return {'asset': mesh.get_path_name(), 'triangles': triangle_count, 'height_cm': height_cm,
            'sections': mesh.get_num_sections(0), 'material': instance.get_path_name()}


def main():
    root = source_root(); require_environment(root)
    log('Starting explicit asset import. No level actors will be created.')
    textures = {
        'base': import_texture(root, 'T_Shed_BaseColor', 'color'),
        'normal': import_texture(root, 'T_Shed_Normal_DX', 'normal'),
        'orm': import_texture(root, 'T_Shed_ORM', 'orm'),
        'emissive': import_texture(root, 'T_Shed_Emissive', 'emissive'),
    }
    _, instance = create_material(textures)
    expected = json.loads((root / 'validation/asset_stats.json').read_text())['triangles']
    files = [('wooden_food_shed.glb', 'Open')]
    if IMPORT_CLOSED_VARIANT:
        files.append(('wooden_food_shed_closed.glb', 'Closed'))
    report = []
    for filename, folder in files:
        objects = import_file(root / 'models' / filename, DESTINATION + '/Meshes/' + folder)
        meshes = [obj for obj in objects if isinstance(obj, unreal.StaticMesh)]
        if len(meshes) != 1:
            fail(f'Expected one merged StaticMesh for {filename}, got {len(meshes)}. Inspect the Interchange pipeline.')
        report.append(configure_mesh(meshes[0], instance, expected))
    log('Import and configuration finished. Results: ' + json.dumps(report))
    try:
        (root / 'validation/ue57_runtime_report.json').write_text(
            json.dumps({'engine': unreal.SystemLibrary.get_engine_version(), 'results': report}, indent=2), encoding='utf-8')
    except OSError as exc:
        unreal.log_warning('[WoodenFoodShed] Could not write local runtime report: ' + str(exc))
    return report

if __name__ == '__main__':
    main()
