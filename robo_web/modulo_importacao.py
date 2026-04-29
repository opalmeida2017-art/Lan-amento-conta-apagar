import time
import re
import database_setup as db

# ========================================================
# MOTOR DE TRADUÇÃO DE MODELOS (O SEGREDO DA MÁGICA)
# ========================================================
def converter_modelo_para_regex(modelo):
    """
    Transforma "PLACA: AAA-1A11" em uma regra de leitura para o robô.
    A = Letra, 1 = Número.
    """
    # Procura onde começa a sequência de letras e números (a placa em si)
    match = re.search(r'([A1][A1\-\s]{5,}[A1])', modelo)
    if not match: return None
    
    mascara = match.group(1) # Pega o "AAA-1A11"
    prefixo = modelo[:match.start()] # Pega o "PLACA: "
    
    mascara_regex = ""
    for char in mascara:
        if char == 'A': mascara_regex += r'[A-Za-z]'
        elif char == '1': mascara_regex += r'\d'
        elif char == ' ': mascara_regex += r'\s*'
        elif char == '-': mascara_regex += r'\-?' # Permite com ou sem traço
        else: mascara_regex += re.escape(char)
        
    # Limpa o prefixo permitindo espaços flexíveis
    prefixo_regex = re.escape(prefixo).replace(r'\ ', r'\s*')
    
    return prefixo_regex + f"({mascara_regex})"

# ========================================================
# FUNÇÃO PRINCIPAL DE PROCESSAMENTO
# ========================================================
def processar_importacao(page, log, notas_processadas=None):
    if notas_processadas is None:
        notas_processadas = set()

    log("🔄 Atualizando painel e verificando notas...")
    page.locator('input[id="formCad:buttonAtualizar"]').click()
    time.sleep(3) 
    
    seletor_linhas = "tbody[id='formCad:tablepnfedestinada:tbn'] tr"
    try:
        page.wait_for_selector(seletor_linhas, state="visible", timeout=10000)
    except:
        log("Nenhuma nota encontrada no painel. Fim do processo.")
        return

    linhas = page.locator(seletor_linhas)
    total_linhas = linhas.count()
    
    for i in range(total_linhas):
        linha = linhas.nth(i)
        
        num_nota = linha.locator("td.rf-edt-td-numNota").text_content().strip()
        celula_status = linha.locator("td.rf-edt-td-status")
        status_texto = celula_status.text_content().strip()
        obs_texto = linha.locator("td").nth(-2).text_content().strip() 

        if num_nota in notas_processadas:
            continue

        log(f"📋 Analisando Nota: {num_nota} | Status: {status_texto}")

        # A. Se já tem observação
        if obs_texto and "IMPORTAR" not in status_texto.upper():
            log(f"⏩ Nota {num_nota} já possui observação. Pulando...")
            continue

        # B. Sem XML
        if "IMPORTAR" not in status_texto.upper() and ("CIÊNCIA" in status_texto.upper() or not status_texto):
            log(f"🔍 Nota {num_nota} sem XML. Executando passos 2 e 3...")
            linha.click()
            time.sleep(1)
            
            page.locator('input[id="formCad:buttonCiencia"]').click()
            time.sleep(2)
            page.locator('input[id="formCad:buttonConsultar"]').click()
            time.sleep(5)
            
            return processar_importacao(page, log, notas_processadas)

        # C. Pronta para Importar
        if "Importar" in status_texto:
            log(f"🚀 Nota {num_nota} pronta! Iniciando importação...")
            
            dados = {
                "status": "Processando",
                "fornecedor": linha.locator("td.rf-edt-td-forn").text_content().strip(),
                "num_nota": num_nota,
                "data_em": linha.locator("td.rf-edt-td-data").text_content().strip(),
                "valor": linha.locator("td.rf-edt-td-valor").text_content().strip(),
                "sit_nfe": linha.locator("td.rf-edt-td-sitNFe").text_content().strip(),
                "chave_nfe": linha.locator("td.rf-edt-td-chaveNFe").text_content().strip(),
                "filial": linha.locator("td.rf-edt-td-filial").text_content().strip(),
                "user_ins": linha.locator("td").last.text_content().strip(),
                "info": "" 
            }
            db.salvar_nota_raspada(dados)
            
            celula_status.locator("a:has-text('Importar')").click()
            time.sleep(3)
            
            executar_logica_interna_importacao(page, log, dados)
            
            notas_processadas.add(num_nota)
            log("Retornando ao painel principal para buscar a próxima nota...")
            return processar_importacao(page, log, notas_processadas)

    log("✅ Todas as notas da página atual foram processadas.")

