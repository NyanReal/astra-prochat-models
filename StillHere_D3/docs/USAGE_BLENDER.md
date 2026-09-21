# Blender 실행 안내

## 기본 실행

빈 Blender 파일을 열고 Scripting 작업 공간에서 `blender/build_scene.py`를 열어 Run Script를 실행합니다. 패키지 경로는 파일 위치에서 자동으로 찾습니다. Blender 4.5 계열의 API를 기준으로 작성했으며, 이 제작 환경에서는 Blender 자체 실행을 검증하지 못했습니다.

스크립트는 새로운 `StillHere_D3` Scene을 만들고, GLB를 종류별로 한 번 임포트합니다. `_AssetLibrary`에는 원본 오브젝트를 숨겨 보관하고, 실제 배치 오브젝트는 그 Mesh 데이터를 공유합니다. 카메라는 `SH_Camera_Reference`입니다. 기존 Scene은 삭제하지 않습니다.

기본 저장 파일은 `output/blender/StillHere_D3.blend`입니다. 같은 파일이 있으면 `_02`, `_03`처럼 새 이름으로 저장합니다. Blender의 현재 파일에 기존 Scene과 데이터가 있다면 그것도 저장 파일에 함께 남을 수 있으므로, 독립적인 결과물은 빈 파일에서 생성하는 편이 명확합니다.

## GLB 임포트에 문제가 있을 때

스크립트 상단의 `IMPORT_MODE='GLB'`를 `IMPORT_MODE='MESH_DATA'`로 바꾸면 동일한 수치 메시 배열과 외부 PNG를 사용합니다. Blender에 기본 포함된 NumPy를 사용하며, 별도의 glTF 임포트 애드온에 의존하지 않는 대체 경로입니다. 기본 GLB 모드에서는 임포트된 모델의 경계 크기를 원본 수치와 비교해, 축이나 단위가 어긋난 상태를 그대로 배치하지 않도록 했습니다.

## 렌더

기본은 장면 구성과 저장까지입니다. 렌더하려면 Blender에서 Render Image를 실행하거나, 터미널에서 패키지 폴더를 기준으로 아래 명령을 사용합니다.

```bash
blender --background --python blender/build_scene.py -- --render --engine cycles
```

Cycles는 기본 96 samples, CPU와 디노이즈를 사용하도록 설정했습니다. GPU 사용은 사용자 Blender 환경에서 별도로 선택하면 됩니다. Eevee 조립·렌더 경로는 다음과 같습니다.

```bash
blender --background --python blender/build_scene.py -- --render --engine eevee
```

결과 이미지는 `output/blender/reference_camera.png`입니다. 실행 버전, 오브젝트 수와 저장 경로는 같은 폴더의 `build_receipt.json`에 남깁니다. 이 실행 영수증은 사용자 Blender에서 스크립트가 실제로 끝났을 때 생성됩니다.

## 수정

지면, 바닥 이음매, 하천, 건축물, 나무, 관목과 소품이 Collection으로 분리됩니다. 인스턴스 하나의 메시를 편집하면 같은 Mesh를 공유하는 다른 배치에도 반영됩니다. 한 개만 별도로 수정할 때는 Blender에서 Single User로 분리한 후 편집하세요.

UV 아틀라스의 이미지 확장은 `Extend`이며 반복 타일링을 사용하지 않습니다. 물의 색상 UV는 고정하고, 월드 좌표 기반 잔물결 노멀만 움직입니다. 레퍼런스와 비교할 때는 자유 시점보다 제공 카메라를 먼저 사용하세요.
