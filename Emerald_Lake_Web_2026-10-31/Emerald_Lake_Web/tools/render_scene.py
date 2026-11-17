#!/usr/bin/env python3
"""Render actual exported Three.js meshes in a standalone EGL OpenGL context."""
import os,sys,json,math,argparse,time,re,hashlib
from pathlib import Path
sys.path.insert(0,'/tmp/lake-gl-deps')
os.environ.setdefault('MESA_SHADER_CACHE_DIR','/tmp/lake-mesa-cache')
import moderngl as gl
import numpy as np
from PIL import Image
BASE=Path(__file__).resolve().parent.parent
DATA=BASE/'qa/offline/scene-data'
parser=argparse.ArgumentParser();parser.add_argument('--views',default='overview,dock,stream,camp');parser.add_argument('--width',type=int,default=1536);parser.add_argument('--height',type=int,default=1024);parser.add_argument('--data',default=str(DATA));parser.add_argument('--output',default=str(BASE/'dist/assets/previews'));args=parser.parse_args();DATA=Path(args.data);OUTPUT=Path(args.output);OUTPUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((DATA/'scene.json').read_text());blob=(DATA/'scene.bin').read_bytes()
for source,digest in manifest['sourceHashes'].items():
 current=hashlib.sha256((BASE/'dist/js'/source).read_bytes()).hexdigest()
 if current!=digest:raise RuntimeError('Scene export is stale for '+source+'; rerun export-scene.mjs')
ctx=gl.create_standalone_context(backend='egl');print(ctx.info['GL_RENDERER'],flush=True)
def raw(ref):return blob[ref['offset']:ref['offset']+ref['length']*4]
def normalize(v):return v/np.linalg.norm(v)
def lookat(eye,target):
 eye=np.array(eye,dtype='f4');target=np.array(target,dtype='f4');z=normalize(eye-target);x=normalize(np.cross([0,1,0],z));y=np.cross(z,x);m=np.eye(4,dtype='f4');m[:3,:3]=[x,y,z];m[:3,3]=-m[:3,:3]@eye;return m

def ortho(l,r,b,t,n,f):
 return np.array([[2/(r-l),0,0,-(r+l)/(r-l)],[0,2/(t-b),0,-(t+b)/(t-b)],[0,0,-2/(f-n),-(f+n)/(f-n)],[0,0,0,1]],dtype='f4')
