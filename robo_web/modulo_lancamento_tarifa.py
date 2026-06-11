"""Automação de lançamento de tarifas bancárias em Contas a Pagar Automática."""

import re
import time

from playwright.sync_api import sync_playwright

import database_setup as db
from robo_web.erp_lock import ERP_LOCK
from robo_web.runtime_config import usar_headless
from robo_web.utils import ErroServidorIndisponivel, fazer_login_erp, verificar_pagina_erp_ok

MSG_ITEM_NAO_ENCONTRADO = ('CADASTRO NAO ENCONTRADO', 'REFAZER CONSULTA')

SEL_FORN = 'input[id="formnotaAuto:NotaAuto_fornInput"]'
SEL_VALOR = 'input[id="formnotaAuto:NotaAuto_valor"]'
SEL_DATA_EMISSAO = 'input[id="formnotaAuto:NotaAuto_dataEmissaoInputDate"]'
SEL_SERIE = 'input[id="formnotaAuto:NotaAuto_serie"]'
SEL_FILIAL = 'select[id="formnotaAuto:NotaAuto_filial"]'
SEL_NEGOCIO = 'select[id="formnotaAuto:NotaAuto_negocio"]'
SEL_COND_PAG = 'select[id="formnotaAuto:NotaAuto_condPag"]'
SEL_DATA_VENC = 'input[id="formnotaAuto:NotaAuto_dataVencimentoInputDate"]'
SEL_ITEM = 'input[id="formnotaAuto:NotaAuto_itemDInput"]'
SEL_VED = 'select[id="formnotaAuto:NotaAuto_vedAuto"]'
SEL_CONTA = 'select[id="formnotaAuto:NotaAuto_contaAuto"]'
SEL_TIPO_PAG = 'select[id="formnotaAuto:NotaAuto_tipoPagto"]'


def _log(msg, log_callback=None):
    texto = f'[TARIFA ERP]: {msg}'
    print(texto)
    if log_callback:
        log_callback(msg)


def _primeiro_locator(page, seletores):
    for sel in seletores:
        loc = page.locator(sel).first
        try:
            if loc.count() > 0:
                return loc
        except Exception:
            continue
    return page.locator(seletores[0]).first


def _preencher_autocomplete(page, seletor, texto, log, delay=40):
    campo = page.locator(seletor).first
    campo.wait_for(state='visible', timeout=10000)
    campo.click()
    campo.fill('')
    campo.press_sequentially(str(texto), delay=delay)
    time.sleep(0.8)
    campo.press('Enter')
    time.sleep(1.2)
    campo.press('Enter')
    time.sleep(0.4)
    campo.press('Tab')
    time.sleep(1.0)
    return campo.input_value().strip()


def _valor_campo_contem_erro_item(valor):
    texto = str(valor or '').strip().upper()
    return any(tag in texto for tag in MSG_ITEM_NAO_ENCONTRADO) or not texto


def _nome_item_tarifa(tarifa, cfg_tarifa):
    descricao = str(tarifa.get('descricao') or '').strip().upper()
    if descricao:
        return descricao[:80]
    padrao = str(cfg_tarifa.get('nome_item_tarifa_padrao') or '').strip().upper()
    return (padrao or 'TARIFAS BANCARIAS')[:80]


def _normalizar_conta_busca(conta):
    return re.sub(r'[^0-9]', '', str(conta or ''))


def _resolver_cod_conta_erp(page, agencia, conta):
    cod_mapa = db.obter_cod_conta_erp_por_conta(agencia, conta)
    if cod_mapa:
        return cod_mapa

    select = page.locator(SEL_CONTA).first
    conta_ref = str(conta or '').strip().replace('_', '-')
    conta_digits = _normalizar_conta_busca(conta_ref)
    total = select.locator('option').count()
    melhor = ''
    for i in range(total):
        opt = select.locator('option').nth(i)
        valor = (opt.get_attribute('value') or '').strip()
        texto = (opt.text_content() or '').strip()
        if not valor or valor == '-':
            continue
        if conta_ref and conta_ref in texto:
            return valor
        if conta_digits and conta_digits in re.sub(r'[^0-9]', '', texto):
            melhor = valor
    return melhor


