import asyncio

class SistemaDecisaoBackpressure:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        self.max_green = 60 # Tranca de segurança máxima

        self.crossroads = {}
        for c in config['crossroads']:
            self.crossroads[c['id']] = {
                'eixo_ativo': 2, 
                'cor_eixo': 2,   
                'tempo_restante': 15
            }

    async def start(self):
        print("[SD-BP] Algoritmo de Backpressure (Diferencial de Filas) iniciado.")
        while True:
            await asyncio.sleep(1)
            await self.update()

    async def update(self):
        step = self.mib.get(f"{self.base}.1.2.0", 1)
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        min_green = self.mib.get(f"{self.base}.1.4.0", 10)

        for cr_id, cr in self.crossroads.items():
            cr['tempo_restante'] -= step
            
            if cr['tempo_restante'] <= 0:
                if cr['cor_eixo'] == 2: 
                    cr['cor_eixo'] = 3
                    cr['tempo_restante'] = yellow_time
                
                elif cr['cor_eixo'] == 3: 
                    cr['cor_eixo'] = 2
                    cr['eixo_ativo'] = 1 if cr['eixo_ativo'] == 2 else 2
                    
                    # ========================================================
                    # LÓGICA BACKPRESSURE (Pressão = Origem - Destino)
                    # ========================================================
                    vias_do_eixo = [tl['roadIndex'] for tl in self.cfg['trafficLights'] 
                                    if tl['crID'] == cr_id and tl['axis'] == cr['eixo_ativo']]
                    
                    maior_pressao_eixo = 0
                    destinos_livres = False
                    
                    for rid in vias_do_eixo:
                        q_origem = self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
                        vias_destino = [l for l in self.cfg['links'] if l['src'] == rid]
                        
                        if not vias_destino:
                            # Se é uma via de saída do mapa, o destino é infinito. A pressão é a própria fila.
                            maior_pressao_eixo = max(maior_pressao_eixo, q_origem)
                            destinos_livres = True
                            continue
                            
                        for link in vias_destino:
                            dest_id = link['dest']
                            q_dest = self.mib.get(f"{self.base}.3.1.6.{dest_id}", 0)
                            cap_dest = self.mib.get(f"{self.base}.3.1.5.{dest_id}", 999)
                            
                            if q_dest < cap_dest:
                                destinos_livres = True
                                pressao = q_origem - q_dest
                                maior_pressao_eixo = max(maior_pressao_eixo, pressao)

                    # Se há espaço no destino, o tempo escala com a pressão máxima (ex: 1.5s por cada ponto de pressão)
                    if destinos_livres:
                        tempo_calculado = min_green + max(0, int(maior_pressao_eixo * 1.5))
                        tempo_calculado = min(self.max_green, max(min_green, tempo_calculado))
                    else:
                        # Destinos entupidos! Abre apenas o mínimo legal para não empancar o ciclo.
                        tempo_calculado = min_green
                    
                    cr['tempo_restante'] = tempo_calculado
                    
                    print(f"[SD-BP] C{cr_id} -> Eixo {cr['eixo_ativo']} | Pressão Máxima: {maior_pressao_eixo} | Verde: {tempo_calculado}s")

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