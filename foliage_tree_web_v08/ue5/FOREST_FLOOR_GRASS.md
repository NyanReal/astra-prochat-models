# v08 — 숲 바닥과 뿌리 주변 풀 이식

이번 추가분은 웹 실행 검증까지 완료한 소스/에셋이다. UE5 에디터에서 실행하거나 .uasset으로 저장한 결과물은 아니다.
v08의 나무는 tree_v08.glb로 교체됐다. 숲 바닥과 풀의 데이터/바람 계약은 v07 그대로 유지했다.

## 데이터
- `assets/forest_floor_basecolor.jpg`: 1024 × 1024 RGB. 생성 이미지의 지면 부분을 추출, 색상과 타일 경계 및 이끼/흙 분포를 보정했다. 실측 재질이 아니며 그림 느낌의 미세 명암이 포함된다.
- `models/root_grass_v08.glb`: 웹과 같은 84개 덤불, 548개 풀잎, 3,836 triangles. 곡선형 리본 메시이고 카메라 추종 카드가 아니다.
- `assets/root_grass.json`: 웹에서 생성하는 것과 같은 정점, 인덱스, 색, 피벗, 위상 데이터.
- `GrassWind.hlsl`: 풀의 정점 변형. GLB 자체는 정지 메시이다.

## 공유 바람과 배율
`GrassWind = MasterWind × GrassRatio`.
나무에 전달하는 동일한 MasterWind와 SharedWindTime을 풀에도 전달한다. 예를 들어 프로젝트의 Material Parameter Collection에 두 공통 값을 두고, 풀 머티리얼 인스턴스에 GrassRatio만 따로 둔다. 기본 배율은 0.65, 조절 범위는 0~2이다. MasterWind=0이면 나무와 풀 모두 정지하고, GrassRatio=0이면 풀만 정지한다.

`GrassWind.hlsl`을 Custom 노드 본문에 넣고, 결과를 적절한 로컬→월드 벡터 변환 후 World Position Offset으로 보낸다. 루트의 높이 가중치는 0, 끝은 1이며 가중치를 제곱하므로 루트는 고정되고 끝이 더 크게 움직인다. 포지션 변형에 카메라 벡터를 사용하지 않는다.

GLB의 UV 데이터 계약:
| 데이터 채널 | 내용 |
| --- | --- |
| UV0 | U = 풀잎 폭 좌표, V = 루트 0 / 끝 1 가중치 |
| UV1 | 루트 X, Z (웹 로컬 미터 좌표) |
| UV2 | 위상(라디안), 풀잎 전체 높이(미터) |
| UV3 | 루트 Y(미터), 덤불 번호 |
| Vertex Color RGB | 잎 색. GLB에는 sRGB→linear 변환하여 저장 |

UV1~3을 라이트맵 UV 생성/재패킹에 덮어쓰지 않는다. 전달 경로에서 추가 UV가 남아 있는지 확인한다. HLSL의 예제 축 변환은 UE(X,Y,Z)=100×Web(X,Z,Y)이다. 프로젝트의 실제 수입 축·단위와 다르면 그 매핑을 맞춰야 한다. 풀 메시 이동/회전과 바람의 위치 기반 위상이 같이 움직이게 할지, 월드 바람장을 통과하게 할지도 프로젝트에서 정한다.

기존 웹 룩에는 Two Sided + Unlit vertex colour 기반이 적합하다. 실제 표면광 반응이 필요하면 Lit으로 바꾸되 다른 외양이 될 수 있다. 바람 최대 변위만큼 렌더 바운드를 여유 있게 잡고 그림자 패스에도 같은 변형을 적용한다.

## 바닥
월드/나무 로컬 XZ를 바닥 UV로 사용한다. 웹은 주 텍스처 3.6m 주기와 작은 1.35m 주기(회전) 텍스처를 21% 혼합하고, 중심에서 멀어지면 중립 배경으로 부드럽게 이어 붙인다. 이것은 바닥 재질 효과일 뿐, 나무 전체 색 그라디언트를 다시 켠 것이 아니다. 일반적인 UE 지면에서는 Repeat 샘플링과 원하는 밀도만 먼저 이식해도 된다.

웹에서는 기본 그림자가 나무의 기존 카메라 독립 카드 프록시를 사용한다. 풀은 실제 리본 메시를 그리며 기본 패스와 그림자 패스에 같은 변형 함수를 사용한다.

## 공식 참고
- Epic, World Position Offset Material Functions: https://dev.epicgames.com/documentation/unreal-engine/world-position-offset-material-functions-in-unreal-engine
  SimpleGrassWind도 가중치·강도를 받을 수 있지만, 웹과 같은 움직임을 유지하려면 위의 동일한 수식을 사용한다.
