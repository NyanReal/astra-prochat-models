"""v08 acceptance: production GPU normal invariance, orbit, modes and depth layout."""
from pathlib import Path
import json,ast,re,subprocess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation'
# Reuse the production-shader transform-feedback test without running its large UI suite.
tree=ast.parse((ROOT/'tests/browser_orbit_check.py').read_text())
GPU=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GPU_TEST' for t in n.targets))
VERT=re.search(r'const VERT=`(.*?)`;', (ROOT/'src/viewer.js').read_text(),re.S).group(1)
VERT=VERT.replace('${Env.GRASS_GLSL}',subprocess.check_output(['node','-e',"process.stdout.write(require('./src/environment.js').GRASS_GLSL)"],cwd=ROOT,text=True))
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':960,'height':720},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 print('load',flush=True);page.set_content((ROOT/'index.html').read_text(),wait_until='load',timeout=60000)
 page.wait_for_function('window.TREE_READY||window.TREE_ERROR');assert page.evaluate('window.TREE_READY')
 page.evaluate('TreePreview.set({paused:true,wind:0,time:0,hideUI:true})')
 print('GPU',flush=True);gpu=page.evaluate(GPU,{'vertexSource':VERT})
 assert gpu['glError']==0,gpu
 for v in gpu['views']:
  assert v['proxyDelta']==0 and v['colorDelta']==0,v
  assert v['minFacing']>.99999 and v['maxPlaneError']<1e-5,v
 print('mouse',flush=True)
 s=page.evaluate('TreePreview.getState()');page.mouse.move(700,260);page.mouse.down();page.mouse.move(780,300,steps=3);page.mouse.up()
 t=page.evaluate('TreePreview.getState()');assert abs(t['angle']-s['angle'])>10
 page.mouse.wheel(0,-160);page.wait_for_timeout(100);assert page.evaluate('TreePreview.getState().zoom')>1
 page.keyboard.press('f');assert page.evaluate('TreePreview.getState().angle')==0
 print('modes',flush=True)
 for mode in ['trunk','normal','value','uv','cards','tree']:
  print(mode,flush=True);page.evaluate('(m)=>TreePreview.set({mode:m})',mode)
  assert page.evaluate('TreePreview.stats().glError')==0
 print('views',flush=True)
 for yaw,elev in [(0,5),(90,5),(180,5),(-90,5),(0,89.5),(30,-50)]:
  page.evaluate('(s)=>TreePreview.set(s)',dict(angle=yaw,elevation=elev,mode='tree'))
  assert page.evaluate('TreePreview.stats().glError')==0
 assert not errors,errors
 report={'passed':True,'gpu':gpu,'browser':'Chromium / Xvfb / SwiftShader','checks':['actual mouse orbit','wheel zoom','F camera reset','all six render modes at 960x720','all cardinal views plus top and below','production shader camera-facing cards','unchanged proxy normals and colours across cameras'],'errors':errors,'stats':page.evaluate('TreePreview.stats()')}
 (OUT/'crown-browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2),flush=True);b.close()
