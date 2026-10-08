/* Static WebGL2 tree viewer. All draw calls use the same real 3D assets.
   No 2D trunk, no SVG scene, no remote dependencies, no whole-tree gradient.
   v06: continuous orbit camera; screen-aligned cards; rest-space shading.
   Shadows use the original rest-card proxy so orbiting cannot move the light/shadow.  */
(()=>{'use strict';
const S=window.TREE_SCENE, IMAGES=window.TREE_IMAGES, canvas=document.getElementById('scene');
const $=id=>document.getElementById(id);
const Orbit=window.TreeOrbit;
const state={time:0,wind:.22,leafScale:1,density:1,mode:'tree',...Orbit.home(),paused:false,hideUI:false};
let viewCamera=null;
const gl=canvas.getContext('webgl2',{antialias:true,alpha:false,preserveDrawingBuffer:true});
if(!gl){$('loading').textContent='WebGL 2를 사용할 수 없습니다. 하드웨어 가속이 켜진 브라우저에서 열어 주세요.';window.TREE_ERROR='WebGL2 unavailable';return;}
const norm=v=>{let l=Math.hypot(...v);return v.map(x=>x/l);};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
function look(eye,target,up){const z=norm(eye.map((v,i)=>v-target[i])),x=norm(cross(up,z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);}
function ortho(l,r,b,t,n,f){return new Float32Array([2/(r-l),0,0,0,0,2/(t-b),0,0,0,0,-2/(f-n),0,-(r+l)/(r-l),-(t+b)/(t-b),-(f+n)/(f-n),1]);}
function mul(a,b){let o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o;}
const VERT=`#version 300 es
precision highp float;
precision highp int;
layout(location=0) in vec3 aPosition;
layout(location=1) in vec3 aNormal;
layout(location=2) in vec2 aUV;
layout(location=3) in vec3 aColor;
layout(location=4) in vec3 aPivot;
layout(location=5) in float aPhase;
layout(location=6) in vec3 aProxyNormal;
layout(location=7) in float aBunch;
uniform mat4 uVP,uLightVP;
uniform vec3 uCardRight,uCardUp;
uniform float uTime,uWind,uLeafScale;
uniform int uLeaf;
out vec2 vUV;out vec3 vNormal,vColor,vPosition,vProxy;out vec4 vShadow;out float vPhase;
void main(){
 vec3 p=aPosition;
 if(uLeaf==1){
  // aPosition-aPivot is the original XY card offset, INCLUDING its random roll.
  // Rotate the visible quad in the current view plane; NEVER rotate aProxyNormal.
  float theta=uWind*.095*(sin(uTime*1.25+aPhase)+.42*sin(uTime*2.1+aPhase*1.7));
  float ca=cos(theta),sa=sin(theta);
  vec2 q=(aPosition-aPivot).xy*uLeafScale;
  q=mat2(ca,sa,-sa,ca)*q;
  float group=.023*uWind*sin(uTime*.82+aBunch*1.39);
  p=aPivot+uCardRight*q.x+uCardUp*q.y+vec3(group,group*.2,0.);
 }
 vPosition=p;vUV=aUV;vNormal=aNormal;vColor=aColor;vProxy=aProxyNormal;vPhase=aPhase;
 vShadow=uLightVP*vec4(p,1.);gl_Position=uVP*vec4(p,1.);
}`;
const FRAG=`#version 300 es
precision highp float;
precision highp int;
in vec2 vUV;in vec3 vNormal,vColor,vPosition,vProxy;in vec4 vShadow;in float vPhase;
uniform sampler2D uTex,uNormalTex,uShadowTex;
uniform vec3 uLight;
uniform int uLeaf,uGround,uDebug;
uniform float uDensity;
out vec4 frag;
float shadow(){
 vec3 p=vShadow.xyz/vShadow.w*.5+.5;
 if(p.x<.002||p.x>.998||p.y<.002||p.y>.998||p.z>1.)return 1.;
 float s=0.;
 for(int x=-1;x<=1;x++)for(int y=-1;y<=1;y++){
  float d=texture(uShadowTex,p.xy+vec2(float(x),float(y))/1024.).r;
  s+=(p.z-.0018<=d)?1.:0.;
 }
 return s/9.;
}
vec3 bumpNormal(vec3 normal){
 vec3 N=normalize(normal);vec3 dx=dFdx(vPosition),dy=dFdy(vPosition);vec2 stx=dFdx(vUV),sty=dFdy(vUV);
 vec3 T=dx*sty.y-dy*stx.y;vec3 B=-dx*sty.x+dy*stx.x;
 float m=max(dot(T,T),dot(B,B));if(m<.0000001)return N;
 float scale=inversesqrt(m);T*=scale;B*=scale;
 vec3 n=texture(uNormalTex,vUV).rgb*2.-1.;n.xy*=.48;
 return normalize(T*n.x+B*n.y+N*n.z);
}
void main(){
 if(uLeaf==1){
  if(fract(vPhase*8.31)>uDensity)discard;
  vec4 tex=texture(uTex,vUV);
  if(uDebug!=3&&tex.a<.48)discard;
  vec3 col=vColor*tex.rgb;
  if(uDebug==1)col=normalize(vProxy)*.5+.5;
  if(uDebug==2){float l=dot(normalize(vProxy),uLight)*.5+.5;col=vec3(l);}
  if(uDebug==3)col=(normalize(vProxy)*.5+.5)*.55+.22;
  frag=vec4(col,1.);return;
 }
 if(uGround==1){
  float sh=shadow();vec3 base=vec3(.9216,.9137,.8902);
  float contact=exp(-dot(vPosition.xz,vPosition.xz)*1.5)*.12;
  frag=vec4(base*(1.-(1.-sh)*.16-contact),1.);return;
 }
 vec3 N=bumpNormal(vNormal);float nd=max(0.,dot(N,uLight));
 vec3 tex=texture(uTex,vUV).rgb;float light=.47+nd*.53;
 light*=mix(.74,1.,shadow());
 vec3 col=tex*light*1.10;
 if(uDebug==4){vec2 q=floor(vUV*42.);float ck=mod(q.x+q.y,2.);col=mix(vec3(.22,.30,.28),vec3(.78,.83,.65),ck)*(.55+.45*nd);}
 frag=vec4(col,1.);
}`;
const DEPTH=`#version 300 es
precision highp float;
precision highp int;
in vec2 vUV;in float vPhase;
uniform sampler2D uTex;uniform int uLeaf;uniform float uDensity;
void main(){if(uLeaf==1){if(fract(vPhase*8.31)>uDensity)discard;if(texture(uTex,vUV).a<.48)discard;}}
`;
function shader(type,source){let sh=gl.createShader(type);gl.shaderSource(sh,source);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(sh));return sh;}
function program(v,f){const p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,v));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,f));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return {p,uniforms:new Map()};}
function loc(p,name){if(!p.uniforms.has(name))p.uniforms.set(name,gl.getUniformLocation(p.p,name));return p.uniforms.get(name);}
const u1=(p,n,v)=>gl.uniform1f(loc(p,n),v),ui=(p,n,v)=>gl.uniform1i(loc(p,n),v),um=(p,n,m)=>gl.uniformMatrix4fv(loc(p,n),false,m);
function mesh(data){
 const vao=gl.createVertexArray();gl.bindVertexArray(vao);const count=data.position.length/3;
 const attrs=[['position',3],['normal',3],['uv',2],['color',3],['pivot',3],['phase',1],['proxyNormal',3],['bunchIndex',1]];
 attrs.forEach(([key,size],i)=>{if(!data[key]){gl.disableVertexAttribArray(i);return;}let b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data[key]),gl.STATIC_DRAW);gl.enableVertexAttribArray(i);gl.vertexAttribPointer(i,size,gl.FLOAT,false,0,0);});
 let ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array(data.indices),gl.STATIC_DRAW);
 gl.bindVertexArray(null);return {vao,count:data.indices.length,vertices:count};
}
function loadTex(url){return new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>{const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);gl.generateMipmap(gl.TEXTURE_2D);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);const ext=gl.getExtension('EXT_texture_filter_anisotropic');if(ext)gl.texParameterf(gl.TEXTURE_2D,ext.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(4,gl.getParameter(ext.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));resolve(t);};image.onerror=()=>reject(new Error('Embedded texture failed to load'));image.src=url;});}
let main,depth,trunk,leaves,ground,barkTex,leafTex,normalTex,shadowTex,shadowFbo,lightVP;
const bindTex=(t,unit)=>{gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,t);};
function setupShadow(){
 shadowTex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,shadowTex);gl.texImage2D(gl.TEXTURE_2D,0,gl.DEPTH_COMPONENT24,1024,1024,0,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
 shadowFbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,shadowFbo);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,shadowTex,0);gl.drawBuffers([gl.NONE]);gl.readBuffer(gl.NONE);
 if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw new Error('Depth framebuffer incomplete');gl.bindFramebuffer(gl.FRAMEBUFFER,null);
 const L=S.meta.lightDirection,at=[0,2.0,0],eye=at.map((x,i)=>x+L[i]*10);
 lightVP=mul(ortho(-4.8,4.8,-4.8,4.8,.1,25),look(eye,at,[0,1,0]));
}
function common(p,vp,shadowPass=false){
 gl.useProgram(p.p);um(p,'uVP',vp);um(p,'uLightVP',lightVP);
 // The main view follows the real camera. Shadow casters keep the v05 rest basis.
 // This deliberate proxy avoids camera-dependent shadows on the 3D trunk/ground.
 gl.uniform3fv(loc(p,'uCardRight'),shadowPass?[1,0,0]:viewCamera.right);
 gl.uniform3fv(loc(p,'uCardUp'),shadowPass?[0,1,0]:viewCamera.up);
 u1(p,'uTime',state.time);u1(p,'uWind',state.wind);u1(p,'uLeafScale',state.leafScale);u1(p,'uDensity',state.density);
 ui(p,'uTex',0);ui(p,'uNormalTex',1);ui(p,'uShadowTex',2);
}
function drawMesh(p,m,isLeaf,isGround=false){ui(p,'uLeaf',isLeaf?1:0);ui(p,'uGround',isGround?1:0);bindTex(isLeaf?leafTex:barkTex,0);gl.bindVertexArray(m.vao);gl.drawElements(gl.TRIANGLES,m.count,gl.UNSIGNED_INT,0);}
function render(){
 if(!main)return;
 const d=Math.min(window.devicePixelRatio||1,2),w=Math.max(1,Math.round(innerWidth*d)),h=Math.max(1,Math.round(innerHeight*d));
 if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
 viewCamera=Orbit.camera(state,w,h);
 const {aspect,halfHeight:scale,eye,target,up}=viewCamera;
 const vp=mul(ortho(-scale*aspect,scale*aspect,-scale,scale,.1,60),look(eye,target,up));
 const drawLeaves=state.mode!=='trunk'&&state.mode!=='uv';
 gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.depthMask(true);gl.disable(gl.CULL_FACE);gl.disable(gl.BLEND);
 // Fixed-rest-card masked shadow proxy. Same wind; deliberately not view-facing.
 gl.bindFramebuffer(gl.FRAMEBUFFER,shadowFbo);gl.viewport(0,0,1024,1024);gl.clear(gl.DEPTH_BUFFER_BIT);common(depth,lightVP,true);drawMesh(depth,trunk,false);if(drawLeaves)drawMesh(depth,leaves,true);
 gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,w,h);gl.clearColor(.9216,.9137,.8902,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
 common(main,vp);bindTex(normalTex,1);bindTex(shadowTex,2);gl.uniform3fv(loc(main,'uLight'),S.meta.lightDirection);
 const debug={normal:1,value:2,cards:3,uv:4}[state.mode]||0;ui(main,'uDebug',debug);
 // Looking upward from below is allowed; do not let the ground hide the tree.
 if(eye[1]>=.01)drawMesh(main,ground,false,true);
 drawMesh(main,trunk,false);if(drawLeaves)drawMesh(main,leaves,true);
 gl.bindVertexArray(null);window.TREE_FRAME_COUNT=(window.TREE_FRAME_COUNT||0)+1;
}
let last=0;
function tick(ms){if(!state.paused){state.time+=last?Math.min((ms-last)/1000,.05):0;render();}last=ms;requestAnimationFrame(tick);}
addEventListener('resize',()=>render());
function update(patch){Object.assign(state,Orbit.sanitize({...state,...patch}));document.body.classList.toggle('hide-ui',state.hideUI);document.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('active',x.dataset.mode===state.mode));const readout=$('camera-val');if(readout)readout.textContent=`${state.angle.toFixed(0)}° / ${state.elevation.toFixed(0)}° · ${state.zoom.toFixed(2)}×`;render();return {...state,pan:[...state.pan]};}
window.TreePreview={set:update,getState:()=>({...state,pan:[...state.pan]}),getCamera:()=>Orbit.camera(state,canvas.width||1,canvas.height||1),render,stats:()=>({...S.meta,version:'06',meshAssetVersion:S.meta.version,cameraMode:'orbit',billboardMode:'screen-aligned',shadingSpace:'tree-rest',shadowCasterMode:'camera-independent-rest-cards',context:gl.getParameter(gl.VERSION),glError:gl.getError(),frames:window.TREE_FRAME_COUNT||0})};
$('wind').oninput=e=>{update({wind:+e.target.value});$('wind-val').textContent=Math.round(state.wind*100)+'%';};
$('leaf-scale').oninput=e=>{update({leafScale:+e.target.value});$('size-val').textContent=state.leafScale.toFixed(2);};
$('density').oninput=e=>{update({density:+e.target.value});$('density-val').textContent=Math.round(state.density*100)+'%';};
$('pause').onclick=()=>{update({paused:!state.paused});$('pause').textContent=state.paused?'바람 재생':'바람 일시정지';};
$('reset').onclick=()=>{update({...Orbit.home(),time:0,wind:.22,leafScale:1,density:1,mode:'tree',paused:false});$('wind').value=.22;$('leaf-scale').value=1;$('density').value=1;$('wind-val').textContent='22%';$('size-val').textContent='1.00';$('density-val').textContent='100%';$('pause').textContent='바람 일시정지';};
for(const el of document.querySelectorAll('[data-mode]'))el.onclick=()=>update({mode:el.dataset.mode});
for(const el of document.querySelectorAll('[data-angle]'))el.onclick=()=>update({...Orbit.home(),angle:+el.dataset.angle,elevation:el.dataset.elevation!==undefined?+el.dataset.elevation:Orbit.DEFAULT_ELEVATION});
$('reset-camera').onclick=()=>update(Orbit.home());
Orbit.attach(canvas,()=>state,update);
$('capture').onclick=()=>{render();const a=document.createElement('a');a.download='tree-web-v06-freeview.png';a.href=canvas.toDataURL('image/png');a.click();};
$('toggle-ui').onclick=()=>update({hideUI:!state.hideUI});
addEventListener('keydown',e=>{if(/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName))return;if(e.key.toLowerCase()==='h')update({hideUI:!state.hideUI});if(e.key.toLowerCase()==='f')update(Orbit.home());});
canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();$('loading').hidden=false;$('loading').textContent='그래픽 컨텍스트가 중단됐습니다. 페이지를 새로고침해 주세요.';});
(async()=>{try{
 main=program(VERT,FRAG);depth=program(VERT,DEPTH);trunk=mesh(S.trunk);leaves=mesh(S.foliage);
 ground=mesh({position:[-30,0,-30,-30,0,30,30,0,30,30,0,-30],normal:[0,1,0,0,1,0,0,1,0,0,1,0],uv:[0,0,0,1,1,1,1,0],indices:[0,1,2,0,2,3]});
 [barkTex,leafTex,normalTex]=await Promise.all([loadTex(IMAGES.bark),loadTex(IMAGES.leaf),loadTex(IMAGES.normal)]);setupShadow();
 $('loading').hidden=true;$('stats').textContent=`${S.bunches.length}개 잎덩이 · ${S.meta.cards.toLocaleString()}개 카드 · 실제 3D 줄기`;
 window.TREE_READY=true;render();requestAnimationFrame(tick);
 }catch(error){window.TREE_ERROR=error.message;$('loading').hidden=false;$('loading').textContent='렌더링 오류: '+error.message;console.error(error);}})();
})();
