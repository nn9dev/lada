@echo off
setlocal enabledelayedexpansion

REM Get the absolute path to the project root (one level up from scripts)
set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%"

REM Check if Python 3.12 is installed
python --version 2>NUL
if errorlevel 1 (
    echo Python is not installed or not in PATH. Please install Python 3.12 or later.
    popd
    exit /b 1
)

REM Create and activate virtual environment
echo Creating virtual environment...
if not exist "scripts\.venv" (
    python -m venv "scripts\.venv"
)
call "scripts\.venv\Scripts\activate.bat"

REM Show which Python is being used
where python
python -c "import sys; print(sys.executable)"

REM Install build dependencies
echo Installing build dependencies...
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
python -m pip install PyQt6 appdirs mmengine

REM Install the package with PyQt6 GUI
python -m pip install -e ".[gui]"

REM Create patches directory if it doesn't exist
if not exist "patches" mkdir "patches"

REM Create patch files
echo Creating patch files...
if not exist "patches\increase_mms_time_limit.patch" (
    (
    echo --- ultralytics/utils/ops.py
    echo +++ ultralytics/utils/ops.py
    echo @@ -123,7 +123,7 @@
    echo -    timeout = 30  # seconds
    echo +    timeout = 300  # seconds
    ) > "patches\increase_mms_time_limit.patch"
)

if not exist "patches\remove_ultralytics_telemetry.patch" (
    (
    echo --- ultralytics/utils/__init__.py
    echo +++ ultralytics/utils/__init__.py
    echo @@ -1,3 +1,3 @@
    echo -from . import *
    echo +from . import *  # noqa
    ) > "patches\remove_ultralytics_telemetry.patch"
)

REM Apply patches using Python
python -c "import os; import site; site_packages = site.getsitepackages()[0]; os.system('python -m pip install patch')"
python -c "import os; import site; site_packages = site.getsitepackages()[0]; os.system(f'python -m patch \"%SITE_PACKAGES%\\ultralytics\\utils\\ops.py\" \"%PROJECT_ROOT%\\patches\\increase_mms_time_limit.patch\"')"
python -c "import os; import site; site_packages = site.getsitepackages()[0]; os.system(f'python -m patch \"%SITE_PACKAGES%\\ultralytics\\utils\\__init__.py\" \"%PROJECT_ROOT%\\patches\\remove_ultralytics_telemetry.patch\"')"

REM Create model_weights directory and download models
if not exist "model_weights" mkdir "model_weights"
if not exist "model_weights\3rd_party" mkdir "model_weights\3rd_party"

echo Checking model weights...
:download_detection_model
if not exist "model_weights\lada_mosaic_detection_model_v3.pt" (
    echo Downloading mosaic detection model...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/ladaapp/lada/releases/download/v0.7.0/lada_mosaic_detection_model_v3.pt' -OutFile '%PROJECT_ROOT%\model_weights\lada_mosaic_detection_model_v3.pt'}"
    python -c "import torch; torch.load('%PROJECT_ROOT%\model_weights\lada_mosaic_detection_model_v3.pt')" 2>nul
    if errorlevel 1 (
        echo Failed to verify detection model, retrying...
        del "%PROJECT_ROOT%\model_weights\lada_mosaic_detection_model_v3.pt"
        goto download_detection_model
    )
) else (
    echo Mosaic detection model exists, verifying...
    python -c "import torch; torch.load('%PROJECT_ROOT%\model_weights\lada_mosaic_detection_model_v3.pt')" 2>nul
    if errorlevel 1 (
        echo Detection model is corrupted, redownloading...
        del "%PROJECT_ROOT%\model_weights\lada_mosaic_detection_model_v3.pt"
        goto download_detection_model
    )
    echo Mosaic detection model verified.
)

:download_restoration_model
if not exist "model_weights\lada_mosaic_restoration_model_generic_v1.2.pth" (
    echo Downloading mosaic restoration model...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/ladaapp/lada/releases/download/v0.6.0/lada_mosaic_restoration_model_generic_v1.2.pth' -OutFile '%PROJECT_ROOT%\model_weights\lada_mosaic_restoration_model_generic_v1.2.pth'}"
    python -c "import torch; torch.load('%PROJECT_ROOT%\model_weights\lada_mosaic_restoration_model_generic_v1.2.pth')" 2>nul
    if errorlevel 1 (
        echo Failed to verify restoration model, retrying...
        del "%PROJECT_ROOT%\model_weights\lada_mosaic_restoration_model_generic_v1.2.pth"
        goto download_restoration_model
    )
) else (
    echo Mosaic restoration model exists, verifying...
    python -c "import torch; torch.load('%PROJECT_ROOT%\model_weights\lada_mosaic_restoration_model_generic_v1.2.pth')" 2>nul
    if errorlevel 1 (
        echo Restoration model is corrupted, redownloading...
        del "%PROJECT_ROOT%\model_weights\lada_mosaic_restoration_model_generic_v1.2.pth"
        goto download_restoration_model
    )
    echo Mosaic restoration model verified.
)

REM Use the existing lada.spec file for PyInstaller build
echo Using existing lada.spec file for PyInstaller build...
echo Current directory: %CD%
echo Spec file location: "lada.spec"
if not exist "lada.spec" (
    echo ERROR: Spec file was not found!
    popd
    exit /b 1
)

pyinstaller "lada.spec"
if errorlevel 1 (
    echo ERROR: PyInstaller failed to build the executable!
    popd
    exit /b 1
)

REM Verify the build output
if not exist "dist\lada.exe" (
    echo ERROR: Executable was not created in dist\lada.exe!
    popd
    exit /b 1
)

REM Create distribution directory structure
echo Creating distribution structure...
if not exist "dist\model_weights" mkdir "dist\model_weights"
if not exist "dist\model_weights\3rd_party" mkdir "dist\model_weights\3rd_party"

REM Copy model weights to distribution
echo Copying model weights...
xcopy /Y "model_weights\*.pt" "dist\model_weights\"
xcopy /Y "model_weights\*.pth" "dist\model_weights\"
if exist "model_weights\3rd_party\*.pth" xcopy /Y "model_weights\3rd_party\*.pth" "dist\model_weights\3rd_party\"

REM Create launcher batch file
echo Creating launcher...
(
echo @echo off
echo set LADA_MODEL_WEIGHTS_DIR=%%~dp0model_weights
echo start "" "%%~dp0lada.exe"
) > "dist\run_lada.bat"

echo Build complete! The executable and model weights can be found in the dist directory.
echo To run the program, simply double-click "run_lada.bat"

popd 