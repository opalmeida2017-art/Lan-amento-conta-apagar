"""HTTPS com certifi; no Windows usa PowerShell se o SSL do Python falhar."""
import json
import os
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def _erro_ssl(exc):
    texto = str(exc).lower()
    return (
        'certificate' in texto
        or 'ssl' in texto
        or 'certificado' in texto
    )


def _erro_conexao(exc):
    texto = str(exc).lower()
    marcadores = (
        '10053', '10054', '10060', 'timed out', 'timeout',
        'connection', 'conexão', 'conexao', 'broken pipe', 'reset',
        'anulada', 'abortada', 'forcibly closed',
    )
    return any(m in texto for m in marcadores) or isinstance(
        exc, (TimeoutError, ConnectionError, BrokenPipeError, OSError),
    )


def _caminho_certifi():
    try:
        import certifi

        cafile = certifi.where()
        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', '')
            for candidato in (
                os.path.join(meipass, 'certifi', 'cacert.pem'),
                os.path.join(meipass, os.path.basename(cafile)),
            ):
                if candidato and os.path.isfile(candidato):
                    return candidato
        return cafile
    except ImportError:
        return None


def criar_contexto_ssl():
    cafile = _caminho_certifi()
    if cafile:
        try:
            return ssl.create_default_context(cafile=cafile)
        except ssl.SSLError:
            pass
    return ssl.create_default_context()


def _escapar_ps(texto):
    return str(texto or '').replace("'", "''")


def _executar_powershell(script, timeout=300):
    caminho = Path(tempfile.gettempdir()) / 'automacao_nfe_http.ps1'
    caminho.write_text(script, encoding='utf-8-sig')
    try:
        resultado = subprocess.run(
            [
                'powershell',
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-File',
                str(caminho),
            ],
            capture_output=True,
            timeout=timeout,
        )
        if resultado.returncode != 0:
            saida = (resultado.stdout or b'') + (resultado.stderr or b'')
            texto = saida.decode('utf-8-sig', errors='replace').strip()
            raise RuntimeError(
                texto or f'PowerShell falhou (código {resultado.returncode})',
            )
        return resultado.stdout
    finally:
        try:
            caminho.unlink(missing_ok=True)
        except OSError:
            pass


def _curl_disponivel():
    if os.name != 'nt':
        return False
    try:
        resultado = subprocess.run(
            ['curl.exe', '--version'],
            capture_output=True,
            timeout=10,
        )
        return resultado.returncode == 0
    except Exception:
        return False


def _http_upload_curl(url, headers, arquivo, timeout):
    caminho = str(Path(arquivo).resolve())
    headers = dict(headers or {})
    headers['Content-Type'] = 'application/octet-stream'
    headers.setdefault('Accept', 'application/vnd.github+json')
    cmd = [
        'curl.exe',
        '-sS',
        '-f',
        '-L',
        '--max-time',
        str(int(timeout)),
        '-X',
        'POST',
        '-H',
        'Expect:',
        '--data-binary',
        f'@{caminho}',
    ]
    for chave, valor in headers.items():
        cmd.extend(['-H', f'{chave}: {valor}'])
    cmd.append(url)
    resultado = subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout + 120,
    )
    if resultado.returncode != 0:
        erro = (resultado.stderr or resultado.stdout or b'').decode(
            'utf-8', errors='replace',
        ).strip()
        raise RuntimeError(erro or f'curl falhou (código {resultado.returncode})')
    return b'', 200


def _http_get_json_powershell(url, headers, timeout):
    linhas_hdr = []
    for chave, valor in (headers or {}).items():
        linhas_hdr.append(f"$h['{_escapar_ps(chave)}'] = '{_escapar_ps(valor)}'")
    bloco_hdr = '\n'.join(linhas_hdr) if linhas_hdr else ''
    script = f"""
$ErrorActionPreference = 'Stop'
$h = @{{}}
{bloco_hdr}
$r = Invoke-RestMethod -Uri '{_escapar_ps(url)}' -Headers $h -Method Get -TimeoutSec {int(timeout)}
$r | ConvertTo-Json -Depth 50 -Compress
"""
    saida = _executar_powershell(script, timeout=timeout + 30)
    texto = saida.decode('utf-8-sig', errors='replace').strip()
    return json.loads(texto)


def _http_download_powershell(url, headers, destino, timeout):
    linhas_hdr = []
    for chave, valor in (headers or {}).items():
        linhas_hdr.append(f"$h['{_escapar_ps(chave)}'] = '{_escapar_ps(valor)}'")
    bloco_hdr = '\n'.join(linhas_hdr) if linhas_hdr else ''
    dest = str(Path(destino).resolve()).replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
