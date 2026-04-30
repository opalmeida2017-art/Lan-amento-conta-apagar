import time
import re
from robo_web.utils import abortar_nota_com_erro

def finalizar_gravacao(page, log, dados):
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
        # Pega o número que está no texto (ex: 127643 de "Abrir nota de código interno = 127643")
        codigo_interno = re.search(r'\d+', texto_sucesso).group()
        log(f"⭐⭐ SUCESSO ABSOLUTO! Código Interno: {codigo_interno} ⭐⭐")
        
        dados['status'] = "Importado"
        dados['info'] = f"Cod: {codigo_interno}"
        
        # Salva o código interno isolado e limpa possíveis erros anteriores
        dados['codigo_interno'] = codigo_interno
        dados['erro_importacao'] = "" 
        
        import database_setup as db
        db.atualizar_nota_raspada(dados)

        log("Clicando no link e aguardando a nova aba abrir...")
        with page.context.expect_page() as nova_aba_nota:
            link_sucesso.first.click()
            
        aba_nota_aberta = nova_aba_nota.value
        aba_nota_aberta.wait_for_load_state("networkidle")
        time.sleep(2) 
        aba_nota_aberta.close() 
        
        page.bring_to_front()
        page.locator('input[value="Voltar"]').first.click(force=True)
        time.sleep(3)
        
    elif mensagens_erro.count() > 0:
        texto_erro = mensagens_erro.first.text_content().strip()
        abortar_nota_com_erro(page, log, dados, texto_erro)
    else:
        log("⚠️ Aviso: A tela não mostrou nem sucesso nem erro claro. Clicando em Voltar...")
        page.bring_to_front()
        page.locator('input[value="Voltar"]').first.click(force=True)
        time.sleep(3)