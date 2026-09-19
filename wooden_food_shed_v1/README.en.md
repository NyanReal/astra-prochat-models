# Wooden Food Shed — v1

[English](README.en.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

![Wooden food shed overview](previews/overview.jpg)

A low-poly wooden food shed for a top-down game, built from the supplied reference. The broad single-slope roof, heavy timber frame, open double doors, and low step define the silhouette. Board gaps, grain, hinges, rivets, and diagonal braces are primarily texture detail; the mesh keeps the large forms and shallow bevels.

The open-door and closed-door GLBs are alternative static poses. Each contains the building, doors, shelves, sacks, crates, barrel, pottery, food, and lantern in 2,952 triangles. They are not intended to be placed together.

## Specifications

| Item | Value |
|---|---|
| Format | glTF 2.0 Binary / GLB |
| Triangles | 2,952 per variant |
| GLB meshes / materials | 1 / 1 |
| Exported vertices | 6,064, including per-face UV and normal seams |
| Blender source objects | 46 |
| Unique surface UV islands | 1,556 |
| Texture atlas | 4,096 × 4,096 |
| UV density | About 222.09 px/m, proportional to surface length |
| Island padding | 6 px around each island |
| Atlas occupancy | About 72.5% of the packed rectangle |
| Bounds | About 4.53 W × 4.02 D × 3.28 H m with doors open |
| Origin | Building center on ground Z=0 |
| Coordinates | Blender Z-up, front -Y, meters; GLB glTF Y-up |

The triangle limit is checked by triangle count, not vertex count. Preview ground, lighting, and shadows are not embedded in the GLB, and no surrounding grass or terrain was added.

## Files

```text
models/wooden_food_shed.glb         # open double doors
models/wooden_food_shed_closed.glb  # closed double doors
textures/T_Shed_BaseColor.png
textures/T_Shed_Normal_GL.png       # Blender / glTF
textures/T_Shed_Normal_DX.png       # Unreal; green channel already flipped
textures/T_Shed_ORM.png              # R=AO, G=Roughness, B=Metallic
textures/T_Shed_Emissive.png        # lantern regions
blender/create_wooden_food_shed.py
unreal/import_wooden_food_shed_ue57.py
source/mesh_payload.json
previews/overview.jpg               # representative overview
validation/                          # statistics and verification reports
tools/build_asset.py                 # rebuild mesh, UV, PBR atlas, and GLB
tools/render_preview.py              # CPU preview renderer
```

## UV and texture workflow

UV0 stays within 0–1. Islands from different faces are never stacked or mirrored, and no tiling shader, repeating trim sheet, or world-coordinate pattern is used. The layout follows real surface length: broad roofs and walls receive more pixels while small hardware and bevels receive fewer. Each final face has its own padded atlas allocation, although a shared section of the generated wood source may be reused across faces.

The architecture image was created with image generation. Prop surfaces were extracted and perspective-corrected from generated images, then independently placed, resampled, and composited. Base Color is an 8-bit RGB PNG. Normal and ORM are conservative image-derived support maps rather than sculpt-baked or measured PBR maps. ORM channels are R=AO, G=Roughness, and B=Metallic. The lantern is simplified as an opaque emissive surface.

## Using the GLB

`models/wooden_food_shed.glb` contains the mesh, UVs, normals, tangents, Base Color, OpenGL normal, ORM, and Emissive images. It is self-contained and does not need external textures. Emissive strength is 2.3 through `KHR_materials_emissive_strength`; viewers that ignore the extension still retain the base emissive image.

The GLBs are combined static game meshes. They do not contain door animation or a separate roof node. Use the Blender reconstruction objects when you need adjustable door hinges or a roof cutaway.

## Blender generation

Blender 4.2 or later / 5.x is supported. Extract the complete folder structure and run `blender/create_wooden_food_shed.py` in a new file, or run:

```bash
blender --background --python blender/create_wooden_food_shed.py -- --output ./blender_output --export-glb --save-blend
```

For the closed pose:

```bash
blender --background --python blender/create_wooden_food_shed.py -- --closed --no-preview --output ./blender_output_closed --export-glb --save-blend
```

The script rebuilds from the explicit vertex, triangle, and UV data in `source/mesh_payload.json`; it does not re-import the GLB and needs no extra external Python library inside Blender. It creates the `WoodenFoodShed_v1` collection and does not delete objects in other collections. `DoorHinge_Left` and `DoorHinge_Right` are the door pivots. Hide `Shed_Roof_HideForCutaway` to inspect the interior. `--export-glb` exports a temporary merged copy while preserving the editable source.

## Unreal Engine 5.7

Enable Python Editor Script Plugin, Editor Scripting Utilities, Interchange Editor, and Interchange Framework. Run `unreal/import_wooden_food_shed_ue57.py` from the editor's Python script command. The default destination is `/Game/Generated/WoodenFoodShed_v1`.

The script imports the external PNGs, creates `M_WoodenFoodShed` and `MI_WoodenFoodShed`, and assigns the material to the StaticMesh returned by the import rather than guessing generated asset names. Open and closed variants are placed under `Meshes/Open` and `Meshes/Closed`. Base Color and Emissive use sRGB; Normal and ORM use linear data. The Normal DX map is already green-flipped, so Flip Green Channel must remain off.

After import, check the triangle count and the approximately 328 cm height. Existing assets are not overwritten when `REPLACE_EXISTING=False`. The script does not create a level actor or change level lighting.

The default `COLLISION_MODE='box'` is a simple top-down obstacle and blocks the doorway. Use custom collision or review `complex` when indoor traversal is required. Lightmap UV generation is disabled by default because the mesh has many small islands; enable `GENERATE_LIGHTMAP_UV=True` and inspect a 512px lightmap if baked lighting is needed. Nanite is disabled for this low-poly asset.

## Validation scope

The delivery checks triangle count, index validity, degenerate triangles, normals, UV range/overlap/density, GLB structure, embedded images, and independent open/closed round trips. Preview images are software renders of the delivered mesh data; `interior.png` hides only the roof for inspection.

Blender and Unreal Editor runtime execution were unavailable in the delivery environment. Python syntax and Epic's UE 5.7 API references were checked, but editor execution and material compilation are not claimed as completed. Local checks can be run with:

```bash
python validation/test_asset.py
python tools/build_asset.py
python tools/render_preview.py --view hero
```

The exact results are in `validation/verification_report.json`, `validation/test_results.txt`, and `validation/environment_versions.json`.

## Official references

- [Unreal 5.7 AssetImportTask](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7)
- [Unreal 5.7 MaterialEditingLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7)
- [Unreal 5.7 StaticMeshEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.7)
- [Unreal 5.7 Texture](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Texture?application_version=5.7)
- [Unreal 5.7 Interchange](https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine?application_version=5.7)