def _cadastrar_item_tarifa(page, nome_item, cfg_tarifa, log):
    cod_grupo = str(cfg_tarifa.get('cod_grupo_item_tarifa') or '44').strip()
    log(f'   Cadastrando item "{nome_item}" (grupo {cod_grupo})...')

    with page.context.expect_page() as nova_aba_info:
        page.locator('form#formnotaAuto img[title="Inserir/Alterar"]').first.click()

    aba_item = nova_aba_info.value
    aba_item.wait_for_load_state('networkidle')
    aba_item.locator('input[id="formitemD:ItemD_descricao"]').fill(nome_item)
    aba_item.locator('select[id="formitemD:ItemD_grupoD"]').select_option(value=cod_grupo)
    aba_item.locator('select[id="formitemD:ItemD_unidade"]').select_option(value='UN')
    aba_item.locator('select[id="formitemD:ItemD_gerenciaEstoque"]').select_option(value='O')
    aba_item.locator('select[id="formitemD:ItemD_viagem"]').select_option(value='N')
    aba_item.locator('select[id="formitemD:ItemD_negocio"]').select_option(value='1')
    aba_item.locator('input[id="formitemD:gravaritemD"]').click()
    aba_item.wait_for_function(
        '() => { var el = document.getElementById("formitemD:ItemD_codItemD"); '
        'return el !== null && el.value.trim() !== ""; }',
        timeout=15000,
    )
    novo_cod = aba_item.locator('input[id="formitemD:ItemD_codItemD"]').input_value().strip()
    aba_item.close()
    page.bring_to_front()
    time.sleep(0.8)
    log(f'   Item cadastrado com codigo {novo_cod}.')
    return novo_cod


def _preencher_item_tarifa(page, nome_item, cfg_tarifa, log):
    valor_item = _preencher_autocomplete(page, SEL_ITEM, nome_item, log)
    if _valor_campo_contem_erro_item(valor_item):
        log(f'   Item "{nome_item}" nao encontrado. Abrindo cadastro...')
        novo_cod = _cadastrar_item_tarifa(page, nome_item, cfg_tarifa, log)
        if not novo_cod:
            raise RuntimeError(f'Falha ao cadastrar item "{nome_item}".')
        _preencher_autocomplete(page, SEL_ITEM, novo_cod, log)
    else:
        log(f'   Item selecionado: {valor_item}')


def navegar_para_contas_pagar_automatica(page, log):
    log('Navegando para Contas a Pagar Automatica...')
    verificar_pagina_erp_ok(page, log)

    cadastros = _primeiro_locator(page, [
        '#formMenu\\:j_idt128_label',
        'div.rf-ddm-lbl-dec:has-text("Cadastros")',
        'text=Cadastros >> visible=true',
    ])
    cadastros.hover()
    time.sleep(0.8)

    submenu_cp = page.locator(
        'span.rf-ddm-itm-lbl:has-text("Contas a Pagar")',
    ).first
    try:
        if submenu_cp.is_visible(timeout=2000):
            submenu_cp.hover()
            time.sleep(0.5)
    except Exception:
        pass

    destino = _primeiro_locator(page, [
        'span.rf-ddm-itm-lbl:has-text("Contas a Pagar Automática")',
        'span.rf-ddm-itm-lbl:has-text("Contas a Pagar Automatica")',
        'text=Contas a Pagar Automática >> visible=true',
    ])
    destino.click(force=True)
    page.wait_for_load_state('networkidle')
    page.locator(SEL_FORN).wait_for(state='visible', timeout=20000)
    time.sleep(1.0)


def _clicar_gravar_nota_auto(page, log):
    botao = _primeiro_locator(page, [
        'input[id="formnotaAuto:gravarNotaAuto"]',
        'input[id*="formnotaAuto"][id*="gravar"]',
        'input[name*="formnotaAuto"][name*="gravar"]',
        'form#formnotaAuto input[src*="gravar"]',
    ])
    if botao.count() == 0:
        raise RuntimeError('Botao Gravar nao encontrado na tela Contas a Pagar Automatica.')
    botao.click(force=True)
    time.sleep(2.0)
    log('   Gravacao enviada.')


def _clicar_finalizar_nota_auto(page, log):
    botao = _primeiro_locator(page, [
        'img[id*="formnotaAuto"][id*="Finalizar"]:not([id*="Desfinalizar"])',
        'form#formnotaAuto img[title*="Finalizar"]:not([title*="Desfinalizar"])',
        'form#formnotaAuto img[src*="finalizar"]',
    ])
    if botao.count() == 0:
        log('   Aviso: botao Finalizar nao localizado; mantendo gravacao.')
        return False
    botao.click(force=True)
    time.sleep(2.0)
    log('   Finalizacao solicitada.')
    return True


def _extrair_codigo_nota_auto(page):
    campos = [
        'input[id="formnotaAuto:NotaAuto_codigo"]',
        'input[id*="formnotaAuto"][id*="codigo"]',
        'input[id="formnotaAuto:NotaAuto_codNotaAuto"]',
    ]
    for sel in campos:
        loc = page.locator(sel).first
        try:
            if loc.count() > 0 and loc.is_visible(timeout=500):
                valor = loc.input_value().strip()
                if valor:
                    return valor
        except Exception:
            continue
    return ''


