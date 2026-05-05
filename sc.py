# ==============================================================================
# Ficheiro: sc.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Sistema Central (Agente SNMP e Motor de Simulação).
#            Atua como o servidor do projeto, mantendo a MIB em memória, gerindo
#            a simulação física (SSFR) e instanciando os Sistemas de Decisão (RL, 
#            Backpressure, etc). Implementa Defesa Ativa bloqueando acessos em
#            plain-text e processando apenas comandos via Túnel Seguro (Fernet).
# ==============================================================================

import sys 
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
# 1. SEGURANÇA E ARRANQUE (VIA ARGUMENTO CLI)
# =====================================================================
print("===============================================")
print("=== INICIALIZAÇÃO SEGURA DO SISTEMA CENTRAL ===")
print("===============================================")

if len(sys.argv) < 2:
    print("[ERRO CRÍTICO] Password mestra em falta!")
    print("Para iniciar o sistema em modo seguro, passa a password como argumento:")
    print("Comando correto: python3 sc.py <a_tua_password>")
    sys.exit(1)

password_lida = sys.argv[1].encode()

salt = b'GSR_UM_2026'
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
chave_cofre = base64.urlsafe_b64encode(kdf.derive(password_lida))
cifra_cofre = Fernet(chave_cofre)

try:
    with open("seguranca.key", "rb") as ficheiro_chave:
        chave_encriptada = ficheiro_chave.read()
    CHAVE_SECRETA = cifra_cofre.decrypt(chave_encriptada)
    cifra = Fernet(CHAVE_SECRETA)
    print("[OK] Segredo lido com sucesso. Túnel Seguro ativado!\n")
except Exception as erro:
    print(f"[ERRO] Falha ao destrancar o cofre com a password fornecida: {erro}")
    sys.exit(1)

OID_TUNEL = "1.3.6.1.3.2026.99.1.0"
historico_pedidos_ips = {}

# =====================================================================
# 2. CARREGAMENTO DA CONFIGURAÇÃO E INICIALIZAÇÃO DA MIB
# =====================================================================
try:
    with open('config3.json', 'r') as ficheiro_config:
        cfg = json.load(ficheiro_config)
except Exception as e:
    print(f"[ERRO CRÍTICO] Não foi possível ler o 'config3.json': {e}")
    sys.exit(1)

mib = {}
OID_BASE = "1.3.6.1.3.2026.1"

# Inicialização da Base de Informação de Gestão (MIB)
mib[f"{OID_BASE}.1.2.0"] = cfg['geral']['simStepDuration']
mib[f"{OID_BASE}.1.4.0"] = cfg['geral']['algoMinGreenTime']
mib[f"{OID_BASE}.1.5.0"] = cfg['geral']['algoYellowTime']
mib[f"{OID_BASE}.1.6.0"] = 4  # Algoritmo padrão: Backpressure
mib[f"{OID_BASE}.1.7.0"] = 0  

for rua in cfg['roads']:
    id_rua = rua['id']
    mib[f"{OID_BASE}.3.1.4.{id_rua}"] = rua.get('rtg', 5)
    mib[f"{OID_BASE}.3.1.5.{id_rua}"] = rua.get('maxCapacity', 999)
    mib[f"{OID_BASE}.3.1.6.{id_rua}"] = rua.get('initialCount', 0)

for semaforo in cfg['trafficLights']:
    id_rua = semaforo['roadIndex']
    mib[f"{OID_BASE}.4.1.2.{id_rua}"] = 0 
    mib[f"{OID_BASE}.4.1.3.{id_rua}"] = 1 
    mib[f"{OID_BASE}.4.1.4.{id_rua}"] = 0 
    mib[f"{OID_BASE}.4.1.5.{id_rua}"] = cfg['geral']['algoMinGreenTime']
    mib[f"{OID_BASE}.4.1.6.{id_rua}"] = cfg['geral']['algoMinGreenTime']

for ligacao in cfg.get('links', []):
    mib[f"{OID_BASE}.5.1.4.{ligacao['src']}.{ligacao['dest']}"] = 0


