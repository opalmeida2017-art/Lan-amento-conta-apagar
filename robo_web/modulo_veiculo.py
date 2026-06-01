import time
import re
from robo_web.utils import converter_modelo_para_regex

# Padrões que parecem placa mas são ano/modelo (ex.: ANO FAB 2021)
_PREFIXOS_FALSO_POSITIVO = ('FAB', 'MOD', 'ANO', 'COR', 'CHA', 'CHAS')


def _normalizar_placa(texto):
    return texto.replace('-', '').replace(' ', '').upper()


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
    A comparação é exata (maiúsculas, minúsculas e acentos).
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


def _tentar_preencher_placa_campo(campo_veiculo, placa_tentativa, log):
    log(f'-> Testando preenchimento com a Placa: {placa_tentativa}')
    campo_veiculo.click()
    campo_veiculo.clear()
    campo_veiculo.press_sequentially(placa_tentativa, delay=100)
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
        log(f"-> ❌ Placa '{placa_tentativa}' rejeitada pelo sistema (Retornou: {valor_atual_veiculo}).")
        campo_veiculo.clear()
        return False, valor_atual_veiculo

    log(f'-> ✅ SUCESSO! Veículo validado pelo sistema: {valor_atual_veiculo}')
    return True, valor_atual_veiculo


def processar_veiculo(page, log, idx, memoria_obs, modelos_usuario, placa_painel=None):
    campo_veiculo = page.locator(f'input[id="formCad:tableItemNota:{idx}:veiculoInput"]')
    valor_v = campo_veiculo.input_value().strip()

    placa_painel = _normalizar_placa(placa_painel) if placa_painel else ''
    if placa_painel:
        log(f'-> Placa informada no painel do robô: {placa_painel}')
        ok, valor_atual = _tentar_preencher_placa_campo(campo_veiculo, placa_painel, log)
        if ok:
            return valor_atual, [placa_painel]
        return False, [placa_painel]

    if valor_v and 'SEM DADOS' not in valor_v.upper():
        log(f'-> Veículo já identificado na tela: {valor_v}')
        placa_tela = valor_v.split('-')[0].strip() if '-' in valor_v else valor_v
        return valor_v, [_normalizar_placa(placa_tela)]

    log('-> Veículo vazio. Lendo observação com os modelos do banco de dados...')
    placas_encontradas = extrair_placas_da_observacao(memoria_obs, modelos_usuario)

    if placas_encontradas:
        log(f'-> 🔎 Placas extraídas da observação: {placas_encontradas}')
    else:
        log(f'-> ⚠️ Nenhuma placa extraída! Modelos testados: {modelos_usuario}')

    for placa_tentativa in placas_encontradas:
        ok, valor_atual_veiculo = _tentar_preencher_placa_campo(campo_veiculo, placa_tentativa, log)
        if ok:
            return valor_atual_veiculo, placas_encontradas

    return False, placas_encontradas