$h = @{{}}
{bloco_hdr}
Invoke-WebRequest -Uri '{_escapar_ps(url)}' -Headers $h -Method Get -OutFile '{dest}' -UseBasicParsing -TimeoutSec {int(timeout)}
"""
    _executar_powershell(script, timeout=timeout + 60)


def _http_get_urllib(url, headers, timeout):
    req = urllib.request.Request(url, headers=headers, method='GET')
    with urllib.request.urlopen(
        req, timeout=timeout, context=criar_contexto_ssl(),
    ) as resp:
        return resp.read()


def http_get(url, headers=None, timeout=30):
    """GET HTTPS — Python/certifi; se SSL falhar no Windows, usa PowerShell."""
    headers = dict(headers or {})
    try:
        return _http_get_urllib(url, headers, timeout)
    except Exception as exc:
        if os.name != 'nt' or not _erro_ssl(exc):
            raise
        dados = _http_get_json_powershell(url, headers, timeout)
        return json.dumps(dados, ensure_ascii=False).encode('utf-8')


def http_download(url, headers, destino, timeout=300):
    """Download para arquivo — com fallback PowerShell no Windows."""
    headers = dict(headers or {})
    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        total = 0
        with urllib.request.urlopen(
            req, timeout=timeout, context=criar_contexto_ssl(),
        ) as resp:
            with open(destino, 'wb') as arquivo:
                while True:
                    bloco = resp.read(1024 * 256)
                    if not bloco:
                        break
                    arquivo.write(bloco)
                    total += len(bloco)
        return total
    except Exception as exc:
        if os.name != 'nt' or not _erro_ssl(exc):
            raise
        _http_download_powershell(url, headers, destino, timeout)
        return Path(destino).stat().st_size if Path(destino).exists() else 0


def http_get_json(url, headers=None, timeout=30):
    headers = dict(headers or {})
    try:
        dados = _http_get_urllib(url, headers, timeout)
        texto = dados.decode('utf-8-sig', errors='replace').strip()
        return json.loads(texto)
    except Exception as exc:
        if os.name != 'nt' or not _erro_ssl(exc):
            raise
        return _http_get_json_powershell(url, headers, timeout)


def _http_request_urllib(method, url, headers, data, timeout):
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(
        req, timeout=timeout, context=criar_contexto_ssl(),
    ) as resp:
        return resp.read(), getattr(resp, 'status', 200)


def _http_request_powershell(method, url, headers, data, timeout, arquivo=None):
    headers = dict(headers or {})
    content_type = headers.pop('Content-Type', None) or headers.pop('content-type', None)
    linhas_hdr = []
    for chave, valor in headers.items():
        linhas_hdr.append(f"$h['{_escapar_ps(chave)}'] = '{_escapar_ps(valor)}'")
    bloco_hdr = '\n'.join(linhas_hdr) if linhas_hdr else ''
    metodo = _escapar_ps(method.upper())
    uri = _escapar_ps(url)
    if arquivo:
        caminho = str(Path(arquivo).resolve()).replace("'", "''")
        ct = _escapar_ps(content_type or 'application/octet-stream')
        script = f"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$uri = '{uri}'
$caminho = '{caminho}'
$h = @{{}}
{bloco_hdr}
try {{
    Invoke-WebRequest -Uri $uri -Headers $h -Method {metodo} -InFile $caminho -ContentType '{ct}' -TimeoutSec {int(timeout)} -UseBasicParsing | Out-Null
    Write-Output 'OK'
}} catch {{
    Write-Error ($_.Exception.Message)
    if ($_.ErrorDetails.Message) {{ Write-Error $_.ErrorDetails.Message }}
    exit 1
}}
"""
    elif data is not None:
        dest = Path(tempfile.gettempdir()) / 'automacao_nfe_http_body.bin'
        dest.write_bytes(data)
        caminho_body = str(dest.resolve()).replace("'", "''")
        script = f"""
$ErrorActionPreference = 'Stop'
$h = @{{}}
{bloco_hdr}
$body = [System.IO.File]::ReadAllBytes('{caminho_body}')
$r = Invoke-RestMethod -Uri '{uri}' -Headers $h -Method {metodo} -Body $body -TimeoutSec {int(timeout)}
if ($r -is [string]) {{ $r }} else {{ $r | ConvertTo-Json -Depth 50 -Compress }}
"""
    else:
        script = f"""
$ErrorActionPreference = 'Stop'
$h = @{{}}
{bloco_hdr}
$r = Invoke-RestMethod -Uri '{uri}' -Headers $h -Method {metodo} -TimeoutSec {int(timeout)}
if ($r -is [string]) {{ $r }} else {{ $r | ConvertTo-Json -Depth 50 -Compress }}
"""
    saida = _executar_powershell(script, timeout=timeout + 120)
    texto = saida.decode('utf-8-sig', errors='replace').strip()
    if texto == '"OK"' or texto == 'OK':
        return b'', 200
    try:
        return json.dumps(json.loads(texto), ensure_ascii=False).encode('utf-8'), 200
    except json.JSONDecodeError:
        return texto.encode('utf-8'), 200


