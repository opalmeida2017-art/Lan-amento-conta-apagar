import time
import calendar
from datetime import datetime, timedelta

from .utils import (
    ErroServidorIndisponivel,
    abrir_painel_nfe_compra,
    fazer_login_erp,
    verificar_pagina_erp_ok,
)

TIMEOUT_SUCESSO_CONSULTA_MS = 60000
MAX_TENTATIVAS_CONSULTA = 3
MONITOR_CONSULTA_SEL = 'span[id="formCad:msgEMonitor1"]'

# Mapa de meses para conversão de texto para número
MAPA_MESES = {
    "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12
}

MAPA_NUMERO_PARA_SIGLA = {
    f"{num:02d}": sigla for sigla, num in MAPA_MESES.items()
}


def _formatar_excecao(exc):
    """Evita log vazio quando str(exc) retorna '' (ex.: KeyError(''))."""
    msg = str(exc).strip()
    nome = type(exc).__name__
    if msg:
        return f"{nome}: {msg}"
    return f"{nome} (sem mensagem)"


def _sigla_mes_valida(entrada):
    texto = str(entrada or "").strip()
    if not texto:
        return None
    if texto in MAPA_MESES:
        return texto

    partes = texto.split()
    if len(partes) >= 3:
        numero = partes[0]
        if numero in MAPA_NUMERO_PARA_SIGLA:
            return MAPA_NUMERO_PARA_SIGLA[numero]
        nome = partes[2]
    else:
        nome = partes[0]
        if nome in MAPA_NUMERO_PARA_SIGLA:
            return MAPA_NUMERO_PARA_SIGLA[nome]

    sigla = nome[:3].capitalize()
    if sigla in MAPA_MESES:
        return sigla
    return None


def normalizar_lista_meses(meses):
    """
    Converte entradas de mês (Jan, Janeiro, 06 - Junho, etc.) para siglas válidas.
    """
    if not meses:
        raise ValueError(
            "Nenhum mês informado para consulta SEFAZ. "
            "Abra Parâmetros ERP, selecione Mês/Ano e clique em Salvar Configurações."
        )

    resultado = []
    for item in meses:
        sigla = _sigla_mes_valida(item)
        if not sigla:
            raise ValueError(
                f"Mês inválido ou não informado: '{item}'. "
                "Abra Parâmetros ERP, selecione Mês/Ano e clique em Salvar Configurações."
            )
        if sigla not in resultado:
            resultado.append(sigla)
    return resultado


def resolver_periodo_filtro(mes_escolhido, ano_escolhido):
    """Retorna (meses_siglas, mes_exibicao, ano) a partir dos filtros salvos."""
    ano = str(ano_escolhido or "").strip()
    if not ano:
        raise ValueError(
            "Ano não informado para consulta SEFAZ. "
            "Abra Parâmetros ERP, selecione Mês/Ano e clique em Salvar Configurações."
        )

    partes = str(mes_escolhido or "").strip().split()
    mes_exibicao = partes[2] if len(partes) >= 3 else (partes[0] if partes else "")
    meses = normalizar_lista_meses([mes_escolhido])
    return meses, mes_exibicao or meses[0], ano


def _texto_acao_inexistente(texto):
    tl = (texto or '').lower()
    return 'ação inexistente' in tl or 'acao inexistente' in tl


def _texto_sucesso_consulta(texto):
    tl = (texto or '').lower()
    return 'sucesso' in tl or 'conclu' in tl


