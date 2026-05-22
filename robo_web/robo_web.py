from playwright.sync_api import sync_playwright
import time

from . import modulo_sefaz
from . import modulo_importacao
from .utils import ErroServidorIndisponivel, verificar_pagina_erp_ok

TEMPO_ESPERA_503_SEG = 120
MAX_REINICIOS_503 = 30


def _executar_sessao(p, config, meses, anos, log):
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    try:
        modulo_sefaz.consultar_sefaz(page, config, meses, anos, log)
        verificar_pagina_erp_ok(page, log)
        modulo_importacao.processar_importacao(page, log)
        return True
    finally:
        try:
            browser.close()
        except Exception:
            pass


def iniciar_automacao(config, meses, anos, progresso_callback=None):
    def log(msg):
        if progresso_callback:
            progresso_callback(msg)
        print(f"[ROBÔ]: {msg}")

    reinicios = 0
    while reinicios <= MAX_REINICIOS_503:
        try:
            with sync_playwright() as p:
                _executar_sessao(p, config, meses, anos, log)
            log('Automação concluída.')
            return
        except ErroServidorIndisponivel:
            reinicios += 1
            if reinicios > MAX_REINICIOS_503:
                log(f'Limite de {MAX_REINICIOS_503} reinícios após erro 503.')
                raise
            log(
                f'Servidor ERP em manutenção (503). '
                f'Aguardando {TEMPO_ESPERA_503_SEG // 60} min para reiniciar o robô '
                f'(tentativa {reinicios}/{MAX_REINICIOS_503})...'
            )
            time.sleep(TEMPO_ESPERA_503_SEG)
            log('Reiniciando robô...')
        except Exception as e:
            log(f'ERRO: {e}')
            raise
