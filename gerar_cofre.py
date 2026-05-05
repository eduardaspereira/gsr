# ==============================================================================
# Ficheiro: gerar_cofre.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Script de inicialização da segurança criptográfica. 
#            Implementa a arquitetura KEK/DEK: gera a Chave Mestra (DEK) para 
#            as comunicações SNMP e protege-a num ficheiro físico ('seguranca.key')
#            utilizando uma chave derivada (KEK) gerada a partir da password 
#            do utilizador (via linha de comandos).
# ==============================================================================

import base64
import sys
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def configurar_cofre_seguranca():
    """
    Gera e tranca a chave de segurança criptográfica do sistema.
    Lê a password dos argumentos e aplica derivação PBKDF2HMAC.
    """
    # 1. Validação de Argumentos da Linha de Comandos
    if len(sys.argv) < 2:
        print("[ERRO] Falta a password!")
        print("Uso correto: python3 gerar_cofre.py <a_tua_password>")
        sys.exit(1)

    password_texto = sys.argv[1]
    password_bytes = password_texto.encode()

    # 2. Geração da KEK (Key Encryption Key)
    # Aplica PBKDF2HMAC com 100.000 iterações e Salt para mitigar ataques de força bruta
    salt = b'GSR_UM_2026'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    chave_cofre = base64.urlsafe_b64encode(kdf.derive(password_bytes))
    cifra_cofre = Fernet(chave_cofre)

    # 3. Geração da DEK (Data Encryption Key)
    # Esta é a verdadeira chave aleatória que será usada no Túnel Seguro SNMP
    chave_mestra_snmp = Fernet.generate_key()

    # 4. Encriptação e Armazenamento (Proteção em Repouso)
    # A chave SNMP é trancada com a KEK e guardada em disco de forma segura
    chave_encriptada = cifra_cofre.encrypt(chave_mestra_snmp)
    
    with open("seguranca.key", "wb") as ficheiro_chave:
        ficheiro_chave.write(chave_encriptada)

    # 5. Feedback no Terminal
    print("\n[SUCESSO] Ficheiro 'seguranca.key' gerado com sucesso! A chave está trancada.")
    print(f"-> A password usada foi: '{password_texto}'")
    print("-> Para arrancar o simulador ou a consola gráfica, usa:")
    print(f"   python3 sc.py {password_texto}\n")

if __name__ == "__main__":
    configurar_cofre_seguranca()