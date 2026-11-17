"""Render the exported GLB geometry using VTK, not a generated concept image.
Optional rebuild dependency: vtk, numpy, Pillow. Uses EGL offscreen rendering.
"""
from pathlib import Path
import json, math, argparse, os
os.environ.setdefault('VTK_DEFAULT_OPENGL_WINDOW','vtkEGLRenderWindow')
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from meshcore import read_glb, read_accessor, GLTF_BASIS
ROOT=Path(__file__).resolve().parents[1]

def texture(path):
 r=vtk.vtkPNGReader();r.SetFileName(str(path));r.Update()
 t=vtk.vtkTexture();t.SetInputConnection(r.GetOutputPort());t.InterpolateOn();t.RepeatOff();t.EdgeClampOn()
 return t

def mesh_actor(path,position=(0,0,0),yaw=0,scale=(1,1,1),textures=None):
 doc,bb=read_glb(path);p=doc['meshes'][0]['primitives'][0]
 v=read_accessor(doc,bb,p['attributes']['POSITION']).astype(float)@GLTF_BASIS
 n=read_accessor(doc,bb,p['attributes']['NORMAL']).astype(float)@GLTF_BASIS
 uv=read_accessor(doc,bb,p['attributes']['TEXCOORD_0']).copy();uv[:,1]=1-uv[:,1]
 f=read_accessor(doc,bb,p['indices']).reshape(-1,3)
 poly=vtk.vtkPolyData();points=vtk.vtkPoints();points.SetData(numpy_to_vtk(v,deep=True));poly.SetPoints(points)
 cells=vtk.vtkCellArray();c=np.column_stack([np.full(len(f),3,dtype=np.int64),f.astype(np.int64)]).ravel();cells.SetCells(len(f),numpy_to_vtkIdTypeArray(c,deep=True));poly.SetPolys(cells)
 nn=numpy_to_vtk(n,deep=True);nn.SetName('Normals');poly.GetPointData().SetNormals(nn)
 tc=numpy_to_vtk(uv,deep=True);tc.SetName('TCoords');poly.GetPointData().SetTCoords(tc)
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(poly);mapper.ScalarVisibilityOff()
 actor=vtk.vtkActor();actor.SetMapper(mapper);actor.SetPosition(*position);actor.SetOrientation(0,0,yaw);actor.SetScale(*scale)
 prop=actor.GetProperty();prop.SetInterpolationToPhong();prop.SetAmbient(.28);prop.SetDiffuse(.76);prop.SetSpecular(.12);prop.SetSpecularPower(30)
 actor.SetTexture((textures or {}) .get('base') or texture(ROOT/'textures'/'T_Pirate_BaseColor.png'))
 prop.BackfaceCullingOff()
 return actor

def make_floor(z=-.025,size=200):
 p=vtk.vtkPlaneSource();p.SetOrigin(-size/2,-size/2,z);p.SetPoint1(size/2,-size/2,z);p.SetPoint2(-size/2,size/2,z);p.Update()
 m=vtk.vtkPolyDataMapper();m.SetInputConnection(p.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(.8,.765,.68);a.GetProperty().SetAmbient(.48);a.GetProperty().SetDiffuse(.5)
 return a

def setup(width=1400,height=1400):
 renderer=vtk.vtkRenderer();renderer.SetBackground(.93,.9,.84);renderer.SetBackground2(.98,.96,.91);renderer.GradientBackgroundOn()
 window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.AddRenderer(renderer);window.SetSize(width,height);window.SetMultiSamples(4);window.SetAlphaBitPlanes(1)
 renderer.SetUseDepthPeeling(0)
 renderer.AutomaticLightCreationOff()
 # Large-scale directional key/fill. SSAO adds actual mesh contact depth.
 for pos,col,intensity in [((-8,-10,16),(1,.91,.79),1.1),((7,-4,9),(.77,.87,1),.52),((0,8,12),(1,.98,.9),.6)]:
  l=vtk.vtkLight();l.SetLightTypeToSceneLight();l.SetPosition(*pos);l.SetFocalPoint(0,0,1);l.SetColor(*col);l.SetIntensity(intensity);l.SetPositional(False);renderer.AddLight(l)
 # SSAO is supported by the EGL renderer in this runtime.
 basic=vtk.vtkRenderStepsPass();ssao=vtk.vtkSSAOPass();ssao.SetDelegatePass(basic);ssao.SetRadius(.45);ssao.SetBias(.012);ssao.SetKernelSize(64);ssao.BlurOn();renderer.SetPass(ssao)
 return renderer,window,ssao

def save_render(window,path):
 window.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(window);f.ReadFrontBufferOff();f.SetInputBufferTypeToRGB();f.Update()
 w=vtk.vtkPNGWriter();w.SetFileName(str(path));w.SetInputConnection(f.GetOutputPort());w.Write()

def single(path,out,azimuth=-48,elevation=23,width=1300,height=1300):
 r,w,ss=setup(width,height);a=mesh_actor(path);r.AddActor(a);bounds=np.array(a.GetBounds()).reshape(3,2)
 mn=bounds[:,0];mx=bounds[:,1];center=(mn+mx)/2
 floor=make_floor(mn[2]-.018);r.AddActor(floor)
 size=max(np.ptp(bounds,axis=1));ss.SetRadius(min(.5,size*.12))
 cam=r.GetActiveCamera();az=math.radians(azimuth);el=math.radians(elevation)
 direction=np.array([math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)])
 # Negative Y is the authored front. Camera 3/4 view exposes front and right side.
 cam.SetFocalPoint(*center);cam.SetPosition(*(center+direction*max(size*3,3)));cam.SetViewUp(0,0,1);cam.ParallelProjectionOn()
 # Frame projected extents exactly, leaving a modest border.
 right=np.cross(direction,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,direction)
 corners=np.array([[x,y,z] for x in [mn[0],mx[0]] for y in [mn[1],mx[1]] for z in [mn[2],mx[2]]]);rc=corners-center
 spanx=np.ptp(rc@right);spany=np.ptp(rc@up);cam.SetParallelScale(max(spany/2,spanx/(2*width/height))*1.13)
 r.ResetCameraClippingRange();save_render(w,out);w.Finalize()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('glb');p.add_argument('output');p.add_argument('--az',type=float,default=-48);p.add_argument('--el',type=float,default=24);p.add_argument('--size',type=int,default=1200);a=p.parse_args()
 single(Path(a.glb),Path(a.output),a.az,a.el,a.size,a.size)
