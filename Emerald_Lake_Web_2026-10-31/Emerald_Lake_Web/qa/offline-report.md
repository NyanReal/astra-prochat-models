# Actual-scene offline rendering

The preview JPEGs are rasterizations of the application's real Three.js scene, exported by running the actual `createTerrain`, `createProps`, `createVegetation`, and `createLife` constructors with high quality and animation time zero. They are not generated replacement artwork and are not screenshots from a browser.

## Why an offline renderer was used

The cloud preview browser reports its graphics vendor as `Disabled`, preventing creation of the site's WebGL context. A separate standalone EGL context in Python successfully reports **llvmpipe (LLVM 20.1.2, 256 bits)** with OpenGL 4.5. This is Mesa's software rasterizer, used directly without a browser.

## Reproduction

From the project directory, install the optional offline rendering dependency with `npm install --no-save @napi-rs/canvas`, or use the supplied runtime module directory in `CODEX_PRIMARY_RUNTIME_NODE_MODULES`. This dependency is not needed by the website itself:

```sh
node --experimental-loader ./tools/three-loader.mjs tools/export-scene.mjs
python -m pip install --target /tmp/lake-gl-deps moderngl glcontext
PYTHONPATH=/tmp/lake-gl-deps python tools/render_scene.py
```

`tools/three-loader.mjs` resolves the real locally vendored Three.js module and addon imports. `tools/export-scene.mjs` supplies a real canvas implementation for the scene's painted needle cards and texture-atlas cropping. It exports indexed geometry, vertex colors, UVs, terrain path weights, materials, real PNG textures, world transforms, and instance colors. Every numeric geometry/transform value is checked for finiteness. Constructors execute unchanged. The compact binary and JSON manifest are in `qa/offline/scene-data/`; the manifest includes source SHA-256 hashes, exact camera configurations parsed from `main.js`, bounds, and scene statistics.

`tools/render_scene.py` uploads the exported meshes to standalone OpenGL and renders all four application camera presets at 1536 × 1024 with four-sample antialiasing. A 4096 × 4096 directional shadow map uses the application's light position and orthographic shadow frustum. Output files are `dist/assets/previews/overview.jpg`, `dock.jpg`, `stream.jpg`, and `camp.jpg`.

## Fidelity and limitations

- All mesh geometry, placements, per-instance colors, texture maps, and camera presets come from the actual app. No substitute scene or generated image is used.
- Lake and creek ShaderMaterial vertex and fragment programs are exported per material and adapted to standalone GLSL. Their wave, pebble, glint, directional flow and cascade aeration formulas are preserved at the selected deterministic animation time.
- Terrain uses the same vertex path-weight blend between grass and ground atlas tiles, including the exact dark-olive grass mix and path RGB tint in its `onBeforeCompile` map block. That compiled block is also retained in the manifest. PNG UV orientation matches Three.js `flipY`; color textures are decoded from sRGB before shading.
- The exact Three.js ACES input/output matrices, rational tone-map fit, exposure 1.216, and sRGB output transform are used.
- Standard materials use a standalone GGX/Lambert approximation with the application's hemispheric ambient and directional illumination. It is visually comparable but is not the full Three.js renderer: small differences in BRDF energy compensation, shadow filtering, edge treatment, and output can occur.
- Line primitives, RGBA texture alpha, material opacity, texture transforms and transparent depth-write behavior are preserved. The broken shoreline foam uses actual textured mesh geometry, rather than omitted line effects.
- The floating point sprites, vegetation shader wind displacement, and atmospheric fog are omitted. The primary modeled forms are retained; preview images are static and are labeled as such in the WebGL-unavailable UI.
- A successful offline render validates scene construction and visible geometry; it does not establish that the browser's WebGL renderer ran. Browser rendering remains limited by that environment's disabled graphics context.

Machine-readable render dimensions, device, bounds, geometry counts, and scene statistics are in `qa/offline/render-report.json`.

## Final verification

Every JavaScript source in `dist/js` is hashed automatically; the renderer refuses stale scene exports. The four page previews are 1536 × 1024. Revision 02 also includes 1200 × 900 truck, stream and shoreline detail views in `qa/revision-02/`. Current geometry counts and source hashes are recorded in the machine-readable render reports. See `qa/revision-02/render-report.md` for the revised renderer checks and remaining fidelity limits.
