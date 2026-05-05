# ==============================================================================
# Ficheiro: sd_backpressure.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Sistema de Decisão Baseado em Algoritmo de Backpressure.
#            Este algoritmo controla os semáforos calculando a "pressão" de 
#            tráfego (diferença entre o tamanho da fila na origem e no destino).
#            O eixo do cruzamento com maior pressão acumulada recebe luz verde,
#            maximizando o escoamento dinâmico e contínuo da rede.
# ==============================================================================

import asyncio

class SistemaDecisaoBackpressure:
    """
    Implementa a lógica de decisão de tráfego baseada na política de Backpressure Routing.
    """
    def __init__(self, mib_partilhada, configuracao):
        self.mib_partilhada = mib_partilhada
        self.configuracao = configuracao
        self.base_oid = "1.3.6.1.3.2026.1"

        # Estado interno de cada cruzamento para gerir as transições de luzes
        self.estado_cruzamentos = {}
        for cruzamento in configuracao['crossroads']:
            self.estado_cruzamentos[cruzamento['id']] = {
                'eixo_ativo': 2, # Começa no eixo 2 por defeito
                'cor_eixo': 2,   # Cores: 1 = Vermelho, 2 = Verde, 3 = Amarelo
                'tempo_restante': 15
            }

    async def start(self):
        """Ciclo de vida independente (não utilizado nesta arquitetura centralizada pelo SC)."""
        pass

    async def update(self, current_step=None, fast_forward_step=None):
        """
        Avalia e atualiza o estado de todos os semáforos a cada ciclo de simulação (passo).
        """
        passo = current_step if current_step is not None else fast_forward_step
        if passo is None: 
            passo = 0.5
        
        tempo_amarelo = self.mib_partilhada.get(f"{self.base_oid}.1.5.0", 3)
        tempo_min_verde = self.mib_partilhada.get(f"{self.base_oid}.1.4.0", 15)

        for id_cruzamento, cruzamento in self.estado_cruzamentos.items():
            cruzamento['tempo_restante'] -= passo
            
            # Quando o tempo mínimo do semáforo expira, recalculamos as pressões
            if cruzamento['tempo_restante'] <= 0:
                pressao_eixo = {1: 0, 2: 0}
                semaforos_cruzamento = [sem for sem in self.configuracao['trafficLights'] if sem['crID'] == id_cruzamento]
                
                # 1. CÁLCULO DA PRESSÃO POR VIA
                for semaforo in semaforos_cruzamento:
                    id_rua = semaforo['roadIndex']
                    eixo = semaforo['axis']
                    fila_origem = self.mib_partilhada.get(f"{self.base_oid}.3.1.6.{id_rua}", 0)
                    ligacoes_destino = [lig for lig in self.configuracao['links'] if lig['src'] == id_rua]
                    
                    maior_pressao = 0
                    
                    # Se for uma via de saída (sem destinos configurados), a pressão é apena a fila atual
                    if not ligacoes_destino:
                        maior_pressao = fila_origem
                    else:
                        # Calcula o peso (pressão) avaliando o quão cheias estão as ruas de destino
                        for ligacao in ligacoes_destino:
                            id_destino = ligacao['dest']
                            fila_destino = self.mib_partilhada.get(f"{self.base_oid}.3.1.6.{id_destino}", 0)
                            capacidade_destino = self.mib_partilhada.get(f"{self.base_oid}.3.1.5.{id_destino}", 999)
                            
                            if fila_destino < capacidade_destino:
                                # Backpressure Teórico: Pressão = Max(0, Fila_Origem - Fila_Destino)
                                maior_pressao = max(maior_pressao, max(0, fila_origem - fila_destino))
                    
                    pressao_eixo[eixo] += maior_pressao

                # 2. DETERMINAR O VENCEDOR
                eixo_vencedor = 1 if pressao_eixo[1] >= pressao_eixo[2] else 2
                
                # Desempate/Rotina: Se não há trânsito, alterna para não deixar um eixo bloqueado indefinidamente
                if pressao_eixo[1] == 0 and pressao_eixo[2] == 0:
                    eixo_vencedor = 1 if cruzamento['eixo_ativo'] == 2 else 2

                # 3. LÓGICA DE TRANSIÇÃO DE LUZES (Máquina de Estados)
                if cruzamento['cor_eixo'] == 2: # Se está Verde
                    if eixo_vencedor != cruzamento['eixo_ativo']:
                        # Exige mudança de eixo: Abranda para Amarelo
                        cruzamento['cor_eixo'] = 3 
                        cruzamento['tempo_restante'] = tempo_amarelo
                    else:
                        # Mantém o verde, mas adiciona apenas o tempo do passo atual
                        cruzamento['tempo_restante'] = passo
                        
                elif cruzamento['cor_eixo'] == 3: # Se está Amarelo
                    # O amarelo terminou, passa o novo eixo a Verde
                    cruzamento['cor_eixo'] = 2
                    cruzamento['eixo_ativo'] = eixo_vencedor
                    cruzamento['tempo_restante'] = tempo_min_verde

        # ====================================================================
        # ATUALIZAÇÃO DA MIB (Sincroniza a decisão com o SC e a Interface)
        # ====================================================================
        for semaforo in self.configuracao['trafficLights']:
            id_rua = semaforo['roadIndex']
            cruzamento = self.estado_cruzamentos[semaforo['crID']] 
            
            if semaforo['axis'] == cruzamento['eixo_ativo']:
                self.mib_partilhada[f"{self.base_oid}.4.1.3.{id_rua}"] = cruzamento['cor_eixo']
                self.mib_partilhada[f"{self.base_oid}.4.1.4.{id_rua}"] = int(cruzamento['tempo_restante'])
            else:
                self.mib_partilhada[f"{self.base_oid}.4.1.3.{id_rua}"] = 1 # Luz Vermelha
                self.mib_partilhada[f"{self.base_oid}.4.1.4.{id_rua}"] = 0