import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {lakePoint,lakeMetric,landHeight,surfaceHeight,isWater,ISLAND} from '../dist/js/world.js';

const root=path.resolve(import.meta.dirname,'../dist');
const files=[];
function walk(dir){for(const item of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,item.name);item.isDirectory()?walk(p):files.push(p);}}walk(root);
let references=0;
function resolve(spec,from){if(spec==='three')return path.join(root,'vendor/three.module.js');if(spec.startsWith('three/addons/'))return path.join(root,'vendor',spec.slice(13));if(spec.startsWith('.'))return path.resolve(path.dirname(from),spec);throw new Error('Unexpected external dependency: '+spec);}
for(const f of files.filter(f=>f.endsWith('.js'))){
  for(const match of fs.readFileSync(f,'utf8').matchAll(/(?:\bfrom\s*|\bimport\s*)['"]([^'"]+)['"]/g)){
    const resolved=resolve(match[1],f);assert.ok(fs.existsSync(resolved),'Missing import '+match[1]+' in '+f);references++;
  }
}
const index=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const match of index.matchAll(/(?:src|href)="(\.\/[^"#]+)"/g)){assert.ok(fs.existsSync(path.resolve(root,match[1])),'Missing HTML asset: '+match[1]);references++;}
for(const name of ['ground','wood','stone','grass','metal','waterbed'])assert.ok(fs.statSync(path.join(root,'assets/textures/material-atlas.png')).size>10000);
for(const name of ['overview','dock','stream','camp'])assert.ok(fs.statSync(path.join(root,'assets/previews',name+'.jpg')).size>10000,'Missing rendered fallback: '+name);
for(let i=0;i<360;i++){const q=lakePoint(i*Math.PI/180);assert.ok(Math.abs(lakeMetric(q.x,q.z)-1)<1e-8,'shore mismatch');assert.ok(Number.isFinite(landHeight(q.x,q.z)));assert.ok(Number.isFinite(surfaceHeight(q.x*1.01,q.z*1.01)));}
assert.equal(isWater(0,0),true);assert.equal(isWater(ISLAND.x,ISLAND.z),false);
const largest=files.reduce((a,f)=>fs.statSync(f).size>a.bytes?{path:path.relative(root,f),bytes:fs.statSync(f).size}:a,{path:'',bytes:0});
assert.ok(largest.bytes<25*1024*1024,'A static asset exceeds the requested hosting-compatible 25 MiB limit');
const summary={status:'passed',jsFiles:files.filter(f=>f.endsWith('.js')).length,localReferencesChecked:references,staticFiles:files.length,largest,totalBytes:files.reduce((n,f)=>n+fs.statSync(f).size,0),browserWebGL:'unverified: preview browser disables GL',scope:'self-contained imports/assets, shoreline continuity, finite sampled ground data; syntax checked separately with node --check'};
console.log(JSON.stringify(summary,null,2));
fs.writeFileSync(path.resolve(root,'../qa/source-validation.json'),JSON.stringify(summary,null,2)+'\n');
