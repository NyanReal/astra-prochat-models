# 입체 수관과 가지 — 스태틱 웹 v08

`index.html`을 브라우저에서 열면 실행됩니다. 메시, 텍스처, 셰이더가 HTML 안에 포함되어 있습니다. 서버나 외부 JavaScript 라이브러리가 필요하지 않습니다. 이 결과물은 실제 WebGL2 페이지이며, validation의 이미지는 그 페이지를 실행해서 캡처한 것입니다.

## 이번 수정

기존 수관의 중심점들이 X(좌우) 2.91m, Z(앞뒤) 0.44m에 모여 있던 배치를 고쳤습니다. 나무를 Z로 통째 늘리거나 시점만 바꾼 것이 아닙니다.

- 주 가지와 보조 가지가 서로 다른 높이에서 앞·뒤·사선으로 갈라지는 새로운 3D 골격을 작성했습니다.
- 각 잎뭉치를 해당하는 실제 가지 끝에 배치했습니다. `assets/scene.json`의 각 bunch에는 `branchIndex`가 있습니다.
- 10개 잎뭉치, 2,880개 잎 카드를 유지했습니다. 삭제했던 상단 ID 909, 1001은 복구하지 않았습니다.
- 중심점 앞뒤 범위 2.35m, 좌우 범위 3.00m. 가장 높은 카드 피벗 Y=4.358978m로 v07과 같습니다. 이것은 **중심점 범위**이며 잎 외곽 바운드와 다릅니다.
- 줄기와 가지는 연결된 실제 메시로 다시 만들었고, 바뀐 형상에 맞춰 고유 UV와 나무껍질 텍스처를 재베이크했습니다.
- 기존 나무/풀 바람 수식, 풀 바람 배율 0~2, 자유시점 카메라, 잎 노멀 셰이딩을 유지했습니다. 전체 높이 그라디언트는 없습니다.
- 잎 알파 아틀라스, 숲 바닥 텍스처, 풀 메시 데이터, 껍질 원본 이미지는 v07과 바이트 단위로 같습니다.

## 조작

드래그는 회전, 휠은 확대/축소, 우클릭 또는 Shift+드래그는 이동입니다. 터치 조작도 기존과 같습니다. F는 시점 복귀, H는 UI 표시/숨김입니다.

**오른쪽 / 뒷면 / 위에서 / 3D 줄기만**을 사용하면 앞뒤 분기 구조를 확인하기 쉽습니다. 풀 바람은 `나무 바람 × 풀 바람 배율`이며, 나무 바람을 0으로 하면 풀도 멈춥니다.

## 파일

- `index.html`: 모든 데이터를 내장한 실제 웹 실행본.
- `models/tree_v08.glb`: 웹과 같은 새 줄기/잎 정지 메시와 재질, 카드 피벗/노멀/위상 데이터.
- `models/root_grass_v08.glb`: 웹과 같은 풀 메시. v07 풀 데이터는 보존했습니다.
- `assets/scene.json`, `cards.json`, `branch_skeleton.json`: 엔진 독립 원본 데이터.
- `src/tree_structure.py`: 가지 계층, 반경, 3D 경로와 잎뭉치 배치를 수정하는 곳.
- `src/build_assets.py`: 연결된 메시 생성, UV와 텍스처 베이크, GLB 내보내기.
- `src/viewer.js`, `environment.js`, `orbit-camera.js`: 실제 웹 렌더러와 조작/바람 소스.
- `ue5/`: 좌표/머티리얼 데이터 계약 및 빌보드·풀 바람 HLSL.
- `validation/`: 실제 브라우저 캡처, 측정 결과, 검사 기록.

## 다시 빌드

Python 의존성: numpy, scipy, scikit-image, Pillow, trimesh. 풀 내보내기에 Node.js가 필요합니다. 브라우저 QA에 Playwright와 Chromium을 사용했습니다.

```sh
python src/build_assets.py
python src/export_grass.py
python src/build_page.py
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_orbit.js tests/test_environment.js
```

Linux 소프트웨어 GPU 검사 환경에서는 Xvfb 디스플레이가 필요했습니다.

```sh
xvfb-run -a python tests/browser_check.py
xvfb-run -a python tests/browser_environment_check.py
xvfb-run -a python tests/browser_crown_check.py
xvfb-run -a python tests/capture_crown.py
```

## 검증 및 제한

Python 10개, Node 10개 검사 통과. 실제 HTML의 WebGL 렌더, 카드의 GPU 노멀/색 불변성, 카메라 추종, 6개 표시 모드, 마우스 조작, 풀 바람 배율과 밑동 고정을 별도로 확인했습니다. `validation/QA_NOTES.md`에 범위와 실행 제한을 적었습니다.

GLB는 정지 메시입니다. 웹의 카메라 추종/바람을 UE5에서 재현하려면 포함된 데이터와 HLSL을 연결해야 합니다. UE5 에디터에서의 임포트·머티리얼 컴파일·성능 검증은 수행하지 않았습니다. 노멀 텍스처는 껍질 이미지 밝기에서 유도한 보조 자료이지 실측 노멀이 아닙니다.
