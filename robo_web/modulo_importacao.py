import time
import database_setup as db
from robo_web.utils import abortar_nota_com_erro, ErroServidorIndisponivel, verificar_pagina_erp_ok
from robo_web.modulo_veiculo import processar_veiculo
from robo_web.modulo_km import processar_km
from robo_web.modulo_item import processar_cadastro_item
from robo_web.modulo_gravacao import finalizar_gravacao

def processar_importacao(page, log, notas_processadas=None):
    if notas_processadas is None:
        notas_processadas = set()

    verificar_pagina_erp_ok(page, log)
    log("🔄 Atualizando painel e verificando notas...")
    page.locator('input[id="formCad:buttonAtualizar"]').click()
    time.sleep(3)
    verificar_pagina_erp_ok(page, log)
    
    seletor_linhas = "tbody[id='formCad:tablepnfedestinada:tbn'] tr"
    try:
        page.wait_for_selector(seletor_linhas, state="visible", timeout=10000)
    except:
        log("Nenhuma nota encontrada no painel. Fim do processo.")
        return

    linhas = page.locator(seletor_linhas)
    total_linhas = linhas.count()
    
    for i in range(total_linhas):
        verificar_pagina_erp_ok(page, log)
        linha = page.locator(seletor_linhas).nth(i)

        num_nota = linha.locator("td.rf-edt-td-numNota").text_content().strip()
        celula_status = linha.locator("td.rf-edt-td-status")
        status_texto = celula_status.text_content().strip().upper()

        if num_nota in notas_processadas: 
            continue

        log(f"📋 Analisando Nota: {num_nota} | Status: {status_texto}")

        # ====================================================================
        # CAPTURA DE DADOS DA GRADE (Com seletores exatos do HTML)
        # ====================================================================
        def ler_dado(seletor):
            """Lê o texto do elemento baseado no seletor CSS exato"""
            elemento = linha.locator(seletor)
            if elemento.count() > 0:
                return elemento.first.text_content().strip()
            return ""

        dados = {
            "status": "Processando",
            "num_nota": num_nota,
            "chave_nfe": ler_dado("td.rf-edt-td-chaveNFe"),
            "fornecedor": ler_dado("td.rf-edt-td-forn"),
            "valor": ler_dado("td.rf-edt-td-valor"),
            "data_em": ler_dado("td.rf-edt-td-data"),           # Pega o 07/05/2026
            "sit_nfe": ler_dado("td.rf-edt-td-sitNFe"),         # Pega o 'Autorizada'
            "filial": ler_dado("td.rf-edt-td-filial"),          # Pega o nome da filial
            "user_ins": ler_dado("td[id$=':userInsDT']"),       # Lê pelo final do ID, já que não tem classe!
            "codigo_interno": "",
            "erro_importacao": "",
            "observacao_nfe": ""
        }

        # Nota já no painel e marcada como arquivada — não baixa XML nem importa
        chave_nfe = (dados.get("chave_nfe") or "").strip()
        if chave_nfe and db.verificar_nota_arquiva(chave_nfe):
            log(f"📁 Nota {num_nota} arquivada no painel. Pulando download e importação.")
            notas_processadas.add(num_nota)
            continue

        # ====================================================================
        # LÓGICA DE DOWNLOAD (Checkbox -> Ciência -> Download)
        # ====================================================================
        if "IMPORTAR" not in status_texto and "CANCELAD" not in status_texto:
            log(f"🔍 Nota {num_nota} sem XML. Tentando Download...")
            
            try:
                # 1. Marca o checkbox de seleção da nota
                chk = linha.locator('input[type="checkbox"]')
                if chk.count() > 0:
                    chk.first.check()
                    time.sleep(1)
                
                # 2. Clica no Ciência APENAS se o botão estiver visível (Espera no máximo 2 segundos)
                btn_ciencia = page.locator('input[id="formCad:buttonCiencia"]')
                if btn_ciencia.count() > 0 and btn_ciencia.is_visible(timeout=2000):
                    btn_ciencia.click()
                    log("   -> Botão Ciência clicado. Aguardando...")
                    time.sleep(3)
                else:
                    log("   -> Ciência já realizada anteriormente. Pulando direto para Download...")
                
                # 3. Clica no Download APENAS se o botão estiver visível
                btn_download = page.locator('input[id="formCad:downloadNFe"]')
                if btn_download.count() > 0 and btn_download.is_visible(timeout=2000):
                    btn_download.click()
                    log("   -> Download solicitado. Aguardando retorno da SEFAZ...")
                    time.sleep(6)
                else:
                    log("   ⚠️ Botão de Download não encontrado na tela.")
                    
            except Exception as e:
                log(f"   ⚠️ Falha ao tentar clicar nos botões: {e}")
            
            # Verifica a mensagem da SEFAZ
            msg_span = page.locator('span[id="formCad:msgEMonitorOp"]')
            if msg_span.is_visible():
                texto_sefaz = msg_span.text_content().strip()
                log(f"   -> Retorno SEFAZ: {texto_sefaz}")
                texto_lower = texto_sefaz.lower()

                # CONDIÇÃO 1: ARQUIVO INDISPONÍVEL / CANCELADA (Pula Nota)
                if "indisponivel" in texto_lower or "cancelada" in texto_lower:
                    log(f"   ❌ Erro: Arquivo indisponível.")
                    dados["status"] = "Erro"
                    dados["erro_importacao"] = "Arquivo indisponível para download (Cancelada/Rejeitada)"
                    db.atualizar_nota_raspada(dados)
                    notas_processadas.add(num_nota)
                    continue

                # CONDIÇÃO 2: 10 TENTATIVAS (Registra erro e Pula Nota)
                elif "10 tentativas" in texto_lower:
                    log("   ⚠️ SEFAZ não respondeu (10 tentativas). Registrando erro e pulando...")
                    dados["status"] = "Erro"
                    dados["erro_importacao"] = "SEFAZ não retornou resposta após 10 tentativas."
                    db.atualizar_nota_raspada(dados)
                    notas_processadas.add(num_nota)
                    continue

                # CONDIÇÃO 3: SUCESSO NO DOWNLOAD (Atualiza Painel e Importa)
                elif "sucesso" in texto_lower:
                    log("   ✅ Download processado com sucesso! Atualizando painel para importar...")
                    page.locator('input[id="formCad:buttonAtualizar"]').click()
                    time.sleep(4)
                    return processar_importacao(page, log, notas_processadas)

            # Se a mensagem sumir, for genérica, ou não tiver mensagem de erro
            # recomeça a leitura da tela por segurança para ver o novo status
            return processar_importacao(page, log, notas_processadas)

        # ====================================================================
        # LÓGICA DE IMPORTAÇÃO NORMAL (XML DISPONÍVEL)
        # ====================================================================
        if "IMPORTAR" in status_texto:
            log(f"🚀 Nota {num_nota} pronta! Iniciando fluxo de preenchimento...")
            
            db.salvar_nota_raspada(dados)
            
            linha.locator("a:has-text('Importar')").first.click()
            time.sleep(3)
            
            orquestrar_preenchimento_interno(page, log, dados)
            
            notas_processadas.add(num_nota)
            return processar_importacao(page, log, notas_processadas)

    log("✅ Todas as notas da página atual foram processadas.")
    
