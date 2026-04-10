import pygame
import sys
import asyncio
import threading
import json
import time # NOVO: Necessário para calcular a Vazão por minuto
from pysnmp.hlapi.asyncio import *

# =====================================================================
# 1. CARREGAR CONFIGURAÇÃO
# =====================================================================
with open('config.json', 'r') as f:
    cfg = json.load(f)

estado_semaforos = {tl['roadIndex']: 1 for tl in cfg['trafficLights']}
estado_filas = {r['id']: r.get('initialCount', 0) for r in cfg['roads']}
estado_rtg = {r['id']: r.get('rtg', 0) for r in cfg['roads'] if r['type'] == 3}
estado_override = {tl['roadIndex']: 0 for tl in cfg['trafficLights']} 
estado_links = {f"{l['src']}.{l['dest']}": 0 for l in cfg.get('links', [])} # NOVO: Lê a passagem de todos os carros!

snmp_loop = None 

# =====================================================================
# 2. CLIENTE SNMP
# =====================================================================
async def obter_dados_snmp():
    snmpEngine = SnmpEngine()
    oids = []
    for via in estado_semaforos.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.4.1.3.{via}')))
    for via in estado_filas.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.3.1.6.{via}')))
    for via in estado_rtg.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.3.1.4.{via}')))
    for via in estado_override.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.4.1.2.{via}')))
    for link in estado_links.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.5.1.4.{link}'))) # NOVO

    while True:
        try:
            errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
                snmpEngine, CommunityData('public', mpModel=1),
                UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0),
                ContextData(), *oids
            )
            if not errorIndication and not errorStatus:
                idx = 0
                for via in estado_semaforos.keys(): estado_semaforos[via] = int(varBinds[idx][1]); idx += 1
                for via in estado_filas.keys(): estado_filas[via] = int(varBinds[idx][1]); idx += 1
                for via in estado_rtg.keys(): estado_rtg[via] = int(varBinds[idx][1]); idx += 1
                for via in estado_override.keys(): estado_override[via] = int(varBinds[idx][1]); idx += 1
                for link in estado_links.keys(): estado_links[link] = int(varBinds[idx][1]); idx += 1
        except Exception: pass 
        await asyncio.sleep(0.5)

async def enviar_novo_rtg_snmp(via, novo_rtg):
    oid = f'1.3.6.1.3.2026.1.3.1.4.{via}'
    await setCmd(SnmpEngine(), CommunityData('public', mpModel=1), UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0), ContextData(), ObjectType(ObjectIdentity(oid), Gauge32(novo_rtg)))

async def enviar_override_snmp(via, modo):
    oid = f'1.3.6.1.3.2026.1.4.1.2.{via}'
    await setCmd(SnmpEngine(), CommunityData('public', mpModel=1), UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0), ContextData(), ObjectType(ObjectIdentity(oid), Integer32(modo)))

def iniciar_thread_snmp():
    global snmp_loop
    snmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(snmp_loop)
    snmp_loop.run_until_complete(obter_dados_snmp())

