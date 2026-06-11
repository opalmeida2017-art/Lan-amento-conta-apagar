import threading

import database_setup as db
from robo_web import modulo_tarifa_bancaria


class TarifaBancariaController:
    def __init__(self, app_controller=None):
        self.view = None
        self.app_controller = app_controller
        self._importando = False
        self._lancando = False

    def obter_tarifas_agrupadas(self, cnpj_filtro='', data_ini='', data_fim='', status='Todos'):
        return db.obter_tarifas_agrupadas_por_cnpj_conta(
            cnpj_filtro=cnpj_filtro,
            data_ini=data_ini,
            data_fim=data_fim,
            status=status,
        )

    def obter_ultima_atualizacao(self):
        return db.obter_ultima_importacao_tarifas() or db.obter_ultima_atualizacao_tarifas()

    def contar_tarifas(self):
        return db.contar_tarifas_bancarias()

    def obter_cnpjs_disponiveis(self):
        vistos = set()
        opcoes = ['Todos']
        for item in db.obter_mapa_contas_sicredi():
            cnpj = str(item.get('cnpj') or '').strip()
            if cnpj and cnpj not in vistos:
                vistos.add(cnpj)
                opcoes.append(cnpj)
        for tarifa in db.listar_tarifas_bancarias():
            cnpj = str(tarifa.get('cnpj') or '').strip()
            if cnpj and cnpj not in vistos:
                vistos.add(cnpj)
                opcoes.append(cnpj)
        return opcoes

    def obter_pasta_planilhas(self):
        return db.obter_pasta_tarifas_bancarias()

    def salvar_pasta_planilhas(self, pasta):
        return db.salvar_pasta_tarifas_bancarias(pasta)

    def obter_config_erp(self):
        return db.obter_config_tarifa_erp()

    def salvar_config_erp(self, cod_fornecedor, cod_grupo, nome_item):
        return db.salvar_config_tarifa_erp(
            cod_fornecedor_sicredi=cod_fornecedor,
            cod_grupo_item_tarifa=cod_grupo,
            nome_item_tarifa=nome_item,
        )

    def lancar_tarifas_pendentes(self, ao_finalizar=None, log_callback=None):
        if self._lancando:
            return False

        def rodar():
            self._lancando = True
            try:
                config = db.carregar_configuracoes()
                modulo_tarifa_bancaria.processar_tarifas_pendentes(
                    config=config,
                    log_callback=log_callback,
                )
            finally:
                self._lancando = False
                if self.view and ao_finalizar:
                    try:
                        self.view.after(0, ao_finalizar)
                    except Exception:
                        pass

        threading.Thread(target=rodar, daemon=True).start()
        return True

    def importar_planilhas_pasta(self, pasta, ao_finalizar=None, log_callback=None):
        if self._importando:
            return False

        def rodar():
            self._importando = True
            try:
                modulo_tarifa_bancaria.importar_tarifas_pasta(
                    pasta,
                    log_callback=log_callback,
                )
            finally:
                self._importando = False
                if self.view and ao_finalizar:
                    try:
                        self.view.after(0, ao_finalizar)
                    except Exception:
                        pass

        threading.Thread(target=rodar, daemon=True).start()
        return True
