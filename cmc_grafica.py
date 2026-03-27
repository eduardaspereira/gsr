import pygame
import sys
import asyncio
import threading
import time
import json
from pysnmp.hlapi.asyncio import *

# =====================================================================
# 1. CARREGAR CONFIGURAÇÃO
# =====================================================================
with open('config.json', 'r') as f:
    cfg = json.load(f)

# Inicializa estados a partir do JSON
estado_semaforos = {tl['roadIndex']: 1 for tl in cfg['trafficLights']}
estado_rtg = {r['id']: r['rtg'] for r in cfg['roads']}
snmp_loop = None 

# =====================================================================
# 2. CLIENTE SNMP DINÂMICO
# =====================================================================
async def obter_dados_snmp():
    snmpEngine = SnmpEngine()
    oids = []
    
    # Gerar OIDs dinamicamente com base nas vias que existem no config
    for via in estado_semaforos.keys():
        oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.4.1.3.{via}')))
    for via in estado_rtg.keys():
        oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.3.1.4.{via}')))

    while True:
        try:
            errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
                snmpEngine, CommunityData('public', mpModel=1),
                UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0),
                ContextData(), *oids
            )

            if not errorIndication and not errorStatus:
                # O array varBinds volta na mesma ordem em que os OIDs foram pedidos
                idx = 0
                for via in estado_semaforos.keys():
                    estado_semaforos[via] = int(varBinds[idx][1])
                    idx += 1
                for via in estado_rtg.keys():
                    estado_rtg[via] = int(varBinds[idx][1])
                    idx += 1
        except Exception:
            pass 
        await asyncio.sleep(1)

async def enviar_novo_rtg_snmp(via, novo_rtg):
    oid = f'1.3.6.1.3.2026.1.3.1.4.{via}'
    await setCmd(
        SnmpEngine(), CommunityData('public', mpModel=1),
        UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0),
        ContextData(), ObjectType(ObjectIdentity(oid), Gauge32(novo_rtg))
    )

def iniciar_thread_snmp():
    global snmp_loop
    snmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(snmp_loop)
    snmp_loop.run_until_complete(obter_dados_snmp())

# =====================================================================
# 3. LÓGICA DOS CARROS
# =====================================================================
class Carro:
    def __init__(self, via):
        self.via = via
        self.cor = (0, 180, 255) 
        
        if via == 1: self.rect = pygame.Rect(-20, 310, 20, 12)
        elif via == 2: self.rect = pygame.Rect(320, 310, 20, 12) # Nasce depois do C1
        elif via == 3: self.rect = pygame.Rect(850, 270, 20, 12)
        elif via == 5: self.rect = pygame.Rect(250, -20, 12, 20)
        elif via == 7: self.rect = pygame.Rect(510, -20, 12, 20)

    def atualizar(self, carros_existentes):
        vel = 2
        futuro_rect = self.rect.copy()
        
        if self.via in [1, 2]: futuro_rect.x += vel
        elif self.via == 3: futuro_rect.x -= vel
        elif self.via in [5, 7]: futuro_rect.y += vel
        
        cor_semaforo = estado_semaforos.get(self.via, 2) # Assume verde se não houver semáforo
        
        # Lógica de Paragem nos Semáforos
        if cor_semaforo in [1, 3]: 
            if self.via == 1 and 220 <= self.rect.right <= 240: return # Para no C1
            if self.via == 2 and 480 <= self.rect.right <= 500: return # Para no C2
            if self.via == 3 and 320 <= self.rect.left <= 340: return  # Para no C1 (vindo de Este)
            if self.via == 5 and 240 <= self.rect.bottom <= 260: return # Para no C1
            if self.via == 7 and 240 <= self.rect.bottom <= 260: return # Para no C2

        # Prevenir bater na traseira do carro da frente
        for c in carros_existentes:
            if c != self and futuro_rect.colliderect(c.rect): return
                
        self.rect = futuro_rect

