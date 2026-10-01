"""Connector dimensions measured from the delivered v4 GLB, not a guessed node pivot."""
from pathlib import Path
import hashlib
import numpy as np
from scipy.spatial.transform import Rotation
from glb_io import read_glb,accessor,world_matrices,triangles

def measure(base_path):
    base_path=Path(base_path);g,b=read_glb(base_path);wm=world_matrices(g)
    scale=float(np.linalg.norm(wm[0][:3,0]))
    spec={'standard':'H03-M1','revision':1,'scope':'Project-specific virtual arm connector; not an industrial standard.',
          'source_file':base_path.name,'source_sha256':hashlib.sha256(base_path.read_bytes()).hexdigest(),
          'base_triangles':triangles(g),'units':'meters','base_axes':{'up':'+Y','forward':'+Z','positive_side':'Socket_R'},
          'module_axes':{'outward':'+Z','index_up':'+Y','tangent':'+X'},'source_authoring_scale':scale,
          'origin':'Center of foremost existing shoulder drive-cap plane; female sleeve extends inward.',
          'existing_interface_m':{'lip_max_outer_diameter':.700*scale,'housing_max_diameter':.770*scale,'front_cap_diameter':.176*scale,
                                'bolt_circle_diameter':.624*scale,'bolt_count':6,'bolt_angle_step_degrees':60},
          'module_interface_m':{'register_inner_diameter':.322,'register_mouth_outer_diameter':.356,'maximum_coupler_diameter':.376,
                               'inboard_sleeve_depth':.046,'minimum_cup_floor_clearance_to_existing_cap':.014,
                               'radial_register_clearance':.161-.350*scale},'sockets':{}}
    for side,sign in [('L',-1),('R',1)]:
        i=next(i for i,n in enumerate(g['nodes']) if n['name']=='Socket_'+side);parts=[]
        for p in g['meshes'][g['nodes'][i]['mesh']]['primitives']:
            a=accessor(g,b,p['attributes']['POSITION']);parts.append(a@wm[i][:3,:3].T+wm[i][:3,3])
        v=np.concatenate(parts);out=sign*v[:,0];plane=out.max();cap=v[np.abs(out-plane)<1e-6]
        yz=(cap[:,1:].min(0)+cap[:,1:].max(0))*.5;origin=np.r_[sign*plane,yz]
        q=Rotation.from_euler('y',sign*90,degrees=True).as_quat();mount=np.eye(4);mount[:3,:3]=Rotation.from_quat(q).as_matrix();mount[:3,3]=origin
        under=np.linalg.inv(wm[i])@mount;ss=np.linalg.norm(under[:3,:3],axis=0);rr=Rotation.from_matrix(under[:3,:3]/ss).as_quat()
        spec['sockets'][side]={'source_node':g['nodes'][i]['name'],'source_node_index':i,'module_file':f'HOPPER_03_Arm_{side}_M1.glb',
          'root_node':f'Arm_{side}_M1_Root','scene_mount':{'translation':origin.tolist(),'rotation_xyzw':q.tolist(),'scale':[1,1,1]},
          'under_source_socket_node':{'translation':under[:3,3].tolist(),'rotation_xyzw':rr.tolist(),'scale':ss.tolist()},
          'existing_socket_world_matrix_column_major':wm[i].T.reshape(-1).tolist(),'tip_plane_vertex_count':len(cap),
          'cap_diameter_measured_m':np.ptp(cap[:,1:],axis=0).tolist(),
          'label_convention':'Preserves source Socket_R=+X / Socket_L=-X, not screen left/right.'}
    return spec