def matwrite(u,m):u.write(m.T.astype('f4').tobytes())
VERT='''#version 330
in vec3 in_pos; in vec3 in_normal; in vec2 in_uv; in vec3 in_color; in float in_path;
in vec4 i0; in vec4 i1; in vec4 i2; in vec4 i3; in vec3 i_color;
uniform mat4 viewproj; uniform mat4 lightvp;
out vec3 vInstance; out vec3 vNormal; out vec3 vWorld; out vec2 vUv; out vec3 vColor; out float vPath; out vec4 vShadow;
void main(){mat4 model=mat4(i0,i1,i2,i3);vec4 p=model*vec4(in_pos,1);vWorld=p.xyz;vNormal=transpose(inverse(mat3(model)))*in_normal;vUv=in_uv;vColor=in_color*i_color;vInstance=i_color;vPath=in_path;vShadow=lightvp*p;gl_Position=viewproj*p;}
'''
COLOR='''
vec3 srgbToLinear(vec3 c){return mix(c/12.92,pow((c+.055)/1.055,vec3(2.4)),step(vec3(.04045),c));}
vec3 linearToSrgb(vec3 c){return mix(c*12.92,1.055*pow(max(c,vec3(0)),vec3(1./2.4))-.055,step(vec3(.0031308),c));}
vec3 aces(vec3 color){
 const mat3 inputMat=mat3(vec3(.59719,.07600,.02840),vec3(.35458,.90834,.13383),vec3(.04823,.01566,.83777));
 const mat3 outputMat=mat3(vec3(1.60475,-.10208,-.00327),vec3(-.53108,1.10813,-.07276),vec3(-.07367,-.00605,1.07602));
 color=inputMat*(color*(1.216/.6));vec3 a=color*(color+.0245786)-.000090537;vec3 b=color*(.983729*color+.4329510)+.238081;return clamp(outputMat*(a/b),0.,1.);
}
'''
FRAG='''#version 330
in vec3 vInstance;in vec3 vNormal;in vec3 vWorld;in vec2 vUv;in vec3 vColor;in float vPath;in vec4 vShadow;
uniform sampler2D tex;uniform sampler2D pathTex;uniform sampler2D shadowTex;
uniform mat3 uvTransform;uniform mat3 pathUvTransform;uniform int texSrgb;uniform int pathSrgb;uniform float alphaTest;uniform int toneMapped;uniform int vertexColors;
uniform int hasTex;uniform int hasPath;uniform int flatNormal;uniform int doubleSide;uniform int basic;uniform int receiveShadow;
uniform vec3 baseColor;uniform vec3 emissive;uniform vec3 eye;uniform float roughness;uniform float metalness;uniform float opacity;
out vec4 outColor;
'''+COLOR+'''
float shadow(){vec3 p=vShadow.xyz/vShadow.w*.5+.5;if(any(lessThan(p,vec3(0)))||any(greaterThan(p,vec3(1))))return 1.;float s=0.;for(int y=-2;y<=2;y++)for(int x=-2;x<=2;x++){float d=texture(shadowTex,p.xy+vec2(x,y)/4096.).r;s+=p.z-.0007<=d?1.:0.;}return s/25.;}
void main(){
 vec3 n=normalize(vNormal);if(flatNormal==1)n=normalize(cross(dFdx(vWorld),dFdy(vWorld)));else if(doubleSide==1&&!gl_FrontFacing)n=-n;
 vec3 color=baseColor*(vertexColors==1?vColor:vInstance);float alpha=opacity;if(hasTex==1){vec4 sampleColor=texture(tex,(uvTransform*vec3(vUv,1)).xy);vec3 tc=texSrgb==1?srgbToLinear(sampleColor.rgb):sampleColor.rgb;alpha*=sampleColor.a;if(hasPath==1){tc=mix(vec3(.12,.23,.035),tc,.40);vec3 pt=texture(pathTex,(pathUvTransform*vec3(vUv,1)).xy).rgb;if(pathSrgb==1)pt=srgbToLinear(pt);pt*=vec3(.96,.91,.82);tc=mix(tc,pt,vPath);}color*=tc;}if(alpha<alphaTest)discard;
 vec3 result=color;
 if(basic==0){
 vec3 light=normalize(vec3(-19,34,8));vec3 view=normalize(eye-vWorld);vec3 halfDir=normalize(light+view);
 float nl=max(dot(n,light),0.),nv=max(dot(n,view),0.),nh=max(dot(n,halfDir),0.),vh=max(dot(view,halfDir),0.);
 vec3 sun=mix(srgbToLinear(vec3(1,.960784,.854902)),srgbToLinear(vec3(1,.803922,.505882)),.68*.26)*2.998;
 vec3 hemi=mix(srgbToLinear(vec3(.219608,.427451,.407843)),srgbToLinear(vec3(.905882,.949020,.831373)),dot(n,vec3(0,1,0))*.5+.5)*1.7;
 vec3 ambient=srgbToLinear(vec3(.850980,.905882,.764706))*.35;
 float sh=receiveShadow==1?shadow():1.;vec3 irradiance=(hemi+ambient+sun*nl*sh)/3.14159265;
 float a=max(.0525,roughness*roughness),a2=a*a;float den=nh*nh*(a2-1.)+1.;float D=a2/(3.14159265*den*den);
 float gv=nl*sqrt(a2+(1.-a2)*nv*nv),gl=nv*sqrt(a2+(1.-a2)*nl*nl);float V=.5/max(gv+gl,.00001);
 vec3 f0=mix(vec3(.04),color,metalness);vec3 F=f0+(1.-f0)*pow(1.-vh,5.);
 result=color*(1.-metalness)*irradiance+F*(D*V)*sun*nl*sh+emissive;
 }
 outColor=vec4(linearToSrgb(toneMapped==1?aces(result):result),alpha);
}
'''
prog=ctx.program(vertex_shader=VERT,fragment_shader=FRAG)
shadowprog=ctx.program(vertex_shader='''#version 330
in vec3 in_pos;in vec4 i0;in vec4 i1;in vec4 i2;in vec4 i3;uniform mat4 lightvp;void main(){gl_Position=lightvp*mat4(i0,i1,i2,i3)*vec4(in_pos,1);}
''',fragment_shader='''#version 330
void main(){}
''')
lightvp=ortho(-33,33,-33,33,1,90)@lookat([-19,34,8],[0,0,0]);matwrite(prog['lightvp'],lightvp);matwrite(shadowprog['lightvp'],lightvp)
textures=[]
for t in manifest['textures']:
 im=Image.open(DATA/t['file']).convert('RGBA')
 if t['flipY']:im=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 tex=ctx.texture(im.size,4,im.tobytes());tex.repeat_x=t.get('wrapS')==1000;tex.repeat_y=t.get('wrapT')==1000;tex.build_mipmaps();tex.filter=(gl.LINEAR_MIPMAP_LINEAR,gl.LINEAR);tex.anisotropy=8;textures.append(tex)
