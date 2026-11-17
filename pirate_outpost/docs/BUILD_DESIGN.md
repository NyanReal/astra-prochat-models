# Pirate Outpost — build design

## Scope
Reconstruct the objects visible in the two approved AI-generated reference sheets as individual static GLB assets. Shared objects appear once in the library and are instanced in the demonstration layout. Include reusable dock modules, watchtower, buildings, defensive structures, supplies, camp equipment, harbor machinery and dressing props.

## Production decisions
- Soft bevels and readable silhouettes, not primitive blockout proxies.
- Geometry built explicitly with a deterministic Python mesh generator; no image-to-3D service is being used.
- 1 unit = 1 metre. Source authoring basis is right-handed X-right / Y-back / Z-up; fronts face -Y. GLB is exported in the standard Y-up basis.
- Ground props pivot at their base; dock modules pivot at deck height. Floor grid = 2 metres.
- Shared 1024-square albedo atlas, using material pixels and the skull emblem extracted from the supplied generated images. A second 1024-square image packs only roughness and metallic (unused red channel is white). No normal map.
- Trim/atlas UVs deliberately overlap. Fine wood grain and flags have larger atlas regions; hidden/simple surfaces share smaller regions. UV0 is NOT a unique lightmap UV.
- Static flames and opaque lantern windows are illustrative meshes, not effects or interactive lighting.
- No rigging, animation, interior gameplay, automated LOD chain or Nanite guarantee.

## Alternatives considered
Whole-sheet image-to-mesh would entangle unrelated objects. Per-object service generation would require an available external 3D service. Explicit mesh construction provides separable modules, exact pivots, consistent dimensions and reproducible source.

## Execution plan
1. Define a catalog and write output-contract tests (red).
2. Extract atlas pixels with traceable crop provenance; implement tested mesh primitives and standard GLB writing.
3. Build every catalog asset with actual geometry, bevels, seams, structural braces, lashings and material zoning.
4. Render exported geometry with the available VTK offscreen renderer; review representative close-ups and the assembled harbor. Correct visible defects.
5. Provide a Blender importer/linked-instance preview scene script and a UE5 editor import/layout script. Do not overwrite existing user scenes or assets without explicit switches.
6. Validate GLB buffers, texture sizes, UVs, normals, finite coordinates, counts, extents, layout references and script syntax. No general watertight/manifold certification is claimed. Package evidence and limitations.

## Environment boundary
Blender and Unreal Editor are not installed in this execution environment. Direct Blender download was attempted but network access from the execution container is unavailable. GLBs and rendered previews will be executed/inspected locally; Blender/Unreal scripts can be syntax-checked and their pure logic tested here, but not honestly claimed as editor-runtime-tested.
