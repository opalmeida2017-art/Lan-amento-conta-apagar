import sqlite3
import database_setup as db

def criar_primeiro_usuario():
    print("=== CADASTRO DE ADMINISTRADOR ===")
    nome = input("Digite seu Nome: ")
    email = input("Digite seu E-mail: ")
    senha = input("Digite sua Senha: ")

    # Criptografa a senha antes de salvar (nunca salvamos em texto puro!)
    senha_hash = db.gerar_hash_senha(senha)

    conn = sqlite3.connect('sistema_automacao.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Usuarios (nome_completo, email, senha_hash) VALUES (?, ?, ?)",
                       (nome, email, senha_hash))
        conn.commit()
        print("\n[+] Usuário criado com sucesso! Você já pode fazer o login no sistema.")
    except sqlite3.IntegrityError:
        print("\n[-] Erro: Este e-mail já está cadastrado no banco de dados.")
    finally:
        conn.close()
        

if __name__ == "__main__":
    criar_primeiro_usuario()