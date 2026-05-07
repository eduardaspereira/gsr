# ==============================================================================
# Ficheiro: cmc.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Consola de Monitorização e Controlo (Interface CLI). 
#            Permite ao administrador enviar comandos para o Sistema Central 
#            via terminal, utilizando o mesmo mecanismo de Túnel Seguro (JSON + Fernet) 
#            presente no Dashboard Gráfico.
# ==============================================================================

import sys
import base64
import json
import asyncio
import threading
import time
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pysnmp.hlapi.asyncio import *

# OID exclusivo para canalizar tráfego seguro
OID_TUNEL = "1.3.6.1.3.2026.99.1.0"

# Carregamento da configuração local
try:
    with open('Mapas/config4.json', 'r') as f:
        cfg_local = json.load(f)
except Exception:
    cfg_local = {'roads': [], 'trafficLights': []}

# Variáveis globais para estatísticas
stats_global = {
    "tempo": 0,
    "algo_id": 4,
    "escoados": 0,
    "escoados_anterior": 0,
    "tempo_anterior": time.time(),
    "vazao_atual": 0.0,
    "ocupacao_media": 0.0,
    "fila_max": 0,
    "via_pior": 0,
    "cfg": cfg_local
}

# =====================================================================
# 1. FUNÇÕES DE SEGURANÇA
# =====================================================================
def inicializar_cifra_segura():
    """
    Lê a password da linha de comandos, deriva a KEK e destranca a DEK 
    (Chave Mestra) armazenada no ficheiro 'seguranca.key'.
    """
    print("=====================================================")
    print("=== INICIALIZAÇÃO SEGURA (CMC CLI) ===")
    print("=====================================================")
    
    if len(sys.argv) < 2:
        print("[ERRO CRÍTICO] Password em falta!")
        print("Uso correto: python3 cmc.py <a_tua_password>")
        sys.exit(1)

    password_lida = sys.argv[1].encode()

    salt = b'GSR_UM_2026'
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    chave_cofre = base64.urlsafe_b64encode(kdf.derive(password_lida))
    ferramenta_cofre = Fernet(chave_cofre)

    try:
        with open("seguranca.key", "rb") as f:
            chave_encriptada = f.read()
        chave_mestra = ferramenta_cofre.decrypt(chave_encriptada)
        print("[OK] Chave carregada com sucesso. Túnel Seguro ativado!")
        return Fernet(chave_mestra)
    except Exception:
        print("[ERRO] Password incorreta ou ficheiro 'seguranca.key' em falta!")
        sys.exit(1)


# =====================================================================
# 2. FUNÇÕES DE REDE (SNMP)
# =====================================================================
async def enviar_comando_tunel(ip, porta, comunidade, dicionario_payload, cifra):
    """
    Serializa o comando num JSON, encripta-o com a Chave Mestra e envia
    o bloco opaco de bytes através de um pacote SNMP perfeitamente normal.
    """
    motor_snmp = SnmpEngine()
    
    # 1. Empacotar e Encriptar
    payload_json = json.dumps(dicionario_payload).encode('utf-8')
    payload_cifrado = cifra.encrypt(payload_json)
    
    # 2. Enviar via SET no Túnel Seguro (como OctetString)
    erro_ind, erro_est, indice_erro, binds = await setCmd(
        motor_snmp,
        CommunityData(comunidade, mpModel=1),
        UdpTransportTarget((ip, porta)),
        ContextData(),
        ObjectType(ObjectIdentity(OID_TUNEL), OctetString(payload_cifrado))
    )

    if erro_ind or erro_est:
        print("[ERRO DE REDE] O pacote seguro foi rejeitado ou falhou a entrega ao Sistema Central.")
    else:
        print("-> [SUCESSO] Comando seguro entregue e validado!")
        
    motor_snmp.transportDispatcher.closeDispatcher()