def lancar_tarifa(page, tarifa, cfg_erp, cfg_tarifa, log):
    tarifa_id = tarifa.get('id')
    descricao = str(tarifa.get('descricao') or '').strip()
    valor = str(tarifa.get('valor') or '').strip()
    data_mov = str(tarifa.get('data_movimento') or '').strip()
    cnpj = str(tarifa.get('cnpj') or '').strip()
    agencia = str(tarifa.get('agencia') or '').strip()
    conta = str(tarifa.get('conta') or '').strip()

    log(
        f'Lancando tarifa #{tarifa_id}: {descricao} | R$ {valor} | '
        f'{data_mov} | CNPJ {cnpj} | conta {agencia}/{conta}'
    )

    cod_forn = str(cfg_tarifa.get('cod_fornecedor_sicredi') or '640').strip()
    cod_filial = db.obter_cod_filial_por_cnpj(cnpj)
    if not cod_filial:
        raise RuntimeError(
            f'Codigo de filial nao configurado para CNPJ {cnpj}. '
            'Adicione a coluna cod_filial no mapa_contas.csv.'
        )

    navegar_para_contas_pagar_automatica(page, log)

    fornecedor_val = _preencher_autocomplete(page, SEL_FORN, cod_forn, log)
    if not fornecedor_val:
        raise RuntimeError(f'Fornecedor {cod_forn} nao selecionado.')

    page.locator(SEL_VALOR).fill(valor)
    page.locator(SEL_DATA_EMISSAO).fill(data_mov)
    page.locator(SEL_SERIE).fill('U')
    page.locator(SEL_FILIAL).select_option(value=str(cod_filial))
    page.locator(SEL_NEGOCIO).select_option(value='1')
    page.locator(SEL_COND_PAG).select_option(value='1')
    page.locator(SEL_DATA_VENC).fill(data_mov)

    nome_item = _nome_item_tarifa(tarifa, cfg_tarifa)
    _preencher_item_tarifa(page, nome_item, cfg_tarifa, log)

    page.locator(SEL_VED).select_option(value='D')

    cod_conta = _resolver_cod_conta_erp(page, agencia, conta)
    if not cod_conta:
        raise RuntimeError(
            f'Conta ERP nao encontrada para {agencia}/{conta}. '
            'Configure cod_conta_erp no mapa_contas.csv ou verifique o select no ERP.'
        )
    page.locator(SEL_CONTA).select_option(value=cod_conta)
    page.locator(SEL_TIPO_PAG).select_option(value='8')

    _clicar_gravar_nota_auto(page, log)
    _clicar_finalizar_nota_auto(page, log)
    codigo_cp = _extrair_codigo_nota_auto(page)

    db.atualizar_status_tarifa_bancaria(
        tarifa_id,
        'Processado',
        codigo_interno=codigo_cp or f'CP-AUTO-{tarifa_id}',
        erro_processamento='',
    )
    log(f'   Tarifa #{tarifa_id} processada. Codigo CP: {codigo_cp or "—"}')
    return True


def executar_lancamento_tarifas(config=None, tarifas=None, log_callback=None):
    def log(msg):
        _log(msg, log_callback=log_callback)

    config = config or db.carregar_configuracoes()
    if not config or not str(config.get('link') or '').strip():
        log('Configuracoes ERP nao encontradas.')
        return False

    cfg_tarifa = db.obter_config_tarifa_erp()
    lista = tarifas or db.listar_tarifas_bancarias(status='Pendente')
    if not lista:
        log('Nenhuma tarifa pendente para lancar.')
        return True

    log(f'Iniciando lancamento de {len(lista)} tarifa(s) pendente(s)...')

    processadas = 0
    erros = 0

    try:
        with ERP_LOCK:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=usar_headless(),
                    channel='chrome',
                )
                context = browser.new_context(viewport={'width': 1380, 'height': 900})
                page = context.new_page()
                try:
                    log('Realizando login no ERP...')
                    fazer_login_erp(page, config, log=log)
                    verificar_pagina_erp_ok(page, log)

                    for tarifa in lista:
                        try:
                            lancar_tarifa(page, tarifa, config, cfg_tarifa, log)
                            processadas += 1
                        except ErroServidorIndisponivel:
                            raise
                        except Exception as exc:
                            erros += 1
                            msg_erro = str(exc).strip() or type(exc).__name__
                            log(f'   ERRO tarifa #{tarifa.get("id")}: {msg_erro}')
                            db.atualizar_status_tarifa_bancaria(
                                tarifa.get('id'),
                                'Erro',
                                erro_processamento=msg_erro,
                            )
                finally:
                    try:
                        context.close()
                    except Exception:
                        pass
                    try:
                        browser.close()
                    except Exception:
                        pass
    except ErroServidorIndisponivel:
        log('Servidor ERP indisponivel (503).')
        return False
    except Exception as exc:
        log(f'Falha na automacao de tarifas: {exc}')
        return False

    log(
        f'Lancamento concluido: {processadas} processada(s), '
        f'{erros} erro(s), {len(lista) - processadas - erros} pendente(s).'
    )
    return erros == 0
