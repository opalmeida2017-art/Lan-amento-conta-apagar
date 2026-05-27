import sqlite3
import os
import urllib.request
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import bcrypt
import secrets
import string
import json

# ==========================================
# 1. MÓDULO DE SEGURANÇA E CRIPTOGRAFIA
# ==========================================
def gerar_chave_seguranca():
    if not os.path.exists("secret.key"):
        chave = Fernet.generate_key()
        with open("secret.key", "wb") as key_file:
            key_file.write(chave)
        print("[+] Chave de segurança gerada.")

def gerar_hash_senha(senha_texto_puro):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha_texto_puro.encode('utf-8'), salt)

def validar_login(email, senha_texto):
    """Verifica se o e-mail existe e se a senha bate com o Hash."""
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    cursor.execute("SELECT senha_hash FROM Usuarios WHERE email = ?", (email,))
    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        senha_hash_banco = resultado[0]
        if bcrypt.checkpw(senha_texto.encode('utf-8'), senha_hash_banco):
            return True, "Login aprovado!"
        else:
            return False, "Senha incorreta."
    return False, "Usuário não encontrado."

# ==========================================
# 2. CONFIGURAÇÃO DO BANCO E USUÁRIOS
# ==========================================
def inicializar_banco():
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS Usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome_completo TEXT, email TEXT UNIQUE, senha_hash BLOB)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Configuracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, link_sistema TEXT, usuario_sistema TEXT, 
        senha_sistema_criptografada BLOB, email_smtp TEXT, email_usuario TEXT, 
        email_senha_criptografada BLOB, email_ssl INTEGER, email_porta INTEGER,
        email_agendamento_tipo TEXT DEFAULT '', email_intervalo_horas INTEGER DEFAULT 1,
        email_proxima_execucao TEXT DEFAULT '', email_ultima_execucao TEXT DEFAULT '',
        email_destinatarios TEXT DEFAULT '')''')

    try:
        cursor.execute("ALTER TABLE Configuracoes ADD COLUMN email_agendamento_tipo TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE Configuracoes ADD COLUMN email_intervalo_horas INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE Configuracoes ADD COLUMN email_proxima_execucao TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE Configuracoes ADD COLUMN email_ultima_execucao TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE Configuracoes ADD COLUMN email_destinatarios TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS Tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash TEXT UNIQUE, 
        data_insercao DATE, ultima_checagem DATE, status TEXT DEFAULT 'PENDENTE')''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Notas_Fiscais (
        id INTEGER PRIMARY KEY AUTOINCREMENT, numero_nf TEXT, status TEXT DEFAULT 'Pendente', data_registro DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS filtros_salvos (
        id INTEGER PRIMARY KEY, mes TEXT, ano TEXT,
        cod_filial TEXT DEFAULT '', cod_unidade_embarque TEXT DEFAULT '',
        ultimos_30_dias INTEGER DEFAULT 0)''')

    try:
        cursor.execute("ALTER TABLE filtros_salvos ADD COLUMN cod_filial TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE filtros_salvos ADD COLUMN cod_unidade_embarque TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE filtros_salvos ADD COLUMN ultimos_30_dias INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    # TABELA COM A COLUNA NOVA DE OBSERVAÇÃO
    cursor.execute('''CREATE TABLE IF NOT EXISTS notas_raspadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT, fornecedor TEXT, num_nota TEXT, data_em TEXT,
        valor TEXT, sit_nfe TEXT, chave_nfe TEXT, filial TEXT, user_ins TEXT,
        codigo_interno TEXT, erro_importacao TEXT, observacao_nfe TEXT,
        data_insercao TEXT DEFAULT '')''')

    # TRUQUE PARA ATUALIZAR O BANCO ANTIGO
    try: cursor.execute("ALTER TABLE notas_raspadas ADD COLUMN codigo_interno TEXT")
    except sqlite3.OperationalError: pass 
        
    try: cursor.execute("ALTER TABLE notas_raspadas ADD COLUMN erro_importacao TEXT")
    except sqlite3.OperationalError: pass 

    try: cursor.execute("ALTER TABLE notas_raspadas ADD COLUMN observacao_nfe TEXT")
    except sqlite3.OperationalError: pass 
    
    try: cursor.execute("ALTER TABLE notas_raspadas ADD COLUMN data_insercao TEXT DEFAULT ''")
    except sqlite3.OperationalError: pass
    
    # 👇 NOVA LINHA AQUI 👇
    try: cursor.execute("ALTER TABLE notas_raspadas ADD COLUMN nfe_estoque TEXT DEFAULT '☐'")
    except sqlite3.OperationalError: pass

    try: cursor.execute("ALTER TABLE notas_raspadas ADD COLUMN nfe_arquiva TEXT DEFAULT '☐'")
    except sqlite3.OperationalError: pass
    
    # Criação da tabela oficial da Frota
    cursor.execute('''CREATE TABLE IF NOT EXISTS frota_erp (
        codVeiculo INTEGER PRIMARY KEY, 
        placa TEXT UNIQUE, 
        veiculoProprio TEXT,
        ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

def configurar_usuario_master():
    """Garante que o seu usuário master sempre exista e não seja contado no limite."""
    email_master = "op.almeida@hotmail.com"
    senha_master = "123"
    
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Usuarios WHERE email = ?", (email_master,))
    if not cursor.fetchone():
        senha_hash = gerar_hash_senha(senha_master)
        cursor.execute("INSERT INTO Usuarios (nome_completo, email, senha_hash) VALUES (?, ?, ?)",
                       ("Master Admin", email_master, senha_hash))
        conn.commit()
    conn.close()

def contar_usuarios_comuns():
    """Conta quantos usuários existem, IGNORANDO o Master."""
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE email != 'op.almeida@hotmail.com'")
    total = cursor.fetchone()[0]
    conn.close()
    return total

def cadastrar_usuario(nome, email, senha):
    """Cadastra o operador respeitando o limite de 1 funcionário."""
    if contar_usuarios_comuns() >= 1:
        return False, "Limite de usuários atingido (Máximo: 1 Operador)."
    
    senha_hash = gerar_hash_senha(senha)
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Usuarios (nome_completo, email, senha_hash) VALUES (?, ?, ?)",
                       (nome, email, senha_hash))
        conn.commit()
        return True, "Operador cadastrado com sucesso!"
    except Exception as e:
        return False, f"Erro ao cadastrar: E-mail já existe."
    finally:
        conn.close()

# ==========================================
# 3. MÓDULO DE LICENCIAMENTO (SISTEMA NOVO OFF-LINE)
# ==========================================
import hashlib
from datetime import datetime, timedelta
import sqlite3

PALAVRA_SECRETA = "AUTOMACAO_FROTA_SEFAZ_2026_MASTER"

def criar_tabela_licenca():
    """Garante que a tabela de licença exista no banco de dados"""
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS licenca_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_expiracao TEXT NOT NULL,
            token_usado TEXT
        )
    ''')
    conn.commit()
    conn.close()

def checar_status_licenca():
    """Verifica se o sistema ainda está dentro do prazo"""
    criar_tabela_licenca()
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        c = conn.cursor()
        c.execute('SELECT data_expiracao FROM licenca_sistema ORDER BY id DESC LIMIT 1')
        resultado = c.fetchone()
        conn.close()

        if not resultado:
            return -1, 0  # -1 = Nunca foi ativado (Tela de Bloqueio)

        data_expiracao = datetime.strptime(resultado[0], "%Y-%m-%d %H:%M:%S")
        hoje = datetime.now()
        
        dias_restantes = (data_expiracao - hoje).days
        
        if dias_restantes < 0:
            return -2, 0  # -2 = Vencido (Tela de Bloqueio)
        elif dias_restantes <= 5:
            return 0, dias_restantes  # 0 = Quase vencendo (Avisa na tela de login)
        else:
            return 1, dias_restantes  # 1 = Ativo e tudo certo
    except Exception as e:
        print(f"Erro ao checar licença: {e}")
        return -1, 0

def ativar_token_31_dias(token):
    """Valida matematicamente o token e adiciona 31 dias de uso"""
    criar_tabela_licenca()
    
    token_limpo = token.replace("-", "").strip().upper()
    if len(token_limpo) != 16:
        return False, "Token inválido! Certifique-se de digitar os 16 caracteres."
        
    caracteres_base = token_limpo[:12]
    assinatura_recebida = token_limpo[12:]
    
    # O aplicativo tenta recriar a assinatura usando o segredo
    assinatura_esperada = hashlib.sha256((caracteres_base + PALAVRA_SECRETA).encode()).hexdigest()[:4].upper()
    
    if assinatura_recebida == assinatura_esperada:
        conn = sqlite3.connect('sistema_automacao.db')
        c = conn.cursor()
        c.execute('SELECT id FROM licenca_sistema WHERE token_usado = ?', (token_limpo,))
        if c.fetchone():
            conn.close()
            return False, "Este token já foi utilizado anteriormente!"

        nova_validade = datetime.now() + timedelta(days=31)
        c.execute('INSERT INTO licenca_sistema (data_expiracao, token_usado) VALUES (?, ?)', 
                  (nova_validade.strftime("%Y-%m-%d %H:%M:%S"), token_limpo))
        conn.commit()
        conn.close()
        
        return True, "Licença validada com sucesso! O sistema foi liberado por 31 dias."
    else:
        return False, "Token inválido ou falsificado!"

# ==========================================
# 3.1 LICENCIAMENTO REMOTO (ID POR INSTALAÇÃO)
# ==========================================
import uuid

def criar_tabela_instalacao():
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS instalacao_licenca (
            id INTEGER PRIMARY KEY,
            instalacao_id TEXT UNIQUE NOT NULL,
            razao_social TEXT,
            nome_arquivo_github TEXT,
            data_criacao TEXT NOT NULL,
            ultimo_upload TEXT,
            ultima_verificacao TEXT,
            status TEXT DEFAULT 'pendente'
        )
    ''')
    try:
        c.execute('ALTER TABLE instalacao_licenca ADD COLUMN razao_social TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE instalacao_licenca ADD COLUMN nome_arquivo_github TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE instalacao_licenca ADD COLUMN ultimo_ativado_github TEXT')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def obter_ou_criar_instalacao_id():
    """Gera UUID único na primeira vez; reutiliza nas próximas."""
    criar_tabela_instalacao()
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute('SELECT instalacao_id FROM instalacao_licenca WHERE id = 1')
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]
    novo_id = str(uuid.uuid4())
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        'INSERT INTO instalacao_licenca (id, instalacao_id, data_criacao, status) VALUES (1, ?, ?, ?)',
        (novo_id, agora, 'pendente'),
    )
    conn.commit()
    conn.close()
    return novo_id

def obter_instalacao_id():
    criar_tabela_instalacao()
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute('SELECT instalacao_id FROM instalacao_licenca WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def carregar_instalacao_licenca():
    criar_tabela_instalacao()
    conn = sqlite3.connect('sistema_automacao.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM instalacao_licenca WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}


def salvar_razao_social_transportadora(razao_social, nome_arquivo_github):
    criar_tabela_instalacao()
    obter_ou_criar_instalacao_id()
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute(
        'UPDATE instalacao_licenca SET razao_social = ?, nome_arquivo_github = ? WHERE id = 1',
        (razao_social.strip(), nome_arquivo_github),
    )
    conn.commit()
    conn.close()


def registrar_upload_licenca_ok():
    criar_tabela_instalacao()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute(
        'UPDATE instalacao_licenca SET ultimo_upload = ?, status = ? WHERE id = 1',
        (agora, 'ativo'),
    )
    conn.commit()
    conn.close()

def registrar_verificacao_licenca(ok):
    """Atualiza status só após leitura confirmada do JSON no GitHub."""
    criar_tabela_instalacao()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = 'ativo' if ok else 'bloqueado'
    ativado_github = 'sim' if ok else 'não'
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute(
        'UPDATE instalacao_licenca SET ultima_verificacao = ?, status = ?, ultimo_ativado_github = ? WHERE id = 1',
        (agora, status, ativado_github),
    )
    conn.commit()
    conn.close()


def limpar_bloqueio_indevido_rede():
    """Remove bloqueio gravado por falha de rede (não por ativado=não no GitHub)."""
    criar_tabela_instalacao()
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute(
        '''UPDATE instalacao_licenca
           SET status = 'ativo', ultimo_ativado_github = 'sim'
           WHERE id = 1 AND ultimo_ativado_github IN ('não', 'nao')
             AND nome_arquivo_github IS NOT NULL AND nome_arquivo_github != '' ''',
    )
    conn.commit()
    conn.close()

# ==========================================
# 4. MÓDULO DE CONFIGURAÇÕES E AUTOMAÇÃO
# ==========================================
def carregar_chave():
    return open("secret.key", "rb").read()

def salvar_configuracoes(
    link,
    user_sis,
    senha_sis,
    smtp,
    user_email,
    senha_email,
    ssl,
    porta,
    agendamento_tipo='',
    intervalo_horas=1,
    proxima_execucao='',
    ultima_execucao='',
    destinatarios='',
):
    chave = carregar_chave()
    f = Fernet(chave)
    
    senha_sis_crypt = f.encrypt(senha_sis.encode()) if senha_sis else b""
    senha_email_crypt = f.encrypt(senha_email.encode()) if senha_email else b""
    
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM Configuracoes WHERE id = 1")
    if cursor.fetchone():
        cursor.execute("""UPDATE Configuracoes SET link_sistema=?, usuario_sistema=?, senha_sistema_criptografada=?, 
                          email_smtp=?, email_usuario=?, email_senha_criptografada=?, email_ssl=?, email_porta=?,
                          email_agendamento_tipo=?, email_intervalo_horas=?, email_proxima_execucao=?, email_ultima_execucao=?,
                          email_destinatarios=?
                          WHERE id=1""",
                       (
                           link, user_sis, senha_sis_crypt, smtp, user_email, senha_email_crypt, ssl, porta,
                           agendamento_tipo, intervalo_horas, proxima_execucao, ultima_execucao,
                           str(destinatarios or '').strip(),
                       ))
    else:
        cursor.execute("""INSERT INTO Configuracoes (id, link_sistema, usuario_sistema, senha_sistema_criptografada, 
                          email_smtp, email_usuario, email_senha_criptografada, email_ssl, email_porta,
                          email_agendamento_tipo, email_intervalo_horas, email_proxima_execucao, email_ultima_execucao,
                          email_destinatarios) 
                          VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (
                           link, user_sis, senha_sis_crypt, smtp, user_email, senha_email_crypt, ssl, porta,
                           agendamento_tipo, intervalo_horas, proxima_execucao, ultima_execucao,
                           str(destinatarios or '').strip(),
                       ))
    conn.commit()
    conn.close()
    return True, "Configurações salvas com segurança!"

def carregar_configuracoes():
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Configuracoes WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        chave = carregar_chave()
        f = Fernet(chave)
        
        try: senha_sis = f.decrypt(row[3]).decode() if row[3] else ""
        except: senha_sis = ""
        
        try: senha_email = f.decrypt(row[6]).decode() if row[6] else ""
        except: senha_email = ""
        
        return {
            "link": row[1] or "", "user_sis": row[2] or "", "senha_sis": senha_sis,
            "smtp": row[4] or "", "user_email": row[5] or "", "senha_email": senha_email,
            "ssl": row[7] if row[7] is not None else 1, "porta": row[8] or "",
            "agendamento_tipo": row[9] or "", "intervalo_horas": row[10] or 1,
            "proxima_execucao": row[11] or "", "ultima_execucao": row[12] or "",
            "destinatarios": row[13] or "",
        }
    return None


def atualizar_agendamento_email(tipo='', intervalo_horas=1, proxima_execucao='', ultima_execucao=None):
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        if ultima_execucao is None:
            cursor.execute(
                '''UPDATE Configuracoes
                   SET email_agendamento_tipo = ?, email_intervalo_horas = ?, email_proxima_execucao = ?
                   WHERE id = 1''',
                (tipo, intervalo_horas, proxima_execucao),
            )
        else:
            cursor.execute(
                '''UPDATE Configuracoes
                   SET email_agendamento_tipo = ?, email_intervalo_horas = ?,
                       email_proxima_execucao = ?, email_ultima_execucao = ?
                   WHERE id = 1''',
                (tipo, intervalo_horas, proxima_execucao, ultima_execucao),
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar agendamento de e-mail: {e}")
        return False

# --- Filtros ---
def salvar_filtros(mes, ano, cod_filial='', cod_unidade_embarque='', ultimos_30_dias=False):
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM filtros_salvos')
        cursor.execute(
            '''INSERT INTO filtros_salvos (mes, ano, cod_filial, cod_unidade_embarque, ultimos_30_dias)
               VALUES (?, ?, ?, ?, ?)''',
            (
                mes,
                ano,
                str(cod_filial or '').strip(),
                str(cod_unidade_embarque or '').strip(),
                1 if ultimos_30_dias else 0,
            ),
        )
        conn.commit()
        conn.close()
        return True, 'Período e códigos de filial/unidade salvos com sucesso!'
    except Exception as e:
        return False, f'Erro ao salvar filtros: {e}'


def carregar_filtros():
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT mes, ano, cod_filial, cod_unidade_embarque, ultimos_30_dias
               FROM filtros_salvos ORDER BY id DESC LIMIT 1''',
        )
        resultado = cursor.fetchone()
        conn.close()
        if resultado:
            return {
                'mes': resultado[0],
                'ano': resultado[1],
                'cod_filial': resultado[2] or '',
                'cod_unidade_embarque': resultado[3] or '',
                'ultimos_30_dias': bool(resultado[4]),
            }
        return None
    except Exception:
        try:
            conn = sqlite3.connect('sistema_automacao.db')
            cursor = conn.cursor()
            cursor.execute('SELECT mes, ano, cod_filial, cod_unidade_embarque FROM filtros_salvos ORDER BY id DESC LIMIT 1')
            resultado = cursor.fetchone()
            conn.close()
            if resultado:
                return {
                    'mes': resultado[0],
                    'ano': resultado[1],
                    'cod_filial': (resultado[2] or '') if len(resultado) > 2 else '',
                    'cod_unidade_embarque': (resultado[3] or '') if len(resultado) > 3 else '',
                    'ultimos_30_dias': False,
                }
        except Exception:
            pass
        return None

