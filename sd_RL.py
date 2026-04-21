import asyncio
import random
import json
import os
import hashlib

class SistemaDecisaoRL:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"

        # --- GERAR ASSINATURA ÚNICA DO MAPA ---
        map_str = "CR:" + ",".join(str(c['id']) for c in config.get('crossroads', []))
        map_str += "|V:" + ",".join(str(r['id']) for r in config.get('roads', []))
        self.map_hash = hashlib.md5(map_str.encode()).hexdigest()[:8]
        
        # Mudei para _v2 para forçar a criar um cérebro novo e ignorar o antigo cego!
        self.q_table_file = f"q_table_mapa_{self.map_hash}.json"
        
        # --- PARÂMETROS DO Q-LEARNING ---
        self.q_table = {}
        self.alpha = 0.1      # Learning Rate 
        self.gamma = 0.9      # Discount Factor
        self.epsilon = 0.2    # Exploration Rate
        
        self.precisa_treino = True 
        self.carregar_cerebro()
        
        self.last_state = {}
        self.last_action = {}
        
        # NOVIDADE: Agora cada cruzamento vigia apenas os seus próprios carros!
        self.last_local_count = {c['id']: 0 for c in config['crossroads']}

        self.crossroads = {}
        for c in config['crossroads']:
            self.crossroads[c['id']] = {
                'eixo_ativo': 2, 
                'cor_eixo': 2,   
                'tempo_restante': 15
            }

    def carregar_cerebro(self):
        if os.path.exists(self.q_table_file):
            try:
                with open(self.q_table_file, 'r') as f:
                    q_table_str_keys = json.load(f)
                    self.q_table = {int(k): v for k, v in q_table_str_keys.items()}
                print(f"[SD-RL 2.0] Cérebro carregado: {self.q_table_file} ({len(self.q_table)} estados)")
                self.precisa_treino = False
                self.epsilon = 0.05 
            except Exception as e:
                print(f"[SD-RL 2.0] Erro ao ler cérebro: {e}. Vai treinar de novo.")
        else:
            print(f"[SD-RL 2.0] Novo modelo detetado. Vai treinar de raiz.")

    def guardar_cerebro(self):
        try:
            with open(self.q_table_file, 'w') as f:
                json.dump(self.q_table, f)
            print(f"[SD-RL 2.0] Cérebro gravado com sucesso.")
        except Exception as e:
            pass

    def get_local_cars(self, cr_id):
        """NOVIDADE: Conta APENAS os carros num cruzamento específico."""
        total = 0
        for tl in self.cfg['trafficLights']:
            if tl.get('crID') == cr_id or tl.get('tlCrossroadID') == cr_id:
                rid = tl['roadIndex']
                total += self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
        return total

    def get_state(self, cr_id, eixo_ativo):
        """NOVIDADE: A IA agora vê as duas ruas (Verde e Vermelho) ao mesmo tempo!"""
        carros_verde = 0
        carros_vermelho = 0
        
        for tl in self.cfg['trafficLights']:
            if tl.get('crID') == cr_id or tl.get('tlCrossroadID') == cr_id:
                rid = tl['roadIndex']
                qtd = self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
                if tl['axis'] == eixo_ativo:
                    carros_verde += qtd
                else:
                    carros_vermelho += qtd
                    
        def discretize(qtd):
            if qtd < 10: return 0  # Vazio
            if qtd < 25: return 1  # Normal
            if qtd < 45: return 2  # Cheio
            return 3               # Crítico / Gridlock iminente!
            
        # ATENÇÃO: Se usares a Opção B, tens de mudar a linha do return no final do get_state!
        # Como agora tens 4 níveis (0, 1, 2, 3), multiplicas por 4 em vez de 3:
        return discretize(carros_verde) * 4 + discretize(carros_vermelho)

    async def start(self):
        print("[SD-RL 2.0] Inicializado com Visão 360º e Recompensa Local.")

    async def update(self, current_step=None, fast_forward_step=None):
        step = current_step if current_step is not None else fast_forward_step
        if step is None: step = 0.5
        
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        acoes_possiveis = [15, 30, 45]

        for cr_id, cr in self.crossroads.items():
            cr['tempo_restante'] -= step
            
            if cr['tempo_restante'] <= 0:
                if cr['cor_eixo'] == 2: # Verde -> Amarelo
                    cr['cor_eixo'] = 3
                    cr['tempo_restante'] = yellow_time
                
                elif cr['cor_eixo'] == 3: # Amarelo -> Decisão
                    cr['cor_eixo'] = 2
                    cr['eixo_ativo'] = 1 if cr['eixo_ativo'] == 2 else 2
                    
                    # --- NOVIDADE: CÁLCULO DA RECOMPENSA (LOCAL E JUSTA) ---
                    carros_atuais = self.get_local_cars(cr_id)
                    reward = self.last_local_count[cr_id] - carros_atuais 
                    self.last_local_count[cr_id] = carros_atuais
                    
                    estado_atual = self.get_state(cr_id, cr['eixo_ativo'])
                    
                    if estado_atual not in self.q_table:
                        self.q_table[estado_atual] = [0.0, 0.0, 0.0]

                    if cr_id in self.last_state:
                        s_ant = self.last_state[cr_id]
                        a_ant = self.last_action[cr_id]
                        max_futuro = max(self.q_table[estado_atual])
                        self.q_table[s_ant][a_ant] += self.alpha * (reward + self.gamma * max_futuro - self.q_table[s_ant][a_ant])

                    sorteio = random.uniform(0, 1)
                    if sorteio < self.epsilon:
                        acao_idx = random.randint(0, 2)
                        tipo_log = "EXPLORAÇÃO"
                    else:
                        acao_idx = self.q_table[estado_atual].index(max(self.q_table[estado_atual]))
                        tipo_log = "INTELIGENTE"

                    tempo_verde = acoes_possiveis[acao_idx]
                    cr['tempo_restante'] = tempo_verde
                    
                    self.last_state[cr_id] = estado_atual
                    self.last_action[cr_id] = acao_idx
                    
                    if not fast_forward_step: 
                        print(f"[RL] Cruzamento {cr_id} | Estado {estado_atual} | Decisão: {tipo_log} -> {tempo_verde}s")

        for tl in self.cfg['trafficLights']:
            rid = tl['roadIndex']
            cr = self.crossroads[tl['crID']] 
            if tl['axis'] == cr['eixo_ativo']:
                self.mib[f"{self.base}.4.1.3.{rid}"] = cr['cor_eixo']
                self.mib[f"{self.base}.4.1.4.{rid}"] = max(0, int(cr['tempo_restante']))
            else:
                self.mib[f"{self.base}.4.1.3.{rid}"] = 1 # Red
                self.mib[f"{self.base}.4.1.4.{rid}"] = 0