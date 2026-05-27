"""Filial e unidade de embarque (filtros salvos + tela ERP)."""
import re
import time

import database_setup as db

AVISO_FILTRO_UI = (
    '⚠️ Com Cod. Filial e Cod. Unid. Embarque preenchidos e salvos, '
    'TODAS as notas serão lançadas nessa filial e UE (um único CNPJ/empresa). '
    'Durante o lançamento o robô altera só a UE do item; '
    'ao abrir a nota ele aplica Filial + UE antes de finalizar. '
    'Deixe em branco para o ERP escolher automaticamente.'
)


def carregar_codigos_filial_ue():
    dados = db.carregar_filtros() or {}
    return {
        'cod_filial': str(dados.get('cod_filial', '')).strip(),
        'cod_unidade_embarque': str(dados.get('cod_unidade_embarque', '')).strip(),
    }


def filial_ue_fixos_configurados():
    """True quando filial e UE estão preenchidos — vale para todas as notas."""
    c = carregar_codigos_filial_ue()
    return bool(c['cod_filial'] and c['cod_unidade_embarque'])


def obter_codigos_para_nota(log=None):
    """
    Retorna (cod_filial, cod_ue, aplicar_fixo).
    aplicar_fixo=True: usar em todas as notas; False: comportamento padrão do ERP.
    """
    c = carregar_codigos_filial_ue()
    cod_f, cod_u = c['cod_filial'], c['cod_unidade_embarque']
    aplicar = filial_ue_fixos_configurados()
    if aplicar and log:
        log(f'   🏢 Filial/UE fixos nos filtros: filial={cod_f}, UE={cod_u} (todas as notas)')
    return cod_f, cod_u, aplicar


def _primeiro_locator_disponivel(candidatos):
    for candidato in candidatos:
        if candidato.count() > 0:
            return candidato
    return candidatos[-1]


def _locator_esta_visivel(locator, timeout=1200):
    try:
        locator.first.wait_for(state='visible', timeout=timeout)
        return True
    except Exception:
        return False


def _preencher_select_locator(loc, codigo, log, nome_campo):
    codigo = str(codigo).strip()
    if not codigo:
        return False

    if loc.count() == 0:
        log(f'   ⚠️ Campo {nome_campo} não encontrado.')
        return False

    try:
        loc.select_option(value=codigo, timeout=4000)
        time.sleep(1)
        valor = loc.evaluate('el => el.value')
        if valor == codigo:
            log(f'   ✅ {nome_campo} = {codigo}')
            return True
    except Exception:
        pass

    try:
        loc.click()
        time.sleep(0.4)
        loc.select_option(label=re.compile(rf'^{re.escape(codigo)}\s*-', re.I))
        time.sleep(1)
        log(f'   ✅ {nome_campo} = {codigo} (por texto)')
        return True
    except Exception:
        pass

    try:
        loc.click()
        time.sleep(0.3)
        loc.press_sequentially(codigo, delay=80)
        time.sleep(0.8)
        loc.press('Enter')
        time.sleep(1)
        loc.press('Enter')
        time.sleep(0.5)
        log(f'   ✅ {nome_campo} = {codigo} (digitação + Enter)')
        return True
    except Exception as e:
        log(f'   ⚠️ Não foi possível preencher {nome_campo}: {e}')
        return False


def _preencher_select_codigo(page, seletor, codigo, log, nome_campo):
    loc = page.locator(seletor).first
    return _preencher_select_locator(loc, codigo, log, nome_campo)


def _localizar_select_ue_item(item_block, idx_item):
    padrao_nome = f'formCad:tableItemNota:{idx_item}:'
    linha_ue = item_block.locator('tr').filter(
        has=item_block.locator('span', has_text=re.compile(r'Unid\.?\s*Emb\.?', re.I)),
    )
    return _primeiro_locator_disponivel([
        linha_ue.locator(f'select[name^="{padrao_nome}"]').first,
        linha_ue.locator('select').first,
        item_block.locator(f'select[name^="{padrao_nome}"]').first,
        linha_ue.locator('select').first,
    ])


