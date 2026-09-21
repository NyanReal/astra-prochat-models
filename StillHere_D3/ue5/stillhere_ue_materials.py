"""Explicit UE5 material/texture setup for the shipped GLB assets.

The external PNGs are authoritative: BaseColor=sRGB, ORM=linear,
Normal=linear OpenGL tangent-space normal with green-channel flip for Unreal.
"""
from pathlib import Path
import unreal

MEL=unreal.MaterialEditingLibrary
EAL=unreal.EditorAssetLibrary


def set_optional(obj,name,value,warnings):
    try:obj.set_editor_property(name,value);return True
    except Exception as exc:
        warnings.append(f'{obj.get_name() if hasattr(obj,"get_name") else type(obj).__name__}.{name}: {exc}')
        return False


def load_texture(filename,dest,name,role,reimport=False):
    path=f'{dest}/{name}'
    old=EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if old and not reimport:return old
    task=unreal.AssetImportTask();task.filename=str(filename);task.destination_path=dest;task.destination_name=name
    task.automated=True;task.replace_existing=reimport;task.save=True;task.async_=False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects=list(task.get_objects());textures=[o for o in objects if isinstance(o,unreal.Texture2D)]
    tex=next((o for o in textures if o.get_name()==name),textures[0] if textures else None)
    if tex is None:raise RuntimeError('Texture import returned no Texture2D: '+str(filename))
    tex.set_editor_property('srgb',role=='base_color')
    if role=='normal':
        tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif role=='orm':tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
    # No repeat texture addressing: all chart coordinates remain inside the atlas.
    tex.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
    if not EAL.save_loaded_asset(tex,only_if_is_dirty=False):raise RuntimeError('Texture could not be saved: '+tex.get_path_name())
    return tex


def expression(mat,cls,x,y):return MEL.create_material_expression(mat,cls,x,y)

def connect(a,out,b,inp):
    if not MEL.connect_material_expressions(a,out,b,inp):raise RuntimeError(f'Material connection failed: {a.get_name()}.{out} -> {b.get_name()}.{inp}')

def output(a,out,prop):
    if not MEL.connect_material_property(a,out,prop):raise RuntimeError('Material property connection failed: '+str(prop))


def build_material(asset,root,content_root,rebuild=False,warnings=None):
    warnings=[] if warnings is None else warnings
    folder=content_root+'/Materials';name='M_'+asset['id'];path=folder+'/'+name
    if EAL.does_asset_exist(path) and not rebuild:return EAL.load_asset(path)
    if EAL.does_asset_exist(path):
        mat=EAL.load_asset(path);MEL.delete_all_material_expressions(mat)
    else:mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    if mat is None:raise RuntimeError('Material creation failed: '+path)
    mat.set_editor_property('two_sided',bool(asset['double_sided']))
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_OPAQUE)
    samples={}
    for j,(role,suffix,sampler) in enumerate([
        ('base_color','BaseColor',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR),
        ('normal','Normal',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL),
        ('orm','ORM',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)]):
        tex=load_texture(root/asset[role],content_root+'/Textures','T_'+asset['id']+'_'+suffix,role,rebuild)
        node=expression(mat,unreal.MaterialExpressionTextureSample,-650,j*230);node.set_editor_property('texture',tex);node.set_editor_property('sampler_type',sampler);samples[role]=node
    output(samples['base_color'],'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
    output(samples['normal'],'RGB',unreal.MaterialProperty.MP_NORMAL)
    output(samples['orm'],'R',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    output(samples['orm'],'G',unreal.MaterialProperty.MP_ROUGHNESS)
    output(samples['orm'],'B',unreal.MaterialProperty.MP_METALLIC)
    st=asset['surface_type']
    if st=='water':
        # Analytic world-space ripples avoid moving/repeating the uniquely unwrapped colour atlas.
        custom=expression(mat,unreal.MaterialExpressionCustom,-150,420)
        inputs=[]
        for n in ('P','T'):
            inp=unreal.CustomInput();inp.set_editor_property('input_name',n);inputs.append(inp)
        custom.set_editor_property('inputs',inputs)
        custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        custom.set_editor_property('description','World-space flowing water normals; atlas UVs stay fixed')
        custom.set_editor_property('code',
            'float2 p=P.xy*0.01; '
            'float dx=0.13*sin(dot(p,float2(8.2,3.1))+T*1.7)+0.05*sin(dot(p,float2(-5.4,10.7))-T*1.1); '
            'float dy=0.10*cos(dot(p,float2(3.2,9.4))-T*1.2)+0.04*cos(dot(p,float2(11.3,-4.1))+T*0.8); '
            'return normalize(float3(dx,dy,1.0));')
        pos=expression(mat,unreal.MaterialExpressionWorldPosition,-670,780)
        time=expression(mat,unreal.MaterialExpressionTime,-670,920)
        connect(pos,'',custom,'P');connect(time,'',custom,'T')
        mat.set_editor_property('tangent_space_normal',False);output(custom,'',unreal.MaterialProperty.MP_NORMAL)
        rough=expression(mat,unreal.MaterialExpressionConstant,-150,210);rough.set_editor_property('r',.20);output(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    if st in ('water','waterfall','foam'):
        multiply=expression(mat,unreal.MaterialExpressionMultiply,-100,-130);multiply.set_editor_property('const_b',.055 if st!='foam' else .15)
        connect(samples['base_color'],'RGB',multiply,'A');output(multiply,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if asset['category'] in ('trees','shrubs','groundcover','vines'):
        # Opaque, double-sided leaf geometry: no card alpha sorting dependency.
        set_optional(mat,'two_sided',True,warnings)
    MEL.layout_material_expressions(mat);MEL.recompile_material(mat)
    if not EAL.save_loaded_asset(mat,only_if_is_dirty=False):raise RuntimeError('Material could not be saved: '+mat.get_path_name())
    return mat
