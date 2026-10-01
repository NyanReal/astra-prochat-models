"""Inspect actual exported triangles. VTK contacts are not rigid-body simulation.
Reports cockpit-to-new-leg contacts at 181 sampled times, including interpolated
half-frame poses. Separately checks authored hydraulic parts against leg armor.
"""
from pathlib import Path
import sys,json
from collections import defaultdict
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
import vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray,vtk_to_numpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from glb_io import read_glb,accessor,world_matrices


def poly(points,faces):
    p=vtk.vtkPoints();p.SetData(numpy_to_vtk(np.asarray(points,'float64'),deep=True));c=vtk.vtkCellArray()
    arr=np.c_[np.full(len(faces),3),faces].astype(np.int64);c.ImportLegacyFormat(numpy_to_vtkIdTypeArray(arr.ravel(),deep=True))
    m=vtk.vtkPolyData();m.SetPoints(p);m.SetPolys(c);return m

def matrix(m):
    a=vtk.vtkMatrix4x4()
    for i in range(4):
        for j in range(4):a.SetElement(i,j,float(m[i,j]))
    return a

def combine(parts):
    ps=[];fs=[];names=[];off=0
    for name,p,f in parts:
        ps.append(p);fs.append(f.astype(np.int64)+off);off+=len(p);names.extend([name]*len(f))
    return poly(np.concatenate(ps),np.concatenate(fs)),names

def collider(a,b):
    c=vtk.vtkCollisionDetectionFilter();c.SetInputData(0,a);c.SetInputData(1,b)
    c.SetMatrix(0,matrix(np.eye(4)));c.SetMatrix(1,matrix(np.eye(4)))
    c.SetBoxTolerance(0);c.SetCellTolerance(1e-10);c.SetNumberOfCellsPerNode(2);c.SetCollisionModeToAllContacts();return c

def sample(g,b,anim,t):
    out={}
    for ch in anim['channels']:
        sm=anim['samplers'][ch['sampler']];ts=accessor(g,b,sm['input']).ravel();values=accessor(g,b,sm['output'])
        hi=min(int(np.searchsorted(ts,t,side='right')),len(ts)-1);lo=max(0,hi-1)
        path=ch['target']['path']
        if t>=float(ts[-1]):val=values[-1]
        elif t<=float(ts[0]):val=values[0]
        else:
            f=(t-ts[lo])/(ts[hi]-ts[lo]);a=values[lo];v=values[hi]
            if path=='rotation':
                if np.dot(a,v)<0:v=-v
                dot=np.clip(np.dot(a,v),-1,1)
                if dot>.9995:val=a*(1-f)+v*f;val=val/np.linalg.norm(val)
                else:
                    th=np.arccos(dot);val=(np.sin((1-f)*th)*a+np.sin(f*th)*v)/np.sin(th)
            else:val=a*(1-f)+v*f
        out[(ch['target']['node'],path)]=val
    return out

