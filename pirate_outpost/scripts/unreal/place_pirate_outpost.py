"""Place a shared JSON layout in the CURRENT UE editor level after the import script.

No level is cleared or saved. Re-running skips this layout's tagged instances.
Set REPLACE_OWNED=True only to rebuild actors carrying this pack+layout tag.
Other actors, even with matching labels, are never touched.

The preview-only island/water are deliberately not imported by this script;
use your game's landscape/water, or manually import previews/environment/*.glb.
Target UE5.6 editor API; editor execution is not verified in this delivery.
"""
from pathlib import Path
from datetime import datetime,timezone
import json
import os
import sys

PACK_ROOT = ""  # Empty uses the location of this script.
LAYOUT = "harbor"  # "harbor" or "gallery"
REPLACE_OWNED = False
PACK_TAG = "PirateOutpost_v1"


def run(pack_root=None,layout_name=LAYOUT,replace_owned=REPLACE_OWNED):
    import unreal
    value=pack_root or PACK_ROOT or os.environ.get('PIRATE_PACK_ROOT')
    root=Path(value).expanduser().resolve() if value else Path(__file__).resolve().parents[2]
    if layout_name not in ('harbor','gallery'):raise ValueError('Layout must be harbor or gallery.')
    sys.path.insert(0,str(root/'scripts'))
    from pipeline_common import read_json,validate_layout,manifest_hash,to_unreal_transform
    manifest=read_json(root/'asset_manifest.json');layout=read_json(root/'layout'/f'{layout_name}_layout.json');validate_layout(layout,manifest)
    import_report=read_json(root/'reports/ue_import_report.json')
    if import_report.get('status')!='complete':raise RuntimeError('Finish import_pirate_outpost.py successfully before placement.')
    if import_report.get('pack')!=PACK_TAG or import_report.get('manifest_sha256')!=manifest_hash(root):raise RuntimeError('The import report belongs to another or changed asset pack. Run the import script again.')
    calibration=import_report['calibration'];assets={a['id']:a for a in manifest['assets']}
    editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);eal=unreal.EditorAssetLibrary
    tag=f'{PACK_TAG}:{layout_name}'
    meshes={}
    # Complete preflight before making ANY actor changes.
    for asset_id in {o['asset'] for o in layout['instances']}:
        info=import_report['assets'].get(asset_id,{})
        if info.get('status')=='failed' or not info.get('path'):raise RuntimeError('No successfully imported mesh for '+asset_id)
        mesh=eal.load_asset(info['path'])
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('Missing StaticMesh '+info['path'])
        if str(eal.get_metadata_tag(mesh,'PirateOutpost.Owner'))!=PACK_TAG or str(eal.get_metadata_tag(mesh,'PirateOutpost.AssetID'))!=asset_id:
            raise RuntimeError('Unowned/wrong asset at '+info['path'])
        if str(eal.get_metadata_tag(mesh,'PirateOutpost.ImportComplete'))!='1':raise RuntimeError('Import finalization is incomplete for '+asset_id)
        meshes[asset_id]=mesh
    prepared=[]
    for o in layout['instances']:
        prepared.append((o,to_unreal_transform(o['position_m'],o.get('yaw_degrees',0),o.get('scale',[1,1,1]),calibration)))
    existing={}
    owned=[]
    for actor in editor.get_all_level_actors():
        tags={str(t) for t in actor.get_editor_property('tags')}
        if tag not in tags:continue
        owned.append(actor)
        for t in tags:
            if t.startswith(tag+'::'):existing[t.split('::',1)[1]]=actor
    created=[];skipped=[]
    report={'pack':PACK_TAG,'layout':layout_name,'created':created,'skipped':skipped,'status':'running','level_saved':False}
    report_path=root/'reports'/f'ue_placement_{layout_name}.json'
    try:
        with unreal.ScopedEditorTransaction('Place Pirate Outpost '+layout_name):
            if replace_owned:
                for actor in owned:
                    if not editor.destroy_actor(actor):raise RuntimeError('Could not remove owned actor '+actor.get_actor_label())
                existing.clear()
            for o,t in prepared:
                if o['name'] in existing:skipped.append(o['name']);continue
                location=unreal.Vector(*t['position_cm']);rotation=unreal.Quat(*t['quaternion_xyzw']).rotator()
                actor=editor.spawn_actor_from_class(unreal.StaticMeshActor,location,rotation)
                if actor is None:raise RuntimeError('Could not spawn '+o['name'])
                actor.set_actor_label(o['name']);actor.set_actor_scale3d(unreal.Vector(*t['scale']))
                actor.set_folder_path('PirateOutpost/'+layout_name+'/'+assets[o['asset']]['category'])
                actor.set_editor_property('tags',[unreal.Name(tag),unreal.Name(tag+'::'+o['name'])])
                component=actor.get_editor_property('static_mesh_component');component.set_static_mesh(meshes[o['asset']]);component.set_mobility(unreal.ComponentMobility.STATIC)
                # No physics simulation is enabled, including boats/flags/static flames.
                if assets[o['asset']]['collision']=='none':component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                else:
                    component.set_collision_profile_name('BlockAll');component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
                created.append(o['name'])
        report['status']='complete'
    except Exception as exc:
        report['status']='failed';report['error']=str(exc)
        unreal.log_error('[PirateOutpost] Placement interrupted; use Undo or rerun (tagged instances are skipped). '+str(exc))
        raise
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat();report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.log(f'[PirateOutpost] {len(created)} actors created, {len(skipped)} skipped. The current level was NOT saved.')
    return report

if __name__=='__main__':run()
