// UE Custom node body. Output Type = CMOT Float3.
// INPUTS (all scalar unless noted):
// RootWebMeters: float3(UV1.x, UV3.x, UV1.y)
// BladeHeightMeters: UV2.y, HeightWeight: UV0.y, Phase: UV2.x
// SharedWindTime: same seconds-valued wind clock used by the tree
// MasterWind: same shared 0..1 scalar used by the tree
// GrassRatio: Material Instance scalar, 0..2, default 0.65
// Output: local UE-centimetre offset. Chosen axis map: UE(X,Y,Z)=100*Web(X,Z,Y).
// For rotated instances transform this local offset into world space before WPO.
// The static GLB does not contain runtime shader animation. Use this explicitly.
float weight=saturate(HeightWeight);
float strength=saturate(MasterWind)*clamp(GrassRatio,0.0,2.0)
               *BladeHeightMeters*weight*weight*0.42;
float flow=SharedWindTime*1.25+RootWebMeters.x*0.85+RootWebMeters.z*0.65;
float sway=sin(flow)+0.42*sin(SharedWindTime*2.1+Phase*1.7);
float across=0.28*sin(SharedWindTime*1.7+Phase);
float offsetX=strength*(0.94*sway-0.34*across);
float offsetZ=strength*(0.34*sway+0.94*across);
return float3(offsetX,offsetZ,0.0)*100.0;
