import database_setup as db
from tkinter import messagebox

class FiltrosController:
    def __init__(self):
        self.view = None

    def carregar_codigos_relatorios(self):
        try:
            return db.carregar_codigos_relatorios()
        except:
            return {}

    def salvar_tudo(self, rel_veiculo, rel_item, comando_salvar_filtros):
        # 1. Salva EXCLUSIVAMENTE os Códigos na Tabela Blindada
        db.salvar_codigos_relatorios(rel_veiculo, rel_item)
        
        # 2. Executa a função de salvar do painel original (Mês, Ano, Combustíveis)
        if comando_salvar_filtros:
            try: 
                comando_salvar_filtros()
            except Exception as e:
                print(f"Erro ao salvar filtros do painel: {e}")
                
        messagebox.showinfo("Sucesso", "✅ Todas as configurações (Datas, Combustíveis e Relatórios) foram salvas!")