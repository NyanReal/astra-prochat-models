# Sources and provenance

## User-requested guidelines

```text
https://github.com/octopus7/model-workflow
https://raw.githubusercontent.com/octopus7/model-workflow/main/docs/reference-image-generation.md
https://raw.githubusercontent.com/octopus7/model-workflow/main/docs/reference-image-modeling.md
```

## Texture pixels

The two reference images supplied/generated in the conversation are retained under `references/`. Base-color atlas pixels are extracted/recolored from those images; material data masks are authored programmatically. Exact crops and source hashes: `textures/provenance.json`. No additional stock texture library, third-party 3D asset or scraped artwork was bundled.

## Official implementation references

```text
https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python
https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeManager?application_version=5.6
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ImportAssetParameters?application_version=5.6
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericAssetsPipeline?application_version=5.6
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericMeshPipeline?application_version=5.6
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericCommonMeshesProperties?application_version=5.6
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.6
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMesh?application_version=5.6
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/BodySetup?application_version=5.6
https://docs.blender.org/api/current/bpy.ops.import_scene.html
https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
```

The editor scripts were written for this pack. They are not copied from an unverified community importer. Documentation review is not equivalent to executing the scripts in an editor. No Blender or Unreal binaries, font files, or third-party package source are redistributed.
