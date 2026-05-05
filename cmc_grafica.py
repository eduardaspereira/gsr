# ==============================================================================
# Ficheiro: cmc_grafica.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Dashboard Gráfico (Cliente/Manager). Interface visual interativa
#            para monitorização e controlo do tráfego. Comunica com o Sistema
#            Central via SNMP, encapsulando pedidos JSON cifrados (Fernet)
#            através de um Túnel Seguro para garantir a integridade da rede.
# ==============================================================================

import pygame
import sys
import asyncio
import threading
import json
import time 
import networkx as nx
import math, re
import base64
import builtins
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pysnmp.hlapi.asyncio import *
from pysnmp.entity import engine as snmp_engine_mod, config as snmp_config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv

# =====================================================================
# 1. CONSTANTES E VARIÁVEIS GLOBAIS
# =====================================================================
RESOLUCAO_BASE = (900, 700)
OID_TUNEL = "1.3.6.1.3.2026.99.1.0"
cifra_fernet = None # Será preenchida após sucesso na autenticação

# Dicionários globais de estado da rede (sincronizados via SNMP)
cfg = {}
estado_semaforos = {}
estado_filas = {}
estado_rtg = {}
estado_override = {}
estado_links = {}

snmp_loop = None 
alerta_trap = {"ativo": False, "via": 0, "carros": 0, "expira": 0}
confirmacao_algoritmo = {"ativo": False, "tempo": 0}

# Variáveis partilhadas via builtins para acesso entre threads
builtins._tempo_execucao_snmp = 0
builtins._algo_id_snmp = 4  

# Carregamento inicial da configuração base
try:
    with open('config2.json', 'r') as f:
        cfg = json.load(f)
except Exception:
    cfg = {'roads': [], 'trafficLights': []} 

estado_semaforos.update({tl['roadIndex']: 1 for tl in cfg.get('trafficLights', [])})
estado_filas.update({r['id']: r.get('initialCount', 0) for r in cfg.get('roads', [])})
estado_rtg.update({r['id']: r.get('rtg', 0) for r in cfg.get('roads', []) if r['type'] == 3})
estado_override.update({tl['roadIndex']: 0 for tl in cfg.get('trafficLights', [])})
estado_links.update({f"{l['src']}.{l['dest']}": 0 for l in cfg.get('links', [])})


