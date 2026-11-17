'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.join(__dirname,'..'),file=path.join(root,'src/environment.js');
const E=fs.existsSync(file)?require(file):null;
const scene=JSON.parse(fs.readFileSync(path.join(root,'assets/scene.json')));
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
test('forest environment implementation is present',()=>assert.ok(E,'No forest-floor/grass module yet'));
test('grass effective wind is master tree wind times the independently clamped multiplier',()=>{
 assert.ok(E);near(E.effectiveWind(.8,.5),.4);near(E.effectiveWind(0,2),0);near(E.effectiveWind(1,0),0);
 near(E.effectiveWind(1,2),2);assert.ok(Number.isFinite(E.effectiveWind(NaN,Infinity)));
});
test('grass roots remain fixed, while tips move and doubling ratio doubles displacement',()=>{
 assert.ok(E);
 for(const t of [0,1.2,4.9,13]){
  assert.deepEqual(E.grassOffset([.5,0,.8],.26,0,.3,t,.9,2),[0,0,0]);
  const a=E.grassOffset([.5,0,.8],.26,1,.3,t,.9,1),b=E.grassOffset([.5,0,.8],.26,1,.3,t,.9,2);
  a.forEach((v,i)=>near(v*2,b[i]));
  assert.deepEqual(E.grassOffset([.5,0,.8],.26,1,.3,t,0,2),[0,0,0]);
 }
});
test('production grass mesh is deterministic, rooted 3D geometry with valid attribute streams',()=>{
 assert.ok(E);const a=E.buildGrass(scene.trunk),b=E.buildGrass(scene.trunk);
 assert.deepEqual(a,b);const n=a.position.length/3;
 assert.ok(n>500&&a.meta.tufts>=35&&a.meta.blades>=150);
 for(const [k,size] of [['normal',3],['color',3],['uv',2],['pivot',3],['phase',1],['proxyNormal',3],['bunchIndex',1]])assert.equal(a[k].length,n*size,k);
 assert.ok(a.indices.every(i=>i>=0&&i<n));assert.ok(a.position.every(Number.isFinite));
 const roots=[];
 for(let i=0;i<n;i++){
  const h=a.uv[i*2+1];assert.ok(h>=0&&h<=1);
  if(h===0){near(a.position[i*3+1],a.pivot[i*3+1]);roots.push(i);}
 }
 assert.equal(roots.length,a.meta.blades*2);
 assert.ok(Math.max(...a.position.filter((_,i)=>i%3===1))<.45);
});
test('forest texture and grass multiplier are wired into the shipped document',()=>{
 const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
 assert.ok(html.includes('id="grass-wind"'),'grass slider missing');assert.ok(html.includes('uGrassWindRatio'),'wind multiplier uniform missing');assert.ok(html.includes('forest_floor'),'floor texture missing');
 assert.ok(fs.existsSync(path.join(root,'assets/forest_floor_basecolor.jpg')));
});
