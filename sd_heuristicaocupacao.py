# ==============================================================================
# Ficheiro: sd_heuristicaocupacao.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Sistema de Decisão Baseado em Heurística de Ocupação.
#            Ao contrário de um ciclo fixo (Round Robin), este algoritmo alterna
#            os eixos de um cruzamento, mas calcula o tempo de Verde dinamicamente
#            baseando-se no número de veículos em espera (Ex: 2s por veículo),
#            limitado por tetos de segurança para evitar starvation (fome) da rede.
# ==============================================================================

import asyncio

class SistemaDecisaoOcupacao:
    """
    Controlador semafórico que define tempos de verde proporcionais ao volume de tráfego.
    Garante a segurança do cruzamento alternando entre Eixos (Axis 1 e Axis 2).
    """
    def __init__(self, mib_partilhada, configuracao):
        self.mib_partilhada = mib_partilhada
        self.configuracao = configuracao
        self.base_oid = "1.3.6.1.3.2026.1"

        # Estado interno de cada cruzamento para gerir as transições seguras (exclusão mútua)
        self.estado_cruzamentos = {}
        for cruzamento in configuracao['crossroads']:
            self.estado_cruzamentos[cruzamento['id']] = {
                'eixo_ativo': 1, # Começa no eixo 1
                'cor_eixo': 2,   # 1 = Vermelho, 2 = Verde, 3 = Amarelo
                'tempo_restante': 10
            }

    async def start(self):
        """Ciclo de vida independente (não utilizado nesta arquitetura centralizada pelo SC)."""
        print("[SD-HEUR] Algoritmo de Ocupação Dinâmica preparado.")

    async def update(self, current_step=None, fast_forward_step=None):
        """
        Avalia e atualiza o estado dos semáforos, calculando novos tempos de verde 
        sempre que um eixo termina o seu ciclo.
        """
        passo = current_step if current_step is not None else fast_forward_step
        if passo is None: 
            passo = 0.5
        
        tempo_amarelo = self.mib_partilhada.get(f"{self.base_oid}.1.5.0", 3)
        tempo_min_verde = self.mib_partilhada.get(f"{self.base_oid}.1.4.0", 10)
        
        # 1. ATUALIZAR ESTADO DE CADA CRUZAMENTO
        for id_cruzamento, cruzamento in self.estado_cruzamentos.items():
            cruzamento['tempo_restante'] -= passo

            if cruzamento['tempo_restante'] <= 0:
                if cruzamento['cor_eixo'] == 2: 
                    # Terminou o Verde -> Passa a Amarelo para esvaziar o cruzamento
                    cruzamento['cor_eixo'] = 3
                    cruzamento['tempo_restante'] = tempo_amarelo
                    
                elif cruzamento['cor_eixo'] == 3: 
                    # Terminou o Amarelo -> Troca de Eixo e calcula novo tempo de Verde
                    novo_eixo = 2 if cruzamento['eixo_ativo'] == 1 else 1
                    cruzamento['eixo_ativo'] = novo_eixo
                    cruzamento['cor_eixo'] = 2
                    
                    # --- CÁLCULO HEURÍSTICO DA OCUPAÇÃO ---
                    # Encontra todas as vias que vão abrir (pertencem ao novo eixo neste cruzamento)
                    semaforos_novo_eixo = [
                        sem for sem in self.configuracao['trafficLights'] 
                        if sem['crID'] == id_cruzamento and sem['axis'] == novo_eixo
                    ]
                    
                    # Soma todos os carros à espera nesse eixo
                    total_carros_espera = sum(
                        self.mib_partilhada.get(f"{self.base_oid}.3.1.6.{sem['roadIndex']}", 0) 
                        for sem in semaforos_novo_eixo
                    )
                    
                    # Regra Heurística: 2 segundos por carro detetado
                    # Exemplo: 20 carros = 40s de verde.
                    tempo_calculado = max(tempo_min_verde, total_carros_espera * 2)
                    
                    # Limite de segurança: Máximo de 60s para não bloquear o eixo oposto para sempre
                    cruzamento['tempo_restante'] = min(60, tempo_calculado)

        # ====================================================================
        # ATUALIZAÇÃO DA MIB (Sincroniza a decisão com a simulação física)
        # ====================================================================
        for semaforo in self.configuracao['trafficLights']:
            id_rua = semaforo['roadIndex']
            cruzamento = self.estado_cruzamentos[semaforo['crID']] 
            
            if semaforo['axis'] == cruzamento['eixo_ativo']:
                self.mib_partilhada[f"{self.base_oid}.4.1.3.{id_rua}"] = cruzamento['cor_eixo']
                self.mib_partilhada[f"{self.base_oid}.4.1.4.{id_rua}"] = int(cruzamento['tempo_restante'])
            else:
                self.mib_partilhada[f"{self.base_oid}.4.1.3.{id_rua}"] = 1 # Luz Vermelha garantida
                self.mib_partilhada[f"{self.base_oid}.4.1.4.{id_rua}"] = 0