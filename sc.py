import asyncio
import json
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

# =====================================================================
# 1. CARREGAR CONFIGURAÇÃO E INICIALIZAR BASE DE DADOS
# =====================================================================
with open('config.json', 'r') as f:
    cfg = json.load(f)

TEMPO_VERDE = cfg['geral']['algoMinGreenTime']
TEMPO_AMARELO = cfg['geral']['algoYellowTime']

# Constrói o estado inicial a partir do JSON
estado_vias = {r['id']: r['rtg'] for r in cfg['roads']}
estado_cruzamentos = {c['id']: {'eixo_ativo': 1, 'cor_eixo': 'green', 'tempo_restante': TEMPO_VERDE} for c in cfg['crossroads']}
estado_semaforos = {tl['roadIndex']: {'crID': tl['crID'], 'axis': tl['axis'], 'color': 1} for tl in cfg['trafficLights']}

OID_BASE_RTG = (1, 3, 6, 1, 3, 2026, 1, 3, 1, 4)
OID_BASE_COLOR = (1, 3, 6, 1, 3, 2026, 1, 4, 1, 3)

# =====================================================================
# 2. SISTEMA DE DECISÃO (SD)
# =====================================================================
async def sistema_de_decisao():
    print(f"[SD] Algoritmo iniciado (Verde: {TEMPO_VERDE}s, Amarelo: {TEMPO_AMARELO}s)")
    while True:
        await asyncio.sleep(1) 
        
        for cr_id, cr in estado_cruzamentos.items():
            cr['tempo_restante'] -= 1
            if cr['tempo_restante'] <= 0:
                if cr['cor_eixo'] == 'green':
                    cr['cor_eixo'] = 'yellow'
                    cr['tempo_restante'] = TEMPO_AMARELO
                elif cr['cor_eixo'] == 'yellow':
                    cr['cor_eixo'] = 'green'
                    cr['tempo_restante'] = TEMPO_VERDE
                    cr['eixo_ativo'] = 2 if cr['eixo_ativo'] == 1 else 1
        
        for road_id, tl in estado_semaforos.items():
            cr = estado_cruzamentos.get(tl['crID'])
            if cr:
                if tl['axis'] == cr['eixo_ativo']:
                    tl['color'] = 2 if cr['cor_eixo'] == 'green' else 3
                else:
                    tl['color'] = 1 

# =====================================================================
# 3. CONSOLA SNMP (Agente)
# =====================================================================
class SCSetResponder(cmdrsp.SetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        respPDU = v2c.apiPDU.getResponse(PDU)
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        novos_varBinds = []
        
        for oid, val in varBinds:
            oid_tuple = oid.asTuple()
            if oid_tuple[:-1] == OID_BASE_RTG:
                road_index = oid_tuple[-1]
                novo_valor = int(val)
                if road_index in estado_vias:
                    estado_vias[road_index] = novo_valor
                    print(f"[SC] Via {road_index} atualizada. Novo RTG: {novo_valor}")
                    novos_varBinds.append((oid, val))
                else:
                    v2c.apiPDU.setErrorStatus(respPDU, 'noAccess')
                    v2c.apiPDU.setErrorIndex(respPDU, 1)
                    novos_varBinds.append((oid, val))
            else:
                novos_varBinds.append((oid, val))
        
        v2c.apiPDU.setVarBinds(respPDU, novos_varBinds)
        snmpEngine.msgAndPduDsp.returnResponsePdu(snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, respPDU, maxSizeResponseScopedPDU, stateReference, {})

class SCGetResponder(cmdrsp.GetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        respPDU = v2c.apiPDU.getResponse(PDU)
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        novos_varBinds = []
        
        for oid, val in varBinds:
            oid_tuple = oid.asTuple()
            if oid_tuple[:-1] == OID_BASE_COLOR:
                road_index = oid_tuple[-1]
                if road_index in estado_semaforos:
                    novos_varBinds.append((oid, v2c.Integer32(estado_semaforos[road_index]['color'])))
                else:
                    novos_varBinds.append((oid, v2c.NoSuchInstance()))
            elif oid_tuple[:-1] == OID_BASE_RTG:
                road_index = oid_tuple[-1]
                if road_index in estado_vias:
                    novos_varBinds.append((oid, v2c.Gauge32(estado_vias[road_index])))
                else:
                    novos_varBinds.append((oid, v2c.NoSuchInstance()))
            else:
                novos_varBinds.append((oid, v2c.NoSuchObject()))
        
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

    print("=== Sistema Central (SC) iniciado ===")
    asyncio.create_task(sistema_de_decisao())
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSC encerrado.")