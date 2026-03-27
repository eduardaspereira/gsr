import asyncio
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

# =====================================================================
# 1. BASE DE DADOS (Estado interno da MIB experimental)
# =====================================================================
estado_vias = {1: 43, 2: 43, 3: 43, 4: 43, 5: 43, 6: 43}
OID_BASE_RTG = (1, 3, 6, 1, 3, 2026, 1, 3, 1, 4)
OID_BASE_COLOR = (1, 3, 6, 1, 3, 2026, 1, 4, 1, 3) # OID para tlColor

# Configurações do Algoritmo SD
TEMPO_VERDE = 15
TEMPO_AMARELO = 3

estado_cruzamentos = {
    1: {'eixo_ativo': 1, 'cor_eixo': 'green', 'tempo_restante': TEMPO_VERDE},
    2: {'eixo_ativo': 1, 'cor_eixo': 'green', 'tempo_restante': TEMPO_VERDE}
}

estado_semaforos = {
    1: {'crID': 1, 'axis': 2, 'color': 1}, 
    3: {'crID': 1, 'axis': 2, 'color': 1}, 
    5: {'crID': 1, 'axis': 1, 'color': 2}  
}

# =====================================================================
# 2. SISTEMA DE DECISÃO (SD) - Algoritmo Round-Robin / Ciclo Fixo
# =====================================================================
async def sistema_de_decisao():
    print("[SD] Componente de Decisão (Ciclo Fixo) iniciado.")
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

# Responde a pedidos SET (Alterar valores, ex: RTG)
class SCSetResponder(cmdrsp.SetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel,
                   securityName, securityLevel, contextEngineId, contextName,
                   pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        
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
                    print(f"[SC - SNMP] Via {road_index} atualizada externamente. Novo RTG: {novo_valor}")
                    novos_varBinds.append((oid, val))
                else:
                    v2c.apiPDU.setErrorStatus(respPDU, 'noAccess')
                    v2c.apiPDU.setErrorIndex(respPDU, 1)
                    novos_varBinds.append((oid, val))
            else:
                novos_varBinds.append((oid, val))
        
        v2c.apiPDU.setVarBinds(respPDU, novos_varBinds)
        
        snmpEngine.msgAndPduDsp.returnResponsePdu(
            snmpEngine, messageProcessingModel, securityModel, securityName,
            securityLevel, contextEngineId, contextName, pduVersion,
            respPDU, maxSizeResponseScopedPDU, stateReference, {}
        )

# Responde a pedidos GET (Ler valores, ex: Cor dos Semáforos)
class SCGetResponder(cmdrsp.GetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel,
                   securityName, securityLevel, contextEngineId, contextName,
                   pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        
        respPDU = v2c.apiPDU.getResponse(PDU)
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        novos_varBinds = []
        
        for oid, val in varBinds:
            oid_tuple = oid.asTuple()
            
            # Pedido para ler a cor do semáforo
            if oid_tuple[:-1] == OID_BASE_COLOR:
                road_index = oid_tuple[-1]
                if road_index in estado_semaforos:
                    cor_atual = estado_semaforos[road_index]['color']
                    novos_varBinds.append((oid, v2c.Integer32(cor_atual)))
                else:
                    novos_varBinds.append((oid, v2c.NoSuchInstance()))
            
            # Pedido para ler o RTG
            elif oid_tuple[:-1] == OID_BASE_RTG:
                road_index = oid_tuple[-1]
                if road_index in estado_vias:
                    rtg_atual = estado_vias[road_index]
                    novos_varBinds.append((oid, v2c.Gauge32(rtg_atual)))
                else:
                    novos_varBinds.append((oid, v2c.NoSuchInstance()))
            else:
                novos_varBinds.append((oid, v2c.NoSuchObject()))
        
        v2c.apiPDU.setVarBinds(respPDU, novos_varBinds)
        
        snmpEngine.msgAndPduDsp.returnResponsePdu(
            snmpEngine, messageProcessingModel, securityModel, securityName,
            securityLevel, contextEngineId, contextName, pduVersion,
            respPDU, maxSizeResponseScopedPDU, stateReference, {}
        )

async def main():
    snmp_engine = engine.SnmpEngine()
    porta = 16161
    
    config.addTransport(snmp_engine, udp.domainName, udp.UdpTransport().openServerMode(('127.0.0.1', porta)))
    config.addV1System(snmp_engine, 'my-area', 'public')
    config.addVacmUser(snmp_engine, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6), (1, 3, 6))
    snmp_context = context.SnmpContext(snmp_engine)
    
    # Registar ambos os "escutas"
    SCSetResponder(snmp_engine, snmp_context)
    SCGetResponder(snmp_engine, snmp_context)

    print(f"=== Sistema Central (SC) iniciado na porta {porta} ===")
    
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