# =====================================================================
# 2. SEGURANÇA E AUTENTICAÇÃO
# =====================================================================
def autenticar_utilizador_pygame(ecra, relogio):
    """
    Renderiza um ecrã de bloqueio nativo em Pygame.
    Garante que a interface principal só é exposta após introdução da password correta.
    """
    fonte_titulo = pygame.font.SysFont("Courier New", 26, bold=True)
    fonte_texto = pygame.font.SysFont("Arial", 18)
    fonte_input = pygame.font.SysFont("Courier New", 24, bold=True)
    
    caixa_input = pygame.Rect(RESOLUCAO_BASE[0]//2 - 150, RESOLUCAO_BASE[1]//2 - 20, 300, 45)
    cor_ativa = (50, 150, 255)
    
    password_digitada = ""
    mensagem_erro = ""
    tempo_erro = 0
    
    while True:
        agora = time.time()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if mensagem_erro != "":
                    mensagem_erro = "" 
                
                if evento.key == pygame.K_RETURN:
                    if len(password_digitada) > 0:
                        return password_digitada.encode()
                elif evento.key == pygame.K_BACKSPACE:
                    password_digitada = password_digitada[:-1]
                elif evento.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif evento.unicode.isprintable():
                    password_digitada += evento.unicode

        ecra.fill((30, 35, 40))
        
        # Textos de UI
        texto_titulo = fonte_titulo.render("SISTEMA CENTRAL DE TRÁFEGO", True, (255, 255, 255))
        texto_sub = fonte_texto.render("Introduza a password mestra para destrancar a rede:", True, (200, 200, 200))
        ecra.blit(texto_titulo, texto_titulo.get_rect(center=(RESOLUCAO_BASE[0]//2, RESOLUCAO_BASE[1]//2 - 80)))
        ecra.blit(texto_sub, texto_sub.get_rect(center=(RESOLUCAO_BASE[0]//2, RESOLUCAO_BASE[1]//2 - 45)))
        
        # Desenhar Caixa de Input e Máscara de Password
        pygame.draw.rect(ecra, (20, 25, 30), caixa_input)
        pygame.draw.rect(ecra, cor_ativa, caixa_input, 2)
        
        texto_mascarado = "*" * len(password_digitada)
        texto_surface = fonte_input.render(texto_mascarado + "_", True, (255, 255, 255))
        ecra.blit(texto_surface, (caixa_input.x + 10, caixa_input.y + 10))
        
        # Gestão de Erros Visuais
        if mensagem_erro:
            texto_erro = fonte_texto.render(mensagem_erro, True, (255, 80, 80))
            ecra.blit(texto_erro, texto_erro.get_rect(center=(RESOLUCAO_BASE[0]//2, RESOLUCAO_BASE[1]//2 + 50)))
            if agora - tempo_erro > 3.0: 
                mensagem_erro = ""
                
        texto_dica = fonte_texto.render("Pressione [ENTER] para confirmar ou [ESC] para sair", True, (100, 100, 100))
        ecra.blit(texto_dica, texto_dica.get_rect(center=(RESOLUCAO_BASE[0]//2, RESOLUCAO_BASE[1] - 30)))

        pygame.display.flip()
        relogio.tick(30)


# =====================================================================
# 3. COMPONENTES VISUAIS E TOPOLOGIA
# =====================================================================
def escalar_valor(valor, escala):
    """Garante que os elementos da UI escalam proporcionalmente ao redimensionar a janela."""
    return max(1, int(valor * escala))

def desenhar_seta(superficie, ponto_o, ponto_d, cor, tamanho):
    """Desenha setas direcionais nas vias para indicar o fluxo de trânsito."""
    mx, my = ponto_o[0] + (ponto_d[0] - ponto_o[0]) * 0.25, ponto_o[1] + (ponto_d[1] - ponto_o[1]) * 0.25
    dx, dy = ponto_d[0] - ponto_o[0], ponto_d[1] - ponto_o[1]
    angulo = math.atan2(dy, dx)
    
    bx, by = int(mx - tamanho * math.cos(angulo)), int(my - tamanho * math.sin(angulo))
    pygame.draw.line(superficie, cor, (bx, by), (int(mx), int(my)), 3)
    
    abertura, comp_lateral = math.pi / 5, tamanho * 0.8
    p1 = (int(mx - comp_lateral * math.cos(angulo + abertura)), int(my - comp_lateral * math.sin(angulo + abertura)))
    p2 = (int(mx - comp_lateral * math.cos(angulo - abertura)), int(my - comp_lateral * math.sin(angulo - abertura)))
    
    pygame.draw.line(superficie, cor, (int(mx), int(my)), p1, 4)
    pygame.draw.line(superficie, cor, (int(mx), int(my)), p2, 4)

def gerar_topologia_dinamica(cfg_atual, resolucao_base=(900, 700), margem=120):
    """Lê o ficheiro JSON de configuração e calcula as coordenadas X,Y de cada nó e aresta."""
    cruzamentos = cfg_atual.get('crossroads', [])
    num_cruzamentos = len(cruzamentos)
    
    colunas = 4 if num_cruzamentos == 8 else math.ceil(math.sqrt(num_cruzamentos))
    linhas = math.ceil(num_cruzamentos / colunas)
    
    pos_normalizada_cruzamentos = {} 
    for idx, cruz in enumerate(cruzamentos):
        linha = idx // colunas
        coluna = idx % colunas
        x = -0.6 + (coluna / max(1, colunas - 1)) * 1.2 if colunas > 1 else 0
        y = -0.6 + (linha / max(1, linhas - 1)) * 1.2 if linhas > 1 else 0
        pos_normalizada_cruzamentos[cruz['id']] = (x, y)
    
    grafo_vias = {} 
    detalhes_vias = {} 
    
    for via in cfg_atual.get('roads', []):
        id_via = via['id']
        tipo_via = via['type']
        nome_via = via.get('name', '')
        detalhes_vias[id_via] = (nome_via, tipo_via)
        
        # Mapeamento com base nos Regex dos nomes das vias no JSON
        if tipo_via == 1: 
            match = re.search(r'C(\d+)->C(\d+)', nome_via)
            if match:
                src_cr, dst_cr = int(match.group(1)), int(match.group(2))
                grafo_vias[id_via] = (f"C{src_cr}", f"C{dst_cr}")
        elif tipo_via == 3: 
            match = re.search(r'\(->C(\d+)\)', nome_via)
            if match:
                dst_cr = int(match.group(1))
                grafo_vias[id_via] = (f"SRC_{id_via}", f"C{dst_cr}")
        elif tipo_via == 2: 
            match = re.search(r'\(C(\d+)->\)', nome_via)
            if match:
                src_cr = int(match.group(1))
                grafo_vias[id_via] = (f"C{src_cr}", f"SINK_{id_via}")
    
    pos_normalizada_nos = {} 
    for id_cr, pos in pos_normalizada_cruzamentos.items():
        pos_normalizada_nos[f"C{id_cr}"] = pos
    
    for id_via, (no_origem, no_destino) in grafo_vias.items():
        nome_via, tipo_via = detalhes_vias[id_via]
        if tipo_via == 3:
            match = re.search(r'\(->C(\d+)\)', nome_via)
            if match:
                dst_cr = int(match.group(1))
                if dst_cr in pos_normalizada_cruzamentos:
                    x_cr, y_cr = pos_normalizada_cruzamentos[dst_cr]
                    if "Norte" in nome_via: x_f, y_f = x_cr, y_cr - 0.25
                    elif "Sul" in nome_via: x_f, y_f = x_cr, y_cr + 0.25
                    elif "Oeste" in nome_via: x_f, y_f = x_cr - 0.25, y_cr
                    elif "Este" in nome_via: x_f, y_f = x_cr + 0.25, y_cr
                    else: x_f, y_f = x_cr - 0.3, y_cr
                    pos_normalizada_nos[no_origem] = (x_f, y_f)
        elif tipo_via == 2:
            match = re.search(r'\(C(\d+)->\)', nome_via)
            if match:
                src_cr = int(match.group(1))
                if src_cr in pos_normalizada_cruzamentos:
                    x_cr, y_cr = pos_normalizada_cruzamentos[src_cr]
                    if "Norte" in nome_via: x_f, y_f = x_cr, y_cr - 0.25
                    elif "Sul" in nome_via: x_f, y_f = x_cr, y_cr + 0.25
                    elif "Oeste" in nome_via: x_f, y_f = x_cr - 0.25, y_cr
                    elif "Este" in nome_via: x_f, y_f = x_cr + 0.25, y_cr
                    else: x_f, y_f = x_cr + 0.3, y_cr
                    pos_normalizada_nos[no_destino] = (x_f, y_f)
    
    largura, altura = resolucao_base
    pos_px_nos = {} 
    coord_x = [p[0] for p in pos_normalizada_nos.values()]
    coord_y = [p[1] for p in pos_normalizada_nos.values()]
    
    min_x, max_x = min(coord_x) if coord_x else -1, max(coord_x) if coord_x else 1
    min_y, max_y = min(coord_y) if coord_y else -1, max(coord_y) if coord_y else 1
    range_x = max_x - min_x if max_x > min_x else 1
    range_y = max_y - min_y if max_y > min_y else 1
    
    area_util_l, area_util_a = largura - 2 * margem, altura - 2 * margem
    for no, (xn, yn) in pos_normalizada_nos.items():
        x_px = margem + ((xn - min_x) / range_x) * area_util_l
        y_px = margem + ((yn - min_y) / range_y) * area_util_a
        pos_px_nos[no] = (int(x_px), int(y_px))
    
    arestas_px = {}
    for id_via, (n_src, n_dst) in grafo_vias.items():
        if n_src in pos_px_nos and n_dst in pos_px_nos:
            arestas_px[id_via] = (pos_px_nos[n_src], pos_px_nos[n_dst])
    
    return pos_px_nos, arestas_px

class MenuSuspenso:
    """Elemento de Interface de Utilizador para selecionar opções (Ex: Algoritmos e Mapas)."""
    def __init__(self, x, y, largura, altura, opcoes, fonte, indice_selecionado=3):
        self.x = x
        self.y = y
        self.largura = largura
        self.altura = altura
        self.opcoes = opcoes
        self.aberto = False
        self.indice_selecionado = indice_selecionado
        self.fonte = fonte
    
    def desenhar(self, superficie):
        cor_fundo = (50, 70, 90) if not self.aberto else (70, 90, 110)
        pygame.draw.rect(superficie, cor_fundo, (self.x, self.y, self.largura, self.altura))
        pygame.draw.rect(superficie, (150, 150, 150), (self.x, self.y, self.largura, self.altura), 2)
        
        texto_opcao = self.opcoes[self.indice_selecionado][1]
        superficie_texto = self.fonte.render(texto_opcao, True, (255, 255, 255))
        superficie.blit(superficie_texto, (self.x + 10, self.y + 8))
        
        cx = self.x + self.largura - 15
        cy = self.y + self.altura / 2
        tamanho_seta = self.altura * 0.15
        
        if self.aberto:
            p1, p2, p3 = (cx - tamanho_seta, cy - tamanho_seta/2), (cx + tamanho_seta, cy - tamanho_seta/2), (cx, cy + tamanho_seta)
        else:
            p1, p2, p3 = (cx - tamanho_seta/2, cy - tamanho_seta), (cx - tamanho_seta/2, cy + tamanho_seta), (cx + tamanho_seta, cy)
        pygame.draw.polygon(superficie, (200, 200, 200), [p1, p2, p3])
        
        if self.aberto:
            y_offset = self.y + self.altura
            for idx, (_, nome) in enumerate(self.opcoes):
                cor_item = (100, 120, 140) if idx == self.indice_selecionado else (60, 80, 100)
                pygame.draw.rect(superficie, cor_item, (self.x, y_offset, self.largura, self.altura))
                pygame.draw.rect(superficie, (150, 150, 150), (self.x, y_offset, self.largura, self.altura), 1)
                superficie.blit(self.fonte.render(nome, True, (255, 255, 255)), (self.x + 10, y_offset + 8))
                y_offset += self.altura
    
    def processar_clique(self, mx, my):
        """Verifica se o utilizador clicou no menu ou numa opção e devolve o valor associado."""
        if self.x <= mx <= self.x + self.largura and self.y <= my <= self.y + self.altura:
            self.aberto = not self.aberto
            return None
            
        if self.aberto:
            y_offset = self.y + self.altura
            for idx, (id_opcao, _) in enumerate(self.opcoes):
                if self.x <= mx <= self.x + self.largura and y_offset <= my <= y_offset + self.altura:
                    self.indice_selecionado = idx
                    self.aberto = False
                    return id_opcao
                y_offset += self.altura
        return None

# =====================================================================
# 4. COMUNICAÇÃO SNMP SEGURA (CLIENTE)
# =====================================================================
def processar_trap(snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
    """Callback assíncrono acionado quando o Servidor SNMP envia uma Trap de Congestionamento."""
    global alerta_trap
    via, carros = 0, 0
    for nome, valor in varBinds:
        if "2026.1.1.1" in str(nome): via = int(valor)
        if "2026.1.1.2" in str(nome): carros = int(valor)
    
    if via > 0:
        alerta_trap = {"ativo": True, "via": via, "carros": carros, "expira": time.time() + 6.0}

async def servidor_traps():
    """Inicia a escuta na porta UDP 16216 para receber notificações assíncronas do Sistema Central."""
    motor = snmp_engine_mod.SnmpEngine()
    snmp_config.addTransport(motor, udp.domainName, udp.UdpTransport().openServerMode(('127.0.0.1', 16216)))
    snmp_config.addV1System(motor, 'my-area', 'public')
    snmp_config.addVacmUser(motor, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6), (1, 3, 6))
    ntfrcv.NotificationReceiver(motor, processar_trap)
    while True: await asyncio.sleep(3600)

async def enviar_comando_tunel(ip, porta, comunidade, dicionario_payload):
    """
    Núcleo da Segurança: Serializa as instruções JSON e aplica criptografia Fernet.
    O resultado é um bloco binário opaco injetado numa OctetString SNMP válida.
    """
    motor_snmp = SnmpEngine()
    payload_json = json.dumps(dicionario_payload).encode('utf-8')
    payload_cifrado = cifra_fernet.encrypt(payload_json)
    
    erro_indicacao, erro_estado, indice_erro, binds = await setCmd(
        motor_snmp,
        CommunityData(comunidade, mpModel=1),
        UdpTransportTarget((ip, porta), timeout=1, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity(OID_TUNEL), OctetString(payload_cifrado))
    )
    motor_snmp.transportDispatcher.closeDispatcher()
    return erro_indicacao, erro_estado, binds

def disparar_tarefa_fundo(corotina):
    """Lança requisições SNMP numa Thread separada para não bloquear os FPS da Interface Gráfica."""
    threading.Thread(target=lambda: asyncio.run(corotina), daemon=True).start()

async def enviar_algoritmo_snmp(id_algoritmo):
    payload = {"comando": "SET_ALG", "alg_id": id_algoritmo}
    await enviar_comando_tunel('127.0.0.1', 16161, 'public', payload)

async def enviar_novo_rtg_snmp(via, novo_rtg):
    payload = {"comando": "SET_RTG", "via": via, "valor": novo_rtg}
    await enviar_comando_tunel('127.0.0.1', 16161, 'public', payload)

async def enviar_override_snmp(via, modo):
    payload = {"comando": "SET_OVERRIDE", "via": via, "modo": modo}
    await enviar_comando_tunel('127.0.0.1', 16161, 'public', payload)

async def obter_dados_snmp():
    """Pooling contínuo (2Hz) para puxar o estado cifrado da rede através do Túnel."""
    while True:
        try:
            payload = {"comando": "PULL_STATE"}
            erro_ind, erro_stat, binds = await enviar_comando_tunel('127.0.0.1', 16161, 'public', payload)

            if not erro_ind and not erro_stat:
                for nome, valor in binds:
                    if str(nome) == OID_TUNEL:
                        resposta_limpa = cifra_fernet.decrypt(bytes(valor)).decode('utf-8')
                        dados = json.loads(resposta_limpa)

                        builtins._tempo_execucao_snmp = dados.get("tempo", 0)
                        builtins._algo_id_snmp = dados.get("algo_id", 4)
                        
                        for k, v in dados.get("filas", {}).items(): estado_filas[int(k)] = v
                        for k, v in dados.get("semaforos", {}).items(): estado_semaforos[int(k)] = v
                        for k, v in dados.get("rtgs", {}).items(): estado_rtg[int(k)] = v
                        for k, v in dados.get("overrides", {}).items(): estado_override[int(k)] = v
                        for k, v in dados.get("links", {}).items(): estado_links[k] = v
        except Exception:
            pass # Silencia erros de timeout ou rede para não poluir o terminal gráfico
        
        await asyncio.sleep(0.5)

def iniciar_thread_snmp():
    global snmp_loop
    snmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(snmp_loop)
    snmp_loop.run_until_complete(asyncio.gather(obter_dados_snmp(), servidor_traps()))

# =====================================================================
# 5. LOOP PRINCIPAL DA INTERFACE GRÁFICA (PYGAME)
# =====================================================================
def iniciar_dashboard():
    global confirmacao_algoritmo, cfg, cifra_fernet

    print("A inicializar motor gráfico...")
    pygame.init()
    ecra = pygame.display.set_mode(RESOLUCAO_BASE, pygame.RESIZABLE)
    pygame.display.set_caption("Dashboard Seguro (Fase B) - Gestão de Tráfego")
    relogio = pygame.time.Clock()

    # --- 1. BLOQUEIO INICIAL: AUTENTICAÇÃO ---
    autenticado = False
    while not autenticado:
        password_submetida = autenticar_utilizador_pygame(ecra, relogio)
        
        salt = b'GSR_UM_2026'
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
        chave_cofre = base64.urlsafe_b64encode(kdf.derive(password_submetida))
        ferramenta_cofre = Fernet(chave_cofre)

        try:
            with open("seguranca.key", "rb") as f:
                chave_encriptada_ficheiro = f.read()
            CHAVE_MESTRA = ferramenta_cofre.decrypt(chave_encriptada_ficheiro)
            cifra_fernet = Fernet(CHAVE_MESTRA)
            autenticado = True
            print("[OK] Autenticação Validada. Túnel Seguro Ativo.\n")
        except Exception:
            ecra.fill((30, 35, 40))
            fonte_erro = pygame.font.SysFont("Arial", 20, bold=True)
            texto_erro = fonte_erro.render("ERRO: Password Incorreta ou Cofre Ausente!", True, (255, 80, 80))
            ecra.blit(texto_erro, texto_erro.get_rect(center=(RESOLUCAO_BASE[0]//2, RESOLUCAO_BASE[1]//2)))
            pygame.display.flip()
            time.sleep(2) 

    # --- 2. LIGAÇÃO ESTABELECIDA: INICIAR THREADS DE REDE ---
    threading.Thread(target=iniciar_thread_snmp, daemon=True).start()

    # --- 3. PREPARAÇÃO DO ESTADO VISUAL ---
    tamanho_atual = RESOLUCAO_BASE
    pos_nos_base, pos_arestas_base = gerar_topologia_dinamica(cfg, RESOLUCAO_BASE)
    
    texto_input_consola = ""
    tempo_anterior, escoados_anterior, vazao_atual = time.time(), 0, 0.0
    algo_anterior = 4 
    
    opcoes_algos = [(1, "ROUND_ROBIN"), (2, "HEURISTICA"), (3, "RL"), (4, "BACKPRESSURE")]
    opcoes_mapas = [(0, "Mapa 1 (config)"), (1, "Mapa 2 (config2)"), (2, "Mapa 3 (config3)")]
    ficheiros_mapas = ["config.json", "config2.json", "config3.json"]

    via_selecionada = None
    texto_rtg_via = ""
    centros_vias = {} 
    consola_visivel = False

    # --- 4. CICLO DE VIDA DO DASHBOARD (A RENDERIZAÇÃO) ---
    while True:
        agora = time.time()
        escala_x = tamanho_atual[0] / RESOLUCAO_BASE[0]
        escala_y = tamanho_atual[1] / RESOLUCAO_BASE[1]
        escala_global = min(escala_x, escala_y)
        
        # --- 4.1 CÁLCULO DE ESTATÍSTICAS ---
        vias_saida = [str(r['id']) for r in cfg.get('roads', []) if r['type'] == 2]
        vias_entrada = [r['id'] for r in cfg.get('roads', []) if r['type'] == 3]
        total_escoados = sum(val for chave, val in estado_links.items() if any(chave.endswith(f".{s}") for s in vias_saida))
        
        vias_internas = [r['id'] for r in cfg.get('roads', []) if r['type'] == 1]
        ocupacao_media = sum(estado_filas.get(v, 0) for v in vias_internas) / max(1, len(vias_internas))
        
        fila_max, via_pior = 0, 0
        for v in vias_entrada + vias_internas:
            if estado_filas.get(v, 0) > fila_max: 
                fila_max, via_pior = estado_filas.get(v, 0), v

        algo_atual_snmp = getattr(builtins, '_algo_id_snmp', 4)
        if algo_atual_snmp != algo_anterior:
            vazao_atual = 0.0
            escoados_anterior = total_escoados
            tempo_anterior = agora
            algo_anterior = algo_atual_snmp

        if agora - tempo_anterior >= 15.0:
            vazao_atual = ((total_escoados - escoados_anterior) / (agora - tempo_anterior)) * 60.0
            tempo_anterior, escoados_anterior = agora, total_escoados

        # --- 4.2 GESTÃO DE EVENTOS DE UTILIZADOR ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT: 
                pygame.quit()
                sys.exit()
                
            elif evento.type == pygame.VIDEORESIZE: 
                tamanho_atual = evento.size
                
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                mx, my = evento.pos
                
                # Botão Toggle da Consola
                tam_btn = max(1, int(40 * escala_global))
                rect_toggle = pygame.Rect(tamanho_atual[0] - tam_btn - 10, tamanho_atual[1] - tam_btn - 10, tam_btn, tam_btn)
                
                if rect_toggle.collidepoint(mx, my):
                    consola_visivel = not consola_visivel
                    continue
                
                # Menu Mudança de Mapa
                if 'menu_mapas' in locals():
                    novo_mapa = menu_mapas.processar_clique(mx, my)
                    if novo_mapa is not None:
                        try:
                            with open(ficheiros_mapas[novo_mapa], 'r') as f:
                                cfg = json.load(f)
                            
                            # Reset Seguro à Memória Gráfica
                            estado_semaforos.clear()
                            estado_semaforos.update({tl['roadIndex']: 1 for tl in cfg['trafficLights']})
                            estado_filas.clear()
                            estado_filas.update({r['id']: r.get('initialCount', 0) for r in cfg['roads']})
                            estado_rtg.clear()
                            estado_rtg.update({r['id']: r.get('rtg', 0) for r in cfg['roads'] if r['type'] == 3})
                            estado_override.clear()
                            estado_override.update({tl['roadIndex']: 0 for tl in cfg['trafficLights']})
                            estado_links.clear()
                            estado_links.update({f"{l['src']}.{l['dest']}": 0 for l in cfg.get('links', [])})
                            
                            pos_nos_base, pos_arestas_base = gerar_topologia_dinamica(cfg, RESOLUCAO_BASE)
                            via_selecionada = None
                            menu_mapas.indice_selecionado = novo_mapa
                        except Exception as e:
                            print(f"[ERRO] Falha ao carregar configuração do mapa: {e}")
                        continue
                
                # Menu Algoritmos
                if 'menu_algoritmos' in locals():
                    novo_algoritmo = menu_algoritmos.processar_clique(mx, my)
                    if novo_algoritmo:
                        confirmacao_algoritmo = {"ativo": True, "tempo": time.time()}
                        disparar_tarefa_fundo(enviar_algoritmo_snmp(novo_algoritmo))
                        continue

                # Caixa de Overrides/Gestão da Via Selecionada
                if via_selecionada and via_selecionada in centros_vias:
                    cx, cy = centros_vias[via_selecionada]
                    larg_caixa, alt_caixa = escalar_valor(180, escala_global), escalar_valor(120, escala_global)
                    cx_caixa = min(cx, tamanho_atual[0] - larg_caixa)
                    cy_caixa = min(cy, tamanho_atual[1] - alt_caixa)
                    
                    rect_caixa = pygame.Rect(cx_caixa, cy_caixa, larg_caixa, alt_caixa)
                    
                    if rect_caixa.collidepoint(mx, my):
                        btn_auto = pygame.Rect(cx_caixa + escalar_valor(10, escala_global), cy_caixa + escalar_valor(75, escala_global), escalar_valor(50, escala_global), escalar_valor(30, escala_global))
                        btn_red = pygame.Rect(cx_caixa + escalar_valor(65, escala_global), cy_caixa + escalar_valor(75, escala_global), escalar_valor(45, escala_global), escalar_valor(30, escala_global))
                        btn_green = pygame.Rect(cx_caixa + escalar_valor(115, escala_global), cy_caixa + escalar_valor(75, escala_global), escalar_valor(55, escala_global), escalar_valor(30, escala_global))
                        
                        if btn_auto.collidepoint(mx, my):
                            disparar_tarefa_fundo(enviar_override_snmp(via_selecionada, 0))
                            via_selecionada = None
                        elif btn_red.collidepoint(mx, my):
                            disparar_tarefa_fundo(enviar_override_snmp(via_selecionada, 2))
                            via_selecionada = None
                        elif btn_green.collidepoint(mx, my):
                            disparar_tarefa_fundo(enviar_override_snmp(via_selecionada, 1))
                            via_selecionada = None
                    else:
                        via_selecionada = None # Clicou fora, fecha a caixa
                else:
                    # Lógica de seleção (clicar na bolinha da via)
                    for id_via, (cx_via, cy_via) in centros_vias.items():
                        if math.hypot(mx - cx_via, my - cy_via) < escalar_valor(25, escala_global):
                            via_selecionada = id_via
                            texto_rtg_via = str(estado_rtg.get(id_via, ""))
                            break

            elif evento.type == pygame.KEYDOWN:
                if via_selecionada:
                    if via_selecionada in vias_entrada:
                        if evento.key == pygame.K_BACKSPACE: 
                            texto_rtg_via = texto_rtg_via[:-1]
                        elif evento.key == pygame.K_RETURN:
                            if texto_rtg_via.isdigit():
                                disparar_tarefa_fundo(enviar_novo_rtg_snmp(via_selecionada, int(texto_rtg_via)))
                            via_selecionada = None
                        elif evento.unicode.isdigit(): 
                            texto_rtg_via += evento.unicode
                elif consola_visivel: 
                    if evento.key == pygame.K_BACKSPACE: texto_input_consola = texto_input_consola[:-1]
                    elif evento.key == pygame.K_RETURN:
                        try:
                            comandos = texto_input_consola.strip().split(' ')
                            if len(comandos) == 2 and comandos[0].upper() == "ALG": 
                                disparar_tarefa_fundo(enviar_algoritmo_snmp(int(comandos[1])))
                            elif len(comandos) == 2: 
                                disparar_tarefa_fundo(enviar_novo_rtg_snmp(int(comandos[0]), int(comandos[1])))
                            elif len(comandos) == 3 and comandos[0].upper() == 'O': 
                                disparar_tarefa_fundo(enviar_override_snmp(int(comandos[1]), int(comandos[2])))
                        except: pass
                        texto_input_consola = ""
                    elif evento.unicode.isprintable(): 
                        texto_input_consola += evento.unicode

        # --- 4.3 RENDERIZAÇÃO GERAL ---
        ecra.fill((30, 35, 40)) # Fundo limpo
        
        fonte_pequena = pygame.font.SysFont("Arial", escalar_valor(14, escala_global), bold=True)
        fonte_grande = pygame.font.SysFont("Courier New", escalar_valor(20, escala_global), bold=True)
        fonte_alerta = pygame.font.SysFont("Arial", escalar_valor(22, escala_global), bold=True)

        tempo_sc = getattr(builtins, '_tempo_execucao_snmp', 0)
        str_relogio = f"{tempo_sc // 3600:02d}:{(tempo_sc % 3600) // 60:02d}:{tempo_sc % 60:02d}"

        margem_esq = escalar_valor(20, escala_global) 
        posicao_y = escalar_valor(15, escala_global)
        
        # Cabeçalho de Métricas
        superficie_titulo = fonte_grande.render("METRICAS DE REDE - ", True, (255, 255, 255))
        superficie_tempo = fonte_grande.render(str_relogio, True, (100, 255, 100))
        ecra.blit(superficie_titulo, (margem_esq, posicao_y))
        ecra.blit(superficie_tempo, (margem_esq + superficie_titulo.get_width(), posicao_y))
        
        posicao_y += escalar_valor(30, escala_global)
        str_estatisticas = f"Escoados: {total_escoados} v | Vazão: {vazao_atual:.1f} v/min | Ocupação Média: {ocupacao_media:.1f} v/via | Pior Fila: {fila_max}v (V{via_pior})"
        ecra.blit(fonte_pequena.render(str_estatisticas, True, (200, 200, 200)), (margem_esq, posicao_y))
        
        posicao_y += escalar_valor(30, escala_global)
        
        # Menus Suspensos
        if 'menu_algoritmos' not in locals():
            menu_algoritmos = MenuSuspenso(margem_esq, posicao_y, escalar_valor(180, escala_global), escalar_valor(35, escala_global), opcoes_algos, fonte_pequena)
        else:
            menu_algoritmos.x, menu_algoritmos.y = margem_esq, posicao_y
            menu_algoritmos.largura, menu_algoritmos.altura = escalar_valor(180, escala_global), escalar_valor(35, escala_global)
            menu_algoritmos.fonte = fonte_pequena
        
        if 1 <= algo_atual_snmp <= 4 and not menu_algoritmos.aberto:
            menu_algoritmos.indice_selecionado = algo_atual_snmp - 1

        if 'menu_mapas' not in locals():
            menu_mapas = MenuSuspenso(tamanho_atual[0] - escalar_valor(220, escala_global), escalar_valor(15, escala_global), escalar_valor(200, escala_global), escalar_valor(35, escala_global), opcoes_mapas, fonte_pequena, indice_selecionado=1)
        else:
            menu_mapas.x = tamanho_atual[0] - escalar_valor(220, escala_global)
            menu_mapas.y = escalar_valor(15, escala_global)
            menu_mapas.largura = escalar_valor(200, escala_global)
            menu_mapas.altura = escalar_valor(35, escala_global)
            menu_mapas.fonte = fonte_pequena

        # Renderizar Alerta Trap
        if alerta_trap["ativo"]:
            if agora < alerta_trap["expira"]:
                if int(agora * 2) % 2 == 0: # Efeito de piscar (blink)
                    x_trap = margem_esq + escalar_valor(200, escala_global) 
                    w_trap = tamanho_atual[0] - x_trap - margem_esq
                    pygame.draw.rect(ecra, (200, 40, 40), (x_trap, posicao_y, w_trap, escalar_valor(35, escala_global)), border_radius=4)
                    texto_alerta = f"ALERTA TRAP: Congestionamento na Via {alerta_trap['via']} ({alerta_trap['carros']} v!)"
                    superficie_alerta = fonte_alerta.render(texto_alerta, True, (255, 255, 255))
                    ecra.blit(superficie_alerta, superficie_alerta.get_rect(center=(x_trap + w_trap//2, posicao_y + escalar_valor(17, escala_global))))
            else: alerta_trap["ativo"] = False

        # --- 4.4 DESENHO DO GRAFO (Nós e Vias) ---
        centros_vias.clear() 
        
        for id_via, (p_origem, p_destino) in pos_arestas_base.items():
            po, pd = (int(p_origem[0] * escala_x), int(p_origem[1] * escala_y)), (int(p_destino[0] * escala_x), int(p_destino[1] * escala_y))
            dx, dy = pd[0] - po[0], pd[1] - po[1]
            distancia = math.hypot(dx, dy)
            meio_x, meio_y = (po[0] + pd[0]) / 2, (po[1] + pd[1]) / 2
            
            if distancia > 0:
                nx, ny = -dy / distancia, dx / distancia
                afastamento = escalar_valor(18, escala_global)
                po_deslocado, pd_deslocado = (int(po[0] + nx * afastamento), int(po[1] + ny * afastamento)), (int(pd[0] + nx * afastamento), int(pd[1] + ny * afastamento))
                centro_x, centro_y = int(meio_x + nx * afastamento), int(meio_y + ny * afastamento)
            else:
                po_deslocado, pd_deslocado, centro_x, centro_y = po, pd, int(meio_x), int(meio_y)
            
            centros_vias[id_via] = (centro_x, centro_y)
            
            # Cor do Semáforo (Vermelho, Verde, Amarelo)
            cor_via = (80, 80, 80)
            if id_via in estado_semaforos:
                st = estado_semaforos[id_via]
                cor_via = (200, 50, 50) if st == 1 else (50, 200, 50) if st == 2 else (200, 150, 50)
            
            pygame.draw.line(ecra, cor_via, po_deslocado, pd_deslocado, escalar_valor(6, escala_global))
            desenhar_seta(ecra, po_deslocado, pd_deslocado, cor_via, escalar_valor(20, escala_global))
            
            carros = estado_filas.get(id_via, 0)
            
            # Renderizar indicador de Override Manual [M]
            if estado_override.get(id_via, 0) != 0:
                pygame.draw.circle(ecra, (255, 200, 0), (centro_x, centro_y), escalar_valor(18, escala_global))
                ecra.blit(fonte_pequena.render("[M]", True, (255, 200, 0)), (centro_x - escalar_valor(10, escala_global), centro_y - escalar_valor(32, escala_global)))
            
            # Bolinha com número de carros
            pygame.draw.circle(ecra, (200, 100, 0) if carros > 15 else (50, 100, 150), (centro_x, centro_y), escalar_valor(14, escala_global))
            pygame.draw.circle(ecra, (255, 255, 255), (centro_x, centro_y), escalar_valor(14, escala_global), 2)
            superficie_carros = fonte_pequena.render(str(carros), True, (255, 255, 255))
            ecra.blit(superficie_carros, superficie_carros.get_rect(center=(centro_x, centro_y)))
            
            txt_x, txt_y = (int(centro_x + nx * escalar_valor(22, escala_global)), int(centro_y + ny * escalar_valor(22, escala_global))) if distancia > 0 else (centro_x+15, centro_y+15)
            ecra.blit(fonte_pequena.render(f"V{id_via}", True, (150, 150, 150)), (txt_x - 5, txt_y - 5))

        # Desenhar os Nós de Cruzamento (Centros C1, C2...)
        for id_no, pos_base in pos_nos_base.items():
            posicao_real = (int(pos_base[0] * escala_x), int(pos_base[1] * escala_y))
            if id_no.startswith('C'):
                raio = escalar_valor(25, escala_global)
                pygame.draw.circle(ecra, (35, 40, 45), posicao_real, raio)
                pygame.draw.circle(ecra, (200, 200, 200), posicao_real, raio, 3)
                superficie_no = fonte_grande.render(id_no, True, (255, 255, 255))
                ecra.blit(superficie_no, superficie_no.get_rect(center=posicao_real))

        # --- 4.5 RENDERIZAÇÃO DA CONSOLA / JANELAS FLUTUANTES ---
        if consola_visivel:
            altura_consola = escalar_valor(110, escala_global) 
            y_consola = tamanho_atual[1] - altura_consola
            pygame.draw.rect(ecra, (20, 25, 30), (0, y_consola, tamanho_atual[0], altura_consola))
            pygame.draw.line(ecra, (50, 150, 50), (0, y_consola), (tamanho_atual[0], y_consola), 2)
            
            str_rtgs = f"RTGs (Entradas): {' | '.join([f'V{v}={estado_rtg.get(v,0)}' for v in sorted(vias_entrada)])}"
            ecra.blit(fonte_pequena.render(str_rtgs, True, (50, 150, 255)), (escalar_valor(20, escala_global), y_consola + escalar_valor(15, escala_global)))
            
            texto_ajuda = "O <Via> <0: Auto | 1: Vermelho | 2: Verde>   |   RTG: <via> <valor>   |   ALG <1: RR | 2: Heurística | 3: RL | 4: Back Pressure>"
            ecra.blit(fonte_pequena.render(texto_ajuda, True, (150, 150, 150)), (escalar_valor(20, escala_global), y_consola + escalar_valor(45, escala_global)))
            
            ecra.blit(fonte_grande.render(f"CMC> {texto_input_consola}_", True, (255, 200, 50)), (escalar_valor(20, escala_global), y_consola + escalar_valor(75, escala_global)))

        # Botão de Toggle da Consola
        tam_btn = max(1, int(40 * escala_global))
        rect_toggle = pygame.Rect(tamanho_atual[0] - tam_btn - 10, tamanho_atual[1] - tam_btn - 10, tam_btn, tam_btn)
        pygame.draw.rect(ecra, (50, 70, 90), rect_toggle, border_radius=8)
        pygame.draw.rect(ecra, (255, 200, 50) if consola_visivel else (150, 150, 150), rect_toggle, 2, border_radius=8)
        
        cx_btn, cy_btn = rect_toggle.centerx, rect_toggle.centery
        s_btn = tam_btn * 0.2
        if consola_visivel:
            pt1, pt2, pt3 = (cx_btn - s_btn, cy_btn - s_btn/2), (cx_btn + s_btn, cy_btn - s_btn/2), (cx_btn, cy_btn + s_btn)
        else:
            pt1, pt2, pt3 = (cx_btn - s_btn, cy_btn + s_btn/2), (cx_btn + s_btn, cy_btn + s_btn/2), (cx_btn, cy_btn - s_btn/2)
        pygame.draw.polygon(ecra, (255, 255, 255), [pt1, pt2, pt3])

        # Caixa de Propriedades da Via
        if via_selecionada and via_selecionada in centros_vias:
            cx, cy = centros_vias[via_selecionada]
            larg_caixa, alt_caixa = escalar_valor(180, escala_global), escalar_valor(120, escala_global)
            cx_caixa = min(cx, tamanho_atual[0] - larg_caixa)
            cy_caixa = min(cy, tamanho_atual[1] - alt_caixa)
            
            rect_caixa = pygame.Rect(cx_caixa, cy_caixa, larg_caixa, alt_caixa)
            pygame.draw.rect(ecra, (40, 50, 60), rect_caixa)
            pygame.draw.rect(ecra, (255, 200, 50), rect_caixa, 2)
            
            ecra.blit(fonte_pequena.render(f"V{via_selecionada} | Configurações", True, (255, 255, 255)), (cx_caixa + escalar_valor(10, escala_global), cy_caixa + escalar_valor(10, escala_global)))
            
            if via_selecionada in vias_entrada:
                ecra.blit(fonte_pequena.render("RTG:", True, (50, 150, 255)), (cx_caixa + escalar_valor(10, escala_global), cy_caixa + escalar_valor(40, escala_global)))
                
                rect_input_rtg = pygame.Rect(cx_caixa + escalar_valor(50, escala_global), cy_caixa + escalar_valor(35, escala_global), escalar_valor(80, escala_global), escalar_valor(25, escala_global))
                pygame.draw.rect(ecra, (20, 25, 30), rect_input_rtg)
                pygame.draw.rect(ecra, (50, 150, 255), rect_input_rtg, 1)
                
                ecra.blit(fonte_pequena.render(texto_rtg_via + "_", True, (255, 255, 255)), (cx_caixa + escalar_valor(55, escala_global), cy_caixa + escalar_valor(40, escala_global)))
            else:
                ecra.blit(fonte_pequena.render("S/ RTG (Via Interna/Saída)", True, (150, 150, 150)), (cx_caixa + escalar_valor(10, escala_global), cy_caixa + escalar_valor(40, escala_global)))
            
            btn_auto = pygame.Rect(cx_caixa + escalar_valor(10, escala_global), cy_caixa + escalar_valor(75, escala_global), escalar_valor(50, escala_global), escalar_valor(30, escala_global))
            pygame.draw.rect(ecra, (100, 100, 100), btn_auto)
            ecra.blit(fonte_pequena.render("AUTO", True, (255, 255, 255)), (cx_caixa + escalar_valor(15, escala_global), cy_caixa + escalar_valor(82, escala_global)))

            btn_red = pygame.Rect(cx_caixa + escalar_valor(65, escala_global), cy_caixa + escalar_valor(75, escala_global), escalar_valor(45, escala_global), escalar_valor(30, escala_global))
            pygame.draw.rect(ecra, (200, 50, 50), btn_red)
            ecra.blit(fonte_pequena.render("RED", True, (255, 255, 255)), (cx_caixa + escalar_valor(72, escala_global), cy_caixa + escalar_valor(82, escala_global)))

            btn_green = pygame.Rect(cx_caixa + escalar_valor(115, escala_global), cy_caixa + escalar_valor(75, escala_global), escalar_valor(55, escala_global), escalar_valor(30, escala_global))
            pygame.draw.rect(ecra, (50, 200, 50), btn_green)
            ecra.blit(fonte_pequena.render("GREEN", True, (255, 255, 255)), (cx_caixa + escalar_valor(118, escala_global), cy_caixa + escalar_valor(82, escala_global)))

        if 'menu_algoritmos' in locals(): menu_algoritmos.desenhar(ecra)
        if 'menu_mapas' in locals(): menu_mapas.desenhar(ecra)

        # Popup Confirmação de Algoritmo
        if confirmacao_algoritmo["ativo"]:
            if agora - confirmacao_algoritmo["tempo"] < 3.0:
                cw, ch = escalar_valor(600, escala_global), escalar_valor(100, escala_global)
                overlay = pygame.Surface(tamanho_atual); overlay.set_alpha(100); overlay.fill((0,0,0)); ecra.blit(overlay, (0,0))
                pygame.draw.rect(ecra, (40, 60, 80), ((tamanho_atual[0]-cw)//2, (tamanho_atual[1]-ch)//2, cw, ch))
                pygame.draw.rect(ecra, (100, 200, 100), ((tamanho_atual[0]-cw)//2, (tamanho_atual[1]-ch)//2, cw, ch), 3)
                txt_sucesso = fonte_grande.render("A enviar alteração de Algoritmo...", True, (100, 200, 100))
                ecra.blit(txt_sucesso, txt_sucesso.get_rect(center=(tamanho_atual[0]//2, tamanho_atual[1]//2)))
            else: confirmacao_algoritmo["ativo"] = False

        pygame.display.flip()
        relogio.tick(30)

if __name__ == "__main__":
    iniciar_dashboard()