@echo off
title AI Design Studio v1.5.0 - Setup May Moi (Home PC)
cd /d "%~dp0"

echo ============================================================
echo   AI DESIGN STUDIO v1.5.0 - HOME PC SETUP
echo ============================================================
echo.

echo [1/4] Checking Python and Node.js...
python --version
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat hoac chua them vao PATH!
    pause
    exit /b 1
)
node --version
if errorlevel 1 (
    echo [ERROR] Node.js chua duoc cai dat hoac chua them vao PATH!
    pause
    exit /b 1
)

echo.
echo [2/4] Installing Python dependencies (requirements.txt)...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Cai dat Python packages that bai!
    pause
    exit /b 1
)

echo.
echo [3/4] Installing Node.js dependencies (package.json)...
call npm install
if errorlevel 1 (
    echo [ERROR] Cai dat Node.js packages that bai!
    pause
    exit /b 1
)

echo.
echo [4/4] Verifying core Python & Node.js packages...
python -c "import PIL, cv2, numpy; print('[OK] Python:', PIL.__version__, cv2.__version__, numpy.__version__)"
if errorlevel 1 (
    echo [ERROR] Khong the import PIL/cv2/numpy!
    pause
    exit /b 1
)
node -e "require('ag-psd'); require('pngjs'); require('tesseract.js'); require('onnxruntime-node'); console.log('[OK] Node.js: ag-psd, pngjs, tesseract.js, onnxruntime-node ready')"
if errorlevel 1 (
    echo [ERROR] Khong the require Node packages!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   SETUP HOAN TAT!
echo   Chay ung dung bang lenh:  python run_studio.py
echo   Hoac mo trinh duyet tai:  http://127.0.0.1:8788
echo ============================================================
pause
