import asyncio
import json
import csv 
import time 
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

# NOVO: Imports exclusivos para disparar a Trap SNMP
from pysnmp.hlapi.asyncio import sendNotification, CommunityData, UdpTransportTarget, ContextData, NotificationType, ObjectIdentity, Integer32
from pysnmp.hlapi.asyncio import SnmpEngine as hlapiSnmpEngine

from ssfr import SistemaSimulacao
from sd_backpressure import SistemaDecisaoBackpressure
from sd_RL import SistemaDecisaoRL
from sd_heuristicaocupacao import SistemaDecisaoOcupacao
from sd_roundrobin import SistemaDecisaoRoundRobin

# 1. Carregamento da configuração
with open('config.json', 'r') as f:
    cfg = json.load(f)

mib = {}
OID_BASE = "1.3.6.1.3.2026.1"

# Inicialização da MIB
mib[f"{OID_BASE}.1.2.0"] = cfg['geral']['simStepDuration']
mib[f"{OID_BASE}.1.4.0"] = cfg['geral']['algoMinGreenTime']
mib[f"{OID_BASE}.1.5.0"] = cfg['geral']['algoYellowTime']

for r in cfg['roads']:
    rid = r['id']
    mib[f"{OID_BASE}.3.1.4.{rid}"] = r.get('rtg', 5)
    mib[f"{OID_BASE}.3.1.5.{rid}"] = r.get('maxCapacity', 999)
    mib[f"{OID_BASE}.3.1.6.{rid}"] = r.get('initialCount', 0)

for tl in cfg['trafficLights']:
    rid = tl['roadIndex']
    mib[f"{OID_BASE}.4.1.2.{rid}"] = 0 
    mib[f"{OID_BASE}.4.1.3.{rid}"] = 1 
    mib[f"{OID_BASE}.4.1.4.{rid}"] = 0 
    mib[f"{OID_BASE}.4.1.5.{rid}"] = cfg['geral']['algoMinGreenTime']
    mib[f"{OID_BASE}.4.1.6.{rid}"] = cfg['geral']['algoMinGreenTime']

for link in cfg.get('links', []):
    mib[f"{OID_BASE}.5.1.4.{link['src']}.{link['dest']}"] = 0

