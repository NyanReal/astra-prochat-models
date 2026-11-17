from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
 page.set_content((ROOT/'index.html').read_text(),wait_until='load');page.wait_for_function('window.TREE_READY||window.TREE_ERROR')
 for name,s in [('forest-overview',{'angle':-22,'elevation':23,'zoom':.93,'pan':[0,-.07,0]}),('forest-roots',{'angle':22,'elevation':32,'zoom':2.25,'pan':[0,-1.55,0]}),('forest-above',{'angle':0,'elevation':65,'zoom':.84,'pan':[0,-.3,0]})]:
  page.evaluate('(s)=>TreePreview.set({...s,time:2,wind:.22,grassWindRatio:.65,paused:true,hideUI:true})',s)
  page.screenshot(path=str(ROOT/'validation'/f'{name}.png'))
 page.evaluate('TreePreview.set({...TreeOrbit.home(),hideUI:false,paused:true,wind:.22,grassWindRatio:.65})')
 page.screenshot(path=str(ROOT/'validation'/'forest-ui.png'))
 b.close()
