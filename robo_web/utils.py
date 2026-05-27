import re
import time


class ErroServidorIndisponivel(Exception):
    """ERP retornou HTTP 503 (Payara — Service Unavailable)."""


def pagina_servidor_indisponivel(page):
    """Detecta a tela HTTP 503 do Payara (SAT / Intersite)."""
    try:
        if page.is_closed():
            return False
        titulo = page.title() or ''
        try:
            corpo = page.locator('body').inner_text(timeout=5000)
        except Exception:
            corpo = page.content()
    except Exception:
        return False

    if 'HTTP Status 503' in titulo or 'HTTP Status 503' in corpo:
        return True
    if 'Service Unavailable' in corpo and 'Payara Server' in corpo:
        return True
    if 'Service Unavailable' in titulo and '503' in titulo:
        return True
    return False


def verificar_pagina_erp_ok(page, log=None):
    """Lança ErroServidorIndisponivel se a página atual for erro 503."""
    if pagina_servidor_indisponivel(page):
        if log:
            log('⚠️ Servidor ERP indisponível (HTTP 503). Fechando e aguardando 2 min...')
        raise ErroServidorIndisponivel('HTTP 503 - Service Unavailable')


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

def obter_mensagem_erro_erp(page):
    """Lê o texto do primeiro <li> de erro visível na tela do ERP."""
    marcadores_erro = (
        'inválido', 'invalido', 'bloqueado', 'favor selecionar',
        'erro', 'não encontrad', 'nao encontrad', 'recusad',
    )
    ignorar = ('sucesso', 'alterados com sucesso', 'finalizada com sucesso')
    try:
        itens = page.locator('li')
        for i in range(itens.count()):
            li = itens.nth(i)
            try:
                if not li.is_visible(timeout=300):
                    continue
            except Exception:
                continue
            texto = (li.text_content() or '').strip()
            if not texto or len(texto) < 8:
                continue
            tl = texto.lower()
            if any(x in tl for x in ignorar):
                continue
            if any(m in tl for m in marcadores_erro):
                return texto
    except Exception:
        pass
    return ''


def voltar_ao_painel_nfe(page, log):
    """Fecha a tela da nota e volta ao painel NFe."""
    log('Clicando em Voltar e aguardando a página carregar...')
    page.bring_to_front()
    btn = page.locator('input[value="Voltar"]')
    if btn.count() > 0:
        btn.first.click(force=True)
    try:
        page.wait_for_load_state('networkidle', timeout=20000)
    except Exception:
        pass
    time.sleep(1.5)


def abortar_nota_com_erro(page, log, dados, erro_msg):
    """Registra o erro no painel (banco) e volta ao painel NFe."""
    log(f'❌ ERRO ABORTANDO: {erro_msg}')
    import database_setup as db
    db.registrar_erro_nota_painel(dados, erro_msg)
    voltar_ao_painel_nfe(page, log)
    
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