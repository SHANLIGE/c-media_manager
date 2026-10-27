block_cipher = None

a = Analysis(
    ["App/App.py"],
    pathex=[
        "/cmediaplayerlinux/cod/C-Media_Linux_player-master/entorno6/lib/python3.10/site-packages/cv2",
        "App",
    ],
    binaries=[
    ],
    datas=[
        # Incluir carpetas del proyecto
        ("App/AppFrames", "AppFrames"),
        ("App/ConfigGUI", "ConfigGUI"),
    ],
    hiddenimports=[
        # PySide6 / Qt
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngine",
        "PySide6.QtPrintSupport",

        # Serial
        "serial",
        "serial.serialposix",
        "serial.serialutil",
        "serial.backends",
        "serial.tools",
        "serial.tools.list_ports",
        "serial.tools.list_ports_posix",

        # Otros módulos del proyecto
        "cv2",
        "netifaces",
        "psutil",
        "gtts",

        # Cryptography
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat",
        "cryptography.hazmat.primitives",
        "cryptography.hazmat.backends",
    ],
    hookspath=["."],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="CMedia_Player",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Excluir librerías Qt de UPX
        "libQt6*.so*",
        "libPySide6*.so*",
        "Qt6*.so*",
    ],
    name="C-Media_Player",
)
