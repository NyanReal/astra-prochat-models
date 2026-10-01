"""GLB 2.0 byte writer and tangent-frame generation for rigid arm modules."""
import json, struct
from pathlib import Path
import numpy as np

class Writer:
    def __init__(self):
        self.bin=bytearray()
        self.g={'asset':{'version':'2.0','generator':'HOPPER modular arm authoring toolkit'},'scene':0,
                'scenes':[{'name':'HOPPER 03 arm module','nodes':[0]}], 'nodes':[], 'meshes':[], 'materials':[],'textures':[],'images':[],
                'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071}],
                'accessors':[],'bufferViews':[],'animations':[]}
    def view(self,data,target=None):
        while len(self.bin)%4:self.bin.append(0)
        offset=len(self.bin);self.bin.extend(data)
        v={'buffer':0,'byteOffset':offset,'byteLength':len(data)}
        if target is not None:v['target']=target
        self.g['bufferViews'].append(v);return len(self.g['bufferViews'])-1
    def accessor(self,array,kind='VEC3',target=None,minmax=False):
        a=np.asarray(array)
        if a.dtype.kind=='f':a=np.ascontiguousarray(a,dtype='<f4');ctype=5126
        elif a.dtype.itemsize==2:a=np.ascontiguousarray(a,dtype='<u2');ctype=5123
        else:a=np.ascontiguousarray(a,dtype='<u4');ctype=5125
        ac={'bufferView':self.view(a.tobytes(),target),'componentType':ctype,'count':len(a),'type':kind}
        if minmax:
            ac['min']=np.min(a,axis=0).reshape(-1).astype(float).tolist();ac['max']=np.max(a,axis=0).reshape(-1).astype(float).tolist()
        self.g['accessors'].append(ac);return len(self.g['accessors'])-1
    def image(self,path,name):
        idx=len(self.g['images']);view=self.view(Path(path).read_bytes())
        self.g['images'].append({'name':name,'bufferView':view,'mimeType':'image/png'})
        self.g['textures'].append({'name':name,'source':idx,'sampler':0});return idx
    def save(self,path):
        self.g['buffers']=[{'byteLength':len(self.bin)}]
        j=json.dumps(self.g,separators=(',',':'),ensure_ascii=False).encode('utf8');j+=b' '*((-len(j))%4)
        binary=bytes(self.bin);binary+=b'\0'*((-len(binary))%4)
        data=struct.pack('<III',0x46546c67,2,12+8+len(j)+8+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary
        Path(path).write_bytes(data);return self.g

def make_tangents(p,n,uv,ind):
    faces=ind.reshape(-1,3).astype(int)
    pp=p[faces];uu=uv[faces]
    e1=pp[:,1]-pp[:,0];e2=pp[:,2]-pp[:,0];d1=uu[:,1]-uu[:,0];d2=uu[:,2]-uu[:,0]
    det=d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0]
    inv=np.divide(1.,det,out=np.zeros_like(det),where=np.abs(det)>1e-15)
    tv=(e1*d2[:,1,None]-e2*d1[:,1,None])*inv[:,None]
    bv=(e2*d1[:,0,None]-e1*d2[:,0,None])*inv[:,None]
    t=np.zeros_like(p);b=np.zeros_like(p)
    for i in range(3):np.add.at(t,faces[:,i],tv);np.add.at(b,faces[:,i],bv)
    t-=n*np.sum(n*t,axis=1,keepdims=True)
    lens=np.linalg.norm(t,axis=1)
    bad=lens<1e-8
    if np.any(bad):
        ref=np.tile([1.,0.,0.],(np.sum(bad),1));nb=n[bad];ref[np.abs(nb[:,0])>.8]=[0,0,1]
        t[bad]=np.cross(ref,nb);lens=np.linalg.norm(t,axis=1)
    t/=lens[:,None]
    handed=np.where(np.sum(np.cross(n,t)*b,axis=1)<0,-1.,1.)
    return np.c_[t,handed].astype(np.float32)
