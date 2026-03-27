import asyncio
import json
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

from ssfr import SistemaSimulacao
from sd import SistemaDecisao
from sd_heuristica import SistemaDecisaoOcupacao
from sd_backpressure import SistemaDecisaoBackpressure
from sd_RL import SistemaDecisaoRL

with open('config.json', 'r') as f:
    cfg = json.load(f)

mib = {}
OID_BASE = "1.3.6.1.3.2026.1"

mib[f"{OID_BASE}.1.2.0"] = cfg['geral']['simStepDuration']
mib[f"{OID_BASE}.1.4.0"] = cfg['geral']['algoMinGreenTime']
mib[f"{OID_BASE}.1.5.0"] = cfg['geral']['algoYellowTime']

for r in cfg['roads']:
    mib[f"{OID_BASE}.3.1.4.{r['id']}"] = r['rtg']
    mib[f"{OID_BASE}.3.1.5.{r['id']}"] = r.get('maxCapacity', 999)
    mib[f"{OID_BASE}.3.1.6.{r['id']}"] = r.get('initialCount', 0)

for tl in cfg['trafficLights']:
    mib[f"{OID_BASE}.4.1.3.{tl['roadIndex']}"] = 1
    mib[f"{OID_BASE}.4.1.4.{tl['roadIndex']}"] = cfg['geral']['algoMinGreenTime']

for link in cfg.get('links', []):
    mib[f"{OID_BASE}.5.1.4.{link['src']}.{link['dest']}"] = 0

class SCSetResponder(cmdrsp.SetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        respPDU = v2c.apiPDU.getResponse(PDU)
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        novos_varBinds = []
        for oid, val in varBinds:
            oid_str = str(oid)
            if oid_str in mib and ".3.1.4." in oid_str:
                mib[oid_str] = int(val)
                print(f"[SC] RTG atualizado via SNMP: {oid_str} -> {int(val)}")
                novos_varBinds.append((oid, val))
            else:
                v2c.apiPDU.setErrorStatus(respPDU, 'noAccess')
                v2c.apiPDU.setErrorIndex(respPDU, 1)
                novos_varBinds.append((oid, val))
        v2c.apiPDU.setVarBinds(respPDU, novos_varBinds)
        snmpEngine.msgAndPduDsp.returnResponsePdu(snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, respPDU, maxSizeResponseScopedPDU, stateReference, {})

class SCGetResponder(cmdrsp.GetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        respPDU = v2c.apiPDU.getResponse(PDU)
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        novos_varBinds = []
        for oid, val in varBinds:
            oid_str = str(oid)
            if oid_str in mib:
                if ".3.1.4." in oid_str or ".3.1.5." in oid_str or ".3.1.6." in oid_str: novos_varBinds.append((oid, v2c.Gauge32(mib[oid_str])))
                elif ".5.1.4." in oid_str: novos_varBinds.append((oid, v2c.Counter32(mib[oid_str])))
                else: novos_varBinds.append((oid, v2c.Integer32(mib[oid_str])))
            else:
                novos_varBinds.append((oid, v2c.NoSuchInstance()))
        v2c.apiPDU.setVarBinds(respPDU, novos_varBinds)
        snmpEngine.msgAndPduDsp.returnResponsePdu(snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, respPDU, maxSizeResponseScopedPDU, stateReference, {})

async def main():
    snmp_engine = engine.SnmpEngine()
    config.addTransport(snmp_engine, udp.domainName, udp.UdpTransport().openServerMode(('127.0.0.1', 16161)))
    config.addV1System(snmp_engine, 'my-area', 'public')
    config.addVacmUser(snmp_engine, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6), (1, 3, 6))
    snmp_context = context.SnmpContext(snmp_engine)
    
    SCSetResponder(snmp_engine, snmp_context)
    SCGetResponder(snmp_engine, snmp_context)

    # =====================================================================
    # SELETOR DE ALGORITMOS DE DECISÃO
    # =====================================================================
    ALGORITMO_ATIVO = "RL" # Opções: "ROUND_ROBIN", "HEURISTICA", "BACKPRESSURE", "RL"

    if ALGORITMO_ATIVO == "BACKPRESSURE": sd = SistemaDecisaoBackpressure(mib, cfg)
    elif ALGORITMO_ATIVO == "HEURISTICA": sd = SistemaDecisaoOcupacao(mib, cfg)
    elif ALGORITMO_ATIVO == "RL":         sd = SistemaDecisaoRL(mib, cfg)
    else:                                 sd = SistemaDecisao(mib, cfg)

    ssfr = SistemaSimulacao(mib, cfg)

    print(f"=== SC iniciado com Algoritmo: {ALGORITMO_ATIVO} ===")

    # =====================================================================
    # FASE DE TREINO RÁPIDO (Se o algoritmo for Reinforcement Learning)
    # =====================================================================
    if ALGORITMO_ATIVO == "RL":
        total_steps = 2000 # Ciclos de simulação virtual para preencher a Q-Table
        step_virtual = 5   # Avança 5 segundos em cada iteração hiper-rápida
        print(f"\n[TREINO RL] Iniciando treino rápido por {total_steps} ciclos...")
        sd.epsilon = 0.5   # Muita exploração inicial
        
        for i in range(total_steps):
            ssfr.run_step(step_virtual)
            await sd.update(fast_forward_step=step_virtual)
            
            if i % 500 == 0 and i > 0:
                print(f"[TREINO RL] Ciclo {i}/{total_steps} | Estados aprendidos: {len(sd.q_table)}")

        print("[TREINO RL] Treino concluído! Q-Table finalizada.")
        sd.epsilon = 0.0 # Desativa exploração, usa apenas as ações "ideais"
        print("==================================================================\n")

    # =====================================================================
    # FASE DE EXECUÇÃO EM TEMPO REAL (SNMP Ativo)
    # =====================================================================
    asyncio.create_task(sd.start())
    asyncio.create_task(ssfr.start())
    
    try:
        while True: await asyncio.sleep(3600)
    except asyncio.CancelledError: pass

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nSC encerrado.")