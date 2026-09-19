# ATV Stylized — GLB / Blender / Unreal Engine 5.7

[English](README.en.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

첨부된 앞·뒤 3/4 참고 이미지를 바탕으로 재구성한 탑다운 게임용 ATV.
스캔이나 CAD 복제가 아니라, 큰 차체·펜더·타이어·랙 실루엣을 중심으로 만든 저폴리 모델이다.

## 바로 사용할 파일

**`Model/SM_ATV_Stylized.glb`**

메시와 베이스컬러·ORM·발광 텍스처가 GLB 안에 들어 있다. 외부 PNG를 따로 찾지 않아도 열린다.
`Textures/`의 PNG는 재질 수정과 UE 임포트에 쓰는 동일한 외부 사본이다.

| 항목 | 납품 데이터 |
|---|---|
| 렌더링 삼각형 | **8,976** — 10,000 미만 |
| 메시 / 머터리얼 / 프리미티브 | 1 / 1 / 1 |
| UV·노멀 경계 분리 포함 정점 | 10,260 |
| UV 채널 | UV0 1개, 전체 0–1 범위 |
| UV 아틀라스 배치 그룹 | 274개 |
| UV 삼각형 면적 겹침 | **0쌍** — 부동소수점 허용오차 1e-11 UV² |
| UV 실제 삼각형 면적 점유율 | 약 60.13% |
| PBR 맵 | 각각 2048 × 2048 PNG |
| 크기 | 길이 약 2.706 m × 폭 1.840 m × 높이 1.837 m |
| 기준축 | 원본/Blender: +X 전방, +Z 위 / GLB: +X 전방, +Y 위 |
| 원점 | 차체 중앙 부근, 지면 높이 Z=0 |
| 리깅 / 애니메이션 | 없음. 정적 게임 에셋 |

274는 배치 그룹 수다. 한 그룹 안에 여러 개의 연결된 면 또는 떨어진 작은 UV 섬이 들어갈 수 있다.
각 삼각형은 겹치지 않는 UV 면적을 가진다. 인접 면이 UV 경계선을 공유하는 것은 허용하며,
좌우 바퀴나 펜더를 같은 UV 영역에 겹치거나 미러링해서 공유하지 않았다.

## 텍스처 구성

| 파일 | 색공간 / 채널 | 용도 |
|---|---|---|
| `T_ATV_BaseColor.png` | sRGB, RGB | 이미지 생성 원화에서 재투영한 색상·마모·시트 봉제선·램프 표현 |
| `T_ATV_ORM.png` | **Non-Color / sRGB OFF** | **R=AO, G=Roughness, B=Metallic** |
| `T_ATV_Emissive.png` | sRGB, RGB | 헤드라이트 중심의 약한 발광 |
| `T_ATV_AO.png` | Non-Color, 단일 채널 | ORM의 R 채널과 같은 AO를 편집용으로 분리한 파일 |
| `ATV_UV_Wire.png` | 가이드 | 납품 UV 배치의 삼각형 와이어 |

최종 재질은 UV0를 그대로 읽으며 UV 반복, 타일링, 프로시저럴 노이즈/체커 패턴을 사용하지 않는다.
텍스처 주소 모드는 Clamp다. 노멀맵은 사용하지 않았고, 굵은 곡면과 모따기는 실제 메시와 정점 노멀로 표현했다.

`Source/AI_Painted_Source.png`가 실제 이미지 생성 원화다. 원화의 네이티브 크기는 1254 × 1254다.
이 원화를 생성된 메시의 고유 UV에 맞게 부분별 재투영·마스킹·색보정하여 2048 아틀라스로 만들었다.
원화를 그대로 텍스처 슬롯에 연결하는 방식이 아니다. `Source/Paint_Projection.json`에 배치별 원화 대응 정보가 있다.
원화의 기본 배치를 유지한 정밀 페인트 편집 결과라고 주장하지 않는다. 최종 UV 정합은 별도의 재투영 단계로 맞췄다.

AO는 메시에서 반구 방향으로 레이를 쏘아 계산했다. 1024 해상도에서 샘플당 24레이를 사용한 뒤
2048 ORM에 리샘플링했다. 베이스컬러의 작은 표현은 이미지 생성 원화에서, 접촉 차폐는 기하 베이크에서 나온다.

## Blender에서 재생성

`Blender/build_atv.py`는 기존 GLB를 읽어오는 스크립트가 아니다.
`Source/atv_geometry.py`의 파라메트릭 형상을 만들고, 납품 UV 배치와 텍스처를 연결한다.

Blender 4.2 이상을 대상으로 작성했다. 새 파일에서 Scripting 작업 공간을 열고,
Text Editor에서 **`Blender/build_atv.py`를 파일로 연 뒤 Run Script**를 실행하면 된다.

명령줄 실행 예시:

```bat
blender --background --python "D:\ATV_Stylized\Blender\build_atv.py" -- --out "D:\ATV_Build"
```

기본 출력은 `Build_Blender/ATV_Stylized.blend`와 `Build_Blender/SM_ATV_Stylized.glb`다.
이미지는 `.blend`에 패킹한다. 이 `.blend`는 스크립트 실행 시 만들어지며, ZIP에 미리 만들어진 `.blend`가 들어 있는 것은 아니다.

`--split-parts`를 붙이면 차체와 네 바퀴를 5개 오브젝트로 나누고 바퀴 축에 피벗을 둔다.
이 옵션은 스켈레톤이나 차량 물리를 만드는 기능은 아니다.
`--render`를 붙이면 별도의 스튜디오 카메라·조명을 만들고 세 방향 프리뷰를 렌더한다.

스크립트를 다시 실행할 때 `ATV_Generated`와 선택적으로 `ATV_Preview` 컬렉션만 교체한다.
다른 오브젝트를 일괄 삭제하지 않는다. 형상 치수는 `Source/atv_geometry.py`에서 바꿀 수 있다.
기존 UV 배치 그룹 이름을 유지하는 치수 수정에는 기존 페인트를 늘려서 적용한다.
새 부품/새 그룹을 추가한다면 새 UV 배치와 재페인팅이 필요하다.

## Unreal Engine 5.7에서 임포트

Python Editor Script Plugin, Editor Scripting Utilities, Interchange의 에디터/glTF 임포트 기능을 활성화한다.
플러그인 활성화 직후에는 에디터를 재시작한다.

**Tools → Execute Python Script**에서 `Unreal/import_atv_ue57.py`를 실행한다.
또는 Output Log를 Python 모드로 바꾸고 다음을 실행한다.

```python
import runpy
runpy.run_path(r"D:/ATV_Stylized/Unreal/import_atv_ue57.py", run_name="__main__")
```

스크립트가 압축을 푼 자신의 위치에서 GLB와 PNG를 찾는다. 기본 생성 위치는 `/Game/ATV_Stylized`다.
경로를 바꾸려면 스크립트 상단의 `DESTINATION`만 수정하면 된다.

임포트 스크립트는 Interchange로 정적 메시를 가져오고, 세 PNG를 임포트한 다음
`atv_materials_ue57.py`로 `M_ATV_UniqueAtlas`와 `MI_ATV_Default`를 만들어 메시 슬롯에 연결한다.
ORM의 sRGB를 끄고 각 채널을 올바른 입력에 연결한다. 이미지 생성은 UE 안에서 다시 수행하지 않는다.

UV0는 유지하고 UV1을 라이트맵용으로 생성하도록 설정했다. 노멀은 가져온 값을 유지하며 탄젠트는 재계산한다.
Nanite는 끈 상태로 설정한다. 기본 충돌은 단순 26-DOP이며 차량 주행용 충돌/서스펜션 구성은 별도 작업이다.

GLB의 미터 단위 변환은 임포터에 맡기므로 추가 100배 스케일을 주지 않는다.
임포트 후 가장 긴 변이 약 271 cm인지 검사한다. 프로젝트의 전방축 관례가 다르다면
`IMPORT_YAW_DEGREES`로 회전을 지정하고 임포트 결과의 앞뒤 방향을 확인한다.

기본적으로 기존 경로에 에셋이 있으면 중단한다. 의도적으로 재생성할 때만 `REPLACE_EXISTING=True`로 바꾼다.
현재 레벨에는 아무것도 배치하거나 저장하지 않는다. `SPAWN_PREVIEW_ACTOR=True`를 선택한 경우만 미리보기 액터를 배치한다.
실제 UE 실행이 성공하면 프로젝트의 `Saved/ATV_Import_Report.json`에 엔진 버전·삼각형 수·크기를 기록한다.

## 검증 범위

**실제 수행한 검증:** 파라메트릭 메시 생성, GLB 기록과 독립적인 trimesh 재로딩,
임베디드 PNG와 외부 PNG의 바이트 일치, 정점·인덱스·노멀 검사, 삼각형 예산 검사,
UV 삼각형의 면적 겹침 검사, 납품 형상의 CPU 프리뷰 렌더, 모든 Python 파일의 문법 검사.

**수행하지 않은 검증:** Blender의 `bpy` 어댑터를 Blender 에디터에서 실행하는 것,
UE 5.7 에디터에서 임포트·머터리얼 컴파일을 실행하는 것, Khronos 공식 Validator 실행.
이 환경에는 두 에디터가 없었다. 따라서 에디터 스크립트가 실행 검증을 통과했다고 표시하지 않는다.
UE 스크립트에 사용한 API는 `Unreal/API_SOURCES.md`의 5.7 공식 문서를 기준으로 작성했다.

상세 수치는 `Validation/asset_report.json`, AO 베이크 정보는 `Validation/AO_Bake.json`에 있다.
`Preview/`는 납품 GLB와 동일한 형상·UV·텍스처를 사용한 CPU 기준 렌더다. UE 스크린샷이 아니다.
조명·톤매핑 설정에 따라 Blender와 UE에서 보이는 밝기와 광택은 달라질 수 있다.

## 추가 소스 도구

`Source/rebuild_glb.py`: 일반 Python + NumPy로 GLB를 재생성한다. 기본 출력은 `Build_Python/`이다.
`Source/reproject_paint.py`: 제공된 이미지 생성 원화를 현재 UV 마스크에 재투영한다.
`Source/bake_ao.py`: 메시 AO를 다시 계산해 ORM의 R 채널에 넣는다.
`Source/validate_asset.py`: 구조·UV·텍스처 검사를 다시 실행한다.
`Source/reference_renderer.py`: 납품 메시 데이터의 CPU 기준 렌더러다.

선택적 소스 도구용 패키지는 `Source/requirements.txt`에 정리했다.
Blender 생성 스크립트는 SciPy·Pillow·Numba·Shapely·trimesh를 사용하지 않는다.

기존 텍스처를 보존하려면 `atv_export.py --reset-paint-layout`을 실행하지 않는다.
이 옵션은 새 UV 템플릿을 만들기 위해 페인트 맵을 초기 가이드로 교체하는 명시적 재작업 명령이다.

이 에셋은 3D 프린팅용 단일 폐곡면, 리깅된 Chaos Vehicle, LOD 세트가 아니다.
게임 렌더링용으로 여러 부품의 셸이 교차·분리되어 있고, LOD0 한 단계만 포함한다.
