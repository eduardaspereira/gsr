import base64
import getpass
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import asyncio
import json
import csv 
import time 
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c
from pysnmp.hlapi.asyncio import sendNotification, CommunityData, UdpTransportTarget, ContextData, NotificationType, ObjectIdentity, Integer32
from pysnmp.hlapi.asyncio import SnmpEngine as hlapiSnmpEngine

from ssfr import SistemaSimulacao
from sd_backpressure import SistemaDecisaoBackpressure
from sd_RL import SistemaDecisaoRL
from sd_heuristicaocupacao import SistemaDecisaoOcupacao
from sd_roundrobin import SistemaDecisaoRoundRobin

# =====================================================================
# 1. SEGURANÇA E ARRANQUE (O COFRE)
# =====================================================================
print("===============================================")
print("=== INICIALIZAÇÃO SEGURA DO SISTEMA CENTRAL ===")
print("===============================================")
password = getpass.getpass("Introduz a password mestra para destrancar a chave: ").encode()

salt = b'GSR_UM_2026'
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
chave_cofre = base64.urlsafe_b64encode(kdf.derive(password))
cofre_cipher = Fernet(chave_cofre)

try:
    with open("seguranca.key", "rb") as f:
        chave_encriptada = f.read()
    CHAVE_SECRETA = cofre_cipher.decrypt(chave_encriptada)
    cipher = Fernet(CHAVE_SECRETA)
    print("[OK] Chave carregada com sucesso! Túnel Seguro ativado.\n")
except Exception:
    print("[ERRO] Password incorreta ou ficheiro 'seguranca.key' em falta!")
    print("Corre primeiro o script 'gerar_cofre.py' para criares o ficheiro de chaves.")
    exit(1)

OID_TUNEL = "1.3.6.1.3.2026.99.1.0"
historico_ips = {}

# =====================================================================
# 2. CARREGAMENTO DA CONFIGURAÇÃO E INICIALIZAÇÃO DA MIB
# =====================================================================
with open('config.json', 'r') as f:
    cfg = json.load(f)

mib = {}
OID_BASE = "1.3.6.1.3.2026.1"

# Inicialização da MIB
mib[f"{OID_BASE}.1.2.0"] = cfg['geral']['simStepDuration']
mib[f"{OID_BASE}.1.4.0"] = cfg['geral']['algoMinGreenTime']
mib[f"{OID_BASE}.1.5.0"] = cfg['geral']['algoYellowTime']
mib[f"{OID_BASE}.1.6.0"] = 4  
mib[f"{OID_BASE}.1.7.0"] = 0  

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

