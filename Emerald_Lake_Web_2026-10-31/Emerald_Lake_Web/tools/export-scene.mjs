import * as THREE from '../dist/vendor/three.module.js';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {createCanvas,loadImage}=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES ? require(path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES,'@napi-rs/canvas')) : require('@napi-rs/canvas');
const arg=(name,fallback)=>{const i=process.argv.indexOf(name);return i<0?fallback:process.argv[i+1];};
const sceneTime=Number(arg('--time',0));
if(!Number.isFinite(sceneTime))throw Error('--time must be finite');
globalThis.document={createElement:(name)=>{if(name!=='canvas')throw Error(name);return createCanvas(1,1);}};
const {createTerrain}=await import('../dist/js/terrain.js');
const {createProps}=await import('../dist/js/props.js');
const {createVegetation}=await import('../dist/js/vegetation.js');
const {createLife}=await import('../dist/js/life.js');
const out=path.resolve(import.meta.dirname,arg('--output','../qa/offline/scene-data'));fs.mkdirSync(out,{recursive:true});
const atlas=await loadImage(path.resolve(import.meta.dirname,'../dist/assets/textures/material-atlas.png'));
const textures={};for(const [i,name] of ['ground','wood','stone','grass','metal','waterbed'].entries()){
 const c=createCanvas(512,512);c.getContext('2d').drawImage(atlas,i%3*512,Math.floor(i/3)*512,512,512,0,0,512,512);
 const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;textures[name]=t;
}
const scene=new THREE.Scene(),stats={};
for(const make of [createTerrain,createProps,createVegetation,createLife]){const part=make({textures,quality:'high'});part.update?.(sceneTime,0);scene.add(part.group);Object.assign(stats,part.stats);}
scene.updateMatrixWorld(true);
let chunks=[],offset=0;const add=(typed)=>{for(const v of typed)if(!Number.isFinite(v))throw Error('Nonfinite geometry or matrix value');const b=Buffer.from(typed.buffer,typed.byteOffset,typed.byteLength);const ref={offset,length:typed.length,type:typed instanceof Uint32Array?'u32':'f32'};chunks.push(b);offset+=b.length;return ref;};
const textureIds=new Map(),materialIds=new Map(),geometryIds=new Map(),manifest={materials:[],textures:[],geometries:[],meshes:[],stats,omitted:[],time:sceneTime};
function texture(t){
 if(!t)return -1;if(textureIds.has(t))return textureIds.get(t);const id=manifest.textures.length;textureIds.set(t,id);const file=`texture-${id}.png`;
 let image=t.image;if(!image?.toBuffer){const c=createCanvas(image.width,image.height);c.getContext('2d').drawImage(image,0,0);image=c;}
 fs.writeFileSync(path.join(out,file),image.toBuffer('image/png'));if(t.matrixAutoUpdate)t.updateMatrix();
 manifest.textures.push({file,flipY:t.flipY,srgb:t.colorSpace===THREE.SRGBColorSpace,repeat:t.repeat.toArray(),offset:t.offset.toArray(),center:t.center.toArray(),rotation:t.rotation,matrix:t.matrix.toArray(),wrapS:t.wrapS,wrapT:t.wrapT});return id;
}
function material(m,name){
 if(Array.isArray(m))throw Error('Multi-material geometry requires explicit group export: '+name);
 if(materialIds.has(m))return materialIds.get(m);const id=manifest.materials.length;materialIds.set(m,id);
 const kind=m.isShaderMaterial?'shader':m.isMeshBasicMaterial||m.isLineBasicMaterial?'basic':'standard';
 const uniforms={};for(const [key,u]of Object.entries(m.uniforms||{})){const v=u.value;uniforms[key]=v?.isTexture?{texture:texture(v)}:typeof v==='number'||typeof v==='boolean'?v:v?.toArray?v.toArray():Array.isArray(v)?v:null;if(uniforms[key]===null)throw Error('Unsupported shader uniform '+key);}
 const data={name:m.name,objectName:name,type:m.type,kind,shaderKind:m.userData?.kind,shaderDigest:m.isShaderMaterial?createHash('sha256').update(m.vertexShader+'\n'+m.fragmentShader).digest('hex'):null,uniforms,color:m.color?.toArray()||[1,1,1],emissive:m.emissive?.toArray().map(x=>x*(m.emissiveIntensity??1))||[0,0,0],map:texture(m.map),pathMap:name==='sculpted shore and paths'?texture(textures.ground):-1,roughness:m.roughness??1,metalness:m.metalness??0,opacity:m.opacity,alphaTest:m.alphaTest||0,transparent:m.transparent,blending:m.blending,side:m.side,vertexColors:m.vertexColors,flatShading:m.flatShading,depthWrite:m.depthWrite,depthTest:m.depthTest,toneMapped:m.toneMapped,linewidth:m.linewidth||1,vertexShader:m.vertexShader,fragmentShader:m.fragmentShader};
 if(name==='sculpted shore and paths'){const shader={uniforms:{},vertexShader:'#include <common>\n#include <begin_vertex>',fragmentShader:'#include <common>\n#include <map_fragment>'};m.onBeforeCompile(shader);data.compiledMapFragment=shader.fragmentShader.split('varying float vPathWeight;')[1].trim();}manifest.materials.push(data);return id;
}
function geometry(g,isLine){if(geometryIds.has(g))return geometryIds.get(g);const id=manifest.geometries.length;geometryIds.set(g,id);if(!g.attributes.normal&&!isLine)g.computeVertexNormals();const pos=g.attributes.position,norm=g.attributes.normal,uv=g.attributes.uv,col=g.attributes.color,pw=g.attributes.pathWeight;const a=new Float32Array(pos.count*12);for(let i=0;i<pos.count;i++){a.set([pos.getX(i),pos.getY(i),pos.getZ(i),norm?.getX(i)||0,norm?.getY(i)??1,norm?.getZ(i)||0,uv?.getX(i)||0,uv?.getY(i)||0,col?.getX(i)??1,col?.getY(i)??1,col?.getZ(i)??1,pw?.getX(i)||0],i*12);}const index=new Uint32Array(g.index?g.index.array:Array.from({length:pos.count},(_,i)=>i));const customAttributes={};for(const [name,attr] of Object.entries(g.attributes)){if(['position','normal','uv','color','pathWeight'].includes(name))continue;if(attr.itemSize>4||attr.normalized||attr.isInterleavedBufferAttribute)throw Error('Unsupported custom attribute '+name);customAttributes[name]={itemSize:attr.itemSize,data:add(new Float32Array(attr.array))};}manifest.geometries.push({vertices:add(a),indices:add(index),count:index.length,customAttributes});return id;}
scene.traverse(o=>{if(!o.visible)return;if(!o.isMesh&&!o.isLine){if(o.isPoints)manifest.omitted.push({name:o.name,type:o.type});return;}let visible=true;o.traverseAncestors(a=>{visible&&=a.visible});if(!visible)return;const n=o.isInstancedMesh?o.count:1,transforms=new Float32Array(n*19),im=new THREE.Matrix4(),wm=new THREE.Matrix4();for(let i=0;i<n;i++){if(o.isInstancedMesh){o.getMatrixAt(i,im);wm.multiplyMatrices(o.matrixWorld,im);}else wm.copy(o.matrixWorld);transforms.set(wm.elements,i*19);transforms.set(o.instanceColor?Array.from(o.instanceColor.array.slice(i*3,i*3+3)):[1,1,1],i*19+16);}manifest.meshes.push({name:o.name,geometry:geometry(o.geometry,o.isLine),material:material(o.material,o.name),instances:add(transforms),count:n,primitive:o.isLineSegments?'lines':o.isLineLoop?'line_loop':o.isLine?'line_strip':'triangles',renderOrder:o.renderOrder,center:new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3()).toArray(),castShadow:o.castShadow,receiveShadow:o.receiveShadow});});
const mainSource=fs.readFileSync(path.resolve(import.meta.dirname,'../dist/js/main.js'),'utf8');
const viewLiteral=mainSource.match(/const views\s*=\s*(\{[\s\S]*?\n\});/)[1];manifest.views=Function('return ('+viewLiteral+')')();
const jsDir=path.resolve(import.meta.dirname,'../dist/js');manifest.sourceHashes=Object.fromEntries(fs.readdirSync(jsDir).filter(n=>n.endsWith('.js')).sort().map(name=>[name,createHash('sha256').update(fs.readFileSync(path.join(jsDir,name))).digest('hex')]));
const bounds=new THREE.Box3().setFromObject(scene);manifest.bounds={min:bounds.min.toArray(),max:bounds.max.toArray()};manifest.triangles=manifest.meshes.filter(m=>m.primitive==='triangles').reduce((n,m)=>n+manifest.geometries[m.geometry].count/3*m.count,0);manifest.generatedAt=new Date().toISOString();manifest.source=`Actual createTerrain/createProps/createVegetation/createLife constructors; deterministic time ${sceneTime}`;
fs.writeFileSync(path.join(out,'scene.bin'),Buffer.concat(chunks));fs.writeFileSync(path.join(out,'scene.json'),JSON.stringify(manifest,null,2));console.log(JSON.stringify({stats,bounds:manifest.bounds,meshes:manifest.meshes.length,triangles:manifest.triangles,bytes:offset,omitted:manifest.omitted},null,2));
