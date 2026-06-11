# -*- coding: utf-8 -*-
"""Notas de cada versão — exibidas na release do GitHub ao publicar o .exe."""

import re
import subprocess
from pathlib import Path

NOTAS_POR_VERSAO = {
    "1.0.2": [
        "Ajustes no painel de execução",
        "Inclusão de limite de linhas nos painéis",
        "Melhorias na tela de configurações",
        "Preparação da atualização automática do executável",
    ],
    "1.1.8": [
        "Correção da atualização automática do executável (SSL e conexão com GitHub)",
        "Ajustes no painel de execução e no painel de licenças",
        "KM obrigatório para combustível em frota, agregado e terceiro",
        "Placa e KM do painel têm prioridade sobre a observação da NFe",
        "Combustíveis: Arla e Diesel S500 com códigos 7 e 444 no mesmo campo",
        "licenca_config.py incluído na pasta de distribuição (dist)",
        "Painel de licenças: publicar .exe e alterar licenças no GitHub pelo botão",
    ],
    "1.1.9": [
        "Envio automático de suporte alterado para uma vez ao dia às 17:00",
        "Relatório automático de suporte passa a incluir do dia anterior até o dia atual",
    ],
    "1.2.0": [
        "Botão Lançar nota em lote no painel de automação NFe (várias notas separadas por vírgula)",
        "Robô processa cada nota do lote em sequência, com o mesmo fluxo do lançamento individual",
        "Notas de release incluídas automaticamente ao gerar o .exe pelo arquivo .spec",
    ],
}


def _normalizar_item(item):
    texto = str(item or "").strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def itens_versao(versao):
    return list(NOTAS_POR_VERSAO.get(str(versao or "").strip(), []))


def _todos_itens_documentados():
    itens = []
    for lista in NOTAS_POR_VERSAO.values():
        itens.extend(lista or [])
    return [_normalizar_item(item).lower() for item in itens if _normalizar_item(item)]


def _filtrar_itens_ja_documentados(itens):
    """Evita repetir nas notas auto-geradas o que já consta em versões anteriores."""
    documentados = _todos_itens_documentados()
    filtrados = []
    for item in itens or []:
        texto = _normalizar_item(item)
        if not texto:
            continue
        chave = texto.lower()
        if any(chave in doc or doc in chave for doc in documentados):
            continue
        if "suporte" in chave and any("suporte" in doc for doc in documentados):
            continue
        filtrados.append(texto)
    return filtrados


def corpo_release(versao, notas_extras=None):
    """Texto da release no GitHub (lista com marcadores, igual v1.0.2)."""
    itens = itens_versao(versao)
    if notas_extras:
        itens = itens + [str(x).strip() for x in notas_extras if str(x).strip()]
    if not itens:
        return f"Atualização V.{versao}"
    return "\n".join(f"- {item}" for item in itens)


_ARQ_NOTAS = Path(__file__).resolve().parent / "release_notas.py"
_MARCADOR_FIM_DICT = "\n}\n\n\ndef _normalizar_item"


def _filtrar_mensagens_git(mensagens):
    ignorar_prefixos = (
        "release ",
        "merge ",
        "commit:",
        "wip",
    )
    ignorar_exatos = {
        "atualizar",
        "sua mensagem descrevendo o que mudou",
    }
    vistos = set()
    itens = []
    for msg in mensagens:
        texto = _normalizar_item(msg)
        if not texto:
            continue
        chave = texto.lower()
        if chave in ignorar_exatos:
            continue
        if any(chave.startswith(prefixo) for prefixo in ignorar_prefixos):
            continue
        if chave in vistos:
            continue
        vistos.add(chave)
        itens.append(texto)
    return itens


def _executar_git(args, cwd):
    try:
        resultado = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if resultado.returncode != 0:
        return []
    return [linha.strip() for linha in (resultado.stdout or "").splitlines() if linha.strip()]


def coletar_itens_git(versao_antiga, raiz=None):
    """Tenta montar a lista de alterações a partir dos commits git."""
    pasta = Path(raiz or Path(__file__).resolve().parent)
    if not (pasta / ".git").exists():
        return []

    tag = f"v{str(versao_antiga or '').strip()}"
    mensagens = _executar_git(
        ["log", f"{tag}..HEAD", "--pretty=format:%s", "--no-merges"],
        pasta,
    )
    if not mensagens:
        ultima_tag = _executar_git(
            ["describe", "--tags", "--abbrev=0"],
            pasta,
        )
        if ultima_tag:
            mensagens = _executar_git(
                ["log", f"{ultima_tag[0]}..HEAD", "--pretty=format:%s", "--no-merges"],
                pasta,
            )
    if not mensagens:
        mensagens = _executar_git(
            ["log", "-5", "--pretty=format:%s", "--no-merges"],
            pasta,
        )

    itens = _filtrar_mensagens_git(mensagens)
    itens = _filtrar_itens_ja_documentados(itens)
    if _executar_git(["status", "--porcelain"], pasta):
        resumo = _executar_git(["diff", "--stat", "--", "."], pasta)
        if resumo:
            itens.insert(0, "Alterações locais ainda não commitadas neste build")
    return itens


def _versao_ja_cadastrada(conteudo, versao):
    return re.search(rf'["\']{re.escape(str(versao))}["\']\s*:', conteudo) is not None


def _formatar_bloco_versao(versao, itens):
    linhas = [f'    "{versao}": [']
    for item in itens:
        texto = str(item).replace("\\", "\\\\").replace('"', '\\"')
        linhas.append(f'        "{texto}",')
    linhas.append("    ],")
    return "\n".join(linhas)


def preparar_notas_build(versao_antiga, versao_nova, raiz=None):
    """
    Garante entrada em NOTAS_POR_VERSAO para a versão do build.
    Chamado automaticamente pelo .spec ao gerar o .exe.
    """
    versao_nova = str(versao_nova or "").strip()
    if not versao_nova:
        return []

    arquivo = Path(raiz or Path(__file__).resolve().parent) / "release_notas.py"
    conteudo = arquivo.read_text(encoding="utf-8")
    if _versao_ja_cadastrada(conteudo, versao_nova):
        return itens_versao(versao_nova)

    itens = coletar_itens_git(versao_antiga, raiz=arquivo.parent)
    itens = _filtrar_itens_ja_documentados(itens)
    if not itens:
        itens = [f"Atualização V.{versao_nova}"]

    marcador = _MARCADOR_FIM_DICT
    if marcador not in conteudo:
        raise RuntimeError("Estrutura de release_notas.py não reconhecida para inclusão automática.")

    bloco = ",\n" + _formatar_bloco_versao(versao_nova, itens)
    novo_conteudo = conteudo.replace(marcador, bloco + marcador, 1)
    arquivo.write_text(novo_conteudo, encoding="utf-8")

    NOTAS_POR_VERSAO[versao_nova] = list(itens)
    return list(itens)
