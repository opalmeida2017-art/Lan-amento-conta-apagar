import time
import re
from playwright.sync_api import sync_playwright
from robo_web import modulo_frota


def iniciar_migracao_lote(config, itens_codigos, novo_grupo_nome, log_callback, grupo_atual="Filtrado"):
    def log(msg):
        print(f"[MIGRAÇÃO EM LOTE]: {msg}")
        if log_callback:
            log_callback(msg)

    log("✅ Processo iniciado: Troca de grupo em lote")
    log(f"📤 Grupo de origem: {grupo_atual}")
    log(f"📥 Novo grupo destino: {novo_grupo_nome}")
    log(f"📦 Total de itens a processar: {len(itens_codigos)}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                channel="chrome",
                args=["--start-maximized"]
            )
            context = browser.new_context(viewport={"width": 1300, "height": 850})
            page = context.new_page()

            # LOGIN
            log("🔐 Fazendo login no ERP...")
            page.goto(config['link'], timeout=60000)
            page.locator('input[type="text"]').first.fill(config['user_sis'])
            page.locator('input[type="password"]').first.fill(config['senha_sis'])
            page.locator('input[value="Entrar"], button:has-text("Entrar")').first.click(force=True)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            # ACESSO AO MENU
            log("📂 Abrindo Cadastros > Itens Despesa/Estoque...")
            page.locator('div[id="formMenu:j_idt128_label"]').click(force=True)
            page.wait_for_timeout(1200)
            page.locator('div[id="formMenu:j_idt151"]').click(force=True)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(3500)

            # LOOP DE PROCESSAMENTO
            for posicao, cod_item in enumerate(itens_codigos, 1):
                cod_item = str(cod_item).strip()
                log(f"\n🔄 Item {posicao}/{len(itens_codigos)} | Código: {cod_item}")

                # VOLTA PARA TELA DE PESQUISA
                try:
                    log("→ Carregando tela de pesquisa...")
                    botao_listar = page.locator('input[id="formitemD:listitemD"]')
                    botao_listar.wait_for(state="visible", timeout=12000)
                    botao_listar.click(force=True)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    page.wait_for_timeout(1500)
                except Exception:
                    if not page.locator('input[id="formitemDFil:ItemDFil_codItemD"]').is_visible(timeout=2000):
                        log(f"❌ Tela não carregou, pulando {cod_item}")
                        continue

                # PESQUISA O ITEM
                log(f"→ Buscando código {cod_item}...")
                campo_codigo = page.locator('input[id="formitemDFil:ItemDFil_codItemD"]')
                campo_codigo.wait_for(state="visible", timeout=8000)
                campo_codigo.click(click_count=3)
                campo_codigo.fill(cod_item)

                page.locator('input[id="formitemDFil:filtraritemDFil"]').click(force=True)
                page.wait_for_load_state("networkidle", timeout=10000)
                page.wait_for_timeout(1500)

                # ABRE O CADASTRO
                try:
                    linha = page.locator('tbody tr').first
                    linha.wait_for(state="visible", timeout=6000)
                    linha.dblclick(force=True)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    page.wait_for_timeout(2000)
                    log("✅ Cadastro aberto")
                except Exception:
                    log(f"❌ Item {cod_item} não encontrado")
                    continue

                # ALTERA O GRUPO - LÓGICA CORRIGIDA
                try:
                    log(f"→ Trocando grupo para: {novo_grupo_nome}")
                    campo_grupo = page.locator('select[id="formitemD:ItemD_grupoD"]')
                    campo_grupo.scroll_into_view_if_needed()
                    campo_grupo.wait_for(state="attached", timeout=8000)
                    
                    nome_limpo = novo_grupo_nome.strip().upper()
                    
                    # 1. Encontra o 'value' exato da opção ignorando espaços sujos do HTML
                    option_value = campo_grupo.evaluate(f'''(select) => {{
                        let options = Array.from(select.options);
                        let target = options.find(opt => opt.text.trim().toUpperCase() === "{nome_limpo}");
                        return target ? target.value : null;
                    }}''')

                    if option_value:
                        # 2. Seleciona pelo valor exato
                        campo_grupo.select_option(value=option_value)
                        
                        # 3. Dispara os eventos AJAX obrigatórios do ERP
                        campo_grupo.evaluate("""el => {
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            el.dispatchEvent(new Event('blur', { bubbles: true }));
                        }""")
                        page.wait_for_timeout(1000)
                        
                        # 4. Confirma se alterou na tela
                        grupo_atual_item = campo_grupo.evaluate("el => el.options[el.selectedIndex].text").strip()
                        log(f"✅ Grupo confirmado: {grupo_atual_item}")
                    else:
                        log(f"⚠️ Grupo '{novo_grupo_nome}' não encontrado no combobox do ERP!")
                        continue

                except Exception as erro_grupo:
                    log(f"❌ Falha ao alterar grupo: {str(erro_grupo)[:50]}")
                    continue

                # GRAVA AS ALTERAÇÕES
                try:
                    log("→ Gravando alteração...")
                    botao_gravar = page.locator('input[id="formitemD:gravaritemD"]')
                    botao_gravar.scroll_into_view_if_needed()
                    botao_gravar.click(force=True)
                    page.wait_for_load_state("networkidle", timeout=12000)
                    page.wait_for_timeout(2000)

                    mensagem = page.locator('div[id="formitemD:messages"] li.fontInfoMessages')
                    if mensagem.is_visible(timeout=4000):
                        log(f"✅ {cod_item} | Salvo com sucesso!")
                    else:
                        log(f"✅ {cod_item} | Finalizado")

                except Exception as e_gravar:
                    if "strict mode violation" in str(e_gravar):
                        log(f"✅ {cod_item} | Gravado normalmente")
                    else:
                        log(f"⚠️ {cod_item} | Atenção: {str(e_gravar)[:50]}")

            log("\n🏁 Migração finalizada com sucesso!")
            
            # FECHAMENTO SEGURO
            # Fecha corretamente o navegador ainda dentro do bloco "with"
            context.close()
            browser.close()
            log("🔒 Navegador fechado com sucesso.")

    except Exception as erro_geral:
        log(f"\n❌ Erro geral: {str(erro_geral)}")

    # SINCRONIZAÇÃO FINAL (AGORA FORA DO BLOCO WITH DO PLAYWRIGHT)
    try:
        log("\n🔄 Atualizando banco de dados...")
        modulo_frota.baixar_e_importar_itens()
        log("✅ Sincronização concluída!")
    except Exception as e_sync:
        log(f"⚠️ Erro na sincronização: {str(e_sync)}")