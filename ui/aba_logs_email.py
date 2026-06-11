from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox

import database_setup as db
from ui.entry_data_calendario import EntryDataComCalendario


def _parse_data_log(texto, fim_do_dia=False):
    valor = str(texto or "").strip()
    if not valor:
        return None
    formatos = ("%d/%m/%Y", "%Y-%m-%d")
    for formato in formatos:
        try:
            dt = datetime.strptime(valor, formato)
            if fim_do_dia:
                return dt.replace(hour=23, minute=59, second=59)
            return dt.replace(hour=0, minute=0, second=0)
        except ValueError:
            continue
    raise ValueError("Use data no formato DD/MM/AAAA.")


def _filtrar_logs_email(logs, dt_ini="", dt_fim=""):
    inicio = _parse_data_log(dt_ini, fim_do_dia=False) if str(dt_ini or "").strip() else None
    fim = _parse_data_log(dt_fim, fim_do_dia=True) if str(dt_fim or "").strip() else None
    filtrados = []
    for item in logs or []:
        texto_data = str(item.get("data_hora") or "").strip()
        try:
            dt_log = datetime.strptime(texto_data, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt_log = None
        if inicio and dt_log and dt_log < inicio:
            continue
        if fim and dt_log and dt_log > fim:
            continue
        if inicio and not dt_log:
            continue
        if fim and not dt_log:
            continue
        filtrados.append(item)
    return filtrados


def _formatar_linha_log(item):
    status = item.get("status") or ""
    detalhe = item.get("detalhe") or ""
    texto = (
        f"[{item.get('data_hora', '')}] [{status}] [{item.get('tipo', '')}] "
        f"{item.get('assunto', '')} | Para: {item.get('destinatarios', '')}"
    )
    if detalhe:
        texto = f"{texto}\n    {detalhe}"
    return texto


class AbaLogsEmail(ctk.CTkFrame):
    _janela_popup = None
    _painel_ativo = None

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._contagem_logs = 0
        self._montar_tela()
        self.carregar_logs()

    @classmethod
    def abrir_popup(cls, parent):
        if cls._janela_popup is not None:
            try:
                if cls._janela_popup.winfo_exists():
                    cls._janela_popup.lift()
                    cls._janela_popup.focus_force()
                    return
            except Exception:
                cls._janela_popup = None

        popup = ctk.CTkToplevel(parent)
        popup.title("Logs de E-mail")
        cls._maximizar_janela(popup)
        popup.minsize(760, 480)
        popup.transient(parent.winfo_toplevel())

        cls._janela_popup = popup
        popup.grid_rowconfigure(0, weight=1)
        popup.grid_columnconfigure(0, weight=1)

        painel = cls(popup)
        painel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        cls._painel_ativo = painel

        def ao_fechar():
            cls._janela_popup = None
            cls._painel_ativo = None
            try:
                painel.destroy()
            except Exception:
                pass
            try:
                popup.destroy()
            except Exception:
                pass

        popup.protocol("WM_DELETE_WINDOW", ao_fechar)

    @staticmethod
    def _maximizar_janela(janela):
        def aplicar():
            try:
                janela.state("zoomed")
                return
            except Exception:
                pass
            try:
                janela.attributes("-zoomed", True)
                return
            except Exception:
                pass
            largura = janela.winfo_screenwidth()
            altura = janela.winfo_screenheight()
            janela.geometry(f"{largura}x{altura}+0+0")

        janela.after(80, aplicar)

    def _montar_tela(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        frame_topo = ctk.CTkFrame(self)
        frame_topo.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
        frame_topo.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(
            frame_topo,
            text="Logs de Envio de E-mail",
            font=("Arial", 18, "bold"),
            text_color="#3b8ed0",
        ).grid(row=0, column=0, columnspan=8, padx=10, pady=(10, 8), sticky="w")

        ctk.CTkLabel(frame_topo, text="Data Inicial:").grid(
            row=1, column=0, padx=(10, 4), pady=(0, 6), sticky="w",
        )
        self.entry_dt_ini = EntryDataComCalendario(frame_topo, width=130)
        self.entry_dt_ini.grid(row=1, column=1, padx=4, pady=(0, 6), sticky="w")

        ctk.CTkLabel(frame_topo, text="Data Final:").grid(
            row=1, column=2, padx=(10, 4), pady=(0, 6), sticky="w",
        )
        self.entry_dt_fim = EntryDataComCalendario(frame_topo, width=130)
        self.entry_dt_fim.grid(row=1, column=3, padx=4, pady=(0, 6), sticky="w")

        ctk.CTkLabel(frame_topo, text="Limite:").grid(
            row=1, column=4, padx=(10, 4), pady=(0, 6), sticky="w",
        )
        self.combo_limite = ctk.CTkComboBox(
            frame_topo, width=100, values=["200", "500", "1000", "2000", "Todos"],
        )
        self.combo_limite.set("1000")
        self.combo_limite.grid(row=1, column=5, padx=4, pady=(0, 6), sticky="w")

        self.btn_atualizar = ctk.CTkButton(
            frame_topo, text="Filtrar", width=90, command=self.carregar_logs,
        )
        self.btn_atualizar.grid(row=2, column=0, padx=(10, 4), pady=(0, 10), sticky="w")

        self.btn_limpar_filtros = ctk.CTkButton(
            frame_topo,
            text="Limpar Filtros",
            width=120,
            fg_color="gray",
            hover_color="#5f5f5f",
            command=self._limpar_filtros,
        )
        self.btn_limpar_filtros.grid(row=2, column=1, padx=4, pady=(0, 10), sticky="w")

        self.lbl_status = ctk.CTkLabel(
            frame_topo, text="Status: carregando logs...", text_color="gray",
        )
        self.lbl_status.grid(row=2, column=7, padx=(10, 10), pady=(0, 10), sticky="e")

        self.caixa_logs = ctk.CTkTextbox(self, wrap="word", font=("Consolas", 12))
        self.caixa_logs.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.caixa_logs.configure(state="disabled")

    def _obter_limite(self):
        valor = self.combo_limite.get().strip()
        if not valor or valor.lower() == "todos":
            return "Todos"
        try:
            return max(1, int(valor))
        except Exception:
            self.combo_limite.set("1000")
            return 1000

    def _ha_filtro_ativo(self):
        return bool(self.entry_dt_ini.get().strip() or self.entry_dt_fim.get().strip())

    def _set_texto(self, texto):
        self.caixa_logs.configure(state="normal")
        self.caixa_logs.delete("1.0", "end")
        self.caixa_logs.insert("end", texto)
        self.caixa_logs.see("end")
        self.caixa_logs.configure(state="disabled")

    def carregar_logs(self):
        dt_ini = self.entry_dt_ini.get().strip()
        dt_fim = self.entry_dt_fim.get().strip()
        limite = "Todos" if self._ha_filtro_ativo() else self._obter_limite()
        logs = db.listar_logs_email(limite=limite)
        try:
            logs = _filtrar_logs_email(logs, dt_ini=dt_ini, dt_fim=dt_fim)
        except ValueError as exc:
            messagebox.showwarning("Filtro de logs", str(exc))
            return

        if not logs:
            self._contagem_logs = 0
            if self._ha_filtro_ativo():
                self._set_texto("Nenhum log de e-mail encontrado para os filtros informados.")
                self.lbl_status.configure(text="Status: 0 log(s) filtrado(s).", text_color="gray")
            else:
                self._set_texto("Nenhum envio de e-mail registrado ainda.")
                self.lbl_status.configure(text="Status: 0 log(s).", text_color="gray")
            return

        self._contagem_logs = len(logs)
        texto = "\n\n".join(_formatar_linha_log(item) for item in logs)
        self._set_texto(texto)
        self.lbl_status.configure(
            text=f"Status: {self._contagem_logs} log(s) carregado(s).",
            text_color="#3b8ed0",
        )

    def _limpar_filtros(self):
        self.entry_dt_ini.delete(0, "end")
        self.entry_dt_fim.delete(0, "end")
        self.carregar_logs()
