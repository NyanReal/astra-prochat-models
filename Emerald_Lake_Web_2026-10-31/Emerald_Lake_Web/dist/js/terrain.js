import * as THREE from 'three';
import { WATER_Y, ISLAND, STREAM, lakePoint, lakeMetric, landHeight, pathDistance, streamDistance, rng } from './world.js';

// The same analytic outline drives both the land rim and the animated lake.
export function createTerrain(ctx = {}) {
  const group = new THREE.Group();
  group.name = 'terrain-and-water';
  const rand = rng(28371);
  const quality = ctx.quality === 'high' ? 'high' : 'balanced';
  const tex = ctx.textures || {};
  const mesh = (geometry, material, name) => {
    const object = new THREE.Mesh(geometry, material);
    object.name = name; object.receiveShadow = true; group.add(object); return object;
  };
  const clamp = THREE.MathUtils.clamp;
  const mix = THREE.MathUtils.lerp;
  const streamInfo = (x,z) => {
    let d=1e4, y=0;
    for (let i=0;i<STREAM.length-1;i++) {
      const a=STREAM[i], b=STREAM[i+1], dx=b.x-a.x, dz=b.z-a.z;
      const t=clamp(((x-a.x)*dx+(z-a.z)*dz)/(dx*dx+dz*dz),0,i===STREAM.length-2?1.4:1);
      const n=Math.hypot(x-a.x-dx*t,z-a.z-dz*t);
      if(n<d){ d=n; const drop=THREE.MathUtils.smoothstep(t,.51,.76); y=mix(a.y,b.y,Math.min(1,.16*t+.84*drop)); }
    }
    return {d,y};
  };
  const terrainHeight = (x,z,shore) => {
    let h=landHeight(x,z);
    const s=streamInfo(x,z);
    if(shore!==undefined) h=mix(WATER_Y+.12,h,THREE.MathUtils.smoothstep(shore,0,2.2));
    // Cut the channel after the shore blend so the creek mouth is never sealed by a soil berm.
    if(s.d<2.5) h=mix(Math.min(h,s.y-.48),h,THREE.MathUtils.smoothstep(s.d,1.25,2.5));
    return h;
  };
  const groundMap = tex.ground ? tex.ground.clone() : null;
  if(groundMap){groundMap.wrapS=groundMap.wrapT=THREE.RepeatWrapping;groundMap.needsUpdate=true;}
  const grassMap = tex.grass ? tex.grass.clone() : null;
  if(grassMap){grassMap.wrapS=grassMap.wrapT=THREE.RepeatWrapping;grassMap.needsUpdate=true;}
  const earth = new THREE.MeshStandardMaterial({color:0xffffff,vertexColors:true,roughness:1, map:grassMap || groundMap});
  earth.userData.ownedTextures=[groundMap,grassMap].filter(Boolean);
  if(grassMap && groundMap){
    earth.onBeforeCompile=shader=>{
      shader.uniforms.pathMap={value:groundMap};
      shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nattribute float pathWeight; varying float vPathWeight;').replace('#include <begin_vertex>','#include <begin_vertex>\nvPathWeight=pathWeight;');
      shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nuniform sampler2D pathMap; varying float vPathWeight;').replace('#include <map_fragment>','vec4 grassTex=texture2D(map,vMapUv); grassTex.rgb=mix(vec3(.12,.23,.035),grassTex.rgb,.40); vec4 pathTex=texture2D(pathMap,vMapUv); pathTex.rgb*=vec3(.96,.91,.82); diffuseColor *= mix(grassTex,pathTex,vPathWeight);');
    };
    earth.customProgramCacheKey=()=> 'terrain-grass-path-v1';
  }
  const N=quality==='high'?192:144, M=quality==='high'?48:36;
  const p=[], c=[], uv=[], weights=[], idx=[];
  const grass=new THREE.Color('#607f38'), grassLight=new THREE.Color('#8c9f49'), path=new THREE.Color('#c9a568'), shoreColor=new THREE.Color('#8c9c5b');
  for(let i=0;i<=N;i++){
    const a=i/N*Math.PI*2, q=lakePoint(a), dx=Math.cos(a), dz=Math.sin(a);
    // Radial rays end on the square outer boundary, preserving a continuous ground mesh.
    const reach=Math.min(dx>0?(26-q.x)/dx:dx<0?(-26-q.x)/dx:1e6,dz>0?(26-q.z)/dz:dz<0?(-26-q.z)/dz:1e6);
    for(let j=0;j<=M;j++){
      const t=j/M, dist=reach*t, x=q.x+dx*dist,z=q.z+dz*dist;
      p.push(x,terrainHeight(x,z,dist),z); uv.push(x/4,z/4);
      const pd=pathDistance(x,z), pathMix=1-THREE.MathUtils.smoothstep(pd,.8,1.5);
      weights.push(pathMix);
      if(grassMap && groundMap){
        const shade=.92+.08*Math.sin(x*.7)*Math.cos(z*.54);
        c.push(shade,shade,shade);
      } else {
        const color=grass.clone().lerp(grassLight,.35+.2*Math.sin(x*.7)*Math.cos(z*.54));
        color.lerp(path,pathMix);color.lerp(shoreColor,(1-THREE.MathUtils.smoothstep(dist,0,2.0))*.45);
        c.push(color.r,color.g,color.b);
      }
      if(i<N&&j<M){const k=i*(M+1)+j;idx.push(k,k+M+1,k+1,k+1,k+M+1,k+M+2);}
    }
  }
  const groundGeo=new THREE.BufferGeometry();
  groundGeo.setAttribute('position',new THREE.Float32BufferAttribute(p,3));
  groundGeo.setAttribute('color',new THREE.Float32BufferAttribute(c,3));
  groundGeo.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
  groundGeo.setAttribute('pathWeight',new THREE.Float32BufferAttribute(weights,1));
  groundGeo.setIndex(idx); groundGeo.computeVertexNormals();
  mesh(groundGeo,earth,'sculpted shore and paths');

  // Subtle vertical cut edge gives the scene a finished diorama silhouette.
  const skirtP=[], skirtI=[];
  for(let i=0;i<=N;i++){
    const a=i/N*Math.PI*2,q=lakePoint(a),dx=Math.cos(a),dz=Math.sin(a);
    const reach=Math.min(dx>0?(26-q.x)/dx:dx<0?(-26-q.x)/dx:1e6,dz>0?(26-q.z)/dz:dz<0?(-26-q.z)/dz:1e6);
    const x=q.x+dx*reach,z=q.z+dz*reach;
    skirtP.push(x,terrainHeight(x,z,reach),z,x,-1.9,z);
    if(i<N){let k=i*2;skirtI.push(k,k+1,k+2,k+1,k+3,k+2);}
  }
  const skirt=new THREE.BufferGeometry();skirt.setAttribute('position',new THREE.Float32BufferAttribute(skirtP,3));skirt.setIndex(skirtI);skirt.computeVertexNormals();
  mesh(skirt,new THREE.MeshStandardMaterial({color:'#576747',roughness:1,side:THREE.DoubleSide}),'earth edge');

  const waterP=[0,WATER_Y,0], waterUV=[0,0], waterI=[];
  const rings=20;
  for(let j=1;j<=rings;j++) for(let i=0;i<N;i++){
    const a=i/N*Math.PI*2,q=lakePoint(a),r=j/rings;
    waterP.push(q.x*r,WATER_Y,q.z*r);waterUV.push(q.x*r,q.z*r);
  }
  for(let i=0;i<N;i++)waterI.push(0,1+(i+1)%N,1+i);
  for(let j=0;j<rings-1;j++)for(let i=0;i<N;i++){
    const a=1+j*N+i,b=1+j*N+(i+1)%N,c0=a+N,d=b+N;
    waterI.push(a,b,c0,b,d,c0);
  }
  const waterGeo=new THREE.BufferGeometry();waterGeo.setAttribute('position',new THREE.Float32BufferAttribute(waterP,3));waterGeo.setAttribute('uv',new THREE.Float32BufferAttribute(waterUV,2));waterGeo.setIndex(waterI);waterGeo.computeVertexNormals();
  const bedMap=tex.waterbed ? tex.waterbed.clone() : new THREE.DataTexture(new Uint8Array([180,200,170,255]),1,1);
  bedMap.wrapS=bedMap.wrapT=THREE.RepeatWrapping; bedMap.needsUpdate=true;
  const waterMat=new THREE.ShaderMaterial({
    uniforms:{uTime:{value:0},uBed:{value:bedMap}}, side:THREE.DoubleSide,
    vertexShader:`varying vec2 vWorld; void main(){vWorld=position.xz; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`uniform float uTime; uniform sampler2D uBed; varying vec2 vWorld;
      float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
      void main(){
        float r=length(vWorld/vec2(13.4,9.7));
        float shore=smoothstep(.32,1.02,r);
        vec2 cell=floor(vWorld*1.05), f=fract(vWorld*1.05);
        float pebbles=0.0;
        for(int y=-1;y<=1;y++) for(int x=-1;x<=1;x++){
          vec2 n=vec2(float(x),float(y)); vec2 id=cell+n;
          vec2 center=n+vec2(hash(id),hash(id+19.7));
          float radius=.22+.12*hash(id+8.1);
          pebbles=max(pebbles,(1.0-smoothstep(radius-.05,radius+.05,length((f-center)*vec2(1.0,1.25))))*(.55+.45*hash(id+4.0)));
        }
        vec3 bed=texture2D(uBed,vWorld/5.0).rgb;
        vec2 p=vWorld*.9;
        float wave=sin(p.x*1.45+p.y*.8+uTime*.5)*sin(p.y*1.9-p.x*.55-uTime*.35);
        float noise=hash(floor((vWorld+vec2(uTime*.07,0.0))*4.0))*.5+hash(floor(vWorld*8.0))*.5;
        float glint=pow(max(0.0,sin(p.x*2.9+sin(p.y*1.7+uTime*.35))*sin(p.y*2.4-uTime*.25)),10.0);
        vec3 deep=vec3(.008,.15,.22), shallow=vec3(.025,.37,.37);
        vec3 col=mix(deep,shallow,shore);
        col+=(bed-vec3(.3))*(.06+.14*shore) + pebbles*(.025+.05*shore)*vec3(.65,1.0,.8);
        col+=vec3(.008,.018,.018)*wave+vec3(.006,.014,.013)*(noise-.5)+vec3(.015,.03,.027)*glint;
        gl_FragColor=vec4(col,1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`});
  mesh(waterGeo,waterMat,'animated turquoise lake');

  const stoneMat=new THREE.MeshStandardMaterial({color:'#d0c8a9',roughness:.96,map:tex.stone||null,flatShading:true});
  const rockGeo=new THREE.IcosahedronGeometry(1,1);
  // Distorted reusable angular boulder preserves facets under instance rotation.
  const rp=rockGeo.attributes.position;
  for(let i=0;i<rp.count;i++){let x=rp.getX(i),y=rp.getY(i),z=rp.getZ(i);const f=.83+.18*Math.sin(x*8+y*5+z*11);rp.setXYZ(i,x*f,y*f,z*f);}
  rockGeo.computeVertexNormals();
  const rocks=[];
  const beneathDock=(x,z)=>(Math.abs(x+4.3)<3.45&&z>5.55&&z<11.0)||(Math.abs(x-2)<2.9&&z>-10.4&&z<-5.35)|| (Math.abs(x+13.6)<2.35&&Math.abs(z+10.4)<1.12);
  const addRock=(x,y,z,sx,sy,sz,rot=0)=>{const color=new THREE.Color().setHSL(.12+rand()*.03,.14+rand()*.10,.62+rand()*.17);if(!beneathDock(x,z) && !(streamInfo(x,z).d<1.35 && z<-4.7) && !(x>10.2 && x<17.0 && z>-11.4 && z<-7.3))rocks.push({x,y,z,sx,sy,sz,rot,color});};
  for(let i=0;i<155;i++){
    const a=i/155*Math.PI*2+(rand()-.5)*.035;
    // Alternating clusters and gaps avoid an even stone necklace.
    const cluster=Math.sin(a*9.0+1.2)+.55*Math.sin(a*17.0-.8);
    if(cluster<-.45 && rand()<.84) continue;
    if(rand()<.22) continue;
    const q=lakePoint(a,(rand()-.48)*1.5);
    const s=.25+rand()*.61+(rand()<.13?.35:0);addRock(q.x,WATER_Y+.09+s*.25,q.z,s*(.75+rand()*.8),s*(.65+rand()*.9),s*(.75+rand()*.8),rand()*6.3);
  }
  for(let i=0;i<27;i++){
    const a=i/27*Math.PI*2, x=ISLAND.x+Math.cos(a)*(ISLAND.rx-.13),z=ISLAND.z+Math.sin(a)*(ISLAND.rz-.13),s=.4+rand()*.5;
    addRock(x,.42,z,s,s*(.85+rand()*.5),s,rand()*6.3);
  }
  for(let i=0;i<54;i++){
    const segment=Math.floor(rand()*(STREAM.length-1)),a=STREAM[segment],b=STREAM[segment+1],t=rand(),dx=b.x-a.x,dz=b.z-a.z,len=Math.hypot(dx,dz),side=rand()<.5?-1:1;
    const x=mix(a.x,b.x,t)-dz/len*side*(1.25+rand()*.6),z=mix(a.z,b.z,t)+dx/len*side*(1.25+rand()*.6),s=.28+rand()*.45;
    addRock(x,mix(a.y,b.y,t)+.02,z,s,s*(.7+rand()*.6),s,rand()*6.3);
  }
  for(let i=0;i<45;i++){
    const a=rand()*Math.PI*2,q=lakePoint(a,1.1+rand()*7),x=q.x,z=q.z;
    if(Math.abs(x)<25&&Math.abs(z)<25&&pathDistance(x,z)>1.4&&streamDistance(x,z)>2.2){const s=.2+rand()*.45;addRock(x,terrainHeight(x,z)+s*.15,z,s,s*.8,s,rand()*6.3);}
  }
  // A half bowl of stones contains the spring instead of exposing a straight sheet edge.
  const head=STREAM[0], headNext=STREAM[1], headLength=Math.hypot(headNext.x-head.x,headNext.z-head.z);
  const headTx=(headNext.x-head.x)/headLength,headTz=(headNext.z-head.z)/headLength,headRand=rng(8721);
  for(let i=0;i<7;i++){
    const a=-Math.PI*.5+i/6*Math.PI,side=Math.sin(a)*1.04,along=.57-Math.cos(a)*.68;
    const s=.32+headRand()*.12;
    rocks.push({x:head.x+headTx*along-headTz*side,y:head.y+.03,z:head.z+headTz*along+headTx*side,
      sx:s*1.22,sy:s*.93,sz:s,rot:headRand()*6.28,color:new THREE.Color('#b8b194')});
  }
  const inst=new THREE.InstancedMesh(rockGeo,stoneMat,rocks.length);inst.name='angular shore boulders';inst.castShadow=true;inst.receiveShadow=true;
  const dummy=new THREE.Object3D(); rocks.forEach((r,i)=>{dummy.position.set(r.x,r.y,r.z);dummy.rotation.set(0,r.rot,0);dummy.scale.set(r.sx,r.sy,r.sz);dummy.updateMatrix();inst.setMatrixAt(i,dummy.matrix);inst.setColorAt(i,r.color);});inst.instanceMatrix.needsUpdate=true;group.add(inst);
  // Small irregular olive caps read as moss on the sunlit stones.
  const mossMat=new THREE.MeshStandardMaterial({color:'#778d39',roughness:1,flatShading:true});
  const mossGeo=new THREE.IcosahedronGeometry(1,0), moss=new THREE.InstancedMesh(mossGeo,mossMat,rocks.length);
  rocks.forEach((r,i)=>{dummy.position.set(r.x,r.y+r.sy*.65,r.z);dummy.rotation.set(0,r.rot,0);dummy.scale.set(r.sx*.56,r.sy*.12,r.sz*.52);dummy.updateMatrix();moss.setMatrixAt(i,dummy.matrix);});moss.instanceMatrix.needsUpdate=true;moss.receiveShadow=true;moss.name='moss on rocks';group.add(moss);

  // Larger faceted limestone ledges interrupt the smaller shoreline stones.
  const blockGeo=new THREE.BoxGeometry(1,1,1,1,1,1);
  const bp=blockGeo.attributes.position;
  for(let i=0;i<bp.count;i++){
    const x=bp.getX(i),y=bp.getY(i),z=bp.getZ(i);
    bp.setXYZ(i,x*(y>0?.82:1),y,z*(y>0?.84:1));
  }
  blockGeo.computeVertexNormals();
  const blocks=[];
  for(const a of [.26,1.04,2.0,2.7,3.58,4.2,5.38,5.85]){
    for(let j=0;j<3;j++){
      const q=lakePoint(a+(j-1)*.045,.25+rand()*.5);
      if(beneathDock(q.x,q.z) || streamInfo(q.x,q.z).d<1.8)continue;
      blocks.push({x:q.x,z:q.z,y:.55+rand()*.17,sx:.85+rand()*.55,sy:1.05+rand()*.5,sz:.7+rand()*.45,rot:a+rand()*.25});
    }
  }
  const outcrops=new THREE.InstancedMesh(blockGeo,stoneMat,blocks.length);
  blocks.forEach((b,i)=>{dummy.position.set(b.x,b.y,b.z);dummy.rotation.set(0,b.rot,0);dummy.scale.set(b.sx,b.sy,b.sz);dummy.updateMatrix();outcrops.setMatrixAt(i,dummy.matrix);});
  outcrops.instanceMatrix.needsUpdate=true;outcrops.castShadow=true;outcrops.receiveShadow=true;outcrops.name='limestone ledges';group.add(outcrops);
  const crackP=[];
  for(const b of blocks){
    const y=b.y+b.sy*.5+.01, cs=Math.cos(b.rot), sn=Math.sin(b.rot);
    const point=(x,z)=>[b.x+x*cs+z*sn,y,b.z-x*sn+z*cs];
    crackP.push(...point(-b.sx*.22,-b.sz*.3),...point(-b.sx*.04,0),...point(-b.sx*.04,0),...point(b.sx*.16,b.sz*.24));
  }
  const crackGeo=new THREE.BufferGeometry();crackGeo.setAttribute('position',new THREE.Float32BufferAttribute(crackP,3));
  const cracks=new THREE.LineSegments(crackGeo,new THREE.LineBasicMaterial({color:'#807a62',transparent:true,opacity:.65}));cracks.name='limestone cracks';group.add(cracks);
  // Low island crown conceals the water beneath it and follows the shared island footprint.
  const islandGeo=new THREE.SphereGeometry(1,24,10,0,Math.PI*2,0,Math.PI*.5);
  const island=mesh(islandGeo,new THREE.MeshStandardMaterial({color:'#819947',roughness:1,map:tex.grass||null}),'island');island.position.set(ISLAND.x,.25,ISLAND.z);island.scale.set(ISLAND.rx, .83, ISLAND.rz);island.castShadow=true;

  // A small feathered alpha map softens the edges of real ribbon geometry.
  const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;
  const cx=canvas.getContext('2d'), grad=cx.createRadialGradient(64,64,5,64,64,63);
  grad.addColorStop(0,'rgba(255,255,255,0.95)');grad.addColorStop(.48,'rgba(255,255,255,0.85)');
  grad.addColorStop(.78,'rgba(255,255,255,0.45)');grad.addColorStop(1,'rgba(255,255,255,0)');
  cx.fillStyle=grad;cx.fillRect(0,0,128,128);
  const foamTexture=new THREE.CanvasTexture(canvas);foamTexture.colorSpace=THREE.SRGBColorSpace;
  const foamMat=new THREE.MeshBasicMaterial({color:'#edfff3',map:foamTexture,transparent:true,opacity:.91,side:THREE.DoubleSide,depthWrite:false});
  foamMat.userData.ownedTextures=[foamTexture];
  const blueMat=new THREE.ShaderMaterial({side:THREE.DoubleSide,transparent:true,depthWrite:false,uniforms:{uTime:{value:0},uBed:{value:bedMap}},
    vertexShader:`attribute float aeration; varying float vAir; varying vec2 vFlow; varying vec2 vWorld;
      void main(){vAir=aeration;vFlow=uv;vWorld=position.xz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`uniform float uTime;uniform sampler2D uBed;varying float vAir;varying vec2 vFlow;varying vec2 vWorld;
      float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
      float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
        return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
      void main(){
        vec3 bed=texture2D(uBed,vWorld/4.0).rgb;
        float current=sin(vFlow.x*17.0+sin(vFlow.y*8.0-uTime*.7)*1.5)*sin(vFlow.y*14.0-uTime*1.3);
        float fleck=hash(floor(vWorld*8.0))*.5+hash(floor(vWorld*3.0))*.5;
        // Elongated moving noise makes strands merge, break and change width.
        float flowY=vFlow.y*8.0-uTime*.72;
        float warp=noise(vec2(vFlow.x*6.0,flowY*.52))-.5;
        float ribbons=noise(vec2(vFlow.x*25.0+warp*1.7,flowY*1.3));
        float fine=noise(vec2(vFlow.x*74.0+warp*2.5,flowY*3.1));
        float white=smoothstep(.49,.73,ribbons*.74+fine*.26);
        float threads=pow(max(0.0,sin(vFlow.x*102.0+warp*6.0)),9.0)*smoothstep(.36,.64,fine);
        vec3 col=vec3(.012,.27,.31)+(bed-vec3(.4))*.13+vec3(.012,.028,.03)*current+vec3(.012,.025,.03)*(fleck-.5);
        col=mix(col,vec3(.045,.40,.42),vAir*.32);
        col=mix(col,vec3(.76,.94,.88),vAir*white*.91+threads*(.035+.27*vAir));
        float edge=smoothstep(0.0,.018,vFlow.x)*(1.0-smoothstep(.982,1.0,vFlow.x));
        float mouth=1.0-smoothstep(3.02,3.37,vFlow.y);
        gl_FragColor=vec4(col,edge*mouth);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`});
  blueMat.userData.kind='creek';
  const ledgeMat=new THREE.MeshStandardMaterial({color:'#526b61',roughness:1,flatShading:true});
  const pool={p:[],uv:[],i:[]},falls={p:[],uv:[],i:[]},foam={p:[],uv:[],i:[]};
  // Add a strip as connected pairs. Each strip has its own UVs, including both ends.
  const strip=(bag, rows)=>{
    const base=bag.p.length/3;
    rows.forEach((r,j)=>{bag.p.push(...r[0],...r[1]);bag.uv.push(0,j/(rows.length-1),1,j/(rows.length-1));
      if(j){const k=base+j*2;bag.i.push(k-2,k-1,k,k-1,k+1,k);}});
  };
  const ellipsePatch=(bag,x,y,z,rx,rz,angle=0)=>{
    const ca=Math.cos(angle),sa=Math.sin(angle),row=[];
    for(let j=0;j<=8;j++){const v=j/8*2-1, half=Math.sqrt(Math.max(0,1-v*v));
      const pts=[];for(const u of [-half,half]){const xx=u*rx,zz=v*rz;pts.push([x+xx*ca-zz*sa,y,z+xx*sa+zz*ca]);}row.push(pts);}
    strip(bag,row);
  };
  const foamArc=(x,z,rx,rz,start,length,y,width,phase=0)=>{
    const rows=[],n=13;
    for(let i=0;i<=n;i++){
      const t=i/n,a=start+length*t, wig=.045*Math.sin(a*7+phase)+.025*Math.sin(a*13-phase);
      const taper=Math.pow(Math.sin(Math.PI*t),.55), w=width*taper*(.75+.25*Math.sin(phase+i*1.5));
      rows.push([[x+Math.cos(a)*(rx+wig-w),y,z+Math.sin(a)*(rz+wig-w)],
                 [x+Math.cos(a)*(rx+wig+w),y,z+Math.sin(a)*(rz+wig+w)]]);
    }strip(foam,rows);
  };
  // Broken foam bands hug exposed rocks; individual gaps keep the shore irregular.
  for(let i=0;i<rocks.length&&i<182;i+=2){const r=rocks[i];if(lakeMetric(r.x,r.z)>1.09 || Math.hypot(r.x-ISLAND.x,r.z-ISLAND.z)<3.4)continue;
    // Center the broken arc on the inward-facing side, beyond each boulder's footprint.
    const toward=Math.atan2(-r.z,-r.x), shift=.25;
    const x=r.x+Math.cos(toward)*shift,z=r.z+Math.sin(toward)*shift;
    const radius=Math.max(r.sx,r.sz)*1.12+.23;
    foamArc(x,z,radius,radius,toward-.65,1.25+rand()*.35,WATER_Y+.055,.085+rand()*.04,i);
    if(i%4===0)foamArc(x,z,radius+.22,radius+.22,toward-.38,.65+rand()*.35,WATER_Y+.056,.055,i+2);
  }
  // Follow individual island boulders instead of tracing an evenly dashed ellipse.
  const islandFoamRand=rng(13794);
  for(const [i,r] of rocks.entries()){
    if(Math.abs(r.y-.42)>.0001 || islandFoamRand()<.28)continue;
    const outward=Math.atan2(r.z-ISLAND.z,r.x-ISLAND.x),length=.55+islandFoamRand()*.90;
    const rx=r.sx*1.05+.15,rz=r.sz*1.05+.15,start=outward-length*.5+(islandFoamRand()-.5)*.32;
    foamArc(r.x,r.z,rx,rz,start,length,WATER_Y+.06,.045+islandFoamRand()*.045,i*.61);
    if(islandFoamRand()<.26)foamArc(r.x,r.z,rx+.18,rz+.18,start+.22,length*.62,WATER_Y+.061,.035,i+1);
  }
  // A single subdivided sheet flows down each reach and rolls over staggered lips.
  const ledges=[], air=[];
  for(let i=0;i<STREAM.length-1;i++){
    const a=STREAM[i],b=STREAM[i+1],dx=b.x-a.x,dz=b.z-a.z,len=Math.hypot(dx,dz),tx=dx/len,tz=dz/len,nx=-tz,nz=tx;
    const adjacentNormal=(from,to)=>{const x=to.x-from.x,z=to.z-from.z,l=Math.hypot(x,z);return [-z/l,x/l];};
    const prior=i?adjacentNormal(STREAM[i-1],a):[nx,nz],next=i<STREAM.length-2?adjacentNormal(b,STREAM[i+2]):[nx,nz];
    const point=(t,side=0)=>{const bend=.16*Math.sin(Math.PI*Math.min(t,1))*(i%2?1:-1),
      before=(1-THREE.MathUtils.smoothstep(t,0,.24))*.5,after=THREE.MathUtils.smoothstep(t,.76,1)*.5;
      let ux=nx*(1-before-after)+prior[0]*before+next[0]*after,uz=nz*(1-before-after)+prior[1]*before+next[1]*after;
      const magnitude=Math.hypot(ux,uz);ux/=magnitude;uz/=magnitude;
      return [mix(a.x,b.x,t)+ux*(side+bend),mix(a.z,b.z,t)+uz*(side+bend)];};
    const lipPhase=side=>.068*Math.sin(side*3.3+i*2.2)+.023*Math.sin(side*7+i);
    const waterY=(t,side=0)=>{const phase=lipPhase(side);
      const y=mix(a.y,b.y,Math.min(1,.16*t+.84*THREE.MathUtils.smoothstep(t,.50+phase,.77+phase)))+.075;
      return i===STREAM.length-2?y-.087*THREE.MathUtils.smoothstep(t,1,1.38):y;};
    const width=t=>mix(a.w,b.w,Math.min(t,1))*(.47+(.065*Math.sin(t*Math.PI*2+i*2)+.016*Math.sin(t*19+i))*Math.sin(Math.min(t,1)*Math.PI));
    const rows=48,cols=14,end=i===STREAM.length-2?1.4:1;
    const base=pool.p.length/3;
    for(let j=0;j<=rows;j++){const rowT=end*j/rows,w=width(rowT);
      for(let k=0;k<=cols;k++){const cross=k/cols*2-1;
        const t=rowT+(i===0?.17*(1-Math.sqrt(Math.max(0,1-cross*cross)))*(1-THREE.MathUtils.smoothstep(rowT,0,.25)):0);
        const side=cross*w,q=point(t,side),phase=lipPhase(side);
        pool.p.push(q[0],waterY(t,side),q[1]);pool.uv.push(k/cols,i+t);
        air.push(THREE.MathUtils.smoothstep(t,.46+phase,.55+phase)*(1-THREE.MathUtils.smoothstep(t,.75+phase,.86+phase)));
        if(j<rows&&k<cols){const q0=base+j*(cols+1)+k;pool.i.push(q0,q0+1,q0+cols+1,q0+1,q0+cols+2,q0+cols+1);}
      }
    }
    const bottom=waterY(.80), toe=point(.8);
    // Low partially submerged stones support the sheet; they do not form a wall.
    for(let j=0;j<2;j++){const t=.47+j*.28,side=(j?1:-1)*width(t)*.85,pp=point(t,side);
      ledges.push({x:pp[0],y:waterY(t,side)-.28,z:pp[1],sx:.22+rand()*.10,sy:.12,sz:.18+rand()*.08});}
    for(let j=0;j<12;j++){const q=point(.79+rand()*.14,(rand()-.5)*width(.8)*1.65);
      ellipsePatch(foam,q[0],bottom+.052,q[1],.10+rand()*.20,.08+rand()*.19,rand()*6.28);}
    for(let j=0;j<4;j++){const q=point(.86+rand()*.10,(rand()-.5)*.8);
      foamArc(q[0],q[1],.32+j*.15,.16+j*.08,rand()*6.2,.9+rand()*.8,bottom+.058,.065,j+i);}
  }
  const ledgeGeo=new THREE.IcosahedronGeometry(1,1),ledgeMesh=new THREE.InstancedMesh(ledgeGeo,ledgeMat,ledges.length);
  ledges.forEach((r,i)=>{dummy.position.set(r.x,r.y,r.z);dummy.rotation.set(0,i*1.7,0);dummy.scale.set(r.sx,r.sy,r.sz);dummy.updateMatrix();ledgeMesh.setMatrixAt(i,dummy.matrix);});
  ledgeMesh.instanceMatrix.needsUpdate=true;ledgeMesh.name='submerged cascade ledges';group.add(ledgeMesh);
  const makeGeo=bag=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(bag.p,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(bag.uv,2));g.setIndex(bag.i);g.computeVertexNormals();return g;};
  const creekGeo=makeGeo(pool);creekGeo.setAttribute('aeration',new THREE.Float32BufferAttribute(air,1));
  mesh(creekGeo,blueMat,'continuous creek');
  const foamMesh=mesh(makeGeo(foam),foamMat,'broken shore and cascade foam');
  const foamPositions=foamMesh.geometry.attributes.position, foamBase=foamPositions.array.slice();
  return {group,update(time){
    waterMat.uniforms.uTime.value=time;blueMat.uniforms.uTime.value=time;foamMat.opacity=.85+.06*Math.sin(time*1.1);
    for(let i=0;i<foamPositions.count;i++){const k=i*3,x=foamBase[k],z=foamBase[k+2];
      foamPositions.array[k]=x+.025*Math.sin(time*.7+z*.7);foamPositions.array[k+2]=z+.018*Math.cos(time*.65+x*.6);}
    foamPositions.needsUpdate=true;
  },stats:{rocks:rocks.length,terrainDrawCalls:14,water:'animated lake and foam',quality}};
}