def orquestrar_preenchimento_interno(page, log, dados):
    """Função que gerencia o fluxo de preenchimento dentro da nota"""
    select_empresa = page.locator('select[name="formCad:j_idt26"]')
    valor_unidade = select_empresa.evaluate("el => el.value")
    select_unid_mestre = page.locator('select[name="formCad:j_idt31"]')
    
    if valor_unidade != "-":
        select_unid_mestre.select_option(value=valor_unidade)
        log(f"Filial e Unid. Emb. Mestre sincronizadas com Unidade {valor_unidade}")
    
    valor_unid_mestre = select_unid_mestre.evaluate("el => el.value")
    memoria_obs = page.locator('textarea[name="formCad:j_idt51"]').input_value()
    dados['observacao_nfe'] = memoria_obs # Guarda a observação da tela

    linhas_item = page.locator('tbody[id="formCad:tableItemNota:tb"] > tr.rf-dt-r')
    total_itens = linhas_item.count()
    
    modelos_usuario = db.obter_modelos_placa() or ["PLACA: AAA-1A11", "PLAC: AAA-1A11"]

    # ==============================================================
    # 0. O ROBÔ PERGUNTA AO BANCO SE A NOTA É PARA O ESTOQUE
    # ==============================================================
    nota_eh_estoque = db.verificar_nota_estoque(dados['chave_nfe'])

    for idx in range(total_itens):
        log(f"\n========================================================")
        log(f"===> PROCESSANDO ITEM {idx + 1} DE {total_itens}")
        log(f"========================================================")

        item_block = page.locator(f'tr[id="formCad:tableItemNota:{idx}"]')

        if valor_unid_mestre and valor_unid_mestre != "-":
            select_unid_item = item_block.locator('tr').filter(has=page.locator('span', has_text="Unid.Emb.:")).locator('select').first
            if select_unid_item.count() > 0:
                select_unid_item.select_option(value=valor_unid_mestre)

        # ==============================================================
        # FLUXO 1: NOTA MARCADA PARA ESTOQUE
        # ==============================================================
        if nota_eh_estoque:
            log("   📦 Modo ESTOQUE ativado! Pulando validação de placa e KM...")
            
            # 1. Muda o campo de 'Diversos' (D) para 'Estoque' (E)
            sel_ved = item_block.locator(f'select[id="formCad:tableItemNota:{idx}:VED"]')
            if sel_ved.count() > 0:
                sel_ved.select_option(value="E")
                log("   -> Tipo de item alterado para: [E] Estoque")
            
            # 2. Muda a 'Não Prevista' para 'Não' (N)
            sel_prevista = item_block.locator(f'select[id="formCad:tableItemNota:{idx}:naoPrevista"]')
            if sel_prevista.count() > 0:
                sel_prevista.select_option(value="N")
                log("   -> 'Despesa não prevista' alterado para: [N] Não")

            # 3. Força o Negócio para 'Frota' (1)
            sel_negocio = item_block.locator(f'select[id="formCad:tableItemNota:{idx}:negocio"]')
            if sel_negocio.count() > 0:
                sel_negocio.select_option(value="1")
                log("   -> Ramo de Negócio fixado em: [1] FROTA")
            
            time.sleep(1.5) # Respiro para o ERP processar as mudanças de Select (AJAX)
            
            dados['codigo_negocio_veiculo'] = "1" # Informa ao Módulo de Gravação que é Frota (não desmarca despesa)

            # 4. Pula direto para o preenchimento do código/nome do item e cadastra
            # Passamos "1" como código de negócio para ele carregar isso corretamente na nova aba (se for preciso cadastrar)
            processar_cadastro_item(page, log, idx, item_block, "1")
            
            # Pula para o próximo item, IGNORANDO toda a leitura de placa e KM abaixo!
            continue 

        # ==============================================================
        # FLUXO 2: NOTA NORMAL (VEÍCULO / FROTA / FRETE)
        # ==============================================================
        # 1. PROCESSA O VEÍCULO E RECUPERA O TEXTO FINAL (ex: RRW0H88-13)
        resultado_veiculo = processar_veiculo(page, log, idx, memoria_obs, modelos_usuario)
        
        if not resultado_veiculo:
            # 🕵️ LÊ O QUE FICOU ESCRITO NO CAMPO DE VEÍCULO
            campo_veic = page.locator(f'input[id="formCad:tableItemNota:{idx}:veiculoInput"]')
            placa_tentativa = campo_veic.input_value().strip() if campo_veic.count() > 0 else ""
            
            # Se tiver algo no campo, usa isso pro erro!
            if placa_tentativa and "NAO ENCONTRADO" not in placa_tentativa.upper():
                msg_erro = f"Placa '{placa_tentativa}' não encontrada/cadastrada no ERP (Item {idx + 1})."
            else:
                # Backup: Se o campo estiver vazio, tenta pescar a placa direto da observação
                import re
                busca_placa = re.search(r'[A-Z]{3}\s*-?\s*\d[A-Z0-9]\d{2}', memoria_obs.upper())
                if busca_placa:
                    placa_achada = busca_placa.group(0).strip()
                    msg_erro = f"Placa '{placa_achada}' lida na NFe, mas falhou ao validar no ERP (Item {idx + 1})."
                else:
                    msg_erro = f"Nenhuma placa encontrada para o Item {idx + 1}."
            
            # Registra no banco de dados e pula a nota!
            abortar_nota_com_erro(page, log, dados, msg_erro)
            return 
            
        # 2. INTELIGÊNCIA: DESCOBRE O CÓDIGO E O RAMO DO NEGÓCIO
        codigo_negocio = "1" # Padrão
        
        if "-" in resultado_veiculo:
            # Pega só o que vem depois do traço (ex: 13)
            cod_veiculo = resultado_veiculo.split("-")[-1].strip()
            vinculo = db.obter_vinculo_veiculo(cod_veiculo).upper() # Garante que está em maiúsculo
            
            # MÁGICA: Procura a palavra com acento OU sem acento!
            if "PRÓPRIO" in vinculo or "PROPRIO" in vinculo:
                codigo_negocio = "1"
                log(f"-> 🧠 Vínculo do veículo ({cod_veiculo}): {vinculo} -> Negócio: FROTA (1)")
            elif vinculo:
                codigo_negocio = "2"
                log(f"-> 🧠 Vínculo do veículo ({cod_veiculo}): {vinculo} -> Negócio: FRETE/AGENCIAMENTO (2)")
            else:
                log(f"-> ⚠️ Vínculo do veículo ({cod_veiculo}) não encontrado na frota. Usando FROTA (1).")

        # 3. SELECIONA O NEGÓCIO NA TELA PRINCIPAL
        sel_negocio_tela_principal = page.locator(f'select[id="formCad:tableItemNota:{idx}:negocio"]')
        if sel_negocio_tela_principal.count() > 0:
            sel_negocio_tela_principal.select_option(value=codigo_negocio)
            log(f"-> 🎯 Formulário validado: Negócio do Item {idx + 1} alterado na tela para a opção {codigo_negocio}")
        
        dados['codigo_negocio_veiculo'] = codigo_negocio    

        # 4. SEGUE A VIDA PARA KM E ITEM
        processar_km(page, log, idx, memoria_obs)
        processar_cadastro_item(page, log, idx, item_block, codigo_negocio)

        # =======================================================================
        # 5. NOVA VALIDAÇÃO: VERIFICA SE O SISTEMA RECUSOU/BLOQUEOU O VEÍCULO
        # =======================================================================
        time.sleep(1) # Dá um respiro para o sistema carregar qualquer mensagem AJAX de erro
        
        # Procura por qualquer <li> na tela que contenha "Veiculo bloqueado"
        erro_bloqueio = page.locator('li', has_text="Veiculo bloqueado")
        
        if erro_bloqueio.count() > 0 and erro_bloqueio.first.is_visible():
            log(f"   ❌ ERRO FATAL: Veículo bloqueado detectado no Item {idx + 1}!")
            
            # Agora a mensagem te mostra a placa exata que o sistema recusou!
            abortar_nota_com_erro(page, log, dados, f"Veículo bloqueado pelo ERP no Item {idx + 1} (Placa: {resultado_veiculo}).")
            return # Interrompe a orquestração desta nota imediatamente

    # =======================================================================
    # 6. VALIDAÇÃO DE SEGURANÇA: GARANTE QUE TODOS OS ITENS DE ESTOQUE SEJAM FROTA
    # =======================================================================
    if nota_eh_estoque:
        log("   📦 Checagem final de segurança: Verificando se todos os itens do Estoque estão como FROTA...")
        for idx in range(total_itens):
            sel_negocio = page.locator(f'select[id="formCad:tableItemNota:{idx}:negocio"]')
            if sel_negocio.count() > 0:
                if sel_negocio.input_value() != "1":
                    sel_negocio.select_option(value="1")
                    log(f"      -> Corrigido o negócio do Item {idx + 1} para FROTA (1).")
        time.sleep(1)

    # FINALIZA A NOTA
    finalizar_gravacao(page, log, dados)