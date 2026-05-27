import time
import re
import database_setup as db
from robo_web.filial_embarque import (
    aplicar_filial_ue_tela_nota,
    abrir_aba_dados_gerais_nota,
    clicar_gravar_nota,
    clicar_finalizar_nota,
    localizar_checkbox_despesa_nota,
    localizar_botao_importar_cp,
    localizar_link_abrir_nota,
    obter_codigos_para_nota,
    processar_itens_nota_interna,
)

def finalizar_gravacao(page, log, dados):
    cod_filial, cod_ue, aplicar_fixo = obter_codigos_para_nota(log)

    log("💾 Clicando em 'Importar para uma Conta a Pagar'...")
    
    # Localiza o botão de importar e clica
    btn_importar = localizar_botao_importar_cp(page)
    btn_importar.click()
    
    log("⏳ Aguardando processamento do ERP (Sucesso ou Erro)...")
    
    for tentativa in range(15): # Aumentei um pouco o tempo de espera para processar erros
        time.sleep(1)
        
        # =================================================================
        # 1. TENTA ACHAR A MENSAGEM DE ERRO
        # =================================================================
        erros_li = page.locator("li")
        if erros_li.count() > 0:
            for i in range(erros_li.count()):
                texto_erro = erros_li.nth(i).text_content().strip()
                texto_lower = texto_erro.lower()
                
                # -------------------------------------------------------------
                # MÁGICA: CORREÇÃO AUTOMÁTICA DE GERENCIAMENTO DE ESTOQUE
                # -------------------------------------------------------------
                if "gerencia estoque" in texto_lower and "inválido" in texto_lower:
                    log("⚠️ Erro detectado: Item não gerencia estoque! Iniciando correção em todos os itens...")
                    
                    # Identifica quantos itens tem na grade para corrigir todos
                    linhas_item = page.locator('tbody[id="formCad:tableItemNota:tb"] > tr.rf-dt-r')
                    total_itens = linhas_item.count()
                    
                    for idx_fix in range(total_itens):
                        log(f"   -> Ajustando gerenciamento do Item {idx_fix + 1}...")
                        # Localiza a linha do item e o ícone de edição
                        linha_item = page.locator(f'tr[id="formCad:tableItemNota:{idx_fix}"]')
                        
                        # Abre o cadastro do item em uma nova aba
                        with page.context.expect_page() as nova_aba_item:
                            linha_item.locator('img[title="Inserir/Alterar"]').click()
                        
                        aba_item = nova_aba_item.value
                        aba_item.wait_for_load_state("networkidle")
                        
                        # Localiza o Select e muda para "S" (Gerencia)
                        sel_estoque = aba_item.locator('select[id="formitemD:ItemD_gerenciaEstoque"]')
                        if sel_estoque.count() > 0:
                            sel_estoque.select_option(value="S")
                            log(f"      - Item {idx_fix + 1}: Alterado para 'Gerencia' [S]")
                            
                            # Clica em Gravar dentro da aba do item
                            aba_item.locator('input[id="formitemD:gravaritemD"]').click()
                            time.sleep(2) # Espera o ERP processar o salvamento
                        
                        aba_item.close() # Fecha a aba de edição
                    
                    page.bring_to_front()
                    log("✅ Todos os itens foram corrigidos! Tentando importar a nota novamente...")
                    btn_importar.click() # Clica no botão de importar de novo
                    time.sleep(2)
                    break # Sai do loop de leitura de erros e volta ao monitoramento principal
                
                # OUTROS ERROS (BLOQUEIO, ETC)
                if "bloqueado" in texto_lower or "inválido" in texto_lower or "selecionar novamente" in texto_lower:
                    log(f"⚠️ ERRO DETECTADO: {texto_erro}")
                    db.registrar_erro_nota_painel(dados, texto_erro)

                    log("⬅️ Clicando em Voltar...")
                    btn_voltar = page.locator('input[value="Voltar"]')
                    if btn_voltar.count() > 0:
                        btn_voltar.first.click(force=True)
                    return False

        # =================================================================
        # 2. TENTA ACHAR O SUCESSO E PROCESSAR A FINALIZAÇÃO
        # =================================================================
        link_sucesso = localizar_link_abrir_nota(page)
        if link_sucesso.count() > 0 and link_sucesso.first.is_visible():
            # ... (Mantenha o seu código de sucesso aqui igual ao anterior) ...
            texto_sucesso = link_sucesso.first.text_content()
            codigo_interno = re.search(r'\d+', texto_sucesso).group()
            log(f"⭐⭐ SUCESSO! Código Gerado: {codigo_interno}")

            dados['status'] = "Importado"
            dados['codigo_interno'] = codigo_interno
            dados['erro_importacao'] = ""
            db.atualizar_nota_raspada(dados)

            log(f"📝 Abrindo a nota {codigo_interno} para finalização...")
            
            with page.context.expect_page() as nova_aba_info:
                link_sucesso.first.click()
            
            nova_aba = nova_aba_info.value
            nova_aba.wait_for_load_state("networkidle")
            time.sleep(2)

            if dados.get('codigo_negocio_veiculo') == "2":
                log("   🚚 Veículo FRETE: Desmarcando flag 'Despesa'...")
                checkbox_despesa = localizar_checkbox_despesa_nota(nova_aba)
                try:
                    if checkbox_despesa.count() > 0 and checkbox_despesa.is_checked():
                        checkbox_despesa.click()
                except Exception:
                    pass
                time.sleep(1.5)
                clicar_gravar_nota(nova_aba, log)
                try: nova_aba.locator('li', has_text="Dados alterados com sucesso").wait_for(state="visible", timeout=8000)
                except: pass

            if aplicar_fixo:
                if not aplicar_filial_ue_tela_nota(nova_aba, log, cod_filial, cod_ue):
                    msg = 'Não foi possível aplicar Filial/UE na tela principal da nota.'
                    log(f'   ❌ {msg}')
                    db.registrar_erro_nota_painel(dados, msg)
                    try:
                        nova_aba.close()
                    except Exception:
                        pass
                    page.bring_to_front()
                    btn_voltar = page.locator('input[value="Voltar"]')
                    if btn_voltar.count() > 0 and btn_voltar.first.is_visible():
                        btn_voltar.first.click(force=True)
                    return False
                if not processar_itens_nota_interna(nova_aba, log, cod_ue):
                    msg = 'Não foi possível aplicar a UE em todos os itens da nota.'
                    log(f'   ❌ {msg}')
                    db.registrar_erro_nota_painel(dados, msg)
                    try:
                        nova_aba.close()
                    except Exception:
                        pass
                    page.bring_to_front()
                    btn_voltar = page.locator('input[value="Voltar"]')
                    if btn_voltar.count() > 0 and btn_voltar.first.is_visible():
                        btn_voltar.first.click(force=True)
                    return False

            if not abrir_aba_dados_gerais_nota(nova_aba, log):
                msg = 'Não foi possível voltar para a aba 1. Dados Gerais antes de finalizar.'
                log(f'   ❌ {msg}')
                db.registrar_erro_nota_painel(dados, msg)
                try:
                    nova_aba.close()
                except Exception:
                    pass
                page.bring_to_front()
                btn_voltar = page.locator('input[value="Voltar"]')
                if btn_voltar.count() > 0 and btn_voltar.first.is_visible():
                    btn_voltar.first.click(force=True)
                return False

            if not clicar_finalizar_nota(nova_aba, log):
                msg = 'Botão/ícone de Finalizar não encontrado na aba principal da nota.'
                log(f'   ❌ {msg}')
                db.registrar_erro_nota_painel(dados, msg)
                try:
                    nova_aba.close()
                except Exception:
                    pass
                page.bring_to_front()
                btn_voltar = page.locator('input[value="Voltar"]')
                if btn_voltar.count() > 0 and btn_voltar.first.is_visible():
                    btn_voltar.first.click(force=True)
                return False
            
            try:
                nova_aba.locator('li', has_text="finalizada com sucesso").wait_for(state="visible", timeout=10000)
                log("   ✅ Documento finalizado com sucesso!")
            except:
                log("   ⚠️ (Mensagem de finalização não detectada)")

            time.sleep(1)
            nova_aba.close()
            page.bring_to_front()
            
            btn_voltar_extra = page.locator('input[value="Voltar"]')
            if btn_voltar_extra.count() > 0 and btn_voltar_extra.first.is_visible():
                btn_voltar_extra.first.click(force=True)
            return True

    db.registrar_erro_nota_painel(
        dados, 'Falha ao importar para Conta a Pagar (tempo esgotado ou sem resposta do ERP).',
    )
    log('⬅️ Voltando ao painel após falha na importação...')
    btn_voltar = page.locator('input[value="Voltar"]')
    if btn_voltar.count() > 0 and btn_voltar.first.is_visible():
        btn_voltar.first.click(force=True)
    return False