# --- Notas Raspadas (Para a Dashboard) ---
def salvar_nota_raspada(dados_nota):
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM notas_raspadas WHERE chave_nfe = ?", (dados_nota['chave_nfe'],))
        if cursor.fetchone():
            conn.close()
            return False

        cursor.execute('''
            INSERT INTO notas_raspadas (status, fornecedor, num_nota, data_em, valor, sit_nfe, chave_nfe, filial, user_ins, codigo_interno, erro_importacao, observacao_nfe, data_insercao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dados_nota.get('status', ''), dados_nota.get('fornecedor', ''), dados_nota.get('num_nota', ''), 
            dados_nota.get('data_em', ''), dados_nota.get('valor', ''), dados_nota.get('sit_nfe', ''), 
            dados_nota.get('chave_nfe', ''), dados_nota.get('filial', ''), dados_nota.get('user_ins', ''),
            dados_nota.get('codigo_interno', ''), dados_nota.get('erro_importacao', ''), dados_nota.get('observacao_nfe', ''),
            dados_nota.get('data_insercao') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar nota no banco: {e}")
        return False

MSG_ERRO_ARQUIVO_INDISPONIVEL = (
    'Arquivo indisponível para download (Cancelada/Rejeitada)'
)


def texto_indica_arquivo_indisponivel(texto):
    """True se o retorno SEFAZ/erro for cancelada/rejeitada/indisponível."""
    if not texto:
        return False
    tl = str(texto).lower()
    if 'indispon' in tl:
        return True
    if 'cancelad' in tl and ('arquivo' in tl or 'download' in tl or 'nfe' in tl):
        return True
    if 'rejeit' in tl and ('arquivo' in tl or 'download' in tl or '656' in tl):
        return True
    return False


def nota_erro_arquivo_indisponivel(erro_importacao):
    """True se a nota já foi gravada com o erro padrão de arquivo indisponível."""
    if not erro_importacao:
        return False
    if erro_importacao.strip() == MSG_ERRO_ARQUIVO_INDISPONIVEL:
        return True
    return texto_indica_arquivo_indisponivel(erro_importacao)


def registrar_erro_nota_painel(dados_nota, erro_msg):
    """Grava status Erro no banco e no dict da nota (dashboard / painel da aplicação)."""
    msg = (erro_msg or 'Erro no processamento')[:500]
    dados_nota['status'] = 'Erro'
    dados_nota['erro_importacao'] = msg
    dados_nota['codigo_interno'] = ''
    if not atualizar_nota_raspada(dados_nota):
        salvar_nota_raspada(dados_nota)
    return True


def atualizar_nota_raspada(dados_nota, arquivar_automatico=False):
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        if arquivar_automatico:
            cursor.execute('''
                UPDATE notas_raspadas
                SET status = ?, codigo_interno = ?, erro_importacao = ?,
                    observacao_nfe = ?, nfe_arquiva = ?
                WHERE chave_nfe = ?
            ''', (
                dados_nota.get('status', ''),
                dados_nota.get('codigo_interno', ''),
                dados_nota.get('erro_importacao', ''),
                dados_nota.get('observacao_nfe', ''),
                '☑',
                dados_nota.get('chave_nfe', ''),
            ))
        else:
            cursor.execute('''
                UPDATE notas_raspadas
                SET status = ?, codigo_interno = ?, erro_importacao = ?, observacao_nfe = ?
                WHERE chave_nfe = ?
            ''', (
                dados_nota.get('status', ''),
                dados_nota.get('codigo_interno', ''),
                dados_nota.get('erro_importacao', ''),
                dados_nota.get('observacao_nfe', ''),
                dados_nota.get('chave_nfe', ''),
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar nota: {e}")
        return False
    
def listar_todas_notas():
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notas_raspadas ORDER BY id DESC")
        res = cursor.fetchall()
        conn.close()
        return [dict(row) for row in res]
    except:
        return []

if __name__ == "__main__":
    gerar_chave_seguranca()
    inicializar_banco()
    configurar_usuario_master()
    print("Banco e Master configurados com sucesso!")
    
# =======================================================
# FUNÇÕES PARA CONFIGURAÇÃO DOS MODELOS DE PLACA
# =======================================================
import sqlite3

def criar_tabela_config_placas():
    conn = sqlite3.connect('banco_nfe.db') 
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS config_placas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo TEXT NOT NULL
        )
    ''')
    c.execute('SELECT count(*) FROM config_placas')
    if c.fetchone()[0] == 0:
        padroes = ["PLACA: AAA-1A11", "PLAC: AAA 1A11", "PLACA: AAA1A11", "PLAC: AAA1111"]
        for p in padroes:
            c.execute('INSERT INTO config_placas (modelo) VALUES (?)', (p,))
    conn.commit()
    conn.close()

