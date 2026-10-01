"""GLB-only module exports and an append-only assembled preview."""
from pathlib import Path
from collections import defaultdict
import copy
import numpy as np
from export_glb import Writer,make_tangents
from glb_io import read_glb

def add_materials(w,textures):
    tx=[w.image(Path(textures)/f'HOPPER_Arms_{kind}_2K.png',f'HOPPER Arms {kind} 2048') for kind in ['BaseColor','ORM','Normal']]
    ids={}
    for kind in ['Paint','Metal','Rubber']:
        ids[kind]=len(w.g['materials']);w.g['materials'].append({'name':'HOPPER_Arms_'+kind,
           'pbrMetallicRoughness':{'baseColorTexture':{'index':tx[0]},'metallicRoughnessTexture':{'index':tx[1]},'metallicFactor':1.,'roughnessFactor':1.},
           'normalTexture':{'index':tx[2],'scale':.8},'occlusionTexture':{'index':tx[1],'strength':.65}})
    return ids

def add_scene(w,s,mats):
    noff=len(w.g['nodes'])
    for original in s.nodes:
        n=copy.deepcopy(original)
        if 'children' in n:n['children']=[i+noff for i in n['children']]
        w.g['nodes'].append(n)
    groups=defaultdict(lambda:defaultdict(list))
    for p in s.patches:groups[p.node][p.material].append(p)
    for ni,bymat in groups.items():
        prims=[]
        for mat,patches in bymat.items():
            points=[];normals=[];uvs=[];faces=[];off=0;index_off=0;ranges=[]
            for p in patches:
                points.append(p.positions);normals.append(p.normals);uvs.append(p.uv);faces.append(p.faces+off)
                ranges.append({'name':p.name,'category':p.category,'index_offset':index_off,'index_count':len(p.faces)*3,'vertex_offset':off,'vertex_count':len(p.positions)})
                off+=len(p.positions);index_off+=len(p.faces)*3
            pp=np.concatenate(points).astype('float32');nn=np.concatenate(normals).astype('float32');uv=np.concatenate(uvs).astype('float32')
            ff=np.concatenate(faces).ravel().astype('uint16' if len(pp)<65536 else 'uint32')
            prims.append({'attributes':{'POSITION':w.accessor(pp,'VEC3',34962,True),'NORMAL':w.accessor(nn,'VEC3',34962),
                                       'TEXCOORD_0':w.accessor(uv,'VEC2',34962),'TANGENT':w.accessor(make_tangents(pp,nn,uv,ff),'VEC4',34962)},
                          'indices':w.accessor(ff,'SCALAR',34963),'material':mats[mat],'extras':{'scope':'independent_arm_module','patch_ranges':ranges}})
        w.g['nodes'][noff+ni]['mesh']=len(w.g['meshes']);w.g['meshes'].append({'name':s.nodes[ni]['name'],'primitives':prims})
    return noff

def export_modules(scenes,spec,root):
    root=Path(root)
    for side,s in scenes.items():
        w=Writer();m=add_materials(w,root/'textures');no=add_scene(w,s,m)
        w.g['asset']['generator']='HOPPER detachable arm module v5';w.g.pop('animations',None)
        w.g['scenes']=[{'name':f'HOPPER independent {side} arm / H03-M1','nodes':[no]}]
        w.save(root/f'models/HOPPER_03_Arm_{side}_M1.glb')
    bg,bb=read_glb(root/'reference/HOPPER_03_Legs_v4.glb')
    w=Writer();w.g=copy.deepcopy(bg);w.bin=bytearray(bb[:bg['buffers'][0]['byteLength']]);m=add_materials(w,root/'textures')
    roots=[]
    for side,s in scenes.items():
        no=add_scene(w,s,m);mount=spec['sockets'][side]['scene_mount'];n=w.g['nodes'][no]
        n['translation']=mount['translation'];n['rotation']=mount['rotation_xyzw'];n['scale']=mount['scale'];roots.append(no)
    w.g['scenes'][0]['nodes']+=roots;w.g['scenes'][0]['name']='Fit check only / source base + independent arm instances'
    w.g['asset']['generator']='HOPPER arm module fit check / append-only base preservation'
    w.save(root/'preview/FitCheck.glb')
    return {'base_nodes':len(bg['nodes']),'base_meshes':len(bg['meshes']),'base_accessors':len(bg['accessors']),
            'base_binary_prefix_bytes':bg['buffers'][0]['byteLength'],'arm_scene_roots':roots}
