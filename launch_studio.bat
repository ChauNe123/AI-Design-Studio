@echo off
setlocal
title AI Design Studio V2 (Standalone Windows)
pushd "%~dp0" || exit /b 1
python "%~dp0run_studio.py"
set "EXIT_CODE=%ERRORLEVEL%"
popd
pause
exit /b %EXIT_CODE%

