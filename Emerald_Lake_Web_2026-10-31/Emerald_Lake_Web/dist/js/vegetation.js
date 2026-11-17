import * as THREE from 'three';
import { WATER_Y, rng, lakeMetric, lakePoint, surfaceHeight, foliageAllowed, isWater, isIsland, inPropZone, pathDistance, streamDistance } from './world.js';

// All plants are built from small, reusable 3D shapes. The seeded distribution
// gives the same landscape on every load and needs no downloaded textures.
export function createVegetation(ctx = {}) {
  const group = new THREE.Group();
  group.name = 'Vegetation';
  const rand = rng(4262025);
  const high = ctx.quality !== 'balanced';
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();
  const up = new THREE.Vector3(0, 1, 0);
  const palettes = {
    needles: [0x075348, 0x096452, 0x10705a, 0x1d8061, 0x358d63, 0x6d9f48],
    shrub: [0x246d40, 0x388943, 0x599a3b, 0x79a947, 0x9bb94b],
    grass: [0x3a873a, 0x65a33b, 0x83b944, 0xb0c94c],
  };
  function mat(color, extra = {}) { return new THREE.MeshStandardMaterial({color, roughness: 1, side: THREE.DoubleSide, ...extra}); }
  // A single hand-painted needle sheet gives every bough fine directional
  // strokes, cool shadow gaps and small sunlit yellow-green flecks.
  function needleTexture() {
    const canvas=document.createElement('canvas'); canvas.width=512; canvas.height=256;
    const c=canvas.getContext('2d'), paintRand=rng(83521);
    const gradient=c.createLinearGradient(0,0,0,256);
    gradient.addColorStop(0,'#abc8a0'); gradient.addColorStop(.48,'#ecf4d2'); gradient.addColorStop(1,'#729f85');
    c.fillStyle=gradient; c.fillRect(0,0,512,256);
    for(let i=0;i<1500;i++) {
      const x=paintRand()*512, y=paintRand()*256, len=3+paintRand()*17;
      c.strokeStyle=paintRand()<.27?'rgba(45,89,70,.34)':paintRand()<.3?'rgba(243,255,135,.6)':'rgba(132,187,134,.5)';
      c.lineWidth=.6+paintRand()*1.7; c.beginPath(); c.moveTo(x,y);
      c.lineTo(x+len,y+(y<128?-1:1)*(2+paintRand()*7)); c.stroke();
    }
    const texture=new THREE.CanvasTexture(canvas); texture.colorSpace=THREE.SRGBColorSpace;
    texture.wrapS=texture.wrapT=THREE.ClampToEdgeWrapping; texture.needsUpdate=true; return texture;
  }
  const windTime={value:0};
  function windMaterial(material, kind) {
    material.onBeforeCompile=shader=>{
      shader.uniforms.vegetationTime=windTime;
      shader.vertexShader=shader.vertexShader.replace('#include <common>', '#include <common>\nuniform float vegetationTime;');
      const weight=kind==='bough'?'position.x':'max(position.y, 0.0)';
      shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
        vec2 plantOrigin = vec2(0.0);
        #ifdef USE_INSTANCING
          plantOrigin = instanceMatrix[3].xz;
        #endif
        float breeze = sin(vegetationTime * 1.15 + plantOrigin.x * 0.53 + plantOrigin.y * 0.37);
        transformed.z += breeze * 0.045 * ${weight};
        transformed.x += cos(vegetationTime * 0.8 + plantOrigin.y * 0.4) * 0.02 * ${weight};`);
    };
    material.customProgramCacheKey=()=>`vegetation-wind-${kind}`;
    return material;
  }
  function instances(geometry, material, list, cast = false) {
    if (!list.length) return null;
    const mesh = new THREE.InstancedMesh(geometry, material, list.length);
    mesh.castShadow = cast; mesh.receiveShadow = true;
    list.forEach((a, i) => {
      p.set(a.x,a.y,a.z); q.setFromAxisAngle(up,a.rot || 0); s.set(a.sx,a.sy,a.sz);
      m4.compose(p,q,s); mesh.setMatrixAt(i,m4);
      if (a.color !== undefined) mesh.setColorAt(i,new THREE.Color(a.color));
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.computeBoundingSphere(); group.add(mesh); return mesh;
  }
  const pick = a => a[Math.floor(rand()*a.length)];
  // Horizontal lobed evergreen bough: tapered center with interlocking needle
  // sprays. The uneven edges preserve a pine silhouette even at a distance.
  function branchGeometry() {
    const outline = [[0,0],[.16,.045],[.20,.20],[.28,.10],[.34,.26],[.41,.14],[.48,.30],[.54,.16],[.62,.29],[.67,.15],[.75,.25],[.80,.13],[.87,.19],[.92,.08],[1,0], [.92,-.08],[.87,-.19],[.80,-.13],[.75,-.25],[.67,-.15],[.62,-.29],[.54,-.16],[.48,-.30],[.41,-.14],[.34,-.26],[.28,-.10],[.20,-.20],[.16,-.045]];
    const v=[0,.05,0];
    for (const [x,z] of outline) v.push(x, .05 + .11*x - .06*Math.abs(z), z);
    const idx=[]; for(let i=0;i<outline.length;i++) idx.push(0,1+i,1+(i+1)%outline.length);
    const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(v,3)); const uv=[]; for(let i=0;i<v.length;i+=3) uv.push(v[i],v[i+2]/.6+.5); g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2)); g.setIndex(idx); g.computeVertexNormals(); return g;
  }
  const bough = branchGeometry();
  const treeBranches=[], treeTrunks=[], treeLeaders=[], shrubs=[], grasses=[], flowers=[], reeds=[], reedHeads=[], pads=[];
  let trees=0;
  // Trees are mostly behind and to either side of the lake; openings reserve
  // the paths, stream, fishing areas and structures defined in world.js.
  const treeSites=[];
  for(let z=-23;z<=23;z+=2.8) for(let x=-23;x<=23;x+=2.8) {
    const xx=x+(rand()-.5)*2.0, zz=z+(rand()-.5)*2.0, lm=lakeMetric(xx,zz);
    if(lm<1.36 || !foliageAllowed(xx,zz) || inPropZone(xx,zz,1.2) || streamDistance(xx,zz)<3 || pathDistance(xx,zz)<2.0) continue;
    if(xx>10 && zz>8 && rand()<.72) continue;
    if(zz>12 && rand()<.55) continue;
    if(rand()<(zz < -8 ? .40 : .25) && treeSites.every(t=>Math.hypot(t.x-xx,t.z-zz)>2.25)) treeSites.push({x:xx,z:zz});
  }
  // Add layered forest framing on both foreground corners and the western
  // bank. Candidates still respect the paths, structures and water.
  let forestAttempts=0;
  while(treeSites.length<61 && forestAttempts++<14000) {
    const k=forestAttempts%4;
    const x=k===0?-16+rand()*7:k===1?10+rand()*9:k===2?-20+rand()*7:-22+rand()*44;
    const z=k===0?10+rand()*10:k===1?11+rand()*9:k===2?-1+rand()*9:-23+rand()*7;
    if(lakeMetric(x,z)<1.16 || !foliageAllowed(x,z) || inPropZone(x,z,.8) || streamDistance(x,z)<2.7 || pathDistance(x,z)<1.45)continue;
    if(treeSites.some(t=>Math.hypot(t.x-x,t.z-z)<2.0))continue;
    treeSites.push({x,z,h:3.1+rand()*3.0});
  }
  // Follow the sculpted shore, creek banks and island surface.
  const groundY=surfaceHeight;
  treeSites.push({x:5.35,z:1.20,h:2.6,island:true},{x:6.65,z:1.90,h:3.3,island:true});
  for(const t of treeSites) {
    const h=t.h || 4.0+rand()*3.3, base=groundY(t.x,t.z)-.03, radius=h*(.28+rand()*.035), phase=rand()*6.28;
    trees++;
    treeTrunks.push({x:t.x,y:base+h*.39,z:t.z,rot:phase,sx:h*.036,sy:h*.78,sz:h*.036,color:pick([0x76553a,0x634a35,0x886343])});
    // Nine whorls; each consists of separate serrated, slightly raised boughs.
    const levels=high?10:8;
    for(let l=0;l<levels;l++) {
      const f=l/(levels-1), y=base+h*(.19+f*.72), len=radius*(1-f*.82)*(0.85+rand()*.25);
      const n=Math.max(5,Math.round(8-f*3));
      for(let j=0;j<n;j++) {
        const a=phase+j*Math.PI*2/n+l*.83+(rand()-.5)*.3;
        const start=.04+rand()*.12;
        treeBranches.push({x:t.x+Math.cos(a)*start,y:y+(rand()-.5)*.12,z:t.z-Math.sin(a)*start,rot:a,sx:len*(.82+rand()*.35),sy:1,sz:len*(.75+rand()*.35),color:pick(f>.73?[0x19765a,0x2d8961,0x5b9c51]:palettes.needles)});
      }
    }
    treeLeaders.push({x:t.x,y:base+h*.84,z:t.z,rot:phase,sx:radius*.28,sy:h*.22,sz:radius*.28,color:0x287b57});
  }
  // Shrubs are loose, angular sprays of separately instanced leaves rather
  // than round solid balls; the raised folded center catches the light.
  function leafGeometry() {
    const verts=[0,.08,0, .38,.18,0, 1,.12,0, .72,.08,.16, .47,.06,.25, .20,.03,.15, .72,.08,-.16, .47,.06,-.25, .20,.03,-.15];
    const idx=[0,1,5,1,4,5,1,3,4,1,2,3,0,8,1,1,8,7,1,7,6,1,6,2];
    const uv=[];for(let i=0;i<verts.length;i+=3)uv.push(verts[i],verts[i+2]*2+.5);
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();return g;
  }
  const shrubGeo=leafGeometry();
  for(let i=0;i<(high?780:470);i++) {
    const x=(rand()-.5)*48,z=(rand()-.5)*48;
    if(!foliageAllowed(x,z) || pathDistance(x,z)<1.35) continue;
    const scale=.25+rand()*.42, y=groundY(x,z), phase=rand()*6.28;
    for(let j=0;j<6;j++) {
      const a=phase+j*Math.PI/3+(rand()-.5)*.3;
      shrubs.push({x:x+Math.cos(a)*scale*.04,y:y+.06+rand()*.17,z:z-Math.sin(a)*scale*.04,rot:a,sx:scale*(.8+rand()*.5),sy:1,sz:scale*(.9+rand()*.6),color:pick(palettes.shrub)});
    }
  }
  function grassGeometry() {
    const v=[], idx=[];
    for(let i=0;i<7;i++) { const a=i*Math.PI*2/7, cx=Math.cos(a),cz=Math.sin(a), tx=-cz,tz=cx, b=v.length/3;
      const h=.65+(i%3)*.16, lean=.22+(i%2)*.1;
      v.push(-tx*.07,0,-tz*.07, tx*.07,0,tz*.07, cx*lean,h,cz*lean); idx.push(b,b+1,b+2);
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(v,3));g.setIndex(idx);g.computeVertexNormals();return g;
  }
  const grassGeo=grassGeometry();
  for(let i=0;i<(high?2500:1550);i++) {
    const x=(rand()-.5)*49,z=(rand()-.5)*49;
    if(!foliageAllowed(x,z) || pathDistance(x,z)<1.20) continue;
    const sc=.22+rand()*.42;
    grasses.push({x,y:groundY(x,z)-.02,z,rot:rand()*6.28,sx:sc,sy:sc*(.8+rand()*.6),sz:sc,color:pick(palettes.grass)});
  }
  // Ferns are low fans of the same serrated leaf, with a broad ring of fronds.
  const ferns=[];
  for(let i=0;i<(high?450:280);i++) {
    const x=(rand()-.5)*48,z=(rand()-.5)*48;
    if(!foliageAllowed(x,z) || pathDistance(x,z)<1.4) continue;
    const y=groundY(x,z)+.08, phase=rand()*6.28, size=.34+rand()*.48;
    for(let j=0;j<6;j++) { const a=phase+j*Math.PI/3; ferns.push({x,y:y+rand()*.07,z,rot:a,sx:size*(.8+rand()*.3),sy:1,sz:size*.75,color:pick(palettes.shrub)}); }
  }
  // Five-petal daisies, each a modeled cluster with a warm center, viewed from above.
  function flowerGeometry() {
    const vertices=[], colors=[], index=[];
    function tri(x1,z1,x2,z2,x3,z3,y,c) {const b=vertices.length/3; for(const [x,z] of [[x1,z1],[x2,z2],[x3,z3]]) {vertices.push(x,y,z);colors.push(...c);}index.push(b,b+1,b+2);}
    for(let i=0;i<5;i++) {let a=i*Math.PI*2/5, b=a+.34,c=a-.34;tri(Math.cos(b)*.10,Math.sin(b)*.10,Math.cos(a)*.43,Math.sin(a)*.43,Math.cos(c)*.10,Math.sin(c)*.10,.01,[1,1,.9]);}
    for(let i=0;i<6;i++){let a=i*Math.PI/3,b=(i+1)*Math.PI/3;tri(0,0,Math.cos(a)*.13,Math.sin(a)*.13,Math.cos(b)*.13,Math.sin(b)*.13,.025,[1,.68,.12]);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));g.setIndex(index);g.computeVertexNormals();return g;
  }
  for(let i=0;i<(high?4100:2500);i++) {
    const x=(rand()-.5)*48,z=(rand()-.5)*48;
    if(!foliageAllowed(x,z) || pathDistance(x,z)<1.2) continue;
    const sc=.14+rand()*.12;
    flowers.push({x,y:groundY(x,z)+.12+rand()*.13,z,rot:rand()*6.28,sx:sc,sy:sc,sz:sc,color:rand()<.24?0xffdf61:0xffffff});
  }
  // Extra clustered blossoms border the winding path and form little carpets.
  // Continue until the high quality scene has at least 2,000 actual flowers.
  let attempts=0;
  while(flowers.length<(high?2400:1450) && attempts++<24000) {
    const x=(rand()-.5)*46,z=(rand()-.5)*46, d=pathDistance(x,z);
    if(d<1.2 || d>3.6 || !foliageAllowed(x,z)) continue;
    for(let j=0;j<5;j++) {
      const xx=x+(rand()-.5)*1.15,zz=z+(rand()-.5)*1.15;
      if(!foliageAllowed(xx,zz)||pathDistance(xx,zz)<1.2)continue;
      const sc=.14+rand()*.12;
      flowers.push({x:xx,y:groundY(xx,zz)+.12+rand()*.11,z:zz,rot:rand()*6.28,sx:sc,sy:sc,sz:sc,color:rand()<.25?0xffdf61:0xffffff});
    }
  }
  // Margin plants follow the actual irregular shoreline, with small groups
  // of reeds growing in shallows and pads scattered in protected clusters.
  for(let i=0;i<150;i++) {
    const a=rand()*Math.PI*2, pt=lakePoint(a,-.15-rand()*.8);
    if(!isWater(pt.x,pt.z) || inPropZone(pt.x,pt.z,.1)) continue;
    const n=2+Math.floor(rand()*5);
    for(let j=0;j<n;j++) {const x=pt.x+(rand()-.5)*.7,z=pt.z+(rand()-.5)*.7,h=.5+rand()*.9;
      if(!isWater(x,z))continue;
      reeds.push({x,y:WATER_Y+h*.5-.01,z,rot:rand()*6.28,sx:.035,sy:h,sz:.035,color:pick(palettes.grass)});
      if(rand()<.22)reedHeads.push({x,y:WATER_Y+h*.87,z,rot:0,sx:.055,sy:.17,sz:.055,color:0x86683a});
    }
  }
  for(let i=0;i<210;i++) {
    const a=rand()*Math.PI*2,pt=lakePoint(a,-.8-rand()*3.2);
    if(!isWater(pt.x,pt.z)||isIsland(pt.x,pt.z,.3))continue;
    const sc=.12+rand()*.19;
    pads.push({x:pt.x,y:WATER_Y+.035+rand()*.012,z:pt.z,rot:rand()*6.28,sx:sc,sy:1,sz:sc*(.75+rand()*.3),color:pick([0x65983c,0x8caa3d,0xa5bd45,0x417f3c])});
  }
  const trunkGeo=new THREE.CylinderGeometry(.7,1,1,7); const poleGeo=new THREE.CylinderGeometry(.65,1,1,5); const leaderGeo=new THREE.ConeGeometry(1,1,7);
  instances(trunkGeo,mat(0xffffff),treeTrunks,true);
  const needleMat=windMaterial(mat(0xffffff,{map:needleTexture()}),'bough');
  instances(bough,needleMat,treeBranches,true);
  instances(leaderGeo,mat(0xffffff),treeLeaders,true);
  instances(shrubGeo,needleMat,shrubs,true);
  instances(grassGeo,windMaterial(mat(0xffffff),'grass'),grasses);
  instances(bough,needleMat,ferns);
  instances(flowerGeometry(),mat(0xffffff,{vertexColors:true}),flowers);
  instances(poleGeo,mat(0xffffff),reeds);
  instances(poleGeo,mat(0xffffff),reedHeads);
  const padShape=new THREE.Shape();padShape.moveTo(.12,0);for(let i=0;i<=20;i++){const a=.14+(Math.PI*2-.28)*i/20,r=1+.045*Math.sin(a*5)+.035*Math.sin(a*9);padShape.lineTo(Math.cos(a)*r,Math.sin(a)*r*.86);}padShape.lineTo(.12,0);
  const padGeo=new THREE.ShapeGeometry(padShape,16);padGeo.rotateX(-Math.PI/2);
  instances(padGeo,mat(0xffffff),pads);
  return {group, update(time) {windTime.value=time;}, stats:{trees, treeBranches:treeBranches.length, shrubs:shrubs.length, grasses:grasses.length, fernFronds:ferns.length, flowers:flowers.length, reeds:reeds.length, lilyPads:pads.length}};
}
