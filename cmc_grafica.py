import pygame
import sys
import asyncio
import threading
import time
import json
import random
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
# 2. CLIENTE SNMP
# =====================================================================
async def obter_dados_snmp():
    snmpEngine = SnmpEngine()
    oids = []
    for via in estado_semaforos.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.4.1.3.{via}')))
    for via in estado_rtg.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.3.1.4.{via}')))

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
                for via in estado_rtg.keys(): estado_rtg[via] = int(varBinds[idx][1]); idx += 1
        except Exception: pass 
        await asyncio.sleep(0.5)

async def enviar_novo_rtg_snmp(via, novo_rtg):
    oid = f'1.3.6.1.3.2026.1.3.1.4.{via}'
    await setCmd(SnmpEngine(), CommunityData('public', mpModel=1), UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0), ContextData(), ObjectType(ObjectIdentity(oid), Gauge32(novo_rtg)))

def iniciar_thread_snmp():
    global snmp_loop
    snmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(snmp_loop)
    snmp_loop.run_until_complete(obter_dados_snmp())

# =====================================================================
# 3. FÍSICA E INTELIGÊNCIA ARTIFICIAL DOS CARROS
# =====================================================================
class Carro:
    def __init__(self, via):
        self.via = via
        self.cor = (0, 180, 255) 
        self.decidido = False 
        
        self.acidentado = False
        self.tempo_espera_acidente = 5.0 
        self.tempo_acidente = 0
        self.imune_ate = 0 
        
        if via == 101: self.rect = pygame.Rect(-20, 210, 20, 12); self.dx, self.dy = 2, 0
        elif via == 102: self.rect = pygame.Rect(550, -20, 12, 20); self.dx, self.dy = 0, 2
        elif via == 103: self.rect = pygame.Rect(850, 470, 20, 12); self.dx, self.dy = -2, 0
        elif via == 104: self.rect = pygame.Rect(290, 650, 12, 20); self.dx, self.dy = 0, -2
        else: self.rect = pygame.Rect(-100,-100,0,0); self.dx, self.dy = 0,0

    def atualizar(self, carros_existentes):
        tempo_atual = time.time()
        
        # --- 1. RECUPERAÇÃO DE ACIDENTE ---
        if self.acidentado:
            if tempo_atual >= self.tempo_acidente + self.tempo_espera_acidente:
                self.acidentado = False
                self.imune_ate = tempo_atual + 3.0 # Fantasma por 3s
                self.cor = (255, 150, 0) # Laranja
            else:
                return # Imobilizado
                
        if not self.acidentado and tempo_atual > self.imune_ate:
            self.cor = (0, 180, 255)

        futuro_rect = self.rect.copy()
        futuro_rect.x += self.dx
        futuro_rect.y += self.dy
        
        stop = False
        
        # --- 2. PARAGEM EXATA NOS SEMÁFOROS (Só antes da linha) ---
        if self.dx > 0: 
            if estado_semaforos.get(self.via, 2) == 1:
                if self.via == 101 and self.rect.right <= 240 and futuro_rect.right >= 240: stop = True
                elif self.via == 1 and self.rect.right <= 500 and futuro_rect.right >= 500: stop = True
        elif self.dx < 0: 
            if estado_semaforos.get(self.via, 2) == 1:
                if self.via == 103 and self.rect.left >= 610 and futuro_rect.left <= 610: stop = True
                elif self.via == 3 and self.rect.left >= 350 and futuro_rect.left <= 350: stop = True
        elif self.dy > 0: 
            if estado_semaforos.get(self.via, 2) == 1:
                if self.via == 102 and self.rect.bottom <= 170 and futuro_rect.bottom >= 170: stop = True
                elif self.via == 2 and self.rect.bottom <= 430 and futuro_rect.bottom >= 430: stop = True
        elif self.dy < 0: 
            if estado_semaforos.get(self.via, 2) == 1:
                if self.via == 104 and self.rect.top >= 520 and futuro_rect.top <= 520: stop = True
                elif self.via == 4 and self.rect.top >= 260 and futuro_rect.top <= 260: stop = True

        if stop: return

        # --- 3. SISTEMA ANTI-COLISÃO (Radar de Fila Perfeita) ---
        # Cria um sensor à frente do carro (4 pixeis)
        radar = self.rect.copy()
        margem_seguranca = 4
        if self.dx > 0: radar.x += self.rect.width; radar.width = margem_seguranca
        elif self.dx < 0: radar.x -= margem_seguranca; radar.width = margem_seguranca
        elif self.dy > 0: radar.y += self.rect.height; radar.height = margem_seguranca
        elif self.dy < 0: radar.y -= margem_seguranca; radar.height = margem_seguranca

        for c in carros_existentes:
            if c != self:
                # A) DETEÇÃO DE FILA (Evita sobreposição na mesma faixa)
                if radar.colliderect(c.rect):
                    # Confirma se partilham o mesmo "corredor" (tolerância de 12px para curvas)
                    na_mesma_faixa = False
                    if self.dx != 0 and abs(self.rect.centery - c.rect.centery) <= 12: na_mesma_faixa = True
                    if self.dy != 0 and abs(self.rect.centerx - c.rect.centerx) <= 12: na_mesma_faixa = True
                    
                    if na_mesma_faixa:
                        stop = True
                        break # Entra perfeitamente na fila

                # B) ACIDENTE LATERAL / T-BONE (Colisão profunda em direções cruzadas)
                if futuro_rect.inflate(-6, -6).colliderect(c.rect.inflate(-6, -6)):
                    # Modos fantasma ou sentidos perfeitamente opostos são ignorados
                    if (tempo_atual < self.imune_ate or tempo_atual < getattr(c, 'imune_ate', 0)) or (self.dx == -c.dx and self.dy == -c.dy):
                        continue 

                    # Acidente Real
                    if not self.acidentado:
                        self.acidentado = True
                        self.tempo_espera_acidente = 5.0
                        self.tempo_acidente = tempo_atual
                        self.cor = (255, 50, 50)
                    
                    if not getattr(c, 'acidentado', False):
                        c.acidentado = True
                        c.tempo_espera_acidente = 6.5
                        c.tempo_acidente = tempo_atual
                        c.cor = (255, 50, 50)
                    stop = True
                    break

        if stop: return
        self.rect = futuro_rect
        x, y = self.rect.x, self.rect.y
        
        # --- 4. VIRAGENS ---
        def decide_turn(current_via):
            opcoes = [l for l in cfg.get('links', []) if l['src'] == current_via]
            if not opcoes: return current_via 
            rand = random.uniform(0, sum(l['flowRate'] for l in opcoes))
            acumulado = 0
            for l in opcoes:
                acumulado += l['flowRate']
                if rand <= acumulado: return l['dest']
            return current_via

        def virar(novo_dx, novo_dy, nova_via):
            self.dx, self.dy = novo_dx, novo_dy
            self.rect.width, self.rect.height = self.rect.height, self.rect.width
            self.via = nova_via
            self.imune_ate = time.time() + 1.5 # Proteção rápida ao rodar o chassi do carro

        if not self.decidido and 280 <= x <= 300 and 200 <= y <= 220:
            if self.via == 101 and self.dx > 0: self.via = 1; self.decidido = True 
            elif self.via == 4 and self.dy < 0:
                dest = decide_turn(self.via)
                if dest == 1: virar(2, 0, 1); self.rect.y = 210 
                else: self.via = 91 
                self.decidido = True

        elif not self.decidido and 540 <= x <= 560 and 200 <= y <= 220:
            if self.via == 102 and self.dy > 0: self.via = 2; self.decidido = True 
            elif self.via == 1 and self.dx > 0:
                dest = decide_turn(self.via)
                if dest == 2: virar(0, 2, 2); self.rect.x = 550 
                else: self.via = 92 
                self.decidido = True

        elif not self.decidido and 540 <= x <= 560 and 460 <= y <= 480:
            if self.via == 103 and self.dx < 0: self.via = 3; self.decidido = True 
            elif self.via == 2 and self.dy > 0:
                dest = decide_turn(self.via)
                if dest == 3: virar(-2, 0, 3); self.rect.y = 470 
                else: self.via = 93 
                self.decidido = True

        elif not self.decidido and 280 <= x <= 300 and 460 <= y <= 480:
            if self.via == 104 and self.dy < 0: self.via = 4; self.decidido = True 
            elif self.via == 3 and self.dx < 0:
                dest = decide_turn(self.via)
                if dest == 4: virar(0, -2, 4); self.rect.x = 290 
                else: self.via = 94 
                self.decidido = True
        
        elif not ((280 <= x <= 300 and 200 <= y <= 220) or (540 <= x <= 560 and 200 <= y <= 220) or 
                  (540 <= x <= 560 and 460 <= y <= 480) or (280 <= x <= 300 and 460 <= y <= 480)):
            self.decidido = False

