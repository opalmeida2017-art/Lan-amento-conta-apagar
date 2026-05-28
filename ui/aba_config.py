import customtkinter as ctk
from tkinter import messagebox
import app_version

from agendamento_email import (
    calcular_proxima_execucao,
    descricao_agendamento,
    formatar_data_hora,
    normalizar_tipo_agendamento,
    _normalizar_smtp_host_porta,
    parse_data_hora,
    resumo_proximo_envio,
)


class AbaConfig(ctk.CTkFrame):
    def __init__(self, master, controller, modo_registro_licenca=False):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.modo_registro_licenca = bool(modo_registro_licenca)
        self._carregando_dados = False
        self._agendamento_tipo = ""
        self.montar_tela()
        self.carregar_dados_iniciais()

    def montar_tela(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.frame_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self.frame_scroll.grid_columnconfigure(0, weight=1)

        scroll = self.frame_scroll

        self.frame_versao = ctk.CTkFrame(scroll, fg_color="#1f538d")
        self.frame_versao.pack(pady=(4, 10), padx=12, fill="x")
        self.lbl_versao = ctk.CTkLabel(
            self.frame_versao,
            text=f"VERSÃO ATUAL: {app_version.versao_exibicao()}",
            font=("Arial", 18, "bold"),
            text_color="white",
        )
        self.lbl_versao.pack(pady=10)

        self.frame_erp = ctk.CTkFrame(scroll)
        self.frame_erp.pack(pady=10, padx=12, fill="x")
        frame_erp = self.frame_erp
        for coluna in range(3):
            frame_erp.grid_columnconfigure(coluna, weight=1)

        ctk.CTkLabel(
            frame_erp, text="Dados do Sistema ERP (Web)", font=("Arial", 16, "bold"),
        ).grid(row=0, column=0, columnspan=3, pady=10)
        self.conf_link = ctk.CTkEntry(
            frame_erp, placeholder_text="Link do Sistema", width=350,
        )
        self.conf_link.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.conf_user_erp = ctk.CTkEntry(frame_erp, placeholder_text="Usuário", width=170)
        self.conf_user_erp.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.conf_senha_erp = ctk.CTkEntry(frame_erp, placeholder_text="Senha", show="*", width=170)
        self.conf_senha_erp.grid(row=1, column=2, padx=10, pady=10, sticky="ew")
        self._mostrar_senha_erp = False
        self.btn_toggle_senha_erp = ctk.CTkButton(
            frame_erp,
            text="👁",
            width=26,
            height=24,
            command=self._toggle_senha_erp,
            fg_color="transparent",
            hover_color="#3a3a3a",
            text_color="#cfcfcf",
        )
        self.btn_toggle_senha_erp.place(in_=self.conf_senha_erp, relx=1.0, rely=0.5, x=-8, anchor="e")
        ctk.CTkLabel(
            frame_erp,
            text="Link: URL da tela de login do ERP. Ex: https://empresa.com/login",
            text_color="gray",
            anchor="w",
            justify="left",
        ).grid(row=2, column=0, padx=10, pady=(0, 8), sticky="ew")
        ctk.CTkLabel(
            frame_erp,
            text="Usuário: login usado para entrar no ERP",
            text_color="gray",
            anchor="w",
            justify="left",
        ).grid(row=2, column=1, padx=10, pady=(0, 8), sticky="ew")
        ctk.CTkLabel(
            frame_erp,
            text="Senha: senha do mesmo usuário do ERP",
            text_color="gray",
            anchor="w",
            justify="left",
        ).grid(row=2, column=2, padx=10, pady=(0, 8), sticky="ew")

        self.frame_email = ctk.CTkFrame(scroll)
        self.frame_email.pack(pady=10, padx=12, fill="x")
        frame_email = self.frame_email
        for coluna in range(3):
            frame_email.grid_columnconfigure(coluna, weight=1)

        ctk.CTkLabel(
            frame_email, text="Disparo de E-mail", font=("Arial", 16, "bold"),
        ).grid(row=0, column=0, columnspan=3, pady=10)
        self.conf_smtp = ctk.CTkEntry(
            frame_email, placeholder_text="SMTP", width=250,
        )
        self.conf_smtp.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.conf_porta = ctk.CTkEntry(frame_email, placeholder_text="Porta", width=100)
        self.conf_porta.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.conf_ssl = ctk.CTkCheckBox(
            frame_email, text="Usar SSL/TLS", command=self._atualizar_dica_ssl,
        )
        self.conf_ssl.grid(row=1, column=2, padx=10, pady=10, sticky="w")
        self.conf_user_email = ctk.CTkEntry(frame_email, placeholder_text="E-mail", width=250)
        self.conf_user_email.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.conf_senha_email = ctk.CTkEntry(
            frame_email, placeholder_text="Senha E-mail", show="*", width=250,
        )
        self.conf_senha_email.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self._mostrar_senha_email = False
        self.btn_toggle_senha_email = ctk.CTkButton(
            frame_email,
            text="👁",
            width=26,
            height=24,
            command=self._toggle_senha_email,
            fg_color="transparent",
            hover_color="#3a3a3a",
            text_color="#cfcfcf",
        )
        self.btn_toggle_senha_email.place(in_=self.conf_senha_email, relx=1.0, rely=0.5, x=-8, anchor="e")
        self.conf_destinatarios = ctk.CTkEntry(
            frame_email,
            placeholder_text="Destinos separados por ,",
            width=250,
        )
        self.conf_destinatarios.grid(
            row=3, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew",
        )
        ctk.CTkLabel(
            frame_email,
            text="SMTP: servidor do provedor. Ex: smtp.gmail.com ou smtp.office365.com",
            text_color="gray",
            anchor="w",
            justify="left",
        ).grid(row=4, column=0, padx=10, pady=(0, 6), sticky="ew")
        ctk.CTkLabel(
            frame_email,
            text="Porta: 465 (SSL/TLS) ou 587 (STARTTLS)",
            text_color="gray",
            anchor="w",
            justify="left",
        ).grid(row=4, column=1, padx=10, pady=(0, 6), sticky="ew")
        self.lbl_info_ssl = ctk.CTkLabel(
            frame_email,
            text="SSL/TLS: marque quando o provedor exigir conexão segura",
            text_color="#3b8ed0",
            anchor="w",
            justify="left",
        )
        self.lbl_info_ssl.grid(row=4, column=2, padx=10, pady=(0, 6), sticky="ew")
        ctk.CTkLabel(
            frame_email,
            text="E-mail: conta remetente usada para enviar os relatórios",
            text_color="gray",
            anchor="w",
            justify="left",
        ).grid(row=5, column=0, padx=10, pady=(0, 6), sticky="ew")
        ctk.CTkLabel(
            frame_email,
            text="Senha E-mail: senha da conta ou senha de aplicativo",
            text_color="gray",
            anchor="w",
            justify="left",
        ).grid(row=5, column=1, columnspan=2, padx=10, pady=(0, 6), sticky="ew")
        ctk.CTkLabel(
            frame_email,
            text="Destinos: separe vários e-mails por vírgula. Ex: a@x.com, b@x.com",
            text_color="gray",
            anchor="w",
            justify="left",
        ).grid(row=6, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")

        self.frame_agendamento = ctk.CTkFrame(scroll)
        self.frame_agendamento.pack(pady=(0, 10), padx=12, fill="x")
        frame_agendamento = self.frame_agendamento
        for coluna in range(4):
            frame_agendamento.grid_columnconfigure(coluna, weight=1)

        ctk.CTkLabel(
            frame_agendamento,
            text="Agendamento Automático dos Relatórios",
            font=("Arial", 16, "bold"),
        ).grid(row=0, column=0, columnspan=4, pady=(10, 6))
        ctk.CTkLabel(
            frame_agendamento,
            text="Selecione uma frequência para enviar por e-mail os relatórios de notas e itens.",
            text_color="gray",
        ).grid(row=1, column=0, columnspan=4, padx=12, pady=(0, 8), sticky="w")

        self.ck_agenda_hora = ctk.CTkCheckBox(
            frame_agendamento,
            text="Por hora",
            command=lambda: self._alternar_agendamento("hora"),
        )
        self.ck_agenda_hora.grid(row=2, column=0, padx=(12, 6), pady=8, sticky="w")

        self.conf_intervalo_horas = ctk.CTkEntry(frame_agendamento, width=90)
        self.conf_intervalo_horas.insert(0, "1")
        self.conf_intervalo_horas.grid(row=2, column=1, padx=(0, 6), pady=8, sticky="w")
        self.conf_intervalo_horas.bind("<FocusOut>", lambda _event: self._ao_intervalo_alterado())
        self.conf_intervalo_horas.bind("<Return>", lambda _event: self._ao_intervalo_alterado())

        self.lbl_intervalo_horas = ctk.CTkLabel(
            frame_agendamento, text="hora(s) entre cada envio",
        )
        self.lbl_intervalo_horas.grid(row=2, column=2, columnspan=2, padx=(0, 10), pady=8, sticky="w")

        self.ck_agenda_diario = ctk.CTkCheckBox(
            frame_agendamento,
            text="Diário às 23:59",
            command=lambda: self._alternar_agendamento("diario"),
        )
        self.ck_agenda_diario.grid(row=3, column=0, padx=12, pady=8, sticky="w")

        self.ck_agenda_semanal = ctk.CTkCheckBox(
            frame_agendamento,
            text="Semanal: segunda 00:00",
            command=lambda: self._alternar_agendamento("semanal"),
        )
        self.ck_agenda_semanal.grid(row=3, column=1, padx=12, pady=8, sticky="w")

        self.ck_agenda_mensal = ctk.CTkCheckBox(
            frame_agendamento,
            text="Mensal: último dia do mês 23:59",
            command=lambda: self._alternar_agendamento("mensal"),
        )
        self.ck_agenda_mensal.grid(row=3, column=2, columnspan=2, padx=12, pady=8, sticky="w")

        self.lbl_resumo_agendamento = ctk.CTkLabel(
            frame_agendamento,
            text="Envio automático desativado.",
            text_color="#3b8ed0",
            justify="left",
        )
        self.lbl_resumo_agendamento.grid(
            row=4, column=0, columnspan=4, padx=12, pady=(4, 12), sticky="w",
        )

        self.frame_lic = ctk.CTkFrame(scroll, fg_color="transparent")
        self.frame_lic.pack(pady=(5, 12), padx=12, fill="x")
        frame_lic = self.frame_lic

        linha1 = ctk.CTkFrame(frame_lic, fg_color="transparent")
        linha1.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            linha1, text="Razão social (transportadora):", font=("Arial", 12, "bold"),
        ).pack(side="left", padx=(0, 10))
        self.entry_razao_social = ctk.CTkEntry(
            linha1, width=420, placeholder_text="Ex: Transportes Silva Ltda",
        )
        self.entry_razao_social.pack(side="left", fill="x", expand=True)

        linha2 = ctk.CTkFrame(frame_lic, fg_color="transparent")
        linha2.pack(fill="x")
        ctk.CTkLabel(
            linha2, text="ID desta instalação:", font=("Arial", 12, "bold"),
        ).pack(side="left", padx=(0, 10))
        self.lbl_instalacao_id = ctk.CTkLabel(
            linha2, text="— gerado ao salvar —",
            font=("Consolas", 11), text_color="#3b8ed0",
        )
        self.lbl_instalacao_id.pack(side="left", anchor="w")

        self.frame_acoes = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_acoes.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 4))
        frame_acoes = self.frame_acoes

        texto_salvar = (
            "💾 Salvar transportadora e gerar ID"
            if self.modo_registro_licenca
            else "💾 Salvar Configurações"
        )
        self.btn_salvar = ctk.CTkButton(
            frame_acoes, text=texto_salvar, command=self._click_salvar, fg_color="green",
        )
        self.btn_salvar.pack(side="left", padx=(0, 10))

        self.btn_enviar_relatorio_email = ctk.CTkButton(
            frame_acoes,
            text="📧 Enviar Relatório para E-mail",
            command=self._click_enviar_relatorio_email,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
        )
        self.btn_enviar_relatorio_email.pack(side="left", padx=(0, 10))

        self.btn_atualizar_sistema = ctk.CTkButton(
            frame_acoes,
            text="🔄 Atualizar Sistema",
            command=self._click_atualizar_sistema,
            fg_color="#1f538d",
            hover_color="#163d68",
        )
        self.btn_atualizar_sistema.pack(side="left")

        self.lbl_status_atualizacao = ctk.CTkLabel(
            self,
            text="Status atualização: aguardando comando.",
            text_color="gray",
            justify="left",
        )
        self.lbl_status_atualizacao.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.lbl_status_teste_email = ctk.CTkLabel(
            self,
            text="Status e-mail: aguardando comando.",
            text_color="gray",
            justify="left",
        )
        self.lbl_status_teste_email.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        self._atualizar_dica_ssl()

        if self.modo_registro_licenca:
            self.frame_erp.pack_forget()
            self.frame_email.pack_forget()
            self.frame_agendamento.pack_forget()
            self.btn_enviar_relatorio_email.pack_forget()
            self.btn_atualizar_sistema.pack_forget()
            self.lbl_status_atualizacao.grid_remove()
            self.lbl_status_teste_email.grid_remove()
            self.frame_lic.pack_forget()
            self.frame_lic.pack(pady=16, padx=12, fill="x")

    def _checkboxes_agendamento(self):
        return {
            "hora": self.ck_agenda_hora,
            "diario": self.ck_agenda_diario,
            "semanal": self.ck_agenda_semanal,
            "mensal": self.ck_agenda_mensal,
        }

    def _atualizar_dica_ssl(self):
        if self.conf_ssl.get():
            self.lbl_info_ssl.configure(
                text="SSL/TLS marcado: recomendado usar porta 465 (SSL implícito).",
            )
            return
        self.lbl_info_ssl.configure(
            text="SSL/TLS desmarcado: recomendado usar porta 587 (STARTTLS).",
        )

    def _toggle_senha_erp(self):
        self._mostrar_senha_erp = not self._mostrar_senha_erp
        self.conf_senha_erp.configure(show="" if self._mostrar_senha_erp else "*")
        self.btn_toggle_senha_erp.configure(text="🙈" if self._mostrar_senha_erp else "👁")

    def _toggle_senha_email(self):
        self._mostrar_senha_email = not self._mostrar_senha_email
        self.conf_senha_email.configure(show="" if self._mostrar_senha_email else "*")
        self.btn_toggle_senha_email.configure(text="🙈" if self._mostrar_senha_email else "👁")

    def _obter_intervalo_horas(self):
        texto = self.conf_intervalo_horas.get().strip() or "1"
        try:
            valor = int(texto)
        except ValueError:
            raise ValueError("Informe um número inteiro válido no campo de horas.")
        if valor < 1:
            raise ValueError("O intervalo em horas deve ser maior ou igual a 1.")
        return valor

    def _atualizar_resumo_agendamento(self, proxima_execucao=None):
        if not self._agendamento_tipo:
            self.lbl_resumo_agendamento.configure(text="Envio automático desativado.")
            return

        intervalo = self._obter_intervalo_horas() if self._agendamento_tipo == "hora" else 1
        proxima = parse_data_hora(proxima_execucao) if proxima_execucao else None
        if not proxima:
            proxima = calcular_proxima_execucao(self._agendamento_tipo, intervalo)
        if not proxima:
            self.lbl_resumo_agendamento.configure(
                text="Envio automático desativado. Salve novamente para recalcular o próximo envio.",
            )
            return
        texto = (
            f"{descricao_agendamento(self._agendamento_tipo, intervalo)}\n"
            f"Próximo envio: {proxima.strftime('%d/%m/%Y %H:%M')}"
        )
        self.lbl_resumo_agendamento.configure(text=texto)

    def _alternar_agendamento(self, tipo):
        checkbox = self._checkboxes_agendamento()[tipo]
        marcado = bool(checkbox.get())

        for outro_tipo, outro_checkbox in self._checkboxes_agendamento().items():
            if outro_tipo != tipo:
                outro_checkbox.deselect()

        self._agendamento_tipo = tipo if marcado else ""

        if marcado and tipo == "hora":
            try:
                self._obter_intervalo_horas()
            except ValueError as exc:
                checkbox.deselect()
                self._agendamento_tipo = ""
                self.lbl_resumo_agendamento.configure(text="Envio automático desativado.")
                messagebox.showwarning("Agendamento", str(exc))
                return

        self._atualizar_resumo_agendamento()

        if marcado and not self._carregando_dados:
            intervalo = self._obter_intervalo_horas() if tipo == "hora" else 1
            messagebox.showinfo("Agendamento", resumo_proximo_envio(tipo, intervalo))

    def _ao_intervalo_alterado(self):
        if self._agendamento_tipo != "hora":
            return
        try:
            intervalo = self._obter_intervalo_horas()
        except ValueError as exc:
            messagebox.showwarning("Agendamento", str(exc))
            return
        self._atualizar_resumo_agendamento()
        if not self._carregando_dados:
            messagebox.showinfo("Agendamento", resumo_proximo_envio("hora", intervalo))

    def _selecionar_agendamento_salvo(self, tipo, intervalo, proxima_execucao):
        self._agendamento_tipo = normalizar_tipo_agendamento(tipo)
        for chave, checkbox in self._checkboxes_agendamento().items():
            if chave == self._agendamento_tipo:
                checkbox.select()
            else:
                checkbox.deselect()

        self.conf_intervalo_horas.delete(0, "end")
        self.conf_intervalo_horas.insert(0, str(intervalo or 1))
        self._atualizar_resumo_agendamento(proxima_execucao=proxima_execucao)

    def _click_salvar(self):
        razao = self.entry_razao_social.get().strip()
        if self.modo_registro_licenca:
            self.controller.salvar_registro_transportadora(razao)
            return

        campos_erp = [
            self.conf_link.get().strip(),
            self.conf_user_erp.get().strip(),
            self.conf_senha_erp.get().strip(),
        ]
        campos_email = [
            self.conf_smtp.get().strip(),
            self.conf_porta.get().strip(),
            self.conf_user_email.get().strip(),
            self.conf_senha_email.get().strip(),
        ]

        smtp_digitado = campos_email[0]
        smtp_normalizado, porta_smtp_normalizada = _normalizar_smtp_host_porta(
            smtp_digitado,
            campos_email[1],
        )
        if not smtp_normalizado:
            messagebox.showwarning(
                "SMTP inválido",
                "Informe o servidor SMTP sem http/https.\n"
                "Exemplo: smtp.gmail.com",
            )
            return
        if smtp_normalizado != smtp_digitado:
            self.conf_smtp.delete(0, "end")
            self.conf_smtp.insert(0, smtp_normalizado)
            campos_email[0] = smtp_normalizado
        if porta_smtp_normalizada and porta_smtp_normalizada != campos_email[1]:
            self.conf_porta.delete(0, "end")
            self.conf_porta.insert(0, porta_smtp_normalizada)
            campos_email[1] = porta_smtp_normalizada

        try:
            intervalo = self._obter_intervalo_horas() if self._agendamento_tipo == "hora" else 1
        except ValueError as exc:
            messagebox.showwarning("Agendamento", str(exc))
            return

        proxima = calcular_proxima_execucao(self._agendamento_tipo, intervalo)
        params = (
            campos_erp[0],
            campos_erp[1],
            campos_erp[2],
            campos_email[0],
            campos_email[2],
            campos_email[3],
            1 if self.conf_ssl.get() else 0,
            campos_email[1],
            self._agendamento_tipo,
            intervalo,
            formatar_data_hora(proxima),
            "",
            self.conf_destinatarios.get().strip(),
        )
        self.controller.salvar_configuracoes(campos_erp, campos_email, params, razao)
        self._atualizar_resumo_agendamento(proxima_execucao=formatar_data_hora(proxima))

    def _click_atualizar_sistema(self):
        self.controller.atualizar_sistema()

    def _click_enviar_relatorio_email(self):
        smtp_digitado = self.conf_smtp.get().strip()
        porta_digitada = self.conf_porta.get().strip()
        smtp_normalizado, porta_smtp_normalizada = _normalizar_smtp_host_porta(
            smtp_digitado,
            porta_digitada,
        )
        if not smtp_normalizado:
            messagebox.showwarning(
                "SMTP inválido",
                "Informe o servidor SMTP sem http/https.\n"
                "Exemplo: smtp.gmail.com",
            )
            return
        if smtp_normalizado != smtp_digitado:
            self.conf_smtp.delete(0, "end")
            self.conf_smtp.insert(0, smtp_normalizado)
        if porta_smtp_normalizada and porta_smtp_normalizada != porta_digitada:
            self.conf_porta.delete(0, "end")
            self.conf_porta.insert(0, porta_smtp_normalizada)

        cfg = {
            "smtp": self.conf_smtp.get().strip(),
            "porta": self.conf_porta.get().strip(),
            "user_email": self.conf_user_email.get().strip(),
            "senha_email": self.conf_senha_email.get().strip(),
            "ssl": 1 if self.conf_ssl.get() else 0,
            "destinatarios": self.conf_destinatarios.get().strip(),
        }
        self.controller.testar_envio_email(cfg)

    def atualizar_status_atualizacao(self, texto):
        self.lbl_status_atualizacao.configure(text=f"Status atualização: {texto}")

    def definir_estado_atualizacao(self, em_andamento):
        estado = "disabled" if em_andamento else "normal"
        if hasattr(self, "btn_atualizar_sistema"):
            self.btn_atualizar_sistema.configure(state=estado)

    def atualizar_status_teste_email(self, texto):
        self.lbl_status_teste_email.configure(text=f"Status e-mail: {texto}")

    def definir_estado_teste_email(self, em_andamento):
        estado = "disabled" if em_andamento else "normal"
        if hasattr(self, "btn_enviar_relatorio_email"):
            self.btn_enviar_relatorio_email.configure(state=estado)

    def carregar_dados_iniciais(self):
        self._carregando_dados = True
        inst = self.controller.carregar_instalacao_licenca()
        if inst.get('razao_social'):
            self.entry_razao_social.insert(0, inst['razao_social'])
        import database_setup as db

        iid = (
            inst.get('instalacao_id')
            or self.controller.obter_id_instalacao()
            or db.obter_ou_criar_instalacao_id()
        )
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
            self.conf_destinatarios.insert(0, dados.get("destinatarios") or "")
            if dados["ssl"] == 1:
                self.conf_ssl.select()
            self._selecionar_agendamento_salvo(
                dados.get("agendamento_tipo"),
                dados.get("intervalo_horas") or 1,
                dados.get("proxima_execucao"),
            )
        else:
            self._atualizar_resumo_agendamento()
        self._carregando_dados = False

