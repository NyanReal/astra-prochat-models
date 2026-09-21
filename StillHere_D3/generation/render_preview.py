"""Render the actual exported mesh data offscreen with VTK (not image generation).

Usage: python generation/render_preview.py --width 1536 --output previews/scene.png
VTK is a preview-only dependency. Blender/UE reconstruction does not need VTK.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,math,time
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray
from PIL import Image
from mesh_core import ROOT,euler_matrix


def polydata(data):
    p=vtk.vtkPolyData();points=vtk.vtkPoints();points.SetData(numpy_to_vtk(np.ascontiguousarray(data['vertices']),deep=True));p.SetPoints(points)
    faces=np.asarray(data['faces'],dtype=np.int64);packed=np.column_stack((np.full(len(faces),3),faces)).ravel()
    cells=vtk.vtkCellArray();cells.ImportLegacyFormat(numpy_to_vtkIdTypeArray(packed,deep=True));p.SetPolys(cells)
    uv=np.asarray(data['uv']).copy();uv[:,1]=1-uv[:,1]
    tc=numpy_to_vtk(np.ascontiguousarray(uv),deep=True);tc.SetName('UVMap');p.GetPointData().SetTCoords(tc)
    normals=numpy_to_vtk(np.ascontiguousarray(data['normals']),deep=True);normals.SetName('Normals');p.GetPointData().SetNormals(normals)
    return p


def load_mapper(asset,clay=False):
    data=np.load(ROOT/asset['mesh_data']);mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(polydata(data));mapper.ScalarVisibilityOff()
    texture=None
    if not clay:
        reader=vtk.vtkPNGReader();reader.SetFileName(str(ROOT/asset['base_color']));reader.Update()
        texture=vtk.vtkTexture();texture.SetInputConnection(reader.GetOutputPort());texture.InterpolateOn();texture.MipmapOn();texture.RepeatOff();texture.EdgeClampOn()
        texture.SetUseSRGBColorSpace(False)
    return mapper,texture


def render(width=1536,output='previews/scene.png',clay=False,asset_only=None,shadows=True,ssao=True):
    start=time.time();catalog=json.loads((ROOT/'data/assets.json').read_text());assets={a['id']:a for a in catalog['assets']}
    scene=json.loads((ROOT/'data/scene.json').read_text());cam=scene['camera']
    renderer=vtk.vtkRenderer();renderer.SetBackground(.14,.20,.18);renderer.SetAmbient(.86,.94,1.0);renderer.AutomaticLightCreationOff();renderer.TwoSidedLightingOn()
    renderer.SetUseShadows(shadows);renderer.SetUseSSAO(ssao);renderer.SetSSAORadius(.48);renderer.SetSSAOBias(.014);renderer.SetSSAOKernelSize(32);renderer.SetSSAOBlur(True)
    renderer.SetUseFXAA(True)
    mappers={};instances=scene['instances']
    if asset_only:instances=[{'asset_id':asset_only,'position_m':[0,0,0],'rotation_euler_xyz_deg':[0,0,0],'scale':[1,1,1]}]
    for i,inst in enumerate(instances):
        aid=inst['asset_id'];asset=assets[aid]
        if aid not in mappers:mappers[aid]=load_mapper(asset,clay)
        mapper,texture=mappers[aid];actor=vtk.vtkActor();actor.SetMapper(mapper)
        if texture:actor.SetTexture(texture)
        prop=actor.GetProperty();prop.SetColor(.78,.80,.76 if clay else 1.0)
        if not clay:prop.SetColor(1,1,1)
        prop.SetAmbient(.40);prop.SetDiffuse(.76);prop.SetSpecular(.015);prop.SetSpecularPower(18);prop.SetInterpolationToPhong();prop.BackfaceCullingOff()
        if asset['category'] in ('trees','shrubs','vines','groundcover'):
            prop.SetAmbient(.52);prop.SetDiffuse(.64);prop.SetSpecular(0.)
        if asset['surface_type'] in ('water','waterfall'):
            prop.SetAmbient(.54);prop.SetDiffuse(.54);prop.SetSpecular(.42);prop.SetSpecularPower(90)
        if asset['surface_type']=='waterfall':prop.SetAmbient(.88);prop.SetDiffuse(.30);prop.SetSpecular(.10)
        if asset['surface_type']=='foam':prop.SetAmbient(.78);prop.SetDiffuse(.25);prop.SetSpecular(0.)
        r=euler_matrix(*inst['rotation_euler_xyz_deg'])@np.diag(inst['scale']);mat=vtk.vtkMatrix4x4()
        for row in range(3):
            for col in range(3):mat.SetElement(row,col,float(r[row,col]))
            mat.SetElement(row,3,float(inst['position_m'][row]))
        actor.SetUserMatrix(mat);renderer.AddActor(actor)
    sun=vtk.vtkLight();sun.SetLightTypeToSceneLight();sun.SetPosition(-24,-34,52);sun.SetFocalPoint(0,0,0);sun.SetColor(1.,.96,.83);sun.SetIntensity(1.16);sun.SetPositional(False);renderer.AddLight(sun)
    fill=vtk.vtkLight();fill.SetLightTypeToSceneLight();fill.SetPosition(30,12,32);fill.SetFocalPoint(0,0,1);fill.SetColor(.71,.85,1.);fill.SetIntensity(.22);fill.SetPositional(False);renderer.AddLight(fill)
    camera=renderer.GetActiveCamera();camera.ParallelProjectionOn();camera.SetPosition(*cam['position_m']);camera.SetFocalPoint(*cam['target_m']);camera.SetViewUp(0,0,1)
    height=round(width*cam['resolution'][1]/cam['resolution'][0]);camera.SetParallelScale(cam['ortho_width_m']*height/width/2);camera.SetClippingRange(.05,250)
    if asset_only:
        lo,hi=np.array(assets[asset_only]['bounds_m']);centre=(lo+hi)/2;diameter=max(np.linalg.norm(hi-lo),1.)
        camera.SetPosition(*(centre+np.array([1.1,-1.5,1.1])*diameter));camera.SetFocalPoint(*centre);camera.SetParallelScale(diameter*.48)
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(width,height);window.SetMultiSamples(0);window.AddRenderer(renderer)
    print(f'Rendering {len(instances)} instances / {len(mappers)} meshes / {width}x{height} shadows={shadows} ssao={ssao}',flush=True)
    window.Render();print('GPU render done',round(time.time()-start,2),flush=True)
    capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.SetInputBufferTypeToRGB();capture.ReadFrontBufferOff();capture.Update()
    path=ROOT/output;path.parent.mkdir(parents=True,exist_ok=True);writer=vtk.vtkPNGWriter();writer.SetFileName(str(path));writer.SetInputConnection(capture.GetOutputPort());writer.Write()
    # Write a machine-readable receipt: this preview is based on the real mesh manifest.
    receipt={'renderer':f'VTK {vtk.vtkVersion.GetVTKVersion()} offscreen OpenGL','source_scene':'data/scene.json','output':output,'resolution':[width,height],
             'instances_rendered':len(instances),'unique_assets_rendered':len(mappers),'shadows':shadows,'ssao':ssao,'clay':clay,'elapsed_seconds':round(time.time()-start,2),
             'is_blender_render':False,'is_unreal_render':False,'is_generated_illustration':False}
    path.with_suffix('.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');window.Finalize();print('Saved',path,flush=True)
    return path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--width',type=int,default=1536);p.add_argument('--output',default='previews/scene.png');p.add_argument('--clay',action='store_true');p.add_argument('--asset');p.add_argument('--no-shadows',action='store_true');p.add_argument('--no-ssao',action='store_true');a=p.parse_args()
    render(a.width,a.output,a.clay,a.asset,not a.no_shadows,not a.no_ssao)
