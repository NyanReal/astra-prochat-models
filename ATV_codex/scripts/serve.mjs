// Local static server restricted to the atv directory, using only Node built-ins.
import http from 'node:http';
import path from 'node:path';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.glb':'model/gltf-binary','.png':'image/png','.svg':'image/svg+xml','.txt':'text/plain; charset=utf-8'};
http.createServer(async(req,res)=>{
  try {
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    let target=path.resolve(root,'.'+pathname);
    if(target!==root&&!target.startsWith(root+path.sep)) throw Error('outside root');
    if((await fs.stat(target)).isDirectory())target=path.join(target,'index.html');
    const real=await fs.realpath(target);
    if(!real.startsWith(root+path.sep))throw Error('outside root');
    const body=await fs.readFile(real);
    res.writeHead(200,{'Content-Type':types[path.extname(real)]||'application/octet-stream','Cache-Control':'no-cache'});res.end(body);
  }catch{res.writeHead(404);res.end('Not found');}
}).listen(Number(process.env.PORT||4177),'127.0.0.1',()=>console.log('ATV preview: http://127.0.0.1:'+(process.env.PORT||4177)));
