import customtkinter as ctk


def filtrar_lista_grupos(lista, texto):
    texto = (texto or "").strip().lower()
    if not texto:
        return list(lista)
    comeca = [g for g in lista if g.lower().startswith(texto)]
    contem = [g for g in lista if texto in g.lower() and g not in comeca]
    return comeca + contem if (comeca or contem) else list(lista)


class ComboBuscaGrupo(ctk.CTkComboBox):
    """CTkComboBox padrão com busca ao digitar (f → FREIOS, FERRAMENTAS...)."""

    TECLAS_IGNORADAS = frozenset({
        "Up", "Down", "Left", "Right", "Escape", "Tab",
        "Shift_L", "Shift_R", "Control_L", "Control_R",
    })

    def __init__(self, master, valores, width=180, valor_inicial="", **kwargs):
        self._lista_completa = list(valores)
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
                vals = self.cget("values")
                if vals:
                    self.set(vals[0])
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