async def obter_dados_snmp(cifra):
    """Pooling contínuo (2Hz) para puxar o estado cifrado da rede através do Túnel."""
    while True:
        try:
            payload = {"comando": "PULL_STATE"}
            motor_snmp = SnmpEngine()
            payload_json = json.dumps(payload).encode('utf-8')
            payload_cifrado = cifra.encrypt(payload_json)
            
            erro_ind, erro_stat, indice_erro, binds = await setCmd(
                motor_snmp,
                CommunityData("public", mpModel=1),
                UdpTransportTarget(("127.0.0.1", 16161), timeout=1, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity(OID_TUNEL), OctetString(payload_cifrado))
            )
            motor_snmp.transportDispatcher.closeDispatcher()

            if not erro_ind and not erro_stat:
                for nome, valor in binds:
                    if str(nome) == OID_TUNEL:
                        resposta_limpa = cifra.decrypt(bytes(valor)).decode('utf-8')
                        dados = json.loads(resposta_limpa)

                        stats_global["tempo"] = dados.get("tempo", 0)
                        stats_global["algo_id"] = dados.get("algo_id", 4)
                        
                        # Recalcular estatísticas
                        estado_filas = dados.get("filas", {})
                        estado_links = dados.get("links", {})
                        estado_semaforos = dados.get("semaforos", {})
                        cfg = dados.get("cfg", stats_global["cfg"])  # Usar cfg recebido ou fallback ao local
                        stats_global["cfg"] = cfg
                        
                        # Escoados
                        vias_saida = [str(r['id']) for r in cfg.get('roads', []) if r.get('type') == 2]
                        total_escoados = sum(val for chave, val in estado_links.items() if chave.split('.')[1] in vias_saida)
                        stats_global["escoados"] = total_escoados
                        
                        # Calcular vazão 
                        agora = time.time()
                        if agora - stats_global["tempo_anterior"] >= 5.0:
                            stats_global["vazao_atual"] = ((total_escoados - stats_global["escoados_anterior"]) / (agora - stats_global["tempo_anterior"])) * 60.0
                            stats_global["tempo_anterior"] = agora
                            stats_global["escoados_anterior"] = total_escoados
                        
                        # Ocupação média
                        vias_internas = [r['id'] for r in cfg.get('roads', []) if r.get('type') == 1]
                        
                        # Se não houver vias tipo 1, calcular de todos os tipos que NÃO são entrada ou saída
                        if len(vias_internas) == 0:
                            vias_entrada_set = {r['id'] for r in cfg.get('roads', []) if r.get('type') == 3}
                            vias_saida_set = {r['id'] for r in cfg.get('roads', []) if r.get('type') == 2}
                            vias_internas = [r['id'] for r in cfg.get('roads', []) if r['id'] not in vias_entrada_set and r['id'] not in vias_saida_set]
                        
                        if len(vias_internas) > 0:
                            ocupacao_total = sum(estado_filas.get(str(v), 0) for v in vias_internas)
                            stats_global["ocupacao_media"] = ocupacao_total / len(vias_internas)
                        else:
                            stats_global["ocupacao_media"] = 0.0
                        
                        # Pior fila - verificar todas as vias que não são de saída
                        vias_para_fila = [r['id'] for r in cfg.get('roads', []) if r.get('type') != 2]
                        
                        stats_global["fila_max"] = 0
                        stats_global["via_pior"] = 0
                        
                        for v in vias_para_fila:
                            fila_v = estado_filas.get(str(v), 0)
                            if fila_v > stats_global["fila_max"]:
                                stats_global["fila_max"] = fila_v
                                stats_global["via_pior"] = v
        except Exception as e:
            pass
        
        await asyncio.sleep(0.5)

def iniciar_atualizador_stats(cifra):
    """Inicia thread de atualização de estatísticas."""
    threading.Thread(target=lambda: asyncio.run(obter_dados_snmp(cifra)), daemon=True).start()

def exibir_stats():
    """Exibe as estatísticas atuais."""
    tempo_sc = stats_global["tempo"]
    str_relogio = f"{tempo_sc // 3600:02d}:{(tempo_sc % 3600) // 60:02d}:{tempo_sc % 60:02d}"
    
    nomes_algos = {1: "ROUND_ROBIN", 2: "HEURISTICA", 3: "RL", 4: "BACKPRESSURE"}
    algo_nome = nomes_algos.get(stats_global["algo_id"], "DESCONHECIDO")
    
    # Debug: verificar se os dados estão a ser atualizados
    cfg = stats_global.get("cfg", {})
    num_vias = len(cfg.get('roads', []))
    
    return f"""
ESTATISTICAS EM TEMPO REAL
Tempo: {str_relogio}
Algoritmo: {algo_nome}
Escoados: {stats_global["escoados"]} v
Vazao: {stats_global["vazao_atual"]:.1f} v/min
Ocupacao Media: {stats_global["ocupacao_media"]:.1f} v/via
Pior Fila: {stats_global["fila_max"]}v (V{stats_global["via_pior"]})
"""


