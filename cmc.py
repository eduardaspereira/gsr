import base64, json
import getpass
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

print("=== INICIALIZAÇÃO SEGURA ===")
password = getpass.getpass("Introduz a password mestra para destrancar a chave: ").encode()

salt = b'GSR_UM_2026'
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
chave_cofre = base64.urlsafe_b64encode(kdf.derive(password))
cofre_cipher = Fernet(chave_cofre)

try:
    with open("seguranca.key", "rb") as f:
        chave_encriptada = f.read()
    CHAVE_SECRETA = cofre_cipher.decrypt(chave_encriptada)
    cipher = Fernet(CHAVE_SECRETA)
    print("Chave carregada com sucesso!")
except Exception:
    print("ERRO: Password incorreta ou ficheiro 'seguranca.key' em falta!")
    exit(1)

OID_TUNEL = "1.3.6.1.3.2026.99.1.0"
import asyncio
from pysnmp.hlapi.asyncio import *

async def enviar_comando_tunel(ip, porta, comunidade, payload_dict):
    snmpEngine = SnmpEngine()
    
    # 1. Empacotar e Encriptar
    payload_json = json.dumps(payload_dict).encode('utf-8')
    payload_encriptado = cipher.encrypt(payload_json)
    
    # 2. Enviar via SET no Túnel
    errorIndication, errorStatus, errorIndex, varBinds = await setCmd(
        snmpEngine,
        CommunityData(comunidade, mpModel=1),
        UdpTransportTarget((ip, porta)),
        ContextData(),
        ObjectType(ObjectIdentity(OID_TUNEL), OctetString(payload_encriptado))
    )

    if errorIndication or errorStatus:
        print("[Erro de Comunicação Segura] O pacote foi rejeitado ou falhou.")
    else:
        print("-> Comando seguro entregue com sucesso!")
        
    snmpEngine.transportDispatcher.closeDispatcher()

async def enviar_comando_snmp(ip, porta, comunidade, oid, valor, tipo_snmp):
    snmpEngine = SnmpEngine()
    
    # Executa o comando SNMP SET de forma assíncrona
    errorIndication, errorStatus, errorIndex, varBinds = await setCmd(
        snmpEngine,
        CommunityData(comunidade, mpModel=1), # SNMPv2c
        UdpTransportTarget((ip, porta)),
        ContextData(),
        ObjectType(ObjectIdentity(oid), tipo_snmp(valor))
    )

    if errorIndication:
        print(f"[Erro de Rede] {errorIndication} -> O SC (Sistema Central) está a correr?")
    elif errorStatus:
        print(f"[Erro SNMP] {errorStatus.prettyPrint()}")
    else:
        print(f"-> Sucesso! Comando enviado para a MIB.")
        
    snmpEngine.transportDispatcher.closeDispatcher()

def iniciar_cmc():
    print("=====================================================")
    print("      CMC: Consola de Monitorização e Controlo")
    print("=====================================================")
    print("Comandos disponíveis:")
    print("  rtg <via> <valor>  - Altera fluxo. Ex: rtg 101 10")
    print("  o <via> <modo>     - Override (0: Auto | 1: Vermelho | 2: Verde). Ex: o 101 2")
    print("  alg <modo>         - Algoritmo (1:RR | 2:Heurística | 3:RL | 4:BP). Ex: alg 3")
    print("  sair               - Termina a consola")
    print("=====================================================")
    
    ip_sc = "127.0.0.1"
    porta_sc = 16161
    comunidade = "public"
    

    while True:
        try:
            comando = input("\nCMC> ").strip().lower()
            
            if comando == 'sair':
                break
            if not comando:
                continue
                
            partes = comando.split()
            
            # --- RTG ---
            if partes[0] == 'rtg' and len(partes) == 3:
                road_index = int(partes[1])
                novo_rtg = int(partes[2])
                
                payload = {"comando": "SET_RTG", "via": road_index, "valor": novo_rtg}
                asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload))
                # Teste DDOS
                #for _ in range(5):
                #    asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload))

                
            # --- OVERRIDE ---
            elif partes[0] == 'o' and len(partes) == 3:
                road_index = int(partes[1])
                modo = int(partes[2])
                if modo not in [0, 1, 2]:
                    print("Erro: Modo de override inválido. Usa 0, 1 ou 2.")
                    continue
                
                payload = {"comando": "SET_OVERRIDE", "via": road_index, "modo": modo}
                asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload))
                
            # --- ALGORITMO ---
            elif partes[0] == 'alg' and len(partes) == 2:
                algo_id = int(partes[1])
                if algo_id not in [1, 2, 3, 4]:
                    print("Erro: Algoritmo inválido. Usa 1, 2, 3 ou 4.")
                    continue
                
                payload = {"comando": "SET_ALG", "alg_id": algo_id}
                asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload))
                
            else:
                print("Comando inválido. Revê as instruções acima.")
                
        except ValueError:
            print("Erro: Certifica-te de que os valores inseridos são números inteiros.")
        except KeyboardInterrupt:
            print("\nA encerrar a CMC...")
            break

if __name__ == "__main__":
    iniciar_cmc()