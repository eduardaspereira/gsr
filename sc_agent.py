# ======================================================================================================
# Autores:
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: sc_agent.py
# Descrição: Atua como o Agente SNMPv2c do Sistema Central (SC). 
#           Carrega a configuração da rede a partir do config.json e instrumenta dinamicamente os objetos da MIB em memória. 
#           Gere a execução multithreaded que integra o simulador (SSFR) e o sistema de decisão (SD), 
#           garantindo a atualização dos valores das instâncias em quase tempo real.
# ===============================================================================

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
        step = self.data.get('simulation_step', 5)
        amarelo_fixo = self.data.get('tempo_amarelo_fixo', 3)
        cycles = 0
        
        while True:
            # 1. Simulação do fluxo rodoviário (SSFR)
            ssfr.simulate_step(self.data['vias'], self.get_via, step)
            
            # 2. Atualização dos tempos e decisão de cores (SD)
            sistema_decisao.calcular_decisao(self.data['vias'], amarelo_fixo, step)
            
            # 3. Atualização direta em memória da MIB
            for via in self.data['vias']:
                v_id = via['id']
                
                oid_key_veiculos = f"1.3.6.1.4.1.9999.1.1.2.1.6.{v_id}"
                if oid_key_veiculos in self.mib_instances:
                    self.mib_instances[oid_key_veiculos].setSyntax(rfc1902.Gauge32(int(via['veiculos_atuais'])))
                
                oid_key_cor = f"1.3.6.1.4.1.9999.1.1.2.1.7.{v_id}"
                if oid_key_cor in self.mib_instances and 'semaforo' in via:
                    self.mib_instances[oid_key_cor].setSyntax(rfc1902.Integer32(via['semaforo']['cor']))

                oid_key_tempo = f"1.3.6.1.4.1.9999.1.1.2.1.8.{v_id}"
                if oid_key_tempo in self.mib_instances and 'semaforo' in via:
                    self.mib_instances[oid_key_tempo].setSyntax(rfc1902.Integer32(max(0, via['semaforo']['tempo_falta'])))

                oid_key_rgt = f"1.3.6.1.4.1.9999.1.1.2.1.4.{v_id}"
                if oid_key_rgt in self.mib_instances:
                    via['rgt'] = int(self.mib_instances[oid_key_rgt].getSyntax())
                
                oid_key_total = f"1.3.6.1.4.1.9999.1.1.2.1.9.{v_id}"
                if oid_key_total in self.mib_instances:
                    self.mib_instances[oid_key_total].setSyntax(rfc1902.Counter32(int(via.get('total_passados', 0))))

                oid_key_avg_wait = f"1.3.6.1.4.1.9999.1.1.2.1.10.{v_id}"
                if oid_key_avg_wait in self.mib_instances:
                    self.mib_instances[oid_key_avg_wait].setSyntax(rfc1902.Gauge32(int(via.get('avg_wait_time', 0))))
                
            cycles += 1
            time.sleep(step)

    async def run_agent(self):
        config.add_transport(
            self.snmp_engine,
            udp.DOMAIN_NAME,
            udp.UdpAsyncioTransport().open_server_mode(('127.0.0.1', 1161))
        )
        # Configuração SNMPv2c sem segurança
        config.add_v1_system(self.snmp_engine, 'my-area', 'public')
        config.add_vacm_user(self.snmp_engine, 2, 'my-area', 'noAuthNoPriv', readSubTree=(1,3,6), writeSubTree=(1,3,6))

        snmp_context = context.SnmpContext(self.snmp_engine)
        cmdrsp.GetCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.SetCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.NextCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.BulkCommandResponder(self.snmp_engine, snmp_context)

        mib_builder = snmp_context.get_mib_instrum().get_mib_builder()
        MibScalar, MibScalarInstance = mib_builder.import_symbols('SNMPv2-SMI', 'MibScalar', 'MibScalarInstance')

        for via in self.data['vias']:
            v_id = via['id']
            
            # roadName (Read-Only)
            oid_name = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, 2, v_id)
            inst_name = MibScalarInstance(oid_name, (0,), rfc1902.OctetString(via['nome']))
            mib_builder.export_symbols('TRAFFIC-MIB', **{f'name_{v_id}': MibScalar(oid_name, rfc1902.OctetString()).setMaxAccess('read-only'), f'name_inst_{v_id}': inst_name})

            # roadMaxCapacity (Read-Only)
            oid_cap = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, 5, v_id)
            inst_cap = MibScalarInstance(oid_cap, (0,), rfc1902.Gauge32(via.get('capacidade', 100)))
            mib_builder.export_symbols('TRAFFIC-MIB', **{f'cap_{v_id}': MibScalar(oid_cap, rfc1902.Gauge32()).setMaxAccess('read-only'), f'cap_inst_{v_id}': inst_cap})

            # Instrumentação da roadLinkTable (Vias de Destino e Ritmos de Saída)
            if 'semaforo' in via and 'destinos' in via['semaforo']:
                for dest in via['semaforo']['destinos']:
                    d_id = dest['via_id']
                    # linkFlowRate (Read-Write)
                    oid_link = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 3, 1, 2, v_id, d_id)
                    inst_link = MibScalarInstance(oid_link, (0,), rfc1902.Gauge32(dest['ritmo_saida']))
                    mib_builder.export_symbols('TRAFFIC-MIB', **{f'link_{v_id}_{d_id}': MibScalar(oid_link, rfc1902.Gauge32()).setMaxAccess('read-write'), f'link_inst_{v_id}_{d_id}': inst_link})

            # roadRTG (Read-Write)
            oid_rgt = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, 4, v_id)
            inst_rgt = MibScalarInstance(oid_rgt, (0,), rfc1902.Gauge32(int(via.get('rgt', 0))))
            mib_builder.export_symbols('TRAFFIC-MIB', **{f'rtg_{v_id}': MibScalar(oid_rgt, rfc1902.Gauge32()).setMaxAccess('read-write'), f'rtg_inst_{v_id}': inst_rgt})
            self.mib_instances[f"1.3.6.1.4.1.9999.1.1.2.1.4.{v_id}"] = inst_rgt
            
            # roadVehicleCount (Read-Only)
            oid_veiculos = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, 6, v_id)
            inst_veiculos = MibScalarInstance(oid_veiculos, (0,), rfc1902.Gauge32(int(via.get('veiculos_atuais', 0))))
            mib_builder.export_symbols('TRAFFIC-MIB', **{f'veic_{v_id}': MibScalar(oid_veiculos, rfc1902.Gauge32()).setMaxAccess('read-only'), f'veic_inst_{v_id}': inst_veiculos})
            self.mib_instances[f"1.3.6.1.4.1.9999.1.1.2.1.6.{v_id}"] = inst_veiculos

            # roadLightColor (Read-Only)
            cor_inicial = via['semaforo']['cor'] if 'semaforo' in via else 1
            oid_cor = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, 7, v_id)
            inst_cor = MibScalarInstance(oid_cor, (0,), rfc1902.Integer32(cor_inicial))
            mib_builder.export_symbols('TRAFFIC-MIB', **{f'cor_{v_id}': MibScalar(oid_cor, rfc1902.Integer32()).setMaxAccess('read-only'), f'cor_inst_{v_id}': inst_cor})
            self.mib_instances[f"1.3.6.1.4.1.9999.1.1.2.1.7.{v_id}"] = inst_cor
            
            tempo_inicial = via['semaforo']['tempo_falta'] if 'semaforo' in via else 0
            oid_tempo = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, 8, v_id)
            inst_tempo = MibScalarInstance(oid_tempo, (0,), rfc1902.Integer32(tempo_inicial))
            mib_builder.export_symbols('TRAFFIC-MIB', **{f'tempo_{v_id}': MibScalar(oid_tempo, rfc1902.Integer32()).setMaxAccess('read-only'), f'tempo_inst_{v_id}': inst_tempo})
            self.mib_instances[f"1.3.6.1.4.1.9999.1.1.2.1.8.{v_id}"] = inst_tempo

            # roadTotalCarsPassed (Read-Only)
            oid_total = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, 9, v_id)
            inst_total = MibScalarInstance(oid_total, (0,), rfc1902.Counter32(int(via.get('total_passados', 0))))
            mib_builder.export_symbols('TRAFFIC-MIB', **{f'total_{v_id}': MibScalar(oid_total, rfc1902.Counter32()).setMaxAccess('read-only'), f'total_inst_{v_id}': inst_total})
            self.mib_instances[f"1.3.6.1.4.1.9999.1.1.2.1.9.{v_id}"] = inst_total

            # roadAverageWaitTime (Read-Only)
            oid_wait = (1, 3, 6, 1, 4, 1, 9999, 1, 1, 2, 1, 10, v_id)
            inst_wait = MibScalarInstance(oid_wait, (0,), rfc1902.Gauge32(int(via.get('avg_wait_time', 0))))
            mib_builder.export_symbols('TRAFFIC-MIB', **{f'wait_{v_id}': MibScalar(oid_wait, rfc1902.Gauge32()).setMaxAccess('read-only'), f'wait_inst_{v_id}': inst_wait})
            self.mib_instances[f"1.3.6.1.4.1.9999.1.1.2.1.10.{v_id}"] = inst_wait
            
        print("Sistema Central (SC) iniciado na porta 1161.")
        while True:
            await asyncio.sleep(3600)

    def start(self):
        sim_thread = threading.Thread(target=self.run_simulation_loop, daemon=True)
        sim_thread.start()
        try:
            asyncio.run(self.run_agent())
        except KeyboardInterrupt:
            print("\nSC terminado.")

if __name__ == "__main__":
    system = TrafficSystem('config.json')
    system.start()