import time
import re
import database_setup as db
from robo_web.utils import converter_modelo_para_regex

# Padrões que parecem placa mas são ano/modelo (ex.: ANO FAB 2021)
_PREFIXOS_FALSO_POSITIVO = ('FAB', 'MOD', 'ANO', 'COR', 'CHA', 'CHAS')

MSG_ERRO_PLACA_VEICULO = db.MSG_ERRO_PLACA_VEICULO
MSG_ERRO_CARRETA_DUPLICADA = db.MSG_ERRO_CARRETA_DUPLICADA
MSG_ERRO_FALTA_VEICULO_OBS = db.MSG_ERRO_FALTA_VEICULO_OBS


def _normalizar_placa(texto):
    return db.normalizar_placa_frota(texto)


def _placa_valida_candidata(placa):
    """Descarta FAB2021, MOD2021 etc. (ano de fabricação, não placa)."""
    p = _normalizar_placa(placa)
    if len(p) < 7:
        return False
    if p[:3] in _PREFIXOS_FALSO_POSITIVO and re.match(r'^[A-Z]{3}(19|20)\d{2}$', p):
        return False
    if re.fullmatch(r'(19|20)\d{2}', p[3:]):
        return False
    return True


def extrair_placas_da_observacao(memoria_obs, modelos_usuario):
    """
    Extrai placas da observação da NFe usando os modelos configurados.
    O prefixo antes da placa deve ser idêntico ao da NFe; letras da placa
    aceitam maiúsculas ou minúsculas.
    """
    if not memoria_obs:
        return []

    placas = []

    def _adicionar(raw):
        p = _normalizar_placa(raw)
        if _placa_valida_candidata(p) and p not in placas:
            placas.append(p)

    for modelo in modelos_usuario or []:
        regex_dinamico = converter_modelo_para_regex(modelo)
        if not regex_dinamico:
            continue
        for match in re.finditer(regex_dinamico, memoria_obs):
            _adicionar(match.group(1))

    return placas


def _placa_para_mensagem_erro(placas_encontradas, campo_veiculo_valor):
    """Placa exibida no painel = mesma lógica da busca (não o lixo do campo após falha)."""
    if placas_encontradas:
        return placas_encontradas[0]
    valor = (campo_veiculo_valor or '').strip()
    if valor and 'NAO ENCONTRADO' not in valor.upper() and 'REFAZER' not in valor.upper():
        v = _normalizar_placa(valor)
        if _placa_valida_candidata(v):
            return v
    return valor or '?'


def _tentar_preencher_cod_veiculo_campo(campo_veiculo, cod_veiculo, log, placa_origem=''):
    cod_veiculo = str(cod_veiculo or '').strip()
    if not cod_veiculo:
        return False, ''

    origem = f' (placa {placa_origem})' if placa_origem else ''
    log(f'-> Preenchendo veículo pelo código {cod_veiculo}{origem}')
    campo_veiculo.click()
    campo_veiculo.clear()
    campo_veiculo.press_sequentially(cod_veiculo, delay=100)
    time.sleep(1)
    campo_veiculo.press('Enter')
    time.sleep(1.5)
    campo_veiculo.press('Enter')
    time.sleep(0.5)
    campo_veiculo.press('Tab')

    time.sleep(2)
    valor_atual_veiculo = campo_veiculo.input_value().strip().upper()

    if (
        'CADASTRO NAO ENCONTRADO' in valor_atual_veiculo
        or 'REFAZER CONSULTA' in valor_atual_veiculo
        or 'SEM DADOS' in valor_atual_veiculo
        or not valor_atual_veiculo
    ):
        log(
            f"-> ❌ Código '{cod_veiculo}' rejeitado pelo ERP "
            f"(Retornou: {valor_atual_veiculo})."
        )
        campo_veiculo.clear()
        return False, valor_atual_veiculo

    log(f'-> ✅ SUCESSO! Veículo validado pelo sistema: {valor_atual_veiculo}')
    return True, valor_atual_veiculo


def _label_coluna_frota(coluna):
    if coluna == 'placa':
        return 'placa cavalo'
    return str(coluna or 'placa')


def montar_mensagem_erro_placa_nao_encontrada(placas_tentadas):
    """Mensagem detalhada para erro_importacao quando a placa não está na frota."""
    placas = []
    for item in placas_tentadas or []:
        p = _normalizar_placa(item)
        if p and p not in placas:
            placas.append(p)

    principal = placas[0] if placas else '?'
    base = (
        f'{MSG_ERRO_PLACA_VEICULO}: placa {principal} não encontrada no painel de veículos '
        '(placa/carreta1/carreta2/carreta3).'
    )

    parecidas = db.buscar_placas_parecidas_na_frota(principal)
    if parecidas:
        itens = []
        for item in parecidas:
            col = _label_coluna_frota(item.get('coluna'))
            itens.append(
                f"{item['placa']} (cod. {item['cod_veiculo']}, {col})"
            )
        base += f" Placa(s) parecida(s) no painel: {', '.join(itens)}."
        base += (
            ' Verifique se a NFe trocou letras parecidas (L/I, O/0) '
            'ou atualize a frota na aba Veículos.'
        )
    else:
        base += (
            ' Atualize a frota na aba Veículos ou informe a placa correta '
            'na coluna Placa da aba Execução (duplo clique).'
        )

    if len(placas) > 1:
        base += f' Placas testadas na observação: {", ".join(placas)}.'

    return base


