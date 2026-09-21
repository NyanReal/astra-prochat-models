"""Build reusable GLB meshes and unique atlases: python generation/build_assets.py [--only ID ...]."""
from pathlib import Path
import argparse,json,time
from mesh_core import ROOT,Mesh,bake,source_images
import environment as env
import vegetation as veg
import architecture as arc
import props

def constructors():
    jobs=[]
    def put(name,fn,density=72,max_size=2048):jobs.append((name,fn,density,max_size))
    for i,s in enumerate('ABCD'):put('Ground_Meadow_'+s,lambda i=i,s=s:env.ground('Ground_Meadow_'+s,110+i),56,1024)
    for i,s in enumerate('AB'):put('Ground_Dirt_'+s,lambda i=i,s=s:env.ground('Ground_Dirt_'+s,120+i,'dirt',radius=2.05,depth=.15),72,1024)
    for i,s in enumerate('ABC'):put('Transition_Moss_'+s,lambda i=i,s=s:env.ground('Transition_Moss_'+s,130+i,'moss',radius=1.3,transition=True),88,512)
    for i,s in enumerate('AB'):put('Transition_Soil_'+s,lambda i=i,s=s:env.ground('Transition_Soil_'+s,140+i,'dirt',radius=1.15,transition=True),88,512)
    for i,s in enumerate('ABC'):put('Paving_Broken_'+s,lambda i=i,s=s:env.paving('Paving_Broken_'+s,150+i,3 if i<2 else 1),112,512)
    for i,s in enumerate('ABC'):
        put('Rock_Bank_'+s,lambda i=i,s=s:env.rock('Rock_Bank_'+s,160+i,(1.25+i*.14,1.05,1.55),True),72,1024)
        put('Rock_River_'+s,lambda i=i,s=s:env.rock('Rock_River_'+s,170+i,(1.10,.88,.96+i*.21),True),80,1024)
    for i,s in enumerate('AB'):put('Cliff_Block_'+s,lambda i=i,s=s:env.cliff_block('Cliff_Block_'+s,180+i),56,1024)
    for i,s in enumerate('ABC'):put('Tank_Arc_'+s,lambda i=i,s=s:arc.tank_arc('Tank_Arc_'+s,210+i),80,2048)
    for fn in [arc.tank_marking,arc.catwalk,arc.stairs,arc.bunker,arc.banner,arc.bridge_deck,arc.bridge_pier,arc.ruined_wall,arc.nature_sign,arc.pylon]:
        obj=fn();put(obj.name,lambda obj=obj:obj,88,2048)
    put('Railing_3m',arc.railing,96,512)
    put('Railing_Broken',lambda:arc.railing('Railing_Broken',True),96,512)
    for fn in [props.truck,props.crate,props.tarp_stack,props.drum,props.log_bridge,props.traveller,props.gull]:
        obj=fn();put(obj.name,lambda obj=obj:obj,96,2048)
    put('Crate_Open',lambda:props.crate('Crate_Open',True),96,1024)
    for i,s in enumerate('ABC'):put('Broadleaf_'+s,lambda i=i,s=s:veg.broadleaf('Broadleaf_'+s,310+i,i),72,2048)
    for i,s in enumerate('AB'):put('Pine_'+s,lambda i=i,s=s:veg.pine('Pine_'+s,320+i,i),64,2048)
    for i,s in enumerate('ABC'):put('Bush_'+s,lambda i=i,s=s:veg.bush('Bush_'+s,330+i,i),80,1024)
    for i,s in enumerate('AB'):put('Grass_'+s,lambda i=i,s=s:veg.grass('Grass_'+s,340+i,i),96,512)
    put('Flowers_White',lambda:veg.flowers('Flowers_White',350),96,1024)
    put('Flowers_Pink',lambda:veg.flowers('Flowers_Pink',351,True),96,1024)
    put('Fern',lambda:veg.fern('Fern',352),96,512)
    put('Ivy_Long',lambda:veg.ivy('Ivy_Long',360,3.3),88,1024)
    put('Ivy_Short',lambda:veg.ivy('Ivy_Short',361,1.6),88,1024)
    put('Rock_Hero_Island',env.hero_island,96,1024)
    put('Foam_Generated_Eddies',env.generated_foam,144,1024)
    put('River_Main',env.river_main,72,2048)
    put('Tank_Interior_Floor',lambda:env.ground('Tank_Interior_Floor',500,'tank_dark',radius=6.75,depth=.1),48,1024)
    put('River_Surface_A',lambda:env.water_strip('River_Surface_A',410),88,1024)
    put('River_Surface_B',lambda:env.water_strip('River_Surface_B',411),88,1024)
    put('Waterfall',lambda:env.waterfall('Waterfall'),104,1024)
    put('Foam_Ring',lambda:env.foam_ring('Foam_Ring',412),112,1024)
    put('Foam_Stream',lambda:env.foam_stream('Foam_Stream',413),112,1024)
    for axis in range(3):
        name='Axis_Probe_'+'XYZ'[axis]
        def probe(axis=axis,name=name):
            m=Mesh(name,'calibration');center=[0,0,0];center[axis]=1.
            m.box(center,(.12,.12,.12),'paint');return m
        put(name,probe,24,128)
    return jobs

def main():
    p=argparse.ArgumentParser();p.add_argument('--only',nargs='*');args=p.parse_args()
    for d in ['assets/glb','assets/textures','data/meshes','data/uv','source/processed_surfaces']:(ROOT/d).mkdir(parents=True,exist_ok=True)
    for name,img in source_images().items():img.save(ROOT/f'source/processed_surfaces/{name}.png')
    manifest_path=ROOT/'data/assets.json'
    existing={a['id']:a for a in json.loads(manifest_path.read_text()).get('assets',[])} if manifest_path.exists() else {}
    jobs=constructors();t0=time.time()
    for i,(name,fn,density,max_size) in enumerate(jobs):
        if args.only and name not in args.only:continue
        print(f'[{i+1:02d}/{len(jobs):02d}] {name}',flush=True)
        meta,_,_=bake(fn(),density,max_size);existing[name]=meta
        print(f'  {meta["triangles"]:,} triangles; {meta["charts"]} charts; {meta["atlas_size"]} square; {meta["effective_texel_density_px_m"]} px/m',flush=True)
        manifest_path.write_text(json.dumps({'schema_version':1,'coordinate_system':'RH_Z_UP_METRES','assets':list(existing.values())},indent=2,ensure_ascii=False),encoding='utf8')
    print(f'Assets ready: {len(existing)}; seconds: {time.time()-t0:.1f}',flush=True)

if __name__=='__main__':main()