def _localizar_select_nota(page, sufixo_campo, rotulo_regex):
    return _primeiro_locator_disponivel([
        page.locator(f'select#formnota\\:{sufixo_campo}').first,
        page.locator(f'select[name="formnota:{sufixo_campo}"]').first,
        page.locator(f'select[id^="formnota:"][id$="{sufixo_campo}"]').first,
        page.locator(f'select[name^="formnota:"][name$="{sufixo_campo}"]').first,
        page.locator('tr, td, div').filter(
            has_text=rotulo_regex,
            has=page.locator('select'),
        ).first.locator('select').first,
        page.locator('select').filter(has_text=re.compile(r'^\s*\d+\s*-', re.I)).first,
    ])


def localizar_select_unidade_mestre(page):
    return _primeiro_locator_disponivel([
        page.locator('select[name="formCad:j_idt31"]').first,
        page.locator('select[id="formCad:j_idt31"]').first,
        page.locator('tr, td, div').filter(
            has_text=re.compile(r'(unid|unidade).*(emb)', re.I),
            has=page.locator('select'),
        ).first.locator('select').first,
        page.locator('select[name^="formCad:j_idt"]').first,
    ])


def localizar_select_filial_lancamento(page):
    return _primeiro_locator_disponivel([
        page.locator('select[name="formCad:j_idt26"]').first,
        page.locator('select[id="formCad:j_idt26"]').first,
        page.locator('tr, td, div').filter(
            has_text=re.compile(r'filial', re.I),
            has=page.locator('select'),
        ).first.locator('select').first,
        page.locator('select[name^="formCad:j_idt"]').first,
    ])


def localizar_botao_atualizar_painel(page):
    return _primeiro_locator_disponivel([
        page.locator('input#formCad\\:buttonAtualizar').first,
        page.locator('input[name="formCad:buttonAtualizar"]').first,
        page.locator('input[id^="formCad:"][id$="buttonAtualizar"]').first,
        page.locator('input[value*="Atualizar"]').first,
        page.locator('button', has_text=re.compile(r'Atualizar', re.I)).first,
    ])


def localizar_observacao_nota_cp(page):
    return _primeiro_locator_disponivel([
        page.locator('textarea[name="formCad:j_idt51"]').first,
        page.locator('textarea[id="formCad:j_idt51"]').first,
        page.locator('tr, td, div').filter(
            has_text=re.compile(r'Obs\.?\s*Nota\s*CP', re.I),
            has=page.locator('textarea'),
        ).first.locator('textarea').first,
        page.locator('textarea').first,
    ])


def localizar_botao_importar_cp(page):
    return _primeiro_locator_disponivel([
        page.locator('input#formCad\\:importarCP').first,
        page.locator('input[name="formCad:importarCP"]').first,
        page.locator('input[id^="formCad:"][id$="importarCP"]').first,
        page.locator('input[value*="Importar para uma Conta a Pagar"]').first,
        page.locator('button', has_text=re.compile(r'Importar.*Conta a Pagar', re.I)).first,
    ])


def localizar_link_abrir_nota(page):
    return _primeiro_locator_disponivel([
        page.locator('a#formCad\\:linkAbrirNota').first,
        page.locator('a[id^="formCad:"][id$="linkAbrirNota"]').first,
        page.locator('a[name="formCad:linkAbrirNota"]').first,
        page.locator('a', has_text=re.compile(r'Abrir nota.*código interno', re.I)).first,
        page.locator('a', has_text=re.compile(r'Abrir nota', re.I)).first,
    ])


def localizar_checkbox_despesa_nota(page):
    return _primeiro_locator_disponivel([
        page.locator('input#formnota\\:Nota_despesa').first,
        page.locator('input[name="formnota:Nota_despesa"]').first,
        page.locator('input[id^="formnota:"][id$="Nota_despesa"]').first,
        page.locator('input[type="checkbox"]').first,
    ])


def localizar_linhas_itens_nota(page):
    return _primeiro_locator_disponivel([
        page.locator('tbody[id="formtableitemNota:tableitemNota:tb"] > tr.rf-dt-r'),
        page.locator('table[id="formtableitemNota:tableitemNota"] tbody > tr.rf-dt-r'),
        page.locator('tr[id^="formtableitemNota:tableitemNota:"]').filter(
            has=page.locator('td'),
        ),
    ])


def _obter_link_edicao_item(linha_item):
    return _primeiro_locator_disponivel([
        linha_item.locator('td').nth(2).locator('a').first,
        linha_item.locator('td').nth(3).locator('a').first,
        linha_item.locator('a').first,
    ])