def _resolver_veiculo_pela_placa(placa_tentativa, log):
    """
    Retorna (cod_veiculo, coluna, erro_tipo).
    erro_tipo: None | 'carreta_duplicada' | 'nao_encontrado'
    """
    placa_tentativa = _normalizar_placa(placa_tentativa)
    resultado = db.resolver_placa_na_frota(placa_tentativa)
    status = resultado.get('status')

    if status == 'carreta_duplicada':
        codigos = ', '.join(resultado.get('codigos') or [])
        log(
            f"-> ❌ Placa '{placa_tentativa}' é carreta duplicada nos cavalos: {codigos}"
        )
        return None, '', 'carreta_duplicada'

    if status != 'ok':
        parecidas = db.buscar_placas_parecidas_na_frota(placa_tentativa)
        log(
            f"-> ❌ Placa '{placa_tentativa}' não encontrada no painel de veículos "
            '(placa/carreta1/carreta2/carreta3).'
        )
        if parecidas:
            sugestoes = ', '.join(
                f"{p['placa']} (cod. {p['cod_veiculo']})" for p in parecidas
            )
            log(f'-> 💡 Placa(s) parecida(s) no painel: {sugestoes}')
        return None, '', 'nao_encontrado'

    cod_veiculo = resultado.get('cod_veiculo', '')
    coluna = resultado.get('coluna', '')
    log(
        f"-> 🔎 Placa '{placa_tentativa}' identificada no painel "
        f"(codVeiculo={cod_veiculo}, coluna={coluna})."
    )
    return cod_veiculo, coluna, None


def processar_veiculo(page, log, idx, memoria_obs, modelos_usuario, placa_painel=None):
    """
    Retorna (resultado_veiculo, placas_extraidas, erro_tipo).
    erro_tipo: None | 'carreta_duplicada' | 'nao_encontrado'
    """
    campo_veiculo = page.locator(f'input[id="formCad:tableItemNota:{idx}:veiculoInput"]')
    valor_v = campo_veiculo.input_value().strip()
    erro_tipo = None

    placa_painel = _normalizar_placa(placa_painel) if placa_painel else ''

    # O ERP pode pré-preencher com cavalo antigo (carreta trocada de composição).
    if valor_v and 'SEM DADOS' not in valor_v.upper():
        log(
            f'-> Veículo já preenchido na tela ({valor_v}); apagando para '
            'reinserir conforme placa verificada no painel de veículos.'
        )
        campo_veiculo.click()
        campo_veiculo.clear()
        time.sleep(0.5)

    if placa_painel:
        log(
            f'-> Placa informada no painel do robô: {placa_painel} '
            '(observação da NFe ignorada).'
        )
        cod_veiculo, coluna, erro_tipo = _resolver_veiculo_pela_placa(placa_painel, log)
        if erro_tipo == 'carreta_duplicada':
            return False, [placa_painel], 'carreta_duplicada'
        if not cod_veiculo:
            return False, [placa_painel], erro_tipo or 'nao_encontrado'
        ok, valor_atual = _tentar_preencher_cod_veiculo_campo(
            campo_veiculo, cod_veiculo, log, placa_origem=placa_painel,
        )
        if ok:
            return valor_atual, [placa_painel], None
        return False, [placa_painel], 'nao_encontrado'

    log('-> Lendo observação com os modelos do banco de dados...')
    placas_encontradas = extrair_placas_da_observacao(memoria_obs, modelos_usuario)

    if placas_encontradas:
        log(f'-> 🔎 Placas extraídas da observação: {placas_encontradas}')
    else:
        log(
            '-> ⚠️ Nenhuma placa na observação da NFe '
            f'(modelos testados: {modelos_usuario})'
        )

    for placa_tentativa in placas_encontradas:
        cod_veiculo, coluna, erro_tipo = _resolver_veiculo_pela_placa(placa_tentativa, log)
        if erro_tipo == 'carreta_duplicada':
            return False, placas_encontradas, 'carreta_duplicada'
        if not cod_veiculo:
            continue
        ok, valor_atual_veiculo = _tentar_preencher_cod_veiculo_campo(
            campo_veiculo, cod_veiculo, log, placa_origem=placa_tentativa,
        )
        if ok:
            return valor_atual_veiculo, placas_encontradas, None

    if placas_encontradas:
        return False, placas_encontradas, erro_tipo or 'nao_encontrado'
    return False, placas_encontradas, 'sem_placa_observacao'
