import database_setup as db

class ExecucaoController:
    def __init__(self, app_controller):
        self.app_controller = app_controller 
        self.view = None

    def obter_notas_dashboard(self, dt_ini, dt_fim, cod, status, nota):
        try:
            notas = db.listar_notas_filtradas(dt_ini, dt_fim, cod, status, nota)
            # Garante que sempre retorne uma lista, mesmo que vazia
            return notas if notas is not None else []
        except Exception as e:
            print(f"[ERRO BANCO DE DADOS] Falha ao buscar notas no SQLite: {e}")
            return []

    def atualizar_estoque(self, chave_da_nota, estado_banco):
        try:
            db.atualizar_estoque_nota(chave_da_nota, estado_banco)
        except Exception as e:
            print(f"[ERRO BANCO DE DADOS] Falha ao atualizar estoque: {e}")

    def atualizar_arquiva(self, chave_da_nota, estado_banco):
        try:
            db.atualizar_arquiva_nota(chave_da_nota, estado_banco)
        except Exception as e:
            print(f"[ERRO BANCO DE DADOS] Falha ao atualizar arquiva: {e}")
        
    def iniciar_robo(self):
        self.app_controller.iniciar_robo()