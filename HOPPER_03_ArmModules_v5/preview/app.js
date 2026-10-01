'use strict';
(()=>{
const $=id=>document.getElementById(id);let renderer=null,loading=false;
const I=window.HOPPER_INFO;
$('load-size').textContent=(I.glb_bytes/1e6).toFixed(1);$('pair-count').textContent=I.pair_triangles.toLocaleString();$('assembled-count').textContent=I.assembled_triangles.toLocaleString();
$('stage-count').textContent=I.pair_triangles.toLocaleString()+' TRIANGLES / PAIR';
$('uv-share').textContent=(I.uv.groups.armor.used_uv_share*100).toFixed(1)+'%';$('uv-density').textContent=I.uv.armor_to_frame_linear_density_ratio.toFixed(2)+'×';
document.querySelector('.uv-meter .armor').style.width=(I.uv.groups.armor.used_uv_share*100)+'%';$('uv-info').textContent=I.uv.unique_islands+'개 독립 배치 영역 · 같은 텍스처, 다른 UV';
function sync(){if(!renderer)return;const mounted=renderer.mode==='mounted';$('mode-label').textContent=mounted?'TEMPORARY FIT CHECK':renderer.mode==='modules'?'DETACHED MODULES':renderer.mode+' / INDEPENDENT MODULE';
 $('view-state').textContent=renderer.onlyInterface?'CONNECTOR INTERIOR':renderer.armArmor?'ENAMEL ARMOR ON':'INNER STRUCTURE';$('clean-pose').textContent=$('mode-label').textContent+' / H03-M1';
 $('explode-value').textContent=Math.round(renderer.explode*1000)+' mm';$('explode').value=renderer.explode;
 for(const b of document.querySelectorAll('[data-mode]'))b.classList.toggle('active',b.dataset.mode===renderer.mode);
 for(const id of ['open','close','cycle','timeline','pause'])$(id).disabled=!mounted;
 $('cockpit-controls').style.opacity=mounted?'1':'.52';$('angle-label').textContent=renderer.hatchAngle.toFixed(0)+'° / 96°';
 if(renderer.clip){$('timeline').max=renderer.clip.duration;$('timeline').value=renderer.time;$('time-label').textContent=renderer.time.toFixed(2)+' / '+renderer.clip.duration.toFixed(2)+' s';}
}
async function local(){if(!window.HOPPER_GLB_BASE64)await new Promise((ok,no)=>{const s=document.createElement('script');s.src='model-data.js';s.onload=ok;s.onerror=()=>no(new Error('model-data.js 파일을 찾을 수 없습니다. ZIP 전체를 압축 해제하세요.'));document.body.appendChild(s);});const txt=atob(window.HOPPER_GLB_BASE64);const arr=Uint8Array.from(txt,c=>c.charCodeAt(0));window.HOPPER_GLB_BASE64=null;return arr.buffer;}
async function start(){if(loading||renderer)return;loading=true;$('load').disabled=true;$('load-status').textContent='GLB와 텍스처를 불러오는 중…';try{
 let buffer;if(window.HOPPER_GLB_BASE64||location.protocol==='file:')buffer=await local();else{const r=await fetch('FitCheck.glb');if(!r.ok)throw new Error('FitCheck.glb 읽기 실패: '+r.status);buffer=await r.arrayBuffer();}
 renderer=new ArmModuleRenderer($('viewport'));window.hopper=renderer;await renderer.load(buffer);renderer.onchange=sync;
 for(const e of document.querySelectorAll('aside button,aside input'))e.disabled=false;$('load-screen').style.display='none';sync();window.__HOPPER_READY__=true;
}catch(e){console.error(e);$('load-status').textContent=e.message;$('load').disabled=false;renderer=null;}finally{loading=false;}}
$('load').onclick=start;
for(const b of document.querySelectorAll('[data-mode]'))b.onclick=()=>{$('interface-only').checked=false;renderer.setMode(b.dataset.mode);sync();};
$('explode').oninput=e=>renderer.setExplode(e.target.value);
$('arm-armor').onchange=e=>{renderer.armArmor=e.target.checked;renderer.render();sync();};$('wire').onchange=e=>{renderer.wire=e.target.checked;renderer.render();};$('rotate').onchange=e=>renderer.spin=e.target.checked;
$('interface-only').onchange=e=>{renderer.onlyInterface=e.target.checked;if(e.target.checked){renderer.setMode('R');renderer.setExplode(0);renderer.onlyInterface=true;renderer.camera('socket');}renderer.render();sync();};
for(const b of document.querySelectorAll('[data-camera]'))b.onclick=()=>{const c=b.dataset.camera;
 if(c==='socket'||c==='elbow'||c==='hand'){renderer.setMode('R');renderer.setExplode(0);$('interface-only').checked=false;}
 if(c==='fit'){renderer.setMode('mounted');renderer.setExplode(.12);}
 renderer.camera(c==='default'?(renderer.mode==='mounted'?'assembled':renderer.mode==='modules'?'modules':'single'):c);sync();};
for(const [id,act] of [['open','Open'],['close','Close'],['cycle','Cycle']])$(id).onclick=()=>renderer.action(act);
$('timeline').oninput=e=>renderer.seek(e.target.value);$('pause').onclick=()=>{renderer.playing=!renderer.playing;sync();};
$('snapshot').onclick=()=>{renderer.render();const a=document.createElement('a');a.download='HOPPER_ArmModules_v5.png';a.href=$('viewport').toDataURL('image/png');a.click();};
$('uv').onclick=()=>$('uv-dialog').showModal();$('uv-close').onclick=()=>$('uv-dialog').close();
const params=new URLSearchParams(location.search);if(params.has('clean'))document.body.classList.add('clean');if(params.has('autoload')||params.has('clean'))start();
})();
