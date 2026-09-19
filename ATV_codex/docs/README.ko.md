# ATV Trail — 에셋 사용 안내

[English](README.en.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

![ATV Trail 전면 프리뷰](../assets/preview-front.png)

이 폴더는 Codex Astra 모델을 **mid 추론강도**로 작업한 비교용 에셋입니다.

첨부 이미지를 기준으로 만든 스타일라이즈드 ATV 스태틱 메시입니다. 큰 타이어와 펜더, 크림색 차체, 랙, 핸들을 실제 형상으로 표현했습니다. 고해상도 기계 부품이나 차량 리깅은 범위에 포함하지 않습니다.

## 미리보기와 ZIP

`start-preview.cmd`를 실행하거나, 이 폴더에서 `node scripts/serve.mjs`를 실행하고 http://127.0.0.1:4177 에 접속하세요. Node.js 18 이상이 필요합니다. 일반 정적 웹 서버에도 `atv` 폴더 그대로 올릴 수 있습니다. 파일 더블클릭(`file://`) 방식은 브라우저의 fetch 보안 제한으로 GLB/ZIP 동작이 제한됩니다.

3D 뷰어와 ZIP 라이브러리를 동봉해 외부 CDN 요청 없이 실행합니다. ZIP은 서버 작업 없이 브라우저에서 생성됩니다. `manifest.json`에 명시한 atv 내부 산출물만 읽고, 상위 경로나 다른 프로젝트를 탐색하지 않습니다. 검증용 UE 프로젝트와 캐시, 임시 로그는 배포 산출물이 아니므로 ZIP에서 제외합니다.

파일 변경 후에는 `node scripts/package-manifest.mjs`로 목록·크기·SHA-256을 갱신하세요. ZIP 자체는 ZIP에 재귀적으로 포함하지 않습니다.

## Blender

검증 환경: Blender 4.5 LTS. 다음 명령은 atv 폴더에서 실행합니다.

```
blender -b --factory-startup --python scripts/build_atv.py
node scripts/validate.mjs
node scripts/package-manifest.mjs
```

스크립트는 전용 장면 `ATV_Production`을 생성합니다. 기존 장면의 오브젝트를 지우지 않으며, 생성한 모델만 GLB/FBX로 내보냅니다. 기존 `assets/atv.*`와 렌더는 재생성 시 덮어씁니다. 원본 수정은 별도 이름으로 저장하세요. 현재 Blender UI에서 실행하려면 스크립트 파일을 Text Editor에서 열어 Run Script를 사용하세요.

단위는 미터, Blender 기준 전방 -Y, 위쪽 +Z, 피벗은 지면의 차체 중심입니다. GLB는 glTF 표준 Y-up으로 변환됩니다. 실제 치수와 삼각형 수는 `assets/model-stats.json`에 기록합니다. 재생성은 동봉한 AI 텍스처를 재사용하며 이미지 생성 서비스 호출은 하지 않습니다.

## 텍스처와 UV

`assets/atv_generated_source.png`는 내장 이미지 생성 도구로 만든 원본 표면 이미지입니다. 프롬프트는 `docs/texture-prompt.txt`에 보관합니다. 프롬프트는 2048×2048을 요청했으나 실제 반환 이미지 해상도는 1254×1254입니다. 이를 모델 표면에 매핑한 후 고유 UV로 Emission 베이크한 최종 아틀라스가 `assets/atv_basecolor.png` (2048×2048)입니다. 2K는 배포용 베이크 해상도이며 원본 생성 해상도와 구분합니다. 새로운 절차적 패턴을 추가하지 않았습니다.

8개의 재질 영역은 청록 플라스틱, 아이보리 차체, 타이어 고무, 안장, 금속 랙, 주황 포인트, 램프, 차대입니다. 이미지에 반복 타일이나 절차적 노이즈 패턴을 적용하지 않았습니다. 같은 색 계열을 쓰더라도 모든 최종 삼각형에 별도의 고유 UV 공간을 배정하며, 좌우·바퀴·트레드가 UV를 공유하지 않습니다. 기하학적 트레드 반복과 텍스처 반복은 구분됩니다.

UV0의 각 삼각형을 실제 면 크기에 비례해 투영하고 서로 떨어진 영역에 패킹합니다. 작은 삼각형은 UV 폭과 높이를 최소 3픽셀로 확보하며 아일랜드 양쪽에 3픽셀씩 여백을 둡니다. 최종 텍스처는 패킹된 UV에 맞추어 생성 이미지의 표면색을 베이크하므로 무작위 삼각형 색 경계를 줄입니다. 제작 중 임시 소스 UV는 최종 메시에서 제거합니다. 매우 멀리서의 밉맵 단계에서는 작은 아일랜드 경계가 혼합될 수 있습니다. `assets/atv_uv.svg`는 실제 UV 배치입니다. 검증은 모든 UV 삼각형 쌍 중 후보를 공간 분할로 추린 뒤 교차 면적을 계산합니다. 공유 경계는 중첩으로 세지 않습니다.

표면 색은 이미지 텍스처, 거칠기는 8개 머터리얼의 상수로 지정합니다. 별도의 노멀/ORM 맵은 만들지 않았습니다. 이 구성을 그대로 GLB와 UE 머터리얼에 반영합니다.

## Unreal Engine 5.7

1. Python Editor Script Plugin과 Editor Scripting Utilities를 활성화하고 에디터를 재시작합니다.
2. ZIP의 폴더 구조를 유지한 채 Tools → Execute Python Script에서 `scripts/ue57_import.py`를 선택합니다.
3. `/Game/ATV_Trail`에 메시, Base Color 텍스처, 8개 머터리얼이 생성됩니다.

GLB와 동일한 메시·UV를 가진 동봉 FBX를 이용합니다. UE 5.7의 FBX Interchange 플래그는 임포트 구간에만 일시 변경하고 `finally`에서 기존 값으로 복구합니다. 머터리얼 슬롯은 이름으로 매칭합니다. sRGB Base Color, Clamp 샘플링, 표면별 Roughness, 램프 Emissive를 명시적으로 연결합니다. 전방 +X로 변환하며 센티미터 단위를 적용합니다. 라이트맵용 UV는 UE에서 별도로 생성합니다. 자동 충돌은 기본 형태이므로 게임의 주행 물리에 맞는 충돌/서스펜션은 후속 작업입니다.

재실행 시 `/Game/ATV_Trail`의 같은 이름 에셋을 갱신합니다. 해당 경로의 에셋을 별도로 커스터마이즈했다면 먼저 복제하세요. 레벨, 프로젝트 설정, 다른 Content 폴더는 수정하지 않습니다. `ue57_materials.py`는 임포트 스크립트가 불러오는 모듈입니다.

실제 검증 여부와 엔진 버전은 `ue57-validation.json`을 확인하세요.

## 출처 및 라이브러리

- 시각적 레퍼런스: 사용자가 제공한 이미지 (`assets/reference.png`). 이미지의 인쇄 문구는 작업 지시로 취급하지 않았습니다.
- 텍스처: 내장 ImageGen으로 새로 생성; CLI/API 우회 사용 없음.
- 3D 뷰어: Google model-viewer 4.0.0, Apache-2.0 (vendor 라이선스 동봉).
- ZIP: fflate 0.8.2, MIT (vendor 라이선스 동봉).
- [UE 5.7 AssetImportTask](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7)
- [UE 5.7 MaterialEditingLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7)
- [UE 5.7 FbxStaticMeshImportData](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.7)

사용자 원문은 `user-brief.txt`, 최종 응답은 `final-response.md`, 모델·임포트·측정 시간은 `execution.json`에 보관하며 index 페이지에 그대로 표시합니다. 모델 계열은 세션이 공개한 정보만 표시합니다. 리즈닝 이포트 설정은 세션에서 노출되지 않아 추정하지 않습니다.
