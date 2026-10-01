/* Inspection transforms only. These do not pretend to be exported arm animation. */
'use strict';
class ArmModuleRenderer extends HopperRenderer {
  constructor(canvas){super(canvas);this.mode='modules';this.explode=0;this.armArmor=true;this.onlyInterface=false;}
  async load(buffer){await super.load(buffer);this.armRoots={};for(const s of ['L','R'])this.armRoots[s]=this.nodes.find(n=>n.name===`Arm_${s}_M1_Root`);this.setMode('modules');return this;}
  setMode(mode){this.mode=mode;this.onlyInterface=false;this.playing=false;this.setExplode(this.explode);this.camera(mode==='mounted'?'assembled':mode==='modules'?'modules':'single');this.onchange?.();}
  setExplode(amount){const previous=this.explode;this.explode=Math.max(0,Math.min(.60,Number(amount)||0));if(!this.armRoots)return;
    for(const [s,n] of Object.entries(this.armRoots)){
      const sign=s==='R'?1:-1,m=HOPPER_SOCKET_SPEC.sockets[s].scene_mount;
      n.r=[...m.rotation_xyzw];n.s=[1,1,1];
      if(this.mode==='mounted')n.t=[m.translation[0]+sign*this.explode,m.translation[1],m.translation[2]];
      else n.t=[sign*(this.mode==='modules'?.125:.0)+sign*this.explode,.8847,0];
    }
    if(this.mode==='modules')this.distance=Math.max(this.distance,3.05+2.8*this.explode);
    else if(this.mode==='mounted')this.distance=Math.max(this.distance,5.55+1.6*this.explode);
    else this.target[0]+=(this.mode==='R'?1:-1)*(this.explode-previous);
    this.updateWorld();this.render();this.onchange?.();
  }
  isVisible(pr){const m=/^Arm_([LR])_/.exec(pr.owner||'');
    if(m){if(this.mode==='L'||this.mode==='R'){if(m[1]!==this.mode)return false;}if(this.onlyInterface&&!/01_Interface_Cup/.test(pr.owner))return false;
      if(!this.armArmor&&/Armor$/.test(pr.owner))return false;return true;}
    if(this.mode!=='mounted'||this.onlyInterface)return false;return super.isVisible(pr);
  }
  camera(name){if(!this.ready)return;
    const sign=this.mode==='L'?-1:1;
    const p={modules:[.54,.18,3.05,[0,.552,.045]],single:[.63*sign,.20,2.32,[sign*.245,.552,.045]],
      assembled:[.56,.20,5.55,[0,1.05,.0]],front:[0,.12,this.mode==='mounted'?5.35:3.0,[0,this.mode==='mounted'?1.05:.55,.02]],
      back:[3.66,.22,this.mode==='mounted'?5.55:3.0,[0,this.mode==='mounted'?1.05:.55,.0]],
      socket:[-1.15,.29,1.20,[.04,.865,0]],elbow:[1.14,.14,1.22,[.32,.500,.040]],
      hand:[.53,.30,1.10,[.295,.120,.165]],fit:[1.03,.22,2.2,[.665,1.48,-.03]]}[name];
    if(!p)return super.camera(name);[this.az,this.el,this.distance,this.target]=[p[0],p[1],p[2],[...p[3]]];if(['modules','front','back','assembled','single'].includes(name)){if(this.mode==='modules')this.distance+=2.8*this.explode;else if(this.mode==='mounted')this.distance+=1.6*this.explode;else this.target[0]+=sign*this.explode;}this.render();
  }
}
window.ArmModuleRenderer=ArmModuleRenderer;
