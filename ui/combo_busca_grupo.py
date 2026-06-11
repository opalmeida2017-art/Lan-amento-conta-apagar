import customtkinter as ctk


def filtrar_lista_grupos(lista, texto):
    texto = (texto or "").strip().lower()
    if not texto:
        return list(lista)
    comeca = [g for g in lista if g.lower().startswith(texto)]
    contem = [g for g in lista if texto in g.lower() and g not in comeca]
    return comeca + contem if (comeca or contem) else list(lista)


class ComboBuscaGrupo(ctk.CTkComboBox):
    """Combo com busca ao digitar e opcional consulta no banco ao pressionar Enter."""

    TECLAS_IGNORADAS = frozenset({
        "Up", "Down", "Left", "Right", "Escape", "Tab",
        "Shift_L", "Shift_R", "Control_L", "Control_R",
    })

    def __init__(
        self,
        master,
        valores,
        width=180,
        valor_inicial="",
        on_buscar_enter=None,
        on_enter_acao=None,
        **kwargs,
    ):
        self._lista_completa = list(valores)
        self._on_buscar_enter = on_buscar_enter
        self._on_enter_acao = on_enter_acao
        super().__init__(master, width=width, values=self._lista_completa, **kwargs)
        if valor_inicial:
            self.set(valor_inicial)
        self._ligar_busca()

    def atualizar_valores(self, valores):
        self._lista_completa = list(valores)
        self.configure(values=self._lista_completa)

    def _ligar_busca(self):
        entry = self._entry

        def aplicar_filtro(event=None):
            if event and event.keysym in self.TECLAS_IGNORADAS:
                return
            if event and event.keysym == "Return":
                texto = entry.get().strip()
                if self._on_buscar_enter:
                    resultado = self._on_buscar_enter(texto)
                    if resultado:
                        self.set(resultado)
                        if resultado not in self._lista_completa:
                            self._lista_completa.append(resultado)
                            self.configure(values=self._lista_completa)
                else:
                    vals = self.cget("values")
                    if vals:
                        self.set(vals[0])
                if self._on_enter_acao:
                    try:
                        self._on_enter_acao()
                    except Exception:
                        pass
                return "break"

            texto = entry.get()
            filtrados = filtrar_lista_grupos(self._lista_completa, texto)
            self.configure(values=filtrados if filtrados else self._lista_completa)
            self.after(30, self._abrir_lista)

        def ao_focar(event=None):
            entry.select_range(0, "end")
            self.after(50, aplicar_filtro)

        entry.bind("<KeyRelease>", aplicar_filtro, add="+")
        entry.bind("<FocusIn>", ao_focar, add="+")

    def _abrir_lista(self):
        if self.cget("state") == "disabled":
            return
        if not self.cget("values"):
            return
        try:
            self._open_dropdown_menu()
        except Exception:
            pass
