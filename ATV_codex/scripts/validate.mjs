import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=n=>fs.readFileSync(path.join(root,n));
const stats=JSON.parse(read('assets/model-stats.json'));
const glb=read('assets/atv.glb');
if(glb.readUInt32LE(0)!==0x46546c67||glb.readUInt32LE(4)!==2||glb.readUInt32LE(8)!==glb.length)throw Error('Invalid GLB');
const gltf=JSON.parse(glb.subarray(20,20+glb.readUInt32LE(12)).toString());
const triangles=gltf.meshes.flatMap(m=>m.primitives).reduce((n,p)=>n+gltf.accessors[p.indices].count/3,0);
if(triangles!==stats.triangles||triangles>=10000)throw Error('Triangle count mismatch/budget');
if(gltf.images.some(i=>i.uri))throw Error('GLB texture is not embedded');
const tris=JSON.parse(read('assets/uv_triangles.json'));
const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
const area=p=>Math.abs(p.reduce((a,v,i)=>a+v[0]*p[(i+1)%p.length][1]-v[1]*p[(i+1)%p.length][0],0))/2;
function intersection(a,b){
  let out=a;
  const sign=cross(b[0],b[1],b[2])>=0?1:-1;
  for(let i=0;i<3&&out.length;i++){
    const p=b[i],q=b[(i+1)%3],input=out;out=[];
    for(let j=0;j<input.length;j++){
      const s=input[j],e=input[(j+1)%input.length],ds=sign*cross(p,q,s),de=sign*cross(p,q,e);
      if(ds>=0)out.push(s);
      if((ds>=0)!==(de>=0)){const t=ds/(ds-de);out.push([s[0]+t*(e[0]-s[0]),s[1]+t*(e[1]-s[1])]);}
    }
  }
  return out.length>=3?area(out):0;
}
const bins=new Map(),seen=new Set();let overlap=0,degenerate=0,outOfBounds=0,maxOverlap=0;
tris.forEach((tri,i)=>{
  if(area(tri)<1e-13)degenerate++;
  if(tri.some(v=>v.some(n=>!Number.isFinite(n)||n<0||n>1)))outOfBounds++;
  const xs=tri.map(v=>v[0]),ys=tri.map(v=>v[1]);
  for(let x=Math.floor(Math.min(...xs)*100);x<=Math.floor(Math.max(...xs)*100);x++)
    for(let y=Math.floor(Math.min(...ys)*100);y<=Math.floor(Math.max(...ys)*100);y++){
      const key=x+','+y,prev=bins.get(key)||[];
      for(const j of prev){const pair=j+','+i;if(seen.has(pair))continue;seen.add(pair);const a=intersection(tri,tris[j]);if(a>1e-10){overlap++;maxOverlap=Math.max(maxOverlap,a);}}
      prev.push(i);bins.set(key,prev);
    }
});
const report={result:overlap||degenerate||outOfBounds?'FAIL':'PASS',glbTriangles:triangles,budget:9999,embeddedTextures:gltf.images.length,uvTriangles:tris.length,positiveAreaOverlapPairs:overlap,degenerateUVTriangles:degenerate,uvOutOfBounds:outOfBounds,maximumOverlapArea:maxOverlap,method:'Spatial buckets + convex triangle clipping; shared edges ignored; area epsilon 1e-10',verifiedAt:new Date().toISOString()};
fs.writeFileSync(path.join(root,'docs/validation.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if(report.result!=='PASS')process.exit(1);
