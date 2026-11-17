# 해적 진영 기지 — 개별 GLB 에셋 팩

**66종 개별 GLB / 공용 1024×1024 텍스처 2장 / 블렌더 프리뷰 스크립트 / UE5 임포트·배치 스크립트**

두 장의 생성형 레퍼런스에 나온 건물·접안 시설·장비·소품을 게임용 정적 메시로 재구성했습니다. 단순 입방체 배치가 아니라 판재, 지붕 조각, 가새, 로프 결속, 통의 곡면, 대포 포구, 열린 상자와 통로 등을 실제 지오메트리로 구성했습니다. 이미지와 완전히 동일한 스컬프팅 결과가 아니라, 그 디자인을 일관된 모듈형 메시로 해석한 제작본입니다.

## 먼저 열어볼 파일

- `previews/harbor_front.jpg`: 실제 GLB 146개 인스턴스를 배치한 항구 전체 렌더.
- `previews/harbor_dock.jpg`: 접안 시설 확대 렌더.
- `previews/All_66_Assets.jpg`: 모든 모델의 실제 지오메트리 미리보기.
- `previews/01_Structures.jpg` ~ `05_Props_Nature.jpg`: 카테고리별 상세 시트.
- `previews/thumbnails/`: 모델별 640×640 렌더.
- `docs/asset_catalog.csv`: 파일명, 한국어 이름, 카테고리, 삼각형 수, 크기 등.

프리뷰는 생성형 이미지가 아니라 **내보낸 GLB를 다시 읽어 VTK로 렌더한 이미지**입니다. UE5 또는 Blender에서 촬영한 스크린샷은 아닙니다.

## 구성

| 구분 | 수량 | 주요 내용 |
|---|---:|---|
| 건물 | 6 | 망루, 지휘소, 대장간, 열린 보급 창고, 해적 텐트, 쉼터 |
| 방어 시설 | 7 | 목책, 목조·석조 성문 열린/닫힌 버전, 바리케이드, 대포 |
| 접안·하역 | 14 | 직선/코너/T/십자/막다른 부두, 플랫폼, 계단, 경사로, 계류주, 로프 난간, 부유 플랫폼, 크레인, 윈치, 소형 범선 |
| 저장·물자 | 10 | 크기별 통·상자, 마대, 채워진/빈 선반, 열린/닫힌 보물상자, 화물 그물 |
| 생활·작업 | 8 | 취사대, 모닥불, 솥, 생선 건조대, 무기 거치대, 테이블, 벤치, 모루 |
| 장식 소품 | 18 | 닻, 조타륜, 로프, 구명환, 랜턴, 횃불, 새장, 형틀, 쇠사슬, 과녁, 깃발·현수막, 뼈, 해골 |
| 자연물 | 3 | 바위 군집, 야자수, 풀 |
| **합계** | **66** | 기술용 기준 메시·프리뷰 지형은 이 수에 포함하지 않음 |

각 GLB는 **메시 1개 / 머티리얼 슬롯 1개 / 텍스처 내장**입니다. 따라서 필요한 GLB 파일 하나만 옮겨도 텍스처가 함께 따라갑니다. 편집 가능한 제작 소스도 `scripts/`에 포함했습니다.

전체 고유 에셋 합계는 **194,627 triangles / 159,463 vertices**입니다. 모든 모델을 동시에 배치한 게임의 성능을 보증하는 수치가 아닙니다. 항구 예시에는 55종을 146번 배치합니다.

## 블렌더에서 프리뷰 구성

대상은 **Blender 4.2 이상 API**입니다. Blender 안에 별도의 pip 패키지를 설치할 필요는 없습니다.

1. ZIP을 풀고 폴더 구조를 유지합니다.
2. Blender에서 새 파일을 열고, Scripting 작업공간의 Text Editor에서 `scripts/blender/build_preview.py`를 엽니다.
3. `Run Script`를 실행합니다. 경로를 자동으로 찾지 못하면 파일 상단의 `PACK_ROOT`를 압축 해제한 `pirate_outpost` 경로로 지정합니다.

기본값은 항구 배치인 `harbor`입니다. 모든 에셋을 격자로 확인하려면 상단 `DEFAULT_LAYOUT = "gallery"`로 바꿉니다.

