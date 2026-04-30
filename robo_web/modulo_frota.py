import time
import os
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright
import database_setup as db

def baixar_e_importar_frota():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciando robô de sincronização de Frota (Relatório 117)...")
    
    config = db.carregar_configuracoes()
    if not config or not config['link']:
        print("❌ Sistema não configurado. Impossível baixar frota.")
        return

    pasta_downloads = os.path.abspath("downloads_erp")
    os.makedirs(pasta_downloads, exist_ok=True)
    
    with sync_playwright() as p:
        # Usa o navegador em modo invisível (headless=True) para não atrapalhar o usuário
        browser = p.chromium.launch(headless=True, channel="chrome")
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        try:
            # 1. LOGIN
            print(" -> Fazendo login no ERP...")
            page.goto(config['link'])
            page.wait_for_load_state("load")
            page.locator('input[type="text"]').first.fill(config['user_sis'])
            page.locator('input[type="password"]').first.fill(config['senha_sis'])
            page.locator('input[value="Entrar"], button:has-text("Entrar")').first.click()
            page.wait_for_load_state("networkidle")
            
            # 2. NAVEGAÇÃO PARA EXPORTAÇÕES
            print(" -> Acessando módulo de Exportações...")
            page.locator('text="Exp./Imp."').first.click()
            time.sleep(1)
            page.locator('text="Cadastro de Exportações"').first.click()
            page.wait_for_load_state("networkidle")
            
            # 3. BUSCANDO RELATÓRIO 117
            print(" -> Pesquisando relatório 117...")
            campo_codigo = page.locator('text=Código:').locator('xpath=./following::input[1]')
            campo_codigo.fill("117")
            page.locator('img[src*="search"], img[src*="lupa"], input[type="image"]').first.click()
            
            page.wait_for_selector("td:has-text('117')", timeout=15000)
            link_resultado = page.locator("td:has-text('117')").locator("xpath=./following-sibling::td[1]").locator("a")
            link_resultado.evaluate("node => node.click()")
            page.wait_for_load_state("networkidle")
            
            # 4. ABRINDO A TELA DO RELATÓRIO
            with context.expect_page() as new_page_info:
                page.locator('text="Exportar Dados"').evaluate("node => node.click()")
            nova_aba = new_page_info.value
            nova_aba.wait_for_load_state("networkidle")
            
            nova_aba.locator('text="### Link para exportação ###"').first.evaluate("node => node.click()")
            nova_aba.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 5. PREENCHENDO OS FILTROS CIRÚRGICOS
            print(" -> Preenchendos os filtros de Data, Veículo e Cavalo...")
            nova_aba.locator('input[id="formrelFilVeicDados:RelFilVeicDados_dataIniInputDate"]').fill("01/01/2000")
            nova_aba.locator('input[id="formrelFilVeicDados:RelFilVeicDados_dataIniInputDate"]').press("Tab")
            
            nova_aba.locator('select[id="formrelFilVeicDados:RelFilVeicDados_filtroLiberado"]').select_option(value="3")
            nova_aba.locator('select[id="formrelFilVeicDados:RelFilVeicDados_veiculoProprio"]').select_option(value="5")
            nova_aba.locator('select[id="formrelFilVeicDados:RelFilVeicDados_cavalo"]').select_option(value="T")
            
            # 6. CLICANDO EM GERAR E BAIXANDO
            print(" -> Gerando relatório...")
            nova_aba.locator('input[id*="filtrar"], input[value="Gerar"], input[value="Filtrar"]').first.click(force=True, no_wait_after=True)
            
            selector_link = nova_aba.get_by_text("Clique aqui para visualizar arquivo", exact=False)
            selector_link.wait_for(state="visible", timeout=90000)
            
            caminho_arquivo = os.path.join(pasta_downloads, "relFilVeicDados.xls")
            if os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo) # Apaga o antigo antes de baixar o novo
            
            with nova_aba.expect_download(timeout=60000) as download_info:
                selector_link.click()
            download_info.value.save_as(caminho_arquivo)
            print(" ✅ Download concluído!")
            
            # 7. IMPORTAÇÃO COM PANDAS
            print(" -> Lendo a planilha e atualizando o banco de dados...")
            try:
                # O Pandas tenta ler como HTML primeiro (comum em sistemas JSF/Sefaz)
                df = pd.read_html(caminho_arquivo)[0]
            except Exception:
                # Se falhar, lê como Excel nativo
                df = pd.read_excel(caminho_arquivo)
                
            # Limpa valores nulos e converte a tabela para uma lista de dicionários
            df = df.dropna(subset=['placa']) 
            lista_veiculos = df.to_dict('records')
            
            sucesso = db.sincronizar_frota_erp(lista_veiculos)
            
            if sucesso:
                print(f" 🌟 SUCESSO! {len(lista_veiculos)} veículos sincronizados com o banco local.")
            else:
                print(" ❌ Falha ao salvar os dados no banco SQLite.")
                
        except Exception as e:
            print(f"❌ ERRO GERAL NO MÓDULO FROTA: {e}")
        finally:
            browser.close()