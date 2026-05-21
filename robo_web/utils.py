import re
import time

def converter_modelo_para_regex(modelo):
    """Transforma 'PLACA: AAA-1A11' em uma regra Regex para o robô"""
    match = re.search(r'([A1][A1\-\s]{5,}[A1])', modelo)
    if not match: return None
    
    mascara = match.group(1)
    prefixo = modelo[:match.start()]
    
    mascara_regex = ""
    for char in mascara:
        if char == 'A': mascara_regex += r'[A-Za-z]'
        elif char == '1': mascara_regex += r'\d'
        elif char == ' ': mascara_regex += r'\s*'
        elif char == '-': mascara_regex += r'\-?' 
        else: mascara_regex += re.escape(char)
        
    prefixo_regex = re.escape(prefixo).replace(r'\ ', r'\s*')
    return prefixo_regex + f"({mascara_regex})"

def abortar_nota_com_erro(page, log, dados, erro_msg):
    """Registra o erro, fecha a nota e volta para o painel principal"""
    log(f"❌ ERRO ABORTANDO: {erro_msg}")
    
    dados['status'] = "Erro"
    # Salva o erro específico no novo campo
    dados['erro_importacao'] = erro_msg 
    dados['codigo_interno'] = "" # Limpa se houver
    
    import database_setup as db
    db.atualizar_nota_raspada(dados) 
    
    log("Clicando em Voltar e aguardando a página carregar...")
    page.bring_to_front()
    page.locator('input[value="Voltar"]').first.click(force=True)
    
    # Substitui o "time.sleep(3)" burro por uma espera inteligente do Playwright
    try:
        # Aguarda até que a rede do navegador fique calma (ou seja, a página carregou)
        page.wait_for_load_state("networkidle", timeout=20000)
    except:
        pass # Se passar de 20 segundos, ele ignora e tenta forçar a continuação
        
    time.sleep(1.5)
    
def converter_modelo_km_para_regex(modelo):
    """Transforma 'HIDRO: 1' em uma regra Regex para o robô extrair o KM"""
    # Se não tiver o número 1 no modelo, ignora
    if '1' not in modelo:
        return None
    
    # Corta a palavra separando pelo "1". Pega só a parte da frente (Ex: "HIDRO: ")
    prefixo = modelo.split('1')[0]
    
    # Escapa os caracteres e permite que os espaços sejam flexíveis (1 ou mais espaços)
    prefixo_regex = re.escape(prefixo).replace(r'\ ', r'\s*')
    
    # Retorna o prefixo exigindo que logo depois dele venham números, pontos ou vírgulas
    return prefixo_regex + r'([0-9.,]+)'