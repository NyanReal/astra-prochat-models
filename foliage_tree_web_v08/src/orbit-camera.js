/* View-only orbit controls. No geometry, proxy normal, colour or light is changed.
 * The same pure camera maths is tested in Node and used by the shipped HTML. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.TreeOrbit=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const DEFAULT_ELEVATION=Math.atan2(1,12)*180/Math.PI;
  const RADIUS=Math.hypot(12,1);
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const number=(v,fallback)=>typeof v==='number'&&Number.isFinite(v)?v:fallback;
  function sanitize(s){
    const a=number(s.angle,0);
    return {...s,
      angle:((a+180)%360+360)%360-180,
      elevation:clamp(number(s.elevation,DEFAULT_ELEVATION),-89.5,89.5),
      zoom:clamp(number(s.zoom,1),.35,8),
      pan:[0,1,2].map(i=>clamp(number(s.pan&&s.pan[i],0),-25,25))
    };
  }
  function camera(raw,width,height){
    const s=sanitize(raw),aspect=Math.max(1,width)/Math.max(1,height);
    let halfHeight=2.63;
    if(aspect<1.05)halfHeight=Math.max(halfHeight,2.50/aspect);
    halfHeight/=s.zoom;
    const yaw=s.angle*Math.PI/180,pitch=s.elevation*Math.PI/180;
    const sy=Math.sin(yaw),cy=Math.cos(yaw),sp=Math.sin(pitch),cp=Math.cos(pitch);
    // Analytic basis avoids a cross(worldUp,view) singularity at the poles.
    const back=[sy*cp,sp,cy*cp],right=[cy,0,-sy],up=[-sy*sp,cp,-cy*sp];
    const target=s.pan.map((p,i)=>p+(i===1?(s.mode==='trunk'?1.95:2.16):0));
    const eye=target.map((t,i)=>t+back[i]*RADIUS);
    return {eye,target,right,up,back,halfHeight,aspect};
  }
  function pan(s,dx,dy,width,height){
    const clean=sanitize(s),c=camera(clean,width,height),units=2*c.halfHeight/Math.max(1,height);
    return {pan:clean.pan.map((p,i)=>p+units*(-dx*c.right[i]+dy*c.up[i]))};
  }
  function home(){return {angle:0,elevation:DEFAULT_ELEVATION,zoom:1,pan:[0,0,0]};}
  function attach(canvas,getState,update){
    const pointers=new Map(),listeners=[];
    const on=(name,fn,opts)=>{canvas.addEventListener(name,fn,opts);listeners.push([name,fn,opts]);};
    const size=()=>[Math.max(1,canvas.clientWidth),Math.max(1,canvas.clientHeight)];
    const point=e=>({x:e.clientX,y:e.clientY,type:e.pointerType,button:e.button});
    const gesture=()=>{const p=Array.from(pointers.values());return {
      x:(p[0].x+p[1].x)/2,y:(p[0].y+p[1].y)/2,
      distance:Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y)
    };};
    on('contextmenu',e=>e.preventDefault());
    on('pointerdown',e=>{
      if(e.pointerType==='mouse'&&![0,1,2].includes(e.button))return;
      e.preventDefault();pointers.set(e.pointerId,point(e));
      canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging');
    });
    on('pointermove',e=>{
      const prev=pointers.get(e.pointerId);if(!prev)return;
      e.preventDefault();const before=pointers.size>=2?gesture():null;
      pointers.set(e.pointerId,{...point(e),button:prev.button});
      const s=getState(),[w,h]=size();
      if(before){
        const after=gesture();
        const next=sanitize({...s,zoom:s.zoom*(before.distance>2?after.distance/before.distance:1)});
        update({zoom:next.zoom,...pan(next,after.x-before.x,after.y-before.y,w,h)});
      }else if(prev.button===1||prev.button===2||e.shiftKey){
        update(pan(s,e.clientX-prev.x,e.clientY-prev.y,w,h));
      }else{
        update({angle:s.angle-(e.clientX-prev.x)*.28,elevation:s.elevation+(e.clientY-prev.y)*.24});
      }
    });
    const end=e=>{
      pointers.delete(e.pointerId);
      if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);
      if(!pointers.size)canvas.classList.remove('dragging');
    };
    on('pointerup',end);on('pointercancel',end);on('lostpointercapture',end);
    on('wheel',e=>{
      e.preventDefault();const s=getState();
      const units=e.deltaMode===1?16:e.deltaMode===2?canvas.clientHeight:1;
      update({zoom:s.zoom*Math.exp(clamp(-e.deltaY*units*.0012,-2,2))});
    },{passive:false});
    on('dblclick',e=>{e.preventDefault();update(home());});
    const blur=()=>{pointers.clear();canvas.classList.remove('dragging');};
    window.addEventListener('blur',blur);
    return ()=>{listeners.forEach(([n,f,o])=>canvas.removeEventListener(n,f,o));window.removeEventListener('blur',blur);blur();};
  }
  return {DEFAULT_ELEVATION,sanitize,camera,pan,home,attach};
});
