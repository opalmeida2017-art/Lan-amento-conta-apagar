import time
import calendar
from datetime import datetime, timedelta

from .utils import ErroServidorIndisponivel, verificar_pagina_erp_ok

TIMEOUT_SUCESSO_CONSULTA_MS = 60000
MAX_TENTATIVAS_CONSULTA = 3

# Mapa de meses para conversão de texto para número
MAPA_MESES = {
    "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12
}


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
            page.locator("text=/sucesso/i").first.wait_for(
                state="visible",
                timeout=TIMEOUT_SUCESSO_CONSULTA_MS,
            )
            verificar_pagina_erp_ok(page, log)
            log(f"Sucesso na consulta de {descricao_periodo}!")
            time.sleep(1)
            return True
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
                time.sleep(2)
                continue
            raise RuntimeError(
                f"Falha na consulta SEFAZ de {descricao_periodo} após "
                f"{tentativa} tentativa(s): {e}"
            ) from e
    return False


def consultar_sefaz(page, config, meses, anos, log, ultimos_30_dias=False, hoje_apenas=False):
    """
    Realiza o login, navega até o painel e executa o loop de consultas
    pelas empresas e períodos selecionados.
    """
    try:
        log("Acessando o sistema para consulta SEFAZ...")
        page.goto(config['link'])
        page.wait_for_load_state("networkidle")
        verificar_pagina_erp_ok(page, log)

        # 1. LOGIN
        log("Realizando login no sistema...")
        page.locator('input[type="text"]').fill(config['user_sis'])
        page.locator('input[type="password"]').fill(config['senha_sis'])
        page.locator('input[value="Entrar"], button:has-text("Entrar")').click()

        time.sleep(3)
        verificar_pagina_erp_ok(page, log)

        # 2. NAVEGAÇÃO AO PAINEL DE NFE
        log("Navegando até o Painel de NFe (Notas Destinadas)...")
        page.locator("text='Painéis' >> visible=true").first.hover()
        time.sleep(1)
        page.locator("text='NFe' >> visible=true").first.hover()
        time.sleep(1)

        page.locator(
            "text='Painel de NFe (Notas de Compras/Destinadas)' >> visible=true"
        ).first.click(force=True)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        verificar_pagina_erp_ok(page, log)

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
                data_hoje = hoje.strftime("%d/%m/%Y")
                _executar_consulta_periodo(
                    page,
                    log,
                    data_hoje,
                    data_hoje,
                    nome_empresa,
                    "Apenas Hoje",
                )
                continue

            for ano in anos:
                for mes_texto in meses:
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
        log(f"ERRO NO MODULO SEFAZ: {str(e)}")
        return False