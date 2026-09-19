# Wooden Food Shed — v1

[English](README.en.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

![木製食料小屋の概要](previews/overview.jpg)

提供されたリファレンスをもとに制作した、トップダウンゲーム向けのローポリ木製食料小屋です。広い片流れ屋根、太い木材フレーム、開いた両開き扉、低い踏み台をシルエットの中心にしています。板の隙間、木目、蝶番、リベット、斜めの補強材は主にテクスチャで表現し、メッシュには大きな形状と浅いベベルを残しています。

扉を開いた GLB と閉じた GLB は別ポーズの静的アセットです。建物、扉、棚、袋、箱、樽、陶器、食料、ランタンを含み、それぞれ 2,952 三角形です。2 つを同時に配置する用途ではありません。

## 仕様

| 項目 | 値 |
|---|---|
| フォーマット | glTF 2.0 Binary / GLB |
| 三角形 | 各バリアント 2,952 |
| GLB メッシュ / マテリアル | 1 / 1 |
| 出力頂点 | 6,064（面ごとの UV・法線シームを含む） |
| Blender ソースオブジェクト | 46 |
| 固有サーフェス UV アイランド | 1,556 |
| テクスチャアトラス | 4,096 × 4,096 |
| UV 密度 | 約 222.09 px/m、表面長に比例 |
| アイランド余白 | 周囲 6 px |
| アトラス占有率 | 配置矩形の約 72.5% |
| 外形 | 扉を開いた状態で約 幅4.53 × 奥行4.02 × 高さ3.28 m |
| 原点 | 地面 Z=0 の建物中央 |
| 座標 | Blender は Z-up / 前方 -Y / m、GLB は glTF Y-up |

制限値は頂点数ではなく三角形数で検査しています。プレビューの地面、照明、影は GLB に含まれず、周囲の草地や地形も追加していません。

## ファイル構成

```text
models/wooden_food_shed.glb         # 両開き扉: 開
models/wooden_food_shed_closed.glb  # 両開き扉: 閉
textures/T_Shed_BaseColor.png
textures/T_Shed_Normal_GL.png       # Blender / glTF 用
textures/T_Shed_Normal_DX.png       # Unreal 用、グリーン反転済み
textures/T_Shed_ORM.png              # R=AO、G=Roughness、B=Metallic
textures/T_Shed_Emissive.png        # ランタン領域
blender/create_wooden_food_shed.py
unreal/import_wooden_food_shed_ue57.py
source/mesh_payload.json
previews/overview.jpg               # 代表概要プレビュー
validation/                          # 統計と検証レポート
tools/build_asset.py                 # メッシュ、UV、PBR アトラス、GLB の再生成
tools/render_preview.py              # CPU プレビューレンダラー
```

## UV とテクスチャ制作

UV0 は 0–1 の範囲内です。異なる面のアイランドを重ねたりミラーしたりせず、タイリングシェーダー、反復トリムシート、ワールド座標パターンも使っていません。広い屋根や壁には多くのピクセルを割り当て、小さな金具やベベルには少なくするよう、実際の表面長に合わせて配置しています。生成した木材原画の一部は複数の面で利用しますが、最終 UV 空間は各面で固有です。

建築表面の原画は画像生成で作成し、小物の表面は生成画像から抽出して遠近を補正した後、独立に配置・リサンプル・合成しました。Base Color は 8bit RGB PNG です。Normal と ORM は画像から推定した補助マップで、スカルプトベイクや実測 PBR マップではありません。ORM は R=AO、G=Roughness、B=Metallic です。ランタンは不透明な発光面に簡略化しています。

## GLB の使用

`models/wooden_food_shed.glb` にはメッシュ、UV、法線、タンジェント、Base Color、OpenGL Normal、ORM、Emissive が含まれています。外部テクスチャなしで読み込める自己完結型です。発光強度は `KHR_materials_emissive_strength` で 2.3 に設定しています。

GLB は結合済みの静的ゲームメッシュで、扉のアニメーションや分離した屋根ノードは含みません。扉のヒンジを調整したり屋根を切り替えたりする場合は Blender 再構成オブジェクトを使ってください。

## Blender での生成

Blender 4.2 以降 / 5.x を対象にしています。フォルダー構造を保ったまま展開し、新しい Blender ファイルで `blender/create_wooden_food_shed.py` を実行します。

```bash
blender --background --python blender/create_wooden_food_shed.py -- --output ./blender_output --export-glb --save-blend
```

閉じたポーズは次のコマンドで生成できます。

```bash
blender --background --python blender/create_wooden_food_shed.py -- --closed --no-preview --output ./blender_output_closed --export-glb --save-blend
```

スクリプトは `source/mesh_payload.json` の明示的な頂点・三角形・UV データから再構成し、GLB を再インポートしません。`WoodenFoodShed_v1` コレクションを作成し、他のコレクションは削除しません。`DoorHinge_Left` と `DoorHinge_Right` が扉のピボットです。`Shed_Roof_HideForCutaway` を非表示にすると内部を確認できます。

## Unreal Engine 5.7

Python Editor Script Plugin、Editor Scripting Utilities、Interchange Editor、Interchange Framework を有効にし、`unreal/import_wooden_food_shed_ue57.py` をエディターの Python スクリプトとして実行します。既定の保存先は `/Game/Generated/WoodenFoodShed_v1` です。

スクリプトは外部 PNG をインポートし、`M_WoodenFoodShed` と `MI_WoodenFoodShed` を作成して、インポート結果の StaticMesh にマテリアルを割り当てます。開いた版と閉じた版は `Meshes/Open` と `Meshes/Closed` に配置されます。Base Color と Emissive は sRGB、Normal と ORM はリニアデータとして設定します。Normal DX はグリーン反転済みなので Flip Green Channel はオフのままにします。

インポート後に三角形数と約 328 cm の高さを確認してください。`REPLACE_EXISTING=False` が既定で、既存アセットは上書きしません。現在のレベルに Actor を作成したり照明を変更したりもしません。

既定の `COLLISION_MODE='box'` はトップダウン用の単純な障害物で、入口も塞ぎます。屋内移動が必要ならカスタム衝突を作成してください。小さな UV アイランドが多いためライトマップ UV の生成は既定で無効です。ベイク照明が必要な場合は `GENERATE_LIGHTMAP_UV=True` にして 512px から確認します。Nanite は無効です。

## 検証範囲

三角形数、インデックス、退化三角形、法線、UV の範囲・重複・密度、GLB 構造、内蔵画像、開閉バリアントの独立ラウンドトリップを検査しています。プレビューは納品メッシュをソフトウェアレンダーした画像で、`interior.png` は確認のため屋根だけを非表示にしています。

納品環境では Blender と Unreal Editor の実行はできませんでした。Python 構文と Epic の UE 5.7 API 参照は確認済みですが、エディター実行やマテリアルコンパイルの完了は主張していません。ローカル検査は次で実行できます。

```bash
python validation/test_asset.py
python tools/build_asset.py
python tools/render_preview.py --view hero
```

詳細な結果は `validation/verification_report.json`、`validation/test_results.txt`、`validation/environment_versions.json` にあります。

## 公式リファレンス

- [Unreal 5.7 AssetImportTask](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7)
- [Unreal 5.7 MaterialEditingLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7)
- [Unreal 5.7 StaticMeshEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.7)
- [Unreal 5.7 Texture](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Texture?application_version=5.7)
- [Unreal 5.7 Interchange](https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine?application_version=5.7)