def _aguardar_mensagem_consulta_nfe(page, log, timeout_seg=60):
    """
    Monitora span#formCad:msgEMonitor1 após clicar em Consultar.
    Retorna ('sucesso'|'acao_inexistente'|'erro'|'timeout', mensagem).
    """
    msg_span = page.locator(MONITOR_CONSULTA_SEL)
    inicio = time.time()
    ultimo_log = ''

    while time.time() - inicio < timeout_seg:
        verificar_pagina_erp_ok(page, log)

        try:
            sucesso_loc = page.locator('text=/sucesso/i').first
            if sucesso_loc.is_visible(timeout=300):
                texto = (sucesso_loc.text_content() or '').strip()
                if texto and _texto_sucesso_consulta(texto):
                    if texto != ultimo_log:
                        log(f'   -> Retorno consulta SEFAZ: {texto}')
                    return 'sucesso', texto
        except Exception:
            pass

        texto = ''
        try:
            if msg_span.is_visible(timeout=500):
                texto = (msg_span.text_content() or '').strip()
        except Exception:
            pass

        if texto:
            if texto != ultimo_log:
                log(f'   -> Retorno consulta SEFAZ: {texto}')
                ultimo_log = texto

            if _texto_sucesso_consulta(texto):
                return 'sucesso', texto

            if _texto_acao_inexistente(texto):
                log(
                    "   ℹ️ ERP retornou 'Ação Inexistente' após consulta — "
                    'seguindo com o fluxo.'
                )
                return 'acao_inexistente', texto

            tl = texto.lower()
            if 'erro grave' in tl or (
                'erro' in tl and 'aguarde' not in tl and 'iniciando consulta' not in tl
            ):
                return 'erro', texto

        time.sleep(0.4)

    return 'timeout', ultimo_log


def _preencher_filtros_consulta(page, data_ini, data_fim):
    """Preenche os filtros do painel antes da consulta."""
    page.locator('input[id="formCad:filtroDataIni:filtroDataIniInputDate"]').fill(data_ini)
    page.locator('input[id="formCad:filtroDataFim:filtroDataFimInputDate"]').fill(data_fim)
    page.locator('select[name="formCad:j_idt47"]').select_option(value="0")


def _executar_consulta_periodo(page, log, data_ini, data_fim, nome_empresa, descricao_periodo):
    for tentativa in range(1, MAX_TENTATIVAS_CONSULTA + 1):
        log(f"Consultando período: {data_ini} a {data_fim} para {nome_empresa}")
        _preencher_filtros_consulta(page, data_ini, data_fim)

        log("Clicando no botão 1. Consultar...")
        page.locator(r"text=/1\.\s*Consultar/i").first.click(force=True)
        verificar_pagina_erp_ok(page, log)

        try:
            resultado, mensagem = _aguardar_mensagem_consulta_nfe(
                page,
                log,
                timeout_seg=TIMEOUT_SUCESSO_CONSULTA_MS // 1000,
            )
            verificar_pagina_erp_ok(page, log)

            if resultado == 'sucesso':
                log(f"Sucesso na consulta de {descricao_periodo}!")
                time.sleep(0.5)
                return True

            if resultado == 'acao_inexistente':
                log(f"Consulta de {descricao_periodo} — continuando após 'Ação Inexistente'.")
                time.sleep(0.5)
                return True

            if resultado == 'timeout' and tentativa < MAX_TENTATIVAS_CONSULTA:
                log(
                    f"⚠️ Consulta sem confirmação em "
                    f"{TIMEOUT_SUCESSO_CONSULTA_MS // 1000}s "
                    f"(última msg: {mensagem or '—'}). "
                    f"Reiniciando consulta ({tentativa}/{MAX_TENTATIVAS_CONSULTA})..."
                )
                time.sleep(1)
                continue

            if resultado == 'erro':
                raise RuntimeError(
                    f"Erro na consulta SEFAZ de {descricao_periodo}: {mensagem}"
                )

            raise RuntimeError(
                f"Consulta SEFAZ de {descricao_periodo} expirou sem resposta "
                f"(última msg: {mensagem or '—'})"
            )
        except RuntimeError:
            raise
        except Exception as e:
            verificar_pagina_erp_ok(page, log)
            msg = str(e)
            timeout_sem_sucesso = "Timeout" in msg and "text=/sucesso/i" in msg
            if timeout_sem_sucesso and tentativa < MAX_TENTATIVAS_CONSULTA:
                log(
                    f"⚠️ Consulta sem confirmação de sucesso em "
                    f"{TIMEOUT_SUCESSO_CONSULTA_MS // 1000}s. "
                    f"Reiniciando consulta ({tentativa}/{MAX_TENTATIVAS_CONSULTA})..."
                )
                time.sleep(1)
                continue
            raise RuntimeError(
                f"Falha na consulta SEFAZ de {descricao_periodo} após "
                f"{tentativa} tentativa(s): {e}"
            ) from e
    return False


