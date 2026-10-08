from pathlib import Path
import json,base64
ROOT=Path(__file__).resolve().parents[1]
scene=(ROOT/'assets/scene.json').read_text()
images={k:'data:image/png;base64,'+base64.b64encode((ROOT/'assets'/n).read_bytes()).decode() for k,n in [('bark','trunk_basecolor.png'),('leaf','leaves_rgba.png'),('normal','trunk_normal_gl.png')]}
page=(ROOT/'src/page.html').read_text().replace('/*__SCENE_DATA__*/','window.TREE_SCENE='+scene+';window.TREE_IMAGES='+json.dumps(images)+';').replace('/*__ORBIT_SOURCE__*/',(ROOT/'src/orbit-camera.js').read_text()).replace('/*__VIEWER_SOURCE__*/',(ROOT/'src/viewer.js').read_text())
(ROOT/'index.html').write_text(page)
print('Self-contained index.html:',len(page),'bytes')
