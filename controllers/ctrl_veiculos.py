import threading

import database_setup as db
from robo_web import modulo_frota


class VeiculosController:
    def __init__(self):
        self.view = None
        self._sincronizando = False

    def obter_veiculos_banco(self, limite=100, placa_filtro=''):
        return db.obter_frota_erp(limite=limite, placa_filtro=placa_filtro)

    def obter_ultima_atualizacao_frota(self):
        return db.obter_ultima_sincronizacao_frota()

    def sincronizar_frota_erp(self, ao_finalizar=None):
        if self._sincronizando:
            return False

        def rodar():
            self._sincronizando = True
            try:
                modulo_frota.baixar_e_importar_frota()
            finally:
                self._sincronizando = False
                if self.view and ao_finalizar:
                    try:
                        self.view.after(0, ao_finalizar)
                    except Exception:
                        pass

        threading.Thread(target=rodar, daemon=True).start()
        return True
