import customtkinter as ctk
from tkinter import ttk

class AbaVeiculos(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.montar_tela()

    def montar_tela(self):
        lbl_titulo = ctk.CTkLabel(self, text="Relação de Veículos Cadastrados no Banco", font=("Arial", 16, "bold"))
        lbl_titulo.pack(pady=(10, 5))

        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.pack(pady=10, padx=10, fill="both", expand=True)

        colunas = ("codigo", "placa", "tipo", "atualizacao")
        self.tabela_veiculos = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=10)
        
        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_veiculos.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_veiculos.xview)
        self.tabela_veiculos.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.tabela_veiculos.pack(side="left", fill="both", expand=True)

        self.tabela_veiculos.heading("codigo", text="Cód. Veículo")
        self.tabela_veiculos.heading("placa", text="Placa")
        self.tabela_veiculos.heading("tipo", text="Tipo (Vínculo)")
        self.tabela_veiculos.heading("atualizacao", text="Última Atualização")
        
        self.tabela_veiculos.column("codigo", width=100, anchor="center")
        self.tabela_veiculos.column("placa", width=120, anchor="center")
        self.tabela_veiculos.column("tipo", width=200, anchor="w")
        self.tabela_veiculos.column("atualizacao", width=160, anchor="center")

        btn_atualizar = ctk.CTkButton(self, text="Atualizar Lista", font=("Arial", 12, "bold"), command=self.atualizar_tabela)
        btn_atualizar.pack(pady=10)

        self.atualizar_tabela()

    def atualizar_tabela(self):
        for item in self.tabela_veiculos.get_children():
            self.tabela_veiculos.delete(item)
            
        veiculos = self.controller.obter_veiculos_banco()
        for v in veiculos:
            self.tabela_veiculos.insert("", "end", values=(v['codVeiculo'], v['placa'], v['veiculoProprio'], v['ultima_atualizacao']))