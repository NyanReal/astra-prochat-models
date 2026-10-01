"""Inspect actual exported triangles in the fixed delivered arm pose."""
from pathlib import Path
import sys,json
from collections import defaultdict
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'source'))
from glb_io import read_glb,accessor,world_matrices
from collision_helpers import combine,collider,matrix,sample,vtk_to_numpy

def extract(g,b):
 wm=world_matrices(g);parts=[]
 for i,n in enumerate(g['nodes']):
  if 'mesh' not in n:continue
  for pr in g['meshes'][n['mesh']]['primitives']:
   p=accessor(g,b,pr['attributes']['POSITION']);f=accessor(g,b,pr['indices']).reshape(-1,3);m=wm[i];p=p@m[:3,:3].T+m[:3,3]
   rr=pr.get('extras',{}).get('patch_ranges')
   if rr:
    for r in rr:
     vo=r['vertex_offset'];vc=r['vertex_count'];ff=f[r['index_offset']//3:(r['index_offset']+r['index_count'])//3].astype(np.int64)-vo
     parts.append((r['name'],p[vo:vo+vc],ff,n['name']))
   else:parts.append((n['name'],p,f,n['name']))
 return parts

def hits(a,b):
 if not a or not b:return []
 aa,an=combine([p[:3] for p in a]);bb,bn=combine([p[:3] for p in b]);c=collider(aa,bb);c.Update();out=set()
 if c.GetNumberOfContacts():
  for x,y in zip(vtk_to_numpy(c.GetContactCells(0)),vtk_to_numpy(c.GetContactCells(1))):out.add((an[int(x)],bn[int(y)]))
 return [list(x) for x in sorted(out)]

def main():
 g,b=read_glb(R/'preview/FitCheck.glb');parts=extract(g,b)
 arms=[p for p in parts if p[3].startswith('Arm_')];body=[p for p in parts if not p[3].startswith('Arm_')]
 report={'method':'VTK triangle surface intersection on exported GLB, no convex proxies','scope':'Fixed arm pose; sampled original cockpit motion.',
  'arms_to_base_rest_contacts':hits(arms,body),
  'arm_damper_to_armor_contacts':hits([p for p in arms if '_damper_' in p[0]],[p for p in arms if 'cowling' in p[0] or 'gauntlet' in p[0]]),
  'arm_frames_to_shell_contacts':hits([p for p in arms if any(s in p[0] for s in ['_main_spar','_web','_backbone','_fork'])],[p for p in arms if 'cowling' in p[0] or 'gauntlet' in p[0]])}
 fixed,names=combine([p[:3] for p in arms]);anim=next(a for a in g['animations'] if a['name']=='Cockpit_Open');moving={c['target']['node'] for c in anim['channels']}
 # Animated parents can carry static descendants. Include the complete moving subtree.
 def descendants(i):
  out={i}
  for ch in g['nodes'][i].get('children',[]):out|=descendants(ch)
  return out
 moving=set().union(*(descendants(i) for i in moving));filters={};primnames={}
 for i in moving:
  n=g['nodes'][i]
  if 'mesh' not in n:continue
  pp=[]
  for pr in g['meshes'][n['mesh']]['primitives']:pp.append((n['name'],accessor(g,b,pr['attributes']['POSITION']),accessor(g,b,pr['indices']).reshape(-1,3)))
  poly,ns=combine(pp);filters[i]=collider(fixed,poly);primnames[i]=ns
 chits=defaultdict(set)
 for k,t in enumerate(np.linspace(0,3,181)):
  wm=world_matrices(g,sample(g,b,anim,float(t)))
  for i,c in filters.items():
   c.SetMatrix(1,matrix(wm[i]));c.Update()
   if c.GetNumberOfContacts():
    for a,bb in zip(vtk_to_numpy(c.GetContactCells(0)),vtk_to_numpy(c.GetContactCells(1))):chits[(names[int(a)],primnames[i][int(bb)])].add(round(float(t),6))
  if k%60==0:print('Cockpit sample',k,'/180',flush=True)
 report['cockpit_samples']=181;report['arms_to_moving_cockpit_contacts']=[{'arm':a,'body':bb,'times':sorted(ts)} for (a,bb),ts in sorted(chits.items())]
 report['notes']=['No arm range-of-motion, containment or continuous swept-volume proof.','No manufacturing/load certification.','Internal intentionally joined fasteners, braces, pins and bearings are not blanket-tested as disjoint parts.']
 (R/'docs/clearance_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
