import database_setup as db
from tkinter import messagebox

class ConfigController:
    def __init__(self):
        self.view = None # Será preenchido pela tela depois

    def carregar_dados(self):
        return db.carregar_configuracoes()

    def salvar_configuracoes(self, campos_erp, campos_email, params):
        if not any(campos_erp) and not any(campos_email):
            messagebox.showwarning("Aviso", "Nenhum dado foi preenchido.")
            return
        if any(campos_erp) and not all(campos_erp):
            messagebox.showwarning("Aviso", "Dados do ERP incompletos!")
            return
        if any(campos_email) and not all(campos_email):
            messagebox.showwarning("Aviso", "Dados de E-mail incompletos!")
            return

        sucesso, msg = db.salvar_configuracoes(*params)
        if sucesso:
            messagebox.showinfo("Sucesso", msg)