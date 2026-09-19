@echo off
setlocal
REM Edit this only when blender.exe is not in PATH.
set "BLENDER_EXE=blender"
"%BLENDER_EXE%" --background --python "%~dp0build_atv.py" -- --out "%~dp0..\Build_Blender"
if errorlevel 1 (
  echo Build failed. Check the Blender path and the console error above.
  pause
  exit /b 1
)
echo Created ..\Build_Blender\ATV_Stylized.blend and SM_ATV_Stylized.glb
pause
