"""Capture the actual self-contained WebGL page, never a replacement illustration."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation';OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1200},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((ROOT/'index.html').read_text(),wait_until='load',timeout=60000)
    page.wait_for_function('window.TREE_READY||window.TREE_ERROR',timeout=30000)
    assert page.evaluate('window.TREE_READY'),page.evaluate('window.TREE_ERROR')
    for name,angle,elev,mode in [('overview',32,25,'tree'),('front',0,6,'tree'),('right',90,6,'tree'),('back',180,6,'tree'),('top',0,89.5,'tree'),('branches',32,18,'trunk'),('branches-back',210,20,'trunk'),('branches-top',0,89.5,'trunk')]:
        page.evaluate('(s)=>TreePreview.set(s)',dict(angle=angle,elevation=elev,mode=mode,pan=[0,0,0],zoom=.95,paused=True,time=0,wind=0,hideUI=True))
        page.screenshot(path=str(OUT/('crown-'+name+'.png')))
    page.evaluate('TreePreview.set({...TreeOrbit.home(),hideUI:false,paused:true})')
    page.screenshot(path=str(OUT/'crown-ui.png'))
    assert not errors,errors
    (OUT/'crown-capture.json').write_text(json.dumps(dict(stats=page.evaluate('TreePreview.stats()'),errors=errors),ensure_ascii=False,indent=2))
    browser.close()
