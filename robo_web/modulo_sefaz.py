import time
import calendar

from .utils import ErroServidorIndisponivel, verificar_pagina_erp_ok

# Mapa de meses para conversão de texto para número
MAPA_MESES = {
    "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12
}

def consultar_sefaz(page, config, meses, anos, log):
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
        # Hover nos menus para abrir as opções
        page.locator("text='Painéis' >> visible=true").first.hover()
        time.sleep(1)
        page.locator("text='NFe' >> visible=true").first.hover()
        time.sleep(1)
        
        # Clique no link final
        page.locator("text='Painel de NFe (Notas de Compras/Destinadas)' >> visible=true").first.click(force=True)
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
            time.sleep(1) # Aguarda o sistema processar a troca de empresa

            for ano in anos:
                for mes_texto in meses:
                    mes_num = MAPA_MESES[mes_texto]
                    ultimo_dia = calendar.monthrange(int(ano), mes_num)[1]
                    
                    data_ini = f"01/{mes_num:02d}/{ano}"
                    data_fim = f"{ultimo_dia}/{mes_num:02d}/{ano}"

                    log(f"Consultando período: {data_ini} a {data_fim} para {nome_empresa}")

                    # --- CORREÇÃO CIRÚRGICA: IDS EXATOS ---
                    # Preenche os campos de data ignorando campos duplicados ou ocultos
                    page.locator('input[id="formCad:filtroDataIni:filtroDataIniInputDate"]').fill(data_ini)
                    page.locator('input[id="formCad:filtroDataFim:filtroDataFimInputDate"]').fill(data_fim)
                    
                    # Aplica filtro de manifestação: "Não" (value="0")
                    # Usamos o nome exato que o sistema espera
                    page.locator('select[name="formCad:j_idt47"]').select_option(value="0") 
                    
                    # Clica no botão Consultar
                    log("Clicando no botão 1. Consultar...")
                    page.locator(r"text=/1\.\s*Consultar/i").first.click(force=True)
                    verificar_pagina_erp_ok(page, log)

                    page.locator("text=/sucesso/i").first.wait_for(state="visible", timeout=60000)
                    verificar_pagina_erp_ok(page, log)
                    log(f"Sucesso na consulta de {mes_texto}/{ano}!")
                    time.sleep(1)

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