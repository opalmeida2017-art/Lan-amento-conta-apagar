# -*- coding: utf-8 -*-
"""
Painel local — ativar / desativar licenças no GitHub (repositório privado).

Como abrir:
  - Duplo clique em: rodar_painel_licencas.bat
  - Ou no terminal: python painel_licencas.py

Requisito: arquivo licenca_config.py com token e dados do repositório.
"""
import customtkinter as ctk
from tkinter import messagebox

import licenca_remota as lr

ctk.set_appearance_mode('Dark')
ctk.set_default_color_theme('blue')


class PainelLicencas(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Painel de Licenças — local')
        self.geometry('960x560')
        self.minsize(800, 400)

        if not lr.licenca_configurada():
            messagebox.showerror(
                'Configuração',
                'Crie o arquivo licenca_config.py (copie de licenca_config.example.py)\n'
                'e preencha GITHUB_OWNER, GITHUB_REPO e GITHUB_TOKEN.',
            )
            self.destroy()
            return

        titulo = ctk.CTkFrame(self, fg_color='transparent')
        titulo.pack(fill='x', padx=12, pady=(12, 0))
        ctk.CTkLabel(
            titulo,
            text='Painel de Licenças (roda no seu PC)',
            font=('Arial', 18, 'bold'),
        ).pack(anchor='w')
        ctk.CTkLabel(
            titulo,
            text=(
                f'Repositório: {lr.GITHUB_OWNER}/{lr.GITHUB_REPO}  |  '
                f'branch: {lr.GITHUB_BRANCH}  |  pasta: {lr.PASTA_LICENCAS}/'
            ),
            font=('Arial', 12),
            text_color='#aaaaaa',
        ).pack(anchor='w', pady=(4, 0))
        ctk.CTkLabel(
            titulo,
            text='Desativar = cliente bloqueado em até 1h (ou ao reabrir o sistema).',
            font=('Arial', 11),
            text_color='#f39c12',
        ).pack(anchor='w', pady=(2, 8))

        topo = ctk.CTkFrame(self)
        topo.pack(fill='x', padx=12, pady=8)
        ctk.CTkButton(
            topo, text='Atualizar lista', command=self.carregar_lista,
            width=160, height=36, fg_color='#3b8ed0',
        ).pack(side='right', padx=8)

        cab = ctk.CTkFrame(self, fg_color='#333333')
        cab.pack(fill='x', padx=12, pady=(0, 4))
        for texto, w in (
            ('Arquivo', 170), ('Razão social', 190), ('ID instalação', 200),
            ('Ativado', 60), ('Status', 90), ('Ações', 170),
        ):
            ctk.CTkLabel(cab, text=texto, font=('Arial', 11, 'bold'), width=w).pack(
                side='left', padx=4, pady=6,
            )

        self.scroll = ctk.CTkScrollableFrame(self, height=380)
        self.scroll.pack(fill='both', expand=True, padx=12, pady=8)

        self.status = ctk.CTkLabel(self, text='', text_color='#aaaaaa')
        self.status.pack(pady=(0, 12))

        self.after(200, self.carregar_lista)

    def carregar_lista(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.status.configure(text='Carregando...')
        self.update_idletasks()
        try:
            licencas = lr.listar_todas_licencas()
        except Exception as e:
            self.status.configure(text='')
            messagebox.showerror('Erro', str(e))
            return

        if not licencas:
            ctk.CTkLabel(
                self.scroll,
                text='Nenhum arquivo .json na pasta licencas.\n'
                     'O cliente precisa salvar Configurações no sistema primeiro.',
                text_color='#f39c12',
                justify='left',
            ).pack(pady=20, padx=10)
            self.status.configure(text='0 licenças')
            return

        for lic in licencas:
            row = ctk.CTkFrame(self.scroll, fg_color='#1e1e1e', corner_radius=6)
            row.pack(fill='x', pady=3, padx=2)

            ctk.CTkLabel(row, text=lic['arquivo'], width=170, anchor='w').pack(side='left', padx=6, pady=8)
            ctk.CTkLabel(row, text=lic['razao_social'], width=190, anchor='w').pack(side='left', padx=4)
            ctk.CTkLabel(
                row, text=(lic['instalacao_id'] or '—')[:32], width=200, anchor='w',
                font=('Consolas', 10),
            ).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=str(lic['ativado']), width=60).pack(side='left', padx=4)

            cor = '#2ecc71' if lic['liberado'] else '#e74c3c'
            status_txt = 'LIBERADO' if lic['liberado'] else 'BLOQUEADO'
            ctk.CTkLabel(row, text=status_txt, width=90, text_color=cor, font=('Arial', 11, 'bold')).pack(
                side='left', padx=4,
            )

            nome = lic['arquivo']
            ctk.CTkButton(
                row, text='Ativar', width=72, height=30, fg_color='#27ae60',
                command=lambda n=nome: self.alterar(n, 'sim'),
            ).pack(side='left', padx=3, pady=6)
            ctk.CTkButton(
                row, text='Desativar', width=82, height=30, fg_color='#c0392b',
                command=lambda n=nome: self.alterar(n, 'não'),
            ).pack(side='left', padx=3, pady=6)

        self.status.configure(text=f'{len(licencas)} licença(s) carregada(s)')

    def alterar(self, nome_arquivo, valor):
        acao = 'ATIVAR (liberar)' if valor == 'sim' else 'BLOQUEAR'
        if not messagebox.askyesno('Confirmar', f'{acao}\n\nArquivo:\n{nome_arquivo}'):
            return
        self.status.configure(text='Salvando no GitHub...')
        self.update_idletasks()
        try:
            ok, msg = lr.definir_ativado_arquivo(nome_arquivo, valor)
        except Exception as e:
            self.status.configure(text='')
            messagebox.showerror('Erro', str(e))
            return
        self.status.configure(text='')
        if ok:
            messagebox.showinfo('Sucesso', msg)
            self.carregar_lista()
        else:
            messagebox.showerror('Erro', msg)


if __name__ == '__main__':
    app = PainelLicencas()
    app.mainloop()
