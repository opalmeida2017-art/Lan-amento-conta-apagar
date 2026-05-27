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
    Extrai placas da observação da NFe.
    Prioridade: texto após PLACA/PLAC, depois modelos com esse prefixo, depois demais.
    """
    if not memoria_obs:
        return []

    obs_upper = memoria_obs.upper()
    placas = []

    def _adicionar(raw):
        p = _normalizar_placa(raw)
        if _placa_valida_candidata(p) and p not in placas:
            placas.append(p)

    # 1) Explícito: "PLACA RCM1D82" (caso Volvo / caminhão)
    for m in re.finditer(
        r'PLACA\s*[:\s]?\s*([A-Z]{3}[0-9][A-Z0-9][0-9]{2}|[A-Z]{3}[0-9]{4})',
        obs_upper,
    ):
        _adicionar(m.group(1))

    # 2) Modelos cadastrados que exigem prefixo PLACA/PLAC no texto
    for modelo in modelos_usuario:
        if not re.search(r'PLAC', modelo, re.IGNORECASE):
            continue
        regex_dinamico = converter_modelo_para_regex(modelo)
        if not regex_dinamico:
            continue
        for match in re.finditer(regex_dinamico, memoria_obs, re.IGNORECASE):
            _adicionar(match.group(1))

    # 3) Demais modelos (com filtro anti FAB 2021)
    for modelo in modelos_usuario:
        if re.search(r'PLAC', modelo, re.IGNORECASE):
            continue
        regex_dinamico = converter_modelo_para_regex(modelo)
        if not regex_dinamico:
            continue
        for match in re.finditer(regex_dinamico, memoria_obs, re.IGNORECASE):
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


def processar_veiculo(page, log, idx, memoria_obs, modelos_usuario):
    campo_veiculo = page.locator(f'input[id="formCad:tableItemNota:{idx}:veiculoInput"]')
    valor_v = campo_veiculo.input_value().strip()

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
        else:
            log(f'-> ✅ SUCESSO! Veículo validado pelo sistema: {valor_atual_veiculo}')
            return valor_atual_veiculo, placas_encontradas

    return False, placas_encontradas
