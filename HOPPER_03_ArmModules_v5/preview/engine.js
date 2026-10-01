/* HOPPER static GLB viewer. No dependencies, build step, CDN or viewer-only animation.
   Reads glTF 2.0 meshes, embedded PNGs, rigid node hierarchy and animation channels.
   This viewer intentionally targets the supplied asset, not every glTF extension. */
'use strict';
const HM = (() => {
  const add=(a,b)=>a.map((v,i)=>v+b[i]), sub=(a,b)=>a.map((v,i)=>v-b[i]);
  const mul=(a,s)=>a.map(v=>v*s), dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const norm=a=>mul(a,1/(Math.hypot(...a)||1));
  const ident=()=>new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
  const mm=(a,b)=>{const r=new Float32Array(16);for(let c=0;c<4;c++)for(let row=0;row<4;row++)for(let k=0;k<4;k++)r[c*4+row]+=a[k*4+row]*b[c*4+k];return r;};
  const trs=(t,q,s)=>{
    const [x,y,z,w]=q, x2=x+x,y2=y+y,z2=z+z,xx=x*x2,xy=x*y2,xz=x*z2,yy=y*y2,yz=y*z2,zz=z*z2,wx=w*x2,wy=w*y2,wz=w*z2;
    return new Float32Array([(1-yy-zz)*s[0],(xy+wz)*s[0],(xz-wy)*s[0],0,(xy-wz)*s[1],(1-xx-zz)*s[1],(yz+wx)*s[1],0,(xz+wy)*s[2],(yz-wx)*s[2],(1-xx-yy)*s[2],0,...t,1]);
  };
  const look=(eye,target,up=[0,1,0])=>{const z=norm(sub(eye,target)),x=norm(cross(up,z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);};
  const persp=(fov,aspect,near,far)=>{const f=1/Math.tan(fov/2),d=1/(near-far);return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*d,-1,0,0,2*far*near*d,0]);};
  const ortho=(l,r,b,t,n,f)=>new Float32Array([2/(r-l),0,0,0,0,2/(t-b),0,0,0,0,-2/(f-n),0,-(r+l)/(r-l),-(t+b)/(t-b),-(f+n)/(f-n),1]);
  const normal=m=>{
    const a=[m[0],m[1],m[2]],b=[m[4],m[5],m[6]],c=[m[8],m[9],m[10]],bc=cross(b,c),ca=cross(c,a),ab=cross(a,b),d=dot(a,bc)||1;
    return new Float32Array([...mul(bc,1/d),...mul(ca,1/d),...mul(ab,1/d)]);
  };
  const slerp=(a,b,t)=>{let d=dot(a,b);if(d<0){b=mul(b,-1);d=-d;}if(d>.9995)return norm(a.map((v,i)=>v+(b[i]-v)*t));const th=Math.acos(Math.min(1,d)),st=Math.sin(th);return a.map((v,i)=>(v*Math.sin((1-t)*th)+b[i]*Math.sin(t*th))/st);};
  return {add,sub,mul,dot,cross,norm,ident,mm,trs,look,persp,ortho,normal,slerp};
})();

