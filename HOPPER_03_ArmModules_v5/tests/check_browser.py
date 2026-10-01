"""Actual Chromium interaction checks. Native Safari/engine import not implied."""
from pathlib import Path
import sys,json,os,subprocess,time,threading,urllib.request
from playwright.sync_api import sync_playwright
from render_preview import setup
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from start_preview import make_server

def run():
    report={'browser':'Chromium / WebGL2 / SwiftShader','checks':[],'physical_iPad_tested':False,'Safari_tested':False,'Blender_Unreal_tested':False}
    server=make_server(port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();port=server.server_address[1]
    root=f'http://127.0.0.1:{port}'
    for path in ['/preview/index.html','/preview/engine.js','/preview/arm-engine.js','/preview/FitCheck.glb','/models/HOPPER_03_Arm_L_M1.glb']:
        with urllib.request.urlopen(root+path) as resp:assert resp.status==200
    report['checks'].append('Static HTTP server returned all sampled assets with HTTP 200')
    xs=subprocess.Popen(['Xvfb',':94','-screen','0','1800x1500x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.5)
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=False,env={**os.environ,'DISPLAY':':94'},args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(root+'/preview/index.html',wait_until='domcontentloaded',timeout=12000)
            page.locator('#load').click(timeout=5000);page.wait_for_function('window.__HOPPER_READY__===true',timeout=25000)
            report['browser_load_route']='Actual HTTP page and GLB fetch'
        except Exception as exc:
            report['browser_load_route']='In-memory HTML and bundled JS; GLB parsed from package base64'
            report['navigation_limitation']=str(exc).splitlines()[0]
            page.close();page=browser.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1);page.on('pageerror',lambda e:errors.append(str(e)));setup(page)
        def check(name,expr):
            assert page.evaluate(expr),name;report['checks'].append(name)
        check('Default view is modules only',"hopper.mode==='modules' && hopper.meshes.flat().filter(p=>hopper.isVisible(p)).every(p=>/^Arm_/.test(p.owner))")
        check('Counts in UI reflect exported data',"document.getElementById('pair-count').textContent==='4,812' && document.getElementById('assembled-count').textContent==='29,870'")
        check('Cockpit disabled when standalone',"document.getElementById('open').disabled && !hopper.playing")
        for s in ['L','R']:
            page.click('[data-mode="'+s+'"]')
            check(s+' isolation',"hopper.meshes.flat().filter(p=>hopper.isVisible(p)).every(p=>p.owner.startsWith('Arm_'+hopper.mode+'_'))")
        page.uncheck('#arm-armor');check('Hide armor preserves mechanical parts',"hopper.meshes.flat().filter(p=>hopper.isVisible(p)).length>0 && hopper.meshes.flat().filter(p=>hopper.isVisible(p)).every(p=>!p.owner.endsWith('Armor'))")
        page.check('#arm-armor');page.check('#interface-only')
        check('Connector interior isolation',"hopper.meshes.flat().filter(p=>hopper.isVisible(p)).every(p=>p.owner.includes('01_Interface_Cup'))")
        page.uncheck('#interface-only');page.click('[data-mode="mounted"]')
        check('Mounted mode restores base and cockpit controls',"!document.getElementById('open').disabled && hopper.meshes.flat().some(p=>hopper.isVisible(p)&&!p.owner.startsWith('Arm_'))")
        page.locator('#explode').evaluate("e=>{e.value=.2;e.dispatchEvent(new Event('input',{bubbles:true}))}")
        check('Separation follows outward world socket axes',"Math.abs(hopper.armRoots.R.t[0]-.767286837)<1e-6 && Math.abs(hopper.armRoots.L.t[0]+.767286837)<1e-6")
        page.locator('#explode').evaluate("e=>{e.value=0;e.dispatchEvent(new Event('input',{bubbles:true}))}")
        check('Zero separation recovers exact mount transforms',"Math.abs(hopper.armRoots.R.t[0]-.567286837)<1e-6 && Math.abs(hopper.armRoots.L.t[0]+.567286837)<1e-6")
        for name,id,final in [('Cockpit_Open','open',96),('Cockpit_Close','close',0),('Cockpit_Cycle','cycle',0)]:
            page.click('#'+id);page.evaluate('hopper.seek(hopper.clip.duration)')
            check(name+' clip endpoint',f"hopper.clip.name==='{name}' && Math.abs(hopper.hatchAngle-{final})<.01")
        page.click('#open');page.locator('#timeline').evaluate("e=>{e.value=1.5;e.dispatchEvent(new Event('input',{bubbles:true}))}")
        check('Mid-open timeline is scrubbed from GLB',"!hopper.playing && hopper.hatchAngle>5 && hopper.hatchAngle<95")
        page.check('#wire');page.evaluate('hopper.render()');check('Wireframe draws without GL error','hopper.gl.getError()===0')
        page.uncheck('#wire');page.evaluate('hopper.render()');check('Solid restored after wireframe','hopper.gl.getError()===0')
        page.click('#uv');check('UV dialog loaded atlas',"document.getElementById('uv-dialog').open && document.querySelector('#uv-dialog img').naturalWidth===2048")
        page.click('#uv-close');check('Dialog closes',"!document.getElementById('uv-dialog').open")
        for camera in ['socket','elbow','hand','fit','back','default']:
            page.click('[data-camera="'+camera+'"]');check('Camera '+camera+' valid',"Number.isFinite(hopper.distance) && hopper.distance>0 && hopper.target.every(Number.isFinite) && hopper.gl.getError()===0")
        page.locator('#explode').evaluate("e=>{e.value=.6;e.dispatchEvent(new Event('input',{bubbles:true}))}");page.click('[data-camera="hand"]');check('Detail camera clears preview separation','hopper.explode===0');page.click('[data-mode="modules"]');page.locator('#explode').evaluate("e=>{e.value=0;e.dispatchEvent(new Event('input',{bubbles:true}))}");page.click('[data-camera="default"]');page.screenshot(path=str(R/'preview/desktop_ui.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(400)
        check('Narrow viewport does not overflow horizontally','document.documentElement.scrollWidth<=window.innerWidth+1')
        page.screenshot(path=str(R/'preview/mobile_ui.png'),full_page=True)
        page.locator('[data-mode="mounted"]').click();page.click('#open');page.evaluate('hopper.seek(3)')
        check('Mobile-sized viewport cockpit control works','Math.abs(hopper.hatchAngle-96)<.01 && hopper.gl.getError()===0')
        check('Download links address separate arm files',"[...document.querySelectorAll('a[download]')].length===2 && [...document.querySelectorAll('a[download]')].every(a=>/HOPPER_03_Arm_[LR]_M1.glb$/.test(a.getAttribute('href')))")
        assert not errors,errors;report['page_errors']=errors;report['checks'].append('No JavaScript page errors')
        browser.close()
    finally:
        server.shutdown();server.server_close();xs.terminate();xs.wait(timeout=5)
    report['passed']=True;report['check_count']=len(report['checks']);(R/'docs/browser_verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':run()