def _obter_codigo_item_linha(linha_item):
    try:
        return (linha_item.locator('td').nth(2).text_content() or '').strip()
    except Exception:
        return ''


def abrir_aba_itens_nota(page, log):
    seletores_grade = [
        'tbody[id="formtableitemNota:tableitemNota:tb"] > tr.rf-dt-r',
        'table[id="formtableitemNota:tableitemNota"]',
        'form[name="formtableitemNota"]',
        'form[name="formitemNota"]',
    ]

    def _itens_visiveis():
        for seletor in seletores_grade:
            try:
                page.locator(seletor).first.wait_for(state='visible', timeout=2500)
                if 'formtableitemNota' in seletor or 'formitemNota' in seletor:
                    log('   📑 Grade/formulário de itens da nota já está disponível.')
                return True
            except Exception:
                continue

        linhas = localizar_linhas_itens_nota(page)
        try:
            if linhas.count() == 0:
                return False
            return _locator_esta_visivel(linhas.first, timeout=1500)
        except Exception:
            return False

    if _itens_visiveis():
        return True

    candidatos = [
        page.locator('td[data-tabname="tabMD1"]').first,
        page.locator('td[id$="tabMD1:header"]').first,
        page.locator('span.rf-tab-lbl').filter(
            has_text=re.compile(r'^\s*2\.\s*Itens', re.I),
        ).first,
        page.locator('span.rf-tab-lbl').filter(
            has_text=re.compile(r'itens', re.I),
        ).first,
        page.locator('a', has_text=re.compile(r'^\s*2\.\s*Itens', re.I)).first,
        page.locator('a', has_text=re.compile(r'aba\s*2', re.I)).first,
        page.locator('a', has_text=re.compile(r'dados\s+dos\s+itens', re.I)).first,
        page.locator('a', has_text=re.compile(r'itens?\s+da\s+nota', re.I)).first,
        page.locator('td, a, span').filter(
            has_text=re.compile(r'^\s*2\.\s*Itens', re.I),
        ).first,
        page.locator('td, a, span').filter(
            has_text=re.compile(r'itens?', re.I),
        ).nth(1),
    ]

    for tentativa in range(3):
        if tentativa > 0:
            log(f'   🔁 Tentando abrir a aba 2. Itens novamente ({tentativa + 1}/3)...')
            time.sleep(1.2)

        if _itens_visiveis():
            return True

        for aba in candidatos:
            if aba.count() == 0:
                continue
            try:
                aba.scroll_into_view_if_needed(timeout=1500)
            except Exception:
                pass

            log('   👉 Clicando na aba 2. Itens...')
            if not _clicar_locator_com_fallback(aba, timeout=5000):
                continue

            time.sleep(2)
            if _itens_visiveis():
                log('   📑 Aba de itens da nota aberta.')
                return True
    log('   ⚠️ Aba 2 / itens da nota não encontrada.')
    return False


def _localizar_select_item_nota(page, rotulo_regex, excluir_nome):
    return _primeiro_locator_disponivel([
        page.locator(
            f'select:not([name="{excluir_nome}"]):not([id="{excluir_nome}"])'
        ).filter(has_text=re.compile(r'^\s*\d+\s*-', re.I)).first,
        page.locator('tr, td, div').filter(
            has_text=rotulo_regex,
            has=page.locator(f'select:not([name="{excluir_nome}"])'),
        ).first.locator('select').first,
        page.locator(f'select[name*="itemNota"]:not([name="{excluir_nome}"])').first,
        page.locator(f'select[id*="itemNota"]:not([id="{excluir_nome}"])').first,
    ])


def abrir_dados_gerais_item_nota(page):
    select_ue = localizar_ue_select_item_nota(page)
    if _locator_esta_visivel(select_ue, timeout=1200):
        return True

    candidatos = [
        page.locator('td#formitemNota\\:intab1_0\\:header').first,
        page.locator('td[id^="formitemNota:intab1_0:header"]').first,
        page.locator('td[data-tabname="intab1_0"]').first,
        page.locator('td, a, span').filter(
            has_text=re.compile(r'A\.\s*Dados Gerais', re.I),
        ).first,
    ]
    for aba in candidatos:
        if aba.count() == 0:
            continue
        try:
            aba.click(force=True)
            time.sleep(0.8)
            select_ue = localizar_ue_select_item_nota(page)
            if _locator_esta_visivel(select_ue, timeout=2000):
                return True
        except Exception:
            continue
    return False


