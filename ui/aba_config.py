import customtkinter as ctk

class AbaConfig(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.montar_tela()
        self.carregar_dados_iniciais()

    def montar_tela(self):
        frame_erp = ctk.CTkFrame(self)
        frame_erp.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_erp, text="Dados do Sistema ERP (Web)", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        self.conf_link = ctk.CTkEntry(frame_erp, placeholder_text="Link do Sistema", width=350)
        self.conf_link.grid(row=1, column=0, padx=10, pady=10)
        self.conf_user_erp = ctk.CTkEntry(frame_erp, placeholder_text="Usuário", width=170)
        self.conf_user_erp.grid(row=1, column=1, padx=10, pady=10)
        self.conf_senha_erp = ctk.CTkEntry(frame_erp, placeholder_text="Senha", show="*", width=170)
        self.conf_senha_erp.grid(row=1, column=2, padx=10, pady=10)

        frame_email = ctk.CTkFrame(self)
        frame_email.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_email, text="Disparo de E-mail", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=4, pady=10)
        self.conf_smtp = ctk.CTkEntry(frame_email, placeholder_text="SMTP", width=250)
        self.conf_smtp.grid(row=1, column=0, padx=10, pady=10)
        self.conf_porta = ctk.CTkEntry(frame_email, placeholder_text="Porta", width=100)
        self.conf_porta.grid(row=1, column=1, padx=10, pady=10)
        self.conf_ssl = ctk.CTkCheckBox(frame_email, text="Usar SSL/TLS")
        self.conf_ssl.grid(row=1, column=2, padx=10, pady=10)
        self.conf_user_email = ctk.CTkEntry(frame_email, placeholder_text="E-mail", width=250)
        self.conf_user_email.grid(row=2, column=0, padx=10, pady=10)
        self.conf_senha_email = ctk.CTkEntry(frame_email, placeholder_text="Senha E-mail", show="*", width=250)
        self.conf_senha_email.grid(row=2, column=1, columnspan=2, padx=10, pady=10)

        frame_lic = ctk.CTkFrame(self, fg_color="transparent")
        frame_lic.pack(pady=(5, 0), padx=20, fill="x")

        linha1 = ctk.CTkFrame(frame_lic, fg_color="transparent")
        linha1.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(linha1, text="Razão social (transportadora):", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 10))
        self.entry_razao_social = ctk.CTkEntry(linha1, width=420, placeholder_text="Ex: Transportes Silva Ltda")
        self.entry_razao_social.pack(side="left", fill="x", expand=True)

        linha2 = ctk.CTkFrame(frame_lic, fg_color="transparent")
        linha2.pack(fill="x")
        ctk.CTkLabel(linha2, text="ID desta instalação:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 10))
        self.lbl_instalacao_id = ctk.CTkLabel(
            linha2, text="— gerado ao salvar —",
            font=("Consolas", 11), text_color="#3b8ed0",
        )
        self.lbl_instalacao_id.pack(side="left", anchor="w")

        btn_salvar = ctk.CTkButton(self, text="Salvar Configurações", command=self._click_salvar, fg_color="green")
        btn_salvar.pack(pady=20)

    def _click_salvar(self):
        razao = self.entry_razao_social.get().strip()
        campos_erp = [self.conf_link.get().strip(), self.conf_user_erp.get().strip(), self.conf_senha_erp.get().strip()]
        campos_email = [self.conf_smtp.get().strip(), self.conf_porta.get().strip(), self.conf_user_email.get().strip(), self.conf_senha_email.get().strip()]
        params = (campos_erp[0], campos_erp[1], campos_erp[2], campos_email[0], campos_email[2], campos_email[3], 1 if self.conf_ssl.get() else 0, campos_email[1])
        self.controller.salvar_configuracoes(campos_erp, campos_email, params, razao)

    def carregar_dados_iniciais(self):
        inst = self.controller.carregar_instalacao_licenca()
        if inst.get('razao_social'):
            self.entry_razao_social.insert(0, inst['razao_social'])
        iid = inst.get('instalacao_id') or self.controller.obter_id_instalacao()
        if iid:
            self.lbl_instalacao_id.configure(text=iid)
        dados = self.controller.carregar_dados()
        if dados:
            self.conf_link.insert(0, dados["link"])
            self.conf_user_erp.insert(0, dados["user_sis"])
            self.conf_senha_erp.insert(0, dados["senha_sis"])
            self.conf_smtp.insert(0, dados["smtp"])
            self.conf_porta.insert(0, str(dados["porta"]))
            self.conf_user_email.insert(0, dados["user_email"])
            self.conf_senha_email.insert(0, dados["senha_email"])
            if dados["ssl"] == 1:
                self.conf_ssl.select()
