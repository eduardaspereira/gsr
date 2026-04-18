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
        # Lê os cruzamentos e vias para perceber a topologia
        map_str = "CR:" + ",".join(str(c['id']) for c in config.get('crossroads', []))
        map_str += "|V:" + ",".join(str(r['id']) for r in config.get('roads', []))
        # Gera um código curto (hash) baseado na topologia
        self.map_hash = hashlib.md5(map_str.encode()).hexdigest()[:8]
        self.q_table_file = f"q_table_mapa_{self.map_hash}.json"
        
        # --- PARÂMETROS DO Q-LEARNING ---
        self.q_table = {}
        self.alpha = 0.1      # Learning Rate (Taxa de aprendizagem)
        self.gamma = 0.9      # Discount Factor (Valorização de recompensas futuras)
        self.epsilon = 0.2    # Exploration Rate (Probabilidade de exploração)
        
        self.precisa_treino = True # Avisa o sc.py se precisa de treinar
        
        # Tenta carregar cérebro se já existir para este mapa específico
        self.carregar_cerebro()
        
        self.last_state = {}
        self.last_action = {}
        self.last_vehicle_count = 0

        self.crossroads = {}
        for c in config['crossroads']:
            self.crossroads[c['id']] = {
                'eixo_ativo': 2, 
                'cor_eixo': 2,   
                'tempo_restante': 15
            }

    def carregar_cerebro(self):
        """Verifica se já existe um cérebro gravado para a topologia atual."""
        if os.path.exists(self.q_table_file):
            try:
                with open(self.q_table_file, 'r') as f:
                    # JSON guarda as chaves como strings. Temos de as passar a inteiros (estados)
                    q_table_str_keys = json.load(f)
                    self.q_table = {int(k): v for k, v in q_table_str_keys.items()}
                    
                print(f"[SD-RL] Cérebro carregado: {self.q_table_file} ({len(self.q_table)} estados)")
                self.precisa_treino = False
                self.epsilon = 0.05 # Corta a exploração porque já é um perito
            except Exception as e:
                print(f"[SD-RL] Erro ao ler cérebro: {e}. O modelo vai ser treinado de novo.")
        else:
            print(f"[SD-RL] Mapa novo detetado ({self.map_hash}). Vai treinar um cérebro de raiz.")

    def guardar_cerebro(self):
        """Guarda o conhecimento adquirido num ficheiro."""
        try:
            with open(self.q_table_file, 'w') as f:
                json.dump(self.q_table, f)
            print(f"[SD-RL] Cérebro gravado com sucesso em: {self.q_table_file}")
        except Exception as e:
            print(f"[SD-RL] Erro ao gravar cérebro: {e}")

    def get_state(self, cr_id, eixo_ativo):
        """Discretiza o estado: 0 (Vazio), 1 (Médio), 2 (Cheio)"""
        total_carros = 0
        vias = [tl['roadIndex'] for tl in self.cfg['trafficLights'] 
                if (tl.get('crID') == cr_id or tl.get('tlCrossroadID') == cr_id) 
                and tl['axis'] == eixo_ativo]
        
        for rid in vias:
            total_carros += self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
            
        if total_carros < 5: return 0
        if total_carros < 15: return 1
        return 2

    def calcular_total_carros_rede(self):
        total = 0
        for r in self.cfg['roads']:
            total += self.mib.get(f"{self.base}.3.1.6.{r['id']}", 0)
        return total

    async def start(self):
        print("[SD-RL] Módulo Q-Learning inicializado.")

    async def update(self, current_step=None, fast_forward_step=None):
        step = current_step if current_step is not None else fast_forward_step
        if step is None: step = 0.5
        
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        acoes_possiveis = [15, 30, 45] # Opções de tempo de verde

        # 1. CÁLCULO DA RECOMPENSA (Variação de carros na rede)
        current_count = self.calcular_total_carros_rede()
        reward = self.last_vehicle_count - current_count 
        self.last_vehicle_count = current_count

        for cr_id, cr in self.crossroads.items():
            cr['tempo_restante'] -= step
            
            if cr['tempo_restante'] <= 0:
                if cr['cor_eixo'] == 2: # Verde -> Amarelo
                    cr['cor_eixo'] = 3
                    cr['tempo_restante'] = yellow_time
                
                elif cr['cor_eixo'] == 3: # Amarelo -> Decisão do novo Verde
                    cr['cor_eixo'] = 2
                    cr['eixo_ativo'] = 1 if cr['eixo_ativo'] == 2 else 2
                    
                    # --- FASE DE APRENDIZAGEM (Bellman) ---
                    estado_atual = self.get_state(cr_id, cr['eixo_ativo'])
                    
                    if estado_atual not in self.q_table:
                        self.q_table[estado_atual] = [0.0, 0.0, 0.0]

                    if cr_id in self.last_state:
                        s_ant = self.last_state[cr_id]
                        a_ant = self.last_action[cr_id]
                        # Atualiza o conhecimento baseado na recompensa obtida
                        max_futuro = max(self.q_table[estado_atual])
                        self.q_table[s_ant][a_ant] += self.alpha * (reward + self.gamma * max_futuro - self.q_table[s_ant][a_ant])

                    # --- ESCOLHA DA AÇÃO (Epsilon-Greedy) ---
                    sorteio = random.uniform(0, 1)
                    if sorteio < self.epsilon:
                        # EXPLORAÇÃO: Tenta algo ao calhas para aprender
                        acao_idx = random.randint(0, 2)
                        tipo_log = "EXPLORAÇÃO (Sorteio)"
                    else:
                        # EXPLORAÇÃO DO CONHECIMENTO: Usa a melhor opção da Q-Table
                        acao_idx = self.q_table[estado_atual].index(max(self.q_table[estado_atual]))
                        tipo_log = "INTELIGENTE (Q-Table)"

                    tempo_verde = acoes_possiveis[acao_idx]
                    cr['tempo_restante'] = tempo_verde
                    
                    self.last_state[cr_id] = estado_atual
                    self.last_action[cr_id] = acao_idx
                    
                    # Log apenas durante a simulação real (não no treino rápido)
                    if not fast_forward_step: 
                        print(f"[RL] Cruzamento {cr_id} | Estado {estado_atual} | Decisão: {tipo_log} -> {tempo_verde}s")

        # Refletir na MIB (O que a Consola Gráfica vai ler)
        for tl in self.cfg['trafficLights']:
            rid = tl['roadIndex']
            cr = self.crossroads[tl['crID']] 
            if tl['axis'] == cr['eixo_ativo']:
                self.mib[f"{self.base}.4.1.3.{rid}"] = cr['cor_eixo']
                self.mib[f"{self.base}.4.1.4.{rid}"] = max(0, int(cr['tempo_restante']))
            else:
                self.mib[f"{self.base}.4.1.3.{rid}"] = 1 # Red
                self.mib[f"{self.base}.4.1.4.{rid}"] = 0