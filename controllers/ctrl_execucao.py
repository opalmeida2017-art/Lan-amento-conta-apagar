import database_setup as db

class ExecucaoController:
    def __init__(self, app_controller):
        self.app_controller = app_controller 
        self.view = None

    def obter_fornecedores_unicos(self):
        return db.obter_fornecedores_unicos_notas()

    def buscar_fornecedor_por_nome(self, texto):
        return db.buscar_fornecedores_por_nome(texto)

    def obter_notas_dashboard(
        self,
        dt_ini,
        dt_fim,
        cod,
        status,
        nota,
        limite=100,
        campo_data='insercao',
        fornecedor='Todos',
    ):
        try:
            notas = db.listar_notas_filtradas(
                dt_ini, dt_fim, cod, status, nota,
                fornecedor=fornecedor,
                limite=limite,
                campo_data=campo_data,
            )
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

    def atualizar_painel_placa(self, chave_da_nota, num_nota, placa):
        ok, msg = db.atualizar_painel_placa_km(
            chave_nfe=chave_da_nota,
            num_nota=num_nota,
            placa=placa,
        )
        if not ok and msg:
            raise ValueError(msg)
        return ok

    def atualizar_painel_km(self, chave_da_nota, num_nota, km):
        ok, msg = db.atualizar_painel_placa_km(
            chave_nfe=chave_da_nota,
            num_nota=num_nota,
            km=km,
        )
        if not ok and msg:
            raise ValueError(msg)
        return ok
        
    def iniciar_robo(self):
        self.app_controller.iniciar_robo()

    def iniciar_robo_para_nota(self, nota_alvo, compra_estoque=False):
        self.app_controller.iniciar_robo(
            nota_alvo=nota_alvo, compra_estoque=compra_estoque,
        )

    def iniciar_robo_lote(self, notas):
        self.app_controller.iniciar_robo_lote(notas)