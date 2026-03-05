# ==============================================================================
# Autores: 
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: sc_agent.py
# 
# Descrição: Implementa o Agente SNMPv2c do Sistema Central (SC). Gere a base
# de dados em memória (MIB SMIv2 experimental) e integra os componentes SSFR
# e SD via multithreading. A MIB está registada sob o OID experimental
# 1.3.6.1.3.2026 (iso.org.dod.internet.experimental.2026).
#
# Tabelas Instrumentadas:
# - trafficGeneral (1.3.6.1.3.2026.1.1): Objetos escalares de controlo
# - crossroadTable (1.3.6.1.3.2026.1.2): Cruzamentos
# - roadTable      (1.3.6.1.3.2026.1.3): Vias rodoviárias (objeto principal)
# - trafficLightTable (1.3.6.1.3.2026.1.4): Semáforos e temporização
# - roadLinkTable  (1.3.6.1.3.2026.1.5): Ligações entre vias com ritmos
#
# Variáveis Principais:
# - mib_instances: Dicionário que mapeia OIDs (string) para instâncias MIB.
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

# ==============================================================================
# Constantes OID — MIB experimental (1.3.6.1.3.2026)
# ==============================================================================
OID_BASE = "1.3.6.1.3.2026.1"

# Escalares (trafficGeneral — .1.1.x)
OID_SIM_STATUS       = f"{OID_BASE}.1.1"
OID_SIM_STEP         = f"{OID_BASE}.1.2"
OID_GLOBAL_VEHICLES  = f"{OID_BASE}.1.3"
OID_ALGO_MIN_GREEN   = f"{OID_BASE}.1.4"
OID_ALGO_YELLOW      = f"{OID_BASE}.1.5"
OID_TOTAL_ROADS      = f"{OID_BASE}.1.6"
OID_TOTAL_CROSSROADS = f"{OID_BASE}.1.7"

# Prefixos de colunas tabulares
OID_CROSSROAD = f"{OID_BASE}.2.1"   # crossroadEntry
OID_ROAD      = f"{OID_BASE}.3.1"   # roadEntry
OID_TL        = f"{OID_BASE}.4.1"   # trafficLightEntry
OID_LINK      = f"{OID_BASE}.5.1"   # roadLinkEntry


def oid_tuple(oid_str):
    """Converte string OID para tuplo (usado pelo pysnmp)."""
    return tuple(int(x) for x in oid_str.split('.'))


