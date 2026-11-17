# Emerald Lake Implementation Plan

> **For agentic workers:** use isolated module ownership and the interface contract in `dist/js/world.js`.

**Goal:** Deliver a textured, animated, lush 3D fishing lake based on the attached illustration, as a working static website and downloadable ZIP.

**Architecture:** Three.js orthographic scene; independent landscape, vegetation, and prop modules return `{group, update(time, delta), stats}`. Main owns scene assembly, camera, lighting, UI, and QA. All runtime files live in `dist/`.

**Tech Stack:** locally vendored Three.js ES modules, HTML/CSS, JavaScript, Python static launcher and packaging.

**Spec:** `docs/superpowers/specs/2026-10-31-emerald-lake-design.md`

## Global constraints

- Y up, water Y=0.18, lake centered (0,0), land around 1.0, shared world.js shoreline and height functions.
- Imports from `three` and `three/addons/` through local importmap; no remote runtime requests.
- Own one module per worker; do not edit another worker's source, main.js, world.js, or vendor files.
- Static meshes cast/receive appropriate shadows; use instancing/merging for dense repeated detail.
- Do not place giant cones as finished trees: sculpt layered irregular branch silhouettes with textured foliage.
- User-facing deliverable ZIP, plus published private viewer; existing attachment remains unchanged.

## Review focus

1. Scene initial framing on desktop and narrow mobile should keep lake and main structures visible.
2. Shader compile errors or external module references must not yield an empty canvas.
3. Touch and mouse orbit/zoom, reset, presets, pause, and quality controls work.
4. Water/land and docks/ground heights line up; no detached vegetation or terrain holes.
5. ZIP starts with a documented local server and includes all texture/vendor files.

## Task 1: Shared world and renderer (owner)

- [x] Create world.js shared shoreline, path, seeded randomness and occupancy contract.
- [x] Vendor three and required addons locally; record version/license.
- [x] Implement renderer, warm/cool lighting, orthographic camera, subtle fog and composition.
- [x] Build restrained full-screen UI and working controls, loading/error feedback.

## Task 2: Terrain and water (terrain worker)

Create `dist/js/terrain.js`, export `createTerrain(ctx)` returning `{group, update, stats}`. ctx has THREE-independent `textures` object and `quality` string. Import shared world helpers. Build textured terrain, shore cliffs, creek cascades, shallow/deep lake, island, submerged stones, water ripples/foam/caustics. Syntax-check and describe integration.

## Task 3: Vegetation (vegetation worker)

Create `dist/js/vegetation.js`, export `createVegetation(ctx)` with same result. Create detailed low-triangle reusable fir trees, bushes, fern fronds, grasses, reeds, white/yellow flowers, lily pads. Use world helpers and avoid prop occupancy. Paint/extract reusable texture cards if helpful; no hidden network dependencies. Syntax-check.

## Task 4: Props (props worker)

Create `dist/js/props.js`, export `createProps(ctx)` with same result. Create plank docks/pilings/steps, fishing chairs/rods/bobbers, crates, supply chests, olive utility truck, striped camp shelter, rail fences and dark warm-lit markers. Parent transforms and material UVs coherent; batch static geometry. Syntax-check.

## Task 5: Integration, verification, delivery (owner + independent review)

- [x] Load generated material texture atlas, tune final lighting and initial view against reference.
- [x] Verify actual model render via standalone EGL, and fallback page interactions through sites-preview/CUA. Browser WebGL is disabled; live renderer verification is explicitly limited.
- [x] Run source/asset closure and finite-geometry checks; address observed defects.
- [ ] Package self-contained ZIP with README and launchers; verify archive.
- [ ] Save ZIP, publish exact source through Sites, return actual URL and file link.
