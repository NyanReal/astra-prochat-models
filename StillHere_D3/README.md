# STILL HERE — D3
## 고정 시점용 모듈식 숲 · 폐시설 장면 / v1

첨부한 레퍼런스의 화면 구도를 기준으로 만든 개별 3D 에셋과 장면 조립 패키지입니다. 왼쪽 원형 시설과 보행 데크, 중앙 길과 여행자, 오른쪽 폭포·하천·교량 잔해·철탑을 공통 배치 데이터로 구성합니다.

**먼저 보기:** `previews/scene_camera.jpg`는 실제 메시와 배치 데이터를 VTK로 렌더한 결과입니다. 생성형 일러스트를 완성 렌더로 사용하지 않았습니다. `previews/asset_contact_sheet.jpg`에는 개별 메시의 실제 렌더가 있습니다.

> Blender와 Unreal Editor 실행 파일이 없는 환경에서 제작했습니다. GLB 독립 재임포트, 메시·UV·텍스처·좌표 변환·Python 구문은 검사했지만, 두 편집기 안에서 스크립트를 실행한 결과는 아직 검증하지 않았습니다. 이 ZIP에 실행했다고 가장한 `.blend` 또는 `.umap` 파일은 없습니다. 제공 스크립트가 사용자 환경에서 해당 파일을 생성합니다.

### 구성

- **장면용 GLB 69종 + 임포트 축 검증용 GLB 3종.** 장면에서는 65종을 재사용해 총 1,370개를 배치했습니다.
- **개별 GLB 안에 BaseColor / Normal / ORM 텍스처가 포함**되어 있으며, 같은 PNG를 외부 파일로도 제공합니다.
- **공통 `data/scene.json`**에 에셋 ID, 위치, 회전, 크기, 그룹과 카메라를 기록했습니다.
- **Blender 조립 스크립트**는 메시 데이터를 공유하는 오브젝트를 만들고 카메라·조명·재질을 구성합니다.
- **UE5 조립 스크립트**는 GLB 임포트, 축·단위 보정, 네이티브 머터리얼 생성, 공유 StaticMesh 배치, 새 레벨 저장을 수행하도록 작성했습니다.

### 바로 사용하기

**Blender**

압축을 모두 푼 뒤 Blender의 Scripting에서 `blender/build_scene.py`를 열고 실행합니다. 기본적으로 새 Scene에 구성하며, 기존 Scene의 오브젝트를 지우지 않습니다. 결과 저장 위치는 `output/blender/`입니다. 깔끔한 독립 파일을 얻으려면 빈 Blender 파일에서 시작하세요. 자세한 내용은 [Blender 실행 안내](docs/USAGE_BLENDER.md)에 있습니다.

**Unreal Engine**

Python Editor Script Plugin, Editor Scripting Utilities와 glTF/Interchange 임포트 기능을 준비하고, 현재 레벨을 먼저 한 번 저장합니다. 편집기의 Python Script 실행 메뉴에서 `ue5/build_level.py`를 선택합니다. 확인 대화상자 이후 별도의 `/Game/StillHere_D3/Maps/` 레벨을 생성하도록 구성했습니다. 기존 액터를 삭제하거나 기존 맵을 덮어쓰지 않습니다. 자세한 내용은 [UE5 실행 안내](docs/USAGE_UE5.md)에 있습니다.

### 바닥과 UV

바닥은 하나의 배경판이 아닙니다. 지면 조각, 흙길, 부서진 포장, 경계용 이끼, 낮은 강둑 받침, 강변 바위와 식생을 겹쳐 배치했습니다. 특히 `Ground/SeamTransitions`, `Ground/BankUnderlap`, `Ground/BankStitchMoss` 그룹에서 연결 오브젝트를 확인할 수 있습니다.

UV는 원본 에셋 내부에서 겹치지 않게 배치했습니다. 연속된 면은 한 차트 안에서 이어지고, 서로 다른 면이 같은 UV 면적을 공유하지 않습니다. 동일한 모델을 여러 곳에 재배치할 때는 같은 메시와 UV·텍스처를 재사용합니다. 3픽셀 여백을 포함한 차트 배치와 실제 UV 삼각형 겹침을 검사했습니다.

생성형 재질 시트와 생성된 물 이미지에서 표면 정보를 가져와 톤과 크기를 조정하고, 고유 UV 아틀라스로 베이크했습니다. Normal·Roughness·Metallic 값은 표현을 위한 추정값입니다. 원본 물체를 측정한 PBR 스캔 데이터가 아닙니다. 설명과 예시는 [UV·텍스처 안내](docs/UV_AND_TEXTURES.md)를 참고하세요.

### 밀도와 범위

고정 카메라는 1536 × 1024 비율의 직교 시점이며, 가로 범위는 36 m로 설정했습니다. 원본 이미지의 실제 렌즈·카메라 값은 제공되지 않아 화면 배치를 기준으로 맞춘 값입니다. 보이지 않는 면과 카메라 밖 영역은 재구성하거나 단순화했습니다.

원본 에셋을 모두 합하면 **70,833 triangles**, 배치 횟수를 반영한 장면은 **670,308 triangles**입니다. 뒤에 가려진 면과 카메라 밖 면까지 포함한 수치이며, GPU 성능 측정 결과는 아닙니다. 자세한 수치는 [에셋 목록](docs/ASSET_CATALOG.md)에 기록했습니다.

물은 스타일화한 불투명 수면, 별도 폭포와 물거품 메시로 구성했습니다. Blender와 UE 머터리얼에는 시간에 따라 변하는 잔물결 노멀을 추가했습니다. 유체 시뮬레이션, 이동 가능한 캐릭터, 애니메이션 리그, 내비게이션과 게임플레이용 콜리전 검수는 포함하지 않습니다.

### 폴더

```text
assets/glb/              개별 모델 + 내장 텍스처
assets/textures/         외부 BaseColor / Normal / ORM PNG
blender/                Blender 장면 조립과 재질 스크립트
ue5/                    UE5 레벨 조립·재질·좌표 변환·API 점검
data/scene.json         전체 배치 및 카메라 정보
data/assets.json        에셋 ID → GLB/텍스처 경로, UV·메시 통계
data/meshes/             독립 검증 및 Blender 대체 로더용 배열
data/uv/                 UV 차트 영역과 표면 정보
source/                 레퍼런스와 생성형 재질 원본·고정 가공본
previews/               실제 장면 / 개별 모델 / UV 배치 예시
generation/             에셋·배치 재생성, 렌더, 검증 코드
tests/                  좌표·UV·변환·구문 테스트
validation/             검사 결과, 수치, 파일 체크섬
```

Blender와 UE5 스크립트는 폴더 구조를 기준으로 경로를 찾으므로 **GLB나 스크립트만 따로 빼지 말고 전체 ZIP을 풀어 사용**하세요.

검증한 범위와 미검증 범위는 [검증 내역](docs/VALIDATION.md), 원시 데이터 재생성은 [재생성 안내](docs/REGENERATION.md), 참조한 공식 API 문서는 [문서 출처](docs/SOURCES.md)에 있습니다.
