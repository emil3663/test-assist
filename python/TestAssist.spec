# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Test Assist desktop build.

Deliberately a one-folder build rather than one-file. A one-file bundle
unpacks PySide6 to a temp directory on every launch, which costs several
seconds each time — unacceptable for a tool you open dozens of times a day
from the taskbar. The folder starts effectively instantly and zips just as
well for distribution.

Build:  pyinstaller --noconfirm TestAssist.spec
Output: dist/TestAssist/TestAssist.exe
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

HERE = Path(SPECPATH)
REPO = HERE.parent

a = Analysis(
    [str(HERE / 'main.py')],
    pathex=[str(HERE)],
    binaries=[],
    datas=[
        (str(REPO / 'assets' / 'icon.ico'), 'assets'),
        (str(HERE / 'help.html'), '.'),
        # Pulls in imageio_ffmpeg/binaries/ffmpeg-win-*.exe (~83 MB), the
        # actual encoder capture.py shells out to for MP4 assembly.
        *collect_data_files('imageio_ffmpeg'),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    # Qt ships a great deal this app never touches; dropping it keeps the
    # download to something a reviewer will actually wait for.
    excludes=[
        'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQuickWidgets',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebChannel',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtBluetooth',
        'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtDesigner', 'PySide6.QtHelp',
        'tkinter', 'unittest', 'pytest', 'pydoc_data',
        # MP4 assembly now shells out to a bundled ffmpeg binary via
        # imageio_ffmpeg instead of linking opencv, so these never need to be
        # pulled in - excluding them keeps the ~250 MB opencv/numpy stack out
        # of the build regardless of what happens to be on the build machine.
        'cv2', 'numpy', 'scipy', 'PIL', 'matplotlib',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TestAssist',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                      # no console window behind the app
    disable_windowed_traceback=False,
    icon=str(REPO / 'assets' / 'icon.ico'),
    version=str(HERE / 'version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='TestAssist',
)
