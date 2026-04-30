
import database_setup as db
from robo_web.utils import abortar_nota_com_erro
from robo_web.modulo_veiculo import processar_veiculo
from robo_web.modulo_km import processar_km
from robo_web.modulo_item import processar_cadastro_item
from robo_web.modulo_gravacao import finalizar_gravacao

def processar_importacao(page, log):
    notas_processadas = set()

    while True:
        log("🔄 Atualizando painel e verificando notas...")
        page.locator('input[id="formCad:buttonAtualizar"]').click()
        
        # Espera o sistema terminar de processar a requisição (substitui o sleep fixo)
        page.wait_for_load_state("networkidle") 
        
        seletor_linhas = "tbody[id='formCad:tablepnfedestinada:tbn'] tr"
        try:
            page.wait_for_selector(seletor_linhas, state="visible", timeout=10000)
        except Exception:
            log("Nenhuma nota encontrada no painel. Fim do processo.")
            break # Sai do loop de forma segura

        linhas = page.locator(seletor_linhas)
        total_linhas = linhas.count()
        nota_processada_neste_ciclo = False
        
        for i in range(total_linhas):
            linha = linhas.nth(i)
            num_nota = linha.locator("td.rf-edt-td-numNota").text_content().strip()
            
            if num_nota in notas_processadas: 
                continue

            celula_status = linha.locator("td.rf-edt-td-status")
            status_texto = celula_status.text_content().strip()
            obs_texto = linha.locator("td").nth(-2).text_content().strip() 

            log(f"📋 Analisando Nota: {num_nota} | Status: {status_texto}")

            if obs_texto and "IMPORTAR" not in status_texto.upper():
                log(f"⏩ Nota {num_nota} já possui observação. Pulando...")
                notas_processadas.add(num_nota)
                continue

            if "IMPORTAR" not in status_texto.upper() and ("CIÊNCIA" in status_texto.upper() or not status_texto):
                log(f"🔍 Nota {num_nota} sem XML. Executando passos 2 e 3...")
                linha.click()
                page.locator('input[id="formCad:buttonCiencia"]').click()
                page.locator('input[id="formCad:buttonConsultar"]').click()
                
                # Aguarda a página recarregar a tabela ao invés de dormir 5 segundos
                page.wait_for_load_state("networkidle")
                nota_processada_neste_ciclo = True
                break # Quebra o for para reiniciar o loop While e pegar a tela atualizada

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
                page.wait_for_load_state("networkidle")
                
                # --- CHAMA A ORQUESTRAÇÃO INTERNA ---
                orquestrar_preenchimento_interno(page, log, dados)
                
                notas_processadas.add(num_nota)
                log("Retornando ao painel principal para buscar a próxima nota...")
                nota_processada_neste_ciclo = True
                break # Quebra o for para reiniciar o loop While com a página principal fresca

        # Se passou pelo loop inteiro e não clicou em nada, acabou.
        if not nota_processada_neste_ciclo:
            log("✅ Todas as notas da página atual foram processadas.")
            break

# ... (mantenha a orquestrar_preenchimento_interno como está) ...

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

    linhas_item = page.locator('tbody[id="formCad:tableItemNota:tb"] > tr.rf-dt-r')
    total_itens = linhas_item.count()
    
    modelos_usuario = db.obter_modelos_placa() or ["PLACA: AAA-1A11", "PLAC: AAA-1A11"]

    for idx in range(total_itens):
        log(f"\n========================================================")
        log(f"===> PROCESSANDO ITEM {idx + 1} DE {total_itens}")
        log(f"========================================================")

        item_block = page.locator(f'tr[id="formCad:tableItemNota:{idx}"]')

        if valor_unid_mestre and valor_unid_mestre != "-":
            select_unid_item = item_block.locator('tr').filter(has=page.locator('span', has_text="Unid.Emb.:")).locator('select').first
            if select_unid_item.count() > 0:
                select_unid_item.select_option(value=valor_unid_mestre)

        # Captura o negócio atual do item
        sel_negocio = page.locator(f'select[id="formCad:tableItemNota:{idx}:negocio"]')
        codigo_negocio = sel_negocio.evaluate("el => el.value")
        if codigo_negocio == "-": codigo_negocio = "1"

        # DELEGA O TRABALHO PARA OS MÓDULOS EXTERNOS
        sucesso_veiculo = processar_veiculo(page, log, idx, memoria_obs, modelos_usuario)
        
        if not sucesso_veiculo:
            # Mensagem alterada conforme solicitado
            abortar_nota_com_erro(page, log, dados, "Não foi encontrada a placa do veículo na NFe | Verifica se os Itens são para Estoque.")
            return 
            
        processar_km(page, log, item_block, memoria_obs)
        processar_cadastro_item(page, log, idx, item_block, codigo_negocio)

    # FINALIZA A NOTA
    finalizar_gravacao(page, log, dados)