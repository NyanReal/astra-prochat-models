"""Directly load each standalone file without the base / fit-check asset."""
from pathlib import Path
import base64,json,os,subprocess,time
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
def run():
    report={};xs=subprocess.Popen(['Xvfb',':96','-screen','0','1100x1000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.5)
    try:
      with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=False,env={**os.environ,'DISPLAY':':96'},args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        for s in 'LR':
            page=b.new_page(viewport={'width':900,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_content('<html><body style="margin:0"><canvas id="c" style="width:100vw;height:100vh"></canvas></body></html>')
            page.add_script_tag(content=(R/'preview/engine.js').read_text())
            data=base64.b64encode((R/f'models/HOPPER_03_Arm_{s}_M1.glb').read_bytes()).decode()
            result=page.evaluate('''async ({data,sign})=>{let buffer=Uint8Array.from(atob(data),c=>c.charCodeAt(0)).buffer;
               window.testRenderer=new HopperRenderer(document.getElementById('c'));let r=testRenderer;await r.load(buffer);
               r.nodes[0].t=[0,.8847,0];r.nodes[0].r=[0,sign*Math.SQRT1_2,0,Math.SQRT1_2];r.updateWorld();
               r.az=.63*sign;r.el=.20;r.distance=2.32;r.target=[sign*.245,.552,.045];r.render();
               return {nodes:r.nodes.length,triangles:r.meshes.flat().reduce((s,p)=>s+p.count/3,0),textures:r.textures.length,animations:r.clips.length,gl_error:r.gl.getError()};}''',{'data':data,'sign':1 if s=='R' else -1})
            assert result['triangles']==2406 and result['textures']==3 and result['animations']==0 and result['gl_error']==0,result
            assert not errors,errors;page.screenshot(path=str(R/f'preview/standalone_{s}.png'));result['page_errors']=errors;report[s]=result;page.close()
        b.close()
    finally:xs.terminate();xs.wait(timeout=5)
    report['scope']='Direct standalone GLB parsing and actual WebGL render; no base asset loaded.'
    (R/'docs/standalone_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':run()
