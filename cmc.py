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

# Carregamento da configuração local (Arranca no config4.json / Índice 3)
try:
    with open('Mapas/config4.json', 'r') as f:
        cfg_local = json.load(f)
except Exception:
    cfg_local = {'roads': [], 'trafficLights': []}

# Variáveis globais para estatísticas
stats_global = {
    "tempo": 0,
    "algo_id": 4,
    "mapa_id": 4,
    "escoados": 0,
    "escoados_anterior": 0,
    "tempo_anterior": time.time(),
    "vazao_atual": 0.0,
    "ocupacao_media": 0.0,
    "fila_max": 0,
    "via_pior": 0,
    "cfg": cfg_local,
    "rtgs": {}  # <-- Adicionado para guardar os RTGs
}

# =====================================================================
# 1. FUNÇÕES DE SEGURANÇA
# =====================================================================
def inicializar_cifra_segura():
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
        time.sleep(1) # Pausa para ler antes de a interface arrancar
        return Fernet(chave_mestra)
    except Exception:
        print("[ERRO] Password incorreta ou ficheiro 'seguranca.key' em falta!")
        sys.exit(1)


# =====================================================================
# 2. FUNÇÕES DE REDE (SNMP)
# =====================================================================
async def enviar_comando_tunel(ip, porta, comunidade, dicionario_payload, cifra):
    motor_snmp = SnmpEngine()
    
    payload_json = json.dumps(dicionario_payload).encode('utf-8')
    payload_cifrado = cifra.encrypt(payload_json)
    
    erro_ind, erro_est, indice_erro, binds = await setCmd(
        motor_snmp,
        CommunityData(comunidade, mpModel=1),
        UdpTransportTarget((ip, porta)),
        ContextData(),
        ObjectType(ObjectIdentity(OID_TUNEL), OctetString(payload_cifrado))
    )
    motor_snmp.transportDispatcher.closeDispatcher()

    # Em vez de imprimir e quebrar a UI, devolvemos a mensagem de sucesso/erro
    if erro_ind or erro_est:
        return "[ERRO DE REDE] O pacote seguro foi rejeitado ou falhou."
    else:
        return f"[SUCESSO] Comando {dicionario_payload['comando']} entregue e validado!"


async def obter_dados_snmp(cifra):
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
                        
                        novo_algo = dados.get("algo_id", 4)
                        novo_mapa = dados.get("mapa_id", 4)
                        
                        # Sincronização automática com a Interface Gráfica
                        if novo_algo != stats_global["algo_id"] or novo_mapa != stats_global["mapa_id"]:
                            stats_global["algo_id"] = novo_algo
                            stats_global["mapa_id"] = novo_mapa
                            stats_global["escoados_anterior"] = 0
                            stats_global["tempo_anterior"] = time.time()
                            stats_global["vazao_atual"] = 0.0
                            
                        # <-- Captura dos RTGs vindos do servidor
                        stats_global["rtgs"] = dados.get("rtgs", {})

                        estado_filas = dados.get("filas", {})
                        estado_links = dados.get("links", {})
                        cfg = dados.get("cfg", stats_global["cfg"])  
                        stats_global["cfg"] = cfg
                        
                        vias_saida = [str(r['id']) for r in cfg.get('roads', []) if r.get('type') == 2]
                        total_escoados = sum(val for chave, val in estado_links.items() if chave.split('.')[1] in vias_saida)
                        stats_global["escoados"] = total_escoados
                        
                        agora = time.time()
                        if agora - stats_global["tempo_anterior"] >= 5.0:
                            stats_global["vazao_atual"] = ((total_escoados - stats_global["escoados_anterior"]) / (agora - stats_global["tempo_anterior"])) * 60.0
                            stats_global["tempo_anterior"] = agora
                            stats_global["escoados_anterior"] = total_escoados
                        
                        vias_internas = [r['id'] for r in cfg.get('roads', []) if r.get('type') == 1]
                        if len(vias_internas) == 0:
                            vias_entrada_set = {r['id'] for r in cfg.get('roads', []) if r.get('type') == 3}
                            vias_saida_set = {r['id'] for r in cfg.get('roads', []) if r.get('type') == 2}
                            vias_internas = [r['id'] for r in cfg.get('roads', []) if r['id'] not in vias_entrada_set and r['id'] not in vias_saida_set]
                        
                        if len(vias_internas) > 0:
                            ocupacao_total = sum(estado_filas.get(str(v), 0) for v in vias_internas)
                            stats_global["ocupacao_media"] = ocupacao_total / len(vias_internas)
                        else:
                            stats_global["ocupacao_media"] = 0.0
                        
                        vias_para_fila = [r['id'] for r in cfg.get('roads', []) if r.get('type') != 2]
                        stats_global["fila_max"] = 0
                        stats_global["via_pior"] = 0
                        
                        for v in vias_para_fila:
                            fila_v = estado_filas.get(str(v), 0)
                            if fila_v > stats_global["fila_max"]:
                                stats_global["fila_max"] = fila_v
                                stats_global["via_pior"] = v
        except Exception:
            pass
        
        await asyncio.sleep(0.5)