def localizar_ue_select_item_nota(page):
    return _primeiro_locator_disponivel([
        page.locator('select#formitemNota\\:ItemNota_unidadeEmbarque').first,
        page.locator('select[name="formitemNota:ItemNota_unidadeEmbarque"]').first,
        page.locator('select[id^="formitemNota:"][id$="ItemNota_unidadeEmbarque"]').first,
        page.locator('select[name^="formitemNota:"][name$="ItemNota_unidadeEmbarque"]').first,
        page.locator('tr, td, div').filter(
            has_text=re.compile(r'(unid|unidade).*(emb)', re.I),
            has=page.locator('select[name*="unidadeEmbarque"]'),
        ).first.locator('select').first,
    ])


def clicar_gravar_item_nota(page, log):
    candidatos = [
        page.locator('input#formitemNota\\:gravaritemNota').first,
        page.locator('input[name="formitemNota:gravaritemNota"]').first,
        page.locator('input[id^="formitemNota:"][id$="gravaritemNota"]').first,
        page.locator('input[name^="formitemNota:"][name$="gravaritemNota"]').first,
        page.locator('input[title*="Gravar"]').first,
        page.locator('input[src*="gravarmacro"]').first,
    ]
    for botao in candidatos:
        if botao.count() == 0:
            continue
        try:
            botao.click(timeout=3000, force=True)
            try:
                page.locator('li, div, span').filter(
                    has_text=re.compile(r'Dados alterados com sucesso', re.I),
                ).first.wait_for(state='visible', timeout=8000)
            except Exception:
                time.sleep(1.5)
            log('   💾 Item gravado com sucesso.')
            return True
        except Exception:
            continue
    log('   ⚠️ Botão Gravar do item não encontrado.')
    return False


def clicar_cancelar_item_nota(page, log):
    form_item = page.locator('form#formitemNota, form[name="formitemNota"]').first
    linhas_itens = localizar_linhas_itens_nota(page)

    try:
        if form_item.count() == 0 or not form_item.is_visible(timeout=1000):
            return True
    except Exception:
        try:
            if linhas_itens.count() > 0:
                return True
        except Exception:
            pass

    candidatos = [
        page.locator('input#formitemNota\\:cancelaritemNota').first,
        page.locator('input[name="formitemNota:cancelaritemNota"]').first,
        page.locator('input[id^="formitemNota:"][id$="cancelaritemNota"]').first,
        page.locator('input[name^="formitemNota:"][name$="cancelaritemNota"]').first,
        page.locator('input[title*="Cancelar"]').first,
        page.locator('input[src*="cancel"]').first,
        page.locator('button', has_text=re.compile(r'cancelar|fechar|voltar', re.I)).first,
    ]
    for botao in candidatos:
        if botao.count() == 0:
            continue
        try:
            botao.click(timeout=3000, force=True)
            time.sleep(1)
            try:
                page.locator('form#formitemNota, form[name="formitemNota"]').first.wait_for(
                    state='hidden', timeout=5000,
                )
            except Exception:
                pass
            try:
                localizar_linhas_itens_nota(page).first.wait_for(state='visible', timeout=5000)
            except Exception:
                pass
            log('   ↩️ Retornando para a grade de itens da nota.')
            return True
        except Exception:
            continue

    try:
        linhas_itens = localizar_linhas_itens_nota(page)
        if linhas_itens.count() > 0:
            return True
    except Exception:
        pass

    log('   ⚠️ Não foi possível fechar o formulário do item.')
    return False


def _clicar_locator_com_fallback(locator, timeout=4000):
    try:
        locator.wait_for(state='visible', timeout=timeout)
        locator.click(timeout=timeout)
        return True
    except Exception:
        pass

    try:
        locator.click(timeout=timeout, force=True)
        return True
    except Exception:
        pass

    try:
        locator.evaluate('(el) => el.click()')
        return True
    except Exception:
        return False


