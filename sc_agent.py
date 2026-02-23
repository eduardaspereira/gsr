# ==============================================================================
# Autores: 
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: sc_agent.py
# 
# Descrição: Implementa o Agente SNMPv2c do Sistema Central. Gere a base de dados
# em memória (MIB SMIv2) e integra os componentes SSFR e SD via multithreading.
#
# Variáveis Principais:
# - mib_instances: Dicionário que mapeia OIDs para objetos instanciados na MIB.
# - tempo_total_simulado: Contador global para gestão de eventos temporais.
# - vias_map: Mapeamento rápido de IDs para dados de configuração.
# ==============================================================================

import threading
import time
import json
import asyncio
from pysnmp.entity import engine, config
from pysnmp.proto import rfc1902
from pysnmp.entity.rfc3413 import context, cmdrsp
from pysnmp.carrier.asyncio.dgram import udp

import ssfr
import sistema_decisao 

class TrafficSystem:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            self.data = json.load(f)
        self.vias_map = {via['id']: via for via in self.data['vias']}
        self.snmp_engine = engine.SnmpEngine()
        self.mib_instances = {}

    def get_via(self, via_id):
        return self.vias_map.get(via_id)

    def run_simulation_loop(self):
        step = self.data.get('simulation_step', 5) # Passo sugerido
        amarelo_fixo = self.data.get('tempo_amarelo_fixo', 3)
        
        while True:
            # 1. Simulação física (SSFR) integrada 
            ssfr.simulate_step(self.data['vias'], self.get_via, step)
            
            # 2. Decisão inteligente (SD) integrada 
            sistema_decisao.calcular_decisao(self.data['vias'], amarelo_fixo, step)
            
            # 3. Atualização da MIB (Sincronização memória -> SNMP)
            for via in self.data['vias']:
                v_id = via['id']
                # Atualiza contagem, cor e temporizador na MIB 
                oids_to_update = {
                    f"1.3.6.1.4.1.9999.1.1.2.1.6.{v_id}": rfc1902.Gauge32(int(via['veiculos_atuais'])),
                    f"1.3.6.1.4.1.9999.1.1.2.1.7.{v_id}": rfc1902.Integer32(via['semaforo']['cor']) if 'semaforo' in via else None,
                    f"1.3.6.1.4.1.9999.1.1.2.1.8.{v_id}": rfc1902.Integer32(max(0, via['semaforo']['tempo_falta'])) if 'semaforo' in via else None
                }
                
                for oid, val in oids_to_update.items():
                    if val is not None and oid in self.mib_instances:
                        self.mib_instances[oid].setSyntax(val)

                # Sincronizacao inversa: le RGT da MIB para permitir alteracao externa 
                oid_rgt = f"1.3.6.1.4.1.9999.1.1.2.1.4.{v_id}"
                if oid_rgt in self.mib_instances:
                    via['rgt'] = int(self.mib_instances[oid_rgt].getSyntax())
                
            time.sleep(step)

    async def run_agent(self):
        config.add_transport(self.snmp_engine, udp.DOMAIN_NAME, udp.UdpAsyncioTransport().open_server_mode(('127.0.0.1', 1161)))
        config.add_v1_system(self.snmp_engine, 'my-area', 'public')
        config.add_vacm_user(self.snmp_engine, 2, 'my-area', 'noAuthNoPriv', readSubTree=(1,3,6), writeSubTree=(1,3,6))

        snmp_context = context.SnmpContext(self.snmp_engine)
        cmdrsp.GetCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.SetCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.NextCommandResponder(self.snmp_engine, snmp_context)
        mib_builder = snmp_context.get_mib_instrum().get_mib_builder()
        MibScalar, MibScalarInstance = mib_builder.import_symbols('SNMPv2-SMI', 'MibScalar', 'MibScalarInstance')

        # Instrumentação dinâmica da MIB baseada no Grafo 
        for via in self.data['vias']:
            v_id = via['id']
            # Criação de objetos da tabela de vias (roadTable) 
            cor_inicial = 1 if 'semaforo' in via else 2
            objs = [
                (2, rfc1902.OctetString(via['nome']), 'read-only'),   # roadName
                (4, rfc1902.Gauge32(int(via.get('rgt', 0))), 'read-write'), # roadRTG
                (5, rfc1902.Gauge32(via.get('capacidade', 100)), 'read-only'), # roadMaxCap
                (6, rfc1902.Gauge32(0), 'read-only'), # roadVehicleCount
                (7, rfc1902.Integer32(cor_inicial), 'read-only'), # roadLightColor
                (8, rfc1902.Integer32(0), 'read-only') # roadTimeRemaining
            ]
            for sub_id, val, access in objs:
                oid = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, sub_id, v_id)
                inst = MibScalarInstance(oid, (0,), val)
                mib_builder.export_symbols('TRAFFIC-MIB', **{f'obj_{sub_id}_{v_id}': MibScalar(oid, val).setMaxAccess(access), f'inst_{sub_id}_{v_id}': inst})
                self.mib_instances[f"1.3.6.1.4.1.9999.1.1.2.1.{sub_id}.{v_id}"] = inst

        print("SC iniciado na porta 1161. Pronto para monitorização CMC")
        while True: await asyncio.sleep(3600)

    def start(self):
        threading.Thread(target=self.run_simulation_loop, daemon=True).start()
        asyncio.run(self.run_agent())

if __name__ == "__main__":
    TrafficSystem('config.json').start()