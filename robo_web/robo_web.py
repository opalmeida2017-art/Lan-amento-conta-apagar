from playwright.sync_api import sync_playwright
import time
# Importando os módulos locais da pasta robo_web
from . import modulo_sefaz
from . import modulo_importacao


def iniciar_automacao(config, meses, anos, progresso_callback=None):
    def log(msg):
        if progresso_callback: progresso_callback(msg)
        print(f"[ROBÔ]: {msg}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            modulo_sefaz.consultar_sefaz(page, config, meses, anos, log)
            modulo_importacao.processar_importacao(page, log)
        except Exception as e:
            log(f"ERRO: {e}")
        finally:
            browser.close()