# Emerald Lake revision 02

User request: improve truck details, visible white shore ripples, and make creek elevation drops natural rather than box-shaped. Existing reference palette, scene layout, website and ZIP delivery remain the goal.

## Concrete changes

1. Replace raw box truck forms with softened cab/hood, framed sloped glazing, wheel arches/tread/hubs, functional small parts, textured bed/cargo straps.
2. Replace barely visible shore lines with broken textured mesh foam, clustered at rock-water contacts, gaps and variable widths.
3. Replace uniform rectangular creek slabs and vertical fronts with curved, unequal cascade strips, meandering pools, rock lips and spread-out landing foam.
4. Upgrade the actual-model offline renderer to preserve RGBA texture alpha so foam is represented faithfully.

## Validation

- Source import closure and finite geometry/instance data.
- Actual model close-up renders of truck, creek and shore.
- Check especially: glass/body intersections, circular wheel visibility, rectangular foam cards, exposed planar water edges, sediment blocking the mouth, artificial continuous white outlines.
- Update all four fallback images from matching source hashes; transparent features must appear in actual renders.
- Preserve the existing Site identity and owner-private audience; replace the existing ZIP Library item with optimistic version guard.

## Browser environment

The previous cloud browser had WebGL disabled. Use the existing standalone EGL model renderer for visual checks and report any remaining browser-specific verification limit honestly. No alternate browser or security setting changes.