white=ctx.texture((1,1),3,bytes([255,255,255]))
geometry=[(ctx.buffer(raw(g['vertices'])),ctx.buffer(raw(g['indices'])),{name:(ctx.buffer(raw(a['data'])),a['itemSize']) for name,a in g.get('customAttributes',{}).items()}) for g in manifest['geometries']]
custom={}
# Each material gets its own program and exported uniform values. Preserve the
# actual vertex logic too; different shader materials may share varying names.
for mid,m in enumerate(manifest['materials']):
 if m['kind']!='shader':continue
 src=m['fragmentShader'].replace('varying ','in ').replace('texture2D(','texture(').replace('gl_FragColor','outColor').replace('#include <tonemapping_fragment>','outColor.rgb=aces(outColor.rgb);').replace('#include <colorspace_fragment>','outColor.rgb=linearToSrgb(outColor.rgb);')
 # Match Three.js color-space decoding for source texture samples.
 for key,value in m['uniforms'].items():
  if isinstance(value,dict) and 'texture' in value and manifest['textures'][value['texture']]['srgb']:
   src=re.sub(r'texture\('+re.escape(key)+r',([^;]*?)\)\.rgb',r'srgbToLinear(texture('+key+r',\1).rgb)',src)
 vertex=m['vertexShader'].replace('varying ','out ').replace('attribute ','in ')
 for old,new in [('projectionMatrix*modelViewMatrix','viewproj*mat4(i0,i1,i2,i3)'),('position','in_pos'),('uv','in_uv'),('normal','in_normal')]:
  vertex=re.sub(r'\b'+re.escape(old)+r'\b',new,vertex) if old.isidentifier() else vertex.replace(old,new)
 if '#include' in src or '#include' in vertex:raise ValueError('Unsupported shader chunk in '+m['objectName'])
 custom[mid]=ctx.program(vertex_shader='#version 330\nin vec3 in_pos;in vec2 in_uv;in vec3 in_normal;in vec4 i0;in vec4 i1;in vec4 i2;in vec4 i3;uniform mat4 viewproj;\n'+vertex,fragment_shader='#version 330\nout vec4 outColor;\n'+COLOR+src)
meshes=[]
for m in manifest['meshes']:
 vbo,ibo,extra=geometry[m['geometry']];instance=ctx.buffer(raw(m['instances']));mat=manifest['materials'][m['material']];p=custom.get(m['material'],prog)
 attrs=[('in_pos','3f',12),('in_normal','3f',12),('in_uv','2f',8),('in_color','3f',12),('in_path','1f',4)]
 fmt=' '.join(f if n in p else str(size)+'x' for n,f,size in attrs);names=[n for n,_,_ in attrs if n in p]
 ifmt='4f 4f 4f 4f '+('3f' if 'i_color' in p else '12x')+' /i';inames=['i0','i1','i2','i3']+(['i_color'] if 'i_color' in p else [])
 content=[(vbo,fmt,*names),(instance,ifmt,*inames)]+[(buf,str(size)+'f',name) for name,(buf,size) in extra.items() if name in p]
 vao=ctx.vertex_array(p,content,ibo,index_element_size=4)
 shadowvao=ctx.vertex_array(shadowprog,[(vbo,'3f 36x','in_pos'),(instance,'4f 4f 4f 4f 12x /i','i0','i1','i2','i3')],ibo,index_element_size=4)
 meshes.append((m,mat,p,vao,shadowvao))
shadowtex=ctx.depth_texture((4096,4096));shadowtex.compare_func='';shadowtex.filter=(gl.NEAREST,gl.NEAREST);shadowtex.repeat_x=shadowtex.repeat_y=False
shadowfb=ctx.framebuffer(depth_attachment=shadowtex);shadowfb.use();shadowfb.clear(depth=1);ctx.enable(gl.DEPTH_TEST);ctx.disable(gl.CULL_FACE)
for m,mat,p,vao,svao in meshes:
 if m['castShadow'] and m['primitive']=='triangles':svao.render(instances=m['count'])
