import pygame
import sys
import asyncio
import threading
import time
from pysnmp.hlapi.asyncio import *

# =====================================================================
# 1. ESTADO PARTILHADO (Atualizado via SNMP)
# =====================================================================
estado_semaforos = {1: 1, 3: 1, 5: 1} # 1=Vermelho, 2=Verde, 3=Amarelo
estado_rtg = {1: 43, 3: 43, 5: 43}    # Veículos por minuto
snmp_loop = None 

# =====================================================================
# 2. CLIENTE SNMP (Corre em Background)
# =====================================================================
async def obter_dados_snmp():
    ip = '127.0.0.1'
    porta = 16161
    comunidade = 'public'
    snmpEngine = SnmpEngine()
    
    oids = [
        ObjectType(ObjectIdentity('1.3.6.1.3.2026.1.4.1.3.1')), 
        ObjectType(ObjectIdentity('1.3.6.1.3.2026.1.4.1.3.3')), 
        ObjectType(ObjectIdentity('1.3.6.1.3.2026.1.4.1.3.5')), 
        ObjectType(ObjectIdentity('1.3.6.1.3.2026.1.3.1.4.1')), 
        ObjectType(ObjectIdentity('1.3.6.1.3.2026.1.3.1.4.3')), 
        ObjectType(ObjectIdentity('1.3.6.1.3.2026.1.3.1.4.5'))  
    ]

    while True:
        try:
            errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
                snmpEngine, CommunityData(comunidade, mpModel=1),
                UdpTransportTarget((ip, porta), timeout=1, retries=0),
                ContextData(), *oids
            )

            if not errorIndication and not errorStatus:
                estado_semaforos[1] = int(varBinds[0][1])
                estado_semaforos[3] = int(varBinds[1][1])
                estado_semaforos[5] = int(varBinds[2][1])
                estado_rtg[1] = int(varBinds[3][1])
                estado_rtg[3] = int(varBinds[4][1])
                estado_rtg[5] = int(varBinds[5][1])
        except Exception:
            pass 
        await asyncio.sleep(1)

async def enviar_novo_rtg_snmp(via, novo_rtg):
    ip = '127.0.0.1'
    porta = 16161
    oid = f'1.3.6.1.3.2026.1.3.1.4.{via}'
    snmpEngine = SnmpEngine()
    
    await setCmd(
        snmpEngine, CommunityData('public', mpModel=1),
        UdpTransportTarget((ip, porta), timeout=1, retries=0),
        ContextData(), ObjectType(ObjectIdentity(oid), Gauge32(novo_rtg))
    )

def iniciar_thread_snmp():
    global snmp_loop
    snmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(snmp_loop)
    snmp_loop.run_until_complete(obter_dados_snmp())

# =====================================================================
# 3. LÓGICA VISUAL DOS CARROS
# =====================================================================
class Carro:
    def __init__(self, via):
        self.via = via
        self.cor = (0, 180, 255) # Azul principal
        
        # Posições ajustadas para o novo mapa com 2 cruzamentos
        if via == 1:
            self.rect = pygame.Rect(-20, 310, 20, 12)
        elif via == 3:
            self.rect = pygame.Rect(800, 270, 20, 12)
        elif via == 5:
            self.rect = pygame.Rect(250, -20, 12, 20)

    def atualizar(self, carros_existentes):
        vel = 2
        futuro_rect = self.rect.copy()
        
        if self.via == 1: futuro_rect.x += vel
        elif self.via == 3: futuro_rect.x -= vel
        elif self.via == 5: futuro_rect.y += vel
        
        cor_semaforo = estado_semaforos[self.via]
        
        # Linhas de paragem para o Cruzamento 1
        if cor_semaforo in [1, 3]: 
            if self.via == 1 and 220 <= self.rect.right <= 240: return
            if self.via == 3 and 320 <= self.rect.left <= 340: return
            if self.via == 5 and 240 <= self.rect.bottom <= 260: return

        # Prevenir colisões na retaguarda
        for c in carros_existentes:
            if c != self and futuro_rect.colliderect(c.rect):
                return
                
        self.rect = futuro_rect

