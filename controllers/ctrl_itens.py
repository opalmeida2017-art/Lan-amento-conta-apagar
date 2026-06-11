import database_setup as db
import threading
from robo_web import modulo_frota, modulo_migracao

class ItensController:
    def __init__(self):
        self.view = None
        self._sincronizando = False

    def obter_grupos_unicos(self):
        itens = db.obter_itens_erp()
        grupos = set()
        for i in itens:
            grupo = str(i.get('descGrupoImp', '')).strip()
            if grupo: grupos.add(grupo)
        return ["Todos"] + sorted(list(grupos))

    def buscar_grupo_por_nome(self, texto):
        return db.buscar_grupos_itens_por_nome(texto)

    def obter_itens_filtrados(self, cod="", grupo="Todos", descricao="", limite=100):
        itens = db.obter_itens_erp()
        filtrados = []
        cod = cod.lower().strip()
        descricao = descricao.lower().strip()
        
        for i in itens:
            val_cod = str(i.get('codItemD', '')).lower()
            val_grupo = str(i.get('descGrupoImp', '')).strip()
            val_desc = str(i.get('descricao', '')).lower()
            
            if cod and cod not in val_cod: continue
            if grupo != "Todos" and grupo.lower() != val_grupo.lower(): continue
            if descricao and descricao not in val_desc: continue
            filtrados.append(i)

        if limite in (None, "", "Todos"):
            return filtrados
        try:
            return filtrados[:max(1, int(limite))]
        except Exception:
            return filtrados

    def sincronizar_itens_erp(self, ao_finalizar=None):
        if self._sincronizando:
            return False

        def rodar():
            self._sincronizando = True
            try:
                modulo_frota.baixar_e_importar_itens()
            finally:
                self._sincronizando = False
                if self.view and ao_finalizar:
                    try:
                        self.view.after(0, ao_finalizar)
                    except Exception:
                        pass

        threading.Thread(target=rodar, daemon=True).start()
        return True

    # ==========================================
    # LÓGICA DE MIGRAÇÃO COM O ROBÔ
    # ==========================================
    def iniciar_migracao_lote(self, itens_codigos, novo_grupo_nome, popup_atualizar_status, grupo_atual="Filtrado", on_finalizado=None):
        config = db.carregar_configuracoes()
        if not config or not config.get('link'):
            popup_atualizar_status("❌ Configure o acesso ao ERP primeiro.")
            return

        def rodar():
            try:
                modulo_migracao.iniciar_migracao_lote(
                    config, itens_codigos, novo_grupo_nome, popup_atualizar_status, grupo_atual,
                )
                if self.view:
                    try:
                        self.view.after(0, self.view.atualizar_tabela)
                    except Exception:
                        pass
            finally:
                if on_finalizado:
                    try:
                        on_finalizado()
                    except Exception:
                        pass

        threading.Thread(target=rodar, daemon=True).start()