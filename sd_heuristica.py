import asyncio

class SistemaDecisaoOcupacao:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        self.max_green = 75 # Aumentei um pouco a tranca máxima para a avenida fluir melhor

        self.crossroads = {}
        for c in config['crossroads']:
            self.crossroads[c['id']] = {
                'eixo_ativo': 2, 
                'cor_eixo': 2,   
                'tempo_restante': 15
            }

    async def start(self):
        print("[SD-HEUR] Algoritmo de Ocupação com Prioridade de Avenida iniciado.")
        while True:
            await asyncio.sleep(1)
            await self.update()

    async def update(self):
        step = self.mib.get(f"{self.base}.1.2.0", 1)
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        min_green_base = self.mib.get(f"{self.base}.1.4.0", 10)

        for cr_id, cr in self.crossroads.items():
            cr['tempo_restante'] -= step
            
            if cr['tempo_restante'] <= 0:
                if cr['cor_eixo'] == 2: 
                    cr['cor_eixo'] = 3
                    cr['tempo_restante'] = yellow_time
                
                elif cr['cor_eixo'] == 3: 
                    cr['cor_eixo'] = 2
                    cr['eixo_ativo'] = 1 if cr['eixo_ativo'] == 2 else 2
                    
                    total_carros_eixo = 0
                    vias_do_eixo = [tl['roadIndex'] for tl in self.cfg['trafficLights'] 
                                    if tl['crID'] == cr_id and tl['axis'] == cr['eixo_ativo']]
                    
                    for rid in vias_do_eixo:
                        total_carros_eixo += self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
                    
                    # ========================================================
                    # LÓGICA DE PRIORIDADE (AVENIDA VS RUAS SECUNDÁRIAS)
                    # ========================================================
                    if cr['eixo_ativo'] == 2:
                        # Eixo Horizontal (Vias 1, 2, 3, 10) -> Grande Prioridade
                        tempo_minimo_ativo = 15 # Abre sempre pelo menos 15s
                        peso_carro = 3.0        # Dá 3 segundos por cada carro na fila
                    else:
                        # Eixo Vertical (Vias 5, 7, 8, 9) -> Baixa Prioridade
                        tempo_minimo_ativo = min_green_base # Abre o mínimo possível (10s)
                        peso_carro = 1.5                    # Dá apenas 1.5s por carro
                        
                    if total_carros_eixo == 0:
                        tempo_calculado = tempo_minimo_ativo
                    else:
                        tempo_calculado = min(self.max_green, max(tempo_minimo_ativo, int(total_carros_eixo * peso_carro)))
                    
                    cr['tempo_restante'] = tempo_calculado
                    
                    # Log mais limpo para perceberes as prioridades
                    tipo_via = "AVENIDA" if cr['eixo_ativo'] == 2 else "SECUNDÁRIA"
                    print(f"[SD-HEUR] C{cr_id} -> Eixo {cr['eixo_ativo']} ({tipo_via}) | Fila: {total_carros_eixo} | Verde: {tempo_calculado}s")

        # Refletir as decisões na MIB
        for tl in self.cfg['trafficLights']:
            rid = tl['roadIndex']
            cr = self.crossroads[tl['crID']] 
            
            if tl['axis'] == cr['eixo_ativo']:
                self.mib[f"{self.base}.4.1.3.{rid}"] = cr['cor_eixo']
                self.mib[f"{self.base}.4.1.4.{rid}"] = max(0, cr['tempo_restante'])
            else:
                self.mib[f"{self.base}.4.1.3.{rid}"] = 1 
                self.mib[f"{self.base}.4.1.4.{rid}"] = 0