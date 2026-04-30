import time
import re

def processar_cadastro_item(page, log, idx, item_block, codigo_negocio):
    campo_item = page.locator(f'input[id="formCad:tableItemNota:{idx}:itemDInput"]')
    
    if not campo_item.input_value().strip():
        time.sleep(1.5) 
        
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
        except Exception:
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