import time
import re
import database_setup as db
from robo_web.utils import converter_modelo_km_para_regex

def processar_km(page, log, item_block, memoria_obs):
    campo_km = item_block.locator('tr').filter(has=page.locator('span', has_text="KM:")).locator('input[type="text"]').first
    
    if campo_km.count() > 0:
        if not campo_km.input_value().strip() or campo_km.input_value() == "0":
            
            # Puxa os modelos configurados no Painel
            modelos_usuario = db.obter_modelos_km()
            if not modelos_usuario:
                log("⚠️ Aviso: Nenhum modelo de KM cadastrado! Usando padrão interno.")
                modelos_usuario = ["KM: 1", "KM 1", "HIDROMETRO: 1", "ODO: 1"]

            km_detectado = None
            
            # Testa cada modelo cadastrado
            for modelo in modelos_usuario:
                regex_dinamico = converter_modelo_km_para_regex(modelo)
                if regex_dinamico:
                    busca = re.search(regex_dinamico, memoria_obs, re.IGNORECASE)
                    if busca:
                        # Achou! Tira pontos, vírgulas e espaços e para o loop
                        km_detectado = re.sub(r"[.,\s]", "", busca.group(1))
                        log(f"-> 🔎 KM detectado via regra '{modelo}': {km_detectado}")
                        break
            
            if km_detectado:
                campo_km.click()
                campo_km.clear()
                campo_km.press_sequentially(km_detectado, delay=50)
                campo_km.press("Tab") 
                log("-> ✅ KM preenchido com sucesso.")
            else:
                log("-> ⚠️ Nenhum KM válido encontrado na observação.")
        else:
            log("-> KM já está preenchido na tela.")