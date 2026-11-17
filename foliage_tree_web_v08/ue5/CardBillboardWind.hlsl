// v06 porting reference. Not compiled/tested in Unreal Editor here.
// ProxyNormal and baked vertex colour DO NOT enter this geometry transform.
// LocalOffsetXYMetres is (RestPositionLocal - PivotLocal).xy in SOURCE Y-up
// coordinates, including the original card's random roll. Preserve it separately
// before an importer changes axes; do not derive it from the atlas UV.
// PivotWorld, RestPositionWorld and all directions below are in UE world space.
float3 TreeCardBillboardWindOffset(
    float3 RestPositionWorld, float3 PivotWorld, float2 LocalOffsetXYMetres,
    float3 CameraRightWorld, float3 CameraUpWorld,
    float3 RestPlaneRightWorld, float3 RestPlaneUpWorld,
    float3 SwayDirectionWorld, float Phase, float BunchId,
    float TimeSeconds, float WindStrength, float CardScale,
    float WorldUnitsPerMetre, float InstanceUniformScale,
    bool StableShadowProxy)
{
    float angle = WindStrength * 0.095 *
        (sin(TimeSeconds * 1.25 + Phase) +
         0.42 * sin(TimeSeconds * 2.1 + Phase * 1.7));
    float c = cos(angle), s = sin(angle);
    float2 q = LocalOffsetXYMetres *
        (WorldUnitsPerMetre * InstanceUniformScale * CardScale);
    float2 rotated = float2(c*q.x - s*q.y, s*q.x + c*q.y);
    float3 right = normalize(StableShadowProxy ? RestPlaneRightWorld : CameraRightWorld);
    float3 up = normalize(StableShadowProxy ? RestPlaneUpWorld : CameraUpWorld);
    float sway = 0.023 * WorldUnitsPerMetre * InstanceUniformScale * WindStrength *
        sin(TimeSeconds * 0.82 + BunchId * 1.39);
    float3 displayPosition = PivotWorld + right*rotated.x + up*rotated.y +
        SwayDirectionWorld*sway;
    return displayPosition - RestPositionWorld; // Connect to World Position Offset.
}
