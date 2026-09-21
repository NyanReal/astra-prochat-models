"""Read-only API preflight for UE5. Run this file directly for a diagnostic report."""
import json
import unreal


def validate_api():
    missing=[]
    methods={
        'AssetImportTask':['get_objects'],
        'EditorActorSubsystem':['spawn_actor_from_object','spawn_actor_from_class','set_selected_level_actors'],
        'LevelEditorSubsystem':['new_level','save_current_level','is_in_play_in_editor'],
        'EditorLoadingAndSavingUtils':['save_current_level'],
        'EditorAssetLibrary':['load_asset','save_loaded_asset','set_metadata_tag','get_metadata_tag','list_assets'],
        'MaterialEditingLibrary':['create_material_expression','connect_material_expressions','connect_material_property','recompile_material'],
        'StaticMesh':['get_bounding_box','set_material','get_material'],
        'EditorDialog':['show_message'],
    }
    for cls,names in methods.items():
        obj=getattr(unreal,cls,None)
        if obj is None:missing.append(cls);continue
        for name in names:
            if not hasattr(obj,name):missing.append(cls+'.'+name)
    enum_members={
        'MaterialSamplerType':['SAMPLERTYPE_COLOR','SAMPLERTYPE_NORMAL','SAMPLERTYPE_MASKS'],
        'TextureAddress':['TA_CLAMP'],
        'TextureCompressionSettings':['TC_NORMALMAP','TC_MASKS'],
        'CustomMaterialOutputType':['CMOT_FLOAT3'],
        'CameraProjectionMode':['ORTHOGRAPHIC'],
        'AutoExposureMethod':['AEM_MANUAL'],
        'AppMsgType':['YES_NO'],'AppReturnType':['YES','NO'],
    }
    for name,values in enum_members.items():
        obj=getattr(unreal,name,None)
        for value in values:
            if obj is None or not hasattr(obj,value):missing.append(name+'.'+value)
    required_pp=['auto_exposure_method','auto_exposure_apply_physical_camera_exposure','camera_iso','camera_shutter_speed','depth_of_field_fstop',
                 'auto_exposure_bias','bloom_intensity','vignette_intensity','ambient_occlusion_intensity','ambient_occlusion_radius','motion_blur_amount',
                 'depth_of_field_focal_distance','depth_of_field_scale']
    settings=unreal.PostProcessSettings()
    for name in required_pp:
        for field in (name,'override_'+name):
            try:settings.get_editor_property(field)
            except Exception:missing.append('PostProcessSettings.'+field)
    report={'engine_version':unreal.SystemLibrary.get_engine_version(),'status':'pass' if not missing else 'incompatible API',
            'missing':missing,'scope':'API existence only — not an import, shader, render or level-build test',
            'required_plugins':['Python Editor Script Plugin','Editor Scripting Utilities','Interchange glTF import']}
    if missing:raise RuntimeError('StillHere API preflight failed. Enable the required editor plugins / check your UE version. Missing: '+', '.join(missing))
    return report

if __name__=='__main__':unreal.log(json.dumps(validate_api(),indent=2))
