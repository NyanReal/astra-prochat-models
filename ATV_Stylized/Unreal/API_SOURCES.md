# UE 5.7 API references

Checked against Epic's versioned 5.7 Python API documentation on 2026-09-18.
These references establish API names/contracts, not successful engine execution.
The Unreal editor was not available in the delivery environment.

- InterchangeManager — source creation, translator check, synchronous import, wait:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeManager?application_version=5.7
- ImportAssetParameters — automation, overrides, destination name, replace behavior:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ImportAssetParameters?application_version=5.7
- InterchangeGenericAssetsPipeline — subpipelines and transform offsets:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericAssetsPipeline?application_version=5.7
- InterchangeGenericMeshPipeline — static meshes, combination, Nanite, lightmap channels:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericMeshPipeline?application_version=5.7
- InterchangeGenericCommonMeshesProperties — imported normals, tangent rebuild, full-precision UVs:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericCommonMeshesProperties?application_version=5.7
- InterchangeGenericMaterialPipeline / TexturePipeline — disabling redundant GLB-generated assets:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericMaterialPipeline?application_version=5.7
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericTexturePipeline?application_version=5.7
- AssetImportTask — synchronous texture imports and get_objects:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7
- MaterialEditingLibrary — node creation, graph wiring, instance parameters:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7
- MaterialExpressionTextureSampleParameter2D — texture, UV index, sampler type:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialExpressionTextureSampleParameter2D?application_version=5.7
- Texture2D — Clamp address modes and texture settings:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Texture2D?application_version=5.7
- StaticMesh — material assignment, triangle count, bounds:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMesh?application_version=5.7
- StaticMeshEditorSubsystem — simplified collision:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.7