print('Shadow pass complete',flush=True)
views={name:(v['target'],v['offset'],v['height']) for name,v in manifest['views'].items()}
views.update({'truck_detail':([13.7,3.5,-9.3],[-14,10,18],8.5),'stream_detail':([-13.4,1.7,-12.7],[12,17,20],13.5),'shore_detail':([6.6,.8,7.6],[6,13,18],10)})
w,h=args.width,args.height
color=ctx.renderbuffer((w,h),components=4,samples=4);depth=ctx.depth_renderbuffer((w,h),samples=4);fb=ctx.framebuffer(color,depth);out=ctx.simple_framebuffer((w,h),components=3)
for name in args.views.split(','):
 start=time.time();target,offset,height=views[name];eye=np.array(target)+offset;vp=ortho(-height*w/h/2,height*w/h/2,-height/2,height/2,.3,180)@lookat(eye,target)
 fb.use();fb.clear(144/255,182/255,160/255,1,depth=1);shadowtex.use(2)
 for program in [prog,*custom.values()]:matwrite(program['viewproj'],vp)
 prog['eye'].value=tuple(eye);prog['tex'].value=0;prog['pathTex'].value=1;prog['shadowTex'].value=2
 for m,mat,p,vao,_ in sorted(meshes,key=lambda a:(a[1]['transparent'],a[0]['renderOrder'],-np.linalg.norm(np.array(a[0]['center'])-eye) if a[1]['transparent'] else 0)):
  if mat['side']==2:ctx.disable(gl.CULL_FACE)
  else:ctx.enable(gl.CULL_FACE);ctx.cull_face='back' if mat['side']==0 else 'front'
  if mat['transparent']:
   ctx.enable(gl.BLEND);ctx.blend_func=(gl.SRC_ALPHA,gl.ONE) if mat.get('blending')==2 else (gl.ZERO,gl.ONE_MINUS_SRC_COLOR) if mat.get('blending')==3 else (gl.ZERO,gl.SRC_COLOR) if mat.get('blending')==4 else (gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA)
  else:ctx.disable(gl.BLEND)
  ctx.depth_mask=mat['depthWrite']
  if mat.get('depthTest',True):ctx.enable(gl.DEPTH_TEST)
  else:ctx.disable(gl.DEPTH_TEST)
  (textures[mat['map']] if mat['map']>=0 else white).use(0)
  (textures[mat['pathMap']] if mat['pathMap']>=0 else white).use(1)
  if p is prog:
   for key,val in {'baseColor':tuple(mat['color']),'emissive':tuple(mat['emissive']),'roughness':mat['roughness'],'metalness':mat['metalness'],'opacity':mat['opacity'],'alphaTest':mat['alphaTest'],'toneMapped':int(mat.get('toneMapped',True)),'vertexColors':int(mat['vertexColors']),'texSrgb':int(manifest['textures'][mat['map']]['srgb']) if mat['map']>=0 else 0,'pathSrgb':int(manifest['textures'][mat['pathMap']]['srgb']) if mat['pathMap']>=0 else 0,'hasTex':int(mat['map']>=0),'hasPath':int(mat['pathMap']>=0),'flatNormal':int(bool(mat.get('flatShading',False))),'doubleSide':int(mat['side']==2),'basic':int(mat['kind']=='basic'),'receiveShadow':int(m['receiveShadow'])}.items():p[key].value=val
  if p is prog:
   for key,tid in [('uvTransform',mat['map']),('pathUvTransform',mat['pathMap'])]:p[key].write(np.array(manifest['textures'][tid]['matrix'] if tid>=0 else [1,0,0,0,1,0,0,0,1],dtype='f4').tobytes())
  else:
   unit=0
   for key,value in mat['uniforms'].items():
    if key not in p:continue
    if isinstance(value,dict):textures[value['texture']].use(unit);p[key].value=unit;unit+=1
    else:p[key].value=tuple(value) if isinstance(value,list) else value
  if m['primitive']!='triangles':ctx.line_width=mat.get('linewidth',1)
  vao.render(mode={'triangles':gl.TRIANGLES,'lines':gl.LINES,'line_loop':gl.LINE_LOOP,'line_strip':gl.LINE_STRIP}[m['primitive']],instances=m['count'])
 ctx.depth_mask=True;ctx.copy_framebuffer(out,fb);im=Image.frombytes('RGB',(w,h),out.read(components=3,alignment=1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 path=OUTPUT/f'{name}.jpg';im.save(path,quality=94,subsampling=0);print(f'{path} ({time.time()-start:.2f}s)',flush=True)
report={'renderer':ctx.info['GL_RENDERER'],'glVersion':ctx.info['GL_VERSION'],'dimensions':[w,h],'samples':4,'shadowSize':4096,'views':args.views.split(','),'meshCount':len(meshes),'triangles':manifest['triangles'],'bounds':manifest['bounds'],'stats':manifest['stats'],'time':manifest.get('time',0),'sourceHashes':manifest['sourceHashes'],'omitted':manifest['omitted'],'rgbaTextures':len(textures),'shaderPrograms':len(custom)}
report_path=BASE/'qa/revision-02/render-presets.json' if OUTPUT==BASE/'dist/assets/previews' else OUTPUT/'render-report.json'
report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,indent=2))
