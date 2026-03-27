import asyncio
import random

class SistemaDecisaoRL:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        
        self.q_table = {}
        self.alpha = 0.1      # Taxa de aprendizagem
        self.gamma = 0.9      # Fator de desconto 
        self.epsilon = 0.2    # Taxa de exploração (alterada durante o treino rápido)
        
        self.last_state = {}
        self.last_action = {}
        self.last_vehicle_count = 0

        # Estado inicial dos cruzamentos compatível com os outros SDs
        self.crossroads = {}
        for c in config['crossroads']:
            self.crossroads[c['id']] = {
                'eixo_ativo': 2, 
                'cor_eixo': 2,   
                'tempo_restante': 15
            }

    def get_state(self, cr_id, eixo_ativo):
        """Discretiza o estado da fila no eixo que vai abrir (Níveis: 0, 1, 2)"""
        total_carros = 0
        vias_do_eixo = [tl['roadIndex'] for tl in self.cfg['trafficLights'] 
                        if tl['crID'] == cr_id and tl['axis'] == eixo_ativo]
        
        for rid in vias_do_eixo:
            total_carros += self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
            
        if total_carros < 5: return 0
        if total_carros < 15: return 1
        return 2

    def calcular_total_carros_rede(self):
        total = 0
        for r in self.cfg['roads']:
            total += self.mib.get(f"{self.base}.3.1.6.{r['id']}", 0)
        return total

    # =====================================================================
    # O MÉTODO QUE FALTAVA PARA O TEMPO REAL:
    # =====================================================================
    async def start(self):
        print("[SD-RL] O Agente Q-Learning assumiu o controlo em tempo real.")
        while True:
            await asyncio.sleep(1)
            await self.update()

    async def update(self, fast_forward_step=None):
        step = fast_forward_step if fast_forward_step else self.mib.get(f"{self.base}.1.2.0", 1)
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        acoes_possiveis = [15, 30, 45] # As três ações do agente: Verde curto, médio ou longo

        # 1. Calcular Recompensa Global (Variação de carros na rede inteira)
        current_vehicle_count = self.calcular_total_carros_rede()
        reward = self.last_vehicle_count - current_vehicle_count 
        self.last_vehicle_count = current_vehicle_count

        for cr_id, cr in self.crossroads.items():
            cr['tempo_restante'] -= step
            
            if cr['tempo_restante'] <= 0:
                if cr['cor_eixo'] == 2: # Terminou Verde -> Amarelo
                    cr['cor_eixo'] = 3
                    cr['tempo_restante'] = yellow_time
                
                elif cr['cor_eixo'] == 3: # Terminou Amarelo -> Muda Eixo
                    cr['cor_eixo'] = 2
                    cr['eixo_ativo'] = 1 if cr['eixo_ativo'] == 2 else 2
                    
                    # --- LÓGICA DE Q-LEARNING ---
                    estado_atual = self.get_state(cr_id, cr['eixo_ativo'])
                    
                    if estado_atual not in self.q_table:
                        self.q_table[estado_atual] = [0.0, 0.0, 0.0]

                    # Atualiza a Q-Table com base na ação ANTERIOR deste cruzamento
                    if cr_id in self.last_state:
                        s_antigo = self.last_state[cr_id]
                        a_antiga = self.last_action[cr_id]
                        max_futuro = max(self.q_table[estado_atual])
                        
                        # Equação de Bellman
                        self.q_table[s_antigo][a_antiga] += self.alpha * (reward + self.gamma * max_futuro - self.q_table[s_antigo][a_antiga])

                    # Escolhe a NOVA ação (Epsilon-Greedy)
                    if random.uniform(0, 1) < self.epsilon:
                        acao_escolhida = random.randint(0, 2) # Exploração Aleatória
                    else:
                        acao_escolhida = self.q_table[estado_atual].index(max(self.q_table[estado_atual])) # Exploração Inteligente

                    tempo_verde = acoes_possiveis[acao_escolhida]
                    cr['tempo_restante'] = tempo_verde
                    
                    self.last_state[cr_id] = estado_atual
                    self.last_action[cr_id] = acao_escolhida
                    
                    # Só faz print das decisões durante a execução em tempo real para não spammar o treino
                    if not fast_forward_step: 
                        acao_tipo = "ALEATÓRIA" if self.epsilon > 0 else "APRENDIDA"
                        print(f"[SD-RL] C{cr_id} -> Eixo {cr['eixo_ativo']} | Nível de Fila: {estado_atual} | Decisão {acao_tipo}: {tempo_verde}s")

        # Refletir na MIB
        for tl in self.cfg['trafficLights']:
            rid = tl['roadIndex']
            cr = self.crossroads[tl['crID']] 
            if tl['axis'] == cr['eixo_ativo']:
                self.mib[f"{self.base}.4.1.3.{rid}"] = cr['cor_eixo']
                self.mib[f"{self.base}.4.1.4.{rid}"] = max(0, cr['tempo_restante'])
            else:
                self.mib[f"{self.base}.4.1.3.{rid}"] = 1 
                self.mib[f"{self.base}.4.1.4.{rid}"] = 0