def consultar_sefaz(
    page, config, meses, anos, log,
    ultimos_30_dias=False, hoje_apenas=False, ultimos_15_dias=False,
):
    """
    Realiza o login, navega até o painel e executa o loop de consultas
    pelas empresas e períodos selecionados.
    """
    try:
        log("Acessando o sistema para consulta SEFAZ...")
        fazer_login_erp(page, config, log=log)

        # NAVEGAÇÃO AO PAINEL DE NFE
        log("Navegando até o Painel de NFe (Notas Destinadas)...")
        abrir_painel_nfe_compra(page, log=log)

        # 3. LOOP DE CONSULTAS POR EMPRESA
        combo_empresas = page.locator('select[id="formCad:codEmpresas"]')
        quantidade_opcoes = combo_empresas.locator("option").count()

        log(f"Iniciando consultas para {quantidade_opcoes - 1} empresas...")

        for i in range(1, quantidade_opcoes):
            nome_empresa = combo_empresas.locator("option").nth(i).text_content().strip()
            combo_empresas.select_option(index=i)
            time.sleep(1)

            if ultimos_30_dias:
                hoje = datetime.now()
                inicio = hoje - timedelta(days=30)
                data_ini = inicio.strftime("%d/%m/%Y")
                data_fim = hoje.strftime("%d/%m/%Y")
                _executar_consulta_periodo(
                    page,
                    log,
                    data_ini,
                    data_fim,
                    nome_empresa,
                    "últimos 30 dias",
                )

                continue

            if hoje_apenas:
                hoje = datetime.now()
                ontem = hoje - timedelta(days=1)
                data_ini = ontem.strftime("%d/%m/%Y")
                data_fim = hoje.strftime("%d/%m/%Y")
                _executar_consulta_periodo(
                    page,
                    log,
                    data_ini,
                    data_fim,
                    nome_empresa,
                    "ontem e hoje",
                )
                continue

            if ultimos_15_dias:
                hoje = datetime.now()
                inicio = hoje - timedelta(days=15)
                data_ini = inicio.strftime("%d/%m/%Y")
                data_fim = hoje.strftime("%d/%m/%Y")
                _executar_consulta_periodo(
                    page,
                    log,
                    data_ini,
                    data_fim,
                    nome_empresa,
                    "últimos 15 dias",
                )
                continue

            meses_validos = normalizar_lista_meses(meses)
            for ano in anos:
                for mes_texto in meses_validos:
                    mes_num = MAPA_MESES[mes_texto]
                    ultimo_dia = calendar.monthrange(int(ano), mes_num)[1]
                    data_ini = f"01/{mes_num:02d}/{ano}"
                    data_fim = f"{ultimo_dia}/{mes_num:02d}/{ano}"
                    _executar_consulta_periodo(
                        page,
                        log,
                        data_ini,
                        data_fim,
                        nome_empresa,
                        f"{mes_texto}/{ano}",
                    )

        log("Todas as consultas na SEFAZ foram concluídas com êxito.")
        return True

    except ErroServidorIndisponivel:
        raise
    except Exception as e:
        try:
            verificar_pagina_erp_ok(page, log)
        except ErroServidorIndisponivel:
            raise
        log(f"ERRO NO MODULO SEFAZ: {_formatar_excecao(e)}")
        return False