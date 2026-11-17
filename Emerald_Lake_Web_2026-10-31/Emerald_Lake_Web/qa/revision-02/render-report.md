# Revision 02 authentic geometry render verification

The images are renders of the current scene constructors and the actual exported meshes, materials, textures, instance colors and world transforms. They are not image-generated replacements. The four normal preview cameras are parsed from `dist/js/main.js`; detailed views are QA cameras only and do not change the live page.

## Renderer changes

- PNG textures now remain RGBA throughout export/upload. Source foam texture has alpha values from 0 to 242; transparent regions remain transparent rather than becoming solid rectangular cards.
- Material opacity, alpha test, depth testing, depth writing, side selection, normal/additive/subtractive/multiply blending and back-to-front transparent object ordering are respected.
- Each texture keeps its own identity, color space, repeat, offset, center, rotation and UV matrix. Regular repeat versus clamp wrapping is applied on both axes.
- Instance colors remain active independently of material vertex colors, matching Three.js instancing behavior.
- Line geometry is exported and rendered, including shore-rock cracks. One Points object (ambient particles) remains omitted.
- Custom float vertex attributes are exported directly and bound to the actual shader; the creek uses the source `aeration` attribute without approximation.
- Custom shader programs are keyed per material, retain the source vertex and fragment logic, and use exported uniform values. Materials with different fragments cannot accidentally share a program because of a guessed object-name category. Unsupported shader chunks/uniform values fail explicitly.
- The exporter accepts `--time`; updates are applied at that deterministic time. Source hashes discover every JavaScript source in `dist/js`; rendering refuses stale source hashes.

## Outputs and verification

The standard previews are `dist/assets/previews/overview.jpg`, `dock.jpg`, `stream.jpg`, and `camp.jpg` at 1536×1024. Detailed views are `qa/revision-02/truck_detail.jpg`, `stream_detail.jpg`, and `shore_detail.jpg` at 1200×900. All use 4× multisampling and the actual scene geometry through standalone EGL OpenGL (Mesa llvmpipe).

Syntax checks passed for the exporter and renderer. Source construction exported 61 objects, 314,573 triangles, and finite geometry and transforms. The detailed truck image resolves grille, lights, mirrors, door seams, wheel bolts, tire tread, wooden bed planks, cargo and weathering. Foam alpha blends without rectangular backgrounds.

## Fidelity limits

This is an independent geometry renderer because browser WebGL is unavailable in the provided cloud browser. Standard material illumination and shadows approximate the page's Three.js lighting; these images are not claimed to be pixel-identical browser screenshots. Source ShaderMaterial logic and painted texture colors are retained. Ambient Points particles and vertex wind applied through `onBeforeCompile` are not reproduced. Alpha-tested shadow silhouettes are not currently needed by the scene's textured materials (all source alphaTest values are zero).

## Reproduction

```sh
node --experimental-loader ./tools/three-loader.mjs tools/export-scene.mjs --time 0
python tools/render_scene.py --views overview,dock,stream,camp
python tools/render_scene.py --views truck_detail,stream_detail,shore_detail --output qa/revision-02 --width 1200 --height 900
```

The renderer's JSON reports include exact source hashes, timestamps via the scene manifest, scene bounds, counts and deterministic time.

## Final source review and animation check

The final stream uses the actual connected creek ShaderMaterial, including its texture, moving streaks, source aeration attribute, and independent uniforms. Stream-detail framing includes all three drops. Final refinement adds a rounded spring enclosed by seven headwater rocks, irregular moving white strands over turquoise fall faces, softened stream edges and an alpha-faded mouth dipping into the lake. The pale fall sheet and dotted exposed ledges are absent. Shore-detail rendering resolves exposed white foam segments around the island and shore rocks. The truck-wheel rock intersection has been removed in source.

Additional deterministic time-1 renders are saved in `qa/revision-02/time-1/stream_detail.jpg` and `shore_detail.jpg`. Their pixels differ from the time-0 images, confirming that source updates and shader uniforms advance. The main previews remain time 0.

Final foam refinement follows individual island boulders with variable arcs and gaps, replacing the evenly spaced ellipse.

Final animation image comparison:

- `stream_detail`: 13.80% of pixels change; mean absolute channel difference 1.951.
- `shore_detail`: 35.87% of pixels change; mean absolute channel difference 0.858.

Final source SHA-256 hashes:

- `life.js`: `c27e9758fcaf41c47644887e96a95e1e1bb3454520e1ac05148cf9b3be2787c7`
- `main.js`: `75a4080e2cf002c540ac9829b685c53de6b53c48abc1c1dc18408f2aba0ef775`
- `props.js`: `afed94fd2853b596e8f4b1e0e5667fa932d3ffdf268689551bdfa577a62a645b`
- `terrain.js`: `6fc6073ea7ed209fea6ae9f7f707d2eac422171edd1c402e128aa2c38de3eba7`
- `vegetation.js`: `3a4a5a9bfae859a40f1268abf7da326933c88eeb981e6a3a68811d3a0c4a418e`
- `world.js`: `7a6c5df46d78e8f1f94f89941f6de50ef932775cffd4480795b50ca20dc7ce4d`

Final source export: 61 objects; 314573 triangles; 174 rocks. The four-preset report has also been synchronized to `qa/offline/render-report.json`.

Stale-export rejection was verified against a temporary manifest with an intentionally incorrect terrain hash. The renderer rejected it before creating images. Current-source hashes all match.
