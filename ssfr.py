# ==============================================================================
# Ficheiro: ssfr.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Sistema de Simulação de Fluxo de Rede (SSFR). Este módulo atua
#            como o "motor físico" do simulador, sendo responsável por injetar, 
#            movimentar e escoar os veículos através das vias com base no estado 
#            dos semáforos, Taxa de Geração (RTG) e capacidade das ruas.
# ==============================================================================

import asyncio
import random

class SistemaSimulacao:
    """
    Motor principal de simulação de tráfego. 
    Lê e atualiza a Base de Informação de Gestão (MIB) em tempo real, 
    simulando a física do trânsito a cada ciclo de tempo (dt).
    """
    
    def __init__(self, mib_partilhada, configuracao):
        self.mib_partilhada = mib_partilhada
        self.configuracao = configuracao
        self.base_oid = "1.3.6.1.3.2026.1"
        
        # Acumuladores fracionais para garantir escoamento e geração fluidos
        self.acumuladores_entrada = {via['id']: 0.0 for via in configuracao['roads']}
        self.acumuladores_saida = {via['id']: 0.0 for via in configuracao['roads']}

    async def start(self):
        """
        Ciclo de vida principal em modo assíncrono.
        Pode ser usado como uma tarefa independente para manter o motor a correr.
        """
        print("[SSFR] Motor de Geração e Distribuição iniciado.")
        dt = 0.5 
        while True:
            await asyncio.sleep(dt)
            self.executar_passo(dt)

    def executar_passo(self, duracao):
        """
        Executa um único ciclo (frame) da simulação.
        O processo está modularizado em geração e movimentação para clareza.
        """
        self._gerar_trafego_entrada(duracao)
        self._processar_movimentos(duracao)

    def _gerar_trafego_entrada(self, duracao):
        """
        1. GERAÇÃO DE TRÁFEGO
        Injeta novos veículos nas vias de entrada (extremidades do mapa) 
        com base na Taxa Geradora de Tráfego (RTG - veículos por minuto).
        """
        for via in self.configuracao['roads']:
            id_via = via['id']
            rtg = self.mib_partilhada.get(f"{self.base_oid}.3.1.4.{id_via}", 0)
            
            if rtg > 0:
                cor_semaforo = self.mib_partilhada.get(f"{self.base_oid}.4.1.3.{id_via}", 2)
                
                # Regra de realismo: Se o semáforo está amarelo (3), o tráfego de entrada abranda
                if cor_semaforo == 3: 
                    rtg = rtg / 2.0 
                
                # Converter RTG (v/min) para o tempo decorrido no ciclo
                self.acumuladores_entrada[id_via] += (rtg / 60.0) * duracao
                
                # Quando acumula 1 ou mais veículos inteiros, materializa-os na via
                if self.acumuladores_entrada[id_via] >= 1.0:
                    carros_adicionados = int(self.acumuladores_entrada[id_via])
                    carros_atuais = self.mib_partilhada.get(f"{self.base_oid}.3.1.6.{id_via}", 0)
                    capacidade_max = self.mib_partilhada.get(f"{self.base_oid}.3.1.5.{id_via}", 999)
                    
                    if carros_atuais + carros_adicionados <= capacidade_max:
                        self.mib_partilhada[f"{self.base_oid}.3.1.6.{id_via}"] = carros_atuais + carros_adicionados
                    
                    # Deduz apenas a parte inteira (mantém a parte decimal para o próximo ciclo)
                    self.acumuladores_entrada[id_via] -= carros_adicionados

    def _processar_movimentos(self, duracao):
        """
        2. DISTRIBUIÇÃO E ESCOAMENTO NOS CRUZAMENTOS
        Avalia os semáforos, calcula a probabilidade de viragem (FlowRate) e 
        move os veículos de uma via para a próxima, tratando limites físicos.
        """
        # Mapeia as ligações disponíveis por via de origem
        ligacoes_por_origem = {}
        for ligacao in self.configuracao.get('links', []):
            ligacoes_por_origem.setdefault(ligacao['src'], []).append(ligacao)

        for via in self.configuracao['roads']:
            id_origem = via['id']
            ligacoes = ligacoes_por_origem.get(id_origem, [])
            carros_atuais = self.mib_partilhada.get(f"{self.base_oid}.3.1.6.{id_origem}", 0)
            
            # --- CASO A: Via de Saída da Rede (Dissipador) ---
            if len(ligacoes) == 0:
                if carros_atuais > 0:
                    # Usa o fluxo nativo da via (por defeito 60 v/min se não definido)
                    fluxo_saida = self.mib_partilhada.get(f"{self.base_oid}.3.1.4.{id_origem}", 60) 
                    self.acumuladores_saida[id_origem] += (fluxo_saida / 60.0) * duracao
                    
                    if self.acumuladores_saida[id_origem] >= 1.0:
                        carros_para_sair = int(self.acumuladores_saida[id_origem])
                        saida_efetiva = min(carros_atuais, carros_para_sair)
                        
                        if saida_efetiva > 0:
                            # Os veículos desaparecem do mapa (escoamento)
                            self.mib_partilhada[f"{self.base_oid}.3.1.6.{id_origem}"] -= saida_efetiva
                            self.acumuladores_saida[id_origem] -= saida_efetiva
            
            # --- CASO B: Via Normal com Semáforo e Cruzamento ---
            else:
                cor_semaforo = self.mib_partilhada.get(f"{self.base_oid}.4.1.3.{id_origem}", 1) 
                
                # Só permite movimento se o semáforo for Verde (2) ou Amarelo (3)
                if cor_semaforo in [2, 3]: 
                    if carros_atuais > 0:
                        fluxo_total = sum(l.get('flowRate', 10) for l in ligacoes)
                        self.acumuladores_saida[id_origem] += (fluxo_total / 60.0) * duracao
                        
                        if self.acumuladores_saida[id_origem] >= 1.0:
                            carros_para_mover = int(self.acumuladores_saida[id_origem])
                            movimento_efetivo = min(carros_atuais, carros_para_mover)

                            if movimento_efetivo > 0:
                                # 1. Retira preventivamente os veículos da via de origem
                                self.mib_partilhada[f"{self.base_oid}.3.1.6.{id_origem}"] -= movimento_efetivo
                                carros_movidos_sucesso = 0
                                
                                # 2. Processa a lógica de encaminhamento para cada veículo individualmente
                                for _ in range(movimento_efetivo):
                                    # Lógica de "Roleta" para escolher a direção baseada no FlowRate
                                    rand = random.uniform(0, fluxo_total)
                                    acumulado = 0
                                    
                                    for ligacao in ligacoes:
                                        acumulado += ligacao.get('flowRate', 10)
                                        if rand <= acumulado:
                                            id_destino = ligacao['dest']
                                            carros_destino = self.mib_partilhada.get(f"{self.base_oid}.3.1.6.{id_destino}", 0)
                                            cap_destino = self.mib_partilhada.get(f"{self.base_oid}.3.1.5.{id_destino}", 999)

                                            if carros_destino < cap_destino:
                                                # Há espaço físico: O veículo transita para a nova via
                                                self.mib_partilhada[f"{self.base_oid}.3.1.6.{id_destino}"] = carros_destino + 1
                                                
                                                # Atualiza métricas de trânsito efetuado no cruzamento (Link)
                                                oid_ligacao = f"{self.base_oid}.5.1.4.{id_origem}.{id_destino}"
                                                self.mib_partilhada[oid_ligacao] = self.mib_partilhada.get(oid_ligacao, 0) + 1
                                                carros_movidos_sucesso += 1
                                            else:
                                                # BACKPRESSURE (Spillback): O cruzamento está engarrafado.
                                                # O veículo "bate no trânsito" e é forçado a recuar para a origem.
                                                self.mib_partilhada[f"{self.base_oid}.3.1.6.{id_origem}"] += 1
                                            
                                            break # Veículo tratado, avança para o próximo
                                
                                # 3. Desconta do acumulador APENAS os veículos que realmente atravessaram
                                self.acumuladores_saida[id_origem] -= carros_movidos_sucesso