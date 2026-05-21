import re
import time
import database_setup as db

def processar_km(page, log, idx, memoria_obs):
    log(f"   -> Verificando KM para o Item {idx + 1}...")
    
    # 1. LOCALIZA O CAMPO DE KM NA TELA
    # Usamos name^= (que começa com) para driblar a mudança do j_idt143 e size="10"
    campo_km = page.locator(f'input[name^="formCad:tableItemNota:{idx}:j_idt"][size="10"]')
    
    # Backup: caso o seletor flexível falhe, tenta o exato que você mapeou
    if campo_km.count() == 0:
        campo_km = page.locator(f'input[name="formCad:tableItemNota:{idx}:j_idt143"]')

    if campo_km.count() == 0 or not campo_km.first.is_visible():
        log("   ⚠️ Campo de KM não encontrado na tela.")
        return False

    # Verifica se já está preenchido pelo sistema (diferente de 0 ou vazio)
    valor_atual = campo_km.first.input_value().strip()
    if valor_atual and valor_atual != "0":
        log(f"   -> KM já veio preenchido na tela: {valor_atual}")
        return True

    # 2. CARREGA OS MODELOS DO SEU FILTRO NO BANCO DE DADOS
    try:
        km_string = db.obter_modelos_km_string()
        if km_string:
            modelos_km = [m.strip().upper() for m in km_string.split(',') if m.strip()]
        else:
            modelos_km = ["KM 1", "KM: 1", "ODOMETRO 1", "ODO: 1", "ODO 1"] # Backup
    except:
        modelos_km = ["KM 1", "KM: 1", "ODOMETRO 1", "ODO: 1", "ODO 1"]

    # 3. MÁGICA DA EXTRAÇÃO (Transforma o "1" na busca do número exato)
    km_encontrado = None
    obs_upper = memoria_obs.upper()
    
    for modelo in modelos_km:
        if "1" not in modelo:
            continue # Pula se o modelo estiver configurado errado

        # Transforma o "ODO: 1" em uma RegEx poderosa -> r"ODO:\s*([\d\.,]+)"
        partes = modelo.split("1")
        prefixo = re.escape(partes[0].strip()).replace(r"\ ", r"\s*")
        sufixo = re.escape(partes[1].strip()).replace(r"\ ", r"\s*") if len(partes) > 1 else ""
        
        # Padrão: Prefixo + (Qualquer número, ponto ou vírgula) + Sufixo
        padrao = rf"{prefixo}\s*([\d\.,]+)\s*{sufixo}"
        
        match = re.search(padrao, obs_upper)
        if match:
            km_bruto = match.group(1)
            
            # Limpa formatação brasileira (Ex: "442.816,00" -> "442816")
            # Remove os pontos e pega só o que vem antes da vírgula
            km_limpo = km_bruto.replace(".", "").split(",")[0]
            km_encontrado = km_limpo
            
            log(f"   -> 🛣️ KM extraído da observação usando a máscara '{modelo}': {km_encontrado}")
            break

    # 4. PREENCHE O CAMPO DE KM SE ENCONTRADO
    if km_encontrado:
        campo_km.first.click()
        campo_km.first.clear()
        campo_km.first.fill(km_encontrado)
        campo_km.first.press("Tab") # Dispara o gatilho do JSF
        time.sleep(1)
        return True
    else:
        log("   ⚠️ Nenhum KM encontrado nas observações usando os filtros atuais.")
        return False