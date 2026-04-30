import sqlite3
import os
import urllib.request
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import bcrypt
import secrets
import string

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
        email_senha_criptografada BLOB, email_ssl INTEGER, email_porta INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash TEXT UNIQUE, 
        data_insercao DATE, ultima_checagem DATE, status TEXT DEFAULT 'PENDENTE')''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Notas_Fiscais (
        id INTEGER PRIMARY KEY AUTOINCREMENT, numero_nf TEXT, status TEXT DEFAULT 'Pendente', data_registro DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS filtros_salvos (
        id INTEGER PRIMARY KEY, mes TEXT, ano TEXT)''')
        
    # TABELA ATUALIZADA COM AS DUAS NOVAS COLUNAS
    cursor.execute('''CREATE TABLE IF NOT EXISTS notas_raspadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT, fornecedor TEXT, num_nota TEXT, data_em TEXT,
        valor TEXT, sit_nfe TEXT, chave_nfe TEXT, filial TEXT, user_ins TEXT,
        codigo_interno TEXT, erro_importacao TEXT)''')

    # TRUQUE PARA ATUALIZAR O BANCO ANTIGO (Evita quebrar se o banco já existir)
    try:
        cursor.execute("ALTER TABLE notas_raspadas ADD COLUMN codigo_interno TEXT")
    except sqlite3.OperationalError:
        pass # Se der erro, é porque a coluna já existe
        
    try:
        cursor.execute("ALTER TABLE notas_raspadas ADD COLUMN erro_importacao TEXT")
    except sqlite3.OperationalError:
        pass # Se der erro, é porque a coluna já existe
    
    # Criação da tabela oficial da Frota
    cursor.execute('''CREATE TABLE IF NOT EXISTS frota_erp (
        codVeiculo INTEGER PRIMARY KEY, 
        placa TEXT UNIQUE, 
        veiculoProprio TEXT,
        ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Salva e SÓ AGORA fecha o banco!
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
# 3. MÓDULO DE LICENCIAMENTO (31 DIAS)
# ==========================================
def obter_data_segura():
    try:
        resposta = urllib.request.urlopen('http://google.com', timeout=3)
        data_str = resposta.headers['Date']
        return datetime.strptime(data_str, '%a, %d %b %Y %H:%M:%S %Z').date()
    except Exception:
        return datetime.now().date()

def gerar_lista_tokens(quantidade=100):
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    tokens = []
    for _ in range(quantidade):
        token = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        tokens.append(token)
        try: cursor.execute("INSERT INTO Tokens (token_hash) VALUES (?)", (token,))
        except: pass
    conn.commit()
    conn.close()
    return tokens

def ativar_token_31_dias(token_inserido):
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Tokens WHERE token_hash = ? AND status = 'PENDENTE'", (token_inserido,))
    if cursor.fetchone():
        hoje = obter_data_segura()
        cursor.execute("""UPDATE Tokens SET status = 'ATIVO', data_insercao = ?, ultima_checagem = ? WHERE token_hash = ?""", 
                       (hoje.strftime('%Y-%m-%d'), hoje.strftime('%Y-%m-%d'), token_inserido))
        conn.commit()
        conn.close()
        return True, "Token ativado com sucesso!"
    conn.close()
    return False, "Token inválido ou já utilizado."

def checar_status_licenca():
    """Retorna: (Status_Code, Dias_Restantes). Status: 1=OK, 0=Aviso(<=3 dias), -1=Bloqueado, -2=Fraude"""
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    cursor.execute("SELECT data_insercao, ultima_checagem FROM Tokens WHERE status = 'ATIVO' LIMIT 1")
    resultado = cursor.fetchone()
    
    if not resultado: return -1, 0 
    
    data_insercao = datetime.strptime(resultado[0], '%Y-%m-%d').date()
    ultima_checagem = datetime.strptime(resultado[1], '%Y-%m-%d').date() if resultado[1] else None
    data_expiracao = data_insercao + timedelta(days=31)
    hoje = obter_data_segura()

    if ultima_checagem and hoje < ultima_checagem: return -2, 0 

    cursor.execute("UPDATE Tokens SET ultima_checagem = ? WHERE status = 'ATIVO'", (hoje.strftime('%Y-%m-%d'),))
    conn.commit()
    conn.close()

    dias_restantes = (data_expiracao - hoje).days
    if dias_restantes <= 0: return -1, 0
    elif dias_restantes <= 3: return 0, dias_restantes
    else: return 1, dias_restantes

# ==========================================
# 4. MÓDULO DE CONFIGURAÇÕES E AUTOMAÇÃO
# ==========================================
def carregar_chave():
    return open("secret.key", "rb").read()

def salvar_configuracoes(link, user_sis, senha_sis, smtp, user_email, senha_email, ssl, porta):
    chave = carregar_chave()
    f = Fernet(chave)
    
    senha_sis_crypt = f.encrypt(senha_sis.encode()) if senha_sis else b""
    senha_email_crypt = f.encrypt(senha_email.encode()) if senha_email else b""
    
    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM Configuracoes WHERE id = 1")
    if cursor.fetchone():
        cursor.execute("""UPDATE Configuracoes SET link_sistema=?, usuario_sistema=?, senha_sistema_criptografada=?, 
                          email_smtp=?, email_usuario=?, email_senha_criptografada=?, email_ssl=?, email_porta=? WHERE id=1""",
                       (link, user_sis, senha_sis_crypt, smtp, user_email, senha_email_crypt, ssl, porta))
    else:
        cursor.execute("""INSERT INTO Configuracoes (id, link_sistema, usuario_sistema, senha_sistema_criptografada, 
                          email_smtp, email_usuario, email_senha_criptografada, email_ssl, email_porta) 
                          VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (link, user_sis, senha_sis_crypt, smtp, user_email, senha_email_crypt, ssl, porta))
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
            "ssl": row[7] if row[7] is not None else 1, "porta": row[8] or ""
        }
    return None

# --- Filtros ---
def salvar_filtros(mes, ano):
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM filtros_salvos") 
        cursor.execute("INSERT INTO filtros_salvos (mes, ano) VALUES (?, ?)", (mes, ano))
        conn.commit()
        conn.close()
        return True, "Período padrão salvo com sucesso!"
    except Exception as e:
        return False, f"Erro ao salvar filtros: {e}"

def carregar_filtros():
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        cursor.execute("SELECT mes, ano FROM filtros_salvos ORDER BY id DESC LIMIT 1")
        resultado = cursor.fetchone()
        conn.close()
        if resultado:
            return {"mes": resultado[0], "ano": resultado[1]}
        return None
    except:
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
            INSERT INTO notas_raspadas (status, fornecedor, num_nota, data_em, valor, sit_nfe, chave_nfe, filial, user_ins, codigo_interno, erro_importacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dados_nota.get('status', ''), dados_nota.get('fornecedor', ''), dados_nota.get('num_nota', ''), 
            dados_nota.get('data_em', ''), dados_nota.get('valor', ''), dados_nota.get('sit_nfe', ''), 
            dados_nota.get('chave_nfe', ''), dados_nota.get('filial', ''), dados_nota.get('user_ins', ''),
            dados_nota.get('codigo_interno', ''), dados_nota.get('erro_importacao', '')
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar nota no banco: {e}")
        return False

# ESTA FUNÇÃO É NOVA E É ELA QUE O ROBÔ VAI CHAMAR QUANDO DER ERRO OU SUCESSO!
def atualizar_nota_raspada(dados_nota):
    try:
        conn = sqlite3.connect('sistema_automacao.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notas_raspadas 
            SET status = ?, codigo_interno = ?, erro_importacao = ?
            WHERE chave_nfe = ?
        ''', (
            dados_nota.get('status', ''),
            dados_nota.get('codigo_interno', ''),
            dados_nota.get('erro_importacao', ''),
            dados_nota.get('chave_nfe', '')
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