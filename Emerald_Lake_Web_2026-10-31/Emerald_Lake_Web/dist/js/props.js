import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { landHeight, WATER_Y } from './world.js';

// Weathered, deliberately hand-built camp objects. Static pieces are merged
// by material once built; the two floats remain independent for gentle motion.
export function createProps(ctx = {}) {
  const tex = ctx.textures || {};
  const mat = (color, map, extra={}) => new THREE.MeshStandardMaterial({color, map:map || null, roughness:.88, ...extra});
  const M = {
    wood:mat(0xe2c8a1,tex.wood), paleWood:mat(0xffe3bc,tex.wood), darkWood:mat(0xa89578,tex.wood),
    endWood:mat(0xe6c79a,tex.wood), metal:mat(0x4d5b55,tex.metal), dark:mat(0x333f3b),
    olive:mat(0x667152), oliveLight:mat(0x899071), rust:mat(0x866547), rubber:mat(0x303832),
    glass:mat(0x82aaa3,null,{roughness:.24,metalness:.18}), cream:mat(0xe8dec2), teal:mat(0x4c8b85),
    white:mat(0xe8eadb), moss:mat(0x758b42), red:mat(0xbc5645), black:mat(0x243b38),
    lamp:mat(0xffe4a5,null,{emissive:0xffcc71,emissiveIntensity:.8})
  };
  const root = new THREE.Group(); root.name = 'Camp props';
  const construction = new THREE.Group();
  const boxGeo = new THREE.BoxGeometry(1,1,1);
  const cylGeo = new THREE.CylinderGeometry(.5,.5,1,8);
  const sphereGeo = new THREE.SphereGeometry(.5,8,6);
  function piece(parent, geo, m, x,y,z,sx,sy,sz, rx=0,ry=0,rz=0) {
    const o=new THREE.Mesh(geo,m); o.position.set(x,y,z); o.scale.set(sx,sy,sz); o.rotation.set(rx,ry,rz); parent.add(o); return o;
  }
  function box(p,m,x,y,z,sx,sy,sz,rx=0,ry=0,rz=0){return piece(p,boxGeo,m,x,y,z,sx,sy,sz,rx,ry,rz);}
  function cyl(p,m,x,y,z,sx,sy,sz,rx=0,ry=0,rz=0){return piece(p,cylGeo,m,x,y,z,sx,sy,sz,rx,ry,rz);}
  function beam(p,m,a,b,r){const mid=new THREE.Vector3().addVectors(a,b).multiplyScalar(.5), d=new THREE.Vector3().subVectors(b,a); const o=cyl(p,m,mid.x,mid.y,mid.z,r,d.length(),r); o.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize());return o;}
  function section(x,y,z,rotation=0){const g=new THREE.Group();g.position.set(x,y,z);g.rotation.y=rotation;construction.add(g);return g;}
  function nail(p,x,y,z){cyl(p,M.dark,x,y,z,.055,.025,.055);}
  function crate(p,x,y,z,s=1){
    const g=new THREE.Group();g.position.set(x,y,z);g.scale.setScalar(s);p.add(g);
    box(g,M.wood,0,.42,0,.84,.84,.78);
    for(let t of [-.31,.31]){box(g,M.paleWood,t,.42,.401,.09,.86,.045);box(g,M.paleWood,t,.42,-.401,.09,.86,.045);box(g,M.paleWood,.431,.42,t,.045,.86,.09);box(g,M.paleWood,-.431,.42,t,.045,.86,.09);}
    for(let t of [.12,.72]) {box(g,M.darkWood,0,t,.415,.87,.07,.045);box(g,M.darkWood,0,t,-.415,.87,.07,.045);}
    box(g,M.paleWood,0,.85,0,.88,.08,.82); for(let t of [-.3,.3])box(g,M.darkWood,t,.9,0,.06,.025,.82);
    for(let a of [-.3,.3])for(let b of [-.3,.3])nail(g,a,.923,b);
  }
  function cooler(p,x,y,z,s=1){
    const g=new THREE.Group();g.position.set(x,y,z);g.scale.setScalar(s);p.add(g);
    box(g,M.white,0,.35,0,.86,.68,.68);box(g,M.metal,0,.14,0,.89,.12,.71);box(g,M.metal,0,.68,0,.9,.09,.73);box(g,M.cream,0,.76,0,.93,.1,.76);
    for(let x1 of [-.38,.38]){box(g,M.metal,x1,.39,.35,.07,.48,.045);box(g,M.metal,x1,.39,-.35,.07,.48,.045);}
    box(g,M.dark,0,.57,.382,.18,.09,.035);box(g,M.metal,0,.83,0,.26,.035,.08);
  }
  function dock(x,z,w,l,y){
    const g=section(x,0,z); let count=Math.round(l/.46);
    for(let i=0;i<count;i++){
      let zz=-l/2+(i+.5)*l/count;box(g,i%4===0?M.paleWood:M.wood,0,y,zz,w,.18,l/count-.035);
      for(let xx of [-w/2+.22,w/2-.22]){nail(g,xx,y+.105,zz-.13);nail(g,xx,y+.105,zz+.13);}
    }
    for(let xx of [-w/2+.34,w/2-.34])box(g,M.darkWood,xx,y-.22,0,.22,.3,l+.12);
    for(let zz of [-l/2+.24,l/2-.24])box(g,M.darkWood,0,y-.31,zz,w+.18,.27,.25);
    for(let xx of [-w/2+.18,w/2-.18])for(let zz of [-l/2+.23,l/2-.23]){
      box(g,M.darkWood,xx,(y-.28)/2,zz,.3,y-.28,.3); box(g,M.endWood,xx,y+.18,zz,.34,.42,.34);
      box(g,M.metal,xx,y+.13,zz,.36,.08,.36);box(g,M.endWood,xx,y+.4,zz,.34,.035,.34);
    }
    for(let xx of [-w*.36,w*.34])box(g,M.moss,xx,y+.1,l*.36,.62,.016,.075);
    return g;
  }
  const near=dock(-4.3,8.25,6,4.6,1.08);
  // Steps descend from the path toward the near deck.
  for(let i=0;i<3;i++)box(near,M.wood,0,1.06+i*.15,2.48+i*.39,2.2,.18,.48);
  crate(near,-2.25,1.18,1.05,.76);cooler(near,2.12,1.18,1.15,.83);
  function chair(p,x,y,z,turn=0){
    const g=new THREE.Group();g.position.set(x,y,z);g.rotation.y=turn;p.add(g);
    box(g,M.teal,0,.52,0,.72,.07,.57);box(g,M.teal,0,.87,.27,.72,.65,.075,-.16);
    for(let xx of [-.34,.34]){
      beam(g,M.dark,new THREE.Vector3(xx,.03,-.34),new THREE.Vector3(xx,.69,.3),.045);
      beam(g,M.dark,new THREE.Vector3(xx,.03,.34),new THREE.Vector3(xx,.7,-.3),.045);
      beam(g,M.dark,new THREE.Vector3(xx,.48,.28),new THREE.Vector3(xx,1.19,.39),.045);
      box(g,M.dark,xx,.7,0,.045,.045,.6);
    }
  }
  chair(near,-.65,1.18,.25,-.25); chair(near,1.02,1.18,.18,.12);
  const floats=[];
  function rod(p,x,y,z,forward=-1){
    const a=new THREE.Vector3(x,y,z), b=new THREE.Vector3(x+.35,y+1.25,z+forward*2.9);
    beam(p,M.dark,a,b,.045);beam(p,M.paleWood,a,new THREE.Vector3(x+.09,y+.32,z+forward*.73),.075);
    cyl(p,M.metal,x+.08,y+.23,z+forward*.48,.19,.09,.19,Math.PI/2);
    const tipWorld=new THREE.Vector3(b.x,b.y,b.z);p.localToWorld(tipWorld);
    const end=new THREE.Vector3(tipWorld.x,WATER_Y+.06,tipWorld.z);
    beam(construction,M.cream,tipWorld,end,.012);
    const float=new THREE.Group(); float.position.copy(end); root.add(float);
    piece(float,sphereGeo,M.white,0,0,0,.17,.19,.17);
    piece(float,sphereGeo,M.red,0,.07,0,.14,.1,.14);
    floats.push(float);
  }
  construction.updateMatrixWorld(true);rod(near,1.7,1.34,-.7,-1);
  const back=dock(2,-7.9,5,4.35,1.26);crate(back,-1.55,1.36,.95,.85);cooler(back,.1,1.36,1.2,.72);cooler(back,1.25,1.36,.95,.64);
  construction.updateMatrixWorld(true);rod(back,.6,1.49,1.1,1);
  // Footbridge across the creek, with exposed bearers.
  const bridge=section(-13.6,landHeight(-13.6,-10.4)+.1,-10.4,.08);
  for(let i=0;i<10;i++)box(bridge,i%3?M.wood:M.paleWood,-2.0+i*.44,0,0,.4,.16,2.0);
  for(let z1 of [-.76,.76])box(bridge,M.darkWood,0,-.18,z1,4.55,.24,.22);
  for(let x1 of [-1.9,1.9])for(let z1 of [-.85,.85])box(bridge,M.darkWood,x1,-.45,z1,.2,.72,.2);
  // Canvas shelter and its camp furniture.
  const cy=landHeight(-2,-14.5), tent=section(-2,cy,-14.5);
  for(let xx of [-1.65,1.65])for(let zz of [-1.05,1.05])box(tent,M.darkWood,xx,1.15,zz,.12,2.3,.12);
  for(let xx of [-1.65,1.65])box(tent,M.darkWood,xx,2.22,0,.12,.12,2.35);
  for(let i=0;i<8;i++)box(tent,i%2?M.teal:M.cream,-1.54+i*.44,2.34,0,.445,.09,2.45,0,0,.04);
  for(let i=0;i<8;i++)box(tent,i%2?M.teal:M.cream,-1.54+i*.44,2.17,1.19,.445,.27,.07,0,0,.04);
  crate(tent,-1.05,0,-.25,.72);cooler(tent,1.05,0,-.26,.7);
  for(let x1 of [-.45,.48]){box(tent,M.paleWood,x1,.48,.57,.48,.1,.48);for(let a of [-.18,.18])for(let b of [-.18,.18])box(tent,M.darkWood,x1+a,.23,.57+b,.055,.46,.055);}
  // Mossy utility flatbed. Rounded panels and small layered parts keep the
  // silhouette readable from the fixed, elevated camera.
  const ty=landHeight(13.7,-9.3), truck=section(13.7,ty,-9.3,-.08);
  const paint=mat(0xa5b18b,tex.metal), paintLight=mat(0xc0c8a4,tex.metal);
  const trim=mat(0x46534b), steel=mat(0x89918a), tire=mat(0x252d29);
  const amber=mat(0xe0a04c), strap=mat(0x544c38), windowMat=mat(0x739e98,null,{roughness:.35,metalness:.12});
  // Round only the corners of a subdivided box, retaining indexed geometry
  // so the static material batching below can merge it with other pieces.
  function rounded(p,m,x,y,z,w,h,d,r){
    const g=new THREE.BoxGeometry(w,h,d,4,4,4), pos=g.attributes.position;
    for(let i=0;i<pos.count;i++){
      const v=new THREE.Vector3(pos.getX(i),pos.getY(i),pos.getZ(i));
      const inner=new THREE.Vector3(THREE.MathUtils.clamp(v.x,-w/2+r,w/2-r),THREE.MathUtils.clamp(v.y,-h/2+r,h/2-r),THREE.MathUtils.clamp(v.z,-d/2+r,d/2-r));
      const out=v.clone().sub(inner).normalize().multiplyScalar(r).add(inner);
      pos.setXYZ(i,out.x,out.y,out.z);
    }
    g.computeVertexNormals();return piece(p,g,m,x,y,z,1,1,1);
  }
  // Ladder chassis, two axles and a slightly projecting foot step.
  for(let zz of [-.65,.65])box(truck,trim,-.05,.46,zz,5.55,.2,.18);
  for(let xx of [-2.55,-.45,1.1,2.5])box(truck,trim,xx,.47,0,.15,.16,1.42);
  for(let xx of [-1.95,1.8])cyl(truck,steel,xx,.48,0,.15,2.1,.15,Math.PI/2);
  rounded(truck,paint,-1.38,1.05,0,1.58,.95,1.86,.13); // cab lower body
  rounded(truck,paintLight,-1.33,1.72,0,1.48,1.17,1.82,.15);
  rounded(truck,paint,-1.33,2.27,0,1.65,.19,1.99,.095);
  rounded(truck,paint,-2.35,1.07,0,1.15,.67,1.82,.16); // separate hood
  box(truck,paintLight,-2.35,1.414,0,.88,.025,1.32);
  // Sloping framed windshield, with split panes and paired wipers.
  box(truck,trim,-2.067,1.78,0,.065,.73,1.58,0,0,-.15);
  for(let zz of [-.39,.39])box(truck,windowMat,-2.105,1.78,zz,.024,.61,.72,0,0,-.15);
  box(truck,paintLight,-2.116,1.79,0,.032,.72,.055,0,0,-.15);
  for(let zz of [-.39,.39])box(truck,trim,-2.153,1.49,zz,.035,.035,.56,0,.22,0);
  // Side windows sit inside a dark gasket and a painted door outline.
  for(let side of [-1,1]){
    const z=side*.923;
    box(truck,trim,-1.35,1.78,z,.98,.68,.035);
    box(truck,windowMat,-1.35,1.79,z+side*.022,.86,.56,.025);
    box(truck,paintLight,-1.54,1.79,z+side*.04,.055,.63,.035);
    for(let xx of [-1.9,-.79])box(truck,trim,xx,1.29,z+side*.022,.025,.79,.025);
    box(truck,trim,-1.35,.92,z+side*.022,1.12,.024,.026);
    box(truck,steel,-.98,1.32,z+side*.05,.23,.055,.06);
    box(truck,trim,-1.32,.57,side*1.01,.96,.09,.3);
    // Mirror supported on thin angled arms.
    beam(truck,trim,new THREE.Vector3(-1.87,1.5,z),new THREE.Vector3(-2.03,1.75,side*1.22),.04);
    beam(truck,trim,new THREE.Vector3(-1.87,1.88,z),new THREE.Vector3(-2.03,1.75,side*1.22),.04);
    rounded(truck,trim,-2.04,1.76,side*1.23,.23,.27,.09,.035);
    // Wood slat rails with uprights and small fasteners.
    for(let yy of [1.13,1.47])box(truck,M.wood,.95,yy,side*.93,2.83,.19,.12);
    for(let xx of [-.34,.66,1.66,2.25]){
      box(truck,M.darkWood,xx,1.29,side*.99,.105,.62,.13);
      for(let yy of [1.13,1.47])cyl(truck,steel,xx,yy,side*1.065,.045,.025,.045,Math.PI/2);
    }
    // restrained edge chips on the doors and hood
    for(const [xx,yy,len] of [[-1.65,1.12,.16],[-1.05,.99,.12],[-2.48,1.22,.13]])
      box(truck,M.rust,xx,yy,side*.944,len,.018,.018,0,0,.06);
  }
  // Front grille, round lamps and protective bumper.
  rounded(truck,trim,-2.94,1.06,0,.1,.52,1.68,.045);
  for(let zz of [-.46,-.23,0,.23,.46])box(truck,steel,-3.003,1.06,zz,.035,.4,.07);
  for(let zz of [-.72,.72]){
    cyl(truck,steel,-3.02,1.17,zz,.29,.1,.29,0,0,Math.PI/2);
    cyl(truck,M.cream,-3.08,1.17,zz,.21,.035,.21,0,0,Math.PI/2);
    box(truck,amber,-3.04,.88,zz,.06,.11,.2);
  }
  rounded(truck,steel,-3.08,.57,0,.2,.16,2.07,.05);
  box(truck,trim,-3.19,.58,0,.035,.11,.48);
  // Bed planks and tailgate; a pair of straps ties the load down.
  for(let zz of [-.72,-.36,0,.36,.72])box(truck,M.wood,.95,.85,zz,2.92,.14,.33);
  for(let yy of [1.12,1.46])box(truck,M.wood,2.4,yy,0,.13,.19,1.96);
  for(let zz of [-.8,.8])box(truck,M.darkWood,2.47,1.28,zz,.12,.62,.1);
  crate(truck,.18,.94,-.35,.82);crate(truck,1.11,.94,.3,.9);crate(truck,1.95,.94,-.33,.65);
  for(let xx of [.18,1.11]){
    box(truck,strap,xx,1.72,xx<.5?-.35:.3,.075,.035,.76);
    box(truck,strap,xx,1.37,xx<.5?.01:.69,.075,.68,.035);
  }
  // Wheels: rounded sidewalls, recessed hubs, lug nuts and raised tread.
  for(let xx of [-1.95,1.8])for(let side of [-1,1]){
    const z=side*1.03;
    const wheel=new THREE.CylinderGeometry(.48,.48,.38,16,1); wheel.rotateX(Math.PI/2);
    piece(truck,wheel,tire,xx,.49,z,1,1,1);
    cyl(truck,trim,xx,.49,side*1.235,.63,.035,.63,Math.PI/2);
    cyl(truck,steel,xx,.49,side*1.26,.39,.05,.39,Math.PI/2);
    cyl(truck,trim,xx,.49,side*1.295,.15,.035,.15,Math.PI/2);
    for(let i=0;i<6;i++){
      const a=i*Math.PI/3; cyl(truck,M.cream,xx+.145*Math.sin(a),.49+.145*Math.cos(a),side*1.295,.035,.025,.035,Math.PI/2);
    }
    for(let i=0;i<12;i++){
      const a=i*Math.PI/6;
      box(truck,trim,xx+.47*Math.sin(a),.49+.47*Math.cos(a),z,.15,.055,.36,0,0,-a);
    }
    // segmented arch follows the tire rather than covering it with a slab.
    for(let i=0;i<7;i++){
      const a=-Math.PI/2+i*Math.PI/6;
      box(truck,paint,xx+.59*Math.sin(a),.49+.59*Math.cos(a),side*1.02,.25,.12,.28,0,0,-a);
    }
  }
  // Exhaust stack behind the cab, with a dark open end.
  cyl(truck,steel,-.55,1.43,-.78,.09,1.42,.09);
  cyl(truck,trim,-.55,2.15,-.78,.14,.08,.14);
  for(let i=0;i<4;i++)box(truck,M.moss,-.1+i*.55,1.25,-1.065,.25,.035,.025,0,0,.1*i);
  // Scattered useful equipment near the shelter and truck.
  crate(construction,10.8,landHeight(10.8,-11.5),-11.5,.75);cooler(construction,10.3,landHeight(10.3,-10.3),-10.3,.8);
  crate(construction,-4.3,landHeight(-4.3,-14.7),-14.7,.75);cooler(construction,1.0,landHeight(1,-14.5),-14.5,.8);
  function fence(x,z,angle,len=3){const g=section(x,landHeight(x,z),z,angle); for(let xx of [-len/2,0,len/2]){box(g,M.darkWood,xx,.62,0,.16,1.24,.16);box(g,M.endWood,xx,1.26,0,.18,.06,.18);}for(let yy of [.43,.91])box(g,M.wood,0,yy,0,len+.1,.17,.11);}
  fence(6.3,-10.6,.15,3.1);fence(-8.4,10.7,-.35,2.7);fence(12.8,3.7,.8,2.5);
  function obelisk(x,z){
    const g=section(x,landHeight(x,z),z);const geo=new THREE.CylinderGeometry(.24,.51,2.35,4,1);geo.rotateY(Math.PI/4);piece(g,geo,M.dark,0,1.18,0,1,1,1);
    box(g,M.lamp,.005,1.27,.355,.12,1.2,.025);box(g,M.metal,0,.1,0,.78,.2,.78);
  }
  obelisk(-9.8,-10.0);obelisk(10.5,10.5);
  // Bake all static transforms into a small material-indexed set of meshes.
  construction.updateMatrixWorld(true);
  const buckets=new Map();let pieces=0;
  construction.traverse(o=>{if(!o.isMesh)return;const geom=o.geometry.clone();geom.applyMatrix4(o.matrixWorld);let arr=buckets.get(o.material);if(!arr)buckets.set(o.material,arr=[]);arr.push(geom);pieces++;});
  for(const [material,geometries] of buckets){const merged=mergeGeometries(geometries,false);const mesh=new THREE.Mesh(merged,material);mesh.castShadow=true;mesh.receiveShadow=true;root.add(mesh);geometries.forEach(g=>g.dispose());}
  return {group:root,update(time){floats.forEach((b,i)=>{b.position.y=WATER_Y+.06+Math.sin(time*2+i)*.035;});},stats:{staticPieces:pieces,staticDrawCalls:buckets.size,animatedFloats:floats.length}};
}
