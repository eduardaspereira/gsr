import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

password = input("Define a password mestra para trancar as chaves: ").encode()

# Derivar uma chave forte a partir da password
salt = b'GSR_UM_2026' # Salt fixo para simplificar o projeto
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
chave_cofre = base64.urlsafe_b64encode(kdf.derive(password))
cofre_cipher = Fernet(chave_cofre)

# Gerar a nossa verdadeira Chave Secreta do SNMP
chave_snmp = Fernet.generate_key()

# Encriptar a chave SNMP com a chave do cofre e guardar em ficheiro
chave_encriptada = cofre_cipher.encrypt(chave_snmp)
with open("seguranca.key", "wb") as f:
    f.write(chave_encriptada)

print("Ficheiro 'seguranca.key' gerado com sucesso! A chave está trancada.")