def _http_upload_urllib_streaming(url, headers, arquivo, timeout):
    tamanho = os.path.getsize(arquivo)
    headers = dict(headers or {})
    headers['Content-Type'] = 'application/octet-stream'
    headers.setdefault('Accept', 'application/vnd.github+json')
    headers['Content-Length'] = str(tamanho)
    with open(arquivo, 'rb') as arquivo_bin:
        corpo = arquivo_bin.read()
    req = urllib.request.Request(
        url,
        data=corpo,
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(
        req, timeout=timeout, context=criar_contexto_ssl(),
    ) as resp:
        return resp.read(), getattr(resp, 'status', 200)


def http_upload_arquivo(url, headers=None, arquivo=None, timeout=1800):
    """
    Envia arquivo grande (ex.: .exe) com streaming e retentativas.
    No Windows tenta curl.exe primeiro (mais estável para ~75 MB).
    """
    if not arquivo:
        raise ValueError('Informe o caminho do arquivo para upload.')
    caminho = str(Path(arquivo).resolve())
    if not os.path.isfile(caminho):
        raise FileNotFoundError(f'Arquivo não encontrado: {caminho}')

    headers = dict(headers or {})
    tamanho_mb = os.path.getsize(caminho) / (1024 * 1024)
    erros = []

    if os.name == 'nt' and tamanho_mb >= 5 and _curl_disponivel():
        try:
            return _http_upload_curl(url, headers, caminho, timeout)
        except Exception as exc:
            erros.append(f'curl: {exc}')

    tentativas = 3 if tamanho_mb >= 10 else 2
    for tentativa in range(1, tentativas + 1):
        try:
            return _http_upload_urllib_streaming(url, headers, caminho, timeout)
        except Exception as exc:
            erros.append(f'Python (tentativa {tentativa}): {exc}')
            if os.name == 'nt' and tentativa == tentativas:
                try:
                    return _http_request_powershell(
                        'POST', url, headers, None, timeout, arquivo=caminho,
                    )
                except Exception as ps_exc:
                    erros.append(f'PowerShell: {ps_exc}')
            if tentativa < tentativas:
                time.sleep(4 * tentativa)
                continue

    resumo = '\n\n'.join(erros[-3:]) if erros else 'Falha desconhecida no upload.'
    raise RuntimeError(
        'Não foi possível enviar o .exe para o GitHub.\n\n'
        f'{resumo}\n\n'
        'Alternativa: no GitHub, abra a release v1.1.8 → Edit → '
        'arraste o .exe manualmente.'
    )


def http_request(method, url, headers=None, data=None, timeout=60, arquivo=None):
    """HTTP(S) genérico — Python/certifi; fallback PowerShell no Windows."""
    method = (method or 'GET').upper()
    headers = dict(headers or {})
    if method == 'GET' and data is None and not arquivo:
        return http_get(url, headers, timeout), 200
    if arquivo and method == 'POST':
        return http_upload_arquivo(url, headers=headers, arquivo=arquivo, timeout=timeout)
    try:
        return _http_request_urllib(method, url, headers, data, timeout)
    except Exception as exc:
        if os.name != 'nt' or not (_erro_ssl(exc) or _erro_conexao(exc)):
            raise
        return _http_request_powershell(method, url, headers, data, timeout, arquivo=arquivo)


def http_post_json(url, headers=None, payload=None, timeout=60):
    headers = dict(headers or {})
    headers.setdefault('Content-Type', 'application/json')
    corpo = json.dumps(payload or {}, ensure_ascii=False).encode('utf-8')
    dados, _ = http_request('POST', url, headers=headers, data=corpo, timeout=timeout)
    if not dados:
        return {}
    resultado = json.loads(dados.decode('utf-8-sig', errors='replace'))
    return resultado if isinstance(resultado, dict) else {}


def urlopen(req, timeout=30):
    """Compatível com urllib — leitura única em memória."""
    url = req.full_url if hasattr(req, 'full_url') else req.get_full_url()
    headers = dict(getattr(req, 'headers', {}) or {})
    method = getattr(req, 'method', None) or req.get_method()
    data = getattr(req, 'data', None)
    if method and method.upper() != 'GET':
        conteudo, _ = http_request(method, url, headers=headers, data=data, timeout=timeout)
    else:
        conteudo = http_get(url, headers=headers, timeout=timeout)

    class _Resp:
        def __init__(self, body):
            self._body = body

        def read(self, size=-1):
            if size is None or size < 0:
                return self._body
            chunk = self._body[:size]
            self._body = self._body[size:]
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    return _Resp(conteudo)
