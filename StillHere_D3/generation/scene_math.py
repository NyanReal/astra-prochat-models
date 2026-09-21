"""Shared mathematical camera contract; canonical right-handed metre/Z-up space."""
import math
import numpy as np

ELEVATION=48.0
WIDTH=36.0
RESOLUTION=(1536,1024)
S=math.sin(math.radians(ELEVATION));C=math.cos(math.radians(ELEVATION))
CAMERA={
    'projection':'orthographic','resolution':list(RESOLUTION),'ortho_width_m':WIDTH,
    'position_m':[0.,-46.,46.*math.tan(math.radians(ELEVATION))],
    'target_m':[0.,0.,0.],'up':[0.,0.,1.],
    'elevation_degrees':ELEVATION,'clip_start_m':.05,'clip_end_m':250.,
    'fit_note':'Artist-fitted orthographic reconstruction from a single image; original camera intrinsics are unknown.'
}

def pixel_to_world(x,y,z=0.):
    height=WIDTH*RESOLUTION[1]/RESOLUTION[0]
    sx=(float(x)/RESOLUTION[0]-.5)*WIDTH
    sy=(.5-float(y)/RESOLUTION[1])*height
    return np.array([sx,(sy-C*z)/S,float(z)])

def world_to_pixel(p):
    x,y,z=np.asarray(p);height=WIDTH*RESOLUTION[1]/RESOLUTION[0]
    return np.array([(x/WIDTH+.5)*RESOLUTION[0],(.5-(S*y+C*z)/height)*RESOLUTION[1]])

def terrain_height(x,y):
    return 1.55+.015*math.sin(x*.55)+.010*math.sin(y*.65)

def ground_at_pixel(x,y,offset=0.):
    p=pixel_to_world(x,y,1.55)
    return pixel_to_world(x,y,terrain_height(p[0],p[1])+offset)

def matrix_quaternion(m):
    """Right-handed rotation matrix -> quaternion [x,y,z,w]."""
    m=np.asarray(m,float);t=np.trace(m)
    if t>0:
        s=math.sqrt(t+1.)*2;return np.array([(m[2,1]-m[1,2])/s,(m[0,2]-m[2,0])/s,(m[1,0]-m[0,1])/s,.25*s])
    i=int(np.argmax(np.diag(m)))
    if i==0:
        s=math.sqrt(1.+m[0,0]-m[1,1]-m[2,2])*2;return np.array([.25*s,(m[0,1]+m[1,0])/s,(m[0,2]+m[2,0])/s,(m[2,1]-m[1,2])/s])
    if i==1:
        s=math.sqrt(1.+m[1,1]-m[0,0]-m[2,2])*2;return np.array([(m[0,1]+m[1,0])/s,.25*s,(m[1,2]+m[2,1])/s,(m[0,2]-m[2,0])/s])
    s=math.sqrt(1.+m[2,2]-m[0,0]-m[1,1])*2;return np.array([(m[0,2]+m[2,0])/s,(m[1,2]+m[2,1])/s,.25*s,(m[1,0]-m[0,1])/s])
