# ==============================================================================
# Ficheiro: sd_RL.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Sistema de Decisão baseado em Aprendizagem por Reforço (Q-Learning).
#            Cada cruzamento age como um Agente autónomo que aprende a melhor 
#            duração de verde (Ação) para um dado volume de trânsito (Estado),
#            maximizando o escoamento local (Recompensa).
# ==============================================================================

import asyncio
import random
import json
import os
import hashlib

class SistemaDecisaoRL:
    """
    Agente Q-Learning para otimização de semáforos.
    Utiliza uma Q-Table persistente e recompensas baseadas na variação do número
    de veículos à espera no cruzamento (delta de escoamento local).
    """
    def __init__(self, mib_partilhada, configuracao):
        self.mib_partilhada = mib_partilhada
        self.configuracao = configuracao
        self.base_oid = "1.3.6.1.3.2026.1"

        # --- GERAR ASSINATURA ÚNICA DO MAPA (Evita mistura de cérebros) ---
        assinatura_mapa = "CR:" + ",".join(str(c['id']) for c in configuracao.get('crossroads', []))
        assinatura_mapa += "|V:" + ",".join(str(r['id']) for r in configuracao.get('roads', []))
        self.hash_mapa = hashlib.md5(assinatura_mapa.encode()).hexdigest()[:8]
        
        self.ficheiro_cerebro = f"q_table_mapa_{self.hash_mapa}.json"
        
        # --- PARÂMETROS MATEMÁTICOS DO Q-LEARNING ---
        self.q_table = {}
        self.alpha = 0.1      # Taxa de Aprendizagem (Learning Rate)
        self.gamma = 0.9      # Fator de Desconto (Discount Factor - visão de futuro)
        self.epsilon = 0.2    # Taxa de Exploração (Exploration Rate inicial)
        
        self.precisa_treino = True 
        self.carregar_cerebro()
        
        # Memória de Curto Prazo (para calcular o delta R na transição s -> s')
        self.estado_anterior = {}
        self.acao_anterior = {}
        self.contagem_local_anterior = {c['id']: 0 for c in configuracao['crossroads']}

        self.estado_cruzamentos = {}
        for cruzamento in configuracao['crossroads']:
            self.estado_cruzamentos[cruzamento['id']] = {
                'eixo_ativo': 2, 
                'cor_eixo': 2,   
                'tempo_restante': 15
            }

    def carregar_cerebro(self):
        """Carrega a Q-Table do disco (se existir para a topologia atual)."""
        if os.path.exists(self.ficheiro_cerebro):
            try:
                with open(self.ficheiro_cerebro, 'r') as ficheiro:
                    q_table_chaves_str = json.load(ficheiro)
                    # O JSON guarda chaves como string, temos de converter de volta para int (Estado)
                    self.q_table = {int(k): v for k, v in q_table_chaves_str.items()}
                print(f"[SD-RL] Cérebro carregado: {self.ficheiro_cerebro} ({len(self.q_table)} estados mapeados)")
                self.precisa_treino = False
                self.epsilon = 0.05 # Reduz a exploração, foca no conhecimento adquirido (Exploitation)
            except Exception as erro:
                print(f"[SD-RL] Erro ao ler cérebro corrompido: {erro}. A iniciar treino de raiz.")
        else:
            print(f"[SD-RL] Novo cenário detetado (Hash: {self.hash_mapa}). A iniciar treino de raiz.")

    def guardar_cerebro(self):
        """Persiste a matriz de conhecimento Q-Table no disco em formato JSON."""
        try:
            with open(self.ficheiro_cerebro, 'w') as ficheiro:
                json.dump(self.q_table, ficheiro)
            print(f"[SD-RL] Cérebro gravado com sucesso.")
        except Exception:
            pass

    def _contar_carros_locais(self, id_cruzamento):
        """Devolve o número total de veículos à espera em TODAS as vias de um cruzamento específico."""
        total = 0
        for semaforo in self.configuracao['trafficLights']:
            if semaforo.get('crID') == id_cruzamento or semaforo.get('tlCrossroadID') == id_cruzamento:
                id_rua = semaforo['roadIndex']
                total += self.mib_partilhada.get(f"{self.base_oid}.3.1.6.{id_rua}", 0)
        return total

    def _obter_estado_cruzamento(self, id_cruzamento, eixo_ativo):
        """
        Observa o ambiente e condensa-o num Estado Discreto (1D) usando Base 4.
        Avalia o peso das vias a Verde e das vias a Vermelho em simultâneo.
        """
        carros_verde = 0
        carros_vermelho = 0
        
        for semaforo in self.configuracao['trafficLights']:
            if semaforo.get('crID') == id_cruzamento or semaforo.get('tlCrossroadID') == id_cruzamento:
                id_rua = semaforo['roadIndex']
                quantidade = self.mib_partilhada.get(f"{self.base_oid}.3.1.6.{id_rua}", 0)
                
                if semaforo['axis'] == eixo_ativo:
                    carros_verde += quantidade
                else:
                    carros_vermelho += quantidade
                    
        def discretizar(qtd):
            if qtd < 10: return 0  # Trânsito Vazio/Leve
            if qtd < 25: return 1  # Trânsito Normal
            if qtd < 45: return 2  # Trânsito Pesado
            return 3               # Gridlock (Congestionamento Crítico)
            
        # Codificação de 2 variáveis (0 a 3) num único inteiro (0 a 15)
        estado_codificado = discretizar(carros_verde) * 4 + discretizar(carros_vermelho)
        return estado_codificado

    async def start(self):
        """Ciclo de vida (não invocado devido ao controlo sincronizado do Sistema Central)."""
        print("[SD-RL] Inicializado com Visão 360º e Funções de Recompensa Locais.")

    async def update(self, current_step=None, fast_forward_step=None):
        """Ciclo de Decisão Principal: Avalia recompensas, atualiza a Q-Table e escolhe novas ações."""
        passo = current_step if current_step is not None else fast_forward_step
        if passo is None: 
            passo = 0.5
        
        tempo_amarelo = self.mib_partilhada.get(f"{self.base_oid}.1.5.0", 3)
        acoes_possiveis = [15, 30, 45] # Durações de Verde disponíveis para o Agente

        for id_cruzamento, cruzamento in self.estado_cruzamentos.items():
            cruzamento['tempo_restante'] -= passo
            
            if cruzamento['tempo_restante'] <= 0:
                if cruzamento['cor_eixo'] == 2: # Terminou o Verde -> Muda para Amarelo
                    cruzamento['cor_eixo'] = 3
                    cruzamento['tempo_restante'] = tempo_amarelo
                
                elif cruzamento['cor_eixo'] == 3: # Terminou o Amarelo -> FASE DE DECISÃO RL
                    cruzamento['cor_eixo'] = 2
                    cruzamento['eixo_ativo'] = 1 if cruzamento['eixo_ativo'] == 2 else 2
                    
                    # 1. CÁLCULO DA RECOMPENSA (R)
                    # Quantos carros saíram do cruzamento desde a última decisão?
                    carros_atuais = self._contar_carros_locais(id_cruzamento)
                    recompensa = self.contagem_local_anterior[id_cruzamento] - carros_atuais 
                    self.contagem_local_anterior[id_cruzamento] = carros_atuais
                    
                    # 2. OBSERVAÇÃO DO NOVO ESTADO (s')
                    estado_atual = self._obter_estado_cruzamento(id_cruzamento, cruzamento['eixo_ativo'])
                    
                    if estado_atual not in self.q_table:
                        self.q_table[estado_atual] = [0.0, 0.0, 0.0]

                    # 3. ATUALIZAÇÃO DA EQUAÇÃO DE BELLMAN
                    if id_cruzamento in self.estado_anterior:
                        s_ant = self.estado_anterior[id_cruzamento]
                        a_ant = self.acao_anterior[id_cruzamento]
                        max_futuro = max(self.q_table[estado_atual])
                        
                        # Q(s,a) = Q(s,a) + alpha * [R + gamma * max(Q(s',a')) - Q(s,a)]
                        delta_aprendizagem = recompensa + self.gamma * max_futuro - self.q_table[s_ant][a_ant]
                        self.q_table[s_ant][a_ant] += self.alpha * delta_aprendizagem

                    # 4. POLÍTICA DE SELEÇÃO DE AÇÃO (Epsilon-Greedy)
                    sorteio = random.uniform(0, 1)
                    if sorteio < self.epsilon:
                        # Exploração (Exploration): Testa uma ação aleatória
                        indice_acao = random.randint(0, 2)
                        tipo_registo = "EXPLORAÇÃO"
                    else:
                        # Aproveitamento (Exploitation): Escolhe a ação com maior Q-Value
                        indice_acao = self.q_table[estado_atual].index(max(self.q_table[estado_atual]))
                        tipo_registo = "INTELIGENTE"

                    tempo_verde_escolhido = acoes_possiveis[indice_acao]
                    cruzamento['tempo_restante'] = tempo_verde_escolhido
                    
                    # Guarda o contexto para a próxima iteração
                    self.estado_anterior[id_cruzamento] = estado_atual
                    self.acao_anterior[id_cruzamento] = indice_acao
                    
                    # Apenas imprime os logs se não estiver em fase de Treino (fast-forward)
                    if not fast_forward_step: 
                        print(f"[RL] Cruzamento C{id_cruzamento} | Estado {estado_atual} | Decisão: {tipo_registo} -> {tempo_verde_escolhido}s")

        # ====================================================================
        # SINCRONIZAÇÃO COM A MIB
        # ====================================================================
        for semaforo in self.configuracao['trafficLights']:
            id_rua = semaforo['roadIndex']
            cruzamento = self.estado_cruzamentos[semaforo['crID']] 
            
            if semaforo['axis'] == cruzamento['eixo_ativo']:
                self.mib_partilhada[f"{self.base_oid}.4.1.3.{id_rua}"] = cruzamento['cor_eixo']
                self.mib_partilhada[f"{self.base_oid}.4.1.4.{id_rua}"] = max(0, int(cruzamento['tempo_restante']))
            else:
                self.mib_partilhada[f"{self.base_oid}.4.1.3.{id_rua}"] = 1 # Vermelho
                self.mib_partilhada[f"{self.base_oid}.4.1.4.{id_rua}"] = 0