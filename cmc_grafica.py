# Autores: [Os teus números/nomes]
# Descrição: CMC Visual - Gestor SNMPv2c para representação gráfica do cruzamento.

import asyncio
import time
import os
from pysnmp.hlapi.asyncio import *

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
    """Vai buscar os dados de todas as 8 vias do cruzamento via SNMP."""
    dados = {}
    transport = await UdpTransportTarget.create(('127.0.0.1', 1161))
    
    for via_id in range(1, 9):
        dados[via_id] = {'c': 0, 's': 1} # c = carros, s = cor do semáforo
        oid_carros = f'1.3.6.1.4.1.9999.1.1.2.1.6.{via_id}.0'
        oid_cor = f'1.3.6.1.4.1.9999.1.1.2.1.7.{via_id}.0'
        
        for key, oid in [('c', oid_carros), ('s', oid_cor)]:
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
        
        # Mapa ASCII formatado com as variáveis de cada via
        mapa = f"""
================= MAPA DO CRUZAMENTO [{time.strftime('%H:%M:%S')}] =================

                     NORTE
             Saída 5       Entrada 1
             Carros: {d[5]['c']:<2}    Carros: {d[1]['c']:<2}
               [{get_color_ansi(d[5]['s'])}]           [{get_color_ansi(d[1]['s'])}]
                 ^ ^           v v
                 | |           | |
OESTE  __________|_|___________|_|__________   ESTE
         < < [{get_color_ansi(d[8]['s'])}]                 Carros: {d[3]['c']:<2} Entrada 3
Saída 8  Carros: {d[8]['c']:<2}                   [{get_color_ansi(d[3]['s'])}] < < <
       -------------------------------------
Entrada 4        [{get_color_ansi(d[4]['s'])}]                 Carros: {d[7]['c']:<2} Saída 7
> > >    Carros: {d[4]['c']:<2}                   [{get_color_ansi(d[7]['s'])}] > > >
       __________   ___________   __________
                 | |           | |
                 | |           | |
                 v v           ^ ^
               [{get_color_ansi(d[6]['s'])}]           [{get_color_ansi(d[2]['s'])}]
             Carros: {d[6]['c']:<2}    Carros: {d[2]['c']:<2}
             Saída 6       Entrada 2
                      SUL

====================================================================
        """
        clear_console()
        print(mapa)
        await asyncio.sleep(2) # Atualiza a cada 2 segundos para ser fluido

async def main():
    snmp_engine = SnmpEngine()
    print("A iniciar interface gráfica do cruzamento...")
    await draw_map(snmp_engine)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCMC Gráfica terminada.")