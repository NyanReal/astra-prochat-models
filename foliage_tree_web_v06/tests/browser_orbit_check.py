"""Actual shipped-HTML regression: input, all-side billboards, GPU normal invariance.
Run: xvfb-run -a python tests/browser_orbit_check.py
Uses set_content because this environment blocks browser URL navigation.
"""
from pathlib import Path
import json,re,hashlib
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation';OUT.mkdir(exist_ok=True)
VERT=re.search(r'const VERT=`(.*?)`;', (ROOT/'src/viewer.js').read_text(),re.S).group(1)
# Captures transformed outputs of the PRODUCTION vertex shader, not a rewritten formula.
GPU_TEST=r'''({vertexSource})=>{
 const element=document.createElement('canvas');
 const gl=element.getContext('webgl2'); if(!gl)throw Error('No test WebGL2 context');
 const prog=gl.createProgram();
 const compile=(t,s)=>{const a=gl.createShader(t);gl.shaderSource(a,s);gl.compileShader(a);
  if(!gl.getShaderParameter(a,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(a));return a;};
 gl.attachShader(prog,compile(gl.VERTEX_SHADER,vertexSource));
 gl.attachShader(prog,compile(gl.FRAGMENT_SHADER,'#version 300 es\nprecision highp float;out vec4 c;void main(){c=vec4(1.);}'));
 gl.transformFeedbackVaryings(prog,['vPosition','vProxy','vColor'],gl.INTERLEAVED_ATTRIBS);
 gl.linkProgram(prog);if(!gl.getProgramParameter(prog,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(prog));gl.useProgram(prog);
 const mesh=window.TREE_SCENE.foliage,count=mesh.position.length/3;
 const vao=gl.createVertexArray();gl.bindVertexArray(vao);
 [['position',3],['normal',3],['uv',2],['color',3],['pivot',3],['phase',1],['proxyNormal',3],['bunchIndex',1]].forEach(([k,n],i)=>{
  const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(mesh[k]),gl.STATIC_DRAW);
  gl.enableVertexAttribArray(i);gl.vertexAttribPointer(i,n,gl.FLOAT,false,0,0);
 });
 const tf=gl.createTransformFeedback();gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK,tf);
 const output=gl.createBuffer();gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,output);gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER,count*9*4,gl.DYNAMIC_READ);gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER,0,output);
 const u=(n)=>gl.getUniformLocation(prog,n);
 const identity=new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
 gl.uniformMatrix4fv(u('uVP'),false,identity);gl.uniformMatrix4fv(u('uLightVP'),false,identity);
 gl.uniform1i(u('uLeaf'),1);gl.uniform1f(u('uLeafScale'),1);
 const views=[{angle:0,elevation:5,wind:0},{angle:90,elevation:5,wind:0},{angle:180,elevation:40,wind:0},{angle:-130,elevation:89,wind:.7},{angle:50,elevation:-80,wind:.7}];
 const result=[];let baseline=null;
 for(const v of views){
  const c=TreeOrbit.camera({...TreePreview.getState(),...v},1280,960);
  gl.uniform3fv(u('uCardRight'),c.right);gl.uniform3fv(u('uCardUp'),c.up);gl.uniform1f(u('uWind'),v.wind);gl.uniform1f(u('uTime'),3.7);
  gl.enable(gl.RASTERIZER_DISCARD);gl.beginTransformFeedback(gl.POINTS);gl.drawArrays(gl.POINTS,0,count);gl.endTransformFeedback();gl.disable(gl.RASTERIZER_DISCARD);
  // Intentional synchronous QA readback: may log a performance stall warning.
  // Production rendering performs no GPU readback and does not use this probe.
  const data=new Float32Array(count*9);gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,output);gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER,0,data);
  if(!baseline)baseline=data;
  let proxyDelta=0,colorDelta=0,minFacing=1,maxPlaneError=0;
  for(let i=0;i<count;i++)for(let j=0;j<3;j++){
   proxyDelta=Math.max(proxyDelta,Math.abs(data[i*9+3+j]-baseline[i*9+3+j]));
   colorDelta=Math.max(colorDelta,Math.abs(data[i*9+6+j]-baseline[i*9+6+j]));
  }
  for(let i=0;i<count;i+=4){
   const a=[0,1,2].map(j=>data[(i+1)*9+j]-data[i*9+j]);
   const b=[0,1,2].map(j=>data[(i+3)*9+j]-data[i*9+j]);
   const n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
   minFacing=Math.min(minFacing,n.reduce((s,x,j)=>s+x*c.back[j],0)/Math.hypot(...n));
   maxPlaneError=Math.max(maxPlaneError,Math.abs(a.reduce((s,x,j)=>s+x*c.back[j],0)),Math.abs(b.reduce((s,x,j)=>s+x*c.back[j],0)));
  }
  result.push({...v,proxyDelta,colorDelta,minFacing,maxPlaneError});
 }
 const error=gl.getError();gl.getExtension('WEBGL_lose_context')?.loseContext();
 return {cards:count/4,views:result,glError:error};
}'''
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
 errors=[];warnings=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:warnings.append(m.text) if m.type in ('error','warning') else None)
 # Observe actual created GL program handles without changing GL behaviour.
 page.evaluate('''()=>{const original=WebGL2RenderingContext.prototype.createProgram;window.__programs=[];
 WebGL2RenderingContext.prototype.createProgram=function(){const p=original.call(this);window.__programs.push({gl:this,p});return p;};}''')
 page.set_content((ROOT/'index.html').read_text(),wait_until='load',timeout=45000)
 page.wait_for_function('window.TREE_READY || window.TREE_ERROR',timeout=30000)
 assert page.evaluate('!!window.TREE_READY'),page.evaluate('window.TREE_ERROR')
 page.evaluate('TreePreview.set({time:0,wind:0,paused:true})')
 base=page.evaluate('TreePreview.getState()')
 # Actual mouse drag, even while wind animation is paused.
 page.mouse.move(950,300);page.mouse.down();page.mouse.move(1180,370,steps=8);page.mouse.up()
 drag=page.evaluate('TreePreview.getState()')
 assert abs(drag['angle']-base['angle'])>30,drag
 assert abs(drag['elevation']-base['elevation'])>10,drag
 page.mouse.wheel(0,-420);page.wait_for_timeout(120)
 zoom=page.evaluate('TreePreview.getState()')
 assert zoom['zoom']>drag['zoom']*1.4,zoom
 page.mouse.move(960,320);page.mouse.down(button='right');page.mouse.move(1025,345,steps=4);page.mouse.up(button='right')
 pan=page.evaluate('TreePreview.getState()');assert np.linalg.norm(pan['pan'])>.05
 # UI buttons, reset-camera, all modes, and PNG download.
 page.locator('#reset-camera').click();reset=page.evaluate('TreePreview.getState()')
 assert reset['angle']==0 and reset['zoom']==1 and reset['pan']==[0,0,0]
 page.locator('[data-angle="180"]').click();assert page.evaluate('TreePreview.getState().angle')==-180
 page.locator('[data-elevation="89.5"]').click();assert page.evaluate('TreePreview.getState().elevation')==89.5
 page.keyboard.press('f');assert page.evaluate('TreePreview.getState().angle')==0
 for mode in ['normal','value','cards','trunk','uv','tree']:
  page.locator(f'[data-mode="{mode}"]').click();assert page.evaluate('TreePreview.getState().mode')==mode
 with page.expect_download() as d:
  page.locator('#capture').click()
 assert d.value.suggested_filename=='tree-web-v06-freeview.png'
 # Check colour/normal streams on the GPU at all angles, including with wind.
 gpu=page.evaluate(GPU_TEST,{'vertexSource':VERT})
 assert gpu['glError']==0,gpu
 for v in gpu['views']:
  assert v['proxyDelta']==0 and v['colorDelta']==0,v
  assert v['minFacing']>.99999 and v['maxPlaneError']<1e-5,v
 # The actual uniforms of both production passes: camera cannot rotate the light or shadow proxy.
 uniform_snapshots=[]
 for angle,elevation in [(0,5),(90,25),(180,60)]:
  page.evaluate('(s)=>TreePreview.set(s)',{'angle':angle,'elevation':elevation})
  uniform_snapshots.append(page.evaluate('''()=>window.__programs.slice(0,2).map(({gl,p})=>{
    const get=n=>{const l=gl.getUniformLocation(p,n);const v=l?gl.getUniform(p,l):null;return v&&v.length?Array.from(v):v;};
    return {right:get('uCardRight'),up:get('uCardUp'),light:get('uLight'),lightVP:get('uLightVP')};})'''))
 for snap in uniform_snapshots:
  assert snap[1]['right']==[1,0,0] and snap[1]['up']==[0,1,0],snap
  assert snap[0]['light']==uniform_snapshots[0][0]['light'],snap
  assert snap[0]['lightVP']==uniform_snapshots[0][0]['lightVP'],snap
 assert uniform_snapshots[0][0]['right']!=uniform_snapshots[1][0]['right']
 # Render the actual page in multiple views. No separate tree renderer.
 views=[('front',0,5),('right',90,8),('back',180,8),('above',35,55),('top',0,89.5),('below',-35,-40)]
 image_stats={}
 for name,angle,elevation in views:
  page.evaluate('(s)=>TreePreview.set(s)',{'angle':angle,'elevation':elevation,'zoom':1,'pan':[0,0,0],'mode':'tree','hideUI':True,'wind':0,'time':0,'paused':True})
  page.screenshot(path=str(OUT/f'freeview-{name}.png'))
  pix=np.asarray(Image.open(OUT/f'freeview-{name}.png').convert('RGB'),float)
  green=(pix[:,:,1]>pix[:,:,0]*1.08)&(pix[:,:,1]>pix[:,:,2]*1.05)
  n=int(green.sum());assert n>35000,(name,n)
  image_stats[name]={'foliagePixels':n,'sha256':hashlib.sha256((OUT/f'freeview-{name}.png').read_bytes()).hexdigest()}
 page.evaluate('TreePreview.set({...TreeOrbit.home(),hideUI:false})')
 page.screenshot(path=str(OUT/'freeview-ui.png'))
 info=page.evaluate('TreePreview.stats()');assert info['glError']==0
 # CDP dispatches real browser touch input, exercising Pointer Events and capture.
 touch=b.new_page(viewport={'width':820,'height':1180},device_scale_factor=1,is_mobile=True,has_touch=True)
 touch.set_content((ROOT/'index.html').read_text(),wait_until='load',timeout=45000)
 touch.wait_for_function('window.TREE_READY || window.TREE_ERROR',timeout=30000)
 assert touch.evaluate('!!window.TREE_READY'),touch.evaluate('window.TREE_ERROR')
 touch.evaluate('TreePreview.set({paused:true,wind:0,time:0})')
 client=touch.context.new_cdp_session(touch)
 def event(kind,points):client.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':[{'x':x,'y':y,'id':i,'radiusX':5,'radiusY':5,'force':1} for i,x,y in points]})
 event('touchStart',[(1,570,320)])
 for x in [590,610,630,650]:event('touchMove',[(1,x,345)])
 event('touchEnd',[])
 one=touch.evaluate('TreePreview.getState()');assert abs(one['angle'])>10,one
 event('touchStart',[(1,500,340),(2,650,340)])
 for step in range(1,5):event('touchMove',[(1,500-step*6,340+step*6),(2,650+step*9,340+step*6)])
 event('touchEnd',[])
 two=touch.evaluate('TreePreview.getState()');assert two['zoom']>one['zoom']*1.2,two
 assert np.linalg.norm(two['pan'])>.01,two
 touch.evaluate('TreePreview.set({...TreeOrbit.home(),wind:0,time:0})')
 touch.screenshot(path=str(OUT/'freeview-tablet.png'))
 assert not errors,errors
 report={'browser':b.version,'tests':'mouse orbit / wheel / pan / camera reset / presets / all modes / actual PNG download / touch orbit / touch pinch+pan / 6 real rendered views / production GPU transform feedback / fixed light+shadow uniforms','mouse':{'drag':drag,'zoom':zoom,'pan':pan},'touch':{'oneFinger':one,'twoFinger':two},'gpu':gpu,'uniforms':uniform_snapshots,'views':image_stats,'stats':info,'errors':errors,'warnings':warnings,'previewSource':'exact shipped index.html in Chromium WebGL2, via page.set_content; no image synthesis'}
 (OUT/'freeview-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print(json.dumps({'passed':True,'gpu':gpu,'glError':info['glError'],'errors':errors,'warnings':warnings,'views':image_stats},indent=2))
 b.close()