def _abrir_item_nota_por_indice(page, linha_item, idx_item, log):
    link_item = _obter_link_edicao_item(linha_item)
    if link_item.count() == 0:
        log(f'   ⚠️ Link do item {idx_item + 1} não encontrado.')
        return False

    try:
        link_item.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    abriu = _clicar_locator_com_fallback(link_item, timeout=5000)
    if not abriu:
        botao_alternativo = _primeiro_locator_disponivel([
            linha_item.locator('img[title*="Alter"]').first,
            linha_item.locator('img[title*="Editar"]').first,
            linha_item.locator('img[src*="alter"]').first,
            linha_item.locator('img[src*="edit"]').first,
            linha_item.locator('input[title*="Alter"]').first,
            linha_item.locator('input[title*="Editar"]').first,
            linha_item.locator('a[onclick*="itemNota"]').first,
        ])
        if botao_alternativo.count() > 0:
            try:
                botao_alternativo.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                pass
            abriu = _clicar_locator_com_fallback(botao_alternativo, timeout=5000)

    if not abriu:
        log(f'   ⚠️ Não foi possível abrir o item {idx_item + 1}.')
        return False

    log(f'   🧩 Abrindo edição do item {idx_item + 1}...')
    time.sleep(1.5)
    try:
        page.locator('form#formitemNota, form[name="formitemNota"]').first.wait_for(
            state='visible', timeout=10000,
        )
    except Exception:
        pass

    abrir_dados_gerais_item_nota(page)
    select_ue = localizar_ue_select_item_nota(page)
    if not _locator_esta_visivel(select_ue, timeout=8000):
        log(f'   ⚠️ Campo UE do item {idx_item + 1} não apareceu após abrir o item.')
        return False
    return True


def processar_itens_nota_interna(page, log, cod_unidade=None):
    """Na edição do item da nota interna altera somente a UE."""
    if cod_unidade is None:
        c = carregar_codigos_filial_ue()
        cod_unidade = c['cod_unidade_embarque']

    cod_unidade = str(cod_unidade or '').strip()
    if not cod_unidade:
        return True

    if not abrir_aba_itens_nota(page, log):
        return False

    linhas = localizar_linhas_itens_nota(page)
    if not _locator_esta_visivel(linhas.first, timeout=5000):
        log('   ⚠️ A grade de itens não ficou visível após abrir a aba 2.')
        return False
    total_itens = linhas.count()
    if total_itens == 0:
        log('   ⚠️ Nenhum item encontrado na grade da nota.')
        return False

    log(f'   📦 Alterando somente a UE em {total_itens} item(ns) da nota...')
    for idx in range(total_itens):
        linhas = localizar_linhas_itens_nota(page)
        linha_item = linhas.nth(idx)
        codigo_item = _obter_codigo_item_linha(linha_item) or '?'

        if not _abrir_item_nota_por_indice(page, linha_item, idx, log):
            return False

        select_ue_item = localizar_ue_select_item_nota(page)
        ok_u = _preencher_select_locator(
            select_ue_item, cod_unidade, log, f'UE do item {idx + 1} ({codigo_item})',
        )
        if not ok_u:
            return False

        if not clicar_gravar_item_nota(page, log):
            return False

        if not clicar_cancelar_item_nota(page, log):
            return False

        time.sleep(0.8)
    return True


def aplicar_filial_ue_itens_nota(page, log, cod_filial=None, cod_unidade=None):
    """Compatibilidade: na edição do item agora só altera a UE."""
    return processar_itens_nota_interna(page, log, cod_unidade)


def abrir_aba_dados_gerais_nota(page, log):
    select_filial = _localizar_select_nota(
        page, 'Nota_filial', re.compile(r'filial', re.I),
    )
    botao_finalizar = _primeiro_locator_disponivel([
        page.locator('img#formnota\\:imgFinalizar').first,
        page.locator('img[id^="formnota:"][id$="imgFinalizar"]').first,
        page.locator('img[src*="iconFinDesfin"]').first,
    ])

    try:
        if (
            (select_filial.count() > 0 and select_filial.is_visible(timeout=800))
            or (botao_finalizar.count() > 0 and botao_finalizar.is_visible(timeout=800))
        ):
            return True
    except Exception:
        pass

    candidatos = [
        page.locator('td[data-tabname="tabMD0"]').first,
        page.locator('td[id$="tabMD0:header"]').first,
        page.locator('span.rf-tab-lbl').filter(
            has_text=re.compile(r'^\s*1\.\s*Dados Gerais$', re.I),
        ).first,
        page.locator('span.rf-tab-lbl').filter(
            has_text=re.compile(r'Dados Gerais', re.I),
        ).first,
        page.locator('td, a, span').filter(
            has_text=re.compile(r'^\s*1\.\s*Dados Gerais$', re.I),
        ).first,
    ]

    for aba in candidatos:
        if aba.count() == 0:
            continue
        try:
            aba.click(force=True)
            time.sleep(1)
        except Exception:
            continue

        try:
            if select_filial.count() > 0:
                select_filial.wait_for(state='visible', timeout=4000)
                log('   📑 Voltando para a aba 1. Dados Gerais da nota.')
                return True
        except Exception:
            pass

        try:
            if botao_finalizar.count() > 0:
                botao_finalizar.wait_for(state='visible', timeout=2000)
                log('   📑 Voltando para a aba 1. Dados Gerais da nota.')
                return True
        except Exception:
            pass

    log('   ⚠️ Não foi possível voltar para a aba 1. Dados Gerais da nota.')
    return False


