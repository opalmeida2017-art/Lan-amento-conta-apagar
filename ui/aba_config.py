import customtkinter as ctk

class AbaConfig(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self # Passa a referência da tela para o controlador
        self.montar_tela()
        self.carregar_dados_iniciais()

    def montar_tela(self):
        # Frame ERP
        frame_erp = ctk.CTkFrame(self)
        frame_erp.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_erp, text="Dados do Sistema ERP (Web)", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        self.conf_link = ctk.CTkEntry(frame_erp, placeholder_text="Link do Sistema", width=350)
        self.conf_link.grid(row=1, column=0, padx=10, pady=10)
        self.conf_user_erp = ctk.CTkEntry(frame_erp, placeholder_text="Usuário", width=170)
        self.conf_user_erp.grid(row=1, column=1, padx=10, pady=10)
        self.conf_senha_erp = ctk.CTkEntry(frame_erp, placeholder_text="Senha", show="*", width=170)
        self.conf_senha_erp.grid(row=1, column=2, padx=10, pady=10)

        # Frame Email
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

        # Botão Salvar envia os dados para o Controlador
        btn_salvar = ctk.CTkButton(self, text="Salvar Configurações", command=self._click_salvar, fg_color="green")
        btn_salvar.pack(pady=20)

    def _click_salvar(self):
        campos_erp = [self.conf_link.get().strip(), self.conf_user_erp.get().strip(), self.conf_senha_erp.get().strip()]
        campos_email = [self.conf_smtp.get().strip(), self.conf_porta.get().strip(), self.conf_user_email.get().strip(), self.conf_senha_email.get().strip()]
        params = (campos_erp[0], campos_erp[1], campos_erp[2], campos_email[0], campos_email[2], campos_email[3], 1 if self.conf_ssl.get() else 0, campos_email[1])
        
        # Chama a inteligência do Controlador
        self.controller.salvar_configuracoes(campos_erp, campos_email, params)

    def carregar_dados_iniciais(self):
        dados = self.controller.carregar_dados()
        if dados:
            self.conf_link.insert(0, dados["link"])
            self.conf_user_erp.insert(0, dados["user_sis"])
            self.conf_senha_erp.insert(0, dados["senha_sis"])
            self.conf_smtp.insert(0, dados["smtp"])
            self.conf_porta.insert(0, str(dados["porta"]))
            self.conf_user_email.insert(0, dados["user_email"])
            self.conf_senha_email.insert(0, dados["senha_email"])
            if dados["ssl"] == 1: self.conf_ssl.select()