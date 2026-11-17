import * as THREE from 'three';
import { WATER_Y, rng, isWater } from './world.js';

// Sparse animated details give scale without competing with the scenery.
export function createLife(){
  const group=new THREE.Group();group.name='small-life';const rand=rng(708);const fish=[];
  const fishMaterial=new THREE.MeshBasicMaterial({color:'#285d61',transparent:true,opacity:.48,depthWrite:false});
  const fishGeometry=new THREE.SphereGeometry(1,10,6);const tailGeo=new THREE.ConeGeometry(.19,.36,3);tailGeo.rotateZ(-Math.PI/2);
  for(let i=0;i<8;i++){
    const g=new THREE.Group(),body=new THREE.Mesh(fishGeometry,fishMaterial);body.scale.set(.42,.022,.12);g.add(body);
    const tail=new THREE.Mesh(tailGeo,fishMaterial);tail.position.x=-.44;tail.scale.set(1,.15,1);g.add(tail);
    const cx=(rand()-.5)*11,cz=(rand()-.5)*8,r=1.5+rand()*2,phase=rand()*6.28;
    g.position.y=WATER_Y+.018;g.renderOrder=3;group.add(g);fish.push({g,tail,cx,cz,r,phase,speed:.09+rand()*.06});
  }
  const count=42,arr=new Float32Array(count*3),base=[];
  for(let i=0;i<count;i++){const x=(rand()-.5)*30,z=(rand()-.5)*28,y=1+rand()*5;base.push({x,y,z,phase:rand()*6.28});arr.set([x,y,z],i*3);}
  const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(arr,3));
  const c=document.createElement('canvas');c.width=c.height=32;const g=c.getContext('2d');const grad=g.createRadialGradient(16,16,1,16,16,15);grad.addColorStop(0,'rgba(255,255,225,0.9)');grad.addColorStop(.3,'rgba(255,245,189,0.6)');grad.addColorStop(1,'rgba(255,245,189,0)');g.fillStyle=grad;g.fillRect(0,0,32,32);
  const motes=new THREE.Points(geo,new THREE.PointsMaterial({size:.10,map:new THREE.CanvasTexture(c),color:'#fff4b8',transparent:true,opacity:.6,depthWrite:false,sizeAttenuation:true}));group.add(motes);
  return {group,update(time){for(const f of fish){const a=time*f.speed+f.phase,x=f.cx+Math.cos(a)*f.r,z=f.cz+Math.sin(a)*f.r*.6;f.g.visible=isWater(x,z);f.g.position.x=x;f.g.position.z=z;f.g.rotation.y=-a-Math.PI/2;f.tail.rotation.y=Math.sin(time*3+f.phase)*.18;}for(let i=0;i<count;i++){const b=base[i];arr[i*3]=b.x+Math.sin(time*.16+b.phase)*.8;arr[i*3+1]=b.y+Math.sin(time*.3+b.phase)*.3;arr[i*3+2]=b.z+Math.cos(time*.2+b.phase)*.6;}geo.attributes.position.needsUpdate=true;},stats:{fish:fish.length}};
}
