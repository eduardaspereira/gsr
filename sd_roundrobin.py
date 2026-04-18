import asyncio

class SistemaDecisaoRoundRobin:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        
        print("[SD-RR] Inicializando estados: Eixo 2 começa VERDE, Eixo 1 começa VERMELHO.")
        
        for tl in config['trafficLights']:
            rid = tl['roadIndex']
            
            # CORREÇÃO: Lê 'axis', mas suporta 'tlAxis' se os ficheiros antigos o usarem
            eixo = tl.get('axis', tl.get('tlAxis', 1))
            inicial_color = 2 if eixo == 2 else 1 
            self.mib[f"{self.base}.4.1.3.{rid}"] = inicial_color
            
            default_green = self.mib.get(f"{self.base}.1.4.0", 15)
            self.mib[f"{self.base}.4.1.4.{rid}"] = default_green

    async def start(self):
        print("[SD-RR] Algoritmo Round-Robin (Ciclo Fixo) pronto.")

    async def update(self, current_step=None, fast_forward_step=None):
        step = current_step if current_step is not None else fast_forward_step
        if step is None: step = 0.5

        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        min_green = self.mib.get(f"{self.base}.1.4.0", 15)

        for cr in self.cfg['crossroads']:
            cr_id = cr['id']
            semaforos = [tl for tl in self.cfg['trafficLights'] if tl.get('crID') == cr_id or tl.get('tlCrossroadID') == cr_id]
            
            for tl in semaforos:
                rid = tl['roadIndex']
                oid_color = f"{self.base}.4.1.3.{rid}"
                oid_time = f"{self.base}.4.1.4.{rid}"
                
                current_time = self.mib.get(oid_time, 0) - step
                curr_color = self.mib.get(oid_color, 1)

                if current_time <= 0:
                    if curr_color == 2: # VERDE -> AMARELO
                        self.mib[oid_color] = 3
                        self.mib[oid_time] = yellow_time
                    elif curr_color == 3: # AMARELO -> VERMELHO
                        self.mib[oid_color] = 1
                        self.mib[oid_time] = min_green 
                    else: # VERMELHO -> VERDE
                        self.mib[oid_color] = 2
                        self.mib[oid_time] = min_green
                else:
                    self.mib[oid_time] = max(0, round(current_time, 2))