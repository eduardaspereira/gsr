import asyncio

class SistemaDecisaoBackpressure:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"

        self.crossroads = {}
        for c in config['crossroads']:
            self.crossroads[c['id']] = {
                'eixo_ativo': 2, # Começa no eixo 2
                'cor_eixo': 2,   # Começa em Verde
                'tempo_restante': 15
            }

    async def start(self):
        pass

    async def update(self, current_step=None, fast_forward_step=None):
        step = current_step if current_step is not None else fast_forward_step
        if step is None: step = 0.5
        
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        min_green = self.mib.get(f"{self.base}.1.4.0", 15)

        for cr_id, cr in self.crossroads.items():
            cr['tempo_restante'] -= step
            
            if cr['tempo_restante'] <= 0:
                pressao_eixo = {1: 0, 2: 0}
                semaforos_cr = [tl for tl in self.cfg['trafficLights'] if tl['crID'] == cr_id]
                
                for tl in semaforos_cr:
                    rid = tl['roadIndex']
                    axis = tl['axis']
                    q_origem = self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
                    vias_destino = [l for l in self.cfg['links'] if l['src'] == rid]
                    
                    maior_p = 0
                    if not vias_destino:
                        maior_p = q_origem
                    else:
                        for link in vias_destino:
                            d_id = link['dest']
                            q_d = self.mib.get(f"{self.base}.3.1.6.{d_id}", 0)
                            cap_d = self.mib.get(f"{self.base}.3.1.5.{d_id}", 999)
                            if q_d < cap_d:
                                maior_p = max(maior_p, max(0, q_origem - q_d))
                    
                    pressao_eixo[axis] += maior_p

                eixo_vencedor = 1 if pressao_eixo[1] >= pressao_eixo[2] else 2
                if pressao_eixo[1] == 0 and pressao_eixo[2] == 0:
                    eixo_vencedor = 1 if cr['eixo_ativo'] == 2 else 2

                if cr['cor_eixo'] == 2: # Verde
                    if eixo_vencedor != cr['eixo_ativo']:
                        cr['cor_eixo'] = 3 # Amarelo
                        cr['tempo_restante'] = yellow_time
                    else:
                        cr['tempo_restante'] = step
                elif cr['cor_eixo'] == 3: # Amarelo
                    cr['cor_eixo'] = 2
                    cr['eixo_ativo'] = eixo_vencedor
                    cr['tempo_restante'] = min_green

        # ATUALIZAÇÃO DA MIB (Sincroniza o que a CMC vê com o que o SD decidiu)
        for tl in self.cfg['trafficLights']:
            rid = tl['roadIndex']
            cr = self.crossroads[tl['crID']] 
            if tl['axis'] == cr['eixo_ativo']:
                self.mib[f"{self.base}.4.1.3.{rid}"] = cr['cor_eixo']
                self.mib[f"{self.base}.4.1.4.{rid}"] = int(cr['tempo_restante'])
            else:
                self.mib[f"{self.base}.4.1.3.{rid}"] = 1 # Red
                self.mib[f"{self.base}.4.1.4.{rid}"] = 0