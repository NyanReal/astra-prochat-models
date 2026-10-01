"""Capture real GLB renders in the bundled WebGL renderer; no concept-image substitution."""
from pathlib import Path
import base64,json,os,re,subprocess,time,argparse
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]

def setup(page):
    html=(R/'preview/index.html').read_text();html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.S);html=re.sub(r'<link[^>]*>','',html)
    css=(R/'preview/style.css').read_text();poster='data:image/jpeg;base64,'+base64.b64encode((R/'preview/poster.jpg').read_bytes()).decode();css=css.replace("url('poster.jpg')","url('"+poster+"')")
    html=html.replace('</head>','<style>'+css+'</style></head>').replace('../textures/HOPPER_Arms_UV_Islands_2K.png','data:image/png;base64,'+base64.b64encode((R/'textures/HOPPER_Arms_UV_Islands_2K.png').read_bytes()).decode())
    page.set_content(html,wait_until='domcontentloaded')
    for f in ['asset-info.js','engine.js','arm-engine.js','model-data.js','app.js']:page.add_script_tag(content=(R/'preview'/f).read_text())
    page.click('#load');page.wait_for_function('window.__HOPPER_READY__===true',timeout=60000)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');args=ap.parse_args()
    xs=subprocess.Popen(['Xvfb',':91','-screen','0','1600x1400x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.5)
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=False,env={**os.environ,'DISPLAY':':91'},args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1150,'height':1100},device_scale_factor=1);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));setup(page)
        page.evaluate('document.body.classList.add("clean")');
        shots={'modules':"hopper.setMode('modules');hopper.camera('modules')",'mounted':"hopper.setMode('mounted');hopper.setExplode(0);hopper.pose(false);hopper.camera('assembled')",'open':"hopper.setMode('mounted');hopper.pose(true);hopper.camera('assembled')",'rear':"hopper.setMode('modules');hopper.camera('back')",'inner':"hopper.setMode('R');hopper.armArmor=false;hopper.camera('single')",'connector':"hopper.setMode('R');hopper.armArmor=true;hopper.onlyInterface=true;hopper.camera('socket')",'elbow':"hopper.setMode('R');hopper.armArmor=true;hopper.camera('elbow')",'hand':"hopper.setMode('R');hopper.armArmor=true;hopper.camera('hand')",'fit':"hopper.setMode('mounted');hopper.pose(false);hopper.armArmor=true;hopper.setExplode(.125);hopper.camera('fit')"}
        if args.quick:shots={k:v for k,v in shots.items() if k in ['modules','mounted','inner','connector']}
        for name,code in shots.items():
            page.evaluate(code+';hopper.render()');page.screenshot(path=str(R/f'preview/{name}.png'));print('RENDER',name,flush=True)
        assert not errors,errors;print('GL errors',page.evaluate('hopper.gl.getError()'),flush=True)
        browser.close()
    finally:xs.terminate();xs.wait(timeout=5)
if __name__=='__main__':main()
