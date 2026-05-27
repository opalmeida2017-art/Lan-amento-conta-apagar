from playwright.sync_api import sync_playwright
import time

from . import modulo_sefaz
from . import modulo_importacao
from .controle_robo import (
    RoboParadoPeloUsuario,
    encerrar_sessao,
    marcar_rodando,
    registrar_browser,
    solicitar_parada,
    verificar_parada,
)
from .erp_lock import ERP_LOCK
from .utils import ErroServidorIndisponivel, verificar_pagina_erp_ok

TEMPO_ESPERA_503_SEG = 120
MAX_REINICIOS = 30


def _aguardar_segundos(segundos, log, mensagem):
    log(mensagem)
    for _ in range(segundos):
        verificar_parada()
        time.sleep(1)


def _executar_sessao(
    p,
    config,
    meses,
    anos,
    log,
    nota_alvo=None,
    compra_estoque=False,
    ultimos_30_dias=False,
):
    browser = p.chromium.launch(headless=False)
    registrar_browser(browser)
    page = browser.new_page()
    try:
        verificar_parada()
        with ERP_LOCK:
            log('🔒 Sessão ERP exclusiva (robô NFe)')
            if not modulo_sefaz.consultar_sefaz(
                page,
                config,
                meses,
                anos,
                log,
                ultimos_30_dias=ultimos_30_dias,
            ):
                raise RuntimeError('Consulta SEFAZ não confirmou sucesso.')
            verificar_parada()
            verificar_pagina_erp_ok(page, log)
            time.sleep(2)
            verificar_parada()
            modulo_importacao.processar_importacao(
                page,
                log,
                {
                    'processadas': set(),
                    'atualizar_agora': True,
                    'nota_alvo': nota_alvo,
                    'nota_alvo_estoque': compra_estoque,
                },
            )
        return True
    finally:
        try:
            browser.close()
        except Exception:
            pass
        registrar_browser(None)


def iniciar_automacao(
    config,
    meses,
    anos,
    progresso_callback=None,
    nota_alvo=None,
    compra_estoque=False,
    ultimos_30_dias=False,
):
    def log(msg):
        if progresso_callback:
            progresso_callback(msg)
        print(f'[ROBÔ]: {msg}')

    marcar_rodando(True)
    reinicios = 0
    try:
        while reinicios <= MAX_REINICIOS:
            verificar_parada()
            try:
                with sync_playwright() as p:
                    _executar_sessao(
                        p,
                        config,
                        meses,
                        anos,
                        log,
                        nota_alvo=nota_alvo,
                        compra_estoque=compra_estoque,
                        ultimos_30_dias=ultimos_30_dias,
                    )
                log('Automação concluída.')
                return
            except RoboParadoPeloUsuario:
                log('Robô parado pelo usuário. Navegador fechado.')
                raise
            except ErroServidorIndisponivel:
                reinicios += 1
                if reinicios > MAX_REINICIOS:
                    log(f'Limite de {MAX_REINICIOS} reinícios após erro 503.')
                    raise
                _aguardar_segundos(
                    TEMPO_ESPERA_503_SEG,
                    log,
                    f'Servidor ERP em manutenção (503). Aguardando {TEMPO_ESPERA_503_SEG // 60} min '
                    f'(tentativa {reinicios}/{MAX_REINICIOS})...',
                )
                log('Reiniciando robô (novo navegador)...')
            except Exception as e:
                from .controle_robo import _sessao
                if _sessao.get('parar'):
                    log('Robô parado pelo usuário. Navegador fechado.')
                    raise RoboParadoPeloUsuario() from e
                log(f'ERRO: {e}')
                raise
    finally:
        encerrar_sessao()
