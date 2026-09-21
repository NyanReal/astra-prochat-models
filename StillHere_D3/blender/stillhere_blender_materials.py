"""Blender material setup. Runs inside Blender; no external Python packages needed."""
from pathlib import Path
import bpy


def _socket(node,*names):
    for name in names:
        if name in node.inputs:return node.inputs[name]
    return None


def make_material(asset,root):
    mat=bpy.data.materials.new('SH_M_'+asset['id']);mat.use_nodes=True;mat.use_backface_culling=False
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    out=nodes.new('ShaderNodeOutputMaterial');out.location=(700,0)
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');bsdf.location=(420,0);links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    tex={}
    for j,(key,noncolor) in enumerate([('base_color',False),('normal',True),('orm',True)]):
        node=nodes.new('ShaderNodeTexImage');node.location=(-650,260-j*260)
        node.image=bpy.data.images.load(str(root/asset[key]),check_existing=True)
        if noncolor:node.image.colorspace_settings.name='Non-Color'
        node.extension='EXTEND';node.interpolation='Linear';tex[key]=node
    links.new(tex['base_color'].outputs['Color'],bsdf.inputs['Base Color'])
    sep=nodes.new('ShaderNodeSeparateColor');sep.mode='RGB';sep.location=(-330,-310);links.new(tex['orm'].outputs['Color'],sep.inputs[0])
    links.new(sep.outputs['Green'],bsdf.inputs['Roughness']);links.new(sep.outputs['Blue'],bsdf.inputs['Metallic'])
    nm=nodes.new('ShaderNodeNormalMap');nm.location=(-50,-130);nm.inputs['Strength'].default_value=.6
    links.new(tex['normal'].outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
    refine_material(mat,asset)
    return mat


def refine_material(mat,asset):
    if not mat or not mat.use_nodes:return
    mat.use_backface_culling=False
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bsdf=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
    if bsdf is None:return
    st=asset['surface_type'];category=asset['category']
    if category in ('trees','shrubs','vines','groundcover'):
        sub=_socket(bsdf,'Subsurface Weight','Subsurface')
        if sub:sub.default_value=.055
    if st in ('water','waterfall'):
        rough=_socket(bsdf,'Roughness')
        for link in list(rough.links):links.remove(link)
        rough.default_value=.19 if st=='water' else .28
        ior=_socket(bsdf,'IOR')
        if ior:ior.default_value=1.333
        geom=nodes.new('ShaderNodeNewGeometry');geom.location=(-700,-800)
        noise=nodes.new('ShaderNodeTexNoise');noise.noise_dimensions='4D';noise.location=(-400,-800)
        noise.inputs['Scale'].default_value=2.6 if st=='water' else 3.2
        noise.inputs['Detail'].default_value=2.;noise.inputs['Roughness'].default_value=.55
        links.new(geom.outputs['Position'],noise.inputs['Vector'])
        noise.inputs['W'].driver_add('default_value').driver.expression='frame / 85.0'
        bump=nodes.new('ShaderNodeBump');bump.location=(140,-460)
        bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.028
        old=list(bsdf.inputs['Normal'].links)
        if old:
            source=old[0].from_socket;links.remove(old[0]);links.new(source,bump.inputs['Normal'])
        links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
        emission=_socket(bsdf,'Emission Color','Emission');strength=_socket(bsdf,'Emission Strength')
        bc=list(bsdf.inputs['Base Color'].links)
        if emission and bc:links.new(bc[0].from_socket,emission)
        if strength:strength.default_value=.065
    if st=='foam':
        strength=_socket(bsdf,'Emission Strength');emission=_socket(bsdf,'Emission Color','Emission')
        if emission:emission.default_value=(.34,.48,.48,1)
        if strength:strength.default_value=.18
    # Pack only the images belonging to this newly created/imported material.
    for node in nodes:
        if node.type=='TEX_IMAGE' and node.image and not node.image.packed_file:
            try:node.image.pack()
            except RuntimeError:pass
    mat['stillhere_asset_id']=asset['id'];mat['surface_type']=st
