# ATV Trail — アセットガイド

[English](README.en.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

![ATV Trail 前方プレビュー](../assets/preview-front.png)

このフォルダーは、Codex Astra モデルを **mid（中程度）の推論強度**で作成した比較用アセットです。

提供された参考画像をもとにしたスタイル化 ATV の静的メッシュです。トップダウンのゲーム画面で読みやすい大きなシルエット、タイヤ、フェンダー、クリーム色の車体、ラック、ハンドルを優先しています。高精細な機械部品やリギングは対象外です。

## プレビューと ZIP

`start-preview.cmd` を実行するか、このフォルダーで `node scripts/serve.mjs` を実行して http://127.0.0.1:4177 を開きます。Node.js 18 以降が必要です。任意の静的 Web サーバーでもフォルダーを配信できます。`file://` で直接開くと、ブラウザーの fetch セキュリティ制限により GLB と ZIP の動作が制限されます。

ページには 3D ビューアーと ZIP ライブラリが同梱されているため、外部 CDN なしで動作します。ZIP はブラウザー側で生成されます。`manifest.json` に記載されたファイルだけを読み込み、親ディレクトリや他プロジェクトは対象にしません。Unreal 検証プロジェクト、キャッシュ、一時ログは配布 ZIP から除外されます。

ファイルを変更した後は `node scripts/package-manifest.mjs` を実行して一覧、サイズ、SHA-256 を更新してください。ZIP 自体は再帰的に ZIP に含まれません。

## Blender

検証環境は Blender 4.5 LTS です。`ATV_codex` フォルダーから次を実行します。

```
blender -b --factory-startup --python scripts/build_atv.py
node scripts/validate.mjs
node scripts/package-manifest.mjs
```

スクリプトは専用の `ATV_Production` シーンを作成し、既存シーンのオブジェクトを削除しません。生成したモデルだけを GLB と FBX に出力し、再生成時には `assets/atv.*` とレンダーを上書きします。元の編集内容は別名で保存してください。

単位はメートルです。Blender の前方は -Y、上方向は +Z、ピボットは地面上の車体中央です。GLB は glTF 標準の Y-up に変換されます。寸法と三角形数は `assets/model-stats.json` に記録されています。再生成では同梱の AI テクスチャを再利用し、画像生成サービスは呼び出しません。

## テクスチャと UV

`assets/atv_generated_source.png` は内蔵 ImageGen で作成した元の表面画像です。プロンプトは `docs/texture-prompt.txt` に保存されています。2048×2048 を要求しましたが、返された元画像は 1254×1254 です。これをモデル表面に適用し、最終的な 2048×2048 の固有 UV アトラス `assets/atv_basecolor.png` を作成しています。

8 つのマテリアル領域は、青緑のプラスチック、アイボリーの車体、タイヤゴム、シート、金属ラック、オレンジのアクセント、ランプ、シャーシです。反復タイルや手続き的ノイズは使用していません。最終メッシュの各三角形に固有の UV 空間を割り当て、左右、ホイール、トレッドで UV を共有しません。実際の配置は `assets/atv_uv.svg` で確認できます。

表面色は画像テクスチャ、粗さは 8 つのマテリアルの定数で指定しています。個別のノーマル／ORM マップは作成していません。この構成は GLB と Unreal マテリアルに反映されています。

## Unreal Engine 5.7

1. Python Editor Script Plugin と Editor Scripting Utilities を有効にしてエディターを再起動します。
2. ZIP のフォルダー構造を保ったまま、**Tools → Execute Python Script** から `scripts/ue57_import.py` を実行します。
3. `/Game/ATV_Trail` にメッシュ、Base Color テクスチャ、8 つのマテリアルが作成されます。

同梱 FBX は GLB と同じメッシュと UV を使用します。UE 5.7 の FBX Interchange 設定はインポート中だけ変更し、`finally` で元に戻します。マテリアルスロットは名前で対応付けます。sRGB Base Color、Clamp サンプリング、面ごとの Roughness、ランプの Emissive、+X 前方変換、センチメートル単位を明示的に設定します。ライトマップ用 UV は UE 側で生成されます。既定の衝突は基本形状のみなので、走行物理やサスペンションは別途実装してください。

再実行すると `/Game/ATV_Trail` 内の同名アセットが更新されます。カスタマイズしたアセットは先に複製してください。他のレベル、プロジェクト設定、Content フォルダーは変更しません。`ue57_materials.py` はインポートスクリプトから読み込まれるマテリアルモジュールです。

実際の検証状況とエンジンバージョンは `ue57-validation.json` を確認してください。

## 出典とライブラリ

- ビジュアルリファレンス: `assets/reference.png` の提供画像。
- テクスチャ: 内蔵 ImageGen で新規作成。CLI/API の迂回は使用していません。
- 3D ビューアー: Google model-viewer 4.0.0、Apache-2.0（ライセンス同梱）。
- ZIP: fflate 0.8.2、MIT（ライセンス同梱）。
- [UE 5.7 AssetImportTask](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7)
- [UE 5.7 MaterialEditingLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7)
- [UE 5.7 FbxStaticMeshImportData](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.7)

元の依頼は `user-brief.txt`、最終応答は `final-response.md`、モデル・インポート・計測時間は `execution.json` に保存されています。ページにはセッションで公開されたモデル系列だけを表示し、非公開の推論設定は推測しません。
