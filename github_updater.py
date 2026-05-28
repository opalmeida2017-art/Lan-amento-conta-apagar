import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


try:
    import licenca_config as _cfg
except ImportError:
    _cfg = None


UPDATE_GITHUB_OWNER = (
    getattr(_cfg, "UPDATE_GITHUB_OWNER", "") if _cfg else ""
) or (
    getattr(_cfg, "GITHUB_OWNER", "") if _cfg else ""
) or os.environ.get("UPDATE_GITHUB_OWNER", "")

UPDATE_GITHUB_REPO = (
    getattr(_cfg, "UPDATE_GITHUB_REPO", "") if _cfg else ""
) or (
    getattr(_cfg, "GITHUB_REPO", "") if _cfg else ""
) or os.environ.get("UPDATE_GITHUB_REPO", "")

UPDATE_GITHUB_TOKEN = (
    getattr(_cfg, "UPDATE_GITHUB_TOKEN", "") if _cfg else ""
) or (
    getattr(_cfg, "GITHUB_TOKEN", "") if _cfg else ""
) or os.environ.get("UPDATE_GITHUB_TOKEN", "")

UPDATE_RELEASE_TAG = (
    getattr(_cfg, "UPDATE_RELEASE_TAG", "latest") if _cfg else "latest"
) or "latest"

UPDATE_ASSET_NAME = (
    getattr(_cfg, "UPDATE_ASSET_NAME", "") if _cfg else ""
) or os.environ.get("UPDATE_ASSET_NAME", "")


def _headers(accept="application/vnd.github+json"):
    headers = {
        "Accept": accept,
        "User-Agent": "AutomacaoNFe-Updater",
    }
    if UPDATE_GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {UPDATE_GITHUB_TOKEN}"
    return headers


def configuracao_disponivel():
    return bool(UPDATE_GITHUB_OWNER and UPDATE_GITHUB_REPO)


def _url_release():
    base = f"https://api.github.com/repos/{UPDATE_GITHUB_OWNER}/{UPDATE_GITHUB_REPO}/releases"
    if str(UPDATE_RELEASE_TAG).strip().lower() == "latest":
        return f"{base}/latest"
    tag = urllib.parse.quote(str(UPDATE_RELEASE_TAG).strip(), safe="")
    return f"{base}/tags/{tag}"


def _ler_json(url):
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _selecionar_asset(release):
    assets = release.get("assets") or []
    if not assets:
        raise RuntimeError("A release do GitHub não possui arquivos anexados.")

    nome_desejado = str(UPDATE_ASSET_NAME or "").strip().lower()
    if nome_desejado:
        for asset in assets:
            if str(asset.get("name") or "").strip().lower() == nome_desejado:
                return asset
        raise RuntimeError(
            f"Asset '{UPDATE_ASSET_NAME}' não encontrado na release configurada."
        )

    for asset in assets:
        nome = str(asset.get("name") or "").strip().lower()
        if nome.endswith(".exe"):
            return asset

    raise RuntimeError(
        "Nenhum arquivo .exe foi encontrado na release. "
        "Defina UPDATE_ASSET_NAME em licenca_config.py."
    )


def _normalizar_versao(texto):
    """Extrai x.y.z de tag, nome da release ou versão do arquivo."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(texto or ""))
    if not match:
        return ""
    return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"


def _extrair_versao_release(release, asset=None):
    candidatos = [
        (release or {}).get("tag_name"),
        (release or {}).get("name"),
        (asset or {}).get("name"),
    ]
    for texto in candidatos:
        versao = _normalizar_versao(texto)
        if versao:
            return versao
    return ""


def _ler_versao_exe(caminho_exe):
    """Lê FileVersion do .exe no Windows (versão embutida no build)."""
    if os.name != "nt" or not caminho_exe or not Path(caminho_exe).exists():
        return ""
    try:
        caminho = str(Path(caminho_exe).resolve()).replace("'", "''")
        comando = (
            f"(Get-Item -LiteralPath '{caminho}').VersionInfo.FileVersion"
        )
        saida = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", comando],
            text=True,
            timeout=15,
            stderr=subprocess.DEVNULL,
        )
        return _normalizar_versao(saida.strip())
    except Exception:
        return ""


def versao_exibicao_de(versao):
    versao = _normalizar_versao(versao)
    return f"V.{versao}" if versao else ""


def _baixar_asset(asset, destino):
    url_asset = asset.get("url")
    if not url_asset:
        raise RuntimeError("Asset da release sem URL de download.")

    req = urllib.request.Request(
        url_asset,
        headers=_headers(accept="application/octet-stream"),
        method="GET",
    )
    total_bytes = 0
    with urllib.request.urlopen(req, timeout=120) as resp:
        with open(destino, "wb") as arquivo:
            while True:
                bloco = resp.read(1024 * 256)
                if not bloco:
                    break
                arquivo.write(bloco)
                total_bytes += len(bloco)

    tamanho_esperado = asset.get("size")
    try:
        tamanho_esperado = int(tamanho_esperado)
    except Exception:
        tamanho_esperado = 0

    if tamanho_esperado > 0 and total_bytes != tamanho_esperado:
        try:
            os.remove(destino)
        except Exception:
            pass
        raise RuntimeError(
            "Download do executável incompleto/corrompido "
            f"(esperado {tamanho_esperado} bytes, recebido {total_bytes} bytes)."
        )


def _criar_script_troca(destino_exe, novo_arquivo, backup_exe, pid_atual):
    pasta_temp = Path(tempfile.gettempdir())
    caminho_script = pasta_temp / "atualizar_automacao_nfe.cmd"
    caminho_log = pasta_temp / "atualizacao_automacao_nfe.log"
    conteudo = f"""@echo off
