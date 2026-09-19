"""UE 5.7 Editor Python: create eight explicit materials from AI atlas.
Called by ue57_import.py; safe on repeat runs, confined to /Game/ATV_Trail.
"""
import unreal

SURFACES = [
    ('Teal_Panels', .62), ('Ivory_Body', .57), ('Rubber_Tires', .91),
    ('Graphite_Seat', .84), ('Steel_Racks', .72), ('Amber_Accents', .47),
    ('Headlamps', .28), ('Chassis', .84),
]

def build_materials(texture, destination='/Game/ATV_Trail'):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    lib = unreal.MaterialEditingLibrary
    result = {}
    for name, roughness in SURFACES:
        asset_name = 'M_ATV_' + name
        asset_path = destination + '/' + asset_name
        material = unreal.load_asset(asset_path)
        if material is None:
            material = tools.create_asset(asset_name, destination, unreal.Material, unreal.MaterialFactoryNew())
        if not isinstance(material, unreal.Material):
            raise TypeError('Expected Material at ' + asset_path)
        lib.delete_all_material_expressions(material)
        sample = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -500, -100)
        sample.set_editor_property('parameter_name', 'BaseColorAtlas')
        sample.set_editor_property('texture', texture)
        sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        assert lib.connect_material_property(sample, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
        scalar = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, 150)
        scalar.set_editor_property('parameter_name', 'Roughness')
        scalar.set_editor_property('default_value', roughness)
        assert lib.connect_material_property(scalar, '', unreal.MaterialProperty.MP_ROUGHNESS)
        if name == 'Headlamps':
            strength = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, 330)
            strength.set_editor_property('parameter_name', 'LampEmission')
            strength.set_editor_property('default_value', .28)
            multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -200, 250)
            assert lib.connect_material_expressions(sample, 'RGB', multiply, 'A')
            assert lib.connect_material_expressions(strength, '', multiply, 'B')
            assert lib.connect_material_property(multiply, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material)
        result[asset_name] = material
    return result
