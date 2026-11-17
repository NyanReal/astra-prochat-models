// Function source for porting; not compiled in Unreal here.
// All positions and basis vectors must be in one common world coordinate system.
float3 TreeCardWindOffset(
    float3 RestPosition, float3 Pivot, float3 Right, float3 Up,
    float3 SwayDirection, float Phase, float BunchId,
    float TimeSeconds, float WindStrength, float CardScale,
    float WorldUnitsPerMetre)
{
    float theta = WindStrength * 0.095 *
        (sin(TimeSeconds * 1.25 + Phase) +
         0.42 * sin(TimeSeconds * 2.1 + Phase * 1.7));
    float c = cos(theta), s = sin(theta);
    float3 q = (RestPosition - Pivot) * CardScale;
    float x = dot(q, Right), y = dot(q, Up);
    float3 perpendicular = q - Right*x - Up*y;
    float3 rotated = Right*(c*x-s*y) + Up*(s*x+c*y) + perpendicular;
    float groupSway = 0.023 * WorldUnitsPerMetre * WindStrength *
        sin(TimeSeconds * 0.82 + BunchId * 1.39);
    return Pivot + rotated + SwayDirection*groupSway - RestPosition;
}
