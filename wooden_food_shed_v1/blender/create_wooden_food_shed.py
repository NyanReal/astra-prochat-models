"""Rebuild the supplied shed in Blender 4.2+ / 5.x from explicit mesh + UV data.

No GLB importer is used. The JSON is the deterministic, editable generation
payload produced by tools/build_asset.py. Textures and payload must remain
next to this folder. No third-party Python modules are needed inside Blender.

GUI: Scripting > Open this file > Run Script, preferably in a new .blend.
CLI: blender --background --python blender/create_wooden_food_shed.py -- \
       --output ./blender_output --export-glb --save-blend

Editor runtime was unavailable during preparation. Syntax was checked, but
Blender execution is not claimed. The supplied GLBs were built independently.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

# Only necessary when pasting this script into an unnamed Blender text block.
ASSET_ROOT = ""  # e.g. r"D:\Assets\wooden_food_shed_v1"
COLLECTION_NAME = 'WoodenFoodShed_v1'
OPEN_ANGLES = {'Left': -105.0, 'Right': 100.0}


def asset_root() -> Path:
    if ASSET_ROOT:
        return Path(ASSET_ROOT).expanduser().resolve()
    file = globals().get('__file__')
    if file and Path(file).is_file():
        return Path(file).resolve().parents[1]
    space = getattr(bpy.context, 'space_data', None)
    text = getattr(space, 'text', None)
    if text and text.filepath:
        return Path(bpy.path.abspath(text.filepath)).resolve().parents[1]
    raise RuntimeError('Open the supplied .py file from disk, or set ASSET_ROOT at the top.')


def collection(name, parent):
    col = bpy.data.collections.new(name)
    parent.children.link(col)
    return col


def clear_own_collection():
    old = bpy.data.collections.get(COLLECTION_NAME)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for child in list(old.children):
            bpy.data.collections.remove(child)
        bpy.data.collections.remove(old)


def load_image(root: Path, filename: str, color_space: str):
    path = root / 'textures' / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = color_space
    return img


def material(root: Path):
    mat = bpy.data.materials.get('M_WoodenFoodShed_v1') or bpy.data.materials.new('M_WoodenFoodShed_v1')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    output = nt.nodes.new('ShaderNodeOutputMaterial'); output.location = (740, 140)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (410, 150)
    nt.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UV0_Unique'; uv.location = (-940, 180)

    def tex(file, color_space, x, y):
        node = nt.nodes.new('ShaderNodeTexImage')
        node.image = load_image(root, file, color_space)
        node.label = file; node.location = (x, y)
        node.extension = 'EXTEND'; node.interpolation = 'Linear'
        nt.links.new(uv.outputs['UV'], node.inputs['Vector'])
        return node

    base = tex('T_Shed_BaseColor.png', 'sRGB', -680, 490)
    normal = tex('T_Shed_Normal_GL.png', 'Non-Color', -680, 170)
    orm = tex('T_Shed_ORM.png', 'Non-Color', -680, -170)
    emission = tex('T_Shed_Emissive.png', 'sRGB', -680, -470)
    nt.links.new(base.outputs['Color'], bsdf.inputs['Base Color'])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); sep.mode = 'RGB'; sep.location = (-300, -100)
    nt.links.new(orm.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.space = 'TANGENT'; nm.uv_map = 'UV0_Unique'
    nm.inputs['Strength'].default_value = .55; nm.location = (-160, 220)
    nt.links.new(normal.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    emission_socket = 'Emission Color' if 'Emission Color' in bsdf.inputs else 'Emission'
    nt.links.new(emission.outputs['Color'], bsdf.inputs[emission_socket])
    if 'Emission Strength' in bsdf.inputs:
        bsdf.inputs['Emission Strength'].default_value = 2.3
    # The Blender glTF exporter recognizes this optional AO socket.
    group = bpy.data.node_groups.get('glTF Material Output')
    if group is None:
        group = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        group.interface.new_socket(name='Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    ao = nt.nodes.new('ShaderNodeGroup'); ao.node_tree = group; ao.location = (80, -160)
    if 'Occlusion' in ao.inputs:
        nt.links.new(sep.outputs['Red'], ao.inputs['Occlusion'])
    return mat


def build(root: Path, closed: bool = False, preview: bool = True):
    path = root / 'source' / 'mesh_payload.json'
    if not path.is_file():
        raise FileNotFoundError(f'Missing generation payload: {path}')
    data = json.loads(path.read_text(encoding='utf-8'))
    expected = sum(len(o['triangles']) for o in data['objects'])
    if expected >= 4000:
        raise RuntimeError(f'Triangle limit exceeded before generation: {expected}')
    clear_own_collection()
    root_col = collection(COLLECTION_NAME, bpy.context.scene.collection)
    architecture = collection('Shed_Architecture', root_col)
    roof_col = collection('Shed_Roof_HideForCutaway', root_col)
    contents = collection('Shed_Contents', root_col)
    doors = collection('Shed_Doors', root_col)
    mat = material(root)
    pivots = {}
    for side in ('Left', 'Right'):
        p = bpy.data.objects.new(f'DoorHinge_{side}', None)
        p.empty_display_type = 'PLAIN_AXES'; p.empty_display_size = .18
        p.location = (-1.355 if side == 'Left' else 1.355, -1.205, .37)
        p.rotation_euler.z = 0 if closed else math.radians(OPEN_ANGLES[side])
        p['closed_rotation_z_degrees'] = 0.0
        p['default_open_rotation_z_degrees'] = OPEN_ANGLES[side]
        doors.objects.link(p); pivots[side] = p
    generated = []
    for item in data['objects']:
        name = item['name']; vertices = [Vector(v) for v in item['positions']]
        side = name.split('_', 1)[1] if name.startswith(('Door_', 'Handle_')) else None
        if side:
            hinge = pivots[side].location
            inv = Matrix.Rotation(math.radians(-OPEN_ANGLES[side]), 3, 'Z')
            vertices = [inv @ (p - hinge) for p in vertices]
        mesh = bpy.data.meshes.new(name + '_Mesh')
        mesh.from_pydata(vertices, [], item['triangles'])
        mesh.update(calc_edges=True)
        uv = mesh.uv_layers.new(name='UV0_Unique')
        for poly in mesh.polygons:
            poly.use_smooth = False
            for loop in poly.loop_indices:
                uv.data[loop].uv = item['uvs'][mesh.loops[loop].vertex_index]
        # A second non-overlapping UV channel is supplied for editing. For low-res
        # baked lightmaps, repack/generate UV1 in the engine: 4K UV0 padding is not
        # sufficient for a 64/128px lightmap with this many small bevel islands.
        uv1 = mesh.uv_layers.new(name='UV1_LayoutCopy')
        for a, b in zip(uv1.data, uv.data):
            a.uv = b.uv
        mesh.uv_layers.active_index = 0
        obj = bpy.data.objects.new(name, mesh)
        target_col = doors if side else (roof_col if name.startswith('Roof_') else (contents if name.startswith(('Prop_', 'Shelf_')) else architecture))
        target_col.objects.link(obj)
        obj.data.materials.append(mat)
        obj['atlas'] = 'T_Shed_BaseColor / 4096 / unique UV0'
        if side:
            obj.parent = pivots[side]
        generated.append(obj)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.view_layer.update()
    count = sum(len(o.data.polygons) for o in generated)
    if count != expected or count >= 4000:
        raise RuntimeError(f'Generated triangles {count} do not match expected {expected}.')
    if preview:
        add_preview(root_col)
    print(f'WoodenFoodShed rebuilt: {count} triangles, {len(generated)} editable mesh objects.')
    return generated


def add_preview(root_col):
    col = collection('Shed_PreviewOnly_NOT_EXPORTED', root_col)
    scene = bpy.context.scene
    world = bpy.data.worlds.new('Shed_PreviewWorld'); world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .26, .31, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .55
    scene.world = world
    for name, pos, power, size, color in [
        ('Shed_Key', (-3.6, -5.3, 8), 1300, 5, (1., .87, .72)),
        ('Shed_Fill', (5, -2, 7), 600, 5, (.77, .86, 1.)),
        ('Shed_Rim', (-3, 5, 7), 850, 4, (.93, 1., .94)),
    ]:
        lamp = bpy.data.lights.new(name, 'AREA'); lamp.energy = power; lamp.shape = 'DISK'; lamp.size = size; lamp.color = color
        obj = bpy.data.objects.new(name, lamp); col.objects.link(obj); obj.location = pos
        obj.rotation_euler = (Vector((0, 0, 1.3)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    lamp = bpy.data.lights.new('Shed_LanternPreview', 'POINT'); lamp.energy = 20; lamp.color = (1., .40, .10); lamp.shadow_soft_size = .12
    obj = bpy.data.objects.new('Shed_LanternPreview', lamp); col.objects.link(obj); obj.location = (1.47, -1.53, 2.075)
    camera = bpy.data.cameras.new('Shed_Camera'); camera.type = 'ORTHO'; camera.ortho_scale = 6.35
    obj = bpy.data.objects.new('Shed_Camera', camera); col.objects.link(obj); obj.location = (6., -11.5, 5.8)
    obj.rotation_euler = (Vector((.15, -.25, 1.42)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = obj
    scene.render.resolution_x = 1440; scene.render.resolution_y = 1200; scene.render.resolution_percentage = 100
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 64
    scene.view_settings.view_transform = 'AgX'


def export_merged(objects, filepath: Path):
    """Join temporary evaluated copies, leaving editable originals and pivots intact."""
    bpy.ops.object.select_all(action='DESELECT')
    temp = bpy.data.collections.new('Shed_TemporaryExport'); bpy.context.scene.collection.children.link(temp)
    copies = []; joined = None
    try:
        deps = bpy.context.evaluated_depsgraph_get()
        for obj in objects:
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), depsgraph=deps)
            duplicate = bpy.data.objects.new(obj.name + '_Export', mesh)
            duplicate.matrix_world = obj.matrix_world.copy(); temp.objects.link(duplicate)
            duplicate.select_set(True); copies.append(duplicate)
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.join(); joined = bpy.context.view_layer.objects.active
        joined.name = 'SM_WoodenFoodShed'
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        # Collapse duplicated material slots to one slot without changing faces.
        mat = objects[0].data.materials[0]
        joined.data.materials.clear(); joined.data.materials.append(mat)
        for poly in joined.data.polygons: poly.material_index = 0
        if len(joined.data.polygons) >= 4000: raise RuntimeError('Export exceeds triangle budget.')
        bpy.ops.export_scene.gltf(filepath=str(filepath), export_format='GLB', use_selection=True,
                                  export_yup=True, export_texcoords=True, export_normals=True,
                                  export_tangents=True, export_materials='EXPORT', export_animations=False,
                                  export_cameras=False, export_lights=False, export_extras=True)
    finally:
        for obj in list(temp.objects): bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(temp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--closed', action='store_true')
    parser.add_argument('--no-preview', action='store_true')
    parser.add_argument('--export-glb', action='store_true')
    parser.add_argument('--save-blend', action='store_true')
    parser.add_argument('--output', default='')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    root = asset_root(); objects = build(root, args.closed, not args.no_preview)
    output = Path(args.output).resolve() if args.output else root / 'blender_output'
    if args.export_glb or args.save_blend: output.mkdir(parents=True, exist_ok=True)
    if args.export_glb:
        export_merged(objects, output / ('wooden_food_shed_closed.glb' if args.closed else 'wooden_food_shed.glb'))
    if args.save_blend:
        for image in bpy.data.images:
            if image.source == 'FILE' and image.filepath and 'T_Shed_' in image.name: image.pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(output / 'wooden_food_shed.blend'))
    return objects

if __name__ == '__main__':
    main()
