# Sweet Potato Game Assets — Astra Pro Rebuild

[한국어](README.ko.md)

A fresh rebuild of two stylized game props: a sparse wild sweet-potato patch and a cultivated three-row plot. New reference images, new image-derived textures, and new mesh-generation code; no meshes, textures, or scripts were reused from the earlier delivered pack.

| Model | Main triangles | LOD1 triangles | Dimensions (X × Y × Z, meters) |
|---|---:|---:|---|
| Wild patch | 6,368 | 2,258 | 2.18 × 0.53 × 1.79 |
| Cultivated field | 22,868 | 7,600 | 3.16 × 0.74 × 3.66 |

## Contents

`models/`: two main GLBs and two separate LOD1 GLBs. `textures/`: all base-color maps. `reference/`: newly generated visual references and the cropped leaf source. `preview/`: renders made by reimporting the actual GLBs. `source/`: geometry and texture preparation scripts. `validation/`: measured statistics and automated tests.

The wild patch has two uneven crowns, five creeping runners and 36 sweet-potato leaves. The field has three raised beds, four crowns per bed, and 168 leaves. LOD switching logic is not included.

## Materials and coordinates

Meters, Y-up, origin at ground center. Textures are embedded. Mesh nodes are grouped by material: soil, foliage, stems, and stone (wild only). Remove the soil node when only vegetation is desired.

Foliage gets a 1024×1024 atlas. Soil is 256×256; stems and stone are 128×128. The leaf atlas contains recolored variants of one freshly generated leaf crop with nearest-color edge dilation. These are image-derived, resampled textures, not four independently generated native-1024 leaves. Source crop coordinates and processing are recorded in `source/texture_provenance.json`.

Only base color and scalar roughness/metallic are used. Metallic is zero, roughness ranges from 0.91 to 1.0. No normal map, AO map or alpha card. Leaf silhouettes are actual curved geometry with double-sided opaque materials.

No rig, wind animation, collider, or engine prefab is included. Confirm that your importer preserves the double-sided setting on foliage. Previews use studio lighting and screen-space ambient shading, which are not baked into the GLBs.

## Rebuild

```bash
python source/prepare_textures.py
python source/build_assets.py
python validation/test_assets.py
python source/render_previews.py
```

Python dependencies: numpy, Pillow, scipy, opencv-python, trimesh; vtk for rendering. Seeds are fixed. `source/package_assets.py` additionally uses a locally installed Noto Sans CJK font for the Korean comparison card; font files are not distributed.

Automated checks cover coordinates, normals, UVs, degenerate triangles, embedded textures, size ceiling, material properties and LOD reduction. Files were reimported and rendered. No Blender/Unity/Unreal editor import test or official Khronos validator run is claimed.

## Guidelines

User-specified source: https://github.com/octopus7/model-workflow

The reference-image-generation and reference-image-modeling guidelines were checked for this rebuild: soft natural forms, no unrelated decorative motifs, importance-weighted UV allocation, generated-image textures, a 1024-pixel ceiling, no normal maps, and GLB/ZIP delivery.
