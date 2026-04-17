import pygame
import sys
import asyncio
import threading
import json
import time 
from pysnmp.hlapi.asyncio import *

# NOVO: Imports para o Servidor de Receção de Traps
from pysnmp.entity import engine as snmp_engine_mod, config as snmp_config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv

# =====================================================================
# CLASSE DE DROPDOWN LIST
# =====================================================================
class DropdownList:
    def __init__(self, x, y, width, height, options, fonte_pequena, fonte_grande, escala_geral):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.options = options  # Lista de tuplas: (valor_id, nome)
        self.is_open = False
        self.selected_idx = 3  # BACKPRESSURE por padrão (índice 3)
        self.fonte_pequena = fonte_pequena
        self.fonte_grande = fonte_grande
        self.escala_geral = escala_geral
    
    def draw(self, surface):
        # Cor da caixa principal
        cor_caixa = (50, 70, 90) if not self.is_open else (70, 90, 110)
        pygame.draw.rect(surface, cor_caixa, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(surface, (150, 150, 150), (self.x, self.y, self.width, self.height), 2)
        
        # Texto da opção selecionada
        texto = self.options[self.selected_idx][1]
        txt_surface = self.fonte_pequena.render(texto, True, (255, 255, 255))
        surface.blit(txt_surface, (self.x + 10, self.y + 8))
        
        # Seta indicadora
        seta = "▼" if self.is_open else "▶"
        seta_surface = self.fonte_pequena.render(seta, True, (200, 200, 200))
        surface.blit(seta_surface, (self.x + self.width - 25, self.y + 5))
        
        # Se está aberto, desenhar opções
        if self.is_open:
            y_offset = self.y + self.height
            for idx, (val_id, nome) in enumerate(self.options):
                cor_bg = (100, 120, 140) if idx == self.selected_idx else (60, 80, 100)
                pygame.draw.rect(surface, cor_bg, (self.x, y_offset, self.width, self.height))
                pygame.draw.rect(surface, (150, 150, 150), (self.x, y_offset, self.width, self.height), 1)
                
                txt = self.fonte_pequena.render(nome, True, (255, 255, 255))
                surface.blit(txt, (self.x + 10, y_offset + 8))
                
                y_offset += self.height
    
    def handle_click(self, mouse_x, mouse_y):
        # Verificar se clicou na caixa principal
        if self.x <= mouse_x <= self.x + self.width and self.y <= mouse_y <= self.y + self.height:
            self.is_open = not self.is_open
            return None
        
        # Se está aberto, verificar se clicou em alguma opção
        if self.is_open:
            y_offset = self.y + self.height
            for idx, (val_id, nome) in enumerate(self.options):
                if self.x <= mouse_x <= self.x + self.width and y_offset <= mouse_y <= y_offset + self.height:
                    self.selected_idx = idx
                    self.is_open = False
                    return val_id  # Retorna o ID do algoritmo selecionado
                y_offset += self.height
        
        return None
    
    def fechar(self):
        self.is_open = False

# =====================================================================
# 1. CARREGAR CONFIGURAÇÃO
# =====================================================================
with open('config.json', 'r') as f:
    cfg = json.load(f)

estado_semaforos = {tl['roadIndex']: 1 for tl in cfg['trafficLights']}
estado_filas = {r['id']: r.get('initialCount', 0) for r in cfg['roads']}
estado_rtg = {r['id']: r.get('rtg', 0) for r in cfg['roads'] if r['type'] == 3}
estado_override = {tl['roadIndex']: 0 for tl in cfg['trafficLights']} 
estado_links = {f"{l['src']}.{l['dest']}": 0 for l in cfg.get('links', [])} 

snmp_loop = None 

# NOVO: Variável global que guarda o estado do alarme na Consola
alerta_trap = {"ativo": False, "via": 0, "carros": 0, "expira": 0}

# Variáveis globais para tempo e algoritmo (inicializadas)
import builtins
builtins._tempo_execucao_snmp = 0
builtins._algo_id_snmp = 4  # Padrão: BACKPRESSURE

# Variável global para controlar a mensagem de confirmação
confirmacao_algoritmo = {"ativo": False, "tempo": 0}

# =====================================================================
# 2. CLIENTE SNMP E RECETOR DE TRAPS
# =====================================================================

# NOVO: Função que é chamada quando uma Trap bate à porta
def processar_trap(snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
    global alerta_trap
    via = 0
    carros = 0
    for name, val in varBinds:
        if "2026.1.1.1" in str(name): via = int(val)
        if "2026.1.1.2" in str(name): carros = int(val)
    
    if via > 0:
        # Ativa o Alarme Visual por 6 segundos!
        alerta_trap = {"ativo": True, "via": via, "carros": carros, "expira": time.time() + 6.0}

# NOVO: Servidor background que escuta Traps na porta 16216
async def servidor_traps():
    snmpEngine = snmp_engine_mod.SnmpEngine()
    snmp_config.addTransport(snmpEngine, udp.domainName, udp.UdpTransport().openServerMode(('127.0.0.1', 16216)))
    snmp_config.addV1System(snmpEngine, 'my-area', 'public')
    snmp_config.addVacmUser(snmpEngine, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6), (1, 3, 6))
    ntfrcv.NotificationReceiver(snmpEngine, processar_trap)
    while True:
        await asyncio.sleep(3600)

async def obter_dados_snmp():
    snmpEngine = SnmpEngine()
    oids = []
    for via in estado_semaforos.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.4.1.3.{via}')))
    for via in estado_filas.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.3.1.6.{via}')))
    for via in estado_rtg.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.3.1.4.{via}')))
    for via in estado_override.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.4.1.2.{via}')))
    for link in estado_links.keys(): oids.append(ObjectType(ObjectIdentity(f'1.3.6.1.3.2026.1.5.1.4.{link}')))
    # Adicionar OIDs do tempo de execução e algoritmo
    oids.append(ObjectType(ObjectIdentity('1.3.6.1.3.2026.1.1.7.0')))  # Tempo de execução
    oids.append(ObjectType(ObjectIdentity('1.3.6.1.3.2026.1.1.6.0')))  # Algoritmo

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
                # Ler tempo e algoritmo
                tempo_execucao = int(varBinds[idx][1]); idx += 1
                algo_id = int(varBinds[idx][1]); idx += 1
                
                # Guardar na memória global
                import builtins
                builtins._tempo_execucao_snmp = tempo_execucao
                builtins._algo_id_snmp = algo_id
        except Exception: pass 
        await asyncio.sleep(0.5)

async def enviar_novo_rtg_snmp(via, novo_rtg):
    oid = f'1.3.6.1.3.2026.1.3.1.4.{via}'
    await setCmd(SnmpEngine(), CommunityData('public', mpModel=1), UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0), ContextData(), ObjectType(ObjectIdentity(oid), Gauge32(novo_rtg)))

