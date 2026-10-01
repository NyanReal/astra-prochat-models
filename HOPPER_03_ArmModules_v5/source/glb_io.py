"""GLB byte reader, accessors, world transforms and measured triangle/bounds helpers."""
import json,struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

DT={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}

def read_glb(path):
    data=Path(path).read_bytes()
    magic,version,size=struct.unpack_from('<III',data,0)
    if magic!=0x46546c67 or version!=2 or size!=len(data):raise ValueError('Invalid GLB 2.0 header')
    offset=12;g=None;binary=None
    while offset<len(data):
        length,kind=struct.unpack_from('<II',data,offset);offset+=8
        if kind==0x4e4f534a:g=json.loads(data[offset:offset+length])
        if kind==0x004e4942:binary=data[offset:offset+length]
        offset+=length
    if g is None or binary is None:raise ValueError('GLB must contain JSON and BIN chunks')
    return g,binary

def accessor(g,binary,index):
    a=g['accessors'][index];v=g['bufferViews'][a['bufferView']];dtype=np.dtype(DT[a['componentType']]);nc=NC[a['type']]
    off=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',nc*dtype.itemsize)
    return np.ndarray((a['count'],nc),dtype=dtype,buffer=binary,offset=off,strides=(stride,dtype.itemsize)).copy()

def world_matrices(g,overrides=None):
    out={};overrides=overrides or {}
    def visit(i,parent):
        n=g['nodes'][i]
        if 'matrix' in n:m=np.array(n['matrix']).reshape(4,4).T
        else:
            t=overrides.get((i,'translation'),n.get('translation',[0,0,0]));r=overrides.get((i,'rotation'),n.get('rotation',[0,0,0,1]));s=overrides.get((i,'scale'),n.get('scale',[1,1,1]))
            m=np.eye(4);m[:3,:3]=Rotation.from_quat(r).as_matrix()@np.diag(s);m[:3,3]=t
        w=parent@m;out[i]=w
        for child in n.get('children',[]):visit(child,w)
    for i in g['scenes'][g.get('scene',0)]['nodes']:visit(i,np.eye(4))
    return out

def bounds(g,binary,node_filter=None):
    mats=world_matrices(g);pts=[]
    for i,n in enumerate(g['nodes']):
        if 'mesh' not in n or i not in mats or (node_filter and not node_filter(n)):continue
        for p in g['meshes'][n['mesh']]['primitives']:
            a=accessor(g,binary,p['attributes']['POSITION']);m=mats[i];pts.append(a@m[:3,:3].T+m[:3,3])
    p=np.concatenate(pts)
    return np.array([p.min(0),p.max(0)])

def triangles(g):
    return sum(g['accessors'][p['indices']]['count']//3 for n in g['nodes'] if 'mesh' in n for p in g['meshes'][n['mesh']]['primitives'])
