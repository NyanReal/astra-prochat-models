import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { createTerrain } from './terrain.js';
import { createVegetation } from './vegetation.js';
import { createProps } from './props.js';
import { createLife } from './life.js';

const $ = s => document.querySelector(s);
const canvas = $('#scene');
let quality = innerWidth < 760 ? 'balanced' : 'high';
let paused = matchMedia('(prefers-reduced-motion: reduce)').matches;
let time = 0, lastTime = performance.now(), currentView = 'overview', tween = null;
let sceneParts = [], textures, renderer, scene, camera, controls, sun, ambient, hemisphere;
let viewHeight = 24.0, renderedFrames = 0, sceneStats = {}, uiClean = false, stoppedByVisibility = false;
const views = {
  overview: { target:[1.0,.4,-1.1], offset:[18,34,42], height:25.8 },
  dock: { target:[-4.3,.7,7.0], offset:[13,19,24], height:15.5 },
  stream: { target:[-12.8,1.4,-10.6], offset:[17,24,28], height:17.5 },
  camp: { target:[7.5,1.5,-11.7], offset:[20,24,29], height:20 }
};

function progress(value,copy){$('#loading-progress').style.width=value+'%';if(copy)$('#loading-copy').textContent=copy;}
function toast(text){const el=$('#toast');el.textContent=text;el.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('show'),2600);}
function fail(error){console.error(error);$('#error').hidden=false;$('#error-copy').textContent=error.message||String(error);$('#loading').hidden=true;}
function loadImage(src){return new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(new Error('텍스처를 불러오지 못했습니다. 새로고침해 주세요.'));im.src=src;});}

async function loadTextures(){
  const image=await loadImage('./assets/textures/material-atlas.png');
  const result={}, names=['ground','wood','stone','grass','metal','waterbed'];
  const w=image.width/3,h=image.height/2;
  names.forEach((name,i)=>{
    const c=document.createElement('canvas');c.width=512;c.height=512;
    c.getContext('2d').drawImage(image,(i%3)*w,Math.floor(i/3)*h,w,h,0,0,512,512);
    const t=new THREE.CanvasTexture(c);t.name='Painted '+name;t.colorSpace=THREE.SRGBColorSpace;
    t.wrapS=t.wrapT=THREE.RepeatWrapping;t.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());result[name]=t;
  });
  return result;
}

function buildWorld(){
  const shared=new Set(Object.values(textures||{})),disposed=new Set();
  const disposeTexture=t=>{if(t?.isTexture&&!shared.has(t)&&!disposed.has(t)){t.dispose();disposed.add(t);}};
  sceneParts.forEach(part=>{scene.remove(part.group);part.group.traverse(o=>{o.geometry?.dispose();if(o.material){for(const m of [].concat(o.material)){for(const v of Object.values(m))disposeTexture(v);for(const u of Object.values(m.uniforms||{}))disposeTexture(u.value);for(const t of m.userData?.ownedTextures||[])disposeTexture(t);m.dispose();}}});});
  const ctx={textures,quality};
  sceneParts=[createTerrain(ctx),createProps(ctx),createVegetation(ctx),createLife(ctx)];
  sceneStats={};
  sceneParts.forEach(part=>{scene.add(part.group);Object.assign(sceneStats,part.stats||{});});
  renderer.shadowMap.needsUpdate=true;
  document.querySelectorAll('[data-quality]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.quality===quality)));
  $('#render-info').textContent=`${sceneStats.trees||0}그루의 나무 · ${(sceneStats.flowers||0).toLocaleString()}송이의 들꽃\n${quality==='high'?'섬세한':'가벼운'} 풍경 · Three.js r170`;
  document.body.dataset.quality=quality;
}

function applyQuality(){
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,quality==='high'?1.75:1.15));
  const size=quality==='high'?4096:2048;
  sun.shadow.mapSize.set(size,size);if(sun.shadow.map){sun.shadow.map.dispose();sun.shadow.map=null;}
  renderer.shadowMap.needsUpdate=true;resize();
}

function resize(){
  if(!renderer)return;
  const w=canvas.clientWidth,h=canvas.clientHeight,aspect=w/h;
  const effective=viewHeight*Math.max(1,1.25/aspect);
  camera.left=-effective*aspect/2;camera.right=effective*aspect/2;camera.top=effective/2;camera.bottom=-effective/2;
  camera.updateProjectionMatrix();renderer.setSize(w,h,false);
}

function setView(name,instant=false){
  currentView=name;const v=views[name],target=new THREE.Vector3(...v.target),position=target.clone().add(new THREE.Vector3(...v.offset));
  document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===name);b.setAttribute('aria-pressed',String(b.dataset.view===name));});
  if(instant){camera.position.copy(position);controls.target.copy(target);viewHeight=v.height;camera.zoom=1;resize();controls.update();return;}
  tween={start:performance.now(),fromPosition:camera.position.clone(),toPosition:position,fromTarget:controls.target.clone(),toTarget:target,fromHeight:viewHeight,toHeight:v.height,fromZoom:camera.zoom};
  controls.autoRotate=false;$('#autorotate').setAttribute('aria-pressed','false');
}

