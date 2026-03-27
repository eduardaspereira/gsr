import asyncio
from pysnmp.hlapi.asyncio import *

async def alterar_rtg_async(ip, porta, comunidade, road_index, novo_rtg):
    # OID da coluna roadRTG na roadTable
    oid = f'1.3.6.1.3.2026.1.3.1.4.{road_index}'
    
    snmpEngine = SnmpEngine()
    
    # Executa o comando SNMP SET de forma assíncrona
    errorIndication, errorStatus, errorIndex, varBinds = await setCmd(
        snmpEngine,
        CommunityData(comunidade, mpModel=1), # mpModel=1 é SNMPv2c
        UdpTransportTarget((ip, porta)),
        ContextData(),
        ObjectType(ObjectIdentity(oid), Gauge32(novo_rtg))
    )

    if errorIndication:
        print(f"[Erro de Rede] {errorIndication} -> O Sistema Central (SC) está a correr?")
    elif errorStatus:
        print(f"[Erro SNMP] {errorStatus.prettyPrint()}")
    else:
        print(f"Sucesso! O RTG da via {road_index} foi atualizado para {novo_rtg} veículos/minuto.")
        
    snmpEngine.transportDispatcher.closeDispatcher()

def iniciar_cmc():
    print("=== CMC: Consola de Monitorização e Controlo ===")
    print("Comandos disponíveis:")
    print("  rtg <id_via> <novo_valor>  - Ex: rtg 1 10")
    print("  sair                       - Termina a consola")
    
    ip_sc = "127.0.0.1"
    porta_sc = 16161
    comunidade = "public"

    while True:
        try:
            comando = input("\nCMC> ").strip().lower()
            
            if comando == 'sair':
                break
            
            partes = comando.split()
            
            if len(partes) == 3 and partes[0] == 'rtg':
                road_index = int(partes[1])
                novo_rtg = int(partes[2])
                
                # Executa o pedido à rede e espera pela resposta
                asyncio.run(alterar_rtg_async(ip_sc, porta_sc, comunidade, road_index, novo_rtg))
            elif comando != '':
                print("Comando inválido. Usa o formato: rtg <id_via> <novo_valor>")
                
        except ValueError:
            print("Erro: O ID da via e o novo valor do RTG têm de ser números inteiros.")
        except KeyboardInterrupt:
            print("\nA encerrar a CMC...")
            break

if __name__ == "__main__":
    iniciar_cmc()