async def enviar_override_snmp(via, modo):
    oid = f'1.3.6.1.3.2026.1.4.1.2.{via}'
    await setCmd(SnmpEngine(), CommunityData('public', mpModel=1), UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0), ContextData(), ObjectType(ObjectIdentity(oid), Integer32(modo)))

async def enviar_algoritmo_snmp(algo_id):
    """Envia o ID do algoritmo para o SC via SNMP"""
    oid = '1.3.6.1.3.2026.1.1.6.0'
    await setCmd(SnmpEngine(), CommunityData('public', mpModel=1), UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0), ContextData(), ObjectType(ObjectIdentity(oid), Integer32(algo_id)))

def iniciar_thread_snmp():
    global snmp_loop
    snmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(snmp_loop)
    # NOVO: Corre as duas tarefas em paralelo (O Polling e o Escutador de Traps)
    snmp_loop.run_until_complete(asyncio.gather(obter_dados_snmp(), servidor_traps()))

# =====================================================================
# 3. INTERFACE GRÁFICA
# =====================================================================
# =====================================================================
# 3. INTERFACE GRÁFICA
# =====================================================================
def desenhar_grafo():
    global confirmacao_algoritmo
    pygame.init()
    # 1. Adicionamos a flag pygame.RESIZABLE para permitir maximizar/redimensionar
    ecra = pygame.display.set_mode((900, 700), pygame.RESIZABLE)
    pygame.display.set_caption("Dashboard Topológico - Filas de Espera")
    relogio = pygame.time.Clock()
    
    # 2. Coordenadas e tamanhos base (para cálculo de proporções)
    RESOLUCAO_BASE = (900, 700)
    tamanho_atual = RESOLUCAO_BASE

    nos_base = {1: (300, 250), 2: (600, 250), 3: (600, 500), 4: (300, 500)}

    pontos_externos_base = {
        101: (100, 250), 94: (100, 500),  
        102: (600, 100), 91: (300, 100),  
        103: (800, 500), 92: (800, 250),  
        104: (300, 650), 93: (600, 650)   
    }

    arestas_base = {
        101: (pontos_externos_base[101], nos_base[1]), 102: (pontos_externos_base[102], nos_base[2]),
        103: (pontos_externos_base[103], nos_base[3]), 104: (pontos_externos_base[104], nos_base[4]),
        1: ((320, 240), (580, 240)), 5: ((580, 260), (320, 260)),
        2: ((610, 270), (610, 480)), 6: ((590, 480), (590, 270)),
        3: ((580, 510), (320, 510)), 7: ((320, 490), (580, 490)),
        4: ((290, 480), (290, 270)), 8: ((310, 270), (310, 480)),
        91: (nos_base[1], pontos_externos_base[91]), 92: (nos_base[2], pontos_externos_base[92]),
        93: (nos_base[3], pontos_externos_base[93]), 94: (nos_base[4], pontos_externos_base[94])
    }
    
    def escalar_coordenada(x, y, escala_x, escala_y):
        """Escala uma coordenada proporcionalmente"""
        return (int(x * escala_x), int(y * escala_y))
    
    def escalar_valor(valor, escala):
        """Escala um valor (tamanho, espessura)"""
        return max(1, int(valor * escala))
    
    def desenhar_seta(surface, p_origem, p_destino, cor, tamanho):
        """Desenha uma seta apenas com traços apontando na direção do trânsito"""
        import math
        
        # Calcular ponto a 1/4 da via (mais perto da origem)
        mid_x = p_origem[0] + (p_destino[0] - p_origem[0]) * 0.25
        mid_y = p_origem[1] + (p_destino[1] - p_origem[1]) * 0.25
        
        # Calcular ângulo da linha
        dx = p_destino[0] - p_origem[0]
        dy = p_destino[1] - p_origem[1]
        angulo = math.atan2(dy, dx)
        
        # Ponta da seta (ponto no meio)
        ponta = (int(mid_x), int(mid_y))
        
        # Base da seta (linha central)
        comprimento_base = tamanho
        base_x = int(mid_x - comprimento_base * math.cos(angulo))
        base_y = int(mid_y - comprimento_base * math.sin(angulo))
        
        # Desenhar linha central (do ponto atrás até a ponta)
        pygame.draw.line(surface, cor, (base_x, base_y), ponta, 2)
        
        # Desenhar as duas linhas laterais da ponta da seta
        ângulo_lateral = math.pi / 6  # 30 graus
        comprimento_lateral = tamanho * 1.5
        
        ponta1_x = int(mid_x - comprimento_lateral * math.cos(angulo + ângulo_lateral))
        ponta1_y = int(mid_y - comprimento_lateral * math.sin(angulo + ângulo_lateral))
        
        ponta2_x = int(mid_x - comprimento_lateral * math.cos(angulo - ângulo_lateral))
        ponta2_y = int(mid_y - comprimento_lateral * math.sin(angulo - ângulo_lateral))
        
        # Desenhar as duas linhas laterais
        pygame.draw.line(surface, cor, ponta, (ponta1_x, ponta1_y), 5)
        pygame.draw.line(surface, cor, ponta, (ponta2_x, ponta2_y), 5)

    texto_input = ""
    
    tempo_anterior = time.time()
    escoados_anterior = 0
    vazao_atual = 0.0
    
    # Criar dropdown list com os algoritmos
    opcoes_algos = [(1, "ROUND_ROBIN"), (2, "HEURISTICA"), (3, "RL"), (4, "BACKPRESSURE")]
    # Inicializar mais tarde no loop quando temos as fontes

    while True:
        agora = time.time()
        
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

        if agora - tempo_anterior >= 15.0:
            vazao_atual = ((total_escoados - escoados_anterior) / (agora - tempo_anterior)) * 60.0
            tempo_anterior = agora
            escoados_anterior = total_escoados

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT: pygame.quit(); sys.exit()
            elif evento.type == pygame.VIDEORESIZE:
                tamanho_atual = evento.size
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                # Lidar com cliques do dropdown (se existir)
                if 'dropdown' in locals():
                    algo_escolhido = dropdown.handle_click(evento.pos[0], evento.pos[1])
                    if algo_escolhido is not None:
                        confirmacao_algoritmo = {"ativo": True, "tempo": time.time()}
                        asyncio.run_coroutine_threadsafe(enviar_algoritmo_snmp(algo_escolhido), snmp_loop)
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE: texto_input = texto_input[:-1]
                elif evento.key == pygame.K_RETURN:
                    try:
                        p = texto_input.strip().split(' ')
                        if len(p) == 2 and p[0].upper() == "ALG":
                            algo_id = int(p[1])
                            if 1 <= algo_id <= 4:
                                asyncio.run_coroutine_threadsafe(enviar_algoritmo_snmp(algo_id), snmp_loop)
                            else:
                                print("[ERRO] Algoritmo inválido. Use: 1=ROUND_ROBIN, 2=HEURISTICA, 3=RL, 4=BACKPRESSURE")
                        elif len(p) == 2: asyncio.run_coroutine_threadsafe(enviar_novo_rtg_snmp(int(p[0]), int(p[1])), snmp_loop)
                        elif len(p) == 3 and p[0].upper() == 'O': asyncio.run_coroutine_threadsafe(enviar_override_snmp(int(p[1]), int(p[2])), snmp_loop)
                    except: pass
                    texto_input = ""
                elif evento.unicode.isprintable(): texto_input += evento.unicode

        # Calcula fatores de escala
        escala_x = tamanho_atual[0] / RESOLUCAO_BASE[0]
        escala_y = tamanho_atual[1] / RESOLUCAO_BASE[1]
        escala_geral = min(escala_x, escala_y)
        
        # Pinta o fundo
        ecra.fill((30, 35, 40))
        
        # Criar fontes redimensionadas
        fonte_pequena = pygame.font.SysFont("Arial", escalar_valor(14, escala_geral), bold=True)
        fonte_grande = pygame.font.SysFont("Courier New", escalar_valor(20, escala_geral), bold=True)
        fonte_alerta = pygame.font.SysFont("Arial", escalar_valor(22, escala_geral), bold=True)
        
        # Criar dropdown list na primeira iteração
        if 'dropdown' not in locals():
            altura_dropdown = escalar_valor(35, escala_geral)
            largura_dropdown = escalar_valor(180, escala_geral)
            dropdown = DropdownList(escalar_valor(15, escala_geral), escalar_valor(85, escala_geral), 
                                largura_dropdown, altura_dropdown, opcoes_algos, 
                                fonte_pequena, fonte_grande, escala_geral)

        # Desenhar arestas
        for via_id, (p_origem_base, p_destino_base) in arestas_base.items():
            p_origem = escalar_coordenada(p_origem_base[0], p_origem_base[1], escala_x, escala_y)
            p_destino = escalar_coordenada(p_destino_base[0], p_destino_base[1], escala_x, escala_y)
            
            cor_linha = (80, 80, 80) 
            if via_id in estado_semaforos:
                estado = estado_semaforos[via_id]
                if estado == 1: cor_linha = (200, 50, 50) 
                elif estado == 2: cor_linha = (50, 200, 50) 
                elif estado == 3: cor_linha = (200, 150, 50) 

            espessura = escalar_valor(6, escala_geral)
            pygame.draw.line(ecra, cor_linha, p_origem, p_destino, espessura)
            
            # Desenhar seta de sentido de trânsito
            tamanho_seta = escalar_valor(15, escala_geral)
            desenhar_seta(ecra, p_origem, p_destino, cor_linha, tamanho_seta)
            
            mid_x, mid_y = (p_origem[0] + p_destino[0]) // 2, (p_origem[1] + p_destino[1]) // 2
            carros = estado_filas.get(via_id, 0)
            
            if estado_override.get(via_id, 0) != 0:
                raio_override = escalar_valor(18, escala_geral)
                pygame.draw.circle(ecra, (255, 200, 0), (mid_x, mid_y), raio_override)
                offset_m = escalar_valor(10, escala_geral)
                offset_y_m = escalar_valor(32, escala_geral)
                ecra.blit(fonte_pequena.render("[M]", True, (255, 200, 0)), (mid_x - offset_m, mid_y - offset_y_m))

            cor_badge = (200, 100, 0) if carros > 15 else (50, 100, 150)
            raio_badge = escalar_valor(14, escala_geral)
            pygame.draw.circle(ecra, cor_badge, (mid_x, mid_y), raio_badge)
            pygame.draw.circle(ecra, (255, 255, 255), (mid_x, mid_y), raio_badge, 2)
            
            txt_surface = fonte_pequena.render(str(carros), True, (255, 255, 255))
            ecra.blit(txt_surface, txt_surface.get_rect(center=(mid_x, mid_y)))
            offset_txt = escalar_valor(15, escala_geral)
            offset_txt_y = escalar_valor(15, escala_geral)
            ecra.blit(fonte_pequena.render(f"V{via_id}", True, (150, 150, 150)), (mid_x + offset_txt, mid_y + offset_txt_y))

        # Desenhar nós
        for nid, pos_base in nos_base.items():
            pos = escalar_coordenada(pos_base[0], pos_base[1], escala_x, escala_y)
            raio_no = escalar_valor(25, escala_geral)
            pygame.draw.circle(ecra, (40, 45, 50), pos, raio_no)
            pygame.draw.circle(ecra, (200, 200, 200), pos, raio_no, 3)
            txt_surface = fonte_grande.render(f"C{nid}", True, (255, 255, 255))
            ecra.blit(txt_surface, txt_surface.get_rect(center=pos))

        # --- PAINEL SUPERIOR DIREITO COM TEMPO E ALGORITMO ---
        painel_width = escalar_valor(200, escala_geral)
        painel_height = escalar_valor(160, escala_geral)
        painel_x = tamanho_atual[0] - painel_width  # Canto superior direito
        pygame.draw.rect(ecra, (15, 20, 25), (painel_x, 0, painel_width, painel_height))
        pygame.draw.line(ecra, (50, 150, 50), (painel_x, 0), (painel_x, painel_height), 2)
        pygame.draw.line(ecra, (50, 150, 50), (painel_x, painel_height), (tamanho_atual[0], painel_height), 2)
        
        # Ler valores globais
        import builtins
        tempo_exec = getattr(builtins, '_tempo_execucao_snmp', 0)
        algo_id = getattr(builtins, '_algo_id_snmp', 4)
        algo_map = {1: "ROUND_ROBIN", 2: "HEURISTICA", 3: "RL", 4: "BACKPRESSURE"}
        algo_nome = algo_map.get(algo_id, "DESCONHECIDO")
        
        # Formatar tempo em HH:MM:SS
        horas = tempo_exec // 3600
        minutos = (tempo_exec % 3600) // 60
        segundos = tempo_exec % 60
        tempo_formatado = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        
        offset_tempo_x = painel_x + escalar_valor(10, escala_geral)
        offset_tempo_y = escalar_valor(10, escala_geral)
        tempo_txt = fonte_pequena.render("Tempo:", True, (200, 200, 200))
        ecra.blit(tempo_txt, (offset_tempo_x, offset_tempo_y))
        tempo_val_txt = fonte_grande.render(tempo_formatado, True, (100, 200, 100))
        ecra.blit(tempo_val_txt, (offset_tempo_x, offset_tempo_y + escalar_valor(20, escala_geral)))
        
        # Desenhar label do algoritmo
        algo_label_txt = fonte_pequena.render("Algoritmo:", True, (200, 200, 200))
        ecra.blit(algo_label_txt, (offset_tempo_x, escalar_valor(55, escala_geral)))
        
        # Desenhar dropdown (atualizar posição e tamanho)
        altura_dropdown = escalar_valor(35, escala_geral)
        largura_dropdown = escalar_valor(180, escala_geral)
        dropdown.x = offset_tempo_x
        dropdown.y = escalar_valor(85, escala_geral)
        dropdown.width = largura_dropdown
        dropdown.height = altura_dropdown
        dropdown.fonte_pequena = fonte_pequena
        dropdown.fonte_grande = fonte_grande
        dropdown.escala_geral = escala_geral
        dropdown.draw(ecra)

        # --- SCOREBOARD ESTATÍSTICO (Centro Superior) ---
        offset_titulo_y = escalar_valor(10, escala_geral)
        ecra.blit(fonte_grande.render("METRICAS DE REDE", True, (255, 255, 255)), (escalar_valor(50, escala_geral), offset_titulo_y))
        
        stats_str = f"Escoados: {total_escoados} v | Vazão: {vazao_atual:.1f} v/min | Ocupação Média: {ocupacao_media:.1f} v/via | Pior Fila: {max_fila}v (Via {max_via})"
        offset_stats_y = escalar_valor(40, escala_geral)
        ecra.blit(fonte_pequena.render(stats_str, True, (200, 200, 200)), (escalar_valor(50, escala_geral), offset_stats_y))

        # --- BARRA DE ALERTA TRAP ---
        altura_painel_superior = escalar_valor(160, escala_geral)
        if alerta_trap["ativo"]:
            if agora < alerta_trap["expira"]:
                if int(agora * 2) % 2 == 0:
                    altura_alerta = escalar_valor(35, escala_geral)
                    pygame.draw.rect(ecra, (200, 40, 40), (0, altura_painel_superior, tamanho_atual[0], altura_alerta))
                    alerta_txt = f"ALERTA SNMP TRAP: Congestionamento Crítico na Via {alerta_trap['via']} ({alerta_trap['carros']} veículos!)"
                    txt_surface = fonte_alerta.render(alerta_txt, True, (255, 255, 255))
                    y_alerta = altura_painel_superior + altura_alerta // 2
                    ecra.blit(txt_surface, txt_surface.get_rect(center=(tamanho_atual[0]//2, y_alerta)))
            else:
                alerta_trap["ativo"] = False

        # --- CONSOLA DE STATUS (INFERIOR) ---
        altura_consola = escalar_valor(80, escala_geral)
        y_consola = tamanho_atual[1] - altura_consola
        pygame.draw.rect(ecra, (20, 25, 30), (0, y_consola, tamanho_atual[0], altura_consola))
        pygame.draw.line(ecra, (50, 150, 50), (0, y_consola), (tamanho_atual[0], y_consola), 2)
        
        offset_console_x = escalar_valor(20, escala_geral)
        offset_console_y1 = escalar_valor(10, escala_geral)
        offset_console_y2 = escalar_valor(35, escala_geral)
        offset_console_y3 = escalar_valor(60, escala_geral)
        
        status_rtg = f"RTGs: O(101)={estado_rtg.get(101,0)} | N(102)={estado_rtg.get(102,0)} | E(103)={estado_rtg.get(103,0)} | S(104)={estado_rtg.get(104,0)}"
        ecra.blit(fonte_pequena.render(status_rtg, True, (150, 200, 255)), (offset_console_x, y_consola + offset_console_y1))
        
        ecra.blit(fonte_pequena.render("RTG: <Via> <Valor>  |  OVERRIDE: O <Via> <0/1/2>", True, (150, 150, 150)), (offset_console_x, y_consola + offset_console_y2))
        ecra.blit(fonte_grande.render(f"CMC> {texto_input}_", True, (255, 200, 50)), (offset_console_x, y_consola + offset_console_y3))

        # --- CAIXA DE AVISO CENTRAL ---
        if confirmacao_algoritmo["ativo"]:
            tempo_agora = time.time()
            if tempo_agora - confirmacao_algoritmo["tempo"] < 3.0:
                # Desenhar caixa de aviso no centro
                caixa_largura = escalar_valor(600, escala_geral)
                caixa_altura = escalar_valor(150, escala_geral)
                caixa_x = (tamanho_atual[0] - caixa_largura) // 2
                caixa_y = (tamanho_atual[1] - caixa_altura) // 2
                
                # Fundo semitransparente (overlay)
                overlay = pygame.Surface((tamanho_atual[0], tamanho_atual[1]))
                overlay.set_alpha(100)
                overlay.fill((0, 0, 0))
                ecra.blit(overlay, (0, 0))
                
                # Caixa de diálogo
                pygame.draw.rect(ecra, (40, 60, 80), (caixa_x, caixa_y, caixa_largura, caixa_altura))
                pygame.draw.rect(ecra, (100, 200, 100), (caixa_x, caixa_y, caixa_largura, caixa_altura), 3)
                
                # Mensagem
                msg = "O sistema irá reiniciar com o algoritmo desejado"
                txt_aviso = fonte_grande.render(msg, True, (100, 200, 100))
                rect_txt = txt_aviso.get_rect(center=(tamanho_atual[0] // 2, caixa_y + caixa_altura // 2))
                ecra.blit(txt_aviso, rect_txt)
            else:
                confirmacao_algoritmo["ativo"] = False

        pygame.display.flip()
        relogio.tick(30)

if __name__ == "__main__":
    threading.Thread(target=iniciar_thread_snmp, daemon=True).start()
    desenhar_grafo()