def iniciar_atualizador_stats(cifra):
    threading.Thread(target=lambda: asyncio.run(obter_dados_snmp(cifra)), daemon=True).start()


def exibir_stats():
    tempo_sc = stats_global["tempo"]
    str_relogio = f"{tempo_sc // 3600:02d}:{(tempo_sc % 3600) // 60:02d}:{tempo_sc % 60:02d}"
    
    nomes_algos = {1: "ROUND_ROBIN", 2: "HEURISTICA", 3: "RL", 4: "BACKPRESSURE"}
    algo_nome = nomes_algos.get(stats_global["algo_id"], "DESCONHECIDO")
    mapa_nome = f"Mapa {stats_global['mapa_id']}"
    
    # <-- Formatação da string de RTGs para ser injetada no ecrã
    rtgs = stats_global.get("rtgs", {})
    str_rtgs = " | ".join([f"V{v}={rtgs[str(v)]}" for v in sorted(map(int, rtgs.keys()))]) if rtgs else "N/A"
    
    return f"""=====================================================
      CMC: Consola de Monitorização e Controlo       
=====================================================
Topologia: {mapa_nome} | Algoritmo: {algo_nome} | Tempo: {str_relogio}
-----------------------------------------------------
Escoados: {stats_global["escoados"]} v
Vazao: {stats_global["vazao_atual"]:.1f} v/min
Ocupacao Media: {stats_global["ocupacao_media"]:.1f} v/via
Pior Fila: {stats_global["fila_max"]}v (V{stats_global["via_pior"]})
RTGs (Entradas): {str_rtgs}
====================================================="""