async def enviar_comando_snmp_puro(ip, porta, comunidade, oid, valor, tipo_snmp):
    """
    [FUNÇÃO DE TESTE / LEGACY] 
    Envia um pacote SNMP clássico em texto limpo.
    Nota: O Sistema Central atual (sc.py) vai rejeitar e bloquear este tráfego
    por questões de segurança (Defesa Ativa). Útil para demonstrar a robustez do projeto.
    """
    motor_snmp = SnmpEngine()
    
    erro_ind, erro_est, indice_erro, binds = await setCmd(
        motor_snmp,
        CommunityData(comunidade, mpModel=1), 
        UdpTransportTarget((ip, porta)),
        ContextData(),
        ObjectType(ObjectIdentity(oid), tipo_snmp(valor))
    )

    if erro_ind:
        print(f"[Erro de Rede] {erro_ind} -> O Sistema Central está a correr?")
    elif erro_est:
        print(f"[Erro SNMP] {erro_est.prettyPrint()} -> (Provavelmente bloqueado pela segurança do SC)")
    else:
        print(f"-> Sucesso! Comando enviado diretamente para a MIB.")
        
    motor_snmp.transportDispatcher.closeDispatcher()


# =====================================================================
# 3. INTERFACE DE UTILIZADOR (LOOP CLI)
# =====================================================================
def iniciar_cmc(cifra):
    """Loop principal de interpretação de comandos da consola."""
    print("=====================================================")
    print("      CMC: Consola de Monitorização e Controlo       ")
    print("=====================================================")
    print("Comandos disponíveis:")
    print("  rtg <via> <valor>  - Altera taxa geradora. Ex: rtg 101 10")
    print("  o <via> <modo>     - Override (0: Auto | 1: Vermelho | 2: Verde). Ex: o 101 2")
    print("  alg <modo>         - Algoritmo (1:RR | 2:Heuristica | 3:RL | 4:BP). Ex: alg 3")
    print("  sair               - Termina a consola")
    print("=====================================================")
    
    # Iniciar thread de atualização de estatísticas
    iniciar_atualizador_stats(cifra)
    time.sleep(0.5)  # Dar tempo para a primeira atualização
    
    ip_sc = "127.0.0.1"
    porta_sc = 16161
    comunidade = "public"
    ultima_atualizacao = time.time()

    while True:
        try:
            # Atualizar estatísticas a cada 0.5s
            agora = time.time()
            if agora - ultima_atualizacao >= 0.5:
                os.system('clear' if os.name == 'posix' else 'cls')
                print("=====================================================")
                print("      CMC: Consola de Monitorização e Controlo       ")
                print("=====================================================")
                print("Comandos disponíveis:")
                print("  rtg <via> <valor>  - Altera taxa geradora. Ex: rtg 101 10")
                print("  o <via> <modo>     - Override (0: Auto | 1: Vermelho | 2: Verde). Ex: o 101 2")
                print("  alg <modo>         - Algoritmo (1:RR | 2:Heuristica | 3:RL | 4:BP). Ex: alg 3")
                print("  sair               - Termina a consola")
                print("=====================================================")
                print(exibir_stats())
                ultima_atualizacao = agora
            
            # Input não-bloqueante
            print("CMC> ", end='', flush=True)
            comando = input().strip().lower()
            
            if comando == 'sair':
                break
            if not comando:
                continue
                
            partes = comando.split()
            
            # --- RTG (Injeção de Tráfego) ---
            if partes[0] == 'rtg' and len(partes) == 3:
                id_via = int(partes[1])
                novo_rtg = int(partes[2])
                payload = {"comando": "SET_RTG", "via": id_via, "valor": novo_rtg}
                asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload, cifra))
                
            # --- OVERRIDE (Forçar Semáforo) ---
            elif partes[0] == 'o' and len(partes) == 3:
                id_via = int(partes[1])
                modo = int(partes[2])
                if modo not in [0, 1, 2]:
                    print("[ERRO] Modo de override inválido. Usa 0, 1 ou 2.")
                    continue
                
                payload = {"comando": "SET_OVERRIDE", "via": id_via, "modo": modo}
                asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload, cifra))
                
            # --- ALGORITMO (Mudança de Motor de Decisão) ---
            elif partes[0] == 'alg' and len(partes) == 2:
                id_algoritmo = int(partes[1])
                if id_algoritmo not in [1, 2, 3, 4]:
                    print("[ERRO] Algoritmo inválido. Usa 1, 2, 3 ou 4.")
                    continue
                
                payload = {"comando": "SET_ALG", "alg_id": id_algoritmo}
                asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload, cifra))
                
            else:
                print("[ERRO] Comando inválido. Revê as instruções acima.")
                
        except ValueError:
            print("[ERRO] Certifica-te de que os valores inseridos são números inteiros.")
        except KeyboardInterrupt:
            print("\n[CMC] A encerrar a Consola...")
            break


if __name__ == "__main__":
    # 1. Autenticação na Fronteira
    cifra_ativa = inicializar_cifra_segura()
    
    # 2. Iniciar Aplicação
    iniciar_cmc(cifra_ativa)