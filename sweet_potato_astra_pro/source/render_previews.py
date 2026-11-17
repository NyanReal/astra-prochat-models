"""Render the EXPORTED and REIMPORTED GLB meshes, not the concept illustrations."""
from pathlib import Path
import argparse
import numpy as np
from PIL import Image
import trimesh
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
ROOT=Path(__file__).resolve().parents[1]

def actor_from_mesh(mesh):
    p=vtk.vtkPoints();p.SetData(numpy_to_vtk(np.array(mesh.vertices,dtype=np.float32),deep=True))
    f=np.column_stack([np.full(len(mesh.faces),3),mesh.faces]).astype(np.int64)
    c=vtk.vtkCellArray();c.ImportLegacyFormat(numpy_to_vtkIdTypeArray(f.ravel(),deep=True))
    pd=vtk.vtkPolyData();pd.SetPoints(p);pd.SetPolys(c)
    normals=numpy_to_vtk(np.array(mesh.vertex_normals,dtype=np.float32),deep=True);normals.SetName('Normals');pd.GetPointData().SetNormals(normals)
    uv=numpy_to_vtk(np.array(mesh.visual.uv,dtype=np.float32),deep=True);uv.SetName('TCoords');pd.GetPointData().SetTCoords(uv)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(pd);mapper.ScalarVisibilityOff()
    actor=vtk.vtkActor();actor.SetMapper(mapper)
    mat=mesh.visual.material
    arr=np.asarray(mat.baseColorTexture.convert('RGB'))
    img=vtk.vtkImageData();img.SetDimensions(arr.shape[1],arr.shape[0],1)
    img.GetPointData().SetScalars(numpy_to_vtk(np.flipud(arr).copy().reshape(-1,3),deep=True,array_type=vtk.VTK_UNSIGNED_CHAR))
    texture=vtk.vtkTexture();texture.SetInputData(img);texture.InterpolateOn();texture.RepeatOn();texture.MipmapOn()
    actor.SetTexture(texture)
    prop=actor.GetProperty();prop.SetInterpolationToPhong();prop.SetAmbient(.35);prop.SetDiffuse(.68);prop.SetSpecular(.035);prop.SetSpecularPower(8)
    # Double-sided lamina surfaces; opaque silhouette geometry needs no alpha.
    prop.BackfaceCullingOff()
    return actor

def render(name,view='hero',size=(1400,1100),wire=False):
    scene=trimesh.load(ROOT/'models'/f'{name}.glb',force='scene',process=False)
    renderer=vtk.vtkRenderer();renderer.SetBackground(.966,.953,.918);renderer.AutomaticLightCreationOff()
    for mesh in scene.geometry.values():
        a=actor_from_mesh(mesh)
        if wire:
            a.SetTexture(None);a.GetProperty().SetColor(.54,.63,.55);a.GetProperty().EdgeVisibilityOn();a.GetProperty().SetEdgeColor(.19,.26,.21);a.GetProperty().SetLineWidth(.65)
        renderer.AddActor(a)
    bounds=scene.bounds;center=(bounds[0]+bounds[1])*.5;extent=np.max(bounds[1]-bounds[0])
    plane=vtk.vtkPlaneSource();plane.SetOrigin(-30,-.008,-30);plane.SetPoint1(30,-.008,-30);plane.SetPoint2(-30,-.008,30)
    mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(plane.GetOutputPort());floor=vtk.vtkActor();floor.SetMapper(mp);floor.GetProperty().SetColor(.966,.953,.918);floor.GetProperty().SetAmbient(.75);floor.GetProperty().SetDiffuse(.25);renderer.AddActor(floor)
    for pos,intensity,color in [((-4,7,5),.82,(1.,.96,.89)),((5,4,0),.36,(.91,.96,1)),((0,5,-5),.36,(1.,1.,.91))]:
        light=vtk.vtkLight();light.SetLightTypeToSceneLight();light.SetPosition(*np.array(pos)*extent);light.SetFocalPoint(*center);light.SetPositional(False);light.SetColor(*color);light.SetIntensity(intensity);renderer.AddLight(light)
    cam=renderer.GetActiveCamera();target=np.array([0,center[1]*.65,0])
    if view=='top':
        cam.SetPosition(0,extent*4,0);cam.SetViewUp(0,0,-1);scale=extent*.58
    elif view=='side':
        cam.SetPosition(extent*4,extent*.75,extent*1.8);cam.SetViewUp(0,1,0);scale=extent*.50
    else:
        cam.SetPosition(*(np.array([1.14,1.05,1.40])*extent));cam.SetViewUp(0,1,0);scale=extent*(.48 if 'wild' in name else .58)
    cam.SetFocalPoint(*target);cam.ParallelProjectionOn();cam.SetParallelScale(scale)
    win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(*size);win.SetMultiSamples(0);win.AddRenderer(renderer)
    # SSAO is a viewport-only effect, not a normal/AO map in the exported materials.
    basic=vtk.vtkRenderStepsPass();ao=vtk.vtkSSAOPass();ao.SetDelegatePass(basic);ao.SetRadius(extent*.065);ao.SetBias(.002*extent);ao.SetKernelSize(128);ao.BlurOn();renderer.SetPass(ao)
    renderer.ResetCameraClippingRange();win.Render()
    grab=vtk.vtkWindowToImageFilter();grab.SetInput(win);grab.ReadFrontBufferOff();grab.SetInputBufferTypeToRGB();grab.Update()
    filename=ROOT/'preview'/f'{name}_{"wire" if wire else view}.png'
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(filename));writer.SetInputConnection(grab.GetOutputPort());writer.Write();win.Finalize()
    print(filename)
    return filename
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',default='all');p.add_argument('--view',default='hero');p.add_argument('--wire',action='store_true');a=p.parse_args()
    for name in (['wild_sweet_potato','cultivated_sweet_potato'] if a.name=='all' else [a.name]):render(name,a.view,wire=a.wire)