def obter_modelos_placa():
    criar_tabela_config_placas()
    try:
        conn = sqlite3.connect('banco_nfe.db')
        c = conn.cursor()
        c.execute('SELECT modelo FROM config_placas')
        resultados = c.fetchall()
        conn.close()
        return [r[0] for r in resultados]
    except:
        return []

def salvar_modelos_placa(modelos_str):
    criar_tabela_config_placas()
    conn = sqlite3.connect('banco_nfe.db')
    c = conn.cursor()
    c.execute('DELETE FROM config_placas') 
    
    modelos = [m.strip() for m in modelos_str.split(',') if m.strip()]
    for m in modelos:
        c.execute('INSERT INTO config_placas (modelo) VALUES (?)', (m,))
        
    conn.commit()
    conn.close()

def obter_modelos_placa_string():
    modelos = obter_modelos_placa() 
    return ", ".join(modelos)
# =======================================================
# FUNÇÕES PARA CONFIGURAÇÃO DOS MODELOS DE KM
# =======================================================
def criar_tabela_config_km():
    conn = sqlite3.connect('banco_nfe.db') 
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS config_km (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo TEXT NOT NULL
        )
    ''')
    c.execute('SELECT count(*) FROM config_km')
    if c.fetchone()[0] == 0:
        padroes = ["KM: 1", "KM 1", "HIDROMETRO: 1", "ODO: 1"]
        for p in padroes:
            c.execute('INSERT INTO config_km (modelo) VALUES (?)', (p,))
    conn.commit()
    conn.close()

def obter_modelos_km():
    criar_tabela_config_km()
    try:
        conn = sqlite3.connect('banco_nfe.db')
        c = conn.cursor()
        c.execute('SELECT modelo FROM config_km')
        resultados = c.fetchall()
        conn.close()
        return [r[0] for r in resultados]
    except:
        return []

def salvar_modelos_km(modelos_str):
    criar_tabela_config_km()
    conn = sqlite3.connect('banco_nfe.db')
    c = conn.cursor()
    c.execute('DELETE FROM config_km') 
    
    modelos = [m.strip() for m in modelos_str.split(',') if m.strip()]
    for m in modelos:
        c.execute('INSERT INTO config_km (modelo) VALUES (?)', (m,))
        
    conn.commit()
    conn.close()

def obter_modelos_km_string():
    modelos = obter_modelos_km() 
    return ", ".join(modelos)

def sincronizar_frota_erp(lista_veiculos):
    import sqlite3
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        
        # =======================================================
        # GARANTIA ABSOLUTA: Cria a tabela aqui mesmo se ela não existir!
        # =======================================================
        cursor.execute('''CREATE TABLE IF NOT EXISTS frota_erp (
            codVeiculo INTEGER PRIMARY KEY, 
            placa TEXT UNIQUE, 
            veiculoProprio TEXT,
            ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Agora salva os veículos
        for v in lista_veiculos:
            cursor.execute('''
                INSERT INTO frota_erp (codVeiculo, placa, veiculoProprio, ultima_atualizacao)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(placa) DO UPDATE SET
                codVeiculo=excluded.codVeiculo,
                veiculoProprio=excluded.veiculoProprio,
                ultima_atualizacao=CURRENT_TIMESTAMP
            ''', (v.get('codVeiculo'), str(v.get('placa')).strip(), str(v.get('veiculoProprio')).strip()))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar frota no banco: {e}")
        return False
    
def obter_vinculo_veiculo(codigo_veiculo):
    """Busca o tipo de vínculo do veículo na base da frota"""
    import sqlite3
    try:
        # ATENÇÃO: A frota está salva no banco sistema_automacao.db
        conn = sqlite3.connect('sistema_automacao.db')
        c = conn.cursor()
        c.execute("SELECT veiculoProprio FROM frota_erp WHERE codVeiculo = ?", (codigo_veiculo,))
        resultado = c.fetchone()
        conn.close()
        
        if resultado:
            return str(resultado[0]).strip().upper()
        return ""
    except Exception as e:
        print(f"Erro ao buscar vínculo do veículo {codigo_veiculo}: {e}")
        return ""
    
# =======================================================
# FUNÇÕES PARA CONFIGURAÇÃO DOS CÓDIGOS DE COMBUSTÍVEL
# =======================================================
def criar_tabela_config_combustiveis():
    import sqlite3
    conn = sqlite3.connect('banco_nfe.db') 
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS config_combustiveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_etanol TEXT,
            cod_gasolina TEXT,
            cod_s10 TEXT,
            cod_s500 TEXT
        )
    ''')
    
    # Truque cirúrgico para adicionar a coluna do ARLA sem quebrar o banco antigo
    try:
        c.execute("ALTER TABLE config_combustiveis ADD COLUMN cod_arla TEXT")
    except sqlite3.OperationalError:
        pass # Se der erro, é porque a coluna já existe

    c.execute('SELECT count(*) FROM config_combustiveis')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO config_combustiveis (cod_etanol, cod_gasolina, cod_s10, cod_s500, cod_arla) VALUES ("", "", "", "", "")')
    conn.commit()
    conn.close()

def salvar_codigos_combustiveis(etanol, gasolina, s10, s500, arla):
    criar_tabela_config_combustiveis()
    import sqlite3
    conn = sqlite3.connect('banco_nfe.db')
    c = conn.cursor()
    c.execute('''
        UPDATE config_combustiveis 
        SET cod_etanol = ?, cod_gasolina = ?, cod_s10 = ?, cod_s500 = ?, cod_arla = ?
        WHERE id = 1
    ''', (etanol.strip(), gasolina.strip(), s10.strip(), s500.strip(), arla.strip()))
    conn.commit()
    conn.close()

def carregar_codigos_combustiveis():
    criar_tabela_config_combustiveis()
    import sqlite3
    try:
        conn = sqlite3.connect('banco_nfe.db')
        c = conn.cursor()
        c.execute('SELECT cod_etanol, cod_gasolina, cod_s10, cod_s500, cod_arla FROM config_combustiveis WHERE id = 1')
        res = c.fetchone()
        conn.close()
        if res:
            return {"etanol": res[0], "gasolina": res[1], "s10": res[2], "s500": res[3], "arla": res[4] if res[4] else ""}
    except:
        pass
    return {"etanol": "", "gasolina": "", "s10": "", "s500": "", "arla": ""}

def atualizar_estoque_nota(chave_nfe, valor_estoque):
    """Atualiza se a NFe vai para o estoque ou não"""
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE notas_raspadas SET nfe_estoque = ? WHERE chave_nfe = ?", (valor_estoque, chave_nfe))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar estoque: {e}")
        return False
    
def atualizar_arquiva_nota(chave_nfe, valor_arquiva):
    """Marca se a NFe está arquivada (robô ignora download e importação)."""
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notas_raspadas SET nfe_arquiva = ? WHERE chave_nfe = ?",
            (valor_arquiva, chave_nfe),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar arquiva: {e}")
        return False


def nota_erro_download_permanente(chave_nfe='', num_nota=''):
    """Erro de download/XML já registrado — não tentar baixar de novo."""
    chave = (chave_nfe or '').strip()
    num = str(num_nota or '').strip()
    if not chave and not num:
        return False
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        c = conn.cursor()
        if chave:
            c.execute(
                'SELECT status, erro_importacao FROM notas_raspadas WHERE chave_nfe = ?',
                (chave,),
            )
        else:
            c.execute(
                '''SELECT status, erro_importacao FROM notas_raspadas
                   WHERE num_nota = ? ORDER BY id DESC LIMIT 1''',
                (num,),
            )
        row = c.fetchone()
        conn.close()
        if not row or str(row[0] or '').strip().upper() != 'ERRO':
            return False
        erro = str(row[1] or '')
        if nota_erro_arquivo_indisponivel(erro):
            return True
        el = erro.lower()
        marcadores = (
            'sefaz', 'download', 'tentativas', 'consumo indevido', 'indispon',
            'rejeicao', 'rejeição', 'nao retornou', 'não retornou',
        )
        return any(m in el for m in marcadores)
    except Exception as e:
        print(f'Erro ao verificar download permanente: {e}')
        return False


def nota_encerrada_robo(chave_nfe='', num_nota=''):
    """
    Nota já tratada pelo robô: importada com código (finalizou) ou erro gravado.
    Evita ficar clicando Importar na mesma linha do painel.
    """
    chave = (chave_nfe or '').strip()
    num = str(num_nota or '').strip()
    if not chave and not num:
        return False, ''
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        c = conn.cursor()
        if chave:
            c.execute(
                'SELECT status, codigo_interno, erro_importacao FROM notas_raspadas WHERE chave_nfe = ?',
                (chave,),
            )
        else:
            c.execute(
                '''SELECT status, codigo_interno, erro_importacao FROM notas_raspadas
                   WHERE num_nota = ? ORDER BY id DESC LIMIT 1''',
                (num,),
            )
        row = c.fetchone()
        conn.close()
        if not row:
            return False, ''
        status = str(row[0] or '').strip().upper()
        codigo = str(row[1] or '').strip()
        erro = str(row[2] or '').strip()
        if status == 'IMPORTADO' and codigo:
            return True, f'importada (cód. {codigo})'
        if status == 'ERRO' and erro:
            return True, 'erro registrado'
        return False, ''
    except Exception as e:
        print(f'Erro ao verificar nota encerrada: {e}')
        return False, ''


def verificar_nota_arquiva(chave_nfe):
    """True se no painel a nota está arquivada (exceto Importado/Processado)."""
    if not chave_nfe or not str(chave_nfe).strip():
        return False
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        c = conn.cursor()
        c.execute(
            "SELECT nfe_arquiva, status FROM notas_raspadas WHERE chave_nfe = ?",
            (chave_nfe.strip(),),
        )
        row = c.fetchone()
        conn.close()
        if not row:
            return False
        status = str(row[1] or "").strip().upper()
        if status in ("IMPORTADO", "PROCESSADO"):
            return False
        return "☑" in str(row[0] or "")
    except Exception as e:
        print(f"Erro ao verificar arquiva: {e}")
        return False


def verificar_nota_estoque(chave_nfe):
    """Verifica se o usuário marcou a flag ☑ NFe p/ Estoque no painel"""
    import sqlite3
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        c = conn.cursor()
        c.execute("SELECT nfe_estoque FROM notas_raspadas WHERE chave_nfe = ?", (chave_nfe,))
        res = c.fetchone()
        conn.close()
        
        # Se o resultado existir e contiver o símbolo de marcado (☑), retorna True
        if res and res[0] and "☑" in res[0]:
            return True
    except Exception as e:
        print(f"Erro ao verificar estoque: {e}")
        
    return False

# =======================================================
# FUNÇÕES PARA O RELATÓRIO DE ITENS (CÓD. 118)
# =======================================================
def criar_tabela_itens():
    import sqlite3
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS itens_erp (
            codItemD TEXT PRIMARY KEY,
            descGrupoImp TEXT,
            descNegocioImp TEXT,
            descricao TEXT,
            ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def sincronizar_itens_erp(lista_itens):
    """Salva os itens baixados do Excel no Banco de Dados"""
    criar_tabela_itens()
    import sqlite3
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        
        for item in lista_itens:
            cursor.execute('''
                INSERT INTO itens_erp (codItemD, descGrupoImp, descNegocioImp, descricao, ultima_atualizacao)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(codItemD) DO UPDATE SET
                descGrupoImp=excluded.descGrupoImp,
                descNegocioImp=excluded.descNegocioImp,
                descricao=excluded.descricao,
                ultima_atualizacao=CURRENT_TIMESTAMP
            ''', (
                str(item.get('codItemD', '')).strip(), 
                str(item.get('descGrupoImp', '')).strip(), 
                str(item.get('descNegocioImp', '')).strip(), 
                str(item.get('descricao', '')).strip()
            ))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar itens no banco: {e}")
        return False

def obter_itens_erp():
    """Lê os itens do banco para preencher a tela"""
    criar_tabela_itens()
    import sqlite3
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT codItemD, descGrupoImp, descNegocioImp, descricao, ultima_atualizacao FROM itens_erp ORDER BY CAST(codItemD AS INTEGER) ASC")
        res = c.fetchall()
        conn.close()
        return [dict(row) for row in res]
    except Exception as e:
        print(f"Erro ao ler itens: {e}")
        return []

# =======================================================
# TABELA EXCLUSIVA PARA RELATÓRIOS (BLINDADA CONTRA DELETES)
# =======================================================
def criar_tabela_relatorios():
    import sqlite3
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS config_relatorios (
            id INTEGER PRIMARY KEY,
            rel_veiculo TEXT,
            rel_item TEXT,
            cod_grupo_item TEXT
        )
    ''')
    try:
        c.execute("ALTER TABLE config_relatorios ADD COLUMN cod_grupo_item TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def salvar_codigos_relatorios(rel_veic, rel_item, cod_grupo_item=""):
    criar_tabela_relatorios()
    import sqlite3
    conn = sqlite3.connect('sistema_automacao.db')
    c = conn.cursor()
    c.execute("DELETE FROM config_relatorios")
    c.execute(
        "INSERT INTO config_relatorios (id, rel_veiculo, rel_item, cod_grupo_item) VALUES (1, ?, ?, ?)",
        (rel_veic, rel_item, str(cod_grupo_item).strip()),
    )
    conn.commit()
    conn.close()

def carregar_codigos_relatorios():
    criar_tabela_relatorios()
    import sqlite3
    conn = sqlite3.connect('sistema_automacao.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM config_relatorios WHERE id=1")
    row = c.fetchone()
    conn.close()
    if row:
        dados = dict(row)
        dados['rel_veiculo'] = str(dados.get('rel_veiculo') or '').strip()
        dados['rel_item'] = str(dados.get('rel_item') or '').strip()
        dados['cod_grupo_item'] = str(dados.get('cod_grupo_item') or '').strip()
        return dados
    return {'rel_veiculo': '', 'rel_item': '', 'cod_grupo_item': ''}


def carregar_codigo_grupo_item_padrao():
    """Código ERP do grupo INDEFINIDO no cadastro de item (configurado em Filtros)."""
    cfg = carregar_codigos_relatorios()
    return str(cfg.get('cod_grupo_item') or '').strip()

def listar_notas_filtradas(dt_ini="", dt_fim="", cod="", status="Todos", nota="", limite=None):
    """Busca todas as notas e usa um atalho seguro: se não houver filtro, mostra tudo!"""
    import sqlite3
    from datetime import datetime
    
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 🚀 CORREÇÃO AQUI: Mudamos de 'notas_fiscais' para 'notas_raspadas'
        c.execute("SELECT * FROM notas_raspadas ORDER BY id DESC")
        todas_notas = [dict(row) for row in c.fetchall()]
        conn.close()

        # ==========================================
        # O GRANDE TRUQUE (ATALHO DE SEGURANÇA): 
        # Se você não preencheu nada, ele devolve tudo na hora e ignora a filtragem!
        # ==========================================
        if not dt_ini and not dt_fim and not cod and not nota and status == "Todos":
            if limite in (None, "", "Todos"):
                return todas_notas
            try:
                return todas_notas[:max(1, int(limite))]
            except Exception:
                return todas_notas

        notas_filtradas = []

        # Converte as datas digitadas na tela
        try: d_ini = datetime.strptime(dt_ini, "%d/%m/%Y").date() if len(dt_ini) == 10 else datetime.min.date()
        except: d_ini = datetime.min.date()
            
        try: d_fim = datetime.strptime(dt_fim, "%d/%m/%Y").date() if len(dt_fim) == 10 else datetime.max.date()
        except: d_fim = datetime.max.date()

        for r in todas_notas:
            # Filtro de Código
            val_cod = str(r.get('codigo_interno') or r.get('cod_interno') or '')
            if cod and cod.lower() not in val_cod.lower():
                continue

            # Filtro de Nota
            val_nota = str(r.get('num_nota') or r.get('nota') or '')
            if nota and nota.lower() not in val_nota.lower():
                continue

            # Filtro de Status
            val_status = str(r.get('status') or '')
            if status and status != "Todos" and status.upper() not in val_status.upper():
                continue

            # Filtro de Data Flexível
            if d_ini != datetime.min.date() or d_fim != datetime.max.date():
                data_str = str(r.get('data_em') or '').strip()[:10]
                if not data_str:
                    continue 
                    
                data_nota = None
                try:
                    if "/" in data_str: 
                        data_nota = datetime.strptime(data_str, "%d/%m/%Y").date()
                    elif "-" in data_str: 
                        data_nota = datetime.strptime(data_str, "%Y-%m-%d").date()
                except:
                    pass 
                    
                if data_nota:
                    if not (d_ini <= data_nota <= d_fim):
                        continue
                else:
                    continue

            # Se a nota passou em todos os filtros exigidos, ela entra na lista
            notas_filtradas.append(r)

        if limite in (None, "", "Todos"):
            return notas_filtradas
        try:
            return notas_filtradas[:max(1, int(limite))]
        except Exception:
            return notas_filtradas

    except Exception as e:
        print(f"Erro ao buscar/filtrar notas: {e}")
        return []