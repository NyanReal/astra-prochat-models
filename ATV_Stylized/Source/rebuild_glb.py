"""Rebuild the GLB from parametric geometry and the delivered unique UV layout.
Run with standard Python + NumPy. Writes Build_Python/SM_ATV_Stylized.glb.
Does NOT overwrite the texture images or the original deliverable.
"""
from pathlib import Path
import json
import numpy as np
from atv_geometry import build_model
from atv_export import save_glb
ROOT=Path(__file__).resolve().parents[1]

def saved_uv(m):
 records=json.loads((ROOT/'Source/UV_Charts.json').read_text())
 layout={c['name']:c['rectangle'] for c in records};local=np.array(m.uv_local);faces=np.array(m.faces);uv=np.zeros((len(local),2),np.float32)
 for c in m.charts:
  x,y,w,h,rot=layout[c.name];c.rect=layout[c.name]
  ids=np.unique(faces[c.triangles].ravel());q=local[ids].copy()
  if rot:q=np.column_stack((q[:,1],1-q[:,0]))
  q=q*np.array([w-10,h-10])+[x+5,y+5]
  uv[ids,0]=q[:,0]/2048;uv[ids,1]=1-q[:,1]/2048
 return uv

def rebuild(out=None):
 m=build_model();uv=saved_uv(m)
 if len(m.faces)>=10000:raise RuntimeError('Triangle budget exceeded')
 out=Path(out) if out else ROOT/'Build_Python/SM_ATV_Stylized.glb';out.parent.mkdir(parents=True,exist_ok=True)
 save_glb(m,uv,out,ROOT/'Textures');return m,uv,out

if __name__=='__main__':
 m,uv,out=rebuild();print(f'{out}: {len(m.faces)} triangles, {len(m.charts)} unique charts')
