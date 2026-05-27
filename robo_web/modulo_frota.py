import time
import os
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright
import database_setup as db
from robo_web.erp_lock import ERP_LOCK


def baixar_e_importar_frota(config_override=None):
    with ERP_LOCK:
        return _baixar_e_importar_frota_impl(config_override=config_override)


def _baixar_e_importar_frota_impl(config_override=None):
    # Puxa o código da tabela blindada
    try: config_rel = db.carregar_codigos_relatorios()
    except: config_rel = {}
    codigo_relatorio = str(config_rel.get('rel_veiculo') or '').strip()

    # Agora o print fala a verdade e mostra o número que você digitou!
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciando robô de sincronização de Frota (Relatório {codigo_relatorio})...")
    
    config = config_override or db.carregar_configuracoes()
    if not config or not config['link']:
        print("❌ Sistema não configurado. Impossível baixar frota.")
        return False
    if not codigo_relatorio:
        print("❌ Código do relatório de Veículos não configurado. Ajuste em Parâmetros ERP.")
        return False

    pasta_downloads = os.path.abspath("downloads_erp")
    os.makedirs(pasta_downloads, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        try:
            print(" -> Fazendo login no ERP...")
            page.goto(config['link'])
            page.wait_for_load_state("load")
            page.locator('input[type="text"]').first.fill(config['user_sis'])
            page.locator('input[type="password"]').first.fill(config['senha_sis'])
            page.locator('input[value="Entrar"], button:has-text("Entrar")').first.click()
            page.wait_for_load_state("networkidle")
            
            print(" -> Acessando módulo de Exportações...")
            page.locator('text="Exp./Imp."').first.click()
            time.sleep(1)
            page.locator('text="Cadastro de Exportações"').first.click()
            page.wait_for_load_state("networkidle")
            
            print(f" -> Pesquisando relatório {codigo_relatorio} (Veículos)...")
            campo_codigo = page.locator('text=Código:').locator('xpath=./following::input[1]')
            campo_codigo.fill(codigo_relatorio)
            page.locator('img[src*="search"], img[src*="lupa"], input[type="image"]').first.click()
            
            page.wait_for_selector(f"td:has-text('{codigo_relatorio}')", timeout=15000)
            link_resultado = page.locator(f"td:has-text('{codigo_relatorio}')").locator("xpath=./following-sibling::td[1]").locator("a")
            link_resultado.evaluate("node => node.click()")
            
            with context.expect_page() as new_page_info:
                page.locator('text="Exportar Dados"').evaluate("node => node.click()")
            nova_aba = new_page_info.value
            nova_aba.locator('text="### Link para exportação ###"').first.evaluate("node => node.click()")
            nova_aba.wait_for_load_state("networkidle")
            
            print(" -> Preenchendos os filtros de Data, Veículo e Cavalo...")
            nova_aba.locator('input[id="formrelFilVeicDados:RelFilVeicDados_dataIniInputDate"]').fill("01/01/2000")
            nova_aba.locator('input[id="formrelFilVeicDados:RelFilVeicDados_dataIniInputDate"]').press("Tab")
            nova_aba.locator('select[id="formrelFilVeicDados:RelFilVeicDados_filtroLiberado"]').select_option(value="3")
            nova_aba.locator('select[id="formrelFilVeicDados:RelFilVeicDados_veiculoProprio"]').select_option(value="5")
            nova_aba.locator('select[id="formrelFilVeicDados:RelFilVeicDados_cavalo"]').select_option(value="T")
            
            print(" -> Gerando relatório...")
            nova_aba.locator('input[id*="filtrar"], input[value="Gerar"], input[value="Filtrar"]').first.click(force=True, no_wait_after=True)
            
            selector_link = nova_aba.get_by_text("Clique aqui para visualizar arquivo", exact=False)
            selector_link.wait_for(state="visible", timeout=90000)
            
            caminho_arquivo = os.path.join(pasta_downloads, "relFilVeicDados.xls")
            if os.path.exists(caminho_arquivo): os.remove(caminho_arquivo)
            
            with nova_aba.expect_download(timeout=60000) as download_info:
                selector_link.click()
            download_info.value.save_as(caminho_arquivo)
            print(" ✅ Download concluído!")
            
            print(" -> Lendo a planilha e atualizando o banco de dados...")
            try:
                df = pd.read_excel(caminho_arquivo)
            except Exception:
                with open(caminho_arquivo, 'r', encoding='latin-1') as f:
                    df = pd.read_html(f.read(), decimal=',', thousands='.')[0]
            
            df = df.dropna(subset=['placa']) 
            lista_veiculos = df.to_dict('records')
            db.sincronizar_frota_erp(lista_veiculos)
            print(f" 🌟 SUCESSO! {len(lista_veiculos)} veículos sincronizados.")
            return True
                
        except Exception as e:
            print(f"❌ ERRO NO MÓDULO FROTA: {e}")
            return False
        finally:
            browser.close()


def baixar_e_importar_itens(config_override=None):
    with ERP_LOCK:
        return _baixar_e_importar_itens_impl(config_override=config_override)


def _baixar_e_importar_itens_impl(config_override=None):
    # Puxa o código da tabela blindada
    try: config_rel = db.carregar_codigos_relatorios()
    except: config_rel = {}
    codigo_relatorio = str(config_rel.get('rel_item') or '').strip()

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciando robô de sincronização de Itens (Relatório {codigo_relatorio})...")
    
    config = config_override or db.carregar_configuracoes()
    if not config or not config['link']:
        print("❌ Sistema não configurado. Impossível baixar itens.")
        return False
    if not codigo_relatorio:
        print("❌ Código do relatório de Itens não configurado. Ajuste em Parâmetros ERP.")
        return False

    pasta_downloads = os.path.abspath("downloads_erp")
    os.makedirs(pasta_downloads, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        try:
            print(" -> Fazendo login no ERP...")
            page.goto(config['link'])
            page.wait_for_load_state("load")
            page.locator('input[type="text"]').first.fill(config['user_sis'])
            page.locator('input[type="password"]').first.fill(config['senha_sis'])
            page.locator('input[value="Entrar"], button:has-text("Entrar")').first.click()
            page.wait_for_load_state("networkidle")
            
            print(" -> Acessando módulo de Exportações...")
            page.locator('text="Exp./Imp."').first.click()
            time.sleep(1)
            page.locator('text="Cadastro de Exportações"').first.click()
            
            print(f" -> Pesquisando relatório {codigo_relatorio} (Itens)...")
            campo_codigo = page.locator('text=Código:').locator('xpath=./following::input[1]')
            campo_codigo.fill(codigo_relatorio)
            page.locator('img[src*="search"], img[src*="lupa"], input[type="image"]').first.click()
            
            page.wait_for_selector(f"td:has-text('{codigo_relatorio}')", timeout=15000)
            link_resultado = page.locator(f"td:has-text('{codigo_relatorio}')").locator("xpath=./following-sibling::td[1]").locator("a")
            link_resultado.evaluate("node => node.click()")
            
            with context.expect_page() as new_page_info:
                page.locator('text="Exportar Dados"').evaluate("node => node.click()")
            nova_aba = new_page_info.value
            nova_aba.locator('text="### Link para exportação ###"').first.evaluate("node => node.click()")
            nova_aba.wait_for_load_state("networkidle")
            
            print(" -> Gerando relatório de itens...")
            nova_aba.locator('input[id*="filtrar"], input[value="Gerar"], input[value="Filtrar"]').first.click(force=True, no_wait_after=True)
            
            selector_link = nova_aba.get_by_text("Clique aqui para visualizar arquivo", exact=False)
            selector_link.wait_for(state="visible", timeout=90000)
            
            caminho_arquivo = os.path.join(pasta_downloads, "itemDFil.xls")
            if os.path.exists(caminho_arquivo): os.remove(caminho_arquivo)
            
            with nova_aba.expect_download(timeout=60000) as download_info:
                selector_link.click()
            download_info.value.save_as(caminho_arquivo)
            print(" ✅ Download concluído!")
            
            print(" -> Lendo a planilha de Itens e atualizando o banco de dados...")
            try:
                df = pd.read_excel(caminho_arquivo)
            except Exception:
                with open(caminho_arquivo, 'r', encoding='latin-1') as f:
                    df = pd.read_html(f.read(), decimal=',', thousands='.')[0]
            
            df = df.dropna(subset=['codItemD']) 
            df = df.fillna("")
            lista_itens = df.to_dict('records')
            
            db.sincronizar_itens_erp(lista_itens)
            print(f" 🌟 SUCESSO! {len(lista_itens)} itens sincronizados.")
            return True
                
        except Exception as e:
            print(f"❌ ERRO NO MÓDULO ITENS: {e}")
            return False
        finally:
            browser.close()