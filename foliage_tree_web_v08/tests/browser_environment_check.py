"""Grass changes are measured from the compiled production vertex shader on the GPU.
Run with xvfb-run -a python tests/browser_environment_check.py.
"""
from pathlib import Path
import json,re,subprocess
import numpy as np
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation'
VERT=re.search(r'const VERT=`(.*?)`;', (ROOT/'src/viewer.js').read_text(),re.S).group(1)
VERT=VERT.replace('${Env.GRASS_GLSL}',subprocess.check_output(['node','-e',"process.stdout.write(require('./src/environment.js').GRASS_GLSL)"],cwd=ROOT,text=True))
GPU=r'''({source})=>{
 const gl=document.createElement('canvas').getContext('webgl2');const p=gl.createProgram();
 function shader(t,s){const a=gl.createShader(t);gl.shaderSource(a,s);gl.compileShader(a);if(!gl.getShaderParameter(a,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(a));return a;}
 gl.attachShader(p,shader(gl.VERTEX_SHADER,source));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,'#version 300 es\nprecision highp float;out vec4 c;void main(){c=vec4(1.);}'));
 gl.transformFeedbackVaryings(p,['vPosition'],gl.INTERLEAVED_ATTRIBS);gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));gl.useProgram(p);
 const m=window.GRASS_MESH,n=m.position.length/3,v=gl.createVertexArray();gl.bindVertexArray(v);
 [['position',3],['normal',3],['uv',2],['color',3],['pivot',3],['phase',1],['proxyNormal',3],['bunchIndex',1]].forEach(([k,size],i)=>{
  const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(m[k]),gl.STATIC_DRAW);gl.enableVertexAttribArray(i);gl.vertexAttribPointer(i,size,gl.FLOAT,false,0,0);
 });
 const out=gl.createBuffer();gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,out);gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER,n*12,gl.STREAM_READ);gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER,0,out);
 const one=(k,x)=>gl.uniform1f(gl.getUniformLocation(p,k),x);
 gl.uniform1i(gl.getUniformLocation(p,'uLeaf'),0);gl.uniform1i(gl.getUniformLocation(p,'uGrass'),1);
 one('uLeafScale',1);const eye=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
 for(const name of ['uVP','uLightVP'])gl.uniformMatrix4fv(gl.getUniformLocation(p,name),false,eye);
 function capture(master,ratio,time){one('uWind',master);one('uGrassWindRatio',ratio);one('uTime',time);
  gl.enable(gl.RASTERIZER_DISCARD);gl.beginTransformFeedback(gl.POINTS);gl.drawArrays(gl.POINTS,0,n);gl.endTransformFeedback();gl.disable(gl.RASTERIZER_DISCARD);
  const r=new Float32Array(n*3);gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER,0,r);return r;
 }
 const base=capture(0,2,0),zeroMaster=capture(0,2,8),zeroRatio=capture(1,0,8),a=capture(.7,1,1.7),b=capture(.7,2,1.7),otherTime=capture(.7,1,5.6);
 let rootError=0,masterZeroError=0,ratioZeroError=0,doubleError=0,maxTipMove=0,temporalMove=0,cpuError=0,roots=0;
 for(let i=0;i<n;i++){
  if(m.uv[i*2+1]===0)roots++;
  const offset=TreeEnvironment.grassOffset(m.pivot.slice(i*3,i*3+3),m.proxyNormal[i*3],m.uv[i*2+1],m.phase[i],1.7,.7,1);
  for(let j=0;j<3;j++){const k=i*3+j;
   if(m.uv[i*2+1]===0)rootError=Math.max(rootError,Math.abs(a[k]-base[k]),Math.abs(b[k]-base[k]));
   masterZeroError=Math.max(masterZeroError,Math.abs(zeroMaster[k]-base[k]));ratioZeroError=Math.max(ratioZeroError,Math.abs(zeroRatio[k]-base[k]));
   doubleError=Math.max(doubleError,Math.abs((b[k]-base[k])-2*(a[k]-base[k])));
   maxTipMove=Math.max(maxTipMove,Math.abs(a[k]-base[k]));temporalMove=Math.max(temporalMove,Math.abs(otherTime[k]-a[k]));
   cpuError=Math.max(cpuError,Math.abs(a[k]-m.position[k]-offset[j]));
  }
 }
 const err=gl.getError();gl.getExtension('WEBGL_lose_context')?.loseContext();
 return {vertices:n,roots,rootError,masterZeroError,ratioZeroError,doubleError,maxTipMove,temporalMove,cpuError,glError:err};
}'''
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.evaluate('''()=>{const f=WebGL2RenderingContext.prototype.createProgram;window.__programs=[];WebGL2RenderingContext.prototype.createProgram=function(){let p=f.call(this);window.__programs.push({gl:this,p});return p;};}''')
 page.set_content((ROOT/'index.html').read_text(),wait_until='load',timeout=60000);page.wait_for_function('window.TREE_READY||window.TREE_ERROR')
 assert page.evaluate('window.TREE_READY'),page.evaluate('window.TREE_ERROR')
 page.evaluate('TreePreview.set({wind:.8,grassWindRatio:.5,time:1.7,paused:true})')
 st=page.evaluate('TreePreview.stats()');assert abs(st['effectiveGrassWind']-.4)<1e-7
 uniforms=page.evaluate('''()=>__programs.map(({gl,p})=>Object.fromEntries(['uWind','uGrassWindRatio','uTime'].map(k=>[k,gl.getUniform(p,gl.getUniformLocation(p,k))])))''')
 for u in uniforms:assert abs(u['uWind']-.8)<1e-6 and abs(u['uGrassWindRatio']-.5)<1e-6
 gpu=page.evaluate(GPU,{'source':VERT});assert gpu['glError']==0,gpu
 assert gpu['rootError']==0 and gpu['masterZeroError']==0 and gpu['ratioZeroError']==0,gpu
 assert gpu['doubleError']<3e-7,gpu
 # GPU sin() is implementation-approximated; CPU reference tolerance is 0.05 mm.
 assert gpu['cpuError']<5e-5,gpu
 assert gpu['maxTipMove']>.015 and gpu['temporalMove']>.025,gpu
 # Actual browser range keyboard input, not directly changing application state.
 slider=page.locator('#grass-wind');slider.focus();slider.press('Home');assert page.evaluate('TreePreview.getState().grassWindRatio')==0
 slider.press('End');assert page.evaluate('TreePreview.getState().grassWindRatio')==2
 assert page.evaluate('TreePreview.getState().wind')==.8
 master=page.locator('#wind');master.focus();master.press('Home');assert page.evaluate('TreePreview.stats().effectiveGrassWind')==0
 page.locator('#toggle-grass').click();assert not page.evaluate('TreePreview.getState().grass')
 page.locator('#toggle-ground').click();assert not page.evaluate('TreePreview.getState().forestFloor')
 page.locator('#reset').click();st=page.evaluate('TreePreview.getState()')
 assert st['grassWindRatio']==.65 and st['grass'] and st['forestFloor']
 page.evaluate('TreePreview.set({paused:true})');assert '14.3%' in page.locator('#grass-effective').inner_text()
 page.locator('#roots-view').click();assert page.evaluate('TreePreview.getState().zoom')==2.25
 page.evaluate('TreePreview.set({hideUI:true,time:2})');page.screenshot(path=str(OUT/'forest-roots.png'))
 page.evaluate('TreePreview.set({angle:-22,elevation:23,zoom:.93,pan:[0,-.07,0],hideUI:true})');page.screenshot(path=str(OUT/'forest-overview.png'))
 page.evaluate('TreePreview.set({...TreeOrbit.home(),hideUI:false})');page.locator('.panel').evaluate('(e)=>e.scrollTop=0');page.screenshot(path=str(OUT/'forest-ui.png'))
 # Mobile portrait controls fit within a scrollable panel; free orbit continues to work.
 page.set_viewport_size({'width':820,'height':1180});page.evaluate('TreePreview.set({...TreeOrbit.home(),paused:true})')
 page.screenshot(path=str(OUT/'forest-tablet.png'))
 page.mouse.move(610,350);page.mouse.down();page.mouse.move(700,400,steps=5);page.mouse.up();assert abs(page.evaluate('TreePreview.getState().angle'))>10
 assert not errors,errors
 report={'gpuGrassChecks':gpu,'bothPassUniforms':uniforms,'uiChecks':['multiplier 0..2','master zero stops grass','grass multiplier does not change tree master','reset restores .65','grass/floor visibility','root close-up','tablet orbit'],
  'stats':page.evaluate('TreePreview.stats()'),'errors':errors,'source':'actual shipped index.html + production vertex shader transform feedback'}
 (OUT/'environment-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));b.close()