function changeSunlight(value){
  const t=value/100;sun.intensity=2.25+t*1.1;sun.color.set('#fff5da').lerp(new THREE.Color('#ffcd81'),t*.26);
  hemisphere.intensity=1.7;ambient.intensity=.35;renderer.toneMappingExposure=1.08+t*.20;
  $('#sun-value').value=value+'%';
  renderer.shadowMap.needsUpdate=true;
}

function syncPause(){
  $('#pause').setAttribute('aria-pressed',String(paused));$('#pause').setAttribute('aria-label',paused?'애니메이션 재생':'애니메이션 일시정지');
  $('#pause-icon').innerHTML=paused?'<path d="m9 5 10 7-10 7Z"/>':'<path d="M9 5v14M15 5v14"/>';
}

function setClean(value){uiClean=value;document.body.classList.toggle('clean',value);$('#restore-ui').hidden=!value;$('#settings').hidden=true;$('#reference').hidden=true;$('#settings-toggle').setAttribute('aria-expanded','false');$('#reference-toggle').setAttribute('aria-expanded','false');}

function setupUI(){
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view)));
  $('#reset').addEventListener('click',()=>{setView('overview');toast('처음 풍경으로 돌아왔습니다.');});
  $('#pause').addEventListener('click',()=>{paused=!paused;syncPause();toast(paused?'물결과 바람이 잠시 멈춥니다.':'물결과 바람이 다시 흐릅니다.');});syncPause();
  for(const name of ['settings','reference']){
    const toggle=$('#'+name+'-toggle'),panel=$('#'+name);
    toggle.addEventListener('click',()=>{const open=panel.hidden;$('#settings').hidden=true;$('#reference').hidden=true;$('#settings-toggle').setAttribute('aria-expanded','false');$('#reference-toggle').setAttribute('aria-expanded','false');panel.hidden=!open;toggle.setAttribute('aria-expanded',String(open));});
    $('#'+name+'-close').addEventListener('click',()=>{panel.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();});
  }
  $('#sunlight').addEventListener('input',e=>changeSunlight(+e.target.value));
  document.querySelectorAll('[data-quality]').forEach(b=>b.addEventListener('click',()=>{
    if(quality===b.dataset.quality)return;quality=b.dataset.quality;buildWorld();applyQuality();toast(quality==='high'?'섬세한 풍경으로 바꿨습니다.':'가볍게 감상할 수 있도록 바꿨습니다.');
  }));
  $('#autorotate').addEventListener('click',()=>{controls.autoRotate=!controls.autoRotate;$('#autorotate').setAttribute('aria-pressed',String(controls.autoRotate));});
  $('#clean-view').addEventListener('click',()=>setClean(true));$('#restore-ui').addEventListener('click',()=>setClean(false));
  $('#capture').addEventListener('click',()=>{
    renderer.render(scene,camera);canvas.toBlob(blob=>{if(!blob){toast('이미지를 저장하지 못했습니다.');return;}const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='Emerald_Lake.png';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);toast('현재 풍경을 이미지로 저장했습니다.');},'image/png');
  });
  window.addEventListener('keydown',e=>{if(/INPUT|TEXTAREA/.test(e.target.tagName))return;if(e.code==='KeyH')setClean(!uiClean);if(e.code==='KeyR')setView('overview');if(e.code==='Space'){e.preventDefault();paused=!paused;syncPause();}if(e.code==='Escape')setClean(false);});
  window.addEventListener('resize',resize);
  document.addEventListener('visibilitychange',()=>{stoppedByVisibility=document.hidden;lastTime=performance.now();});
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();toast('그래픽 연결이 잠시 끊겼습니다. 화면을 복구합니다.');});
  canvas.addEventListener('webglcontextrestored',()=>{renderer.shadowMap.needsUpdate=true;toast('풍경이 복구됐습니다.');});
}

function frame(now){
  requestAnimationFrame(frame);
  const dt=Math.min((now-lastTime)/1000,.05);lastTime=now;if(stoppedByVisibility)return;
  if(!paused)time+=dt;
  if(tween){
    const t=Math.min(1,(now-tween.start)/1300),e=t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
    camera.position.lerpVectors(tween.fromPosition,tween.toPosition,e);controls.target.lerpVectors(tween.fromTarget,tween.toTarget,e);
    viewHeight=THREE.MathUtils.lerp(tween.fromHeight,tween.toHeight,e);camera.zoom=THREE.MathUtils.lerp(tween.fromZoom,1,e);resize();if(t===1)tween=null;
  }
  controls.update(dt);for(const part of sceneParts)part.update?.(time,paused?0:dt);
  renderer.render(scene,camera);renderedFrames++;
  if(renderedFrames===2){window.__lakeReady=true;document.body.dataset.ready='true';progress(100);$('#loading').classList.add('loaded');setTimeout(()=>$('#loading').hidden=true,700);}
}