# =====================================================================
# 4. INTERFACE GRÁFICA (Pygame)
# =====================================================================
def desenhar_mapa():
    pygame.init()
    ecra = pygame.display.set_mode((850, 650))
    pygame.display.set_caption("CMC - Simulador Gráfico de Tráfego (2 Cruzamentos)")
    relogio = pygame.time.Clock()

    CORES_SEMAFORO = {1: (255, 50, 50), 2: (50, 255, 50), 3: (255, 200, 50)}
    fonte = pygame.font.SysFont("Arial", 16, bold=True)
    fonte_grande = pygame.font.SysFont("Arial", 20, bold=True)

    carros = []
    tempo_ultimo_spawn = {1: time.time(), 3: time.time(), 5: time.time()}

    via_selecionada = None
    texto_input = ""

    enquanto_corre = True
    while enquanto_corre:
        agora = time.time()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                enquanto_corre = False
                
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_1, pygame.K_KP1]: via_selecionada = 1; texto_input = ""
                elif evento.key in [pygame.K_3, pygame.K_KP3]: via_selecionada = 3; texto_input = ""
                elif evento.key in [pygame.K_5, pygame.K_KP5]: via_selecionada = 5; texto_input = ""
                
                elif via_selecionada is not None:
                    if evento.key == pygame.K_BACKSPACE:
                        texto_input = texto_input[:-1]
                    elif evento.key == pygame.K_RETURN and texto_input.isdigit():
                        novo_rtg = int(texto_input)
                        if snmp_loop:
                            asyncio.run_coroutine_threadsafe(enviar_novo_rtg_snmp(via_selecionada, novo_rtg), snmp_loop)
                        texto_input = ""
                        via_selecionada = None
                    elif evento.unicode.isdigit():
                        texto_input += evento.unicode

        for via in [1, 3, 5]:
            rtg_atual = estado_rtg.get(via, 0)
            if rtg_atual > 0:
                intervalo_segundos = 60.0 / rtg_atual
                if agora - tempo_ultimo_spawn[via] > intervalo_segundos:
                    carros.append(Carro(via))
                    tempo_ultimo_spawn[via] = agora

        for carro in carros[:]:
            carro.atualizar(carros)
            if not ecra.get_rect().colliderect(carro.rect):
                carros.remove(carro)

        # --- DESENHAR TUDO ---
        ecra.fill((40, 45, 50)) 

        # Avenida Principal (Oeste -> Este)
        pygame.draw.rect(ecra, (100, 100, 100), (0, 260, 850, 80))
        for x in range(10, 850, 40): pygame.draw.rect(ecra, (255, 255, 255), (x, 298, 20, 4))
        
        # Cruzamento 1 (C1) - Estrada Norte -> Sul
        pygame.draw.rect(ecra, (100, 100, 100), (240, 50, 80, 500))
        for y in range(50, 550, 40): pygame.draw.rect(ecra, (255, 255, 255), (278, y, 4, 20))

        # Cruzamento 2 (C2) - Estrada Norte -> Sul
        pygame.draw.rect(ecra, (100, 100, 100), (500, 50, 80, 500))
        for y in range(50, 550, 40): pygame.draw.rect(ecra, (255, 255, 255), (538, y, 4, 20))

        # Semáforos do C1
        pygame.draw.circle(ecra, CORES_SEMAFORO.get(estado_semaforos[1], (150,150,150)), (220, 325), 10)
        pygame.draw.circle(ecra, CORES_SEMAFORO.get(estado_semaforos[3], (150,150,150)), (340, 275), 10)
        pygame.draw.circle(ecra, CORES_SEMAFORO.get(estado_semaforos[5], (150,150,150)), (255, 240), 10)

        # Carros (Com contorno preto)
        for carro in carros:
            # 1. Desenha o interior azul
            pygame.draw.rect(ecra, carro.cor, carro.rect)
            # 2. Desenha o contorno preto (espessura 2)
            pygame.draw.rect(ecra, (0, 0, 0), carro.rect, 2)

        # Rótulos dos Cruzamentos
        ecra.blit(fonte_grande.render("C1", True, (255, 255, 255)), (325, 350))
        ecra.blit(fonte_grande.render("C2", True, (255, 255, 255)), (585, 350))

        # Textos das Vias
        ecra.blit(fonte.render(f"Via 5 (Norte) | RTG: {estado_rtg[5]}", True, (200, 200, 200)), (110, 20))
        ecra.blit(fonte.render(f"Via 1 (Oeste) | RTG: {estado_rtg[1]}", True, (200, 200, 200)), (20, 350))
        ecra.blit(fonte.render(f"Via 3 (Este) | RTG: {estado_rtg[3]}", True, (200, 200, 200)), (620, 230))

        # Painel Inferior
        pygame.draw.rect(ecra, (20, 25, 30), (0, 570, 850, 80))
        instrucoes = fonte.render("Controlos: Pressiona a tecla 1, 3 ou 5 para escolher a via e alterar o RTG.", True, (150, 150, 150))
        ecra.blit(instrucoes, (20, 580))
        
        if via_selecionada is not None:
            txt_input = fonte_grande.render(f"A alterar Via {via_selecionada} -> Escreve o novo RTG: {texto_input}_ (Enter para gravar)", True, (255, 200, 50))
            ecra.blit(txt_input, (20, 610))

        pygame.display.flip()
        relogio.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    thread_snmp = threading.Thread(target=iniciar_thread_snmp, daemon=True)
    thread_snmp.start()
    desenhar_mapa()