# =====================================================================
# 3. RESPONDERS SNMP (A BARREIRA DE SEGURANÇA E DEFESA ATIVA)
# =====================================================================
class ResponderSetSeguro(cmdrsp.SetCommandResponder):
    """Interceta todos os pedidos SNMP SET. Se não vierem pelo Túnel Seguro ou falharem a desencriptação, são bloqueados."""
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        global historico_pedidos_ips
        resposta_pdu = v2c.apiPDU.getResponse(PDU)
        binds = v2c.apiPDU.getVarBinds(PDU)
        novos_binds = []
        
        cliente_id = str(securityName) 
        tempo_atual = time.time()

        for oid, valor in binds:
            oid_str = str(oid)
            
            if oid_str == OID_TUNEL:
                # 1. Tentar Desencriptar o Payload (Verificação de Autenticidade)
                try:
                    payload_limpo = cifra.decrypt(bytes(valor)).decode('utf-8')
                    comando_json = json.loads(payload_limpo)
                    tipo_comando = comando_json.get("comando", "DESCONHECIDO")
                    
                    # 2. Rate Limiting Inteligente (Prevenção de Ataques DoS)
                    chave_limite = f"{cliente_id}_{tipo_comando}"
                    if chave_limite in historico_pedidos_ips and (tempo_atual - historico_pedidos_ips[chave_limite]) < 0.2:
                        if tipo_comando != "PULL_STATE":
                            print(f"[SEGURANÇA] Bloqueio DoS! Ritmo excessivo de '{tipo_comando}' do cliente {cliente_id}.")
                        v2c.apiPDU.setErrorStatus(resposta_pdu, 'genErr')
                        novos_binds.append((oid, valor))
                        continue
                        
                    historico_pedidos_ips[chave_limite] = tempo_atual
                    
                    if tipo_comando != "PULL_STATE":
                        print(f"[TÚNEL SEGURO] Comando autorizado: {comando_json}")
                    
                    # 3. Execução das Instruções JSON
                    if tipo_comando == "PULL_STATE":
                        estado_atual = {
                            "tempo": mib.get(f"{OID_BASE}.1.7.0", 0),
                            "algo_id": mib.get(f"{OID_BASE}.1.6.0", 4),
                            "filas": {r['id']: mib.get(f"{OID_BASE}.3.1.6.{r['id']}", 0) for r in cfg['roads']},
                            "semaforos": {tl['roadIndex']: mib.get(f"{OID_BASE}.4.1.3.{tl['roadIndex']}", 1) for tl in cfg['trafficLights']},
                            "rtgs": {r['id']: mib.get(f"{OID_BASE}.3.1.4.{r['id']}", 0) for r in cfg['roads'] if r['type'] == 3},
                            "overrides": {tl['roadIndex']: mib.get(f"{OID_BASE}.4.1.2.{tl['roadIndex']}", 0) for tl in cfg['trafficLights']},
                            "links": {f"{l['src']}.{l['dest']}": mib.get(f"{OID_BASE}.5.1.4.{l['src']}.{l['dest']}", 0) for l in cfg.get('links', [])}
                        }
                        resposta_encriptada = cifra.encrypt(json.dumps(estado_atual).encode('utf-8'))
                        novos_binds.append((oid, v2c.OctetString(resposta_encriptada)))
                        
                    elif tipo_comando == "SET_RTG":
                        mib[f"{OID_BASE}.3.1.4.{comando_json['via']}"] = comando_json["valor"]
                        novos_binds.append((oid, v2c.OctetString(cifra.encrypt(b'{"status": "sucesso"}'))))
                        
                    elif tipo_comando == "SET_OVERRIDE":
                        mib[f"{OID_BASE}.4.1.2.{comando_json['via']}"] = comando_json["modo"]
                        novos_binds.append((oid, v2c.OctetString(cifra.encrypt(b'{"status": "sucesso"}'))))
                        
                    elif tipo_comando == "SET_ALG":
                        mib[f"{OID_BASE}.1.6.0"] = comando_json["alg_id"]
                        novos_binds.append((oid, v2c.OctetString(cifra.encrypt(b'{"status": "sucesso"}'))))

                except InvalidToken:
                    print("[SEGURANÇA] Intrusão detetada! Falha na desencriptação do payload.")
                    v2c.apiPDU.setErrorStatus(resposta_pdu, 'authorizationError')
                    novos_binds.append((oid, valor))
                except Exception as erro:
                    print(f"[TÚNEL SEGURO] Erro interno ao processar comando: {erro}")
                    v2c.apiPDU.setErrorStatus(resposta_pdu, 'genErr')
                    novos_binds.append((oid, valor))
            
            # Bloquear acessos plain-text à MIB (A Obrigatoriedade do Túnel)
            elif oid_str in mib:
                print(f"[SEGURANÇA] Tentativa de escrita bloqueada ao OID nativo: {oid_str}")
                v2c.apiPDU.setErrorStatus(resposta_pdu, 'noAccess')
                novos_binds.append((oid, valor))
            else:
                novos_binds.append((oid, v2c.NoSuchInstance()))

        v2c.apiPDU.setVarBinds(resposta_pdu, novos_binds)
        snmpEngine.msgAndPduDsp.returnResponsePdu(snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, resposta_pdu, maxSizeResponseScopedPDU, stateReference, {})