class HopperRenderer {
  constructor(canvas){
    this.canvas=canvas;this.gl=canvas.getContext('webgl2',{antialias:true,alpha:false,preserveDrawingBuffer:true,powerPreference:'high-performance'});
    if(!this.gl)throw new Error('이 브라우저에서 WebGL 2를 사용할 수 없습니다. Safari 또는 Chrome 최신 버전에서 열어 주세요.');
    this.az=.65;this.el=.22;this.distance=4.8;this.target=[0,1.02,-.03];this.spin=false;this.wire=false;this.armorVisible=true;this.glassVisible=true;this.isolateDrive=false;this.onlyLegs=false;this.legArmorVisible=true;
    this.meshes=[];this.nodes=[];this.textures=[];this.clip=null;this.time=0;this.playing=false;this.speed=1;this.ready=false;this.last=0;
    this.program=this.makeProgram(this.vertexSource(),this.fragmentSource());
    this.depthProgram=this.makeProgram(`#version 300 es\nlayout(location=0) in vec3 aPos;uniform mat4 uM;uniform mat4 uLVP;void main(){gl_Position=uLVP*uM*vec4(aPos,1.);}`,`#version 300 es\nprecision highp float;void main(){}`);
    this.locations={};this.depthLocations={};this.setupShadow();this.setupFloor();this.attachControls();
    this.lightDirection=HM.norm([-6,7.9,7.35]);
    this.lightVP=HM.mm(HM.ortho(-2.9,2.9,-2.9,2.9,.1,24),HM.look([-6,10,7.5],[0,1.4,.15]));
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(canvas);this.resize();
  }
  makeProgram(vs,fs){
    const gl=this.gl,p=gl.createProgram();
    for(const [type,src] of [[gl.VERTEX_SHADER,vs],[gl.FRAGMENT_SHADER,fs]]){
      const sh=gl.createShader(type);gl.shaderSource(sh,src);gl.compileShader(sh);
      if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(sh));
      gl.attachShader(p,sh);gl.deleteShader(sh);
    }
    gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p;
  }
  loc(name,depth=false){const cache=depth?this.depthLocations:this.locations;return cache[name]??(cache[name]=this.gl.getUniformLocation(depth?this.depthProgram:this.program,name));}
  resize(){const dpr=Math.min(window.devicePixelRatio||1,1.75),w=Math.max(1,Math.round(this.canvas.clientWidth*dpr)),h=Math.max(1,Math.round(this.canvas.clientHeight*dpr));if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h;}if(this.ready)this.render();}
  setupShadow(){
    const gl=this.gl;this.shadowSize=2048;this.shadowTex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.shadowTex);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.DEPTH_COMPONENT24,this.shadowSize,this.shadowSize,0,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);
    for(const p of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,p,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    this.shadowFBO=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowFBO);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,this.shadowTex,0);gl.drawBuffers([gl.NONE]);gl.readBuffer(gl.NONE);
    if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw new Error('Shadow framebuffer unavailable');gl.bindFramebuffer(gl.FRAMEBUFFER,null);
  }
  makeVAO(pos,norm,uv,indices,tangents=null){
    const gl=this.gl,vao=gl.createVertexArray();gl.bindVertexArray(vao);
    if(!tangents){tangents=new Float32Array(pos.length/3*4);for(let i=0;i<tangents.length;i+=4){tangents[i]=1;tangents[i+3]=1;}}
    [[pos,3,0],[norm,3,1],[uv,2,2],[tangents,4,3]].forEach(([arr,size,loc])=>{const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,arr,gl.STATIC_DRAW);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,0,0);});
    const ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);gl.bindVertexArray(null);
    return {vao,count:indices.length,indexType:indices instanceof Uint16Array?gl.UNSIGNED_SHORT:gl.UNSIGNED_INT,indices,indexBuffer:ib};
  }
  setupFloor(){this.floor=this.makeVAO(new Float32Array([-35,0,-35,-35,0,35,35,0,35,35,0,-35]),new Float32Array([0,1,0,0,1,0,0,1,0,0,1,0]),new Float32Array([0,0,0,1,1,1,1,0]),new Uint16Array([0,1,2,0,2,3]));}
  async load(buffer){
    const dv=new DataView(buffer);if(dv.getUint32(0,true)!==0x46546c67||dv.getUint32(4,true)!==2)throw new Error('Not a glTF 2.0 binary');
    if(dv.getUint32(8,true)!==buffer.byteLength)throw new Error('GLB length mismatch');
    let off=12,json,bin;
    while(off<buffer.byteLength){const len=dv.getUint32(off,true),type=dv.getUint32(off+4,true);off+=8;if(type===0x4e4f534a)json=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,off,len)));if(type===0x004e4942)bin=buffer.slice(off,off+len);off+=len;}
    if(!json||!bin)throw new Error('Missing GLB chunks');this.gltf=json;
    const width={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16},types={5126:Float32Array,5125:Uint32Array,5123:Uint16Array,5121:Uint8Array};
    const acc=i=>{const a=json.accessors[i],v=json.bufferViews[a.bufferView],C=types[a.componentType];if(!C||v.byteStride)throw new Error('This viewer expects tightly packed GLB accessors');return new C(bin,(v.byteOffset||0)+(a.byteOffset||0),a.count*width[a.type]);};
    this.nodes=json.nodes.map(n=>({name:n.name,t:[...(n.translation||[0,0,0])],r:[...(n.rotation||[0,0,0,1])],s:[...(n.scale||[1,1,1])],children:n.children||[],mesh:n.mesh,world:HM.ident()}));
    this.meshes=json.meshes.map(m=>m.primitives.map(p=>({...this.makeVAO(acc(p.attributes.POSITION),acc(p.attributes.NORMAL),acc(p.attributes.TEXCOORD_0),acc(p.indices),p.attributes.TANGENT===undefined?null:acc(p.attributes.TANGENT)),material:p.material,owner:m.name})));
    const gl=this.gl;
    this.textures=await Promise.all(json.images.map(async im=>{
      const v=json.bufferViews[im.bufferView],bytes=new Uint8Array(bin,v.byteOffset||0,v.byteLength),blob=new Blob([bytes],{type:im.mimeType}),url=URL.createObjectURL(blob),image=new Image();
      await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('Embedded texture decode failed'));image.src=url;});
      const tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      const aniso=gl.getExtension('EXT_texture_filter_anisotropic');if(aniso)gl.texParameterf(gl.TEXTURE_2D,aniso.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(8,gl.getParameter(aniso.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));
      URL.revokeObjectURL(url);return tex;
    }));
    this.materials=json.materials;
    this.clips=(json.animations||[]).map(a=>({name:a.name,duration:Math.max(...a.samplers.map(s=>{const t=acc(s.input);return t[t.length-1];})),tracks:a.channels.map(c=>{const sam=a.samplers[c.sampler];return {node:c.target.node,path:c.target.path,times:acc(sam.input),values:acc(sam.output),size:c.target.path==='rotation'?4:3};})}));
    this.clip=this.clips.find(c=>c.name==='Cockpit_Cycle')||this.clips[0];this.time=0;this.ready=true;this.sample();this.updateWorld();this.render();
    this.last=performance.now();requestAnimationFrame(t=>this.tick(t));return this;
  }
  sample(){if(!this.clip)return;const time=this.time;
    for(const tr of this.clip.tracks){const times=tr.times;let lo=0,hi=times.length-1;
      while(lo<hi-1){const m=(lo+hi)>>1;if(times[m]<=time)lo=m;else hi=m;}
      if(time>=times[times.length-1])lo=hi=times.length-1;
      const f=hi===lo?0:Math.max(0,Math.min(1,(time-times[lo])/(times[hi]-times[lo]))),a=Array.from(tr.values.subarray(lo*tr.size,(lo+1)*tr.size)),b=Array.from(tr.values.subarray(hi*tr.size,(hi+1)*tr.size));
      const value=tr.path==='rotation'?HM.slerp(a,b,f):a.map((v,i)=>v+(b[i]-v)*f);this.nodes[tr.node][{translation:'t',rotation:'r',scale:'s'}[tr.path]]=value;
    }
  }
  updateWorld(){const visit=(i,parent)=>{const n=this.nodes[i];n.world=HM.mm(parent,HM.trs(n.t,n.r,n.s));n.nmat=HM.normal(n.world);for(const child of n.children)visit(child,n.world);};for(const i of this.gltf.scenes[this.gltf.scene||0].nodes)visit(i,HM.ident());}
  get hatchAngle(){const n=this.nodes.find(n=>n.name==='Hatch_Pivot');return n?Math.abs(2*Math.atan2(n.r[0],n.r[3]))*180/Math.PI:0;}
  nearestOpenTime(){const clip=this.clips.find(c=>c.name==='Cockpit_Open'),tr=clip.tracks.find(t=>this.nodes[t.node].name==='Hatch_Pivot');let best=0,d=Infinity;for(let i=0;i<tr.times.length;i++){const angle=Math.abs(2*Math.atan2(tr.values[i*4],tr.values[i*4+3]))*180/Math.PI,delta=Math.abs(angle-this.hatchAngle);if(delta<d){d=delta;best=tr.times[i];}}return best;}
  action(kind){
    const ot=this.nearestOpenTime();this.clip=this.clips.find(c=>c.name===`Cockpit_${kind}`)||this.clips[0];
    this.time=kind==='Open'?ot:kind==='Close'?3-ot:0;this.playing=true;this.sample();this.updateWorld();this.render();this.onchange?.();
  }
  seek(time){this.time=Math.max(0,Math.min(this.clip.duration,Number(time)||0));this.playing=false;this.sample();this.updateWorld();this.render();this.onchange?.();}
  pose(open){this.clip=this.clips.find(c=>c.name==='Cockpit_Open');this.seek(open?3:0);}
  camera(name){
    const presets={threequarter:[.58,.21,4.90,[0,1.035,.055]],front:[0,.095,4.65,[0,1.035,0]],back:[3.73,.19,4.80,[0,1.04,-.10]],side:[1.57,.10,4.70,[0,1.04,-.05]],cockpit:[.25,.23,2.8,[0,1.47,.38]],fit:[.95,.19,2.9,[0,1.56,.33]],mechanism:[1.06,.37,2.3,[0,1.20,.18]],legs:[.62,.22,2.60,[0,.53,.08]],knee:[1.07,.18,1.32,[.48,.56,-.015]],ankle:[.74,.26,1.48,[.44,.20,.10]]};
    const p=presets[name]||presets.threequarter;[this.az,this.el,this.distance,this.target]=[p[0],p[1],p[2],[...p[3]]];if(name==='cockpit')this.pose(true);this.render();
  }
  tick(t){const dt=Math.min(.08,(t-this.last)/1000);this.last=t;let changed=false;
    if(this.playing){this.time+=dt*this.speed;if(this.time>=this.clip.duration){if(this.clip.name==='Cockpit_Cycle')this.time%=this.clip.duration;else{this.time=this.clip.duration;this.playing=false;}}this.sample();this.updateWorld();changed=true;}
    if(this.spin){this.az+=dt*.18;changed=true;}
    if(changed){this.render();this.onchange?.();}requestAnimationFrame(tt=>this.tick(tt));
  }
  attachControls(){
    const el=this.canvas,pointers=new Map();el.addEventListener('contextmenu',e=>e.preventDefault());
    el.addEventListener('pointerdown',e=>{pointers.set(e.pointerId,[e.clientX,e.clientY]);el.setPointerCapture(e.pointerId);this.spin=false;el.classList.add('dragging');});
    el.addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId))return;const old=pointers.get(e.pointerId),dx=e.clientX-old[0],dy=e.clientY-old[1];
      if(pointers.size>1){const other=[...pointers].find(([id])=>id!==e.pointerId)[1],a=Math.hypot(old[0]-other[0],old[1]-other[1]),b=Math.hypot(e.clientX-other[0],e.clientY-other[1]);this.distance=Math.max(.45,Math.min(18,this.distance*(a/(b||a))));}
      else if(e.shiftKey||e.buttons===2){const k=this.distance*.0015;this.target[0]-=Math.cos(this.az)*dx*k;this.target[2]+=Math.sin(this.az)*dx*k;this.target[1]+=dy*k;}
      else{this.az-=dx*.006;this.el=Math.max(-.08,Math.min(1.35,this.el+dy*.005));}
      pointers.set(e.pointerId,[e.clientX,e.clientY]);if(this.ready)this.render();});
    const release=e=>{pointers.delete(e.pointerId);if(!pointers.size)el.classList.remove('dragging');};el.addEventListener('pointerup',release);el.addEventListener('pointercancel',release);
    el.addEventListener('wheel',e=>{e.preventDefault();this.distance=Math.max(.45,Math.min(18,this.distance*Math.exp(e.deltaY*.001)));if(this.ready)this.render();},{passive:false});
  }
  vertexSource(){return `#version 300 es
  layout(location=0) in vec3 aPos;layout(location=1) in vec3 aNorm;layout(location=2) in vec2 aUV;layout(location=3) in vec4 aTan;
  uniform mat4 uM,uVP,uLVP;uniform mat3 uN;out vec3 vP;out vec3 vN;out vec2 vUV;out vec4 vLight;out vec3 vT;out float vSign;
  void main(){vec4 p=uM*vec4(aPos,1.);vP=p.xyz;vN=normalize(uN*aNorm);vT=normalize(mat3(uM)*aTan.xyz);vSign=aTan.w;vUV=aUV;vLight=uLVP*p;gl_Position=uVP*p;}`;}
  fragmentSource(){return `#version 300 es
  precision highp float;
  in vec3 vP;in vec3 vN;in vec2 vUV;in vec4 vLight;in vec3 vT;in float vSign;out vec4 outColor;
  uniform sampler2D uBase,uORM,uNormal,uShadow;uniform vec3 uEye,uLightDir,uEmit;uniform float uAlpha,uNormalScale;uniform int uGround,uWire;
  const float PI=3.14159265359;
  vec3 aces(vec3 x){return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0.,1.);}
  vec3 fresnel(float c,vec3 f0){return f0+(1.-f0)*pow(clamp(1.-c,0.,1.),5.);}
  float shadow(vec3 N){vec3 p=vLight.xyz/vLight.w*.5+.5;if(p.x<0.||p.x>1.||p.y<0.||p.y>1.||p.z>1.)return 1.;
    float bias=max(.00045,.0013*(1.-max(dot(N,uLightDir),0.))),s=0.;for(int x=-2;x<=2;x++)for(int y=-2;y<=2;y++){float d=texture(uShadow,p.xy+vec2(x,y)/2048.*1.65).r;s+=p.z-bias>d?0.:1.;}return s/25.;}
  vec3 brdf(vec3 N,vec3 V,vec3 L,vec3 base,float rough,float metal,vec3 radiance){
    vec3 H=normalize(V+L);float NL=max(dot(N,L),0.),NV=max(dot(N,V),.001),NH=max(dot(N,H),0.),HV=max(dot(H,V),0.);
    float a=rough*rough,a2=a*a,d=NH*NH*(a2-1.)+1.,D=a2/(PI*d*d+.00001),k=(rough+1.)*(rough+1.)/8.;
    float G=(NL/(NL*(1.-k)+k+.00001))*(NV/(NV*(1.-k)+k));vec3 F=fresnel(HV,mix(vec3(.04),base,metal));
    vec3 spec=D*G*F/(4.*NL*NV+.001),kd=(vec3(1.)-F)*(1.-metal);return (kd*base/PI+spec)*radiance*NL;
  }
  void main(){
    if(uWire==1){outColor=vec4(.105,.155,.155,.45);return;}
    vec3 N=normalize(vN);if(!gl_FrontFacing)N=-N;vec3 V=normalize(uEye-vP);vec3 srgb;float rough,metal,ao;
    if(uGround==1){srgb=vec3(.83,.827,.795);rough=.92;metal=0.;ao=1.;}
    else{srgb=texture(uBase,vUV).rgb;vec3 orm=texture(uORM,vUV).rgb;rough=clamp(orm.g,.08,.95);metal=orm.b;ao=orm.r;
      vec3 nm=texture(uNormal,vUV).rgb*2.-1.;nm.xy*=uNormalScale;
      vec3 T=normalize(vT-N*dot(N,vT));vec3 B=normalize(cross(N,T))*vSign;
      N=normalize(mat3(T,B,N)*nm);
    }
    vec3 base=pow(srgb,vec3(2.2)),F0=mix(vec3(.04),base,metal);float NV=max(dot(N,V),0.);vec3 F=fresnel(NV,F0);
    vec3 hemi=mix(vec3(.19,.17,.135),vec3(.57,.62,.64),N.y*.5+.5);
    vec3 color=base*(1.-metal)*hemi*.56*ao;
    color+=brdf(N,V,uLightDir,base,rough,metal,vec3(3.35,3.18,2.83))*mix(.20,1.,shadow(N));
    color+=brdf(N,V,normalize(vec3(4.,3.,-1.)),base,rough,metal,vec3(1.20,1.36,1.43));
    color+=brdf(N,V,normalize(vec3(-1.,2.,-5.)),base,rough,metal,vec3(.93,1.02,1.02));
    vec3 R=reflect(-V,N);vec3 env=mix(vec3(.13,.145,.14),vec3(.68,.75,.78),clamp(R.y*.5+.5,0.,1.));
    env+=vec3(.60,.57,.49)*pow(max(dot(R,normalize(vec3(-3.,4.,5.))),0.),max(2.,55.*(1.-rough)));
    color+=env*F*(1.-rough*.5)*.54*ao;
    if(uGround==0)color+=pow(srgb,vec3(2.2))*uEmit*1.8;
    color=pow(aces(color),vec3(1./2.2));
    if(uGround==1){float fog=1.-exp(-max(0.,length(vP.xz)-6.)*.038);color=mix(color,vec3(.88,.872,.842),fog);}
    float alpha=uGround==1?1.:min(1.,uAlpha+(uAlpha<.99?pow(1.-NV,4.)*.40:0.));outColor=vec4(color,alpha);
  }`;}
  isVisible(pr){const n=this.materials[pr.material].name;const lower=/^(Leg_|LowerBody_)/.test(pr.owner||'');if(this.onlyLegs&&!lower)return false;if(lower&&!this.legArmorVisible&&n.endsWith('_Paint'))return false;if(this.isolateDrive){if(n.endsWith('_Paint')||n.endsWith('_Glass'))return false;if(!/^(Hatch_Pivot|Internal_|Bell_Crank_|Rigid_Connecting_Link_)/.test(pr.owner||''))return false;}return (this.armorVisible||!n.endsWith('_Paint'))&&(this.glassVisible&&this.armorVisible||!n.endsWith('_Glass'));}
  material(index){const gl=this.gl,m=this.materials[index],p=m.pbrMetallicRoughness;
    // Each material selects its own atlas. Torso and lower-body maps stay independent.
    const ids=[p.baseColorTexture.index,p.metallicRoughnessTexture.index,m.normalTexture?.index??2];
    ids.forEach((idx,unit)=>{gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,this.textures[this.gltf.textures[idx].source]);});