# =====================================================================
# 4. DESENHO E INTERFACE
# =====================================================================
def desenhar_mapa():
    pygame.init()
    ecra = pygame.display.set_mode((850, 650))
    pygame.display.set_caption("CMC - Filas Perfeitas (Radar Anti-Sobreposição)")
    relogio = pygame.time.Clock()
    fonte = pygame.font.SysFont("Arial", 16, bold=True)
    fonte_grande = pygame.font.SysFont("Courier New", 20, bold=True)

    carros = []
    vias_geradoras = [101, 102, 103, 104]
    tempo_ultimo_spawn = {v: time.time() for v in vias_geradoras}
    texto_input = ""

    while True:
        agora = time.time()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT: pygame.quit(); sys.exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE: texto_input = texto_input[:-1]
                elif evento.key == pygame.K_TAB: texto_input += "\t"
                elif evento.key == pygame.K_RETURN:
                    try:
                        p = texto_input.split('\t')
                        if len(p) == 2: asyncio.run_coroutine_threadsafe(enviar_novo_rtg_snmp(int(p[0]), int(p[1])), snmp_loop)
                    except: pass
                    texto_input = ""
                elif evento.unicode.isdigit(): texto_input += evento.unicode

        for via in vias_geradoras:
            rtg = estado_rtg.get(via, 0)
            if rtg > 0:
                intv = 60.0 / (rtg / 2.0 if estado_semaforos.get(via) == 3 else rtg)
                if agora - tempo_ultimo_spawn[via] > intv:
                    carros.append(Carro(via))
                    tempo_ultimo_spawn[via] = agora

        for carro in carros[:]:
            carro.atualizar(carros)
            if not ecra.get_rect().colliderect(carro.rect): carros.remove(carro)

        ecra.fill((40, 45, 50))
        
        pygame.draw.rect(ecra, (100, 100, 100), (0, 180, 850, 60)) 
        pygame.draw.rect(ecra, (100, 100, 100), (0, 440, 850, 60)) 
        pygame.draw.rect(ecra, (100, 100, 100), (260, 0, 60, 560)) 
        pygame.draw.rect(ecra, (100, 100, 100), (520, 0, 60, 560)) 
        
        for x in range(10, 850, 40): 
            pygame.draw.rect(ecra, (255, 255, 255), (x, 208, 20, 4))
            pygame.draw.rect(ecra, (255, 255, 255), (x, 468, 20, 4))
        for y in range(10, 550, 40): 
            pygame.draw.rect(ecra, (255, 255, 255), (288, y, 4, 20))
            pygame.draw.rect(ecra, (255, 255, 255), (548, y, 4, 20))

        colors = {1: (255, 50, 50), 2: (50, 255, 50), 3: (255, 200, 50)}
        for rid, col in estado_semaforos.items():
            pos = {
                101: (240, 225), 4: (305, 250), 
                1:   (500, 225), 102: (565, 160), 
                103: (600, 485), 2:   (535, 420), 
                3:   (340, 485), 104: (305, 510)  
            }.get(rid)
            if pos: pygame.draw.circle(ecra, colors.get(col, (100,100,100)), pos, 10)

        for c in carros:
            pygame.draw.rect(ecra, c.cor, c.rect)
            pygame.draw.rect(ecra, (0, 0, 0), c.rect, 2)

        ecra.blit(fonte_grande.render("C1", True, (255, 255, 255)), (330, 225))
        ecra.blit(fonte_grande.render("C2", True, (255, 255, 255)), (480, 225))
        ecra.blit(fonte_grande.render("C3", True, (255, 255, 255)), (480, 485))
        ecra.blit(fonte_grande.render("C4", True, (255, 255, 255)), (330, 485))

        ecra.blit(fonte.render(f"Via 101 (Oeste): {estado_rtg.get(101, 0)}", True, (200, 200, 200)), (10, 160))
        ecra.blit(fonte.render(f"Via 102 (Norte): {estado_rtg.get(102, 0)}", True, (200, 200, 200)), (590, 10))
        ecra.blit(fonte.render(f"Via 103 (Este): {estado_rtg.get(103, 0)}", True, (200, 200, 200)), (700, 510))
        ecra.blit(fonte.render(f"Via 104 (Sul): {estado_rtg.get(104, 0)}", True, (200, 200, 200)), (100, 540))

        pygame.draw.rect(ecra, (20, 25, 30), (0, 570, 850, 80))
        ecra.blit(fonte.render("Comando: <Via (101 a 104)> [TAB] <Novo RTG> + Enter", True, (150, 150, 150)), (20, 580))
        txt = texto_input.replace("\t", " [TAB] ")
        ecra.blit(fonte_grande.render(f"CMC> {txt}_", True, (255, 200, 50)), (20, 610))
        
        pygame.display.flip()
        relogio.tick(60)

if __name__ == "__main__":
    threading.Thread(target=iniciar_thread_snmp, daemon=True).start()
    desenhar_mapa()