class ResponderGetBloqueado(cmdrsp.GetCommandResponder):
    """Mata proativamente qualquer pedido GET em plain-text para proteger a topologia da rede."""
    def processPdu(self, snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, PDU, maxSizeResponseScopedPDU, stateReference):
        resposta_pdu = v2c.apiPDU.getResponse(PDU)
        binds = v2c.apiPDU.getVarBinds(PDU)
        novos_binds = []
        
        for oid, valor in binds:
            print(f"[SEGURANÇA] Bloqueada tentativa de escuta (GET) ao OID: {oid}. Requer PULL_STATE cifrado.")
            v2c.apiPDU.setErrorStatus(resposta_pdu, 'noAccess')
            novos_binds.append((oid, valor))
            
        v2c.apiPDU.setVarBinds(resposta_pdu, novos_binds)
        snmpEngine.msgAndPduDsp.returnResponsePdu(snmpEngine, messageProcessingModel, securityModel, securityName, securityLevel, contextEngineId, contextName, pduVersion, resposta_pdu, maxSizeResponseScopedPDU, stateReference, {})


# =====================================================================
# 4. LÓGICA DE SIMULAÇÃO E ESTATÍSTICAS
# =====================================================================
async def disparar_alerta_trap(id_via, numero_carros):
    """Envia uma Trap SNMP assíncrona notificando o Dashboard de um congestionamento severo."""
    try:
        await sendNotification(
            hlapiSnmpEngine(),
            CommunityData('public', mpModel=1),
            UdpTransportTarget(('127.0.0.1', 16216)),
            ContextData(),
            'trap',
            NotificationType(ObjectIdentity('1.3.6.1.4.1.2026.1.0.1')).addVarBinds(
                ('1.3.6.1.4.1.2026.1.1.1', Integer32(id_via)),
                ('1.3.6.1.4.1.2026.1.1.2', Integer32(numero_carros))
            )
        )
        print(f"[TRAP ENVIADA] Alerta Crítico: Congestionamento na Via {id_via}!")
    except Exception:
        pass

def resetar_metricas_mib(dicionario_mib, configuracao):
    dicionario_mib[f"{OID_BASE}.1.7.0"] = 0
    for rua in configuracao['roads']:
        dicionario_mib[f"{OID_BASE}.3.1.6.{rua['id']}"] = rua.get('initialCount', 0)
    for ligacao in configuracao.get('links', []):
        dicionario_mib[f"{OID_BASE}.5.1.4.{ligacao['src']}.{ligacao['dest']}"] = 0

