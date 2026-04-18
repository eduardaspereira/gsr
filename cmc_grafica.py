import base64
import getpass
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

print("=== INICIALIZAÇÃO SEGURA ===")
password = getpass.getpass("Introduz a password mestra para destrancar a chave: ").encode()

salt = b'GSR_UM_2026'
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
chave_cofre = base64.urlsafe_b64encode(kdf.derive(password))
cofre_cipher = Fernet(chave_cofre)

try:
    with open("seguranca.key", "rb") as f:
        chave_encriptada = f.read()
    CHAVE_SECRETA = cofre_cipher.decrypt(chave_encriptada)
    cipher = Fernet(CHAVE_SECRETA)
    print("Chave carregada com sucesso!")
except Exception:
    print("ERRO: Password incorreta ou ficheiro 'seguranca.key' em falta!")
    exit(1)

OID_TUNEL = "1.3.6.1.3.2026.99.1.0"


import pygame
import sys
import asyncio
import threading
import json
import time 
import networkx as nx
import math, re
from pysnmp.hlapi.asyncio import *

from pysnmp.entity import engine as snmp_engine_mod, config as snmp_config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv

# =====================================================================
# FUNÇÃO DE GERAÇÃO DINÂMICA DA TOPOLOGIA
# =====================================================================

def gerar_topologia_dinamica(cfg, resolucao_base=(900, 700), padding=120):
    crossroads = cfg.get('crossroads', [])
    num_crossroads = len(crossroads)
    
    grid_cols = 4 if num_crossroads == 8 else math.ceil(math.sqrt(num_crossroads))
    grid_rows = math.ceil(num_crossroads / grid_cols)
    
    crossroad_pos_norm = {} 
    for idx, cr in enumerate(crossroads):
        row = idx // grid_cols
        col = idx % grid_cols
        x = -0.6 + (col / max(1, grid_cols - 1)) * 1.2 if grid_cols > 1 else 0
        y = -0.6 + (row / max(1, grid_rows - 1)) * 1.2 if grid_rows > 1 else 0
        crossroad_pos_norm[cr['id']] = (x, y)
    
    via_graph = {} 
    via_details = {} 
    
    for road in cfg.get('roads', []):
        road_id = road['id']
        road_type = road['type']
        road_name = road.get('name', '')
        via_details[road_id] = (road_name, road_type)
        
        if road_type == 1: 
            match = re.search(r'C(\d+)->C(\d+)', road_name)
            if match:
                src_cr, dst_cr = int(match.group(1)), int(match.group(2))
                via_graph[road_id] = (f"C{src_cr}", f"C{dst_cr}")
        elif road_type == 3: 
            match = re.search(r'\(->C(\d+)\)', road_name)
            if match:
                dst_cr = int(match.group(1))
                via_graph[road_id] = (f"SRC_{road_id}", f"C{dst_cr}")
        elif road_type == 2: 
            match = re.search(r'\(C(\d+)->\)', road_name)
            if match:
                src_cr = int(match.group(1))
                via_graph[road_id] = (f"C{src_cr}", f"SINK_{road_id}")
    
    nos_pos_norm = {} 
    for cr_id, pos in crossroad_pos_norm.items():
        nos_pos_norm[f"C{cr_id}"] = pos
    
    for via_id, (nó_src, nó_dest) in via_graph.items():
        road_name, road_type = via_details[via_id]
        if road_type == 3:
            match = re.search(r'\(->C(\d+)\)', road_name)
            if match:
                dst_cr = int(match.group(1))
                if dst_cr in crossroad_pos_norm:
                    x_cr, y_cr = crossroad_pos_norm[dst_cr]
                    if "Norte" in road_name: x_f, y_f = x_cr, y_cr - 0.25
                    elif "Sul" in road_name: x_f, y_f = x_cr, y_cr + 0.25
                    elif "Oeste" in road_name: x_f, y_f = x_cr - 0.25, y_cr
                    elif "Este" in road_name: x_f, y_f = x_cr + 0.25, y_cr
                    else: x_f, y_f = x_cr - 0.3, y_cr
                    nos_pos_norm[nó_src] = (x_f, y_f)
        elif road_type == 2:
            match = re.search(r'\(C(\d+)->\)', road_name)
            if match:
                src_cr = int(match.group(1))
                if src_cr in crossroad_pos_norm:
                    x_cr, y_cr = crossroad_pos_norm[src_cr]
                    if "Norte" in road_name: x_f, y_f = x_cr, y_cr - 0.25
                    elif "Sul" in road_name: x_f, y_f = x_cr, y_cr + 0.25
                    elif "Oeste" in road_name: x_f, y_f = x_cr - 0.25, y_cr
                    elif "Este" in road_name: x_f, y_f = x_cr + 0.25, y_cr
                    else: x_f, y_f = x_cr + 0.3, y_cr
                    nos_pos_norm[nó_dest] = (x_f, y_f)
    
    width, height = resolucao_base
    nos_pos_px = {} 
    xs = [p[0] for p in nos_pos_norm.values()]; ys = [p[1] for p in nos_pos_norm.values()]
    min_x, max_x = min(xs) if xs else -1, max(xs) if xs else 1
    min_y, max_y = min(ys) if ys else -1, max(ys) if ys else 1
    range_x = max_x - min_x if max_x > min_x else 1; range_y = max_y - min_y if max_y > min_y else 1
    
    area_w, area_h = width - 2 * padding, height - 2 * padding
    for nó, (xn, yn) in nos_pos_norm.items():
        x_px = padding + ((xn - min_x) / range_x) * area_w
        y_px = padding + ((yn - min_y) / range_y) * area_h
        nos_pos_px[nó] = (int(x_px), int(y_px))
    
    arestas_px = {}
    for vid, (n_src, n_dst) in via_graph.items():
        if n_src in nos_pos_px and n_dst in nos_pos_px:
            arestas_px[vid] = (nos_pos_px[n_src], nos_pos_px[n_dst])
    
    return nos_pos_px, arestas_px

