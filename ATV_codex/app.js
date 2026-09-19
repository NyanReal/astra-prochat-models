const $=id=>document.getElementById(id);
const viewer=$('viewer');
const load=async path=>{const r=await fetch(new URL(path,import.meta.url));if(!r.ok)throw Error(`${path}: ${r.status}`);return r;};
const text=async path=>(await load(path)).text();
const json=async path=>(await load(path)).json();
viewer.addEventListener('load',()=>{$('model-status').textContent='GLB 로드 완료';});
viewer.addEventListener('error',()=>{$('model-status').textContent='모델 로드 실패 · HTTP 실행 확인';});
if(location.protocol==='file:')$('file-warning').hidden=false;
document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-selected',String(b===button));});
  const tab=button.dataset.tab,model=tab==='model';
  viewer.hidden=!model;$('flat-preview').hidden=model;$('camera-controls').hidden=!model;$('orbit-hint').hidden=!model;
  if(!model){$('flat-preview').src={texture:'assets/atv_basecolor.png',uv:'assets/atv_uv.svg',reference:'assets/reference.png'}[tab];$('flat-preview').alt=button.textContent;}
}));
document.querySelectorAll('[data-orbit]').forEach(button=>button.addEventListener('click',()=>{
  viewer.cameraOrbit=button.dataset.orbit;viewer.autoRotate=false;$('rotate').setAttribute('aria-pressed','false');
  document.querySelectorAll('[data-orbit]').forEach(b=>b.classList.toggle('selected',b===button));
}));
$('rotate').addEventListener('click',()=>{viewer.autoRotate=!viewer.autoRotate;$('rotate').setAttribute('aria-pressed',String(viewer.autoRotate));});
async function copy(id,button){
  const content=$(id).textContent,original=button.textContent;
  try{await navigator.clipboard.writeText(content);button.textContent='복사 완료 ✓';}
  catch{const range=document.createRange();range.selectNodeContents($(id));const selection=getSelection();selection.removeAllRanges();selection.addRange(range);button.textContent='선택됨 · Ctrl+C로 복사';}
  setTimeout(()=>button.textContent=original,2500);
}
$('copy-brief').onclick=()=>copy('brief-text',$('copy-brief'));
$('copy-response').onclick=()=>copy('response-text',$('copy-response'));
await Promise.allSettled([
  text('docs/user-brief.txt').then(t=>$('brief-text').textContent=t),
  text('docs/final-response.md').then(t=>$('response-text').textContent=t),
  json('assets/model-stats.json').then(s=>{$('tri-count').textContent=s.triangles.toLocaleString();$('texture-size').textContent=`${s.textureWidth} × ${s.textureHeight}`;}),
  json('docs/validation.json').then(v=>$('validation-text').textContent=`GLB ${v.glbTriangles.toLocaleString()} 트라이앵글. UV 중첩 ${v.positiveAreaOverlapPairs}쌍, 면적 0 UV ${v.degenerateUVTriangles}개, 범위 이탈 ${v.uvOutOfBounds}개. 검사 결과: ${v.result}.`),
  json('docs/ue57-validation.json').then(v=>$('ue-validation-text').textContent=v.result==='PASS'?`UE ${v.engine.split('-')[0]} 실제 임포트 검증 통과. LOD0 ${v.lod0Triangles.toLocaleString()} 트라이앵글 / 머터리얼 ${v.materialSlots.length}개.`:`UE 실제 실행 검증: ${v.result}. ${v.note||''}`),
  json('docs/execution.json').then(m=>{$('meta-model').textContent=m.model;$('meta-effort').textContent=m.reasoningEffort;$('meta-duration').textContent=m.elapsedDisplay;$('meta-time-note').textContent=m.measurementNote;})
]);
document.querySelectorAll('.zip-button').forEach(b=>b.addEventListener('click',downloadKit));
async function downloadKit(){
  const buttons=[...document.querySelectorAll('.zip-button')];buttons.forEach(b=>b.disabled=true);
  const status=$('zip-status');
  try{
    if(location.protocol==='file:')throw Error('start-preview.cmd 실행 후 HTTP 페이지에서 다운로드하세요.');
    status.textContent='산출물 목록을 확인하는 중…';
    const manifest=await json('manifest.json'),files={};
    const base=new URL('./',import.meta.url);
    let complete=0;
    for(const item of manifest.files){
      // Strict allowlist manifest, reject every traversal/absolute/encoded path.
      if(!/^[a-zA-Z0-9_./-]+$/.test(item.path)||item.path.startsWith('/')||item.path.split('/').some(s=>s==='..'||s==='.'||!s))throw Error('허용되지 않은 ZIP 경로');
      const url=new URL(item.path,base);
      if(url.origin!==base.origin||!url.pathname.startsWith(base.pathname))throw Error('atv 범위를 벗어난 경로');
      const response=await fetch(url);if(!response.ok)throw Error(`파일 읽기 실패: ${item.path}`);
      const bytes=new Uint8Array(await response.arrayBuffer());
      if(bytes.length!==item.bytes)throw Error(`파일 변경 감지: ${item.path}. manifest를 재생성하세요.`);
      files['atv/'+item.path]=bytes;status.textContent=`파일 준비 ${++complete} / ${manifest.files.length} — ${item.path}`;
    }
    const mr=await load('manifest.json');files['atv/manifest.json']=new Uint8Array(await mr.arrayBuffer());
    status.textContent='브라우저에서 ZIP을 생성하는 중…';
    const data=await new Promise((resolve,reject)=>fflate.zip(files,{level:1},(error,data)=>error?reject(error):resolve(data)));
    const blob=new Blob([data],{type:'application/zip'}),url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download='ATV-Trail-Asset-Kit.zip';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
    status.textContent=`ZIP 생성 완료 · ${manifest.files.length+1}개 파일 · ${(blob.size/1048576).toFixed(1)} MB · 다운로드가 시작되었습니다.`;
  }catch(error){status.textContent=`다운로드 실패: ${error.message}`;}
  finally{buttons.forEach(b=>b.disabled=false);}
}
