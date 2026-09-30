# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/HP/Documents/akash/akash w/Ai_assistent/Mark-LIV-main/main.py'],
    pathex=['C:/Users/HP/Documents/akash/akash w/Ai_assistent/Mark-LIV-main'],
    binaries=[],
    datas=[('C:/Users/HP/Documents/akash/akash w/Ai_assistent/Mark-LIV-main/dashboard/static', 'dashboard/static'), ('C:/Users/HP/Documents/akash/akash w/Ai_assistent/Mark-LIV-main/core/prompt.txt', 'core'), ('C:/Users/HP/Documents/akash/akash w/Ai_assistent/Mark-LIV-main/core/face_model.obj', 'core')],
    hiddenimports=['actions.background_monitor', 'actions.browser_control', 'actions.call_whatsapp', 'actions.code_helper', 'actions.computer_control', 'actions.computer_settings', 'actions.desktop', 'actions.dev_agent', 'actions.file_controller', 'actions.file_processor', 'actions.flight_finder', 'actions.game_updater', 'actions.open_app', 'actions.proactive', 'actions.reminder', 'actions.screen_processor', 'actions.send_message', 'actions.system_monitor', 'actions.weather_report', 'actions.web_search', 'actions.youtube_video', 'plugins._template'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GENI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GENI',
)