setlocal
set "TARGET={destino_exe}"
set "NEWFILE={novo_arquivo}"
set "BACKUP={backup_exe}"
set "PID={pid_atual}"
set "LOGFILE={caminho_log}"
for %%I in ("%TARGET%") do set "TARGET_NAME=%%~nxI"

echo.>"%LOGFILE%"
echo [%date% %time%] Iniciando troca de executavel>>"%LOGFILE%"
echo TARGET=%TARGET%>>"%LOGFILE%"
echo NEWFILE=%NEWFILE%>>"%LOGFILE%"
echo BACKUP=%BACKUP%>>"%LOGFILE%"

:waitloop
tasklist /FI "PID eq %PID%" /FO CSV /NH 2>NUL | find /I "\"%PID%\"" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >NUL
    goto waitloop
)

if not exist "%NEWFILE%" (
    echo [%date% %time%] ERRO: novo executavel nao encontrado.>>"%LOGFILE%"
    exit /b 2
)

if exist "%BACKUP%" del /f /q "%BACKUP%" >>"%LOGFILE%" 2>&1
if exist "%TARGET%" move /Y "%TARGET%" "%BACKUP%" >>"%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERRO: falha ao mover executavel atual para backup.>>"%LOGFILE%"
    exit /b 3
)

move /Y "%NEWFILE%" "%TARGET%" >>"%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERRO: falha ao substituir executavel.>>"%LOGFILE%"
    if exist "%BACKUP%" move /Y "%BACKUP%" "%TARGET%" >>"%LOGFILE%" 2>&1
    exit /b 4
)

if not exist "%TARGET%" (
    echo [%date% %time%] ERRO: executavel final nao encontrado apos troca.>>"%LOGFILE%"
    exit /b 5
)

echo [%date% %time%] Troca concluida com sucesso.>>"%LOGFILE%"
echo [%date% %time%] Atualizacao finalizada. Abra o sistema manualmente.>>"%LOGFILE%"
exit /b
"""
    # Usa encoding ANSI do Windows para evitar quebra de acentos em .cmd.
    caminho_script.write_text(conteudo, encoding="mbcs")
    return caminho_script


def preparar_atualizacao_exe():
    if os.name != "nt":
        raise RuntimeError("A atualização automática do executável está disponível apenas no Windows.")

    if not getattr(sys, "frozen", False):
        raise RuntimeError(
            "A atualização automática funciona apenas na versão publicada em .exe."
        )

    if not configuracao_disponivel():
        raise RuntimeError(
            "Configure UPDATE_GITHUB_OWNER e UPDATE_GITHUB_REPO em licenca_config.py."
        )

    try:
        release = _ler_json(_url_release())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError("Release do GitHub não encontrada.") from exc
        if exc.code == 401:
            raise RuntimeError("Token do GitHub inválido ou sem acesso à release.") from exc
        raise RuntimeError(f"Erro ao consultar release do GitHub ({exc.code}).") from exc
    except Exception as exc:
        raise RuntimeError(f"Falha ao consultar release do GitHub: {exc}") from exc

    asset = _selecionar_asset(release)
    exe_atual = Path(sys.executable).resolve()
    novo_arquivo = Path(tempfile.gettempdir()) / f"{exe_atual.stem}.novo.exe"
    backup_exe = exe_atual.with_suffix(exe_atual.suffix + ".bak")

    _baixar_asset(asset, novo_arquivo)
    versao_sistema = _ler_versao_exe(novo_arquivo) or _extrair_versao_release(release, asset)
    script = _criar_script_troca(
        str(exe_atual),
        str(novo_arquivo),
        str(backup_exe),
        os.getpid(),
    )

    flags = 0
    if hasattr(subprocess, "DETACHED_PROCESS"):
        flags |= subprocess.DETACHED_PROCESS
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        flags |= subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        ["cmd", "/c", str(script)],
        creationflags=flags,
        close_fds=True,
    )

    return {
        "asset_name": str(asset.get("name") or ""),
        "release_name": str(release.get("name") or release.get("tag_name") or "latest"),
        "versao_sistema": versao_sistema,
        "versao_exibicao": versao_exibicao_de(versao_sistema),
        "exe_atual": str(exe_atual),
        "backup_exe": str(backup_exe),
        "script_troca": str(script),
        "log_troca": str(Path(tempfile.gettempdir()) / "atualizacao_automacao_nfe.log"),
    }
