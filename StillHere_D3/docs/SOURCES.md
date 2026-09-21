# 데이터와 구현 문서 출처

## 아트 입력

사용자가 제공한 원본 이미지: `source/reference.jpeg`.

생성형 재질 시트: `source/generated_surfaces.png`.

이미지 생성 결과에서 발췌한 물 표면: `source/generated_water_crop.png`.

이 세 이미지와 가공본의 역할은 `source/provenance.json`에 기록했습니다. 원본 장면 이미지를 배경 평면에 붙여 완성 장면처럼 사용하는 구성은 포함하지 않습니다.

## 공식 API 문서

코드 작성 시 확인한 문서입니다. 문서상 API 확인은 실제 편집기 실행 검증을 의미하지 않습니다.

**Epic Games / UE5.7 Editor Python**

- `AssetImportTask`: 자동 임포트와 실제 반환 객체 조회.
- `LevelEditorSubsystem`: 새 레벨 생성, 저장, 카메라 파일럿.
- `EditorLoadingAndSavingUtils`: 현재 레벨 저장.
- `StaticMesh`: 경계 상자와 머터리얼 슬롯.
- `MaterialEditingLibrary`: 네이티브 머터리얼 노드 연결.
- `PostProcessSettings`: 수동 노출과 후처리 설정.
- `CameraComponent`: 직교 카메라 설정.

```text
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LevelEditorSubsystem?application_version=5.7
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLoadingAndSavingUtils?application_version=5.7
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMesh?application_version=5.7
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PostProcessSettings?application_version=5.7
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/CameraComponent?application_version=5.7
```

**Khronos glTF 2.0 규격**

GLB 구조, 좌표·단위, PBR 텍스처와 버퍼/이미지 내장 규약.

```text
https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc
```

## 제작 환경과 배포 범위

사용한 일반 Python 라이브러리 버전은 `validation/metrics.json`에 기록했습니다. 라이브러리와 폰트 바이너리를 이 ZIP에 묶어 배포하지 않습니다. Blender와 Unreal은 사용자 환경에 설치되어 있어야 합니다. 일반 Python 재생성·검증에 필요한 패키지는 `requirements-*.txt`에 분리했습니다.