# =====================================================================
# 3. RESPONDERS SNMP (A BARREIRA DE SEGURANÇA)
# =====================================================================
class SCSetResponder(cmdrsp.SetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        global historico_ips
        respPDU = v2c.apiPDU.getResponse(PDU)
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        novos_varBinds = []
        
        cliente_id = str(securityName) 
        agora = time.time()

        for oid, val in varBinds:
            oid_str = str(oid)
            
            # Intercetar mensagens dirigidas ao Túnel Seguro
            if oid_str == OID_TUNEL:
                # 1. Desencriptação Primeiro (Para sabermos o que é antes de bloquear)
                try:
                    payload_limpo = cipher.decrypt(bytes(val)).decode('utf-8')
                    comando_json = json.loads(payload_limpo)
                    cmd_type = comando_json.get("comando", "DESCONHECIDO")
                    
                    # 2. Rate Limiting Inteligente (Baldes separados por tipo de comando)
                    chave_limite = f"{cliente_id}_{cmd_type}"
                    if chave_limite in historico_ips and (agora - historico_ips[chave_limite]) < 0.2:
                        print(f"[SEGURANÇA] Bloqueio DoS! Ritmo excessivo de '{cmd_type}' do cliente {cliente_id}.")
                        v2c.apiPDU.setErrorStatus(respPDU, 'genErr')
                        novos_varBinds.append((oid, val))
                        continue
                        
                    # Atualiza o tempo do último pedido para este tipo de comando
                    historico_ips[chave_limite] = agora
                    
                    if cmd_type != "PULL_STATE":
                        print(f"[TÚNEL SEGURO] Comando recebido: {comando_json}")
                    
                    # 3. Execução das ordens
                    if cmd_type == "PULL_STATE":
                        estado_atual = {
                            "tempo": mib.get(f"{OID_BASE}.1.7.0", 0),
                            "algo_id": mib.get(f"{OID_BASE}.1.6.0", 4),
                            "filas": {r['id']: mib.get(f"{OID_BASE}.3.1.6.{r['id']}", 0) for r in cfg['roads']},
                            "semaforos": {tl['roadIndex']: mib.get(f"{OID_BASE}.4.1.3.{tl['roadIndex']}", 1) for tl in cfg['trafficLights']},
                            "rtgs": {r['id']: mib.get(f"{OID_BASE}.3.1.4.{r['id']}", 0) for r in cfg['roads'] if r['type'] == 3},
                            "overrides": {tl['roadIndex']: mib.get(f"{OID_BASE}.4.1.2.{tl['roadIndex']}", 0) for tl in cfg['trafficLights']},
                            "links": {f"{l['src']}.{l['dest']}": mib.get(f"{OID_BASE}.5.1.4.{l['src']}.{l['dest']}", 0) for l in cfg.get('links', [])}
                        }
                        resposta_encriptada = cipher.encrypt(json.dumps(estado_atual).encode('utf-8'))
                        novos_varBinds.append((oid, v2c.OctetString(resposta_encriptada)))
                        
                    elif cmd_type == "SET_RTG":
                        via = comando_json["via"]
                        novo_rtg = comando_json["valor"]
                        mib[f"{OID_BASE}.3.1.4.{via}"] = novo_rtg
                        resposta_encriptada = cipher.encrypt(json.dumps({"status": "sucesso"}).encode('utf-8'))
                        novos_varBinds.append((oid, v2c.OctetString(resposta_encriptada)))
                        
                    elif cmd_type == "SET_OVERRIDE":
                        via = comando_json["via"]
                        modo = comando_json["modo"]
                        mib[f"{OID_BASE}.4.1.2.{via}"] = modo
                        resposta_encriptada = cipher.encrypt(json.dumps({"status": "sucesso"}).encode('utf-8'))
                        novos_varBinds.append((oid, v2c.OctetString(resposta_encriptada)))
                        
                    elif cmd_type == "SET_ALG":
                        mib[f"{OID_BASE}.1.6.0"] = comando_json["alg_id"]
                        resposta_encriptada = cipher.encrypt(json.dumps({"status": "sucesso"}).encode('utf-8'))
                        novos_varBinds.append((oid, v2c.OctetString(resposta_encriptada)))

                except InvalidToken:
                    print("[SEGURANÇA] Intrusão detetada! Falha na desencriptação do payload.")
                    v2c.apiPDU.setErrorStatus(respPDU, 'authorizationError')
                    novos_varBinds.append((oid, val))
                except Exception as e:
                    print(f"[TÚNEL SEGURO] Erro ao processar comando: {e}")
                    v2c.apiPDU.setErrorStatus(respPDU, 'genErr')
                    novos_varBinds.append((oid, val))
            
            # Bloquear SETs diretos aos OIDs antigos para forçar o uso do túnel
            elif oid_str in mib:
                print(f"[SEGURANÇA] Tentativa de escrita não autorizada ao OID direto: {oid_str}")
                v2c.apiPDU.setErrorStatus(respPDU, 'noAccess')
                novos_varBinds.append((oid, val))
            else:
                novos_varBinds.append((oid, v2c.NoSuchInstance()))

        v2c.apiPDU.setVarBinds(respPDU, novos_varBinds)
        snmpEngine.msgAndPduDsp.returnResponsePdu(snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, respPDU, maxSizeResponseScopedPDU, stateReference, {})

class SCGetResponder(cmdrsp.GetCommandResponder):
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        # A morte do GET: Bloqueamos proativamente qualquer tentativa de leitura em plain-text.
        respPDU = v2c.apiPDU.getResponse(PDU)
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        novos_varBinds = []
        
        for oid, val in varBinds:
            print(f"[SEGURANÇA] Bloqueado GET em texto limpo ao OID: {oid}. Apenas PULL_STATE via Túnel é permitido.")
            v2c.apiPDU.setErrorStatus(respPDU, 'noAccess')
            novos_varBinds.append((oid, val))
            
        v2c.apiPDU.setVarBinds(respPDU, novos_varBinds)
        snmpEngine.msgAndPduDsp.returnResponsePdu(snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, respPDU, maxSizeResponseScopedPDU, stateReference, {})

# =====================================================================
# 4. LÓGICA DE SIMULAÇÃO E TRAPS
# =====================================================================
async def disparar_trap(via, carros):
    try:
        await sendNotification(
            hlapiSnmpEngine(),
            CommunityData('public', mpModel=1),
            UdpTransportTarget(('127.0.0.1', 16216)),
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

def limpar_metricas_mib(mib_dict, config):
    mib_dict[f"{OID_BASE}.1.7.0"] = 0
    for r in config['roads']:
        mib_dict[f"{OID_BASE}.3.1.6.{r['id']}"] = r.get('initialCount', 0)
    for link in config.get('links', []):
        mib_dict[f"{OID_BASE}.5.1.4.{link['src']}.{link['dest']}"] = 0

async def main():
    snmp_engine = engine.SnmpEngine()
    config_snmp = config
    config_snmp.addTransport(snmp_engine, udp.domainName, udp.UdpTransport().openServerMode(('127.0.0.1', 16161)))
    config_snmp.addV1System(snmp_engine, 'my-area', 'public')
    config_snmp.addVacmUser(snmp_engine, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6), (1, 3, 6))
    snmp_context = context.SnmpContext(snmp_engine)
    
    SCSetResponder(snmp_engine, snmp_context)
    SCGetResponder(snmp_engine, snmp_context)

    ALGO_MAP = {1: "ROUND_ROBIN", 2: "HEURISTICA", 3: "RL", 4: "BACKPRESSURE"}
    
    def criar_sd(algoritmo_nome):
        if algoritmo_nome == "ROUND_ROBIN": return SistemaDecisaoRoundRobin(mib, cfg)
        elif algoritmo_nome == "HEURISTICA": return SistemaDecisaoOcupacao(mib, cfg)
        elif algoritmo_nome == "RL": return SistemaDecisaoRL(mib, cfg)
        else: return SistemaDecisaoBackpressure(mib, cfg)

    algo_id = mib.get(f"{OID_BASE}.1.6.0", 4)
    ALGORITMO = ALGO_MAP.get(algo_id, "BACKPRESSURE")
    sd = criar_sd(ALGORITMO)
    
    if ALGORITMO == "RL":
        if sd.precisa_treino:
            ssfr_treino = SistemaSimulacao(mib, cfg)
            print("\n[TREINO RL] Iniciando treino acelerado (1000 ciclos virtuais)...")
            sd.epsilon = 0.5 
            
            for i in range(1000):
                ssfr_treino.run_step(5) 
                await sd.update(fast_forward_step=5)
                if i % 250 == 0: print(f"[TREINO RL] Progresso: {i}/1000 ciclos | Estados na memória: {len(sd.q_table)}")

            print("[TREINO RL] Treino concluído! A gravar conhecimento...")
            sd.guardar_cerebro()
            sd.epsilon = 0.05 
        else:
            print("\n[TREINO RL] O cérebro para este mapa já existe. A saltar o treino e arrancar a simulação!")
    
    limpar_metricas_mib(mib, cfg)
    ssfr = SistemaSimulacao(mib, cfg)
    
    nome_ficheiro_csv = f"historico_simulacao_{ALGORITMO}.csv"
    with open(nome_ficheiro_csv, mode='w', newline='') as file:
        writer = csv.writer(file, delimiter=';') 
        writer.writerow(["Tempo (s)", "Algoritmo", "Total Escoados", "Fila Maxima"])

    async def simulation_loop():
        nonlocal ALGORITMO, sd, ssfr, nome_ficheiro_csv
        
        sim_step = cfg['geral']['simStepDuration']
        iteration = 0
        tempo_inicio = time.time()
        tempo_ultimo_trap = {} 
        algo_anterior = ALGORITMO

        print(f"\n=== SC EM EXECUÇÃO (Porta 16161) | Algoritmo: {ALGORITMO} ===")
        print(f"A gravar dados em: {nome_ficheiro_csv}")
        
        while True:
            # --- VERIFICAR MUDANÇA DE ALGORITMO ---
            algo_id_atual = mib.get(f"{OID_BASE}.1.6.0", 4)
            ALGORITMO = ALGO_MAP.get(algo_id_atual, "BACKPRESSURE")
            
            if ALGORITMO != algo_anterior:
                print(f"\n[ALTERAÇÃO] Mudando algoritmo de {algo_anterior} para {ALGORITMO}...")
                sd = criar_sd(ALGORITMO)
                
                if ALGORITMO == "RL":
                    ssfr_treino = SistemaSimulacao(mib, cfg)
                    print("[TREINO RL] Iniciando treino acelerado (1000 ciclos virtuais)...")
                    sd.epsilon = 0.5 
                    for i in range(1000):
                        ssfr_treino.run_step(5) 
                        await sd.update(fast_forward_step=5)
                        if i % 250 == 0: print(f"[TREINO RL] Progresso: {i}/1000 ciclos | Estados na memória: {len(sd.q_table)}")
                    sd.guardar_cerebro()
                    sd.epsilon = 0.05 
                    print("[TREINO RL] Treino concluído!")
                
                limpar_metricas_mib(mib, cfg)
                ssfr = SistemaSimulacao(mib, cfg)
                tempo_inicio = time.time()
                tempo_ultimo_trap = {}
                iteration = 0
                
                nome_ficheiro_csv = f"historico_simulacao_{ALGORITMO}.csv"
                with open(nome_ficheiro_csv, mode='w', newline='') as file:
                    writer = csv.writer(file, delimiter=';') 
                    writer.writerow(["Tempo (s)", "Algoritmo", "Total Escoados", "Fila Maxima"])
                
                algo_anterior = ALGORITMO
                print(f"[ALTERAÇÃO] Simulação reiniciada a ZEROS com {ALGORITMO}!")
            
            tempo_decorrido = int(time.time() - tempo_inicio)
            mib[f"{OID_BASE}.1.7.0"] = tempo_decorrido
            
            ssfr.run_step(sim_step)
            await sd.update(current_step=sim_step)
            
            # --- PROCESSAR OVERRIDES MANUAIS ---
            for tl in cfg['trafficLights']:
                rid = tl['roadIndex']
                modo_manual = mib.get(f"{OID_BASE}.4.1.2.{rid}", 0)
                
                if modo_manual == 1:
                    mib[f"{OID_BASE}.4.1.3.{rid}"] = 2 
                    mib[f"{OID_BASE}.4.1.4.{rid}"] = 99 
                elif modo_manual == 2:
                    mib[f"{OID_BASE}.4.1.3.{rid}"] = 1 
                    mib[f"{OID_BASE}.4.1.4.{rid}"] = 99
            
            # --- CÁLCULO DE ESTATÍSTICAS E TRAPS ---
            saidas = ['91', '92', '93', '94']
            total_escoados = sum(mib.get(f"{OID_BASE}.5.1.4.{link['src']}.{link['dest']}", 0) 
                                 for link in cfg.get('links', []) 
                                 if str(link['dest']) in saidas)
            
            max_fila = 0
            vias_saida = [91, 92, 93, 94]
            for r in cfg['roads']:
                if r['id'] not in vias_saida:
                    fila_atual = mib.get(f"{OID_BASE}.3.1.6.{r['id']}", 0)
                    
                    if fila_atual >= 20:
                        agora = time.time()
                        if agora - tempo_ultimo_trap.get(r['id'], 0) > 10.0:
                            asyncio.create_task(disparar_trap(r['id'], fila_atual))
                            tempo_ultimo_trap[r['id']] = agora

                    if fila_atual > max_fila:
                        max_fila = fila_atual

            with open(nome_ficheiro_csv, mode='a', newline='') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow([tempo_decorrido, ALGORITMO, total_escoados, max_fila])

            if iteration % 4 == 0:
                vias = " | ".join([f"V{r['id']}:{mib[f'{OID_BASE}.3.1.6.{r['id']}']}v" for r in cfg['roads'][:4]])
                print(f"[MONITOR] {vias} | Escoados: {total_escoados} | Algoritmo: {ALGORITMO}")
            
            iteration += 1
            await asyncio.sleep(sim_step)

    await simulation_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SC] Encerrado pelo utilizador.")