import asyncio
from pysnmp.hlapi.asyncio import *

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
            
            if partes[0] == 'rtg' and len(partes) == 3:
                road_index = int(partes[1])
                novo_rtg = int(partes[2])
                oid = f'1.3.6.1.3.2026.1.3.1.4.{road_index}'
                asyncio.run(enviar_comando_snmp(ip_sc, porta_sc, comunidade, oid, novo_rtg, Gauge32))
                
            elif partes[0] == 'o' and len(partes) == 3:
                road_index = int(partes[1])
                modo = int(partes[2])
                if modo not in [0, 1, 2]:
                    print("Erro: Modo de override inválido. Usa 0, 1 ou 2.")
                    continue
                oid = f'1.3.6.1.3.2026.1.4.1.2.{road_index}'
                asyncio.run(enviar_comando_snmp(ip_sc, porta_sc, comunidade, oid, modo, Integer32))
                
            elif partes[0] == 'alg' and len(partes) == 2:
                algo_id = int(partes[1])
                if algo_id not in [1, 2, 3, 4]:
                    print("Erro: Algoritmo inválido. Usa 1, 2, 3 ou 4.")
                    continue
                oid = '1.3.6.1.3.2026.1.1.6.0'
                asyncio.run(enviar_comando_snmp(ip_sc, porta_sc, comunidade, oid, algo_id, Integer32))
                
            else:
                print("Comando inválido. Revê as instruções acima.")
                
        except ValueError:
            print("Erro: Certifica-te de que os valores inseridos são números inteiros.")
        except KeyboardInterrupt:
            print("\nA encerrar a CMC...")
            break

if __name__ == "__main__":
    iniciar_cmc()