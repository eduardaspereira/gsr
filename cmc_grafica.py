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

estado_semaforos = {tl['roadIndex']: 1 for tl in cfg['trafficLights']}
estado_rtg = {r['id']: r['rtg'] for r in cfg['roads']}
snmp_loop = None 

# =====================================================================
# 2. CLIENTE SNMP DINÂMICO
# =====================================================================
async def obter_dados_snmp():
    snmpEngine = SnmpEngine()
    oids = []
    
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
        elif via == 10: self.rect = pygame.Rect(850, 270, 20, 12) # Nova Via 10 (Entrada Este)
        elif via == 5: self.rect = pygame.Rect(250, -20, 12, 20)  
        elif via == 7: self.rect = pygame.Rect(510, -20, 12, 20)  
        elif via == 8: self.rect = pygame.Rect(290, 650, 12, 20)  
        elif via == 9: self.rect = pygame.Rect(550, 650, 12, 20)  

    def atualizar(self, carros_existentes):
        vel = 2
        futuro_rect = self.rect.copy()
        
        if self.via == 1: futuro_rect.x += vel
        elif self.via == 10: futuro_rect.x -= vel
        elif self.via in [5, 7]: futuro_rect.y += vel
        elif self.via in [8, 9]: futuro_rect.y -= vel
        
        # Lógica de Paragem (Apenas no Vermelho == 1)
        if self.via == 1:
            if estado_semaforos.get(1, 2) == 1 and 220 <= self.rect.right <= 240: return
            if estado_semaforos.get(2, 2) == 1 and 480 <= self.rect.right <= 500: return
        elif self.via == 10:
            # Pára no C2 (Semáforo 10)
            if estado_semaforos.get(10, 2) == 1 and 580 <= self.rect.left <= 600: return
            # Pára no C1 (Semáforo 3)
            if estado_semaforos.get(3, 2) == 1 and 320 <= self.rect.left <= 340: return
        elif self.via == 5:
            if estado_semaforos.get(5, 2) == 1 and 240 <= self.rect.bottom <= 260: return
        elif self.via == 7:
            if estado_semaforos.get(7, 2) == 1 and 240 <= self.rect.bottom <= 260: return
        elif self.via == 8:
            if estado_semaforos.get(8, 2) == 1 and 340 <= self.rect.top <= 360: return
        elif self.via == 9:
            if estado_semaforos.get(9, 2) == 1 and 340 <= self.rect.top <= 360: return

        # Colisões em fila
        for c in carros_existentes:
            if c != self and futuro_rect.colliderect(c.rect): return
                
        self.rect = futuro_rect