스크립트는 **기존 오브젝트를 삭제하지 않고 새 씬**을 만듭니다. 66개의 원본 메시를 숨겨진 컬렉션에 두고, 보이는 배치는 그 메시 데이터를 공유합니다. 공용 머티리얼·텍스처, 카메라, 조명, 항구 프리뷰용 지형·수면을 구성합니다. 기존 `.blend`를 자동 저장하거나 덮어쓰지 않습니다.

명령줄에서 새 프리뷰 `.blend`와 렌더까지 생성하는 예시:

```bat
blender --background --python "D:/Assets/pirate_outpost/scripts/blender/build_preview.py" -- --pack "D:/Assets/pirate_outpost" --layout harbor --save "D:/Assets/PiratePreview.blend" --render "D:/Assets/PiratePreview.png"
```

기존 출력 파일을 교체할 때만 `--overwrite`를 추가합니다. `.blend` 저장은 현재 Blender 파일 전체를 저장하므로, 프리뷰만 저장하려면 새 Blender 파일에서 실행하십시오.

**이 팩에는 실행해서 생성한 `.blend`가 포함되어 있지 않습니다.** 여기에는 Blender 실행기가 없어 해당 에디터 내 실행은 검증하지 못했습니다.

## UE5에 임포트

스크립트는 **UE5.6 공식 Python/Interchange API를 기준으로 작성**했습니다. 다른 UE5 버전은 필요한 속성·기능을 검사하고, 맞지 않으면 오류를 남기도록 했습니다. 에디터에서의 버전별 작동 보증은 아닙니다.

프로젝트에서 Python Editor Script Plugin, Editor Scripting Utilities, Interchange Editor/Framework를 활성화하고 에디터를 재시작합니다. 먼저 테스트 프로젝트 또는 별도 Content 경로에서 사용하십시오.

`File > Execute Python Script`에서 아래 파일을 실행합니다.

```text
scripts/unreal/import_pirate_outpost.py
```

또는 Output Log의 **Cmd 모드**에서:

```text
py "D:/Assets/pirate_outpost/scripts/unreal/import_pirate_outpost.py"
```

기본 목적지는 `/Game/PirateOutpost`입니다. 바꾸려면 스크립트 상단 `DESTINATION`을 수정합니다. `PACK_ROOT`는 기본적으로 스크립트 위치에서 찾습니다.

임포트 스크립트가 수행하도록 구성한 작업:

- GLB를 카테고리별 Static Mesh로 임포트합니다. 모든 에셋을 하나로 합치지 않습니다.
- 기준 메시 `technical/SM_AxisProbe.glb`로 실제 임포터의 축 변환과 단위를 측정합니다.
- 메시가 실제 크기(cm)로 들어오도록 배율을 맞추고, 각 메시의 바운드·피벗을 원본과 비교합니다.
- BaseColor 및 RoughMetal 텍스처를 한 번 임포트하고 공용 머티리얼 `M_PirateAtlas`를 연결합니다.
- 자산별 충돌 정책을 적용합니다. 문·창고·망루처럼 빈 공간이 중요한 구조물은 단일 볼록 충돌체로 막지 않습니다.
- 처리 결과를 `reports/ue_import_report.json`에 기록합니다. 오류나 취소를 성공으로 보고하지 않습니다.

기본 `REIMPORT_OWNED = False`에서는 기존 에셋을 덮어쓰지 않습니다. 이 팩이 만든 소유 태그가 없는 동명 에셋은 수정하지 않고 중단합니다. 원본 GLB가 달라졌으면 명시적으로 `REIMPORT_OWNED = True`로 설정하거나 새 목적지에 임포트해야 합니다. 실패한 메시의 마무리 단계는 다음 실행에서 재시도하도록 구성했습니다.

> **UE 에디터 실행은 이 제작 환경에서 검증하지 못했습니다.** Python 문법·공용 좌표 계산 테스트를 통과한 스크립트이며, 실제 Interchange 임포트·머티리얼 컴파일·충돌 생성·레벨 배치는 사용 중인 UE 버전에서 확인해야 합니다. `ue_import_report.json`은 실제 UE 실행 시 만들어지며, 미리 생성한 가짜 성공 보고서는 포함하지 않았습니다.

