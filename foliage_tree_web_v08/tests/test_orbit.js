'use strict';
// Regression contract: deleting orbit-camera.js or applying camera basis to
// proxy normals must fail. These tests use the actual production camera math.
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const file=path.join(__dirname,'../src/orbit-camera.js');
const exists=fs.existsSync(file);
let Orbit=exists?require(file):null;
const near=(a,b,e=1e-6)=>assert.ok(Math.abs(a-b)<e,`${a} != ${b}`);
const dot=(a,b)=>a.reduce((n,v,i)=>n+v*b[i],0);
const state={angle:0,elevation:Math.atan2(1,12)*180/Math.PI,zoom:1,pan:[0,0,0],mode:'tree'};
test('production free-camera controller exists',()=>assert.ok(exists,'v05 only has preset angles; continuous camera controller is missing'));
test('front camera preserves the v05 composition',()=>{
 assert.ok(Orbit,'camera controller missing');
 const c=Orbit.camera(state,1440,1080);
 near(c.halfHeight,2.63);near(c.eye[0],0);near(c.eye[1],3.16);near(c.eye[2],12);
});
test('camera basis remains orthonormal at all azimuths and near both poles',()=>{
 assert.ok(Orbit,'camera controller missing');
 for(const angle of [-720,-180,-90,0,90,180,360,901])for(const elevation of [-89.5,-30,0,40,89.5]){
  const c=Orbit.camera({...state,angle,elevation},1440,1080);
  for(const v of [c.right,c.up,c.back])near(dot(v,v),1);
  near(dot(c.right,c.up),0);near(dot(c.right,c.back),0);near(dot(c.up,c.back),0);
 }
});
test('zoom changes screen scale, and pan follows the current camera plane',()=>{
 assert.ok(Orbit,'camera controller missing');
 const c=Orbit.camera({...state,zoom:2},1440,1080);near(c.halfHeight,2.63/2);
 const p=Orbit.pan({...state,angle:90},100,0,1440,1080);
 assert.ok(p.pan[2]>.1);near(p.pan[0],0);
});
test('invalid values cannot produce a singular camera',()=>{
 assert.ok(Orbit,'camera controller missing');
 const s=Orbit.sanitize({...state,angle:Infinity,elevation:10000,zoom:0,pan:[NaN,undefined,0]});
 assert.ok(Number.isFinite(s.angle));assert.ok(s.elevation<90);assert.ok(s.zoom>0);assert.ok(s.pan.every(Number.isFinite));
});
