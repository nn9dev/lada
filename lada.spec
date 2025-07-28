# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Common exclusions for large packages
common_excludes = [
    'tkinter', 'pydoc', 'doctest',
    'py', 'pytest', 'sphinx', 'IPython', 'notebook', 'jupyter',
    'PIL.ImageQt', 'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngine',
    'PyQt6.QtSql', 'PyQt6.QtTest',
    'PyQt6.QtXml', 'PyQt6.QtDesigner', 'PyQt6.QtHelp',
    'PyQt6.QtOpenGL', 'PyQt6.QtPrintSupport', 'PyQt6.QtQml',
    'PyQt6.QtQuick', 'PyQt6.QtSvg', 'PyQt6.QtWebSockets',
    'PyQt6.QtXmlPatterns', 'PyQt6.QtBluetooth', 'PyQt6.QtDBus',
    'PyQt6.QtNfc', 'PyQt6.QtPositioning', 'PyQt6.QtRemoteObjects',
    'PyQt6.QtSensors', 'PyQt6.QtSerialPort', 'PyQt6.QtWebChannel',
    'PyQt6.QtWebEngineQuick', 'PyQt6.QtWebEngineQuickDelegatesQml',
    'PyQt6.QtWebEngineQuickWidgets', 'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebSockets', 'PyQt6.QtXmlPatterns',
]

# Files that should not be compressed with UPX
upx_exclude = [
    'vcruntime140.dll',
    'msvcp140.dll',
    'torch_cpu.dll',
    'torch_cuda.dll',
    'cudart64_*.dll',
    'cublas64_*.dll',
    'cublasLt64_*.dll',
    'cufft64_*.dll',
    'curand64_*.dll',
    'cusolver64_*.dll',
    'cusparse64_*.dll',
    'cudnn64_*.dll',
    'cudnn_ops_infer64_*.dll',
    'cudnn_ops_train64_*.dll',
    'cudnn_adv_infer64_*.dll',
    'cudnn_adv_train64_*.dll',
    'cudnn_cnn_infer64_*.dll',
    'cudnn_cnn_train64_*.dll',
    'cudnn_ops_infer64_*.dll',
    'cudnn_ops_train64_*.dll',
]

a = Analysis(
    ['lada/gui/qt_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('lada/gui/icons', 'lada/gui/icons'),
        ('lada/gui/*.ui', 'lada/gui'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtNetwork',
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',
        'numpy.core.multiarray',
        'numpy.core.umath',
        'numpy.core._multiarray_umath',
        'numpy.core._multiarray_tests',
        'numpy.core._dtype_ctypes',
        'numpy.core._internal',
        'numpy.core._dotblas',
        'cv2',
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.optim',
        'torch.utils.data',
        'torchvision',
        'ultralytics',
        'matplotlib',
        'matplotlib.pyplot',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=common_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lada',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Enable stripping of symbols
    upx=True,
    upx_exclude=upx_exclude,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
) 