### UE5에 예시 배치까지 올리기

임포트가 성공한 뒤 원하는 레벨을 열고 다음 스크립트를 실행합니다.

```text
scripts/unreal/place_pirate_outpost.py
```

기본은 항구 배치입니다. `LAYOUT = "gallery"`로 바꾸면 모델 목록용 격자 배치를 만듭니다. 기존 레벨을 비우지 않고, 같은 태그의 배치는 기본적으로 중복 생성하지 않습니다. 레벨을 자동 저장하지도 않습니다.

각 배치는 **동일 StaticMesh 자산을 재사용하는 개별 StaticMeshActor**입니다. ISM/HISM으로 일괄 묶는 GPU 인스턴싱 스크립트는 아닙니다. 플레이어 상호작용이나 최적화 정책에 따라 해당 프로젝트에서 분류하십시오.

프리뷰용 섬·수면은 UE 자동 임포트/배치 대상에서 제외했습니다. 기존 게임의 지형·물 시스템을 사용하거나 `previews/environment/`의 GLB를 별도로 임포트하십시오.

## 좌표·피벗·모듈 연결

제작 단위는 m, 제작 좌표는 X 오른쪽 / Y 뒤 / Z 위, 정면은 -Y입니다. GLB에는 표준 glTF Y-up 좌표로 기록되어 있습니다. Blender·Unreal 임포터가 좌표를 변환하므로 파일에 임의로 90도 회전을 추가하기 전에 기준 메시와 배치를 확인하십시오.

일반 소품은 바닥 중심을 기준으로 하고, 부두 타일은 **데크 상단 z=0**에 피벗을 둡니다. 부두의 다리는 음수 z로 내려갑니다. 배치 스크립트가 피벗을 중앙으로 다시 옮기지 않습니다.

| 모듈 | 제작 좌표 기준 연결 가능한 방향 | 규격 |
|---|---|---|
| Dock_Straight | +Y / -Y | 2×2m |
| Dock_Corner | +Y / +X | 2×2m |
| Dock_T | +Y / +X / -X | 2×2m |
| Dock_Cross | 네 방향 | 2×2m |
| Dock_End | +Y | 2×2m |
| Dock_Platform | 사방 확장 | 4×4m |
| Dock_Stairs | 위쪽 기준 (0,0,0), -Y 쪽으로 내려감 | 폭 약 1.6m / 수평 길이 2m |
| Gangway | -Y 쪽 낮음, +Y 쪽 높음 | 폭 약 1.6m / 길이 2m / 높이 차 약 0.28m |

타일은 2m 이동·90도 회전으로 연결합니다. 부두의 높이는 함께 맞춰야 합니다. 계단의 경사 설계 높이는 약 1m이며 마지막 계단 면과 아래 랜딩은 별도 높이 조정이 필요할 수 있습니다. 소켓 방향은 `asset_manifest.json`과 배치 JSON의 제작 좌표 기준입니다.

## 텍스처와 UV

`T_Pirate_BaseColor.png`와 `T_Pirate_RoughMetal.png`는 각각 **1024×1024**입니다. 모든 모델이 같은 아틀라스를 사용합니다. 각 GLB에는 독립 사용을 위해 복사본이 들어 있지만, 제공 에디터 스크립트는 공용 재질로 묶도록 작성했습니다.

- BaseColor: sRGB.
- RoughMetal: 비색상 데이터. **G=Roughness / B=Metallic / R=미사용(흰색)**. AO 맵이 아닙니다.
- Normal Map 없음. 판재 단차·로프·돌·주름의 큰 형태는 지오메트리로 표현합니다.

목재·천·금속·해적 문양은 **대화에서 이미 생성한 레퍼런스 이미지의 픽셀을 추출·보정**하여 사용했습니다. 새로 독립 생성한 타일 텍스처라고 주장하지 않습니다. 출처 이미지, 추출 영역, 원본 해시는 `textures/provenance.json`에 있습니다. Roughness/Metallic은 부위별 값을 작성한 데이터 맵입니다.