def clicar_gravar_nota(page, log):
    candidatos = [
        page.locator('input#formnota\\:gravarnota').first,
        page.locator('input[name="formnota:gravarnota"]').first,
        page.locator('input[id^="formnota:"][id$="gravarnota"]').first,
        page.locator('input[name^="formnota:"][name$="gravarnota"]').first,
        page.locator('input[value*="Gravar"]').first,
    ]
    for botao in candidatos:
        if botao.count() == 0:
            continue
        try:
            botao.click(timeout=3000)
            try:
                page.locator('li, div, span').filter(
                    has_text=re.compile(r'Dados alterados com sucesso', re.I),
                ).first.wait_for(state='visible', timeout=8000)
            except Exception:
                time.sleep(2.5)
            log('   💾 Gravando filial/UE na nota antes de finalizar...')
            return True
        except Exception:
            continue
    return False


def clicar_finalizar_nota(page, log):
    candidatos = [
        page.locator('img#formnota\\:imgFinalizar').first,
        page.locator('img[id^="formnota:"][id$="imgFinalizar"]').first,
        page.locator('img[src*="iconFinDesfin"]').first,
        page.locator('img[title*="Final"]').first,
        page.locator('a, button, input', has_text=re.compile(r'Finaliz', re.I)).first,
    ]
    for botao in candidatos:
        if botao.count() == 0:
            continue
        try:
            botao.click(timeout=3000, force=True)
            log('   🏁 Clicando no ícone/botão de Finalizar...')
            return True
        except Exception:
            continue
    log('   ⚠️ Botão/ícone de Finalizar não encontrado.')
    return False


def aplicar_ue_item(item_block, codigo_ue, log, idx_item):
    """Durante o lançamento altera somente a UE do item."""
    codigo_ue = str(codigo_ue or '').strip()
    if not codigo_ue:
        return True

    select_unid_item = _localizar_select_ue_item(item_block, idx_item)
    if select_unid_item.count() == 0:
        log(f'   ⚠️ UE do Item {idx_item + 1} não encontrada.')
        return False

    try:
        select_unid_item.select_option(value=codigo_ue)
        time.sleep(1)
        log(f'   ✅ UE do Item {idx_item + 1} = {codigo_ue}')
        return True
    except Exception as e:
        log(f'   ⚠️ Não foi possível definir a UE do Item {idx_item + 1}: {e}')
        return False


def aplicar_filial_ue_tela_nota(page, log, cod_filial=None, cod_unidade=None):
    """Antes de Finalizar — formnota:Nota_filial e formnota:Nota_unidadeEmbarque."""
    if cod_filial is None or cod_unidade is None:
        c = carregar_codigos_filial_ue()
        cod_filial = cod_filial if cod_filial is not None else c['cod_filial']
        cod_unidade = cod_unidade if cod_unidade is not None else c['cod_unidade_embarque']

    if not cod_filial or not cod_unidade:
        return True

    log('   🏢 Aplicando Cod. Filial / UE na nota (antes de Finalizar)...')
    select_filial = _localizar_select_nota(
        page, 'Nota_filial', re.compile(r'filial', re.I),
    )
    select_ue = _localizar_select_nota(
        page, 'Nota_unidadeEmbarque', re.compile(r'(unid|unidade).*(emb)', re.I),
    )
    ok_f = _preencher_select_locator(select_filial, cod_filial, log, 'Filial (nota)')
    ok_u = _preencher_select_locator(select_ue, cod_unidade, log, 'Unid. Embarque (nota)')

    clicar_gravar_nota(page, log)
    return ok_f and ok_u
