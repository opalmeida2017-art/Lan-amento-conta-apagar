import calendar
from datetime import datetime

import customtkinter as ctk


def _formatar_data_teclado(event):
    entry = event.widget
    texto = "".join(c for c in entry.get() if c.isdigit())[:8]
    if event.keysym == "BackSpace":
        return
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


def _formatar_data_hora_teclado(event):
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
        partes.append(texto[2:4])
    if len(texto) > 4:
        partes.append(texto[4:8])

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


class PopupCalendario(ctk.CTkToplevel):
    MESES = (
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    )
    COR_HOJE = "#ffb74d"
    COR_HOJE_HOVER = "#ffa726"
    COR_SELECIONADO = "#1f538d"
    COR_SELECIONADO_HOVER = "#163d68"

    def __init__(self, parent, entry_destino, com_hora=False):
        super().__init__(parent)
        self.entry_destino = entry_destino
        self.com_hora = bool(com_hora)
        hoje = datetime.now()
        self._ano = hoje.year
        self._mes = hoje.month
        self._dia_hoje = hoje.day
        self._dia_selecionado = self._extrair_dia_selecionado(entry_destino.get().strip()) or self._dia_hoje

        self.title("Selecionar data")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._montar()
        self._renderizar_mes()
        self._posicionar(parent)

    @staticmethod
    def _extrair_dia_selecionado(texto):
        valor = str(texto or "").strip()
        if not valor:
            return None
        parte_data = valor.split(" ", 1)[0]
        try:
            return datetime.strptime(parte_data, "%d/%m/%Y").day
        except ValueError:
            return None

    def _eh_hoje(self, dia):
        hoje = datetime.now()
        return dia == self._dia_hoje and self._mes == hoje.month and self._ano == hoje.year

    def _estilo_botao_dia(self, dia):
        if self._eh_hoje(dia):
            return self.COR_HOJE, self.COR_HOJE_HOVER
        if dia == self._dia_selecionado:
            return self.COR_SELECIONADO, self.COR_SELECIONADO_HOVER
        return None, None

    def _posicionar(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + 20
        y = parent.winfo_rooty() + parent.winfo_height() + 8
        self.geometry(f"300x320+{x}+{y}")

    def _montar(self):
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=10, pady=(10, 6))

        self.btn_mes_ant = ctk.CTkButton(topo, text="◀", width=36, command=self._mes_anterior)
        self.btn_mes_ant.pack(side="left")

        self.lbl_mes = ctk.CTkLabel(topo, text="", font=("Arial", 14, "bold"))
        self.lbl_mes.pack(side="left", expand=True)

        self.btn_mes_prox = ctk.CTkButton(topo, text="▶", width=36, command=self._mes_proximo)
        self.btn_mes_prox.pack(side="right")

        dias = ctk.CTkFrame(self, fg_color="transparent")
        dias.pack(fill="x", padx=10, pady=(0, 4))
        for idx, nome in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
            ctk.CTkLabel(dias, text=nome, width=36, font=("Arial", 10, "bold")).grid(
                row=0, column=idx, padx=1, pady=1,
            )

        self.frame_dias = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_dias.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes = 12
            self._ano -= 1
        else:
            self._mes -= 1
        self._renderizar_mes()

    def _mes_proximo(self):
        if self._mes == 12:
            self._mes = 1
            self._ano += 1
        else:
            self._mes += 1
        self._renderizar_mes()

    def _selecionar_dia(self, dia):
        self._dia_selecionado = dia
        data = f"{dia:02d}/{self._mes:02d}/{self._ano}"
        if self.com_hora:
            hora_atual = ""
            texto = self.entry_destino.get().strip()
            if " " in texto:
                hora_atual = texto.split(" ", 1)[1].strip()
            data = f"{data} {hora_atual or '00:00'}".strip()
        self.entry_destino.delete(0, "end")
        self.entry_destino.insert(0, data)
        self.grab_release()
        self.destroy()

    def _renderizar_mes(self):
        for widget in self.frame_dias.winfo_children():
            widget.destroy()

        self.lbl_mes.configure(text=f"{self.MESES[self._mes - 1]} {self._ano}")

        semanas = calendar.monthcalendar(self._ano, self._mes)
        for linha, semana in enumerate(semanas):
            for coluna, dia in enumerate(semana):
                if dia == 0:
                    ctk.CTkLabel(self.frame_dias, text="", width=36).grid(
                        row=linha, column=coluna, padx=1, pady=1,
                    )
                    continue
                fg, hover = self._estilo_botao_dia(dia)
                kwargs = {
                    "text": str(dia),
                    "width": 36,
                    "height": 28,
                    "command": lambda d=dia: self._selecionar_dia(d),
                }
                if fg:
                    kwargs["fg_color"] = fg
                    kwargs["hover_color"] = hover
                    kwargs["text_color"] = "#1a1a1a" if self._eh_hoje(dia) else "white"
                ctk.CTkButton(self.frame_dias, **kwargs).grid(
                    row=linha, column=coluna, padx=1, pady=1,
                )


class EntryDataComCalendario(ctk.CTkFrame):
    """Campo de data com botão de calendário."""

    def __init__(
        self,
        master,
        width=120,
        placeholder="DD/MM/AAAA",
        com_hora=False,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.com_hora = bool(com_hora)
        texto_ph = "DD/MM/AAAA HH:MM" if self.com_hora else placeholder

        self.entry = ctk.CTkEntry(self, width=width, placeholder_text=texto_ph)
        self.entry.pack(side="left", fill="x", expand=True)

        formatador = _formatar_data_hora_teclado if self.com_hora else _formatar_data_teclado
        self.entry.bind("<KeyRelease>", formatador)

        self.btn_calendario = ctk.CTkButton(
            self,
            text="📅",
            width=34,
            fg_color="#1f538d",
            hover_color="#163d68",
            command=self._abrir_calendario,
        )
        self.btn_calendario.pack(side="left", padx=(4, 0))

    def _abrir_calendario(self):
        PopupCalendario(self, self.entry, com_hora=self.com_hora)

    def get(self):
        return self.entry.get()

    def delete(self, inicio, fim):
        return self.entry.delete(inicio, fim)

    def insert(self, indice, texto):
        return self.entry.insert(indice, texto)

    def bind(self, sequencia, funcao, add=None):
        return self.entry.bind(sequencia, funcao, add=add or "")