# =====================================================================
# 3. INTERFACE DE UTILIZADOR (TUI LOOP)
# =====================================================================
def iniciar_cmc(cifra):
    if os.name == 'nt':
        os.system('color') # Ativa códigos ANSI no Windows CMD/Powershell
        
    os.system('clear' if os.name == 'posix' else 'cls')
    
    iniciar_atualizador_stats(cifra)
    time.sleep(0.5) 
    
    # Atualiza a metade superior do ecrã a cada 0.5s via background thread
    def atualizador_ui():
        while True:
            time.sleep(0.5)
            stats = exibir_stats()
            sys.stdout.write("\033[s") # Guarda posição do cursor (o teu input)
            sys.stdout.write("\033[1;1H") # Vai para a Linha 1 do terminal
            for linha in stats.strip().split('\n'):
                sys.stdout.write(linha + "\033[K\n") # Imprime e limpa lixo da linha
            sys.stdout.write("\033[u") # Restaura o cursor onde tu estavas a escrever!
            sys.stdout.flush()

    threading.Thread(target=atualizador_ui, daemon=True).start()
    
    ip_sc = "127.0.0.1"
    porta_sc = 16161
    comunidade = "public"
    
    # Renderiza a Ajuda uma única vez abaixo das métricas (Linha 14)
    sys.stdout.write("\033[14;1H")
    print("Comandos disponíveis:")
    print("  rtg <via> <val>  - Altera taxa geradora. Ex: rtg 101 10.5")
    print("  o <via> <modo>   - Override (0: Auto | 1: Verm | 2: Verde). Ex: o 101 2")
    print("  alg <modo>       - Algoritmo (1:RR | 2:Heuristica | 3:RL | 4:BP). Ex: alg 3")
    print("  mapa <id>        - Muda topologia (1:Mapa1 | 2:Mapa2 | 3:Mapa3 | 4:Mapa4)")
    print("  sair             - Termina a consola")
    
    mensagem_sistema = "A aguardar comandos..."

    while True:
        try:
            # Imprime mensagens de sucesso ou erro (Linha 21)
            sys.stdout.write(f"\033[21;1H\033[K> {mensagem_sistema}\n")
            
            # Reposiciona e bloqueia na linha de Input (Linha 22)
            sys.stdout.write("\033[22;1H\033[K")
            comando = input("CMC> ").strip().lower()
            
            # Ao dar enter, o terminal gera uma linha nova (23). Limpamos logo!
            sys.stdout.write("\033[23;1H\033[K")
            
            if comando == 'sair':
                os.system('clear' if os.name == 'posix' else 'cls')
                break
            if not comando:
                continue
                
            partes = comando.split()
            
            # --- RTG (Injeção de Tráfego) ---
            if partes[0] == 'rtg' and len(partes) == 3:
                id_via = int(partes[1])
                novo_rtg = float(partes[2])
                payload = {"comando": "SET_RTG", "via": id_via, "valor": novo_rtg}
                mensagem_sistema = asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload, cifra))
                
            # --- OVERRIDE (Forçar Semáforo) ---
            elif partes[0] == 'o' and len(partes) == 3:
                id_via = int(partes[1])
                modo = int(partes[2])
                if modo not in [0, 1, 2]:
                    mensagem_sistema = "[ERRO] Modo de override inválido. Usa 0, 1 ou 2."
                    continue
                
                payload = {"comando": "SET_OVERRIDE", "via": id_via, "modo": modo}
                mensagem_sistema = asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload, cifra))
                
            # --- MAPA (Mudança de Topologia) ---
            elif partes[0] == 'mapa' and len(partes) == 2:
                id_mapa = int(partes[1])
                if id_mapa not in [1, 2, 3, 4]:
                    mensagem_sistema = "[ERRO] Mapa inválido. Usa 1, 2, 3 ou 4."
                    continue
                
                payload = {"comando": "SET_MAPA", "mapa_id": id_mapa}
                mensagem_sistema = asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload, cifra))
                
            # --- ALGORITMO (Mudança de Motor de Decisão) ---
            elif partes[0] == 'alg' and len(partes) == 2:
                id_algoritmo = int(partes[1])
                if id_algoritmo not in [1, 2, 3, 4]:
                    mensagem_sistema = "[ERRO] Algoritmo inválido. Usa 1, 2, 3 ou 4."
                    continue
                
                payload = {"comando": "SET_ALG", "alg_id": id_algoritmo}
                mensagem_sistema = asyncio.run(enviar_comando_tunel(ip_sc, porta_sc, comunidade, payload, cifra))
                
            else:
                mensagem_sistema = "[ERRO] Comando inválido. Revê as instruções acima."
                
        except ValueError:
            mensagem_sistema = "[ERRO] Certifica-te de que os valores numéricos inseridos são válidos."
        except KeyboardInterrupt:
            os.system('clear' if os.name == 'posix' else 'cls')
            print("\n[CMC] A encerrar a Consola...")
            break


if __name__ == "__main__":
    cifra_ativa = inicializar_cifra_segura()
    iniciar_cmc(cifra_ativa)