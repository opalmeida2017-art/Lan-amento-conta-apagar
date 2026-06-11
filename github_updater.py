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

import http_ssl
import release_notas


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
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if UPDATE_GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {UPDATE_GITHUB_TOKEN}"
    return headers


def _headers_upload_asset():
    """Headers corretos para uploads.github.com (Accept JSON + corpo binário)."""
    headers = _headers()
    headers["Content-Type"] = "application/octet-stream"
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
    return http_ssl.http_get_json(url, headers=_headers(), timeout=30)


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

    total_bytes = http_ssl.http_download(
        url_asset,
        headers=_headers(accept="application/octet-stream"),
        destino=destino,
        timeout=300,
    )

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


def _api_base():
    return f"https://api.github.com/repos/{UPDATE_GITHUB_OWNER}/{UPDATE_GITHUB_REPO}"


def _mensagem_erro_github(exc):
    if isinstance(exc, urllib.error.HTTPError):
        try:
            corpo = exc.read().decode("utf-8", errors="replace")
            dados = json.loads(corpo) if corpo.strip().startswith("{") else {}
            msg = dados.get("message") or dados.get("error")
            if msg:
                detalhe = dados.get("errors")
                if detalhe:
                    return f"GitHub ({exc.code}): {msg}\n{detalhe}"
                return f"GitHub ({exc.code}): {msg}"
        except Exception:
            pass
        return f"GitHub HTTP {exc.code}: {exc.reason or 'erro na API'}"
    return str(exc) or repr(exc)


def _obter_release_por_tag(tag):
    tag = str(tag or "").strip()
    if not tag:
        return None
    url = f"{_api_base()}/releases/tags/{urllib.parse.quote(tag, safe='')}"
    try:
        return _ler_json(url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _atualizar_texto_release(release_id, titulo, body):
    url = f"{_api_base()}/releases/{release_id}"
    payload = json.dumps(
        {"name": titulo, "body": body},
        ensure_ascii=False,
    ).encode("utf-8")
    headers = _headers()
    headers["Content-Type"] = "application/json"
    http_ssl.http_request("PATCH", url, headers=headers, data=payload, timeout=60)


def _criar_release(tag, titulo, notas=""):
    url = f"{_api_base()}/releases"
    payload = {
        "tag_name": tag,
        "name": titulo,
        "body": notas or f"Release {titulo}",
        "draft": False,
        "prerelease": False,
        "generate_release_notes": False,
    }
    try:
        release = http_ssl.http_post_json(url, headers=_headers(), payload=payload, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            existente = _obter_release_por_tag(tag)
            if existente:
                return existente
        raise RuntimeError(_mensagem_erro_github(exc)) from exc
    if not release or not release.get("id"):
        raise RuntimeError(
            "GitHub não retornou dados da release. "
            "Verifique se o token tem permissão de Releases no repositório "
            f"{UPDATE_GITHUB_OWNER}/{UPDATE_GITHUB_REPO}."
        )
    return release


def _deletar_asset(asset_id):
    url = f"https://api.github.com/repos/{UPDATE_GITHUB_OWNER}/{UPDATE_GITHUB_REPO}/releases/assets/{asset_id}"
    try:
        http_ssl.http_request("DELETE", url, headers=_headers(), timeout=60)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_mensagem_erro_github(exc)) from exc


def _upload_asset_release(release_id, caminho_exe, nome_asset, status_callback=None):
    nome = urllib.parse.quote(str(nome_asset), safe="")
    url = (
        f"https://uploads.github.com/repos/{UPDATE_GITHUB_OWNER}/{UPDATE_GITHUB_REPO}"
        f"/releases/{release_id}/assets?name={nome}"
    )
    headers = _headers_upload_asset()
    tamanho_mb = Path(caminho_exe).stat().st_size / (1024 * 1024)
    if status_callback:
        status_callback(
            f'Enviando {nome_asset} ({tamanho_mb:.0f} MB) — pode levar até 20 minutos...'
        )
    try:
        http_ssl.http_upload_arquivo(
            url,
            headers=headers,
            arquivo=str(caminho_exe),
            timeout=1800,
        )
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_mensagem_erro_github(exc)) from exc
    except Exception as exc:
        texto = str(exc).strip() or repr(exc)
        if '10053' in texto or '10054' in texto:
            raise RuntimeError(
                'Conexão interrompida durante o envio do .exe.\n\n'
                'A release pode ter sido criada sem o arquivo. Tente publicar de novo.\n'
                'Se repetir: desative antivírus temporariamente ou use internet mais estável.'
            ) from exc
        raise


