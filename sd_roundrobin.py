# ==============================================================================
# Ficheiro: sd_roundrobin.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Sistema de Decisão Baseado em Round-Robin (Ciclo Fixo).
#            Este algoritmo atua como a baseline (base de comparação) do projeto.
#            É "cego" ao volume de tráfego, alternando a luz verde entre o Eixo 1 
#            e o Eixo 2 de cada cruzamento de forma estática e periódica.
# ==============================================================================

import asyncio

class SistemaDecisaoRoundRobin:
    """
    Controlador semafórico de ciclo estático.
    Garante a exclusão mútua dos eixos e alterna de forma contínua e previsível.
    """
    def __init__(self, mib_partilhada, configuracao):
        self.mib_partilhada = mib_partilhada
        self.configuracao = configuracao
        self.base_oid = "1.3.6.1.3.2026.1"
        
        # Estado interno por cruzamento (Garante a sincronização perfeita dos semáforos)
        self.estado_cruzamentos = {}
        tempo_verde_inicial = self.mib_partilhada.get(f"{self.base_oid}.1.4.0", 15)
        
        for cruzamento in configuracao.get('crossroads', []):
            self.estado_cruzamentos[cruzamento['id']] = {
                'eixo_ativo': 2, # Começamos a dar primazia ao Eixo 2
                'cor_eixo': 2,   # 1 = Vermelho, 2 = Verde, 3 = Amarelo
                'tempo_restante': tempo_verde_inicial
            }
            
        print("[SD-RR] Algoritmo Round-Robin inicializado (Exclusão mútua garantida).")

    async def start(self):
        """Ciclo de vida (não invocado diretamente devido à arquitetura centralizada do SC)."""
        print("[SD-RR] Algoritmo Round-Robin (Ciclo Fixo) pronto.")

    async def update(self, current_step=None, fast_forward_step=None):
        """
        Calcula as transições de tempo fixo. Quando o tempo de um eixo esgota, 
        passa ao amarelo e depois roda o eixo ativo.
        """
        passo = current_step if current_step is not None else fast_forward_step
        if passo is None: 
            passo = 0.5

        tempo_amarelo = self.mib_partilhada.get(f"{self.base_oid}.1.5.0", 3)
        tempo_verde_fixo = self.mib_partilhada.get(f"{self.base_oid}.1.4.0", 15)

        # 1. ATUALIZAÇÃO DOS ESTADOS DOS CRUZAMENTOS
        for id_cruzamento, cruzamento in self.estado_cruzamentos.items():
            cruzamento['tempo_restante'] -= passo

            if cruzamento['tempo_restante'] <= 0:
                if cruzamento['cor_eixo'] == 2: 
                    # Terminou o Verde -> Transição para Amarelo
                    cruzamento['cor_eixo'] = 3
                    cruzamento['tempo_restante'] = tempo_amarelo
                    
                elif cruzamento['cor_eixo'] == 3: 
                    # Terminou o Amarelo -> Troca de Eixo (Round-Robin puro)
                    cruzamento['cor_eixo'] = 2
                    cruzamento['eixo_ativo'] = 1 if cruzamento['eixo_ativo'] == 2 else 2
                    cruzamento['tempo_restante'] = tempo_verde_fixo

        # ====================================================================
        # ATUALIZAÇÃO DA MIB (Propagação das cores e tempos)
        # ====================================================================
        for semaforo in self.configuracao.get('trafficLights', []):
            id_rua = semaforo['roadIndex']
            
            # Suporta compatibilidade com configs antigos (crID vs tlCrossroadID)
            id_cruzamento = semaforo.get('crID') or semaforo.get('tlCrossroadID')
            eixo_semaforo = semaforo.get('axis', semaforo.get('tlAxis', 1))
            
            if id_cruzamento in self.estado_cruzamentos:
                cruzamento = self.estado_cruzamentos[id_cruzamento]

                if eixo_semaforo == cruzamento['eixo_ativo']:
                    self.mib_partilhada[f"{self.base_oid}.4.1.3.{id_rua}"] = cruzamento['cor_eixo']
                    self.mib_partilhada[f"{self.base_oid}.4.1.4.{id_rua}"] = max(0, int(cruzamento['tempo_restante']))
                else:
                    self.mib_partilhada[f"{self.base_oid}.4.1.3.{id_rua}"] = 1 # Vermelho
                    self.mib_partilhada[f"{self.base_oid}.4.1.4.{id_rua}"] = 0