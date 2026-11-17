#!/usr/bin/env python3
"""Package the portable website, project source, and verification reports."""
from pathlib import Path
import hashlib
import json
import zipfile

root=Path(__file__).resolve().parents[1]
output=root.parent/'exports'/'Emerald_Lake_Web_2026-10-31.zip'
output.parent.mkdir(parents=True,exist_ok=True)
selected=[]
for directory in ['dist','docs','tools']:
    selected.extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
selected.extend(root/name for name in ['README_KO.md','THIRD_PARTY_NOTICES.md','serve.py','START_WINDOWS.bat','START_MAC.command','package.json'])
for name in ['source-validation.json','browser-verification.md','offline-report.md','offline/render-report.json']:
    p=root/'qa'/name
    if p.exists():selected.append(p)
revision=root/'qa'/'revision-02'
if revision.exists():
    selected.extend(p for p in revision.iterdir() if p.is_file() and (
        p.name.endswith('-report.md') or p.name in {
            'truck_detail.jpg','stream_detail.jpg','shore_detail.jpg',
            'render-report.json','render-presets.json','verification.json'
        }
    ))
    selected.extend(p for p in (revision/'time-1').glob('*') if p.is_file() and p.suffix in {'.jpg','.json'})
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for p in sorted(set(selected)):
        archive.write(p,Path('Emerald_Lake_Web')/p.relative_to(root))
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    files=archive.namelist()
    for name in ['dist/index.html','dist/js/main.js','dist/assets/textures/material-atlas.png','dist/vendor/three.module.js','serve.py','README_KO.md']:
        assert 'Emerald_Lake_Web/'+name in files
    assert not any('/.git/' in n or '/.openai/' in n or '/node_modules/' in n for n in files)
summary={'file':str(output),'bytes':output.stat().st_size,'files':len(files),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'zip_integrity':'passed'}
(root/'qa'/'download-package.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
