// Build a convenience ZIP with the same bundled fflate implementation and verify
// every entry byte-for-byte. The webpage still builds its own ZIP in the browser.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(import.meta.url),{zipSync,unzipSync}=require('../vendor/fflate.min.js');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'))),files={};
for(const file of manifest.files){
  if(file.path.split('/').includes('..')||path.isAbsolute(file.path))throw Error('Path traversal');
  const bytes=fs.readFileSync(path.join(root,file.path));
  if(bytes.length!==file.bytes||createHash('sha256').update(bytes).digest('hex')!==file.sha256)throw Error('Manifest differs: '+file.path);
  files['atv/'+file.path]=bytes;
}
files['atv/manifest.json']=fs.readFileSync(path.join(root,'manifest.json'));
const zip=zipSync(files,{level:1}),decoded=unzipSync(zip);
for(const [name,bytes] of Object.entries(files))if(!Buffer.from(decoded[name]).equals(bytes))throw Error('ZIP data mismatch '+name);
fs.writeFileSync(path.join(root,'ATV-Trail-Asset-Kit.zip'),zip);
console.log(JSON.stringify({result:'PASS',files:Object.keys(decoded).length,bytes:zip.length,allPathsUnderATV:Object.keys(decoded).every(n=>n.startsWith('atv/')),roundTrip:'byte-for-byte'},null,2));
