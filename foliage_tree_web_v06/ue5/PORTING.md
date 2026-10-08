# UE5 이식 메모 — 실제 웹 데이터 / 자유시점 v06

## 범위
이 문서는 웹에 들어간 실제 메시를 기반으로 한다. Unreal Editor 실행/머티리얼 컴파일은 이 환경에서 수행하지 않았다. GLB의 표준 정적 형상과 재질을 가져오는 것과 웹 바람 수식의 이식은 별개다.

## 메시/좌표
원본은 오른손 Y-up, 단위 metre다. 원본/GLB 임포터의 좌표축·단위 변환을 정점 위치뿐 아니라 카드 피벗에도 동일하게 적용한다. UV 채널에 데이터로 담긴 숫자는 임포터가 위치로 인식해서 변환하지 않을 수 있으므로 직접 변환해야 한다. 피벗과 정점을 일치시키는 검증용 카드 하나로 먼저 확인한다.

GLB: Trunk_UniqueUV / Foliage_Cards의 2개 노드. `models/tree_v05.glb`는 v05와 동일한 정지 형상이다. 이번에 바꾼 것은 런타임 웹 셰이더/카메라이므로 메시 파일을 이름만 v06으로 바꾸거나 재생성하지 않았다.

**v06 웹은 모든 카드가 현재 카메라 평면을 향한다.** UV, 카드 피벗, 소속 덩이, 프록시 노멀, 베이크 색은 정지 좌표에 그대로 남고 정점 위치만 바뀐다. GLB의 일반 임포트만으로 웹의 빌보드 코드가 자동 적용되지는 않는다. `CardBillboardWind.hlsl`이 추가된 이식용 수식이다.

## 잎 데이터
- TEXCOORD_0: 4×4 잎 알파 아틀라스 UV.
- COLOR_0: 프록시 노멀과 고정 조명으로 정한 잎 색(선형 값으로 내보냄).
- TEXCOORD_1: 원본 카드 피벗 X/Y.
- TEXCOORD_2: 원본 카드 피벗 Z / 위상(radian).
- TEXCOORD_3: 덩이 ID / 예약값 1.
- _PIVOT / _PROXY_NORMAL / _WIND_PHASE: 동일 의미의 glTF 사용자 속성. 임포터가 버릴 수 있으므로 추가 UV와 cards.json도 같이 보관했다.

추가 UV를 라이트맵 생성/재패킹으로 덮어쓰면 안 된다. 프록시 노멀을 새 엔진의 광원으로 재평가하려면 cards.json 또는 사용자 속성의 노멀을 별도로 전달한다. 현재 COLOR_0은 고정 조명용이며 나무를 무작위 회전 배치하면 구워진 밝은 방향도 따라 회전한다.

## 머티리얼
잎 기본형: Masked / Unlit / Two Sided. 마스크는 leaves_rgba.png의 A, 컷오프는 0.48. 잎 RGB는 아틀라스 RGB × 버텍스 컬러로 사용한다. 정확한 미술 비교에는 UE 노출·톤매핑 차이를 별도 조정해야 한다. 나무 높이에 따른 그라디언트는 넣지 않는다.

줄기: 고유 UV 0에 trunk_basecolor.png를 연결한다. UE 일반 노멀 규약을 사용한다면 trunk_normal_dx.png부터 확인한다. 노멀은 베이스 컬러 밝기에서 유도한 보조 자료이지 스캔 노멀은 아니다. roughness 맵은 보조 자료다. 웹은 일반 PBR보다 단순한 무광 조명식을 사용하므로 UE PBR과 최종 픽셀이 저절로 같아지지는 않는다.

## 바람
CardWind.hlsl의 입력 RestPosition / Pivot / Right / Up / SwayDirection을 동일한 월드 공간으로 전달한다. 웹 기본은 Right=(1,0,0), Up=(0,1,0), SwayDirection=(1,0.2,0)이다. 이를 UE 좌표계로 변환한다. WindStrength 기본 0.22.

결과는 월드 공간 이동량이므로 WPO에 연결한다. 빌보드에 그려진 여러 잎은 카드 단위로 같이 움직인다. 색/명암은 정지 상태 기준이다. 바람에 따른 바운딩 박스 여유와 그림자 패스 변형 일치도 점검한다.

## 공식 참조
- glTF 2.0 규격: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
- UE World Position Offset: https://dev.epicgames.com/documentation/unreal-engine/world-position-offset-material-functions-in-unreal-engine
- UE Material Inputs: https://dev.epicgames.com/documentation/unreal-engine/material-inputs-in-unreal-engine


## v06 자유시점 / 카메라 추종 이식

웹의 기하 수식은 아래와 같다. 위치와 피벗은 원본 Y-up / metre다.

```text
q = (RestPosition - Pivot).xy * CardScale
q = rotate2D(q, WindAngle)
DisplayPosition = Pivot + CameraRight*q.x + CameraUp*q.y + WorldSway
ShadingNormal = StoredProxyNormal  // 카메라로 회전시키지 않는다
Color = StoredVertexColor * LeafAtlas.rgb
```

원래 XY 카드 정점에 이미 랜덤 회전이 들어 있으므로 q를 재구성할 때 그 회전을 잃지 않는다. 프록시 노멀을 CameraRight/Up으로 회전시키거나 빌보드의 실제 면 노멀로 교체하지 않는다. 단, 실제 나무 인스턴스의 모델 변환과 카메라 변환은 구분해야 한다. 나무를 회전 배치한 후 광원을 다시 평가하려면 노멀에 해당 모델의 노멀 변환을 적용하고 월드 공간 광원과 내적한다. 지금의 베이크 색은 새 조명에 자동 반응하지 않는다.

`LocalOffsetXYMetres`를 추가 정점 채널/UV/데이터 텍스처에 넣거나, 원본 위치와 피벗 차이에서 복원한다. 아틀라스 UV는 카드의 국소 위치 데이터가 아니다. UE 단위에 맞춰 위치뿐 아니라 카드 오프셋과 바람 진폭도 변환한다. 제공 함수는 균일 인스턴스 스케일을 전제로 하며 비균일 스케일은 별도 기준을 정해야 한다.

### 그림자 처리의 의도적 차이

카메라가 이동하면서 표시용 카드가 회전할 때 지면/줄기 그림자까지 흔들리지 않도록, **웹의 그림자 패스는 기존 정지 카드 방향을 쓰는 고정 그림자 프록시**다. 바람 수식과 알파 컷오프는 공유하지만 표시용 빌보드와 그림자용 카드의 방향은 다를 수 있다. 실제 표시 카드의 정확한 물리 그림자라고 주장하지 않는다.

UE에서는 표시 카드와 별도의 그림자 프록시를 두거나, 선택한 렌더링 경로에서 확실하게 구분되는 그림자 패스 입력을 사용해야 한다. 단순히 각 패스의 View 축을 쓰면 그림자 카메라가 들어올 수 있으므로 주의한다. 제공 함수의 `StableShadowProxy`는 그 선택을 명시한 것이며, 엔진에서 패스 판별/바운딩 박스/컬링 연결을 자동 설정하지는 않는다.

카드가 피벗 주위를 회전하므로 정지 GLB 바운드만 쓰지 말고 최대 카드 반대각선 및 바람 진폭 여유를 포함한다. UE5 에디터의 컴파일, Lumen/VSM/Nanite 호환 검증은 이번 작업에 포함되지 않는다.
