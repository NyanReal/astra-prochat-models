"""UE 5.7 editor-only material construction. Called by import_atv_ue57.py.
Official APIs: MaterialEditingLibrary, MaterialFactoryNew,
MaterialInstanceConstantFactoryNew, MaterialExpressionTextureSampleParameter2D.
No normal map is used: the asset uses actual bevel/curved geometry + painted color.
ORM channels: R=AO, G=roughness, B=metallic; this map MUST have sRGB disabled.
"""
from __future__ import annotations
import unreal

MEL=unreal.MaterialEditingLibrary
EAL=unreal.EditorAssetLibrary


def _create_or_load(name,folder,cls,factory):
    path=f'{folder}/{name}'
    obj=EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if obj is not None:
        if not isinstance(obj,cls):raise TypeError(f'Asset has wrong class: {path}')
        return obj
    obj=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,cls,factory)
    if obj is None:raise RuntimeError('Asset creation failed: '+path)
    return obj


def create_materials(folder,base_color,orm,emissive,rebuild=False):
    EAL.make_directory(folder)
    material_path=f'{folder}/M_ATV_UniqueAtlas'
    existed=EAL.does_asset_exist(material_path)
    material=_create_or_load('M_ATV_UniqueAtlas',folder,unreal.Material,unreal.MaterialFactoryNew())
    if existed and not rebuild:
        raise RuntimeError(f'{material_path} already exists. Set REPLACE_EXISTING=True to rebuild this asset.')
    MEL.delete_all_material_expressions(material)
    material.set_editor_property('two_sided',False)
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_OPAQUE)
    def expression(cls,x,y):
        node=MEL.create_material_expression(material,cls,x,y)
        if node is None:raise RuntimeError('Could not create expression '+str(cls))
        return node
    def link(a,out,b,input_name):
        if not MEL.connect_material_expressions(a,out,b,input_name):
            raise RuntimeError(f'Material connection failed: {a.get_name()}.{out} -> {b.get_name()}.{input_name}')
    def output(node,pin,prop):
        if not MEL.connect_material_property(node,pin,prop):raise RuntimeError('Material output connection failed: '+str(prop))
    def tex(parameter,texture,x,y,sampler):
        node=expression(unreal.MaterialExpressionTextureSampleParameter2D,x,y)
        node.set_editor_property('parameter_name',parameter);node.set_editor_property('texture',texture)
        node.set_editor_property('sampler_type',sampler);node.set_editor_property('const_coordinate',0)
        return node
    def scalar(name,value,x,y):
        node=expression(unreal.MaterialExpressionScalarParameter,x,y)
        node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value)
        return node
    base=tex('BaseColor',base_color,-780,-260,unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    packed=tex('ORM',orm,-780,100,unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    glow=tex('Emissive',emissive,-780,490,unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    tint=expression(unreal.MaterialExpressionVectorParameter,-780,-500)
    tint.set_editor_property('parameter_name','BaseColorTint');tint.set_editor_property('default_value',unreal.LinearColor(1,1,1,1))
    tint_mul=expression(unreal.MaterialExpressionMultiply,-390,-260)
    link(base,'RGB',tint_mul,'A');link(tint,'RGB',tint_mul,'B');output(tint_mul,'',unreal.MaterialProperty.MP_BASE_COLOR)
    output(packed,'G',unreal.MaterialProperty.MP_ROUGHNESS)
    output(packed,'B',unreal.MaterialProperty.MP_METALLIC)
    # lerp(1, AO, AO_Strength) is compatible with the GLB's 0.65 AO strength.
    one=expression(unreal.MaterialExpressionConstant,-510,70);one.set_editor_property('r',1.)
    ao_strength=scalar('AO_Strength',.65,-520,310)
    lerp=expression(unreal.MaterialExpressionLinearInterpolate,-220,130)
    link(one,'',lerp,'A');link(packed,'R',lerp,'B');link(ao_strength,'',lerp,'Alpha')
    output(lerp,'',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    emission_strength=scalar('Emissive_Strength',.55,-510,690)
    em_mul=expression(unreal.MaterialExpressionMultiply,-220,510)
    link(glow,'RGB',em_mul,'A');link(emission_strength,'',em_mul,'B')
    output(em_mul,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    spec=scalar('Specular',.35,-220,-70);output(spec,'',unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(material)
    instance=_create_or_load('MI_ATV_Default',folder,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(instance,material)
    for name,texture in [('BaseColor',base_color),('ORM',orm),('Emissive',emissive)]:
        if not MEL.set_material_instance_texture_parameter_value(instance,name,texture):
            raise RuntimeError('Failed to set instance texture '+name)
    MEL.set_material_instance_scalar_parameter_value(instance,'AO_Strength',.65)
    MEL.set_material_instance_scalar_parameter_value(instance,'Emissive_Strength',.55)
    MEL.update_material_instance(instance)
    EAL.save_loaded_asset(material,False);EAL.save_loaded_asset(instance,False)
    return material,instance
