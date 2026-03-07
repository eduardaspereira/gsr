# ======================================================================================================
# Autores:
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: cmc_grafica.py
# 
# Descrição: Gestor SNMP auxiliar focado na visualização visual da rede urbana.
#            Realiza pedidos GET periódicos para monitorizar o número de veículos e o estado dos semáforos. 
#            Mapeia a topologia definida no config.json, utilizando códigos ANSI para desenhar um 
#            mapa ASCII dinâmico que ilustra o fluxo de tráfego entre cruzamentos em tempo real.
# ========================================================================================================

import asyncio
import time
import os
from pysnmp.hlapi.asyncio import *

# OID base: experimental(3).trafficMgmtMIB(2026).trafficObjects(1)
OID_ROAD_ENTRY   = '1.3.6.1.3.2026.1.3.1'   # roadEntry
OID_TL_ENTRY     = '1.3.6.1.3.2026.1.4.1'   # trafficLightEntry

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_color_ansi(color_code):
    """Converte o valor da MIB num bloco de cor ANSI para o terminal."""
    if color_code == 1:
        return "\033[91m██\033[0m" # Vermelho
    elif color_code == 2:
        return "\033[92m██\033[0m" # Verde
    elif color_code == 3:
        return "\033[93m██\033[0m" # Amarelo
    return "  "

async def fetch_all_vias(snmp_engine):
    """Vai buscar os dados das vias específicas do nosso config.json atual."""
    dados = {}
    transport = await UdpTransportTarget.create(('127.0.0.1', 1161))
    
    # Lista de IDs conforme o config.json (vias e sumidouros)
    vias_ids = [1, 2, 3, 4, 97, 98, 99]
    
    for via_id in vias_ids:
        # Sumidouros 97-99 não têm semáforo, logo cor Verde 2 por defeito
        dados[via_id] = {'c': 0, 's': 2} 
        
        oids = {
            'c': f'{OID_ROAD_ENTRY}.6.{via_id}.0',   # roadVehicleCount
            's': f'{OID_TL_ENTRY}.3.{via_id}.0'       # tlColor
        }
        
        for key, oid in oids.items():
            try:
                errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
                    snmp_engine,
                    CommunityData('public', mpModel=1),
                    transport,
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
                if not errorIndication and not errorStatus:
                    dados[via_id][key] = int(varBinds[0][1])
            except Exception:
                pass
    return dados

async def draw_map(snmp_engine):
    while True:
        d = await fetch_all_vias(snmp_engine)
        
        # Mapeamento Visual da Topologia:
        # Via 1 -> Via 2 -> Sumidouro 99 (Eixo Norte-Sul)
        # Via 3 -> Sumidouro 98 (Eixo Este-Oeste Cruzamento 1)
        # Via 4 -> Sumidouro 97 (Eixo Este-Oeste Cruzamento 2)
        
        mapa = f"""
================= MAPA DO CRUZAMENTO [{time.strftime('%H:%M:%S')}] =================

           CRUZAMENTO 1 (Norte)                           CRUZAMENTO 2 (Sul)
           --------------------                         ------------------
                 ENTRADA 1                                   VIA 2
                Carros: {d[1]['c']:<2}                                  Carros: {d[2]['c']:<2}
                   [{get_color_ansi(d[1]['s'])}]                                      [{get_color_ansi(d[2]['s'])}]
                    v v                                       v v
                    | |                                       | |
    Rua 3   ________|_|________ Saída 98      Rua 4   ________|_|________ Saída 99
    ----->  [{get_color_ansi(d[3]['s'])}]  {d[3]['c']:<2}      ----->      ----->  [{get_color_ansi(d[4]['s'])}]  {d[4]['c']:<2}      ----->
    In: {d[3]['c']:<2}  ________   ________ Out:{d[98]['c']:<2}      In: {d[4]['c']:<2}  ________   ________ Out:{d[99]['c']:<2}
                    | |                                     | |
                    | |                                     | |
                    v v                                     v v
                  Saída 2                                  Saída 97
                Carros: {d[2]['c']:<2}                                 Carros: {d[97]['c']:<2}

====================================================================
Legenda: Entrada 1 -> Via 2 -> Sumidouro 97 (Avenida Principal / Onda Verde)
Para simular Onda Verde, aumenta o RGT da Via 1 (ex: set 1 60).
        """
        clear_console()
        print(mapa)
        await asyncio.sleep(2)

async def main():
    snmp_engine = SnmpEngine()
    print("A iniciar interface gráfica do cruzamento (Onda Verde)...")
    await draw_map(snmp_engine)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCMC Gráfica terminada.")