async function start(){
  const context=canvas.getContext('webgl2',{antialias:true,alpha:false,powerPreference:'high-performance',preserveDrawingBuffer:true});
  if(!context){await startStillPreview();return;}
  renderer=new THREE.WebGLRenderer({canvas,context,antialias:true,alpha:false,powerPreference:'high-performance',preserveDrawingBuffer:true});
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;
  renderer.setClearColor('#8fbfa4');scene=new THREE.Scene();scene.background=new THREE.Color('#90b6a0');scene.fog=new THREE.Fog('#8db4a0',70,115);
  camera=new THREE.OrthographicCamera(-25,25,16,-16,.3,180);
  controls=new OrbitControls(camera,canvas);controls.enableDamping=true;controls.dampingFactor=.07;controls.enablePan=true;
  controls.minPolarAngle=.28;controls.maxPolarAngle=1.24;controls.minZoom=.66;controls.maxZoom=2.9;controls.rotateSpeed=.6;controls.panSpeed=.65;controls.zoomSpeed=.8;controls.autoRotateSpeed=.38;
  controls.addEventListener('start',()=>{tween=null;});
  sun=new THREE.DirectionalLight('#fff0ca',2.9);sun.position.set(-19,34,8);sun.castShadow=true;
  Object.assign(sun.shadow.camera,{left:-33,right:33,top:33,bottom:-33,near:1,far:90});sun.shadow.bias=-.0004;sun.shadow.normalBias=.035;sun.shadow.radius=2.5;
  scene.add(sun);hemisphere=new THREE.HemisphereLight('#e7f2d4','#386d68',1.7);scene.add(hemisphere);ambient=new THREE.AmbientLight('#d9e7c3',.35);scene.add(ambient);
  progress(25,'돌과 나무에 색을 입히는 중');textures=await loadTextures();progress(55,'호숫가의 작은 물건을 놓는 중');
  buildWorld();applyQuality();setView('overview',true);changeSunlight(68);setupUI();progress(85,'물결과 바람을 깨우는 중');
  // Quality diagnostics are intentionally kept out of the default viewing UI.
  window.lakeViewer={getStats:()=>({...sceneStats,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,quality,paused,view:currentView}),setView:(name)=>views[name]&&setView(name),scene,renderer,camera};
  requestAnimationFrame(frame);
}
start().catch(fail);

// Offline renders of the actual meshes provide an explicitly labeled fallback.
async function startStillPreview(){
  progress(55,'정지된 렌더 미리보기를 불러오는 중');
  const still=await loadImage('./assets/previews/overview.jpg');
  still.id='fallback-preview';still.alt='실제 3D 모델을 렌더링한 숲속 호수 정지 미리보기';canvas.before(still);canvas.hidden=true;
  document.body.classList.add('still-mode');document.body.dataset.ready='still';window.__lakeReady=true;
  $('.live-label').innerHTML='<i></i> RENDER PREVIEW';
  const info=document.createElement('p');info.className='still-notice';info.textContent='정지 미리보기 · 이 브라우저는 WebGL이 비활성화되어 있습니다.';$('#viewer').append(info);
  $('#sunlight').disabled=true;document.querySelectorAll('[data-quality]').forEach(b=>b.disabled=true);$('#autorotate').hidden=true;$('#pause').hidden=true;
  $('#render-info').textContent='실제 3D 모델의 렌더 이미지입니다. WebGL 2가 활성화된 브라우저에서는 회전·확대와 실시간 물결이 제공됩니다.';
  $('.gesture-hint').textContent='아래 버튼으로 각 장소의 렌더 이미지를 볼 수 있습니다.';
  const select=name=>{currentView=name;still.src='./assets/previews/'+name+'.jpg';document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===name);b.setAttribute('aria-pressed',String(b.dataset.view===name));});};
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>select(b.dataset.view)));$('#reset').addEventListener('click',()=>select('overview'));
  for(const name of ['settings','reference']){const button=$('#'+name+'-toggle'),panel=$('#'+name);button.addEventListener('click',()=>{const open=panel.hidden;$('#settings').hidden=true;$('#reference').hidden=true;$('#settings-toggle').setAttribute('aria-expanded','false');$('#reference-toggle').setAttribute('aria-expanded','false');panel.hidden=!open;button.setAttribute('aria-expanded',String(open));});$('#'+name+'-close').addEventListener('click',()=>{panel.hidden=true;button.setAttribute('aria-expanded','false');});}
  $('#clean-view').addEventListener('click',()=>setClean(true));$('#restore-ui').addEventListener('click',()=>setClean(false));
  $('#capture').addEventListener('click',()=>{const a=document.createElement('a');a.href=still.src;a.download='Emerald_Lake_'+currentView+'.jpg';a.click();});
  window.addEventListener('keydown',e=>{if(e.code==='KeyH')setClean(!uiClean);if(e.code==='Escape')setClean(false);if(e.code==='KeyR')select('overview');});
  progress(100);$('#loading').classList.add('loaded');setTimeout(()=>$('#loading').hidden=true,650);
}
