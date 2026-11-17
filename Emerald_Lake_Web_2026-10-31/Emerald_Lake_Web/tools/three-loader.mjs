import {pathToFileURL} from 'node:url';
import path from 'node:path';
const vendor=path.resolve(import.meta.dirname,'../dist/vendor');
export async function resolve(specifier,context,next){
 if(specifier==='three')return {url:pathToFileURL(path.join(vendor,'three.module.js')).href,shortCircuit:true};
 if(specifier.startsWith('three/addons/'))return {url:pathToFileURL(path.join(vendor,specifier.slice(13))).href,shortCircuit:true};
 return next(specifier,context);
}
