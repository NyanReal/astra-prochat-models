from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_editor_entry_points_exist():
    assert (ROOT/'blender'/'build_scene.py').is_file()
    assert (ROOT/'ue5'/'build_level.py').is_file()

def test_calibration_module_exists():
    assert (ROOT/'ue5'/'stillhere_transform_math.py').is_file()

def test_calibrated_transforms_match_geometry_for_axis_and_unit_variants():
    import sys,numpy as np
    sys.path.insert(0,str(ROOT/'ue5'))
    from stillhere_transform_math import calibrate,convert_instance,quaternion_matrix,rotation,WORLD_BASIS
    rec={'id':'test','position_m':[2.,-3.,1.7],'rotation_euler_xyz_deg':[11.,-19.,37.],'scale':[.7,1.3,2.1]}
    variants=[np.diag([100,-100,100]),np.array([[0,100,0],[100,0,0],[0,0,100]]),np.eye(3),np.array([[0,0,-1],[1,0,0],[0,1,0]])]
    p=np.array([.4,-.7,1.1]);W=np.array(WORLD_BASIS)
    for raw in variants:
        cal=calibrate(raw.T.tolist());converted=convert_instance(rec,cal)
        R=np.array(quaternion_matrix(converted['quaternion_xyzw']))
        actual=R@np.diag(converted['scale'])@raw@p+converted['position_cm']
        expected=W@(np.array(rotation(rec['rotation_euler_xyz_deg']))@np.diag(rec['scale'])@p+rec['position_m'])
        assert np.allclose(actual,expected,atol=1e-7)
        assert np.isclose(np.linalg.det(R),1,atol=1e-8)

def test_recentered_probe_fails_safely():
    import sys,pytest
    sys.path.insert(0,str(ROOT/'ue5'))
    from stillhere_transform_math import calibrate
    with pytest.raises(ValueError,match='recentered'):
        calibrate([[0,0,0],[0,0,0],[0,0,0]])

def test_camera_preserves_reference_frame_handedness_and_width():
    import sys,json,numpy as np
    sys.path.insert(0,str(ROOT/'ue5'))
    from stillhere_transform_math import camera_transform,quaternion_matrix,WORLD_BASIS
    camera=json.loads((ROOT/'data/camera.json').read_text())
    out=camera_transform(camera);R=np.array(quaternion_matrix(out['quaternion_xyzw']))
    forward=np.array(camera['target_m'])-camera['position_m'];forward/=np.linalg.norm(forward)
    assert np.allclose(R[:,0],np.array(WORLD_BASIS)@forward/100)
    assert np.allclose(R.T@R,np.eye(3))
    assert out['ortho_width_cm']==3600

def test_all_delivered_python_files_parse_without_engine_modules():
    import ast
    for folder in ['generation','blender','ue5']:
        for path in (ROOT/folder).glob('*.py'):
            ast.parse(path.read_text(encoding='utf8'),filename=str(path))
