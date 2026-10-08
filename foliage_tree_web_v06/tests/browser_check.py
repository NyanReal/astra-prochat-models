"""Run with: xvfb-run -a python tests/browser_check.py
Renders the shipped HTML directly; screenshots are NOT separate reconstructions.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation';OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
 errors=[];warnings=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:warnings.append(m.text) if m.type in ['error','warning'] else None)
 page.set_content((ROOT/'index.html').read_text(),wait_until='load',timeout=60000)
 page.wait_for_function('window.TREE_READY || window.TREE_ERROR',timeout=60000)
 err=page.evaluate('window.TREE_ERROR || null');assert not err,err
 page.evaluate("TreePreview.set({time:0,wind:0,paused:true})")
 page.screenshot(path=str(OUT/'web-ui.png'))
 page.evaluate("TreePreview.set({hideUI:true})")
 page.screenshot(path=str(OUT/'web-render.png'))
 pixels=np.asarray(Image.open(OUT/'web-render.png').convert('RGB'),float)
 green=(pixels[:,:,1]>pixels[:,:,0]*1.08)&(pixels[:,:,1]>pixels[:,:,2]*1.05)
 assert int(green.sum())>35000, 'The real web frame is blank or contains no foliage'
 page.evaluate("TreePreview.set({mode:'trunk',angle:22})")
 page.screenshot(path=str(OUT/'web-trunk.png'))
 page.evaluate("TreePreview.set({mode:'tree',angle:28})")
 page.screenshot(path=str(OUT/'web-angle.png'))
 page.evaluate("TreePreview.set({mode:'tree',angle:0,wind:.8,time:3})")
 page.screenshot(path=str(OUT/'web-wind.png'))
 info=page.evaluate('TreePreview.stats()');assert info['glError']==0,info
 # Real UI actions change viewer state.
 page.evaluate("TreePreview.set({hideUI:false})")
 page.locator('[data-mode="normal"]').click();assert page.evaluate('TreePreview.getState().mode')=='normal'
 page.locator('#reset').click();assert page.evaluate('TreePreview.getState().mode')=='tree'
 page.set_viewport_size({'width':820,'height':1180});page.evaluate('TreePreview.set({wind:0,time:0,paused:true})')
 page.screenshot(path=str(OUT/'web-tablet.png'))
 assert not errors,errors
 info.update(browser=b.version,errors=errors,consoleWarnings=warnings,previewSource='shipped index.html executed in Chromium WebGL2 / SwiftShader; no separate image renderer',viewport=[1440,1080])
 (OUT/'browser-report.json').write_text(json.dumps(info,indent=2,ensure_ascii=False))
 print(json.dumps(info,indent=2,ensure_ascii=False))
 b.close()
