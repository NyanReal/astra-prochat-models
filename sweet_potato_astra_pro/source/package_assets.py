"""Create the comparison image, documentation, provenance manifest and final ZIP."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json, hashlib, zipfile, importlib.metadata, subprocess
ROOT=Path(__file__).resolve().parents[1]
METRICS=json.loads((ROOT/'validation'/'asset_metrics.json').read_text())
def font(size,bold=False):
    file='/usr/share/fonts/opentype/noto/NotoSansCJK-'+('Bold' if bold else 'Regular')+'.ttc'
    return ImageFont.truetype(file,size)

def comparison():
    bg=(247,243,233);canvas=Image.new('RGB',(2000,1030),bg);d=ImageDraw.Draw(canvas)
    d.text((65,35),'고구마 게임 에셋 · 아스트라 프로',font=font(42,True),fill=(45,61,37))
    d.text((67,100),'새로 제작한 GLB를 다시 불러와 렌더링한 결과입니다.',font=font(23),fill=(110,113,98))
    for i,(name,title,desc) in enumerate([
        ('wild_sweet_potato','01  야생 고구마','불규칙한 두 포기 · 기는 덩굴 · 드러난 흙'),
        ('cultivated_sweet_potato','02  관리된 고구마 밭','3개 두둑 × 4포기 · 규칙적인 식재 간격')]):
        x=45+i*990
        d.rounded_rectangle((x,160,x+955,967),radius=24,fill=(251,249,243),outline=(223,223,207),width=2)
        render=Image.open(ROOT/'preview'/f'{name}_hero.png').convert('RGB')
        # Crop only empty studio background; never change model shape or appearance.
        box=(70,190,1320,900) if i else (100,270,1290,885)
        render=render.crop(box);render.thumbnail((925,620),Image.Resampling.LANCZOS)
        canvas.paste(render,(x+(955-render.width)//2,215+(620-render.height)//2))
        d.text((x+30,805),title,font=font(32,True),fill=(50,68,42))
        d.text((x+30,855),desc,font=font(22),fill=(91,102,79))
        main=METRICS[name]['triangles'];lod=METRICS[name+'_LOD1']['triangles']
        d.text((x+30,906),f'{main:,} triangles  /  LOD1 {lod:,}  /  GLB',font=font(20),fill=(113,118,103))
    canvas.save(ROOT/'preview'/'models_comparison.png')

def docs():
    ko='''# 고구마 게임 에셋 — 아스트라 프로 재제작판

[English](README.md)

이번 요청에서 레퍼런스 이미지를 새로 생성하고, 메시와 UV를 새 코드로 만들었습니다. 이전 에셋 팩의 GLB·텍스처·모델링 스크립트는 재사용하지 않았습니다.

## 파일

| 모델 | 기본형 삼각형 | LOD1 삼각형 | 기본형 크기 (가로 × 높이 × 깊이) |
|---|---:|---:|---|
| `wild_sweet_potato.glb` | 6,368 | 2,258 | 약 2.18 × 0.53 × 1.79 m |
| `cultivated_sweet_potato.glb` | 22,868 | 7,600 | 약 3.16 × 0.74 × 3.66 m |

야생형은 두 포기와 다섯 개의 기는 덩굴, 36장의 고구마 잎을 사용합니다. 흙이 드러나는 공간과 적은 잡초·돌로 자연스러운 불규칙성을 표현했습니다. 밭형은 3개 두둑에 4포기씩, 총 12포기이며 고구마 잎은 168장입니다. LOD1은 각각 별도 GLB이며 자동 전환 규칙은 포함하지 않습니다.

## 재질과 UV

- `foliage_basecolor_1024.png`: 잎 전용 1024×1024 아틀라스. 새로 생성한 이미지의 잎 한 장을 추출해 네 가지 색상으로 정리했습니다. 같은 잎 UV 영역을 반복 사용합니다.
- `soil_basecolor_256.png`: 256×256 흙 텍스처. 넓은 면적이지만 중요도가 낮아 작은 반복 텍스처를 사용했습니다.
- `stem_basecolor_128.png`, `stone_basecolor_128.png`: 저밀도 줄기·돌 텍스처.

텍스처는 새 이미지 생성 결과에서 잎·흙을 크롭하고, 가장자리 색 확장·리샘플링·색상 조정을 거쳐 제작했습니다. 최종 아틀라스가 1024인 것이며, 각 잎 원본이 네이티브 1024 해상도로 생성된 것은 아닙니다. 원본 크롭과 처리 좌표는 `reference/generated_leaf_source.png`, `source/texture_provenance.json`에 있습니다.

추가 PBR 정보는 roughness 상수(0.91~1.0)와 metallic=0뿐입니다. Normal map, 별도 AO map, 투명도 맵은 없습니다. 잎은 윤곽을 실제 메시로 만들었고 양면 렌더링을 지정했습니다. 따라서 사각 알파 카드의 투명도 정렬에 의존하지 않습니다.

## 사용

`models/`의 GLB를 가져오면 텍스처가 내장되어 있습니다. 1단위=1m, Y-up, 지면 중앙 원점입니다. `soil`, `foliage`, `stems`, `stone` 노드가 분리되어 있으며 밭형에는 `stone`이 없습니다. 식물만 쓰려면 임포트 후 soil 노드를 숨기거나 제거할 수 있습니다.

리깅, 바람 애니메이션, 충돌체, 엔진별 프리팹은 포함하지 않습니다. 모든 재질은 불투명이며 잎에만 doubleSided를 지정했습니다. 사용하는 엔진의 가져오기 기능이 양면 설정을 유지하는지 확인하세요.

## 미리보기

`preview/models_comparison.png`는 실제 GLB 두 개의 비교 렌더입니다. `*_hero.png`, `*_top.png`, `*_side.png`, `*_wire.png` 역시 내보낸 GLB를 다시 불러와 렌더링했습니다. `reference/`의 이미지는 생성된 디자인 참고 이미지이므로 실제 메시 렌더와 구분해 보세요. 렌더링의 조명과 화면 공간 음영은 미리보기 전용이며 재질에 굽지 않았습니다.

## 재생성 및 검사

```bash
python source/prepare_textures.py
python source/build_assets.py
python validation/test_assets.py
python source/render_previews.py
```

Python 패키지: numpy, Pillow, scipy, opencv-python, trimesh. 미리보기 렌더링에는 vtk가 추가로 필요합니다. 생성 코드의 난수 시드는 고정되어 있습니다. 배포 ZIP을 다시 만들려면 `package_assets.py`도 실행할 수 있으며, 비교 이미지의 한국어 글꼴은 실행 환경의 Noto Sans CJK 설치를 사용합니다. 글꼴 파일은 제공하지 않습니다.

자동 검사는 GLB 구조, 좌표·UV·노멀의 유효성, 삼각형 퇴화 여부, 내장 텍스처, 크기 제한, 재질 구성, LOD 삼각형 수를 확인합니다. 검사 결과는 `validation/`에 있습니다. Blender·Unity·Unreal의 실제 편집기 안에서의 임포트 테스트나 Khronos 공식 validator 실행은 하지 않았습니다.

## 적용한 제작 기준

사용자가 지정한 `octopus7/model-workflow`의 reference-image-generation 및 reference-image-modeling 지침을 확인했습니다. 둥글고 자연스러운 단순화, 기능과 무관한 장식 생략, 묘사 중요도별 UV 배분, 이미지 생성 기반 텍스처, 최대 1024, Normal map 생략, GLB/ZIP 납품 기준을 적용했습니다.

원본 지침: https://github.com/octopus7/model-workflow
'''
    en='''# Sweet Potato Game Assets — Astra Pro Rebuild

[한국어](README.ko.md)

A fresh rebuild of two stylized game props: a sparse wild sweet-potato patch and a cultivated three-row plot. New reference images, new image-derived textures, and new mesh-generation code; no meshes, textures, or scripts were reused from the earlier delivered pack.

| Model | Main triangles | LOD1 triangles | Dimensions (X × Y × Z, meters) |
|---|---:|---:|---|
| Wild patch | 6,368 | 2,258 | 2.18 × 0.53 × 1.79 |
| Cultivated field | 22,868 | 7,600 | 3.16 × 0.74 × 3.66 |

## Contents

`models/`: two main GLBs and two separate LOD1 GLBs. `textures/`: all base-color maps. `reference/`: newly generated visual references and the cropped leaf source. `preview/`: renders made by reimporting the actual GLBs. `source/`: geometry and texture preparation scripts. `validation/`: measured statistics and automated tests.

The wild patch has two uneven crowns, five creeping runners and 36 sweet-potato leaves. The field has three raised beds, four crowns per bed, and 168 leaves. LOD switching logic is not included.

## Materials and coordinates

Meters, Y-up, origin at ground center. Textures are embedded. Mesh nodes are grouped by material: soil, foliage, stems, and stone (wild only). Remove the soil node when only vegetation is desired.

Foliage gets a 1024×1024 atlas. Soil is 256×256; stems and stone are 128×128. The leaf atlas contains recolored variants of one freshly generated leaf crop with nearest-color edge dilation. These are image-derived, resampled textures, not four independently generated native-1024 leaves. Source crop coordinates and processing are recorded in `source/texture_provenance.json`.

Only base color and scalar roughness/metallic are used. Metallic is zero, roughness ranges from 0.91 to 1.0. No normal map, AO map or alpha card. Leaf silhouettes are actual curved geometry with double-sided opaque materials.

No rig, wind animation, collider, or engine prefab is included. Confirm that your importer preserves the double-sided setting on foliage. Previews use studio lighting and screen-space ambient shading, which are not baked into the GLBs.

## Rebuild

```bash
python source/prepare_textures.py
python source/build_assets.py
python validation/test_assets.py
python source/render_previews.py
```

Python dependencies: numpy, Pillow, scipy, opencv-python, trimesh; vtk for rendering. Seeds are fixed. `source/package_assets.py` additionally uses a locally installed Noto Sans CJK font for the Korean comparison card; font files are not distributed.

Automated checks cover coordinates, normals, UVs, degenerate triangles, embedded textures, size ceiling, material properties and LOD reduction. Files were reimported and rendered. No Blender/Unity/Unreal editor import test or official Khronos validator run is claimed.

## Guidelines

User-specified source: https://github.com/octopus7/model-workflow

The reference-image-generation and reference-image-modeling guidelines were checked for this rebuild: soft natural forms, no unrelated decorative motifs, importance-weighted UV allocation, generated-image textures, a 1024-pixel ceiling, no normal maps, and GLB/ZIP delivery.
'''
    (ROOT/'README.md').write_text(en,encoding='utf-8');(ROOT/'README.ko.md').write_text(ko,encoding='utf-8')
    packages={}
    for p in ['numpy','Pillow','scipy','opencv-python','trimesh','vtk']:
        try:packages[p]=importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:packages[p]='available module; distribution name differs'
    (ROOT/'source'/'requirements_environment.json').write_text(json.dumps(packages,indent=2))

def package():
    comparison();docs()
    checks={}
    for p in ROOT.rglob('*'):
        if p.is_file() and not any(x in p.parts for x in ['__pycache__','docs']):
            if p.name not in ['file_manifest.json','initial_tests.txt','render_log.txt']:
                checks[str(p.relative_to(ROOT))]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    (ROOT/'validation'/'file_manifest.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=ROOT.parent/'sweet_potato_wild_and_field_아스트라 프로.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in ROOT.rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ['__pycache__','docs']) and p.name not in ['initial_tests.txt','render_log.txt']:
                z.write(p,Path('sweet_potato_astra_pro')/p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        print('ZIP entries',len(z.namelist()))
    print(str(archive));print('ZIP size',archive.stat().st_size)
if __name__=='__main__':package()
