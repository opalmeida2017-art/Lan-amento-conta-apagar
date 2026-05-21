import random
import string
import hashlib

PALAVRA_SECRETA = "AUTOMACAO_FROTA_SEFAZ_2026_MASTER"

def gerar_novo_token():
    """Gera um token seguro de 16 caracteres"""
    caracteres_base = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    assinatura_hash = hashlib.sha256((caracteres_base + PALAVRA_SECRETA).encode()).hexdigest()
    assinatura_final = assinatura_hash[:4].upper()
    token_cru = f"{caracteres_base}{assinatura_final}"
    return f"{token_cru[:4]}-{token_cru[4:8]}-{token_cru[8:12]}-{token_cru[12:]}"

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" 🔐 GERADOR DE LICENÇAS - SISTEMA DE AUTOMAÇÃO")
    print("="*50)
    
    quantidade = int(input("Quantos tokens de 31 dias você quer gerar? "))
    
    print("\nTokens Gerados:")
    for _ in range(quantidade):
        print(f"-> {gerar_novo_token()}")
        
    print("\nCopie um desses tokens e cole no aplicativo!")
    print("="*50 + "\n")