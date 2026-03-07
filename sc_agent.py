# ==============================================================================
# Autores: 
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: sc_agent.py
# 
# Descrição: Implementa o Agente SNMPv2c do Sistema Central. Gere a base de dados
# em memória (MIB SMIv2) e integra os componentes SSFR e SD via multithreading.
#
# OID Base: 1.3.6.1.3.2026 (experimental.2026)
#   trafficGeneral: .1.1  (escalares)
#   crossroadTable: .1.2  (tabela de cruzamentos)
#   roadTable:      .1.3  (tabela de vias)
#   trafficLightTable: .1.4 (tabela de semáforos)
#   roadLinkTable:  .1.5  (tabela de ligações entre vias)
#
# Variáveis Principais:
# - mib_instances: Dicionário que mapeia OIDs para objetos instanciados na MIB.
# - stats: Dicionário global com estatísticas acumulativas (veículos entrados/saídos, tempo simulado).
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

# Prefixo OID base para a MIB experimental
OID_BASE = "1.3.6.1.3.2026"
OID_GENERAL = f"{OID_BASE}.1.1"       # trafficGeneral
OID_CROSSROAD = f"{OID_BASE}.1.2.1"   # crossroadEntry
OID_ROAD = f"{OID_BASE}.1.3.1"        # roadEntry
OID_TL = f"{OID_BASE}.1.4.1"          # trafficLightEntry
OID_LINK = f"{OID_BASE}.1.5.1"        # roadLinkEntry

# Tupla OID base para definicao de objetos
OID_BASE_T = (1, 3, 6, 1, 3, 2026)

