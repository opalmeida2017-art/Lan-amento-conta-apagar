import database_setup as db
import licenca_remota
from tkinter import messagebox

class ConfigController:
    def __init__(self):
        self.view = None

    def carregar_dados(self):
        return db.carregar_configuracoes()

    def obter_id_instalacao(self):
        return db.obter_instalacao_id() or ''

    def carregar_instalacao_licenca(self):
        return db.carregar_instalacao_licenca()

    def salvar_configuracoes(self, campos_erp, campos_email, params, razao_social=''):
        if not razao_social.strip():
            messagebox.showwarning("Aviso", "Informe a razão social da transportadora.")
            return
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
            texto = msg
            ok_lic, msg_lic, iid = licenca_remota.registrar_instalacao(razao_social)
            texto += f"\n\nID desta instalação:\n{iid or '—'}"
            if ok_lic:
                texto += f"\n\n{msg_lic}"
            else:
                messagebox.showwarning("Licença remota", msg_lic)
            if self.view and hasattr(self.view, 'lbl_instalacao_id') and iid:
                self.view.lbl_instalacao_id.configure(text=iid)
            messagebox.showinfo("Sucesso", texto)
