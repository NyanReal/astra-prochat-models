# Browser verification

Preview served through the supported Sites preview at http://terminal.local:4173/.

## Observed environment limitation

Browser console reported GL_VENDOR=Disabled and GL_RENDERER=Disabled at WebGL context creation. No alternative browser or changed browser/network security setting was used. Browser-only live GPU shader execution, orbit gestures, live sunlight and live animation remain unverified in this environment.

## Confirmed through visible browser UI

- Page loads the explicitly labeled RENDER PREVIEW fallback from actual offline model renders.
- Main image naturally resolves to 1536×1024 pixels; local image file loads successfully.
- View controls select the dock, waterfall and camp images with correct active states.
- Settings panel expands and closes; live-only settings are disabled in still mode with an explanatory description.
- Full-scene viewing hides page overlays; the restore control restores them.
- The reference image panel displays the user-provided image and closes.
- The reset control returns to overview.

The static fallback is a progressive enhancement for devices with unavailable WebGL, not evidence that live 3D ran in this browser. The implementation and geometry construction are independently checked by source validation and offline EGL rendering.
