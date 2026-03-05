# ======================================================================================================
# Autores:
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: cmc_manager.py
# Descrição: Implementa a Consola de Monitorização e Controlo (CMC) como Gestor SNMPv2c.
#           Utiliza GETNEXT para SNMP Walk dinâmico e descoberta de vias ativas no agente.
#           Acede à MIB experimental (1.3.6.1.3.2026) para monitorização e controlo de RGT.
#           Apresenta dados da roadTable (.1.3.1) e trafficLightTable (.1.4.1) em formato tabular.
# ======================================================================================================

import asyncio
import time
import os
import json
from pysnmp.hlapi.asyncio import *

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def calcular_percentagens(config_file='config.json'):
    """Calcula as percentagens de distribuição dinâmica para cada via de destino."""
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    percentagens = {}
    
    # Percorre todas as vias de origem
    for via in config_data['vias']:
        if 'semaforo' in via:
            destinos = via['semaforo'].get('destinos', [])
            if len(destinos) > 1:  # Se tem múltiplos destinos
                total_ritmo = sum(d.get('ritmo_saida', 0) for d in destinos)
                if total_ritmo > 0:
                    for destino in destinos:
                        dest_id = destino['via_id']
                        ritmo = destino.get('ritmo_saida', 0)
                        percentagem = (ritmo / total_ritmo) * 100
                        percentagens[dest_id] = f"{percentagem:.1f}%"
    
    return percentagens

async def discover_vias(snmp_engine):
    """
    Realiza um SNMP WALK na coluna roadVehicleCount (1.3.6.1.3.2026.1.3.1.6)
    para descobrir dinamicamente todos os IDs das vias ativas no Sistema Central.
    """
    vias_descobertas = []
    base_oid_str = '1.3.6.1.3.2026.1.3.1.6'
    current_oid = ObjectType(ObjectIdentity(base_oid_str))
    
    transport = await UdpTransportTarget.create(('127.0.0.1', 1161))
    
    while True:
        errorIndication, errorStatus, errorIndex, varBinds = await next_cmd(
            snmp_engine,
            CommunityData('public', mpModel=1),
            transport,
            ContextData(),
            current_oid
        )
        
        if errorIndication or errorStatus or not varBinds:
            break
            
        name, val = varBinds[0]
        name_str = str(name)
        
        # Verifica se saímos da coluna correta na MIB usando manipulação de strings
        if not name_str.startswith(base_oid_str):
            break
            
        # O ID da via é o último número do OID (ex: 1.3.6.1.4.1.9999.1.1.2.1.6.4 -> ID 4)
        via_id = int(name_str.split('.')[-2])
        
        if via_id not in vias_descobertas:
            vias_descobertas.append(via_id)
            
        current_oid = ObjectType(name) # Prepara o próximo passo com o OID devolvido
        
    return vias_descobertas

async def fetch_via_data(snmp_engine, via_id):
    dados = {'veiculos': 0, 'cor': 1, 'rgt': 0, 'tempo': 0, 'total': 0, 'avg_wait': 0}
    oids = {
        'rgt':      f'1.3.6.1.3.2026.1.3.1.4.{via_id}.0',   # roadRTG
        'veiculos': f'1.3.6.1.3.2026.1.3.1.6.{via_id}.0',   # roadVehicleCount
        'total':    f'1.3.6.1.3.2026.1.3.1.7.{via_id}.0',   # roadTotalCarsPassed
        'avg_wait': f'1.3.6.1.3.2026.1.3.1.8.{via_id}.0',   # roadAverageWaitTime
        'cor':      f'1.3.6.1.3.2026.1.4.1.3.{via_id}.0',   # tlColor
        'tempo':    f'1.3.6.1.3.2026.1.4.1.4.{via_id}.0',   # tlTimeRemaining
    }
    
    transport = await UdpTransportTarget.create(('127.0.0.1', 1161))
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
                for name, val in varBinds:
                    dados[key] = int(val)
        except Exception:
            pass
    return dados

async def monitor_loop(snmp_engine):
    cores_map = {1: "VERMELHO", 2: "VERDE", 3: "AMARELO"}
    
    print("A iniciar descoberta dinâmica de vias (SNMP WALK)...")
    vias_ativas = await discover_vias(snmp_engine)
    
    # Calcula as percentagens dinâmicas uma vez no início
    percentagens = calcular_percentagens()
    
    while True:
        output = f"\n--- Tabela de Monitorização [{time.strftime('%H:%M:%S')}] ---\n"
        output += f"{'Via ID':<10} | {'Veículos':<10} | {'Cor Sinal':<12} | {'Tempo(s)':<9} | {'RGT':<6} | {'Passados':<10} | {'Espera(s)':<10} | {'Obs':<10}\n"
        output += "-" * 100 + "\n"
        
        for via_id in vias_ativas:
            dados = await fetch_via_data(snmp_engine, via_id)
            cor_str = cores_map.get(dados['cor'], "N/A")
            tipo = "(Sink)" if dados['rgt'] == 0 and dados['cor'] == 0 else ""
            
            # Observação: percentagem de distribuição se for via destino
            observacao = percentagens.get(via_id, "")
            
            output += f"{str(via_id) + ' ' + tipo:<10} | {dados['veiculos']:<10} | {cor_str:<12} | {dados['tempo']:<9} | {dados['rgt']:<6} | {dados['total']:<10} | {dados['avg_wait']:<10} | {observacao:<10}\n"
        
        clear_console()
        print(output)
        print("\nPara alterar o RGT, escreve: set <via_id> <novo_rgt> e pressiona Enter.")
        await asyncio.sleep(5)

async def set_rgt(snmp_engine, via_id, new_rgt):
    oid = f'1.3.6.1.3.2026.1.3.1.4.{via_id}.0'
    transport = await UdpTransportTarget.create(('127.0.0.1', 1161))
    errorIndication, errorStatus, errorIndex, varBinds = await set_cmd(
        snmp_engine,
        CommunityData('public', mpModel=1),
        transport,
        ContextData(),
        ObjectType(ObjectIdentity(oid), Gauge32(new_rgt))
    )
    if errorStatus:
        print(f"Erro ao atualizar RGT: {errorStatus.prettyPrint()}")

async def user_prompt(snmp_engine):
    loop = asyncio.get_running_loop()
    while True:
        user_input = await loop.run_in_executor(None, input, "")
        if user_input.startswith("set"):
            try:
                parts = user_input.split()
                if len(parts) == 3:
                    v_id, rgt = parts[1], parts[2]
                    await set_rgt(snmp_engine, int(v_id), int(rgt))
            except ValueError:
                pass

async def main():
    snmp_engine = SnmpEngine()
    asyncio.create_task(monitor_loop(snmp_engine))
    await user_prompt(snmp_engine)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass