@echo off
setlocal enabledelayedexpansion

REM Check if Python 3.12 is installed
python --version 2>NUL
if errorlevel 1 (
    echo Python is not installed or not in PATH. Please install Python 3.12 or later.
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat

REM Install PyTorch (CUDA version)
echo Installing PyTorch...
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

REM Install other dependencies
echo Installing other dependencies...
python -m pip install -e ".[basicvsrpp]"

REM Create patches directory if it doesn't exist
if not exist patches mkdir patches

REM Apply patches
echo Applying patches...
python -c "import os; import site; site_packages = site.getsitepackages()[0]; print(site_packages)" > temp_site_packages.txt
set /p SITE_PACKAGES=<temp_site_packages.txt
del temp_site_packages.txt

REM Create patch files
echo Creating patch files...
(
echo --- ultralytics/utils/ops.py
echo +++ ultralytics/utils/ops.py
echo @@ -123,7 +123,7 @@
echo -    timeout = 30  # seconds
echo +    timeout = 300  # seconds
) > patches\increase_mms_time_limit.patch

(
echo --- ultralytics/utils/__init__.py
echo +++ ultralytics/utils/__init__.py
echo @@ -1,3 +1,3 @@
echo -from . import *
echo +from . import *  # noqa
) > patches\remove_ultralytics_telemetry.patch

REM Apply patches using Python
python -c "import os; import site; site_packages = site.getsitepackages()[0]; os.system(f'python -m pip install patch')"
python -c "import os; import site; site_packages = site.getsitepackages()[0]; os.system(f'python -m patch -u \"%SITE_PACKAGES%\\ultralytics\\utils\\ops.py\" patches\\increase_mms_time_limit.patch')"
python -c "import os; import site; site_packages = site.getsitepackages()[0]; os.system(f'python -m patch -u \"%SITE_PACKAGES%\\ultralytics\\utils\\__init__.py\" patches\\remove_ultralytics_telemetry.patch')"

REM Create model_weights directory
if not exist model_weights mkdir model_weights
if not exist model_weights\3rd_party mkdir model_weights\3rd_party

REM Download model weights using PowerShell
echo Downloading model weights...
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/ladaapp/lada/releases/download/v0.7.0/lada_mosaic_detection_model_v3.pt' -OutFile 'model_weights/lada_mosaic_detection_model_v3.pt'}"
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/ladaapp/lada/releases/download/v0.6.0/lada_mosaic_restoration_model_generic_v1.2.pth' -OutFile 'model_weights/lada_mosaic_restoration_model_generic_v1.2.pth'}"

echo Installation complete! You can now use lada-cli.
echo To activate the virtual environment in the future, run: .venv\Scripts\activate.bat 