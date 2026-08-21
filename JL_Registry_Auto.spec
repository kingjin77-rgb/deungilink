# -*- mode: python ; coding: utf-8 -*-
#
# 빌드: pyinstaller JL_Registry_Auto.spec   (또는 빌드.bat 더블클릭)
# 필요: 표준 python.org 배포판의 Python (tkinter 기본 포함, PyInstaller 가
#       자동으로 tcl/tk DLL 을 수집한다 — 별도 경로 지정 불필요).
#
# noarchive=True 인 이유:
#   기본값(False)이면 순수 파이썬 모듈이 PYZ 아카이브로 압축되어, 그 안의
#   모듈이 사용하는 Path(__file__).parent 기반 경로(설정파일·라이선스파일·
#   세율표 등 다수 모듈이 이 방식 사용)가 실제 디스크 경로가 아니게 되어
#   빌드된 exe 에서 FileNotFoundError 로 깨진다. noarchive=True 로 모든
#   모듈을 _internal/ 아래 일반 파일로 풀어두면 이 문제가 원천 차단된다.

a = Analysis(
    ['main_frozen.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('deploy_assets\\config.ini', '.'),
        ('data', 'data'),
        ('template.xlsx', '.'),
        ('template_clean.xlsx', '.'),
        ('template_new.xlsx', '.'),
        ('template_nj.xlsx', '.'),
        ('templates', 'templates'),
        ('mappings', 'mappings'),
    ],
    hiddenimports=['_tkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JL_Registry_Auto',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JL_Registry_Auto',
)
