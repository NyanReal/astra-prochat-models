# 원본 에셋과 배치 재생성

아래 과정은 Blender/UE 조립에 필수가 아닙니다. 제공된 GLB를 그대로 사용하면 됩니다. 형상 생성 코드와 배치를 수정하려는 경우에만 일반 Python 환경에서 실행하세요. Python 3.10 이상 문법을 사용합니다.

## 모델과 아틀라스

패키지 루트에서:

```bash
python -m pip install -r requirements-generation.txt
python generation/build_assets.py
```

GLB, 외부 PNG, 검증용 메시 배열과 UV 차트 정보를 다시 만듭니다. 개별 모델만 재생성할 수도 있습니다.

```bash
python generation/build_assets.py --only Truck_Abandoned Broadleaf_A
```

기본적으로 `source/processed_surfaces/`의 고정 가공본을 읽습니다. 원시 생성 이미지부터 톤·글자 처리를 다시 수행하려면 `STILLHERE_REPROCESS_SOURCE=1` 환경 변수를 사용합니다. 이 추가 경로는 코드에 명시된 로컬 글꼴 경로가 필요하므로, 다른 OS에서는 글꼴 경로를 수정해야 할 수 있습니다. 글꼴 파일은 배포하지 않습니다.

생성 결과를 덮어쓰는 작업이므로, 수동 수정한 GLB와 PNG는 먼저 별도로 보관하세요. Blender와 UE 조립 스크립트는 기존 맵을 보존하지만, 이 원본 재생성 명령은 패키지의 해당 산출물을 갱신합니다.

## 배치만 재생성

```bash
python generation/build_scene.py
```

원본 메시를 변경하지 않고 `data/scene.json`과 `data/camera.json`을 만듭니다. 고정 시드를 사용하며 같은 Python 프로세스에서 반복 실행해도 같은 배치가 나오도록 검사했습니다.

개별 오브젝트의 ID와 좌표를 직접 수정할 때는 `data/scene.json`을 편집할 수도 있습니다. `asset_id`는 `data/assets.json`에 존재해야 합니다. 좌표 단위는 미터이며 Z가 높이입니다. 회전은 XYZ Euler degrees와 XYZW quaternion을 함께 기록합니다. 직접 회전을 수정할 때는 두 표현을 일치시켜야 Blender와 UE 결과가 같습니다.

## 실제 메시 미리보기

```bash
python -m pip install -r requirements-preview.txt
python generation/render_preview.py --width 1536 --output previews/scene_camera.png
python generation/make_previews.py
```

VTK/OpenGL 오프스크린 렌더 경로입니다. 실행 환경에 맞는 OpenGL 지원이 필요합니다. Blender나 Unreal의 렌더 결과는 아닙니다. 동봉한 최종 미리보기는 이 경로로 실제 생성했습니다.

## 검증

```bash
python -m pip install -r requirements-validation.txt
python -m pytest -q
python generation/validate_package.py
```

UV 중복 검사는 Shapely로 실제 UV 삼각형의 합집합 면적을 구해 수행합니다. GLB는 자체 디코더와 별도의 trimesh 로더 양쪽에서 확인합니다. 이 검증은 Blender/UE 편집기 실행을 대신하지 않습니다.
