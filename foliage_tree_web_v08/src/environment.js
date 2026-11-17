/* v07: image-textured floor + actual rooted ribbon grass, independent of the camera.
 * The shared master wind remains the tree's uWind. No separate grass clock.
 * The GLSL function below is inserted verbatim into both production vertex passes.
 */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TreeEnvironment=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const DEFAULT_GRASS_RATIO=.65;
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
 const finite=(v,d)=>Number.isFinite(v)?v:d;
 function effectiveWind(master,ratio){return clamp(finite(master,0),0,1)*clamp(finite(ratio,DEFAULT_GRASS_RATIO),0,2);}
 function grassOffset(root,height,weight,phase,time,master,ratio){
  const strength=effectiveWind(master,ratio)*height*weight*weight*.42;
  if(strength===0)return [0,0,0];
  const flow=time*1.25+root[0]*.85+root[2]*.65;
  const sway=Math.sin(flow)+.42*Math.sin(time*2.1+phase*1.7);
  const across=.28*Math.sin(time*1.7+phase);
  return [strength*(.94*sway-.34*across),0,strength*(.34*sway+.94*across)];
 }
 const GRASS_GLSL=`
vec3 rootedGrassOffset(vec3 root,float height,float weight,float phase,float time,float master,float ratio){
 float strength=master*ratio*height*weight*weight*.42;
 float flow=time*1.25+root.x*.85+root.z*.65;
 float sway=sin(flow)+.42*sin(time*2.1+phase*1.7);
 float across=.28*sin(time*1.7+phase);
 return vec3(strength*(.94*sway-.34*across),0.,strength*(.34*sway+.94*across));
}`;
 function buildGrass(trunk){
  let seed=710826;const rnd=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
  const m={position:[],normal:[],uv:[],color:[],pivot:[],phase:[],proxyNormal:[],bunchIndex:[],indices:[]};
  // A small occupancy set from the actual low trunk mesh prevents plants in the root solid.
  const blocked=new Set(),cell=.045;
  const key=(x,z)=>Math.floor(x/cell)+','+Math.floor(z/cell);
  if(trunk&&trunk.position)for(let i=0;i<trunk.position.length;i+=3){
   const [x,y,z]=trunk.position.slice(i,i+3);
   if(y>=-.01&&y<.19)for(let dx=-1;dx<=1;dx++)for(let dz=-1;dz<=1;dz++)blocked.add(key(x+dx*cell,z+dz*cell));
  }
  const clear=(x,z)=>Math.hypot(x,z)>.39&&!blocked.has(key(x,z));
  let tufts=0,blades=0;
  const centers=[];
  // Grouped islands, not an equally spaced ring. Front openings keep roots visible.
  const islands=[[-.74,.34],[-.83,-.48],[-.22,-.80],[.51,-.71],[.87,-.18],[.65,.59],[.07,.92],[-1.16,.06],[1.20,.38]];
  for(let k=0;k<84;k++){
   let x=0,z=0,found=false;
   for(let tries=0;tries<90;tries++){
    if(k<68){const c=islands[k%islands.length],a=rnd()*Math.PI*2,r=Math.sqrt(rnd())*.26;x=c[0]+Math.cos(a)*r;z=c[1]+Math.sin(a)*r;}
    else{const a=rnd()*Math.PI*2,r=1.28+rnd()*.38;x=Math.cos(a)*r;z=Math.sin(a)*r;}
    if(clear(x,z)&&!centers.some(c=>Math.hypot(c[0]-x,c[1]-z)<.075)){found=true;break;}
   }
   if(!found)continue;
   centers.push([x,z]);const count=5+Math.floor(rnd()*4);const tuftHeight=.18+rnd()*.12;
   const phase=rnd()*Math.PI*2;
   for(let b=0;b<count;b++){
    const ang=rnd()*Math.PI*2,dx=Math.cos(ang),dz=Math.sin(ang),rad=.014+rnd()*.035;
    const rx=x+dx*rad,rz=z+dz*rad;if(!clear(rx,rz))continue;
    const h=tuftHeight*(.70+rnd()*.45),wide=.010+rnd()*.013,bend=h*(.26+rnd()*.54),base=m.position.length/3;
    const left=[-dz,0,dx],root=[rx,.004,rz];
    const tint=rnd(),tip=[.57+tint*.12,.66+tint*.10,.26+tint*.10],bottom=[.20+tint*.05,.32+tint*.07,.15+tint*.035];
    const levels=[0,.30,.61,.84];
    for(let row=0;row<levels.length;row++){
     const t=levels[row],width=wide*(1-t*.72),cx=rx+dx*bend*t*t,cy=root[1]+h*t,cz=rz+dz*bend*t*t;
     for(let side=0;side<2;side++){
      const a=side===0?-1:1;
      m.position.push(cx+left[0]*width*a,cy,cz+left[2]*width*a);
      m.normal.push(-dx*.43,.78,-dz*.43);m.uv.push(side,t);
      m.color.push(...bottom.map((v,i)=>v+(tip[i]-v)*(t*.86+.12)));
      m.pivot.push(...root);m.phase.push(phase+b*.47);m.proxyNormal.push(h,0,0);m.bunchIndex.push(tufts);
     }
    }
    m.position.push(rx+dx*bend,root[1]+h,rz+dz*bend);m.normal.push(-dx*.43,.78,-dz*.43);m.uv.push(.5,1);
    m.color.push(...tip);m.pivot.push(...root);m.phase.push(phase+b*.47);m.proxyNormal.push(h,0,0);m.bunchIndex.push(tufts);
    for(let j=0;j<3;j++){const a=base+j*2;m.indices.push(a,a+1,a+3,a,a+3,a+2);}m.indices.push(base+6,base+7,base+8);blades++;
   }
   tufts++;
  }
  m.meta={version:'07',tufts,blades,triangles:m.indices.length/3,rootHeight:.004,defaultGrassWindRatio:DEFAULT_GRASS_RATIO,
   wind:'uWind (shared with tree) * uGrassWindRatio',placement:'deterministic clustered scatter, trunk footprint exclusion',cameraFacing:false};
  return m;
 }
 return {DEFAULT_GRASS_RATIO,effectiveWind,grassOffset,GRASS_GLSL,buildGrass};
});
