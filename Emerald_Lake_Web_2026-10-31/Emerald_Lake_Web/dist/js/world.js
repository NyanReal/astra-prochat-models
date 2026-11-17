export const WATER_Y = 0.18;
export const WORLD_SIZE = 52;
export const ISLAND = {x:6.0,z:1.5,rx:2.15,rz:1.8};
export const PROP_ZONES = [
 {x:-4.3,z:8.3,rx:4.6,rz:4.7},
 {x:2.0,z:-8.0,rx:4.4,rz:3.7},
 {x:13.7,z:-9.3,rx:4.6,rz:3.8},
 {x:-2.0,z:-14.5,rx:3.6,rz:3.2},
 {x:-13.6,z:-10.4,rx:3.2,rz:2.0}
];
export const STREAM = [
 {x:-15.5,z:-19.0,y:3.18,w:2.2},
 {x:-14.4,z:-15.6,y:2.30,w:2.1},
 {x:-13.1,z:-12.1,y:1.38,w:2.2},
 {x:-10.7,z:-7.1,y:WATER_Y,w:2.5}
];
export function rng(seed=1234){return ()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return ((t^t>>>14)>>>0)/4294967296;};}
export function shorelineScale(a){return 1+.083*Math.sin(3*a+.6)+.052*Math.sin(7*a-1.1)+.021*Math.sin(11*a);}
export function lakePoint(a,offset=0){const r=shorelineScale(a);return {x:Math.cos(a)*(13.4*r+offset),z:Math.sin(a)*(9.7*r+offset)};}
export function lakeMetric(x,z){const a=Math.atan2(z/9.7,x/13.4);return Math.sqrt((x/13.4)**2+(z/9.7)**2)/shorelineScale(a);}
export function isIsland(x,z,pad=0){return ((x-ISLAND.x)/(ISLAND.rx+pad))**2+((z-ISLAND.z)/(ISLAND.rz+pad))**2<1;}
export function isWater(x,z){return lakeMetric(x,z)<1&&!isIsland(x,z);}
export function streamDistance(x,z){let best=1e5;for(let i=0;i<STREAM.length-1;i++){let a=STREAM[i],b=STREAM[i+1],dx=b.x-a.x,dz=b.z-a.z,t=Math.max(0,Math.min(1,((x-a.x)*dx+(z-a.z)*dz)/(dx*dx+dz*dz)));best=Math.min(best,Math.hypot(x-a.x-dx*t,z-a.z-dz*t));}return best;}
export function landHeight(x,z){if(isIsland(x,z,.1))return 1.0+.16*Math.sin(x*1.9)*Math.cos(z*2);let back=Math.max(0,(-z-8)/15);return 1.10+back*1.9+.13*Math.sin(x*.42)*Math.cos(z*.38)+.08*Math.sin(x*.9+z*.8);}
export function pathDistance(x,z){const ring=Math.abs(lakeMetric(x,z)-1.34)*11.5;const north=Math.abs(z+13.6);const south=Math.abs(x+3.6)+Math.max(0,7-z);return Math.min(ring,north<2&&x>-10&&x<18?north:99,south);}
export function inPropZone(x,z,pad=0){return PROP_ZONES.some(p=>Math.abs(x-p.x)<p.rx+pad&&Math.abs(z-p.z)<p.rz+pad);}
export function foliageAllowed(x,z){return (!isWater(x,z)||isIsland(x,z))&&streamDistance(x,z)>2.05&&!inPropZone(x,z)&&pathDistance(x,z)>1.15;}
// Match the low bank and carved creek when positioning small plants.
export function surfaceHeight(x,z){
 if(isIsland(x,z))return .25+.83*Math.sqrt(Math.max(0,1-((x-ISLAND.x)/ISLAND.rx)**2-((z-ISLAND.z)/ISLAND.rz)**2));
 const smooth=(v,a,b)=>{const t=Math.max(0,Math.min(1,(v-a)/(b-a)));return t*t*(3-2*t);};
 let h=landHeight(x,z),best=Infinity,streamY=0;
 for(let i=0;i<STREAM.length-1;i++){const a=STREAM[i],b=STREAM[i+1],dx=b.x-a.x,dz=b.z-a.z,t=Math.max(0,Math.min(1,((x-a.x)*dx+(z-a.z)*dz)/(dx*dx+dz*dz)));const d=Math.hypot(x-a.x-dx*t,z-a.z-dz*t);if(d<best){best=d;streamY=a.y+(b.y-a.y)*t;}}
 if(best<2.5){const s=smooth(best,1.05,2.5);h=Math.min(h,streamY-.15)*(1-s)+h*s;}
 if(lakeMetric(x,z)>=1){const a=Math.atan2(z/9.7,x/13.4),q=lakePoint(a),dist=Math.hypot(x-q.x,z-q.z),s=smooth(dist,0,2.2);h=(WATER_Y+.12)*(1-s)+h*s;}
 return h;
}