async def iniciar_sistema_central():
    """Configura o motor SNMP, instancia a simulação física e executa o ciclo de vida principal."""
    motor_snmp = engine.SnmpEngine()
    configuracao_snmp = config
    configuracao_snmp.addTransport(motor_snmp, udp.domainName, udp.UdpTransport().openServerMode(('127.0.0.1', 16161)))
    configuracao_snmp.addV1System(motor_snmp, 'my-area', 'public')
    configuracao_snmp.addVacmUser(motor_snmp, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6), (1, 3, 6))
    contexto_snmp = context.SnmpContext(motor_snmp)
    
    ResponderSetSeguro(motor_snmp, contexto_snmp)
    ResponderGetBloqueado(motor_snmp, contexto_snmp)

    MAPA_ALGORITMOS = {1: "ROUND_ROBIN", 2: "HEURISTICA", 3: "RL", 4: "BACKPRESSURE"}
    
    def instanciar_sistema_decisao(nome_algoritmo):
        if nome_algoritmo == "ROUND_ROBIN": return SistemaDecisaoRoundRobin(mib, cfg)
        elif nome_algoritmo == "HEURISTICA": return SistemaDecisaoOcupacao(mib, cfg)
        elif nome_algoritmo == "RL": return SistemaDecisaoRL(mib, cfg)
        else: return SistemaDecisaoBackpressure(mib, cfg)

    id_algoritmo_atual = mib.get(f"{OID_BASE}.1.6.0", 4)
    algoritmo_ativo = MAPA_ALGORITMOS.get(id_algoritmo_atual, "BACKPRESSURE")
    sistema_decisao = instanciar_sistema_decisao(algoritmo_ativo)
    
    # Fase de Treino do Reinforcement Learning
    if algoritmo_ativo == "RL":
        if sistema_decisao.precisa_treino:
            simulador_treino = SistemaSimulacao(mib, cfg)
            print("\n[TREINO RL] A iniciar simulação acelerada (10.000 ciclos virtuais)...")
            sistema_decisao.epsilon = 0.5 
            
            for ciclo in range(10000):
                simulador_treino.executar_passo(5) 
                await sistema_decisao.update(fast_forward_step=5)
                if ciclo % 250 == 0: 
                    print(f"[TREINO RL] Progresso: {ciclo}/10000 ciclos | Memória: {len(sistema_decisao.q_table)} estados")

            print("[TREINO RL] Treino concluído! A persistir conhecimento no disco...")
            sistema_decisao.guardar_cerebro()
            sistema_decisao.epsilon = 0.05 
        else:
            print("\n[TREINO RL] Cérebro detetado em disco. A saltar fase de treino!")
    
    resetar_metricas_mib(mib, cfg)
    motor_fisica = SistemaSimulacao(mib, cfg)
    
    # Prepara Ficheiro de Logs CSV
    nome_ficheiro_csv = f"historico_simulacao_{algoritmo_ativo}.csv"
    try:
        with open(nome_ficheiro_csv, mode='w', newline='') as ficheiro:
            escritor = csv.writer(ficheiro, delimiter=';') 
            escritor.writerow(["Tempo (s)", "Algoritmo", "Total Escoados", "Fila Maxima", "Ocupacao Media"])
    except PermissionError:
        print(f"\n[ERRO CRÍTICO] O ficheiro {nome_ficheiro_csv} está aberto noutro programa (ex: Excel)!")
        sys.exit(1)

    async def ciclo_simulacao():
        nonlocal algoritmo_ativo, sistema_decisao, motor_fisica, nome_ficheiro_csv
        
        duracao_passo = cfg['geral']['simStepDuration']
        iteracao = 0
        marca_tempo_inicio = time.time()
        dicionario_traps_enviadas = {} 
        algoritmo_anterior = algoritmo_ativo

        print(f"\n=== SISTEMA CENTRAL A CORRER (UDP 16161) | Algoritmo: {algoritmo_ativo} ===")
        print(f"A exportar logs analíticos para: {nome_ficheiro_csv}")
        
        while True:
            # --- 1. VERIFICAR MUDANÇAS DINÂMICAS DE ALGORITMO ---
            id_novo_algoritmo = mib.get(f"{OID_BASE}.1.6.0", 4)
            algoritmo_ativo = MAPA_ALGORITMOS.get(id_novo_algoritmo, "BACKPRESSURE")
            
            if algoritmo_ativo != algoritmo_anterior:
                print(f"\n[HOT-SWAP] Alteração recebida: Mudando de {algoritmo_anterior} para {algoritmo_ativo}...")
                sistema_decisao = instanciar_sistema_decisao(algoritmo_ativo)
                
                if algoritmo_ativo == "RL":
                    simulador_treino = SistemaSimulacao(mib, cfg)
                    print("[TREINO RL] A efetuar treino acelerado para adaptação...")
                    sistema_decisao.epsilon = 0.5 
                    for c in range(10000):
                        simulador_treino.executar_passo(5) 
                        await sistema_decisao.update(fast_forward_step=5)
                    sistema_decisao.guardar_cerebro()
                    sistema_decisao.epsilon = 0.05 
                    print("[TREINO RL] Adaptação concluída.")
                
                resetar_metricas_mib(mib, cfg)
                motor_fisica = SistemaSimulacao(mib, cfg)
                marca_tempo_inicio = time.time()
                dicionario_traps_enviadas = {}
                iteracao = 0
                
                nome_ficheiro_csv = f"historico_simulacao_{algoritmo_ativo}.csv"
                try:
                    with open(nome_ficheiro_csv, mode='w', newline='') as f:
                        writer = csv.writer(f, delimiter=';') 
                        writer.writerow(["Tempo (s)", "Algoritmo", "Total Escoados", "Fila Maxima", "Ocupacao Media"])
                except PermissionError:
                    print(f"\n[ERRO CSV] Falha de escrita. Ficheiro em uso: {nome_ficheiro_csv}")
                
                algoritmo_anterior = algoritmo_ativo
                print(f"[HOT-SWAP] Simulação reiniciada. Contadores a zero com {algoritmo_ativo}!")
            
            # --- 2. EXECUÇÃO DA FÍSICA E DA DECISÃO ---
            tempo_decorrido = int(time.time() - marca_tempo_inicio)
            mib[f"{OID_BASE}.1.7.0"] = tempo_decorrido
            
            motor_fisica.executar_passo(duracao_passo)
            await sistema_decisao.update(current_step=duracao_passo)
            
            # Forçar overrides manuais
            for semaforo in cfg['trafficLights']:
                id_rua = semaforo['roadIndex']
                modo_imposto = mib.get(f"{OID_BASE}.4.1.2.{id_rua}", 0)
                if modo_imposto == 1:
                    mib[f"{OID_BASE}.4.1.3.{id_rua}"] = 2 
                    mib[f"{OID_BASE}.4.1.4.{id_rua}"] = 99 
                elif modo_imposto == 2:
                    mib[f"{OID_BASE}.4.1.3.{id_rua}"] = 1 
                    mib[f"{OID_BASE}.4.1.4.{id_rua}"] = 99
            
            # --- 3. CÁLCULO DINÂMICO DE ESTATÍSTICAS E TRAPS ---
            vias_saida = [str(rua['id']) for rua in cfg['roads'] if rua.get('type') == 2]
            vias_internas = [rua['id'] for rua in cfg['roads'] if str(rua['id']) not in vias_saida]
            
            # BUG FIX: Conta todos os links que apontam para qualquer via do tipo 2
            total_escoados = sum(mib.get(f"{OID_BASE}.5.1.4.{ligacao['src']}.{ligacao['dest']}", 0) 
                                 for ligacao in cfg.get('links', []) 
                                 if str(ligacao['dest']) in vias_saida)
            
            maxima_fila = 0
            for id_via in vias_internas:
                fila_presente = mib.get(f"{OID_BASE}.3.1.6.{id_via}", 0)
                
                if fila_presente >= 20:
                    agora_trap = time.time()
                    if agora_trap - dicionario_traps_enviadas.get(id_via, 0) > 10.0:
                        asyncio.create_task(disparar_alerta_trap(id_via, fila_presente))
                        dicionario_traps_enviadas[id_via] = agora_trap

                if fila_presente > maxima_fila:
                    maxima_fila = fila_presente

            # Exportação de Logs para o Dashboard
            try:
                ocupacao_media = 0
                if len(vias_internas) > 0:
                    ocupacao_media = sum(mib.get(f"{OID_BASE}.3.1.6.{v}", 0) for v in vias_internas) / len(vias_internas)

                with open(nome_ficheiro_csv, mode='a', newline='') as ficheiro_log:
                    escritor_csv = csv.writer(ficheiro_log, delimiter=';')
                    escritor_csv.writerow([tempo_decorrido, algoritmo_ativo, total_escoados, maxima_fila, round(ocupacao_media, 2)])
            except Exception:
                pass 

            if iteracao % 4 == 0:
                print(f"[MONITOR {algoritmo_ativo}] T={tempo_decorrido}s | Escoados: {total_escoados} v | Fila Máx: {maxima_fila} v")
            
            iteracao += 1
            await asyncio.sleep(duracao_passo)

    await ciclo_simulacao()

if __name__ == "__main__":
    try:
        asyncio.run(iniciar_sistema_central())
    except KeyboardInterrupt:
        print("\n[SC] Sistema Central desligado em segurança pelo administrador.")