gl.uniform1f(this.loc('uAlpha'),p.baseColorFactor?.[3]??1);gl.uniform3fv(this.loc('uEmit'),m.emissiveFactor||[0,0,0]);gl.uniform1f(this.loc('uNormalScale'),m.normalTexture?.scale??0);if(m.doubleSided)gl.disable(gl.CULL_FACE);else gl.enable(gl.CULL_FACE);}
  render(){if(!this.ready)return;const gl=this.gl;this.resizeWithoutRender();
    const eye=HM.add(this.target,[Math.sin(this.az)*Math.cos(this.el)*this.distance,Math.sin(this.el)*this.distance,Math.cos(this.az)*Math.cos(this.el)*this.distance]);
    const vp=HM.mm(HM.persp(36*Math.PI/180,this.canvas.width/this.canvas.height,.07,100),HM.look(eye,this.target));
    gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.depthMask(true);gl.disable(gl.BLEND);gl.enable(gl.CULL_FACE);gl.cullFace(gl.FRONT);
    gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowFBO);gl.viewport(0,0,this.shadowSize,this.shadowSize);gl.clear(gl.DEPTH_BUFFER_BIT);gl.useProgram(this.depthProgram);gl.uniformMatrix4fv(this.loc('uLVP',true),false,this.lightVP);
    for(const n of this.nodes){if(n.mesh===undefined)continue;gl.uniformMatrix4fv(this.loc('uM',true),false,n.world);for(const pr of this.meshes[n.mesh]){if(!this.isVisible(pr))continue;if(this.materials[pr.material].alphaMode==='BLEND')continue;gl.bindVertexArray(pr.vao);gl.drawElements(gl.TRIANGLES,pr.count,pr.indexType,0);}}
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.clearColor(.88,.872,.842,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.cullFace(gl.BACK);gl.useProgram(this.program);
    gl.uniformMatrix4fv(this.loc('uVP'),false,vp);gl.uniformMatrix4fv(this.loc('uLVP'),false,this.lightVP);gl.uniform3fv(this.loc('uEye'),eye);gl.uniform3fv(this.loc('uLightDir'),this.lightDirection);gl.uniform1i(this.loc('uWire'),0);
    [this.textures[0],this.textures[1],this.textures[2],this.shadowTex].forEach((tex,i)=>{gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,tex);});
    ['uBase','uORM','uNormal','uShadow'].forEach((u,i)=>gl.uniform1i(this.loc(u),i));
    gl.uniform1i(this.loc('uGround'),1);gl.uniformMatrix4fv(this.loc('uM'),false,HM.ident());gl.uniformMatrix3fv(this.loc('uN'),false,new Float32Array([1,0,0,0,1,0,0,0,1]));gl.uniform1f(this.loc('uAlpha'),1);gl.uniform3fv(this.loc('uEmit'),[0,0,0]);gl.bindVertexArray(this.floor.vao);gl.drawElements(gl.TRIANGLES,this.floor.count,this.floor.indexType,0);
    gl.uniform1i(this.loc('uGround'),0);
    const transparent=[];
    for(const n of this.nodes){if(n.mesh===undefined)continue;for(const pr of this.meshes[n.mesh]){if(!this.isVisible(pr))continue;if(this.materials[pr.material].alphaMode==='BLEND'){transparent.push([n,pr]);continue;}this.drawPrimitive(n,pr);}}
    if(this.wire){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1i(this.loc('uWire'),1);gl.disable(gl.CULL_FACE);
      for(const n of this.nodes){if(n.mesh===undefined)continue;for(const pr of this.meshes[n.mesh]){if(!this.isVisible(pr))continue;gl.bindVertexArray(pr.vao);if(!pr.wireBuffer){const ii=pr.indices,edges=new Uint32Array(ii.length*2);for(let i=0,j=0;i<ii.length;i+=3){edges.set([ii[i],ii[i+1],ii[i+1],ii[i+2],ii[i+2],ii[i]],j);j+=6;}pr.wireBuffer=gl.createBuffer();pr.wireCount=edges.length;gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,pr.wireBuffer);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,edges,gl.STATIC_DRAW);}
        gl.uniformMatrix4fv(this.loc('uM'),false,n.world);gl.uniformMatrix3fv(this.loc('uN'),false,n.nmat);gl.bindVertexArray(pr.vao);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,pr.wireBuffer);gl.drawElements(gl.LINES,pr.wireCount,gl.UNSIGNED_INT,0);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,pr.indexBuffer);}}
      gl.uniform1i(this.loc('uWire'),0);gl.disable(gl.BLEND);gl.depthMask(true);
    }
    gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);for(const [n,pr] of transparent)this.drawPrimitive(n,pr);gl.depthMask(true);gl.disable(gl.BLEND);gl.bindVertexArray(null);
  }
  drawPrimitive(n,pr){const gl=this.gl;gl.uniformMatrix4fv(this.loc('uM'),false,n.world);gl.uniformMatrix3fv(this.loc('uN'),false,n.nmat);this.material(pr.material);gl.bindVertexArray(pr.vao);gl.drawElements(gl.TRIANGLES,pr.count,pr.indexType,0);}
  resizeWithoutRender(){const dpr=Math.min(window.devicePixelRatio||1,1.75),w=Math.max(1,Math.round(this.canvas.clientWidth*dpr)),h=Math.max(1,Math.round(this.canvas.clientHeight*dpr));if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h;}}
}
window.HopperRenderer=HopperRenderer;