# ========================================================
# PREENCHIMENTO INTERNO DA NOTA
# ========================================================
def executar_logica_interna_importacao(page, log, dados):
    # ========================================================
    # 1. SINCRONIZAR FILIAL E UNID. EMB.
    # ========================================================
    select_empresa = page.locator('select[name="formCad:j_idt26"]')
    valor_unidade = select_empresa.evaluate("el => el.value")
    select_unid_mestre = page.locator('select[name="formCad:j_idt31"]')
    
    if valor_unidade != "-":
        select_unid_mestre.select_option(value=valor_unidade)
        log(f"Filial e Unid. Emb. Mestre sincronizadas com Unidade {valor_unidade}")
    
    valor_unid_mestre = select_unid_mestre.evaluate("el => el.value")
    memoria_obs = page.locator('textarea[name="formCad:j_idt51"]').input_value()

    # ========================================================
    # 2. LOOP DE ITENS (VEÍCULO, KM, ITEM)
    # ========================================================
    linhas_item = page.locator('tbody[id="formCad:tableItemNota:tb"] > tr.rf-dt-r')
    total_itens = linhas_item.count()
    
    modelos_usuario = db.obter_modelos_placa()
    if not modelos_usuario:
        log("⚠️ Aviso: Nenhum modelo de placa cadastrado! Usando padrão interno.")
        modelos_usuario = ["PLACA: AAA-1A11", "PLAC: AAA-1A11"]

    for idx in range(total_itens):
        log(f"\n========================================================")
        log(f"===> PROCESSANDO ITEM {idx + 1} DE {total_itens}")
        log(f"========================================================")

        item_block = page.locator(f'tr[id="formCad:tableItemNota:{idx}"]')

        if valor_unid_mestre and valor_unid_mestre != "-":
            select_unid_item = item_block.locator('tr').filter(has=page.locator('span', has_text="Unid.Emb.:")).locator('select').first
            if select_unid_item.count() > 0:
                select_unid_item.select_option(value=valor_unid_mestre)

        # --- A. LÓGICA DO VEÍCULO E CONFIGURAÇÃO DINÂMICA ---
        campo_veiculo = page.locator(f'input[id="formCad:tableItemNota:{idx}:veiculoInput"]')
        valor_v = campo_veiculo.input_value().strip()
        
        veiculo_sucesso = False
        
        if valor_v and "SEM DADOS" not in valor_v.upper():
            log(f"-> Veículo já identificado na tela: {valor_v}")
            veiculo_sucesso = True
        else:
            log("-> Veículo vazio. Lendo observação com os modelos do banco de dados...")
            
            placas_encontradas = []
            for modelo in modelos_usuario:
                regex_dinamico = converter_modelo_para_regex(modelo)
                if regex_dinamico:
                    for match in re.finditer(regex_dinamico, memoria_obs, re.IGNORECASE):
                        placa_extraida = match.group(1).replace("-", "").replace(" ", "").upper()
                        if placa_extraida not in placas_encontradas:
                            placas_encontradas.append(placa_extraida)
            
            if placas_encontradas:
                log(f"-> 🔎 Placas extraídas da observação: {placas_encontradas}")
            else:
                log(f"-> ⚠️ Nenhuma placa extraída! Modelos testados: {modelos_usuario}")

            for placa_tentativa in placas_encontradas:
                log(f"-> Testando preenchimento com a Placa: {placa_tentativa}")
                campo_veiculo.click()
                campo_veiculo.clear()
                campo_veiculo.press_sequentially(placa_tentativa, delay=100)
                time.sleep(1)
                campo_veiculo.press("Enter")
                time.sleep(1.5)
                campo_veiculo.press("Enter")
                time.sleep(0.5)
                campo_veiculo.press("Tab") 
                
                time.sleep(2)
                valor_atual_veiculo = campo_veiculo.input_value().strip().upper()
                
                # CORREÇÃO: AGORA O "SEM DADOS" É BARRADO E REJEITADO
                if "CADASTRO NAO ENCONTRADO" in valor_atual_veiculo or "REFAZER CONSULTA" in valor_atual_veiculo or "SEM DADOS" in valor_atual_veiculo or not valor_atual_veiculo:
                    log(f"-> ❌ Placa '{placa_tentativa}' rejeitada pelo sistema (Retornou: {valor_atual_veiculo}).")
                    campo_veiculo.clear()
                else:
                    log(f"-> ✅ SUCESSO! Veículo validado pelo sistema: {valor_atual_veiculo}")
                    veiculo_sucesso = True
                    break 

        if not veiculo_sucesso:
            erro_msg = f"Nenhum formato de placa válido no Item {idx + 1}. Revise as Configurações."
            log(f"❌ ERRO ABORTANDO: {erro_msg}")
            
            dados['status'] = "Erro"
            dados['info'] = erro_msg
            # <<-- COLOQUE SUA FUNÇÃO DE BANCO AQUI PARA SALVAR O ERRO DA PLACA
            
            log("Clicando em Voltar e pulando para a próxima nota...")
            page.locator('input[value="Voltar"]').first.click(force=True)
            time.sleep(3)
            return 

        # --- B. LÓGICA DO KM / HIDROMETRO ---
        campo_km = item_block.locator('tr').filter(has=page.locator('span', has_text="KM:")).locator('input[type="text"]').first
        if campo_km.count() > 0:
            if not campo_km.input_value().strip() or campo_km.input_value() == "0":
                formatos_km = [r"KM[:\s=]*([0-9.,]+)", r"HIDROMETRO[:\s=]*([0-9.,]+)", r"KILOMETRAGEM[:\s=]*([0-9.,]+)", r"ODO[:\s=]*([0-9.,]+)"]
                km_detectado = None
                for f in formatos_km:
                    busca = re.search(f, memoria_obs, re.IGNORECASE)
                    if busca:
                        km_detectado = re.sub(r"[.,\s]", "", busca.group(1))
                        break
                
                if km_detectado:
                    campo_km.click()
                    campo_km.clear()
                    campo_km.press_sequentially(km_detectado, delay=50)
                    campo_km.press("Tab") 
            else:
                log("-> KM já está preenchido.")

        # --- C. VERIFICAR / PESQUISAR / CADASTRAR ITEM ---
        campo_item = page.locator(f'input[id="formCad:tableItemNota:{idx}:itemDInput"]')
        
        if not campo_item.input_value().strip():
            time.sleep(1.5) 
            sel_negocio = page.locator(f'select[id="formCad:tableItemNota:{idx}:negocio"]')
            codigo_negocio = sel_negocio.evaluate("el => el.value") 
            if codigo_negocio == "-": codigo_negocio = "1"
            
            try:
                texto_item_bloco = item_block.inner_text()
                busca_nome = re.search(r"Produto na NFe:\s*([^\n]+)", texto_item_bloco, re.IGNORECASE)
                if busca_nome:
                    nome_bruto = busca_nome.group(1)
                    nome_limpo = re.split(r'\s{2,}|\bNegócio\b', nome_bruto, flags=re.IGNORECASE)[0].strip()
                    nome_limpo = re.sub(r'^[^a-zA-Z0-9]*\d+(?:\s+|-|\)|\])[^a-zA-Z0-9]*', '', nome_limpo).strip()
                    nome_item_temporario = nome_limpo[:80]
                else:
                    nome_item_temporario = "ITEM NFE"
            except Exception as e:
                nome_item_temporario = "ITEM NFE"
                
            campo_item.click()
            campo_item.clear()
            campo_item.press_sequentially(nome_item_temporario, delay=30) 
            time.sleep(1)
            campo_item.press("Enter")
            time.sleep(1.5) 
            campo_item.press("Enter")
            time.sleep(0.5)
            campo_item.press("Tab")
            time.sleep(2) 

            valor_item_atual = campo_item.input_value().strip().upper()
            
            if "CADASTRO NAO ENCONTRADO" in valor_item_atual or "REFAZER CONSULTA" in valor_item_atual or not valor_item_atual:
                log("-> Item não achou. Iniciando cadastro na aba secundária...")
                campo_item.clear()
                linha_img = item_block.locator('tr').filter(has=page.locator(f'input[id="formCad:tableItemNota:{idx}:itemDInput"]'))

                with page.context.expect_page() as nova_aba_item:
                    linha_img.locator('img[title="Inserir/Alterar"]').click()
                
                aba_item = nova_aba_item.value
                aba_item.wait_for_load_state("networkidle")
                
                aba_item.locator('input[id="formitemD:ItemD_descricao"]').fill(nome_item_temporario)
                aba_item.locator('select[id="formitemD:ItemD_grupoD"]').select_option(value="107")
                aba_item.locator('select[id="formitemD:ItemD_unidade"]').select_option(value="LT")
                aba_item.locator('select[id="formitemD:ItemD_gerenciaEstoque"]').select_option(value="N")
                aba_item.locator('select[id="formitemD:ItemD_viagem"]').select_option(value="N")
                if codigo_negocio != "-": aba_item.locator('select[id="formitemD:ItemD_negocio"]').select_option(value=codigo_negocio)
                
                aba_item.locator('input[id="formitemD:gravaritemD"]').click()
                aba_item.wait_for_function('() => { var el = document.getElementById("formitemD:ItemD_codItemD"); return el !== null && el.value.trim() !== ""; }', timeout=15000)
                
                novo_cod = aba_item.locator('input[id="formitemD:ItemD_codItemD"]').input_value()
                log(f"-> Código gerado com sucesso: {novo_cod}")
                
                aba_item.close()
                
                # CORREÇÃO: GARANTINDO QUE A TELA PRINCIPAL RETOME O FOCO
                page.bring_to_front()
                time.sleep(1)
                
                campo_item.click()
                campo_item.clear()
                campo_item.press_sequentially(novo_cod, delay=50)
                time.sleep(1)
                campo_item.press("Enter")
                time.sleep(1)
                campo_item.press("Enter")
                time.sleep(0.5)
                campo_item.press("Tab")
            else:
                log(f"-> SUCESSO! Item selecionado: {valor_item_atual}")
        else:
            log(f"-> O item {idx + 1} já estava preenchido: {campo_item.input_value()}")

    # ========================================================
    # 3. GRAVAÇÃO FINAL E VALIDAÇÃO DE SUCESSO OU ERRO
    # ========================================================
    log("\nTODOS OS ITENS FORAM PROCESSADOS! Iniciando Gravação Final...")
    page.locator('input[id="formCad:importarCP"]').click()
    
    log("Aguardando resposta do sistema (Sucesso ou Erro)...")
    try:
        page.wait_for_selector('a[id="formCad:linkAbrirNota"], div[id="formCad:messages"] li, ul.rf-msgs li', state="visible", timeout=15000)
    except:
        pass

    link_sucesso = page.locator('a[id="formCad:linkAbrirNota"]')
    mensagens_erro = page.locator('div[id="formCad:messages"] li, ul.rf-msgs li, span.rf-msgs-err')
    
    if link_sucesso.count() > 0:
        texto_sucesso = link_sucesso.first.text_content()
        codigo_interno = re.search(r'\d+', texto_sucesso).group()
        log(f"⭐⭐ SUCESSO ABSOLUTO! Código Interno: {codigo_interno} ⭐⭐")
        
        dados['status'] = "Importado"
        dados['info'] = f"Cod: {codigo_interno}"
        # <<-- COLOQUE SUA FUNÇÃO DE BANCO AQUI PARA SALVAR O SUCESSO FINAL

        log("Clicando no link e aguardando a nova aba abrir...")
        with page.context.expect_page() as nova_aba_nota:
            link_sucesso.first.click()
            
        aba_nota_aberta = nova_aba_nota.value
        aba_nota_aberta.wait_for_load_state("networkidle")
        time.sleep(2) 
        aba_nota_aberta.close() 
        
        # CORREÇÃO: RETOMA O FOCO NA TELA PRINCIPAL
        page.bring_to_front()
        page.locator('input[value="Voltar"]').first.click(force=True)
        time.sleep(3)
        
    elif mensagens_erro.count() > 0:
        texto_erro = mensagens_erro.first.text_content().strip()
        log(f"❌ ERRO DO SISTEMA: {texto_erro} ❌")
        
        dados['status'] = "Erro"
        dados['info'] = texto_erro
        # <<-- COLOQUE SUA FUNÇÃO DE BANCO AQUI PARA SALVAR O ERRO DO SISTEMA FINAL
        
        log("Clicando em Voltar para abortar e tentar a próxima nota...")
        page.bring_to_front()
        page.locator('input[value="Voltar"]').first.click(force=True)
        time.sleep(3)
        
    else:
        log("⚠️ Aviso: A tela não mostrou nem sucesso nem erro claro. Clicando em Voltar...")
        page.bring_to_front()
        page.locator('input[value="Voltar"]').first.click(force=True)
        time.sleep(3)