# 3. Responders SNMPv2c Reais
class SCSetResponder(cmdrsp.SetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        respPDU = v2c.apiPDU.getResponse(PDU)
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        novos_varBinds = []
        for oid, val in varBinds:
            oid_str = str(oid)
            if oid_str in mib and (".3.1.4." in oid_str or ".4.1.2." in oid_str):
                mib[oid_str] = int(val)
                tipo = "OVERRIDE" if ".4.1.2." in oid_str else "RTG"
                print(f"[SNMP SET] {tipo} atualizado: {oid_str} -> {int(val)}")
                novos_varBinds.append((oid, val))
            else:
                v2c.apiPDU.setErrorStatus(respPDU, 'noAccess')
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
                if any(x in oid_str for x in [".3.1.4.", ".3.1.5.", ".3.1.6."]):
                    novos_varBinds.append((oid, v2c.Gauge32(mib[oid_str])))
                elif ".5.1.4." in oid_str:
                    novos_varBinds.append((oid, v2c.Counter32(mib[oid_str])))
                else:
                    novos_varBinds.append((oid, v2c.Integer32(mib[oid_str])))
            else:
                novos_varBinds.append((oid, v2c.NoSuchInstance()))
        v2c.apiPDU.setVarBinds(respPDU, novos_varBinds)
        snmpEngine.msgAndPduDsp.returnResponsePdu(snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, respPDU, maxSizeResponseScopedPDU, stateReference, {})

# NOVO: Função que cria e envia a Trap SNMP
async def disparar_trap(via, carros):
    try:
        await sendNotification(
            hlapiSnmpEngine(),
            CommunityData('public', mpModel=1),
            UdpTransportTarget(('127.0.0.1', 16216)), # Envia para a porta da Consola
            ContextData(),
            'trap',
            NotificationType(ObjectIdentity('1.3.6.1.4.1.2026.1.0.1')).addVarBinds(
                ('1.3.6.1.4.1.2026.1.1.1', Integer32(via)),
                ('1.3.6.1.4.1.2026.1.1.2', Integer32(carros))
            )
        )
        print(f"[TRAP ENVIADA] Alerta de Congestionamento na Via {via}!")
    except Exception:
        pass

async def main():
    snmp_engine = engine.SnmpEngine()
    config.addTransport(snmp_engine, udp.domainName, udp.UdpTransport().openServerMode(('127.0.0.1', 16161)))
    config.addV1System(snmp_engine, 'my-area', 'public')
    config.addVacmUser(snmp_engine, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6), (1, 3, 6))
    snmp_context = context.SnmpContext(snmp_engine)
    
    SCSetResponder(snmp_engine, snmp_context)
    SCGetResponder(snmp_engine, snmp_context)

    ssfr = SistemaSimulacao(mib, cfg)
    
    ALGORITMO = "RL" # Opções: "ROUND_ROBIN", "HEURISTICA", "RL", "BACKPRESSURE" 

    if ALGORITMO == "ROUND_ROBIN":
        sd = SistemaDecisaoRoundRobin(mib, cfg)
    elif ALGORITMO == "HEURISTICA":
        sd = SistemaDecisaoOcupacao(mib, cfg)
    elif ALGORITMO == "RL":
        sd = SistemaDecisaoRL(mib, cfg)
    else:
        sd = SistemaDecisaoBackpressure(mib, cfg)

    if ALGORITMO == "RL":
        print("\n[TREINO RL] Iniciando treino acelerado (2000 ciclos virtuais)...")
        sd.epsilon = 0.5 
        
        for i in range(2000):
            ssfr.run_step(5) 
            await sd.update(fast_forward_step=5)
            if i % 500 == 0: print(f"[TREINO RL] Progresso: {i}/2000 ciclos | Estados na memória: {len(sd.q_table)}")

        print("[TREINO RL] ✅ Treino concluído! Agente pronto para agir.")
        sd.epsilon = 0.05 

    nome_ficheiro_csv = f"historico_simulacao_{ALGORITMO}.csv"
    with open(nome_ficheiro_csv, mode='w', newline='') as file:
        writer = csv.writer(file, delimiter=';') # Mantive o ponto e vírgula!
        writer.writerow(["Tempo (s)", "Algoritmo", "Total Escoados", "Fila Maxima"])

    async def simulation_loop():
        sim_step = cfg['geral']['simStepDuration']
        iteration = 0
        tempo_inicio = time.time()
        tempo_ultimo_trap = {} # NOVO: Para não spammar a rede

        print(f"\n=== SC EM EXECUÇÃO (Porta 16161) | Algoritmo: {ALGORITMO} ===")
        print(f"📊 Gravando dados em: {nome_ficheiro_csv}")
        
        while True:
            ssfr.run_step(sim_step)
            await sd.update(current_step=sim_step)
            
            for tl in cfg['trafficLights']:
                rid = tl['roadIndex']
                modo_manual = mib.get(f"{OID_BASE}.4.1.2.{rid}", 0)
                
                if modo_manual == 1:
                    mib[f"{OID_BASE}.4.1.3.{rid}"] = 2 
                    mib[f"{OID_BASE}.4.1.4.{rid}"] = 99 
                elif modo_manual == 2:
                    mib[f"{OID_BASE}.4.1.3.{rid}"] = 1 
                    mib[f"{OID_BASE}.4.1.4.{rid}"] = 99
            
            saidas = ['91', '92', '93', '94']
            total_escoados = sum(mib.get(f"{OID_BASE}.5.1.4.{link['src']}.{link['dest']}", 0) 
                                 for link in cfg.get('links', []) 
                                 if str(link['dest']) in saidas)
            
            max_fila = 0
            vias_saida = [91, 92, 93, 94]
            for r in cfg['roads']:
                if r['id'] not in vias_saida:
                    fila_atual = mib.get(f"{OID_BASE}.3.1.6.{r['id']}", 0)
                    
                    # --- NOVO: LÓGICA DE ALARME ---
                    if fila_atual >= 20:
                        agora = time.time()
                        # Dispara a Trap no máximo a cada 10s por via
                        if agora - tempo_ultimo_trap.get(r['id'], 0) > 10.0:
                            asyncio.create_task(disparar_trap(r['id'], fila_atual))
                            tempo_ultimo_trap[r['id']] = agora
                    # ------------------------------

                    if fila_atual > max_fila:
                        max_fila = fila_atual

            tempo_decorrido = int(time.time() - tempo_inicio)

            with open(nome_ficheiro_csv, mode='a', newline='') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow([tempo_decorrido, ALGORITMO, total_escoados, max_fila])

            if iteration % 4 == 0:
                vias = " | ".join([f"V{r['id']}:{mib[f'{OID_BASE}.3.1.6.{r['id']}']}v" for r in cfg['roads'][:4]])
                print(f"[MONITOR] {vias} | Escoados: {total_escoados}")
            
            iteration += 1
            await asyncio.sleep(sim_step)

    await simulation_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SC] Encerrado pelo utilizador.")