import customtkinter as ctk
from tkinter import messagebox

import log_service
from ui.relatorio_suporte import enviar_log_suporte_por_email


class AbaLogs(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._listener = self._receber_evento_log
        self._contagem_logs = 0
        self._montar_tela()
        log_service.adicionar_listener(self._listener)
        self.carregar_logs()

    def _montar_tela(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        frame_topo = ctk.CTkFrame(self)
        frame_topo.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
        frame_topo.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(
            frame_topo,
            text="Logs do Robô e Execuções",
            font=("Arial", 18, "bold"),
            text_color="#3b8ed0",
        ).grid(row=0, column=0, columnspan=8, padx=10, pady=(10, 8), sticky="w")

        ctk.CTkLabel(frame_topo, text="Data/Hora Inicial:").grid(
            row=1, column=0, padx=(10, 4), pady=(0, 6), sticky="w",
        )
        self.entry_dt_ini = ctk.CTkEntry(
            frame_topo, width=150, placeholder_text="DD/MM/AAAA HH:MM",
        )
        self.entry_dt_ini.grid(row=1, column=1, padx=4, pady=(0, 6), sticky="w")
        self.entry_dt_ini.bind("<KeyRelease>", self._formatar_data_hora_teclado)

        ctk.CTkLabel(frame_topo, text="Data/Hora Final:").grid(
            row=1, column=2, padx=(10, 4), pady=(0, 6), sticky="w",
        )
        self.entry_dt_fim = ctk.CTkEntry(
            frame_topo, width=150, placeholder_text="DD/MM/AAAA HH:MM",
        )
        self.entry_dt_fim.grid(row=1, column=3, padx=4, pady=(0, 6), sticky="w")
        self.entry_dt_fim.bind("<KeyRelease>", self._formatar_data_hora_teclado)

        ctk.CTkLabel(frame_topo, text="Nº Nota:").grid(
            row=1, column=4, padx=(10, 4), pady=(0, 6), sticky="w",
        )
        self.entry_nota = ctk.CTkEntry(
            frame_topo, width=120, placeholder_text="Ex: 1441",
        )
        self.entry_nota.grid(row=1, column=5, padx=4, pady=(0, 6), sticky="ew")

        ctk.CTkLabel(frame_topo, text="Limite:").grid(
            row=2, column=0, padx=(10, 4), pady=(0, 10), sticky="w",
        )
        self.combo_limite = ctk.CTkComboBox(
            frame_topo, width=100, values=["200", "500", "1000", "2000", "Todos"],
        )
        self.combo_limite.set("1000")
        self.combo_limite.grid(row=2, column=1, padx=4, pady=(0, 10), sticky="w")

        self.btn_atualizar = ctk.CTkButton(
            frame_topo, text="Filtrar", width=90, command=self.carregar_logs,
        )
        self.btn_atualizar.grid(row=2, column=2, padx=(10, 4), pady=(0, 10), sticky="w")

        self.btn_limpar_filtros = ctk.CTkButton(
            frame_topo,
            text="Limpar Filtros",
            width=120,
            fg_color="gray",
            hover_color="#5f5f5f",
            command=self._limpar_filtros,
        )
        self.btn_limpar_filtros.grid(row=2, column=3, padx=4, pady=(0, 10), sticky="w")

        self.btn_limpar = ctk.CTkButton(
            frame_topo,
            text="Limpar Logs",
            width=110,
            fg_color="#c62828",
            hover_color="#b71c1c",
            command=self._limpar_logs,
        )
        self.btn_limpar.grid(row=2, column=4, padx=4, pady=(0, 10), sticky="w")

        self.btn_enviar_suporte = ctk.CTkButton(
            frame_topo,
            text="Enviar log p/ Suporte",
            width=160,
            fg_color="#1565c0",
            hover_color="#0d47a1",
            command=self._abrir_popup_suporte,
        )
        self.btn_enviar_suporte.grid(row=2, column=5, padx=(10, 4), pady=(0, 10), sticky="w")

        self.lbl_status = ctk.CTkLabel(
            frame_topo, text="Status: carregando logs...", text_color="gray",
        )
        self.lbl_status.grid(row=2, column=7, padx=(10, 10), pady=(0, 10), sticky="e")

        self.caixa_logs = ctk.CTkTextbox(
            self,
            wrap="word",
            font=("Consolas", 12),
        )
        self.caixa_logs.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.caixa_logs.configure(state="disabled")

    def _formatar_data_hora_teclado(self, event):
        entry = event.widget
        texto = "".join(c for c in entry.get() if c.isdigit())[:14]
        if event.keysym == "BackSpace":
            return

        partes = []
        if len(texto) >= 2:
            partes.append(texto[:2])
        elif texto:
            partes.append(texto)

        if len(texto) > 2:
            trecho = texto[2:4]
            partes.append(trecho)

        if len(texto) > 4:
            trecho = texto[4:8]
            partes.append(trecho)

        data = "/".join(parte for parte in partes if parte)

        hora = ""
        if len(texto) > 8:
            hora = texto[8:10]
        if len(texto) > 10:
            hora = f"{hora}:{texto[10:12]}"
        if len(texto) > 12:
            hora = f"{hora}:{texto[12:14]}"

        novo_texto = data
        if hora:
            novo_texto = f"{data} {hora}".strip()

        entry.delete(0, "end")
        entry.insert(0, novo_texto)

    def _formatar_data_teclado(self, event):
        entry = event.widget
        if event.keysym == "BackSpace":
            return
        texto = "".join(c for c in entry.get() if c.isdigit())[:8]
        partes = []
        if len(texto) >= 2:
            partes.append(texto[:2])
        elif texto:
            partes.append(texto)
        if len(texto) > 2:
            partes.append(texto[2:4])
        if len(texto) > 4:
            partes.append(texto[4:8])
        entry.delete(0, "end")
        entry.insert(0, "/".join(p for p in partes if p))

    def _abrir_popup_suporte(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Enviar log para suporte")
        popup.geometry("420x260")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        popup.transient(self.winfo_toplevel())
        popup.grab_set()

        popup.update_idletasks()
        x = self.winfo_rootx() + max((self.winfo_width() - 420) // 2, 0)
        y = self.winfo_rooty() + max((self.winfo_height() - 260) // 2, 0)
        popup.geometry(f"420x260+{x}+{y}")

        ctk.CTkLabel(
            popup,
            text="Período do relatório",
            font=("Arial", 16, "bold"),
            text_color="#3b8ed0",
        ).pack(pady=(16, 6))

        ctk.CTkLabel(
            popup,
            text=(
                "Informe as datas de registro no painel.\n"
                "Será enviado um e-mail para o suporte com os relatórios em anexo."
            ),
            justify="center",
            font=("Arial", 11),
        ).pack(pady=(0, 12))

        frame_campos = ctk.CTkFrame(popup, fg_color="transparent")
        frame_campos.pack(pady=4, padx=20, fill="x")

        ctk.CTkLabel(frame_campos, text="Data inicial:").grid(
            row=0, column=0, padx=(0, 8), pady=6, sticky="w",
        )
        entry_ini = ctk.CTkEntry(
            frame_campos, width=180, placeholder_text="DD/MM/AAAA",
        )
        entry_ini.grid(row=0, column=1, pady=6, sticky="w")
        entry_ini.bind("<KeyRelease>", self._formatar_data_teclado)

        ctk.CTkLabel(frame_campos, text="Data final:").grid(
            row=1, column=0, padx=(0, 8), pady=6, sticky="w",
        )
        entry_fim = ctk.CTkEntry(
            frame_campos, width=180, placeholder_text="DD/MM/AAAA",
        )
        entry_fim.grid(row=1, column=1, pady=6, sticky="w")
        entry_fim.bind("<KeyRelease>", self._formatar_data_teclado)

        frame_btn = ctk.CTkFrame(popup, fg_color="transparent")
        frame_btn.pack(pady=16, padx=20, fill="x")
        frame_btn.grid_columnconfigure((0, 1), weight=1)

        def confirmar():
            dt_ini = entry_ini.get().strip()
            dt_fim = entry_fim.get().strip()
            if len(dt_ini) != 10 or len(dt_fim) != 10:
                messagebox.showwarning(
                    "Datas inválidas",
                    "Informe data inicial e final completas no formato DD/MM/AAAA.",
                    parent=popup,
                )
                return
            try:
                log_service.periodo_suporte(dt_ini, dt_fim)
            except ValueError as exc:
                messagebox.showwarning("Datas inválidas", str(exc), parent=popup)
                return

            popup.grab_release()
            popup.destroy()

            self.lbl_status.configure(
                text="Status: enviando log para suporte...",
                text_color="#3b8ed0",
            )
            self.update_idletasks()

            try:
                resultado = enviar_log_suporte_por_email(dt_ini, dt_fim)
            except Exception as exc:
                messagebox.showerror(
                    "Erro ao enviar e-mail",
                    f"Não foi possível enviar o log para o suporte:\n{exc}",
                )
                self.lbl_status.configure(
                    text="Status: falha ao enviar log para suporte.",
                    text_color="#c62828",
                )
                return

            messagebox.showinfo(
                "E-mail enviado",
                (
                    f"Assunto: {resultado['assunto']}\n"
                    f"Para: {resultado['destinatario']}\n"
                    f"De: {resultado['remetente']}\n\n"
                    f"Período: {dt_ini} 00:00 até {dt_fim} 23:59\n"
                    f"Logs: {resultado['qtd_logs']} registro(s)\n"
                    f"NFes: {resultado['qtd_notas']} nota(s)"
                ),
            )
            self.lbl_status.configure(
                text=(
                    f"Status: log enviado ao suporte "
                    f"({resultado['qtd_logs']} logs, {resultado['qtd_notas']} notas)."
                ),
                text_color="#3b8ed0",
            )

        def cancelar():
            popup.grab_release()
            popup.destroy()

        ctk.CTkButton(
            frame_btn, text="Confirmar", fg_color="green",
            hover_color="darkgreen", command=confirmar,
        ).grid(row=0, column=0, padx=6, sticky="ew")
        ctk.CTkButton(
            frame_btn, text="Cancelar", fg_color="gray",
            hover_color="#5f5f5f", command=cancelar,
        ).grid(row=0, column=1, padx=6, sticky="ew")

        popup.protocol("WM_DELETE_WINDOW", cancelar)
        entry_ini.focus_set()

    def _obter_limite(self):
        valor = self.combo_limite.get().strip()
        if not valor or valor.lower() == "todos":
            return None
        try:
            return max(1, int(valor))
        except Exception:
            self.combo_limite.set("1000")
            return 1000

    def _obter_filtros(self):
        return {
            "dt_ini": self.entry_dt_ini.get().strip(),
            "dt_fim": self.entry_dt_fim.get().strip(),
            "nota": self.entry_nota.get().strip(),
        }

    def _ha_filtro_ativo(self):
        filtros = self._obter_filtros()
        return any(filtros.values())

    def _set_texto(self, texto):
        self.caixa_logs.configure(state="normal")
        self.caixa_logs.delete("1.0", "end")
        self.caixa_logs.insert("end", texto)
        self.caixa_logs.see("end")
        self.caixa_logs.configure(state="disabled")

    def _append_evento(self, evento):
        try:
            filtrados = log_service.filtrar_logs(
                [evento],
                dt_ini=self.entry_dt_ini.get().strip(),
                dt_fim=self.entry_dt_fim.get().strip(),
                numero_nota=self.entry_nota.get().strip(),
            )
        except ValueError:
            self.carregar_logs()
            return

        if self._ha_filtro_ativo():
            self.carregar_logs()
            return
        if not filtrados:
            return

        self.caixa_logs.configure(state="normal")
        texto_atual = self.caixa_logs.get("1.0", "end-1c").strip()
        if self._contagem_logs == 0 and texto_atual == "Nenhum log registrado ainda.":
            self.caixa_logs.delete("1.0", "end")
        if self.caixa_logs.index("end-1c") != "1.0":
            self.caixa_logs.insert("end", "\n")
        self.caixa_logs.insert("end", log_service.formatar_evento(evento))
        self.caixa_logs.see("end")
        self.caixa_logs.configure(state="disabled")
        self._contagem_logs += 1
        self.lbl_status.configure(
            text=f"Status: {self._contagem_logs} log(s) carregado(s).",
            text_color="#3b8ed0",
        )

    def _receber_evento_log(self, evento):
        try:
            self.after(0, lambda: self._append_evento(evento))
        except Exception:
            pass

    def carregar_logs(self):
        filtros = self._obter_filtros()
        limite = None if self._ha_filtro_ativo() else self._obter_limite()
        logs = log_service.listar_logs(limite=limite)
        try:
            logs = log_service.filtrar_logs(
                logs,
                dt_ini=filtros["dt_ini"],
                dt_fim=filtros["dt_fim"],
                numero_nota=filtros["nota"],
            )
        except ValueError as exc:
            messagebox.showwarning("Filtro de logs", str(exc))
            return

        if not logs:
            self._contagem_logs = 0
            if self._ha_filtro_ativo():
                self._set_texto("Nenhum log encontrado para os filtros informados.")
                self.lbl_status.configure(text="Status: 0 log(s) filtrado(s).", text_color="gray")
            else:
                self._set_texto("Nenhum log registrado ainda.")
                self.lbl_status.configure(text="Status: 0 log(s).", text_color="gray")
            return

        self._contagem_logs = len(logs)
        texto = "\n".join(log_service.formatar_evento(log) for log in logs)
        self._set_texto(texto)
        self.lbl_status.configure(
            text=f"Status: {self._contagem_logs} log(s) carregado(s).",
            text_color="#3b8ed0",
        )

    def _limpar_filtros(self):
        self.entry_dt_ini.delete(0, "end")
        self.entry_dt_fim.delete(0, "end")
        self.entry_nota.delete(0, "end")
        self.carregar_logs()

    def _limpar_logs(self):
        if not messagebox.askyesno(
            "Limpar logs",
            "Deseja realmente apagar todo o historico de logs do robô?",
        ):
            return
        log_service.limpar_logs()
        self.carregar_logs()

    def destroy(self):
        try:
            log_service.remover_listener(self._listener)
        except Exception:
            pass
        super().destroy()
