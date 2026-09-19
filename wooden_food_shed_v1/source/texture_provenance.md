# Texture provenance / processing

## Design reference

The wooden outdoor food shed reference was supplied by the user in this conversation. The final model is a low-poly reinterpretation, not a scan or a claimed exact reconstruction.

## Generated artwork used

- `generated_architecture.png`: image-generated, non-tileable 1536×1024 sheet. Includes roof planks, outside boards, darker inside boards, and two braced door panels.
- `prop_sack.png`, `prop_crate.png`, `prop_stone.png`, `prop_glass.png`, `prop_pot.png`: isolated and perspective-corrected surface crops from image-generated shed artwork produced in this same conversation. The source was a rendered illustration, so small amounts of painted shading remain in these cropped surfaces.
- `prop_barrel.png`: image composite made from the generated plank artwork and generated iron-strap artwork. No procedural noise texture or runtime repeated UV sampler is used.

The generated presentation boards contained illustrative, unverified technical labels. Those labels and boards are NOT deliverables and are NOT used as evidence of geometry counts. The actual count is read from the GLB buffers and independently loaded geometry.

## UV allocation

Every source surface receives its own independently padded rectangle. No final UV overlap, stacking, mirrored sharing, texture tiling, or runtime trim repetition is used. Parts of the common material artwork are reused as input to different face patches. Distinct UV allocation does not mean a different generative image call for every small polygon.

## Material maps

BaseColor is resampled and composited from the artwork, then color-quantized and stored as 8-bit/channel RGB PNG for compatibility. Normal is a conservative local-contrast-derived relief approximation. ORM uses material labels and artwork contrast; AO is a restrained image-based crevice approximation. Neither map is a physical measurement or a high-poly sculpt bake. Emissive is black everywhere except the amber lantern faces. DirectX and OpenGL normal versions differ only by inversion of the green channel.

All final material maps are 4096×4096. Final atlas resolution is not a claim that every source patch was generated at native 4K. Mesh-derived CPU preview images are separate from generated source art.