# =====================================================================
# 4. INTERFACE GRÁFICA
# =====================================================================
def desenhar_mapa():
    pygame.init()
    ecra = pygame.display.set_mode((850, 650))
    pygame.display.set_caption("CMC Gráfica - Config Dinâmica")
    relogio = pygame.time.Clock()

    CORES_SEMAFORO = {1: (255, 50, 50), 2: (50, 255, 50), 3: (255, 200, 50)}
    fonte = pygame.font.SysFont("Arial", 16, bold=True)
    fonte_grande = pygame.font.SysFont("Arial", 20, bold=True)

    carros = []
    tempo_ultimo_spawn = {v: time.time() for v in estado_rtg.keys()}

    via_selecionada = None
    texto_input = ""

    while True:
        agora = time.time()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif evento.type == pygame.KEYDOWN:
                # Mapeia as teclas 1, 2, 3, 5, 7
                if evento.unicode in ['1', '2', '3', '5', '7']:
                    via_selecionada = int(evento.unicode)
                    texto_input = ""
                elif via_selecionada is not None:
                    if evento.key == pygame.K_BACKSPACE: texto_input = texto_input[:-1]
                    elif evento.key == pygame.K_RETURN and texto_input.isdigit():
                        if snmp_loop: asyncio.run_coroutine_threadsafe(enviar_novo_rtg_snmp(via_selecionada, int(texto_input)), snmp_loop)
                        texto_input = ""
                        via_selecionada = None
                    elif evento.unicode.isdigit(): texto_input += evento.unicode

        # Spawn dinâmico com base nas vias lidas do config
        for via in [1, 2, 3, 5, 7]:
            rtg_atual = estado_rtg.get(via, 0)
            if rtg_atual > 0 and agora - tempo_ultimo_spawn[via] > (60.0 / rtg_atual):
                carros.append(Carro(via))
                tempo_ultimo_spawn[via] = agora

        for carro in carros[:]:
            carro.atualizar(carros)
            if not ecra.get_rect().colliderect(carro.rect): carros.remove(carro)

        ecra.fill((40, 45, 50)) 

        # Desenhar Estradas
        pygame.draw.rect(ecra, (100, 100, 100), (0, 260, 850, 80)) # EW
        for x in range(10, 850, 40): pygame.draw.rect(ecra, (255, 255, 255), (x, 298, 20, 4))
        
        pygame.draw.rect(ecra, (100, 100, 100), (240, 50, 80, 500)) # C1 NS
        for y in range(50, 550, 40): pygame.draw.rect(ecra, (255, 255, 255), (278, y, 4, 20))

        pygame.draw.rect(ecra, (100, 100, 100), (500, 50, 80, 500)) # C2 NS
        for y in range(50, 550, 40): pygame.draw.rect(ecra, (255, 255, 255), (538, y, 4, 20))

        # Desenhar Semáforos lidos do config
        if 1 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[1]], (220, 325), 10)
        if 3 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[3]], (340, 275), 10)
        if 5 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[5]], (255, 240), 10)
        if 2 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[2]], (480, 325), 10)
        if 7 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[7]], (515, 240), 10)

        # Desenhar Carros (com contorno preto)
        for carro in carros:
            pygame.draw.rect(ecra, carro.cor, carro.rect)
            pygame.draw.rect(ecra, (0, 0, 0), carro.rect, 2)

        # Labels
        ecra.blit(fonte_grande.render("C1", True, (255, 255, 255)), (325, 350))
        ecra.blit(fonte_grande.render("C2", True, (255, 255, 255)), (585, 350))
        
        # Labels das Vias e RTG
        ecra.blit(fonte.render(f"Via 5 (Norte C1) | RTG: {estado_rtg.get(5, 0)}", True, (200, 200, 200)), (110, 20))
        ecra.blit(fonte.render(f"Via 7 (Norte C2) | RTG: {estado_rtg.get(7, 0)}", True, (200, 200, 200)), (580, 20))
        ecra.blit(fonte.render(f"Via 1 (Oeste) | RTG: {estado_rtg.get(1, 0)}", True, (200, 200, 200)), (20, 350))
        ecra.blit(fonte.render(f"Via 2 (C1->C2) | RTG: {estado_rtg.get(2, 0)}", True, (200, 200, 200)), (350, 350))
        ecra.blit(fonte.render(f"Via 3 (C2->C1) | RTG: {estado_rtg.get(3, 0)}", True, (200, 200, 200)), (650, 230))

        # Painel Inferior
        pygame.draw.rect(ecra, (20, 25, 30), (0, 570, 850, 80))
        ecra.blit(fonte.render("Controlos: Teclas 1, 2, 3, 5 ou 7 para escolher via e alterar RTG.", True, (150, 150, 150)), (20, 580))
        
        if via_selecionada is not None:
            txt_input = fonte_grande.render(f"A alterar Via {via_selecionada} -> Escreve o novo RTG: {texto_input}_ (Enter para gravar)", True, (255, 200, 50))
            ecra.blit(txt_input, (20, 610))

        pygame.display.flip()
        relogio.tick(60)

if __name__ == "__main__":
    threading.Thread(target=iniciar_thread_snmp, daemon=True).start()
    desenhar_mapa()