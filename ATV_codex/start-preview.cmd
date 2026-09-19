@echo off
cd /d "%~dp0"
start "" http://127.0.0.1:4177
node scripts/serve.mjs
pause
