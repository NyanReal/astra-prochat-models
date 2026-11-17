# 고구마 게임 에셋 — 아스트라 프로 재제작판

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
