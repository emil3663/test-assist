# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Test Assist desktop build.

Deliberately a one-folder build rather than one-file. A one-file bundle
unpacks PySide6 to a temp directory on every launch, which costs several
seconds each time — unacceptable for a tool you open dozens of times a day
from the taskbar. The folder starts effectively instantly and zips just as
well for distribution.

Build:  pyinstaller --noconfirm TestAssist.spec
Output: Windows  dist/TestAssist/TestAssist.exe
        macOS    dist/Test Assist.app

One spec for both platforms rather than two, so the datas, excludes and
hiddenimports cannot drift apart - they are the parts that actually decide
whether a build works, and they are identical either way. Only the icon
format, the Windows version resource and the macOS bundle differ, and each
is guarded below.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

HERE = Path(SPECPATH)
REPO = HERE.parent
MACOS = sys.platform == 'darwin'

# __version__ without importing main.py, which would need PySide6 present in
# the environment running PyInstaller rather than the one being packaged.
VERSION = next(
    line.split('=')[1].strip().strip('"\'')
    for line in (HERE / 'main.py').read_text().splitlines()
    if line.startswith('__version__')
)

a = Analysis(
    [str(HERE / 'main.py')],
    pathex=[str(HERE)],
    binaries=[],
    datas=[
        (str(REPO / 'assets' / 'icon.ico'), 'assets'),
        *([(str(REPO / 'assets' / 'icon.icns'), 'assets')] if MACOS else []),
        # The UI's icons are glyphs from this font, so a build without it
        # falls back to text labels on every icon button.
        (str(REPO / 'assets' / 'MaterialIcons-Regular.ttf'), 'assets'),
        (str(REPO / 'assets' / 'MaterialIcons-LICENSE.txt'), 'assets'),
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
    icon=str(REPO / 'assets' / ('icon.icns' if MACOS else 'icon.ico')),
    # A Windows PE version resource; meaningless in a Mach-O binary, and
    # PyInstaller rejects the argument outright when it is not building one.
    version=None if MACOS else str(HERE / 'version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='TestAssist',
)

# The .app wrapper. Everything a macOS user notices about "is this a real
# application" comes from here rather than from the executable inside it.
if MACOS:
    app = BUNDLE(
        coll,
        name='Test Assist.app',
        icon=str(REPO / 'assets' / 'icon.icns'),
        bundle_identifier='com.emil3663.testassist',
        version=VERSION,
        info_plist={
            # CFBundleName is what the macOS menu bar titles the application
            # menu, and what it interpolates into "About X", "Hide X" and
            # "Quit X". Running from source those read "Python", because the
            # running bundle is the interpreter - this is the only thing that
            # fixes it, and it fixes all four at once.
            'CFBundleName': 'Test Assist',
            'CFBundleDisplayName': 'Test Assist',
            'CFBundleShortVersionString': VERSION,
            'CFBundleVersion': VERSION,
            # Without this the app renders through the 1x compatibility path
            # and every screenshot it takes comes back at half resolution -
            # which would undo the HiDPI capture fix at the packaging step.
            'NSHighResolutionCapable': True,
            # Not an agent: Test Assist has a Dock icon and a menu bar.
            'LSUIElement': False,
            'LSMinimumSystemVersion': '11.0',
            'NSHumanReadableCopyright': 'MIT licensed. See LICENSE.',
        },
    )
