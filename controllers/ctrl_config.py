import database_setup as db
import licenca_remota
import threading
from tkinter import messagebox
from agendamento_email import resumo_proximo_envio, enviar_relatorios_agendados
import github_updater

class ConfigController:
    def __init__(self, app_controller=None):
        self.view = None
        self.app_controller = app_controller
        self._atualizacao_em_andamento = False
        self._teste_email_em_andamento = False

    def carregar_dados(self):
        return db.carregar_configuracoes()

    def obter_id_instalacao(self):
        return db.obter_instalacao_id() or ''

    def carregar_instalacao_licenca(self):
        return db.carregar_instalacao_licenca()

    def salvar_configuracoes(self, campos_erp, campos_email, params, razao_social=''):
        tipo_agendamento = str(params[8] or '').strip().lower() if len(params) > 8 else ''
        intervalo_horas = params[9] if len(params) > 9 else 1

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
        if tipo_agendamento and not all(campos_email):
            messagebox.showwarning(
                "Aviso",
                "Preencha SMTP, porta, e-mail e senha para ativar o envio automático.",
            )
            return

        sucesso, msg = db.salvar_configuracoes(*params)
        if sucesso:
            texto = msg
            if tipo_agendamento:
                texto += f"\n\n{resumo_proximo_envio(tipo_agendamento, intervalo_horas)}"
            ok_lic, msg_lic, iid = licenca_remota.registrar_instalacao(razao_social)
            texto += f"\n\nID desta instalação:\n{iid or '—'}"
            if ok_lic:
                texto += f"\n\n{msg_lic}"
            else:
                messagebox.showwarning("Licença remota", msg_lic)
            if self.view and hasattr(self.view, 'lbl_instalacao_id') and iid:
                self.view.lbl_instalacao_id.configure(text=iid)
            messagebox.showinfo("Sucesso", texto)

    def atualizar_sistema(self):
        if self._atualizacao_em_andamento:
            messagebox.showwarning("Atualização", "Já existe uma atualização do sistema em andamento.")
            return

        self._atualizacao_em_andamento = True
        if self.view and hasattr(self.view, "definir_estado_atualizacao"):
            self.view.definir_estado_atualizacao(True)
        if self.view and hasattr(self.view, "atualizar_status_atualizacao"):
            self.view.atualizar_status_atualizacao("Baixando nova versão do GitHub...")

        def rodar():
            resultado = None
            erro = None
            try:
                resultado = github_updater.preparar_atualizacao_exe()
            except Exception as exc:
                erro = str(exc)
            finally:
                self._atualizacao_em_andamento = False

                def finalizar():
                    if self.view and hasattr(self.view, "definir_estado_atualizacao"):
                        self.view.definir_estado_atualizacao(False)

                    if erro:
                        if self.view and hasattr(self.view, "atualizar_status_atualizacao"):
                            self.view.atualizar_status_atualizacao(f"Falha na atualização: {erro}")
                        messagebox.showerror("Atualização", f"Erro ao atualizar o sistema:\n{erro}")
                        return

                    if self.view and hasattr(self.view, "atualizar_status_atualizacao"):
                        self.view.atualizar_status_atualizacao(
                            f"Nova versão pronta: {resultado.get('asset_name')}"
                        )

                    messagebox.showinfo(
                        "Atualização",
                        "A nova versão foi baixada com sucesso.\n\n"
                        f"Release: {resultado.get('release_name')}\n"
                        f"Arquivo: {resultado.get('asset_name')}\n\n"
                        "O sistema será fechado para substituir o executável atual.",
                    )

                    if self.app_controller and getattr(self.app_controller, "view", None):
                        try:
                            self.app_controller.view.after(800, self.app_controller.view.destroy)
                        except Exception:
                            try:
                                self.app_controller.view.destroy()
                            except Exception:
                                pass

                if self.view and hasattr(self.view, "after"):
                    self.view.after(0, finalizar)
                else:
                    finalizar()

        threading.Thread(target=rodar, daemon=True).start()

    def testar_envio_email(self, configuracao_email):
        if self._teste_email_em_andamento:
            messagebox.showwarning("Teste de e-mail", "Já existe um teste de e-mail em andamento.")
            return

        cfg = configuracao_email or {}
        smtp = str(cfg.get("smtp") or "").strip()
        porta = str(cfg.get("porta") or "").strip()
        usuario = str(cfg.get("user_email") or "").strip()
        senha = str(cfg.get("senha_email") or "").strip()
        if not smtp or not porta or not usuario or not senha:
            messagebox.showwarning(
                "Teste de e-mail",
                "Preencha SMTP, porta, e-mail e senha antes de testar o envio.",
            )
            return

        self._teste_email_em_andamento = True
        if self.view and hasattr(self.view, "definir_estado_teste_email"):
            self.view.definir_estado_teste_email(True)
        if self.view and hasattr(self.view, "atualizar_status_teste_email"):
            self.view.atualizar_status_teste_email("Enviando relatórios de teste por e-mail...")

        def rodar():
            resultado = None
            erro = None
            try:
                resultado = enviar_relatorios_agendados(cfg)
            except Exception as exc:
                erro = str(exc)
            finally:
                self._teste_email_em_andamento = False

                def finalizar():
                    if self.view and hasattr(self.view, "definir_estado_teste_email"):
                        self.view.definir_estado_teste_email(False)

                    if erro:
                        if self.view and hasattr(self.view, "atualizar_status_teste_email"):
                            self.view.atualizar_status_teste_email(f"Falha no teste de e-mail: {erro}")
                        messagebox.showerror(
                            "Teste de e-mail",
                            f"Falha ao enviar o e-mail de teste:\n{erro}",
                        )
                        return

                    if self.view and hasattr(self.view, "atualizar_status_teste_email"):
                        self.view.atualizar_status_teste_email(
                            "E-mail de teste enviado com sucesso.",
                        )
                    messagebox.showinfo(
                        "Teste de e-mail",
                        "E-mail de teste enviado com sucesso.\n\n"
                        f"Notas no anexo: {resultado.get('total_notas', 0)}\n"
                        f"Itens no anexo: {resultado.get('total_itens', 0)}",
                    )

                if self.view and hasattr(self.view, "after"):
                    self.view.after(0, finalizar)
                else:
                    finalizar()

        threading.Thread(target=rodar, daemon=True).start()

