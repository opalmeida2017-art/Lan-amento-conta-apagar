import time
import re
from robo_web.utils import converter_modelo_para_regex

def processar_veiculo(page, log, idx, memoria_obs, modelos_usuario):
    campo_veiculo = page.locator(f'input[id="formCad:tableItemNota:{idx}:veiculoInput"]')
    valor_v = campo_veiculo.input_value().strip()
    
    if valor_v and "SEM DADOS" not in valor_v.upper():
        log(f"-> Veículo já identificado na tela: {valor_v}")
        return valor_v # Retorna a string do veículo em vez de True

    log("-> Veículo vazio. Lendo observação com os modelos do banco de dados...")
    placas_encontradas = []
    
    for modelo in modelos_usuario:
        regex_dinamico = converter_modelo_para_regex(modelo)
        if regex_dinamico:
            for match in re.finditer(regex_dinamico, memoria_obs, re.IGNORECASE):
                placa_extraida = match.group(1).replace("-", "").replace(" ", "").upper()
                if placa_extraida not in placas_encontradas:
                    placas_encontradas.append(placa_extraida)
    
    if placas_encontradas:
        log(f"-> 🔎 Placas extraídas da observação: {placas_encontradas}")
    else:
        log(f"-> ⚠️ Nenhuma placa extraída! Modelos testados: {modelos_usuario}")

    for placa_tentativa in placas_encontradas:
        log(f"-> Testando preenchimento com a Placa: {placa_tentativa}")
        campo_veiculo.click()
        campo_veiculo.clear()
        campo_veiculo.press_sequentially(placa_tentativa, delay=100)
        time.sleep(1)
        campo_veiculo.press("Enter")
        time.sleep(1.5)
        campo_veiculo.press("Enter")
        time.sleep(0.5)
        campo_veiculo.press("Tab") 
        
        time.sleep(2)
        valor_atual_veiculo = campo_veiculo.input_value().strip().upper()
        
        if "CADASTRO NAO ENCONTRADO" in valor_atual_veiculo or "REFAZER CONSULTA" in valor_atual_veiculo or "SEM DADOS" in valor_atual_veiculo or not valor_atual_veiculo:
            log(f"-> ❌ Placa '{placa_tentativa}' rejeitada pelo sistema (Retornou: {valor_atual_veiculo}).")
            campo_veiculo.clear()
        else:
            log(f"-> ✅ SUCESSO! Veículo validado pelo sistema: {valor_atual_veiculo}")
            return valor_atual_veiculo # Retorna a string do veículo em vez de True

    return False