# =====================================================================
# 3. INTERFACE GRÁFICA
# =====================================================================
def desenhar_grafo():
    pygame.init()
    ecra = pygame.display.set_mode((900, 700))
    pygame.display.set_caption("Dashboard Topológico - Filas de Espera")
    relogio = pygame.time.Clock()
    fonte_pequena = pygame.font.SysFont("Arial", 14, bold=True)
    fonte_grande = pygame.font.SysFont("Courier New", 20, bold=True)

    nos = {1: (300, 250), 2: (600, 250), 3: (600, 500), 4: (300, 500)}

    pontos_externos = {
        101: (100, 250), 94: (100, 500),  
        102: (600, 100), 91: (300, 100),  
        103: (800, 500), 92: (800, 250),  
        104: (300, 650), 93: (600, 650)   
    }

    arestas = {
        101: (pontos_externos[101], nos[1]), 102: (pontos_externos[102], nos[2]),
        103: (pontos_externos[103], nos[3]), 104: (pontos_externos[104], nos[4]),
        1: ((320, 240), (580, 240)), 5: ((580, 260), (320, 260)),
        2: ((610, 270), (610, 480)), 6: ((590, 480), (590, 270)),
        3: ((580, 510), (320, 510)), 7: ((320, 490), (580, 490)),
        4: ((290, 480), (290, 270)), 8: ((310, 270), (310, 480)),
        91: (nos[1], pontos_externos[91]), 92: (nos[2], pontos_externos[92]),
        93: (nos[3], pontos_externos[93]), 94: (nos[4], pontos_externos[94])
    }

    texto_input = ""
    
    # Variáveis para cálculo de Vazão
    tempo_anterior = time.time()
    escoados_anterior = 0
    vazao_atual = 0.0

    while True:
        agora = time.time()
        
        # --- CÁLCULO DE ESTATÍSTICAS ---
        saidas = ['91', '92', '93', '94']
        total_escoados = sum(val for key, val in estado_links.items() if any(key.endswith(f".{s}") for s in saidas))
        
        vias_internas = [1, 2, 3, 4, 5, 6, 7, 8]
        ocupacao_media = sum(estado_filas.get(v, 0) for v in vias_internas) / len(vias_internas) if vias_internas else 0
        
        vias_todas = [101, 102, 103, 104] + vias_internas
        max_fila = 0
        max_via = 0
        for v in vias_todas:
            if estado_filas.get(v, 0) > max_fila:
                max_fila = estado_filas.get(v, 0)
                max_via = v

        if agora - tempo_anterior >= 15.0: # Atualiza a velocidade a cada 2s
            vazao_atual = ((total_escoados - escoados_anterior) / (agora - tempo_anterior)) * 60.0
            tempo_anterior = agora
            escoados_anterior = total_escoados
        # -------------------------------

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT: pygame.quit(); sys.exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE: texto_input = texto_input[:-1]
                elif evento.key == pygame.K_RETURN:
                    try:
                        p = texto_input.strip().split(' ')
                        if len(p) == 2: asyncio.run_coroutine_threadsafe(enviar_novo_rtg_snmp(int(p[0]), int(p[1])), snmp_loop)
                        elif len(p) == 3 and p[0].upper() == 'O': asyncio.run_coroutine_threadsafe(enviar_override_snmp(int(p[1]), int(p[2])), snmp_loop)
                    except: pass
                    texto_input = ""
                elif evento.unicode.isprintable(): texto_input += evento.unicode

        ecra.fill((30, 35, 40)) 

        # DESENHAR GRAFO
        for via_id, (p_origem, p_destino) in arestas.items():
            cor_linha = (80, 80, 80) 
            if via_id in estado_semaforos:
                estado = estado_semaforos[via_id]
                if estado == 1: cor_linha = (200, 50, 50) 
                elif estado == 2: cor_linha = (50, 200, 50) 
                elif estado == 3: cor_linha = (200, 150, 50) 

            pygame.draw.line(ecra, cor_linha, p_origem, p_destino, 6)
            mid_x, mid_y = (p_origem[0] + p_destino[0]) // 2, (p_origem[1] + p_destino[1]) // 2
            carros = estado_filas.get(via_id, 0)
            
            if estado_override.get(via_id, 0) != 0:
                pygame.draw.circle(ecra, (255, 200, 0), (mid_x, mid_y), 18)
                ecra.blit(fonte_pequena.render("[M]", True, (255, 200, 0)), (mid_x - 10, mid_y - 32))

            cor_badge = (200, 100, 0) if carros > 15 else (50, 100, 150)
            pygame.draw.circle(ecra, cor_badge, (mid_x, mid_y), 14)
            pygame.draw.circle(ecra, (255, 255, 255), (mid_x, mid_y), 14, 2)
            
            txt_surface = fonte_pequena.render(str(carros), True, (255, 255, 255))
            ecra.blit(txt_surface, txt_surface.get_rect(center=(mid_x, mid_y)))
            ecra.blit(fonte_pequena.render(f"V{via_id}", True, (150, 150, 150)), (mid_x + 15, mid_y + 15))

        for nid, pos in nos.items():
            pygame.draw.circle(ecra, (40, 45, 50), pos, 25)
            pygame.draw.circle(ecra, (200, 200, 200), pos, 25, 3)
            txt_surface = fonte_grande.render(f"C{nid}", True, (255, 255, 255))
            ecra.blit(txt_surface, txt_surface.get_rect(center=pos))

        # --- SCOREBOARD ESTATÍSTICO (TOPO) ---
        pygame.draw.rect(ecra, (15, 20, 25), (0, 0, 900, 70))
        pygame.draw.line(ecra, (50, 200, 50), (0, 70), (900, 70), 2)
        ecra.blit(fonte_grande.render("METRICAS DE REDE", True, (255, 255, 255)), (10, 10))
        stats_str = f"Escoados: {total_escoados} v | Vazão: {vazao_atual:.1f} v/min | Ocupação Média: {ocupacao_media:.1f} v/via | Pior Fila: {max_fila}v (Via {max_via})"
        ecra.blit(fonte_pequena.render(stats_str, True, (200, 200, 200)), (10, 40))

        # --- CONSOLA DE COMANDOS (FUNDO) ---
        pygame.draw.rect(ecra, (20, 25, 30), (0, 600, 900, 100))
        status_rtg = f"RTGs: O(101)={estado_rtg.get(101,0)} | N(102)={estado_rtg.get(102,0)} | E(103)={estado_rtg.get(103,0)} | S(104)={estado_rtg.get(104,0)}"
        ecra.blit(fonte_pequena.render(status_rtg, True, (150, 200, 255)), (20, 610))
        ecra.blit(fonte_pequena.render("RTG: <Via> <Valor> | OVERRIDE: O <Via> <0=Auto, 1=Verde, 2=Vermelho>", True, (150, 150, 150)), (20, 640))
        ecra.blit(fonte_grande.render(f"CMC> {texto_input}_", True, (255, 200, 50)), (20, 670))
        
        pygame.display.flip()
        relogio.tick(30)

if __name__ == "__main__":
    threading.Thread(target=iniciar_thread_snmp, daemon=True).start()
    desenhar_grafo()