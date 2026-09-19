# ATV Stylized — GLB / Blender / Unreal Engine 5.7

[English](README.en.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

前後の 3/4 参考画像をもとに再構成した、ゲーム向けのスタイル化 ATV です。スキャンや CAD の複製ではなく、車体・フェンダー・タイヤ・ラックのシルエットを重視したモデルです。

## すぐに使えるアセット

**`Model/SM_ATV_Stylized.glb`**

GLB にはメッシュ、ベースカラー、ORM、エミッシブテクスチャが含まれているため、外部 PNG を別途探さずに開けます。編集用の同じテクスチャは `Textures/` にあります。

| 項目 | 納品データ |
|---|---|
| レンダリング三角形 | **8,976** — 10,000 未満 |
| メッシュ / マテリアル / プリミティブ | 1 / 1 / 1 |
| UV・法線シームを含む頂点 | 10,260 |
| UV チャンネル | UV0 が 1 つ、全体が 0–1 範囲 |
| UV アトラスグループ | 274 |
| UV 三角形の重なり | **0 ペア**（許容誤差 1e-11 UV²） |
| PBR マップ | 各 2048 × 2048 PNG |
| サイズ | 約 2.706 m × 1.840 m × 1.837 m |
| 軸 | Source/Blender: +X 前方、+Z 上。GLB: +X 前方、+Y 上 |
| 原点 | 車体中央付近、地面の高さは Z=0 |
| リグ / アニメーション | なし。静的ゲームアセット |

## テクスチャ

| ファイル | 色空間 / チャンネル | 用途 |
|---|---|---|
| `T_ATV_BaseColor.png` | sRGB, RGB | ペイント、摩耗、シートの縫い目、ランプ表現 |
| `T_ATV_ORM.png` | **Non-Color / sRGB オフ** | **R=AO、G=Roughness、B=Metallic** |
| `T_ATV_Emissive.png` | sRGB, RGB | ヘッドライト中心の弱い発光 |
| `T_ATV_AO.png` | Non-Color、単一チャンネル | ORM の R チャンネルから分離した AO |
| `ATV_UV_Wire.png` | ガイド画像 | UV レイアウトの確認用 |

最終ペイントは UV0 をそのまま使用します。テクスチャアドレスは Clamp で、リピート・ミラーや左右のホイール／フェンダー間での UV 共有はありません。

## Blender での生成

`Blender/build_atv.py` はパラメトリックメッシュ、UV、テクスチャ、GLB を生成します。Blender 4.2 以降を対象にしています。

```bat
blender --background --python "D:\ATV_Stylized\Blender\build_atv.py" -- --out "D:\ATV_Build"
```

既定の出力は `Build_Blender/ATV_Stylized.blend` と `Build_Blender/SM_ATV_Stylized.glb` です。`--split-parts` で車体と 4 つのホイールを分離し、`--render` で前方 3/4 プレビューを作成できます。

## Unreal Engine 5.7 へのインポート

Python Editor Script Plugin、Editor Scripting Utilities、Interchange を有効にします。**Tools → Execute Python Script** から `Unreal/import_atv_ue57.py` を実行してください。

```python
import runpy
runpy.run_path(r"D:/ATV_Stylized/Unreal/import_atv_ue57.py", run_name="__main__")
```

スクリプトは GLB と PNG を `/Game/ATV_Stylized` にインポートし、マテリアルとインスタンスを作成します。UV0 を保持し、ライトマップ用の UV1 を生成して Nanite を有効にします。保存先を変更する場合はスクリプト上部の `DESTINATION` を編集してください。既存アセットを置き換える場合だけ `REPLACE_EXISTING=True` にします。

## 検証とソースツール

検証データは `Validation/asset_report.json`、`Validation/AO_Bake.json`、`Validation/SHA256SUMS.json` にあります。`Preview/` は納品メッシュ、UV、テクスチャを使った CPU 基準レンダーです。

追加ツールは `Source/` にあり、`rebuild_glb.py`、`reproject_paint.py`、`bake_ao.py`、`validate_asset.py`、`reference_renderer.py` を含みます。任意の Python パッケージは `Source/requirements.txt` に記載しています。

納品環境には Blender と Unreal のエディタ、および Khronos Validator がなかったため、エディタ側の実行検証は完了したものとして扱っていません。