def atualizar_notas_release(status_callback=None):
    """Atualiza só o texto da release no GitHub (lista de alterações)."""
    def _status(texto):
        if status_callback:
            status_callback(str(texto))

    if not configuracao_disponivel():
        raise RuntimeError(
            "Configure UPDATE_GITHUB_OWNER e UPDATE_GITHUB_REPO em licenca_config.py."
        )
    if not UPDATE_GITHUB_TOKEN:
        raise RuntimeError("Configure UPDATE_GITHUB_TOKEN ou GITHUB_TOKEN em licenca_config.py.")

    import app_version

    versao = app_version.APP_VERSION
    tag = f"v{versao}"
    titulo = f"Versão {versao}"
    corpo = release_notas.corpo_release(versao)

    _status('Consultando release no GitHub...')
    release = _obter_release_por_tag(tag)
    if not release:
        raise RuntimeError(
            f'Release {tag} não encontrada. Publique o .exe primeiro.'
        )
    release_id = release.get("id")
    if not release_id:
        raise RuntimeError("GitHub não retornou ID da release.")

    _status('Gravando notas da versão...')
    _atualizar_texto_release(release_id, titulo, corpo)

    html_url = release.get("html_url") or (
        f"https://github.com/{UPDATE_GITHUB_OWNER}/{UPDATE_GITHUB_REPO}/releases/tag/{tag}"
    )
    return {
        "tag": tag,
        "versao": versao,
        "release_url": html_url,
        "corpo": corpo,
    }


def publicar_exe_release(caminho_exe=None, notas="", status_callback=None):
    """
    Cria (ou atualiza) uma release no GitHub e envia o .exe.
    Retorna dict com tag, url e nome do asset.
    """
    def _status(texto):
        if status_callback:
            status_callback(str(texto))
    if not configuracao_disponivel():
        raise RuntimeError(
            "Configure UPDATE_GITHUB_OWNER e UPDATE_GITHUB_REPO em licenca_config.py."
        )
    if not UPDATE_GITHUB_TOKEN:
        raise RuntimeError("Configure UPDATE_GITHUB_TOKEN ou GITHUB_TOKEN em licenca_config.py.")

    import app_version

    if caminho_exe:
        caminho = Path(caminho_exe).expanduser()
    else:
        pasta_projeto = Path(__file__).resolve().parent
        caminho = pasta_projeto / "dist" / "lancamento-conta-apagar.exe"
    if not caminho.is_file():
        raise RuntimeError(f"Executável não encontrado:\n{caminho}")

    versao = app_version.APP_VERSION
    tag = f"v{versao}"
    titulo = f"Versão {versao}"
    nome_asset = str(UPDATE_ASSET_NAME or "").strip() or caminho.name
    corpo = notas or release_notas.corpo_release(versao)

    try:
        _status('Consultando release no GitHub...')
        release = _obter_release_por_tag(tag)
        if not release:
            _status(f'Criando release {tag}...')
            release = _criar_release(tag, titulo, corpo)
        else:
            _status(f'Release {tag} encontrada — atualizando notas...')
        release_id = release.get("id")
        if release_id:
            _atualizar_texto_release(release_id, titulo, corpo)
            _status('Notas da versão registradas no GitHub.')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_mensagem_erro_github(exc)) from exc

    if not release_id:
        raise RuntimeError(
            "GitHub não retornou ID da release. "
            f"Confira o token em licenca_config.py e o acesso ao repositório "
            f"{UPDATE_GITHUB_OWNER}/{UPDATE_GITHUB_REPO}."
        )

    release = _obter_release_por_tag(tag) or release
    asset_ja_publicado = any(
        str(asset.get("name") or "").strip().lower() == nome_asset.lower()
        for asset in (release.get("assets") or [])
    )

    if asset_ja_publicado:
        _status('Arquivo .exe já está na release — notas atualizadas.')
    else:
        _upload_asset_release(release_id, caminho, nome_asset, status_callback=_status)

    html_url = release.get("html_url") or f"https://github.com/{UPDATE_GITHUB_OWNER}/{UPDATE_GITHUB_REPO}/releases/tag/{tag}"
    return {
        "tag": tag,
        "versao": versao,
        "asset_name": nome_asset,
        "release_url": html_url,
        "exe_local": str(caminho.resolve()),
    }


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
        detalhe = str(exc)
        if 'certificate' in detalhe.lower() or 'ssl' in detalhe.lower():
            detalhe += (
                ' (no Windows o sistema tenta PowerShell como alternativa; '
                'verifique se PowerShell está habilitado e se antivírus '
                'não bloqueia o programa).'
            )
        raise RuntimeError(f"Falha ao consultar release do GitHub: {detalhe}") from exc

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