문양과 목재 결은 비교적 큰 아틀라스 영역을 사용하고, 단순 색상이나 중요도가 낮은 면은 작은 영역을 공유합니다. UV0는 **겹침을 허용한 재질 아틀라스 UV**입니다. 고유 베이크용 UV나 독립적인 0~1 텍스처 공간이 아닙니다.

정적 라이트맵을 구울 때는 별도 UV1이 필요합니다. UE 자동 Lightmap UV 생성은 선택 옵션일 뿐, 현재 겹친 UV0에서 항상 올바르게 분리된 UV1을 만든다고 보증하지 않습니다. 정적 베이크를 사용할 프로젝트는 DCC에서 UV1을 확인·작성하십시오.

## 충돌과 게임 적용 범위

`complex` 35종, `convex` 15종, `box` 3종, `none` 13종으로 정책을 지정했습니다. 실제 충돌 데이터는 UE 임포트 스크립트를 실행할 때 생성합니다. GLB 안에 UE 전용 UCX 메시를 넣은 구성은 아닙니다.

통로가 있는 건물과 구조물의 complex collision은 **정적 배치용**입니다. 이 설정 그대로 물리 시뮬레이션하는 보트·문·가구를 만들지 마십시오. 움직이는 물체에는 프로젝트에 맞는 별도의 단순 충돌과 액터 구성이 필요합니다.

본 팩은 정적 모델입니다. 열린/닫힌 성문과 상자는 별도 정적 변형이며, 경첩 리깅이나 애니메이션은 없습니다. 불꽃은 정적 메시, 랜턴 유리는 불투명 표현입니다. 바람에 흔들리는 천, Niagara 불, 실제 조명, 부력, 인벤토리/상호작용 기능은 포함하지 않습니다.

건물은 외관 중심이며 완성된 플레이용 실내 공간 팩이 아닙니다. 창고·텐트 등 일부 열린 공간은 표현했지만, 지휘소의 문을 열고 내부를 이동하는 시스템까지 제작한 것은 아닙니다.

## 실제 수행한 검증과 남은 확인

검증 보고서: `reports/validation.json`, `reports/independent_readback.json`, `reports/unit_tests.txt`, `reports/REVIEW_KO.md`.

여기서 실제 수행한 항목은 GLB 생성 및 재읽기, 66종 전체 유효 인덱스·유한 좌표·UV 범위·단위 법선·퇴화 삼각형·면 방향 검사, 텍스처 크기·노멀맵 부재 확인, 피벗·모델 목록·배치 참조 검사, 실제 GLB 렌더, Python 문법 및 공용 좌표 변환 테스트입니다. 별도 GLB 로더인 trimesh로도 66종을 재읽었습니다.

**하지 못한 검증:** Blender/UE5 에디터 안에서의 실행, 게임 빌드·플레이 테스트, 목표 기기 프레임 성능, 물리 동작, LOD 전환, Nanite 적용, 정적 라이트맵 베이크. 자동 LOD 체인은 포함하지 않았습니다. 출고용 최종 승인을 받은 게임 에셋 팩과 같은 의미로 해석하지 마십시오.

## 소스 재생성

이 부분은 모델을 수정해서 다시 만들 때만 필요합니다. 이미 들어 있는 GLB를 사용하는 데는 실행할 필요가 없습니다.

제작 소스에는 Python, NumPy, SciPy, Pillow, OpenCV가 필요합니다. 프리뷰 렌더는 추가로 VTK를 사용합니다. 자세한 환경 버전은 `reports/environment.json`에 기록했습니다.

```text
python scripts/make_atlas.py
python scripts/build_assets.py
python scripts/make_layout.py
python -m unittest discover -s tests -v
python scripts/validate_assets.py
python scripts/render_pack.py thumbnails
python scripts/render_pack.py sheets
python scripts/render_pack.py scene --angle front
python scripts/render_pack.py scene --angle dock
```

제작 소스는 자체 출력 파일을 다시 씁니다. 수정한 GLB·텍스처를 보존하려면 먼저 팩 폴더를 복사하십시오. 외부 3D 생성 서비스나 유료 API 호출은 사용하지 않았습니다. 공식 기술 문서와 적용한 GitHub 지침은 `docs/SOURCES.md`에 정리했습니다.
