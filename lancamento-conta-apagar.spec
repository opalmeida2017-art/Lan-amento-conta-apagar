# -*- mode: python ; coding: utf-8 -*-
import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

if "__file__" in globals():
    RAIZ = Path(__file__).resolve().parent
elif len(sys.argv) > 1:
    RAIZ = Path(sys.argv[1]).resolve().parent
else:
    RAIZ = Path.cwd().resolve()
ARQ_VERSAO_APP = RAIZ / "app_version.py"
ARQ_VERSAO_WIN = RAIZ / "build_version_info.txt"


def _ler_versao_atual():
    if not ARQ_VERSAO_APP.exists():
        ARQ_VERSAO_APP.write_text(
            'APP_VERSION = "1.0.0"\n\n\ndef versao_exibicao():\n    return f"V.{APP_VERSION}"\n',
            encoding="utf-8",
        )
        return "1.0.0"

    conteudo = ARQ_VERSAO_APP.read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"(\d+\.\d+\.\d+)"', conteudo)
    if not match:
        raise RuntimeError("Não foi possível ler APP_VERSION em app_version.py")
    return match.group(1)


def _proxima_versao(versao):
    major, minor, patch = [int(parte) for parte in versao.split(".")]
    if patch >= 9:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _salvar_versao_app(nova_versao):
    ARQ_VERSAO_APP.write_text(
        f'APP_VERSION = "{nova_versao}"\n\n\ndef versao_exibicao():\n    return f"V.{{APP_VERSION}}"\n',
        encoding="utf-8",
    )


def _gerar_arquivo_versao_windows(versao):
    major, minor, patch = [int(parte) for parte in versao.split(".")]
    conteudo = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'Automacao NFe'),
        StringStruct('FileDescription', 'Sistema de Automacao NFe'),
        StringStruct('FileVersion', '{versao}'),
        StringStruct('InternalName', 'lancamento-conta-apagar'),
        StringStruct('OriginalFilename', 'lancamento-conta-apagar.exe'),
        StringStruct('ProductName', 'Automacao NFe'),
        StringStruct('ProductVersion', '{versao}')])
      ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    ARQ_VERSAO_WIN.write_text(conteudo, encoding="utf-8")


# Instrucao de versao automatica:
# Toda vez que gerar o .exe por este .spec:
# V.1.0.0 -> ... -> V.1.0.9 -> V.1.1.0 -> V.1.1.1 ...
VERSAO_ANTIGA = _ler_versao_atual()
VERSAO_BUILD = _proxima_versao(VERSAO_ANTIGA)
_salvar_versao_app(VERSAO_BUILD)
_gerar_arquivo_versao_windows(VERSAO_BUILD)

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

hiddenimports += [
    'robo_web',
    'robo_web.automacao',
    'robo_web.controle_robo',
    'robo_web.utils',
    'robo_web.erp_lock',
    'robo_web.filial_embarque',
    'robo_web.modulo_importacao',
    'robo_web.modulo_sefaz',
    'robo_web.modulo_importa_xml',
    'robo_web.modulo_frota',
    'robo_web.modulo_migracao',
    'robo_web.modulo_km',
    'robo_web.modulo_item',
    'robo_web.modulo_item_sync',
    'robo_web.modulo_gravacao',
    'robo_web.modulo_veiculo',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'pandas.tests',
        'pandas.plotting._matplotlib',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='lancamento-conta-apagar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    version=str(ARQ_VERSAO_WIN),
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