# =====================================================================
# 4. INTERFACE GRÁFICA
# =====================================================================
def desenhar_mapa():
    pygame.init()
    ecra = pygame.display.set_mode((850, 650))
    pygame.display.set_caption("CMC Gráfica - Via 10 no C2 e Via 3 no C1")
    relogio = pygame.time.Clock()

    CORES_SEMAFORO = {1: (255, 50, 50), 2: (50, 255, 50), 3: (255, 200, 50)}
    fonte = pygame.font.SysFont("Arial", 16, bold=True)
    fonte_grande = pygame.font.SysFont("Courier New", 20, bold=True)

    carros = []
    vias_geradoras = [1, 5, 7, 8, 9, 10] # Trocado 3 por 10
    tempo_ultimo_spawn = {v: time.time() for v in vias_geradoras}

    texto_input = ""

    while True:
        agora = time.time()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE:
                    texto_input = texto_input[:-1]
                elif evento.key == pygame.K_TAB:
                    texto_input += "\t"
                elif evento.key == pygame.K_RETURN:
                    try:
                        partes = texto_input.split('\t')
                        if len(partes) == 2:
                            via_alvo = int(partes[0].strip())
                            novo_rtg = int(partes[1].strip())
                            if snmp_loop and via_alvo in estado_rtg:
                                asyncio.run_coroutine_threadsafe(enviar_novo_rtg_snmp(via_alvo, novo_rtg), snmp_loop)
                    except ValueError:
                        pass 
                    
                    texto_input = "" 
                elif evento.unicode.isdigit():
                    texto_input += evento.unicode

        # Geração de Tráfego com redução no amarelo
        for via in vias_geradoras:
            rtg_base = estado_rtg.get(via, 0)
            if rtg_base > 0:
                if estado_semaforos.get(via, 2) == 3:
                    rtg_efetivo = rtg_base / 2.0
                else:
                    rtg_efetivo = float(rtg_base)
                
                if rtg_efetivo > 0:
                    intervalo_segundos = 60.0 / rtg_efetivo
                    if agora - tempo_ultimo_spawn[via] > intervalo_segundos:
                        carros.append(Carro(via))
                        tempo_ultimo_spawn[via] = agora

        for carro in carros[:]:
            carro.atualizar(carros)
            if not ecra.get_rect().colliderect(carro.rect): carros.remove(carro)

        ecra.fill((40, 45, 50)) 

        # Estradas
        pygame.draw.rect(ecra, (100, 100, 100), (0, 260, 850, 80))
        for x in range(10, 850, 40): pygame.draw.rect(ecra, (255, 255, 255), (x, 298, 20, 4))
        pygame.draw.rect(ecra, (100, 100, 100), (240, 50, 80, 500))
        for y in range(50, 550, 40): pygame.draw.rect(ecra, (255, 255, 255), (278, y, 4, 20))
        pygame.draw.rect(ecra, (100, 100, 100), (500, 50, 80, 500))
        for y in range(50, 550, 40): pygame.draw.rect(ecra, (255, 255, 255), (538, y, 4, 20))

        # Semáforos
        if 1 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[1]], (220, 325), 10)
        if 5 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[5]], (255, 240), 10)
        if 8 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[8]], (305, 355), 10)
        if 3 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[3]], (340, 275), 10) # Via 3 (No C1)
        
        if 2 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[2]], (480, 325), 10)
        if 7 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[7]], (515, 240), 10)
        if 9 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[9]], (565, 355), 10)
        if 10 in estado_semaforos: pygame.draw.circle(ecra, CORES_SEMAFORO[estado_semaforos[10]], (600, 275), 10) # Via 10 (No C2)

        for carro in carros:
            pygame.draw.rect(ecra, carro.cor, carro.rect)
            pygame.draw.rect(ecra, (0, 0, 0), carro.rect, 2)

        ecra.blit(fonte_grande.render("C1", True, (255, 255, 255)), (325, 350))
        ecra.blit(fonte_grande.render("C2", True, (255, 255, 255)), (585, 350))
        
        # Textos das Vias (Atualizado para a Via 10)
        ecra.blit(fonte.render(f"Via 5 (Norte) | RTG: {estado_rtg.get(5, 0)}", True, (200, 200, 200)), (90, 20))
        ecra.blit(fonte.render(f"Via 7 (Norte) | RTG: {estado_rtg.get(7, 0)}", True, (200, 200, 200)), (550, 20))
        ecra.blit(fonte.render(f"Via 8 (Sul) | RTG: {estado_rtg.get(8, 0)}", True, (200, 200, 200)), (90, 540))
        ecra.blit(fonte.render(f"Via 9 (Sul) | RTG: {estado_rtg.get(9, 0)}", True, (200, 200, 200)), (550, 540))
        ecra.blit(fonte.render(f"Via 1 (Oeste) | RTG: {estado_rtg.get(1, 0)}", True, (200, 200, 200)), (20, 350))
        ecra.blit(fonte.render(f"Via 10 (Este) | RTG: {estado_rtg.get(10, 0)}", True, (200, 200, 200)), (680, 230))

        # Painel Inferior
        pygame.draw.rect(ecra, (20, 25, 30), (0, 570, 850, 80))
        ecra.blit(fonte.render("Comando: Escreve <ID da Via> + Tecla TAB + <Novo RTG> e pressiona Enter.", True, (150, 150, 150)), (20, 580))
        
        texto_display = texto_input.replace("\t", " [TAB] ")
        txt_surface = fonte_grande.render(f"CMC> {texto_display}_", True, (255, 200, 50))
        ecra.blit(txt_surface, (20, 610))

        pygame.display.flip()
        relogio.tick(60)

if __name__ == "__main__":
    threading.Thread(target=iniciar_thread_snmp, daemon=True).start()
    desenhar_mapa()