# ATV Stylized — GLB / Blender / Unreal Engine 5.7

[English](README.en.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

A stylized, game-ready ATV reconstructed from front and rear three-quarter reference images. The asset focuses on the large body, fenders, tires, and rack silhouette rather than duplicating a scan or CAD model.

## Ready-to-use asset

**`Model/SM_ATV_Stylized.glb`**

The GLB contains the mesh, base color, ORM, and emissive textures, so it can be opened without locating external PNG files. Matching editable texture copies are available in `Textures/`.

| Item | Delivered data |
|---|---|
| Render triangles | **8,976** — fewer than 10,000 |
| Mesh / material / primitive | 1 / 1 / 1 |
| Vertices including UV and normal seams | 10,260 |
| UV channels | One UV0 channel, entirely within 0–1 |
| UV atlas groups | 274 |
| UV triangle overlap | **0 pairs** within a 1e-11 UV² tolerance |
| PBR maps | 2048 × 2048 PNG each |
| Dimensions | Approximately 2.706 m × 1.840 m × 1.837 m |
| Axes | Source/Blender: +X forward, +Z up; GLB: +X forward, +Y up |
| Origin | Near the body center; ground at Z=0 |
| Rig / animation | None; static game asset |

## Textures

| File | Color space / channels | Purpose |
|---|---|---|
| `T_ATV_BaseColor.png` | sRGB, RGB | Reprojected paint, wear, seat seams, and lamp details |
| `T_ATV_ORM.png` | **Non-Color / sRGB off** | **R=AO, G=Roughness, B=Metallic** |
| `T_ATV_Emissive.png` | sRGB, RGB | Subtle headlight-centered emission |
| `T_ATV_AO.png` | Non-Color, single channel | AO separated from the ORM red channel |
| `ATV_UV_Wire.png` | Guide image | UV layout reference |

The final paint uses UV0 directly. Texture addressing is Clamp; no repeat, mirror, or shared wheel/fender UV regions are used.

## Blender generation

`Blender/build_atv.py` generates the parametric mesh, UV layout, textures, and GLB. It targets Blender 4.2 or later.

```bat
blender --background --python "D:\ATV_Stylized\Blender\build_atv.py" -- --out "D:\ATV_Build"
```

The default output is `Build_Blender/ATV_Stylized.blend` and `Build_Blender/SM_ATV_Stylized.glb`. Use `--split-parts` to separate the body and four wheels, or `--render` to create a front three-quarter preview.

## Unreal Engine 5.7 import

Enable Python Editor Script Plugin, Editor Scripting Utilities, and Interchange. Run `Unreal/import_atv_ue57.py` from **Tools → Execute Python Script**, or use:

```python
import runpy
runpy.run_path(r"D:/ATV_Stylized/Unreal/import_atv_ue57.py", run_name="__main__")
```

The script imports the GLB and PNG textures into `/Game/ATV_Stylized`, creates the material and instance, preserves UV0, generates UV1 for lightmaps, and enables Nanite. Set `DESTINATION` at the top of the script to change the destination. Set `REPLACE_EXISTING=True` only when replacing an existing import.

## Validation and source tools

The validation data is in `Validation/asset_report.json`, `Validation/AO_Bake.json`, and `Validation/SHA256SUMS.json`. The `Preview/` images are CPU reference renders using the delivered mesh, UVs, and textures.

Additional tools are in `Source/`: `rebuild_glb.py`, `reproject_paint.py`, `bake_ao.py`, `validate_asset.py`, and `reference_renderer.py`. Optional Python packages are listed in `Source/requirements.txt`.

Blender and Unreal editor execution, and the Khronos validator, were not available in the delivery environment; those editor-side checks are therefore not claimed as executed.
