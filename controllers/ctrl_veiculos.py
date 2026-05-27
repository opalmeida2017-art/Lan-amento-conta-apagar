import sqlite3

class VeiculosController:
    def __init__(self):
        self.view = None

    def obter_veiculos_banco(self, limite=100):
        try:
            conn = sqlite3.connect('sistema_automacao.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            sql = "SELECT codVeiculo, placa, veiculoProprio, ultima_atualizacao FROM frota_erp ORDER BY codVeiculo ASC"
            if limite not in (None, "", "Todos"):
                try:
                    sql += f" LIMIT {max(1, int(limite))}"
                except Exception:
                    pass
            cursor.execute(sql)
            veiculos = cursor.fetchall()
            conn.close()
            return veiculos
        except Exception as e:
            print(f"Aguardando primeira leitura de frota... ({e})")
            return []