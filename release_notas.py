# -*- coding: utf-8 -*-
"""Notas de cada versão — exibidas na release do GitHub ao publicar o .exe."""

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
}


def itens_versao(versao):
    return list(NOTAS_POR_VERSAO.get(str(versao or "").strip(), []))


def corpo_release(versao, notas_extras=None):
    """Texto da release no GitHub (lista com marcadores, igual v1.0.2)."""
    itens = itens_versao(versao)
    if notas_extras:
        itens = itens + [str(x).strip() for x in notas_extras if str(x).strip()]
    if not itens:
        return f"Atualização V.{versao}"
    return "\n".join(f"- {item}" for item in itens)