# =====================================================================
# CLASSE DE DROPDOWN LIST
# =====================================================================
class DropdownList:
    def __init__(self, x, y, width, height, options, fonte_pequena, selected_idx=3):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.options = options
        self.is_open = False
        self.selected_idx = selected_idx
        self.fonte_pequena = fonte_pequena
    
    def draw(self, surface):
        cor_caixa = (50, 70, 90) if not self.is_open else (70, 90, 110)
        pygame.draw.rect(surface, cor_caixa, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(surface, (150, 150, 150), (self.x, self.y, self.width, self.height), 2)
        
        txt = self.options[self.selected_idx][1]
        txt_s = self.fonte_pequena.render(txt, True, (255, 255, 255))
        surface.blit(txt_s, (self.x + 10, self.y + 8))
        
        cx = self.x + self.width - 15
        cy = self.y + self.height / 2
        s = self.height * 0.15
        if self.is_open:
            p1, p2, p3 = (cx - s, cy - s/2), (cx + s, cy - s/2), (cx, cy + s)
        else:
            p1, p2, p3 = (cx - s/2, cy - s), (cx - s/2, cy + s), (cx + s, cy)
        pygame.draw.polygon(surface, (200, 200, 200), [p1, p2, p3])
        
        if self.is_open:
            y_off = self.y + self.height
            for idx, (_, nome) in enumerate(self.options):
                cor_bg = (100, 120, 140) if idx == self.selected_idx else (60, 80, 100)
                pygame.draw.rect(surface, cor_bg, (self.x, y_off, self.width, self.height))
                pygame.draw.rect(surface, (150, 150, 150), (self.x, y_off, self.width, self.height), 1)
                surface.blit(self.fonte_pequena.render(nome, True, (255, 255, 255)), (self.x + 10, y_off + 8))
                y_off += self.height
    
    def handle_click(self, mx, my):
        if self.x <= mx <= self.x + self.width and self.y <= my <= self.y + self.height:
            self.is_open = not self.is_open
            return None
        if self.is_open:
            y_off = self.y + self.height
            for idx, (vid, _) in enumerate(self.options):
                if self.x <= mx <= self.x + self.width and y_off <= my <= y_off + self.height:
                    self.selected_idx = idx
                    self.is_open = False
                    return vid
                y_off += self.height
        return None

# =====================================================================
# SNMP E MIB (VARIÁVEIS GLOBAIS)
# =====================================================================
cfg = {}
estado_semaforos = {}
estado_filas = {}
estado_rtg = {}
estado_override = {}
estado_links = {}

with open('config2.json', 'r') as f:
    cfg = json.load(f)

estado_semaforos.update({tl['roadIndex']: 1 for tl in cfg['trafficLights']})
estado_filas.update({r['id']: r.get('initialCount', 0) for r in cfg['roads']})
estado_rtg.update({r['id']: r.get('rtg', 0) for r in cfg['roads'] if r['type'] == 3})
estado_override.update({tl['roadIndex']: 0 for tl in cfg['trafficLights']})
estado_links.update({f"{l['src']}.{l['dest']}": 0 for l in cfg.get('links', [])})

snmp_loop = None 
alerta_trap = {"ativo": False, "via": 0, "carros": 0, "expira": 0}

import builtins
builtins._tempo_execucao_snmp = 0
builtins._algo_id_snmp = 4  
confirmacao_algoritmo = {"ativo": False, "tempo": 0}

def processar_trap(snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
    global alerta_trap
    via, carros = 0, 0
    for name, val in varBinds:
        if "2026.1.1.1" in str(name): via = int(val)
        if "2026.1.1.2" in str(name): carros = int(val)
    if via > 0:
        alerta_trap = {"ativo": True, "via": via, "carros": carros, "expira": time.time() + 6.0}

async def servidor_traps():
    engine = snmp_engine_mod.SnmpEngine()
    snmp_config.addTransport(engine, udp.domainName, udp.UdpTransport().openServerMode(('127.0.0.1', 16216)))
    snmp_config.addV1System(engine, 'my-area', 'public')
    snmp_config.addVacmUser(engine, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6), (1, 3, 6))
    ntfrcv.NotificationReceiver(engine, processar_trap)
    while True: await asyncio.sleep(3600)

async def obter_dados_snmp():
    engine = SnmpEngine()
    while True:
        try:
            payload = {"comando": "PULL_STATE"}
            payload_encriptado = cipher.encrypt(json.dumps(payload).encode('utf-8'))

            errorInd, errorStat, errorIdx, varBinds = await setCmd(
                engine, CommunityData('public', mpModel=1),
                UdpTransportTarget(('127.0.0.1', 16161), timeout=1, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity(OID_TUNEL), OctetString(payload_encriptado))
            )

            if not errorInd and not errorStat:
                for name, val in varBinds:
                    if str(name) == OID_TUNEL:
                        # Desencriptar a resposta gorda enviada pelo SC
                        resposta_json = cipher.decrypt(bytes(val)).decode('utf-8')
                        dados = json.loads(resposta_json)

                        # Atualizar as variáveis globais da interface gráfica
                        builtins._tempo_execucao_snmp = dados.get("tempo", 0)
                        builtins._algo_id_snmp = dados.get("algo_id", 4)
                        
                        # Atualizar dicionários convertendo as chaves de string para int onde necessário
                        for k, v in dados.get("filas", {}).items(): estado_filas[int(k)] = v
                        for k, v in dados.get("semaforos", {}).items(): estado_semaforos[int(k)] = v
                        for k, v in dados.get("rtgs", {}).items(): estado_rtg[int(k)] = v
                        for k, v in dados.get("overrides", {}).items(): estado_override[int(k)] = v
                        for k, v in dados.get("links", {}).items(): estado_links[k] = v

        except Exception as e:
            pass 
        
        await asyncio.sleep(3)

# =====================================================================
# FUNÇÕES DE ENVIO (A USAR O TÚNEL SEGURO JSON)
# =====================================================================
async def enviar_algoritmo_snmp(algo_id):
    payload = {"comando": "SET_ALG", "alg_id": algo_id}
    await enviar_comando_tunel('127.0.0.1', 16161, 'public', payload)

async def enviar_novo_rtg_snmp(via, novo_rtg):
    payload = {"comando": "SET_RTG", "via": via, "valor": novo_rtg}
    await enviar_comando_tunel('127.0.0.1', 16161, 'public', payload)

async def enviar_override_snmp(via, modo):
    payload = {"comando": "SET_OVERRIDE", "via": via, "modo": modo}
    await enviar_comando_tunel('127.0.0.1', 16161, 'public', payload)
def iniciar_thread_snmp():
    global snmp_loop
    snmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(snmp_loop)
    snmp_loop.run_until_complete(asyncio.gather(obter_dados_snmp(), servidor_traps()))

# =====================================================================
# 3. INTERFACE GRÁFICA
# =====================================================================
def desenhar_grafo():
    global confirmacao_algoritmo, cfg, nos_base, arestas_base
    pygame.init()
    ecra = pygame.display.set_mode((900, 700), pygame.RESIZABLE)
    pygame.display.set_caption("Dashboard Topológico - Filas de Espera")
    relogio = pygame.time.Clock()
    
    RESOLUCAO_BASE = (900, 700)
    tamanho_atual = RESOLUCAO_BASE
    nos_base, arestas_base = gerar_topologia_dinamica(cfg, RESOLUCAO_BASE)
    
    def escalar_valor(v, e): return max(1, int(v * e))

    def desenhar_seta(surface, p_o, p_d, cor, tam):
        mx, my = p_o[0] + (p_d[0] - p_o[0]) * 0.25, p_o[1] + (p_d[1] - p_o[1]) * 0.25
        dx, dy = p_d[0] - p_o[0], p_d[1] - p_o[1]
        ang = math.atan2(dy, dx)
        bx, by = int(mx - tam * math.cos(ang)), int(my - tam * math.sin(ang))
        pygame.draw.line(surface, cor, (bx, by), (int(mx), int(my)), 3)
        al, cl = math.pi / 5, tam * 0.8
        p1 = (int(mx - cl * math.cos(ang + al)), int(my - cl * math.sin(ang + al)))
        p2 = (int(mx - cl * math.cos(ang - al)), int(my - cl * math.sin(ang - al)))
        pygame.draw.line(surface, cor, (int(mx), int(my)), p1, 4)
        pygame.draw.line(surface, cor, (int(mx), int(my)), p2, 4)

    texto_input = ""
    tempo_anterior, escoados_anterior, vazao_atual = time.time(), 0, 0.0
    algo_anterior_gui = 4 
    
    opcoes_algos = [(1, "ROUND_ROBIN"), (2, "HEURISTICA"), (3, "RL"), (4, "BACKPRESSURE")]
    opcoes_mapas = [(0, "Mapa 1 (config)"), (1, "Mapa 2 (config2)"), (2, "Mapa 3 (config3)")]
    ficheiros_mapas = ["config.json", "config2.json", "config3.json"]

    via_selecionada = None
    texto_rtg_via = ""
    centros_vias = {} 
    
    cmc_visivel = False

    while True:
        agora = time.time()
        ex, ey = tamanho_atual[0] / RESOLUCAO_BASE[0], tamanho_atual[1] / RESOLUCAO_BASE[1]
        eg = min(ex, ey)
        
        v_out = [str(r['id']) for r in cfg['roads'] if r['type'] == 2]
        v_in = [r['id'] for r in cfg['roads'] if r['type'] == 3]
        total_escoados = sum(val for key, val in estado_links.items() if any(key.endswith(f".{s}") for s in v_out))
        oc_media = sum(estado_filas.get(v, 0) for v in [r['id'] for r in cfg['roads'] if r['type'] == 1]) / max(1, len([r['id'] for r in cfg['roads'] if r['type'] == 1]))
        
        max_f, max_v = 0, 0
        for v in v_in + [r['id'] for r in cfg['roads'] if r['type'] == 1]:
            if estado_filas.get(v, 0) > max_f: max_f, max_v = estado_filas.get(v, 0), v

        algo_snmp = getattr(builtins, '_algo_id_snmp', 4)
        if algo_snmp != algo_anterior_gui:
            vazao_atual = 0.0
            escoados_anterior = total_escoados
            tempo_anterior = agora
            algo_anterior_gui = algo_snmp

        if agora - tempo_anterior >= 15.0:
            vazao_atual = ((total_escoados - escoados_anterior) / (agora - tempo_anterior)) * 60.0
            tempo_anterior, escoados_anterior = agora, total_escoados

        # --- TRATAMENTO DE EVENTOS (TECLADO E RATO) ---
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            elif ev.type == pygame.VIDEORESIZE: tamanho_atual = ev.size
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx_mouse, my_mouse = ev.pos
                
                btn_t_size = max(1, int(40 * eg))
                btn_toggle_rect = pygame.Rect(tamanho_atual[0] - btn_t_size - 10, tamanho_atual[1] - btn_t_size - 10, btn_t_size, btn_t_size)
                
                if btn_toggle_rect.collidepoint(mx_mouse, my_mouse):
                    cmc_visivel = not cmc_visivel
                    continue
                
                if 'dropdown_mapa' in locals():
                    res_mapa = dropdown_mapa.handle_click(mx_mouse, my_mouse)
                    if res_mapa is not None:
                        try:
                            with open(ficheiros_mapas[res_mapa], 'r') as f:
                                cfg = json.load(f)
                            
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
                            
                            nos_base, arestas_base = gerar_topologia_dinamica(cfg, RESOLUCAO_BASE)
                            via_selecionada = None
                            dropdown_mapa.selected_idx = res_mapa
                        except Exception as e:
                            print(f"[ERRO] Falha ao carregar mapa: {e}")
                        continue
                
                if 'dropdown' in locals():
                    res = dropdown.handle_click(mx_mouse, my_mouse)
                    if res:
                        confirmacao_algoritmo = {"ativo": True, "tempo": time.time()}
                        asyncio.run_coroutine_threadsafe(enviar_algoritmo_snmp(res), snmp_loop)
                        continue

                if via_selecionada and via_selecionada in centros_vias:
                    cx, cy = centros_vias[via_selecionada]
                    box_w, box_h = escalar_valor(180, eg), escalar_valor(120, eg)
                    cx_box = min(cx, tamanho_atual[0] - box_w)
                    cy_box = min(cy, tamanho_atual[1] - box_h)
                    
                    caixa_rect = pygame.Rect(cx_box, cy_box, box_w, box_h)
                    
                    if caixa_rect.collidepoint(mx_mouse, my_mouse):
                        btn_auto = pygame.Rect(cx_box + escalar_valor(10, eg), cy_box + escalar_valor(75, eg), escalar_valor(50, eg), escalar_valor(30, eg))
                        btn_red = pygame.Rect(cx_box + escalar_valor(65, eg), cy_box + escalar_valor(75, eg), escalar_valor(45, eg), escalar_valor(30, eg))
                        btn_green = pygame.Rect(cx_box + escalar_valor(115, eg), cy_box + escalar_valor(75, eg), escalar_valor(55, eg), escalar_valor(30, eg))
                        
                        if btn_auto.collidepoint(mx_mouse, my_mouse):
                            asyncio.run_coroutine_threadsafe(enviar_override_snmp(via_selecionada, 0), snmp_loop)
                            via_selecionada = None
                        elif btn_red.collidepoint(mx_mouse, my_mouse):
                            asyncio.run_coroutine_threadsafe(enviar_override_snmp(via_selecionada, 2), snmp_loop)
                            via_selecionada = None
                        elif btn_green.collidepoint(mx_mouse, my_mouse):
                            asyncio.run_coroutine_threadsafe(enviar_override_snmp(via_selecionada, 1), snmp_loop)
                            via_selecionada = None
                    else:
                        via_selecionada = None
                else:
                    for vid, (cx_via, cy_via) in centros_vias.items():
                        if math.hypot(mx_mouse - cx_via, my_mouse - cy_via) < escalar_valor(25, eg):
                            via_selecionada = vid
                            texto_rtg_via = str(estado_rtg.get(vid, ""))
                            break

            elif ev.type == pygame.KEYDOWN:
                if via_selecionada:
                    # Só deixa digitar RTG se for via de entrada
                    if via_selecionada in v_in:
                        if ev.key == pygame.K_BACKSPACE: 
                            texto_rtg_via = texto_rtg_via[:-1]
                        elif ev.key == pygame.K_RETURN:
                            if texto_rtg_via.isdigit():
                                asyncio.run_coroutine_threadsafe(enviar_novo_rtg_snmp(via_selecionada, int(texto_rtg_via)), snmp_loop)
                            via_selecionada = None
                        elif ev.unicode.isdigit(): 
                            texto_rtg_via += ev.unicode
                elif cmc_visivel: 
                    if ev.key == pygame.K_BACKSPACE: texto_input = texto_input[:-1]
                    elif ev.key == pygame.K_RETURN:
                        try:
                            p = texto_input.strip().split(' ')
                            if len(p) == 2 and p[0].upper() == "ALG": asyncio.run_coroutine_threadsafe(enviar_algoritmo_snmp(int(p[1])), snmp_loop)
                            elif len(p) == 2: asyncio.run_coroutine_threadsafe(enviar_novo_rtg_snmp(int(p[0]), int(p[1])), snmp_loop)
                            elif len(p) == 3 and p[0].upper() == 'O': asyncio.run_coroutine_threadsafe(enviar_override_snmp(int(p[1]), int(p[2])), snmp_loop)
                        except: pass
                        texto_input = ""
                    elif ev.unicode.isprintable(): texto_input += ev.unicode

        ecra.fill((30, 35, 40))
        
        f_p = pygame.font.SysFont("Arial", escalar_valor(14, eg), bold=True)
        f_g = pygame.font.SysFont("Courier New", escalar_valor(20, eg), bold=True)
        f_a = pygame.font.SysFont("Arial", escalar_valor(22, eg), bold=True)

        t_snmp = getattr(builtins, '_tempo_execucao_snmp', 0)
        t_fmt = f"{t_snmp // 3600:02d}:{(t_snmp % 3600) // 60:02d}:{t_snmp % 60:02d}"

        margin_x = escalar_valor(20, eg) 
        curr_y = escalar_valor(15, eg)
        
        titulo_s = f_g.render("METRICAS DE REDE - ", True, (255, 255, 255))
        tempo_s = f_g.render(t_fmt, True, (100, 255, 100))
        ecra.blit(titulo_s, (margin_x, curr_y))
        ecra.blit(tempo_s, (margin_x + titulo_s.get_width(), curr_y))
        
        curr_y += escalar_valor(30, eg)
        stats_s = f"Escoados: {total_escoados} v | Vazão: {vazao_atual:.1f} v/min | Ocupação Média: {oc_media:.1f} v/via | Pior Fila: {max_f}v (V{max_v})"
        ecra.blit(f_p.render(stats_s, True, (200, 200, 200)), (margin_x, curr_y))
        
        curr_y += escalar_valor(30, eg)
        
        if 'dropdown' not in locals():
            dropdown = DropdownList(margin_x, curr_y, escalar_valor(180, eg), escalar_valor(35, eg), opcoes_algos, f_p)
        else:
            dropdown.x, dropdown.y = margin_x, curr_y
            dropdown.width, dropdown.height = escalar_valor(180, eg), escalar_valor(35, eg)
            dropdown.fonte_pequena = f_p
        
        if 1 <= algo_snmp <= 4 and not dropdown.is_open:
            dropdown.selected_idx = algo_snmp - 1

        if 'dropdown_mapa' not in locals():
            dropdown_mapa = DropdownList(tamanho_atual[0] - escalar_valor(220, eg), escalar_valor(15, eg), escalar_valor(200, eg), escalar_valor(35, eg), opcoes_mapas, f_p, selected_idx=1)
        else:
            dropdown_mapa.x = tamanho_atual[0] - escalar_valor(220, eg)
            dropdown_mapa.y = escalar_valor(15, eg)
            dropdown_mapa.width = escalar_valor(200, eg)
            dropdown_mapa.height = escalar_valor(35, eg)
            dropdown_mapa.fonte_pequena = f_p

        if alerta_trap["ativo"]:
            if agora < alerta_trap["expira"]:
                if int(agora * 2) % 2 == 0:
                    x_trap = margin_x + escalar_valor(200, eg) 
                    w_trap = tamanho_atual[0] - x_trap - margin_x
                    pygame.draw.rect(ecra, (200, 40, 40), (x_trap, curr_y, w_trap, escalar_valor(35, eg)), border_radius=4)
                    at = f"ALERTA TRAP: Congestionamento na Via {alerta_trap['via']} ({alerta_trap['carros']} v!)"
                    asur = f_a.render(at, True, (255, 255, 255))
                    ecra.blit(asur, asur.get_rect(center=(x_trap + w_trap//2, curr_y + escalar_valor(17, eg))))
            else: alerta_trap["ativo"] = False

        centros_vias.clear() 
        
        for vid, (pb_o, pb_d) in arestas_base.items():
            po, pd = (int(pb_o[0] * ex), int(pb_o[1] * ey)), (int(pb_d[0] * ex), int(pb_d[1] * ey))
            dx, dy = pd[0] - po[0], pd[1] - po[1]
            dist = math.hypot(dx, dy)
            mx_b, my_b = (po[0] + pd[0]) / 2, (po[1] + pd[1]) / 2
            
            if dist > 0:
                nx, ny = -dy / dist, dx / dist
                off = escalar_valor(18, eg)
                po_d, pd_d = (int(po[0] + nx * off), int(po[1] + ny * off)), (int(pd[0] + nx * off), int(pd[1] + ny * off))
                mx, my = int(mx_b + nx * off), int(my_b + ny * off)
            else:
                po_d, pd_d, mx, my = po, pd, int(mx_b), int(my_b)
            
            centros_vias[vid] = (mx, my)
            
            cor = (80, 80, 80)
            if vid in estado_semaforos:
                st = estado_semaforos[vid]
                cor = (200, 50, 50) if st == 1 else (50, 200, 50) if st == 2 else (200, 150, 50)
            
            pygame.draw.line(ecra, cor, po_d, pd_d, escalar_valor(6, eg))
            desenhar_seta(ecra, po_d, pd_d, cor, escalar_valor(20, eg))
            
            c = estado_filas.get(vid, 0)
            
            if estado_override.get(vid, 0) != 0:
                pygame.draw.circle(ecra, (255, 200, 0), (mx, my), escalar_valor(18, eg))
                ecra.blit(f_p.render("[M]", True, (255, 200, 0)), (mx - escalar_valor(10, eg), my - escalar_valor(32, eg)))
            
            pygame.draw.circle(ecra, (200, 100, 0) if c > 15 else (50, 100, 150), (mx, my), escalar_valor(14, eg))
            pygame.draw.circle(ecra, (255, 255, 255), (mx, my), escalar_valor(14, eg), 2)
            ts = f_p.render(str(c), True, (255, 255, 255))
            ecra.blit(ts, ts.get_rect(center=(mx, my)))
            
            tx, ty = (int(mx + nx * escalar_valor(22, eg)), int(my + ny * escalar_valor(22, eg))) if dist > 0 else (mx+15, my+15)
            ecra.blit(f_p.render(f"V{vid}", True, (150, 150, 150)), (tx - 5, ty - 5))

        for nid_s, p_b in nos_base.items():
            pos = (int(p_b[0] * ex), int(p_b[1] * ey))
            if nid_s.startswith('C'):
                r = escalar_valor(25, eg)
                pygame.draw.circle(ecra, (35, 40, 45), pos, r)
                pygame.draw.circle(ecra, (200, 200, 200), pos, r, 3)
                ns = f_g.render(nid_s, True, (255, 255, 255))
                ecra.blit(ns, ns.get_rect(center=pos))

        if cmc_visivel:
            h_c = escalar_valor(110, eg) 
            y_c = tamanho_atual[1] - h_c
            pygame.draw.rect(ecra, (20, 25, 30), (0, y_c, tamanho_atual[0], h_c))
            pygame.draw.line(ecra, (50, 150, 50), (0, y_c), (tamanho_atual[0], y_c), 2)
            
            # MOSTRAR RTGs APENAS DAS VIAS DE ENTRADA A AZUL FORTE
            rtg_s = f"RTGs (Entradas): {' | '.join([f'V{v}={estado_rtg.get(v,0)}' for v in sorted(v_in)])}"
            ecra.blit(f_p.render(rtg_s, True, (50, 150, 255)), (escalar_valor(20, eg), y_c + escalar_valor(15, eg)))
            
            texto_comandos = "O <Via> <0: Auto | 1: Vermelho | 2: Verde>   |   RTG: <via> <valor>   |   ALG <1: RR | 2: Heurística | 3: RL | 4: Back Pressure>"
            ecra.blit(f_p.render(texto_comandos, True, (150, 150, 150)), (escalar_valor(20, eg), y_c + escalar_valor(45, eg)))
            
            ecra.blit(f_g.render(f"CMC> {texto_input}_", True, (255, 200, 50)), (escalar_valor(20, eg), y_c + escalar_valor(75, eg)))

        btn_t_size = max(1, int(40 * eg))
        btn_toggle_rect = pygame.Rect(tamanho_atual[0] - btn_t_size - 10, tamanho_atual[1] - btn_t_size - 10, btn_t_size, btn_t_size)
        pygame.draw.rect(ecra, (50, 70, 90), btn_toggle_rect, border_radius=8)
        pygame.draw.rect(ecra, (255, 200, 50) if cmc_visivel else (150, 150, 150), btn_toggle_rect, 2, border_radius=8)
        
        cx_btn, cy_btn = btn_toggle_rect.centerx, btn_toggle_rect.centery
        s_btn = btn_t_size * 0.2
        if cmc_visivel:
            pt1, pt2, pt3 = (cx_btn - s_btn, cy_btn - s_btn/2), (cx_btn + s_btn, cy_btn - s_btn/2), (cx_btn, cy_btn + s_btn)
        else:
            pt1, pt2, pt3 = (cx_btn - s_btn, cy_btn + s_btn/2), (cx_btn + s_btn, cy_btn + s_btn/2), (cx_btn, cy_btn - s_btn/2)
        pygame.draw.polygon(ecra, (255, 255, 255), [pt1, pt2, pt3])

        if via_selecionada and via_selecionada in centros_vias:
            cx, cy = centros_vias[via_selecionada]
            box_w, box_h = escalar_valor(180, eg), escalar_valor(120, eg)
            cx_box = min(cx, tamanho_atual[0] - box_w)
            cy_box = min(cy, tamanho_atual[1] - box_h)
            
            caixa_rect = pygame.Rect(cx_box, cy_box, box_w, box_h)
            pygame.draw.rect(ecra, (40, 50, 60), caixa_rect)
            pygame.draw.rect(ecra, (255, 200, 50), caixa_rect, 2)
            
            titulo_menu = f_p.render(f"V{via_selecionada} | Configs", True, (255, 255, 255))
            ecra.blit(titulo_menu, (cx_box + escalar_valor(10, eg), cy_box + escalar_valor(10, eg)))
            
            # SÓ MOSTRA O RTG SE FOR VIA DE ENTRADA
            if via_selecionada in v_in:
                lbl_rtg = f_p.render("RTG:", True, (50, 150, 255)) # Azul forte a acompanhar a CMC
                ecra.blit(lbl_rtg, (cx_box + escalar_valor(10, eg), cy_box + escalar_valor(40, eg)))
                
                caixa_input_rtg = pygame.Rect(cx_box + escalar_valor(50, eg), cy_box + escalar_valor(35, eg), escalar_valor(80, eg), escalar_valor(25, eg))
                pygame.draw.rect(ecra, (20, 25, 30), caixa_input_rtg)
                pygame.draw.rect(ecra, (50, 150, 255), caixa_input_rtg, 1) # Borda da caixa de input também a azul
                
                txt_rtg_sur = f_p.render(texto_rtg_via + "_", True, (255, 255, 255))
                ecra.blit(txt_rtg_sur, (cx_box + escalar_valor(55, eg), cy_box + escalar_valor(40, eg)))
            else:
                # Se não for entrada, indica que não permite edição de RTG
                lbl_no_rtg = f_p.render("S/ RTG (Via Interna/Saída)", True, (150, 150, 150))
                ecra.blit(lbl_no_rtg, (cx_box + escalar_valor(10, eg), cy_box + escalar_valor(40, eg)))
            
            btn_auto = pygame.Rect(cx_box + escalar_valor(10, eg), cy_box + escalar_valor(75, eg), escalar_valor(50, eg), escalar_valor(30, eg))
            pygame.draw.rect(ecra, (100, 100, 100), btn_auto)
            ecra.blit(f_p.render("AUTO", True, (255, 255, 255)), (cx_box + escalar_valor(15, eg), cy_box + escalar_valor(82, eg)))

            btn_red = pygame.Rect(cx_box + escalar_valor(65, eg), cy_box + escalar_valor(75, eg), escalar_valor(45, eg), escalar_valor(30, eg))
            pygame.draw.rect(ecra, (200, 50, 50), btn_red)
            ecra.blit(f_p.render("RED", True, (255, 255, 255)), (cx_box + escalar_valor(72, eg), cy_box + escalar_valor(82, eg)))

            btn_green = pygame.Rect(cx_box + escalar_valor(115, eg), cy_box + escalar_valor(75, eg), escalar_valor(55, eg), escalar_valor(30, eg))
            pygame.draw.rect(ecra, (50, 200, 50), btn_green)
            ecra.blit(f_p.render("GREEN", True, (255, 255, 255)), (cx_box + escalar_valor(118, eg), cy_box + escalar_valor(82, eg)))

        if 'dropdown' in locals():
            dropdown.draw(ecra)
            
        if 'dropdown_mapa' in locals():
            dropdown_mapa.draw(ecra)

        if confirmacao_algoritmo["ativo"]:
            if agora - confirmacao_algoritmo["tempo"] < 3.0:
                cw, ch = escalar_valor(600, eg), escalar_valor(100, eg)
                ov = pygame.Surface(tamanho_atual); ov.set_alpha(100); ov.fill((0,0,0)); ecra.blit(ov, (0,0))
                pygame.draw.rect(ecra, (40, 60, 80), ((tamanho_atual[0]-cw)//2, (tamanho_atual[1]-ch)//2, cw, ch))
                pygame.draw.rect(ecra, (100, 200, 100), ((tamanho_atual[0]-cw)//2, (tamanho_atual[1]-ch)//2, cw, ch), 3)
                ms = f_g.render("O sistema irá reiniciar com o novo algoritmo", True, (100, 200, 100))
                ecra.blit(ms, ms.get_rect(center=(tamanho_atual[0]//2, tamanho_atual[1]//2)))
            else: confirmacao_algoritmo["ativo"] = False

        pygame.display.flip()
        relogio.tick(30)

if __name__ == "__main__":
    threading.Thread(target=iniciar_thread_snmp, daemon=True).start()
    desenhar_grafo()