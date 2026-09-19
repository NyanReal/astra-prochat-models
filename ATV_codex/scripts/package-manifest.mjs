// Enumerate deliverables only; never traverses outside atv or follows symlinks.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const files=[];
async function add(relative){
  const absolute=path.join(root,relative),stat=await fs.lstat(absolute);
  if(stat.isSymbolicLink())throw Error('Symlinks are not deliverables');
  if(stat.isDirectory()){for(const name of (await fs.readdir(absolute)).sort())await add(relative+'/'+name);return;}
  if(relative.endsWith('.blend1')||relative.includes('__pycache__')||relative.endsWith('.pyc'))return;
  const data=await fs.readFile(absolute);
  files.push({path:relative,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')});
}
for(const entry of ['index.html','style.css','app.js','start-preview.cmd','assets','docs','scripts','vendor'])await add(entry);
await fs.writeFile(path.join(root,'manifest.json'),JSON.stringify({scope:'atv only',generatedAt:new Date().toISOString(),files},null,2));
console.log(`${files.length} deliverables, ${(files.reduce((n,f)=>n+f.bytes,0)/1048576).toFixed(2)} MiB. manifest.json is also included by the browser.`);