class TrafficSystem:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            self.data = json.load(f)
        self.vias_map = {via['id']: via for via in self.data['vias']}
        self.snmp_engine = engine.SnmpEngine()
        self.mib_instances = {}
        self.tempo_total_simulado = 0

    def get_via(self, via_id):
        return self.vias_map.get(via_id)

    # ------------------------------------------------------------------
    # Registo de instâncias MIB
    # ------------------------------------------------------------------
    def _register(self, mib_builder, MibScalar, MibScalarInstance,
                  oid_str, val, access, sym):
        """Regista um par MibScalar/MibScalarInstance na MIB."""
        oid = oid_tuple(oid_str)
        inst = MibScalarInstance(oid, (0,), val)
        mib_builder.export_symbols(
            'TRAFFIC-MGMT-MIB',
            **{f'{sym}_obj': MibScalar(oid, val).setMaxAccess(access),
               f'{sym}_inst': inst}
        )
        self.mib_instances[oid_str] = inst

    def _update(self, oid_str, val):
        """Atualiza o valor de uma instância MIB existente."""
        if oid_str in self.mib_instances:
            self.mib_instances[oid_str].setSyntax(val)

    # ------------------------------------------------------------------
    # Loop principal da simulação (SSFR + SD integrados)
    # ------------------------------------------------------------------
    def run_simulation_loop(self):
        step = self.data.get('simulation_step', 5)
        amarelo_fixo = self.data.get('tempo_amarelo_fixo', 3)
        algo_min_green = self.data.get('algo_min_green_time', 10)

        while True:
            # 1. Lê algoMinGreenTime da MIB (permite alteração externa via SET)
            if OID_ALGO_MIN_GREEN in self.mib_instances:
                algo_min_green = int(self.mib_instances[OID_ALGO_MIN_GREEN].getSyntax())

            # 2. Simulação física (SSFR) integrada no SC
            ssfr.simulate_step(self.data['vias'], self.get_via, step)

            # 3. Decisão inteligente (SD) integrada no SC
            sistema_decisao.calcular_decisao(
                self.data['vias'], amarelo_fixo, step, algo_min_green
            )

            # 4. Gestão de Eventos temporais (Ex: Hora de Ponta)
            self.tempo_total_simulado += step
            for evento in self.data.get('eventos_rgt', []):
                if self.tempo_total_simulado == evento['tempo_simulacao']:
                    via = self.get_via(evento['via_id'])
                    if via:
                        via['rgt'] = evento['novo_rgt']
                        print(f"[EVENTO] {evento['descricao']} na Via {via['id']}")

            # 5. Sincronização memória → MIB SNMP
            self._sync_mib()

            time.sleep(step)

    # ------------------------------------------------------------------
    # Sincronização de todos os valores da memória para instâncias SNMP
    # ------------------------------------------------------------------
    def _sync_mib(self):
        """Sincroniza o estado interno do SC com as instâncias da MIB."""

        # --- Escalares ---
        total = sum(int(v.get('veiculos_atuais', 0)) for v in self.data['vias'])
        self._update(OID_GLOBAL_VEHICLES, rfc1902.Gauge32(total))

        # --- roadTable (.1.3.1) ---
        for via in self.data['vias']:
            v = via['id']
            self._update(f"{OID_ROAD}.6.{v}",
                         rfc1902.Gauge32(int(via.get('veiculos_atuais', 0))))
            self._update(f"{OID_ROAD}.7.{v}",
                         rfc1902.Counter32(int(via.get('total_passados', 0))))
            self._update(f"{OID_ROAD}.8.{v}",
                         rfc1902.Gauge32(int(via.get('avg_wait_time', 0))))

            # Sincronização Inversa: Lê RGT da MIB para alteração externa via CMC
            k = f"{OID_ROAD}.4.{v}"
            if k in self.mib_instances:
                via['rgt'] = int(self.mib_instances[k].getSyntax())

        # --- trafficLightTable (.1.4.1) ---
        for via in self.data['vias']:
            if 'semaforo' not in via:
                continue
            v = via['id']
            sem = via['semaforo']
            self._update(f"{OID_TL}.3.{v}",
                         rfc1902.Integer32(sem['cor']))
            self._update(f"{OID_TL}.4.{v}",
                         rfc1902.Integer32(max(0, sem.get('tempo_falta', 0))))
            self._update(f"{OID_TL}.5.{v}",
                         rfc1902.Integer32(sem.get('green_duration', 20)))
            self._update(f"{OID_TL}.6.{v}",
                         rfc1902.Integer32(sem.get('red_duration', 0)))

        # --- roadLinkTable (.1.5.1) ---
        for via in self.data['vias']:
            if 'semaforo' not in via:
                continue
            v = via['id']
            for dest in via['semaforo'].get('destinos', []):
                d = dest['via_id']
                link_key = f"{v}_{d}"
                cars = int(via.get('link_cars_passed', {}).get(link_key, 0))
                self._update(f"{OID_LINK}.4.{v}.{d}",
                             rfc1902.Counter32(cars))

    # ------------------------------------------------------------------
    # Arranque do agente SNMP
    # ------------------------------------------------------------------
    async def run_agent(self):
        # Transporte UDP e comunidade SNMPv2c
        config.add_transport(
            self.snmp_engine, udp.DOMAIN_NAME,
            udp.UdpAsyncioTransport().open_server_mode(('127.0.0.1', 1161))
        )
        config.add_v1_system(self.snmp_engine, 'my-area', 'public')
        config.add_vacm_user(
            self.snmp_engine, 2, 'my-area', 'noAuthNoPriv',
            readSubTree=(1, 3, 6), writeSubTree=(1, 3, 6)
        )

        snmp_context = context.SnmpContext(self.snmp_engine)
        cmdrsp.GetCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.SetCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.NextCommandResponder(self.snmp_engine, snmp_context)
        cmdrsp.BulkCommandResponder(self.snmp_engine, snmp_context)

        mib_builder = snmp_context.get_mib_instrum().get_mib_builder()
        MibScalar, MibScalarInstance = mib_builder.import_symbols(
            'SNMPv2-SMI', 'MibScalar', 'MibScalarInstance'
        )

        # --- Instrumentação completa da MIB ---
        self._instrument_scalars(mib_builder, MibScalar, MibScalarInstance)
        self._instrument_crossroads(mib_builder, MibScalar, MibScalarInstance)
        self._instrument_roads(mib_builder, MibScalar, MibScalarInstance)
        self._instrument_traffic_lights(mib_builder, MibScalar, MibScalarInstance)
        self._instrument_links(mib_builder, MibScalar, MibScalarInstance)

        n_vias = len(self.data['vias'])
        n_cruz = len(self.data.get('cruzamentos', []))
        n_links = sum(
            len(v['semaforo'].get('destinos', []))
            for v in self.data['vias'] if 'semaforo' in v
        )
        print(f"SC iniciado na porta 1161 (OID base: 1.3.6.1.3.2026)")
        print(f"  Vias: {n_vias}, Cruzamentos: {n_cruz}, Ligações: {n_links}")
        print(f"  Pronto para monitorização CMC.")

        while True:
            await asyncio.sleep(3600)

    # ------------------------------------------------------------------
    # Instrumentação: Escalares (trafficGeneral .1.1.x)
    # ------------------------------------------------------------------
    def _instrument_scalars(self, mb, MS, MSI):
        step = self.data.get('simulation_step', 5)
        amarelo = self.data.get('tempo_amarelo_fixo', 3)
        min_green = self.data.get('algo_min_green_time', 10)
        n_vias = len(self.data['vias'])
        n_cruz = len(self.data.get('cruzamentos', []))

        for oid_str, val, access, sym in [
            (OID_SIM_STATUS,       rfc1902.Integer32(1),          'read-write', 'simSt'),
            (OID_SIM_STEP,         rfc1902.Integer32(step),       'read-write', 'simStep'),
            (OID_GLOBAL_VEHICLES,  rfc1902.Gauge32(0),            'read-only',  'globVeh'),
            (OID_ALGO_MIN_GREEN,   rfc1902.Integer32(min_green),  'read-write', 'minGrn'),
            (OID_ALGO_YELLOW,      rfc1902.Integer32(amarelo),    'read-only',  'yellow'),
            (OID_TOTAL_ROADS,      rfc1902.Gauge32(n_vias),       'read-only',  'totRds'),
            (OID_TOTAL_CROSSROADS, rfc1902.Gauge32(n_cruz),       'read-only',  'totCr'),
        ]:
            self._register(mb, MS, MSI, oid_str, val, access, sym)

    # ------------------------------------------------------------------
    # Instrumentação: crossroadTable (.1.2.1)
    # ------------------------------------------------------------------
    def _instrument_crossroads(self, mb, MS, MSI):
        for cruz in self.data.get('cruzamentos', []):
            c = cruz['id']
            self._register(mb, MS, MSI,
                f"{OID_CROSSROAD}.2.{c}",
                rfc1902.Integer32(cruz.get('mode', 1)),
                'read-write', f'crM_{c}')
            self._register(mb, MS, MSI,
                f"{OID_CROSSROAD}.3.{c}",
                rfc1902.Integer32(1),  # active(1)
                'read-only', f'crRS_{c}')

    # ------------------------------------------------------------------
    # Instrumentação: roadTable (.1.3.1) — Objeto principal
    # ------------------------------------------------------------------
    def _instrument_roads(self, mb, MS, MSI):
        tipo_map = {'normal': 1, 'sink': 2, 'source': 3}
        for via in self.data['vias']:
            v = via['id']
            tipo = tipo_map.get(via.get('tipo', 'normal'), 1)
            for col, val, acc, sym in [
                (2, rfc1902.OctetString(via.get('nome', '')),
                    'read-only',  f'rNm_{v}'),
                (3, rfc1902.Integer32(tipo),
                    'read-only',  f'rTp_{v}'),
                (4, rfc1902.Gauge32(int(via.get('rgt', 0))),
                    'read-write', f'rRTG_{v}'),
                (5, rfc1902.Gauge32(int(via.get('capacidade', 100))),
                    'read-only',  f'rCap_{v}'),
                (6, rfc1902.Gauge32(int(via.get('veiculos_atuais', 0))),
                    'read-only',  f'rVeh_{v}'),
                (7, rfc1902.Counter32(0),
                    'read-only',  f'rPas_{v}'),
                (8, rfc1902.Gauge32(0),
                    'read-only',  f'rWt_{v}'),
                (9, rfc1902.Integer32(1),
                    'read-only',  f'rRS_{v}'),
            ]:
                self._register(mb, MS, MSI,
                    f"{OID_ROAD}.{col}.{v}", val, acc, sym)

    # ------------------------------------------------------------------
    # Instrumentação: trafficLightTable (.1.4.1) — Semáforos
    # ------------------------------------------------------------------
    def _instrument_traffic_lights(self, mb, MS, MSI):
        axis_map = {'NS': 1, 'EO': 2}
        for via in self.data['vias']:
            if 'semaforo' not in via:
                continue
            v = via['id']
            sem = via['semaforo']
            for col, val, acc, sym in [
                (1, rfc1902.Integer32(via.get('cruzamento', 0)),
                    'read-only',  f'tlCr_{v}'),
                (2, rfc1902.Integer32(axis_map.get(via.get('eixo', 'NS'), 1)),
                    'read-only',  f'tlAx_{v}'),
                (3, rfc1902.Integer32(sem.get('cor', 1)),
                    'read-only',  f'tlCo_{v}'),
                (4, rfc1902.Integer32(sem.get('tempo_falta', 0)),
                    'read-only',  f'tlRm_{v}'),
                (5, rfc1902.Integer32(sem.get('green_duration', 20)),
                    'read-only',  f'tlGD_{v}'),
                (6, rfc1902.Integer32(sem.get('red_duration', 0)),
                    'read-only',  f'tlRD_{v}'),
                (7, rfc1902.Integer32(1),
                    'read-only',  f'tlRS_{v}'),
            ]:
                self._register(mb, MS, MSI,
                    f"{OID_TL}.{col}.{v}", val, acc, sym)

    # ------------------------------------------------------------------
    # Instrumentação: roadLinkTable (.1.5.1) — Ligações entre vias
    # ------------------------------------------------------------------
    def _instrument_links(self, mb, MS, MSI):
        for via in self.data['vias']:
            if 'semaforo' not in via:
                continue
            v = via['id']
            for dest in via['semaforo'].get('destinos', []):
                d = dest['via_id']
                for col, val, acc, sym in [
                    (2, rfc1902.Gauge32(int(dest.get('ritmo_saida', 0))),
                        'read-only',  f'lFR_{v}_{d}'),
                    (3, rfc1902.Integer32(1),   # active(1)
                        'read-only',  f'lAc_{v}_{d}'),
                    (4, rfc1902.Counter32(0),
                        'read-only',  f'lCP_{v}_{d}'),
                    (5, rfc1902.Integer32(1),   # active(1)
                        'read-only',  f'lRS_{v}_{d}'),
                ]:
                    self._register(mb, MS, MSI,
                        f"{OID_LINK}.{col}.{v}.{d}", val, acc, sym)

    # ------------------------------------------------------------------
    # Arranque do sistema
    # ------------------------------------------------------------------
    def start(self):
        threading.Thread(target=self.run_simulation_loop, daemon=True).start()
        asyncio.run(self.run_agent())


if __name__ == "__main__":
    TrafficSystem('config.json').start()