class TrafficSystem:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            self.data = json.load(f)
        self.vias_map = {via['id']: via for via in self.data['vias']}
        self.snmp_engine = engine.SnmpEngine()
        self.mib_instances = {}
        # Construir link_map: (source_id, dest_id) -> link_id sequencial
        self.link_map = {}
        link_id = 1
        for via in self.data['vias']:
            if 'semaforo' not in via:
                continue
            for dest in via['semaforo'].get('destinos', []):
                self.link_map[(via['id'], dest['via_id'])] = link_id
                link_id += 1
        # Estatísticas globais acumulativas
        self.stats = {
            'elapsed_time': 0,
            'total_entered': 0,
            'total_exited': 0,
        }

    def get_via(self, via_id):
        return self.vias_map.get(via_id)

    def _update_mib_instance(self, oid_str, value):
        """Atualiza uma instância na MIB se existir."""
        if oid_str in self.mib_instances:
            self.mib_instances[oid_str].setSyntax(value)

    def _read_mib_instance(self, oid_str):
        """Lê o valor de uma instância da MIB."""
        if oid_str in self.mib_instances:
            return int(self.mib_instances[oid_str].getSyntax())
        return None

    def run_simulation_loop(self):
        step = self.data.get('simulation_step', 5)
        amarelo_fixo = self.data.get('tempo_amarelo_fixo', 3)
        algo_min = self.data.get('algo_min_green', 10)
        algo_max = self.data.get('algo_max_green', 60)
        
        while True:
            # 1. Simulação física (SSFR) integrada 
            step_stats = ssfr.simulate_step(self.data['vias'], self.get_via, step)
            self.stats['elapsed_time'] += step
            self.stats['total_entered'] += step_stats.get('entered', 0)
            self.stats['total_exited'] += step_stats.get('exited', 0)
            
            # 2. Leitura de parâmetros do algoritmo da MIB (permite alteração via SNMP)
            val = self._read_mib_instance(f"{OID_GENERAL}.8.0")
            if val is not None:
                algo_min = val
            val = self._read_mib_instance(f"{OID_GENERAL}.9.0")
            if val is not None:
                algo_max = val

            # 3. Decisão inteligente (SD) integrada 
            sistema_decisao.calcular_decisao(self.data['vias'], amarelo_fixo, step, algo_min, algo_max)
            
            # 4. Atualização da MIB — Escalares globais
            total_veiculos = sum(int(v.get('veiculos_atuais', 0)) for v in self.data['vias'])
            self._update_mib_instance(f"{OID_GENERAL}.3.0", rfc1902.Counter32(int(self.stats['elapsed_time'])))
            self._update_mib_instance(f"{OID_GENERAL}.4.0", rfc1902.Gauge32(total_veiculos))
            
            # Tempo médio de espera global (média ponderada das vias com semáforo)
            vias_com_semaforo = [v for v in self.data['vias'] if 'semaforo' in v]
            if vias_com_semaforo:
                avg_wait = sum(v.get('avg_wait_time', 0) for v in vias_com_semaforo) / len(vias_com_semaforo)
            else:
                avg_wait = 0
            self._update_mib_instance(f"{OID_GENERAL}.5.0", rfc1902.Gauge32(int(avg_wait)))
            self._update_mib_instance(f"{OID_GENERAL}.6.0", rfc1902.Counter32(int(self.stats['total_entered'])))
            self._update_mib_instance(f"{OID_GENERAL}.7.0", rfc1902.Counter32(int(self.stats['total_exited'])))

            # 5. Atualização da MIB — roadTable
            for via in self.data['vias']:
                v_id = via['id']
                self._update_mib_instance(f"{OID_ROAD}.6.{v_id}", rfc1902.Gauge32(int(via['veiculos_atuais'])))
                self._update_mib_instance(f"{OID_ROAD}.7.{v_id}", rfc1902.Counter32(int(via.get('total_cars_passed', 0))))
                self._update_mib_instance(f"{OID_ROAD}.8.{v_id}", rfc1902.Gauge32(int(via.get('avg_wait_time', 0))))

                # Sincronização inversa: lê RGT da MIB (permite alteração externa via CMC)
                val = self._read_mib_instance(f"{OID_ROAD}.4.{v_id}")
                if val is not None:
                    via['rgt'] = val

            # 6. Atualização da MIB — trafficLightTable
            for via in self.data['vias']:
                if 'semaforo' not in via:
                    continue
                v_id = via['id']
                self._update_mib_instance(f"{OID_TL}.3.{v_id}", rfc1902.Integer32(via['semaforo']['cor']))
                self._update_mib_instance(f"{OID_TL}.4.{v_id}", rfc1902.Integer32(max(0, int(via['semaforo']['tempo_falta']))))
                self._update_mib_instance(f"{OID_TL}.5.{v_id}", rfc1902.Integer32(int(via['semaforo'].get('green_duration', 0))))
                self._update_mib_instance(f"{OID_TL}.6.{v_id}", rfc1902.Integer32(int(via['semaforo'].get('red_duration', 0))))

            # 7. Atualização da MIB — roadLinkTable (linkCarsPassed)
            for via in self.data['vias']:
                if 'semaforo' not in via:
                    continue
                for dest in via['semaforo'].get('destinos', []):
                    lid = self.link_map.get((via['id'], dest['via_id']))
                    if lid is not None:
                        self._update_mib_instance(
                            f"{OID_LINK}.6.{lid}",
                            rfc1902.Counter32(int(dest.get('cars_passed', 0)))
                        )
                
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

        step = self.data.get('simulation_step', 5)
        amarelo_fixo = self.data.get('tempo_amarelo_fixo', 3)
        algo_min = self.data.get('algo_min_green', 10)
        algo_max = self.data.get('algo_max_green', 60)

        # --- Instrumentação dos Escalares (trafficGeneral) ---
        scalars = [
            (1, rfc1902.Integer32(1), 'read-write'),       # simStatus (running)
            (2, rfc1902.Integer32(step), 'read-write'),     # simStepDuration
            (3, rfc1902.Counter32(0), 'read-only'),         # simElapsedTime
            (4, rfc1902.Gauge32(0), 'read-only'),           # globalVehicleCount
            (5, rfc1902.Gauge32(0), 'read-only'),           # globalAvgWaitTime
            (6, rfc1902.Counter32(0), 'read-only'),         # totalVehiclesEntered
            (7, rfc1902.Counter32(0), 'read-only'),         # totalVehiclesExited
            (8, rfc1902.Integer32(algo_min), 'read-write'), # algoMinGreenTime
            (9, rfc1902.Integer32(algo_max), 'read-write'), # algoMaxGreenTime
            (10, rfc1902.Integer32(amarelo_fixo), 'read-only'), # algoYellowTime
        ]
        for sub_id, val, access in scalars:
            oid = OID_BASE_T + (1, 1, sub_id)
            inst = MibScalarInstance(oid, (0,), val)
            mib_builder.export_symbols(
                'TRAFFIC-MIB',
                **{f'scalar_{sub_id}': MibScalar(oid, val).setMaxAccess(access),
                   f'scalar_inst_{sub_id}': inst}
            )
            self.mib_instances[f"{OID_GENERAL}.{sub_id}.0"] = inst

        # --- Instrumentação da crossroadTable ---
        cruzamentos_unicos = set()
        for via in self.data['vias']:
            c_id = via.get('cruzamento')
            if c_id and c_id not in cruzamentos_unicos:
                cruzamentos_unicos.add(c_id)
                objs_cr = [
                    (2, rfc1902.Integer32(1), 'read-write'),  # crossroadMode (normal)
                    (3, rfc1902.Integer32(1), 'read-only'),   # crossroadRowStatus (active)
                ]
                for sub_id, val, access in objs_cr:
                    oid = OID_BASE_T + (1, 2, 1, sub_id, c_id)
                    inst = MibScalarInstance(oid, (0,), val)
                    mib_builder.export_symbols(
                        'TRAFFIC-MIB',
                        **{f'cr_{sub_id}_{c_id}': MibScalar(oid, val).setMaxAccess(access),
                           f'cr_inst_{sub_id}_{c_id}': inst}
                    )
                    self.mib_instances[f"{OID_CROSSROAD}.{sub_id}.{c_id}"] = inst

        # --- Instrumentação da roadTable ---
        tipo_map = {'normal': 1, 'sink': 2, 'source': 3}
        for via in self.data['vias']:
            v_id = via['id']
            tipo_val = tipo_map.get(via.get('tipo', 'normal'), 1)
            objs_road = [
                (2, rfc1902.OctetString(via['nome']), 'read-only'),            # roadName
                (3, rfc1902.Integer32(tipo_val), 'read-only'),                 # roadType
                (4, rfc1902.Gauge32(int(via.get('rgt', 0))), 'read-write'),    # roadRTG
                (5, rfc1902.Gauge32(via.get('capacidade', 100)), 'read-only'), # roadMaxCapacity
                (6, rfc1902.Gauge32(int(via.get('veiculos_atuais', 0))), 'read-only'), # roadVehicleCount
                (7, rfc1902.Counter32(0), 'read-only'),                        # roadTotalCarsPassed
                (8, rfc1902.Gauge32(0), 'read-only'),                          # roadAverageWaitTime
                (9, rfc1902.Integer32(1), 'read-only'),                        # roadRowStatus (active)
            ]
            for sub_id, val, access in objs_road:
                oid = OID_BASE_T + (1, 3, 1, sub_id, v_id)
                inst = MibScalarInstance(oid, (0,), val)
                mib_builder.export_symbols(
                    'TRAFFIC-MIB',
                    **{f'road_{sub_id}_{v_id}': MibScalar(oid, val).setMaxAccess(access),
                       f'road_inst_{sub_id}_{v_id}': inst}
                )
                self.mib_instances[f"{OID_ROAD}.{sub_id}.{v_id}"] = inst

        # --- Instrumentação da trafficLightTable ---
        eixo_map = {'NS': 1, 'EO': 2}
        for via in self.data['vias']:
            if 'semaforo' not in via:
                continue
            v_id = via['id']
            c_id = via.get('cruzamento', 0)
            eixo_val = eixo_map.get(via.get('eixo', 'NS'), 1)
            drain = via.get('drain_rate', 0)
            objs_tl = [
                (1, rfc1902.Integer32(c_id), 'read-only'),                       # tlCrossroadID
                (2, rfc1902.Integer32(eixo_val), 'read-only'),                   # tlAxis
                (3, rfc1902.Integer32(via['semaforo'].get('cor', 1)), 'read-only'), # tlColor
                (4, rfc1902.Integer32(max(0, via['semaforo'].get('tempo_falta', 0))), 'read-only'), # tlTimeRemaining
                (5, rfc1902.Integer32(0), 'read-only'),                          # tlGreenDuration
                (6, rfc1902.Integer32(0), 'read-only'),                          # tlRedDuration
                (7, rfc1902.Gauge32(drain), 'read-only'),                        # tlDrainRate
                (8, rfc1902.Integer32(1), 'read-only'),                          # tlRowStatus (active)
            ]
            for sub_id, val, access in objs_tl:
                oid = OID_BASE_T + (1, 4, 1, sub_id, v_id)
                inst = MibScalarInstance(oid, (0,), val)
                mib_builder.export_symbols(
                    'TRAFFIC-MIB',
                    **{f'tl_{sub_id}_{v_id}': MibScalar(oid, val).setMaxAccess(access),
                       f'tl_inst_{sub_id}_{v_id}': inst}
                )
                self.mib_instances[f"{OID_TL}.{sub_id}.{v_id}"] = inst

        # --- Instrumentação da roadLinkTable ---
        for via in self.data['vias']:
            if 'semaforo' not in via:
                continue
            for dest in via['semaforo'].get('destinos', []):
                link_id = self.link_map[(via['id'], dest['via_id'])]
                objs_link = [
                    (2, rfc1902.Integer32(via['id']), 'read-only'),                   # linkSourceIndex
                    (3, rfc1902.Integer32(dest['via_id']), 'read-only'),              # linkDestIndex
                    (4, rfc1902.Gauge32(dest.get('ritmo_saida', 0)), 'read-only'),   # linkFlowRate
                    (5, rfc1902.Integer32(1), 'read-only'),                           # linkActive
                    (6, rfc1902.Counter32(0), 'read-only'),                           # linkCarsPassed
                    (7, rfc1902.Integer32(1), 'read-only'),                           # linkRowStatus (active)
                ]
                for sub_id, val, access in objs_link:
                    oid = OID_BASE_T + (1, 5, 1, sub_id, link_id)
                    inst = MibScalarInstance(oid, (0,), val)
                    mib_builder.export_symbols(
                        'TRAFFIC-MIB',
                        **{f'link_{sub_id}_{link_id}': MibScalar(oid, val).setMaxAccess(access),
                           f'link_inst_{sub_id}_{link_id}': inst}
                    )
                    self.mib_instances[f"{OID_LINK}.{sub_id}.{link_id}"] = inst

        print("SC iniciado na porta 1161. Pronto para monitorização CMC")
        print(f"  MIB experimental: {OID_BASE}")
        print(f"  Vias instrumentadas: {len(self.data['vias'])}")
        print(f"  Cruzamentos: {len(cruzamentos_unicos)}")
        while True: await asyncio.sleep(3600)

    def start(self):
        threading.Thread(target=self.run_simulation_loop, daemon=True).start()
        asyncio.run(self.run_agent())

if __name__ == "__main__":
    TrafficSystem('config.json').start()