import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

password = input("Define a password mestra para trancar as chaves: ").encode()

salt = b'GSR_UM_2026'
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
chave_cofre = base64.urlsafe_b64encode(kdf.derive(password))
cofre_cipher = Fernet(chave_cofre)

chave_snmp = Fernet.generate_key()

chave_encriptada = cofre_cipher.encrypt(chave_snmp)

# 1. Guarda o cofre (A chave da rede trancada)
with open("seguranca.key", "wb") as f:
    f.write(chave_encriptada)

# 2. Guarda o Segredo (A password) num ficheiro oculto para o sc.py ler
with open(".password_guardada.txt", "wb") as f:
    f.write(password)

print("Setup Concluído! Ficheiro 'seguranca.key' e segredo guardados com sucesso.")