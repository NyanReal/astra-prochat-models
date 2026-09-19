# ATV Trail — Asset Guide

[English](README.en.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

![ATV Trail front preview](../assets/preview-front.png)

This folder contains a comparison asset created with the Codex Astra model using **mid reasoning effort**.

The stylized ATV static mesh was built from the supplied reference images. The design prioritizes the large silhouette, tires, fenders, cream body, rack, and handlebar for a top-down game view; high-resolution mechanical details and rigging are outside the scope.

## Preview and ZIP

Run `start-preview.cmd`, or from this folder run `node scripts/serve.mjs` and open http://127.0.0.1:4177. Node.js 18 or later is required. The folder can also be hosted by any static web server. Opening the page with `file://` limits GLB and ZIP behavior because of browser fetch security.

The page bundles the 3D viewer and ZIP library, so it runs without external CDN requests. The ZIP is generated in the browser. Only the files listed by `manifest.json` are read; parent directories and other projects are outside the scope. Unreal validation projects, caches, and temporary logs are excluded from the delivery ZIP.

After changing files, run `node scripts/package-manifest.mjs` to refresh the file list, sizes, and SHA-256 values. The ZIP does not recursively include itself.

## Blender

Validation environment: Blender 4.5 LTS. Run these commands from the `ATV_codex` folder:

```
blender -b --factory-startup --python scripts/build_atv.py
node scripts/validate.mjs
node scripts/package-manifest.mjs
```

The script creates a dedicated `ATV_Production` scene without deleting objects from an existing scene. Only generated model outputs are exported to GLB and FBX; existing `assets/atv.*` files and renders are overwritten on regeneration. Save original edits under a separate name.

Units are meters. Blender uses -Y forward and +Z up, with the pivot at the body center on the ground. The GLB is converted to glTF Y-up. Dimensions and triangle counts are recorded in `assets/model-stats.json`. Regeneration reuses the included AI texture and does not call an image-generation service.

## Texture and UV

`assets/atv_generated_source.png` is the source surface image created by the built-in image-generation tool. Its prompt is stored in `docs/texture-prompt.txt`. The prompt requested 2048×2048, but the returned source image is 1254×1254. After mapping it to the model, the final 2048×2048 unique-UV atlas is `assets/atv_basecolor.png`.

The eight material regions are teal plastic, ivory body, rubber tires, seat, metal rack, orange accents, lamps, and chassis. No repeating tile or procedural noise pattern is applied. Every final triangle receives its own UV space; the left and right sides, wheels, and treads do not share UVs. `assets/atv_uv.svg` shows the actual UV layout.

Surface color comes from the image texture, while roughness is defined as constants in the eight materials. Separate normal and ORM maps were not created. The same setup is reflected in the GLB and Unreal materials.

## Unreal Engine 5.7

1. Enable Python Editor Script Plugin and Editor Scripting Utilities, then restart the editor.
2. Keep the ZIP folder structure and run `scripts/ue57_import.py` from **Tools → Execute Python Script**.
3. The script creates the mesh, Base Color texture, and eight materials under `/Game/ATV_Trail`.

The included FBX uses the same mesh and UVs as the GLB. UE 5.7 FBX Interchange flags are changed only during import and restored in `finally`. Material slots are matched by name. The script sets sRGB Base Color, Clamp sampling, per-surface Roughness, lamp Emissive, +X forward conversion, and centimeter units. UE generates a separate lightmap UV. Default collision is basic; driving physics and suspension require follow-up work.

On rerun, assets with the same names under `/Game/ATV_Trail` are updated. Duplicate customized assets before rerunning. Other levels, project settings, and Content folders are not modified. `ue57_materials.py` is the material module loaded by the import script.

Check `ue57-validation.json` for the actual validation status and engine version.

## Sources and libraries

- Visual reference: the supplied image at `assets/reference.png`.
- Texture: newly created with the built-in ImageGen tool; no CLI/API workaround was used.
- 3D viewer: Google model-viewer 4.0.0, Apache-2.0; the vendor license is included.
- ZIP: fflate 0.8.2, MIT; the vendor license is included.
- [UE 5.7 AssetImportTask](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7)
- [UE 5.7 MaterialEditingLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7)
- [UE 5.7 FbxStaticMeshImportData](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.7)

The original brief is in `user-brief.txt`, the final response is in `final-response.md`, and model/import/measurement timing is in `execution.json`. The page displays only model-family information exposed by the session; it does not infer hidden reasoning settings.
