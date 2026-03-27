import asyncio
import random

class SistemaSimulacao:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        self.accumulators = {r['id']: 0.0 for r in config['roads']}

    async def start(self):
        print("[SSFR] Motor de Geração e Distribuição iniciado.")
        dt = 0.5 
        while True:
            await asyncio.sleep(dt)
            self.run_step(dt)

    def run_step(self, duration):
        # 1. Geração por RTG
        for road in self.cfg['roads']:
            rid = road['id']
            rtg = self.mib.get(f"{self.base}.3.1.4.{rid}", 0)
            if rtg > 0:
                if self.mib.get(f"{self.base}.4.1.3.{rid}", 2) == 3:
                    rtg = rtg / 2.0
                self.accumulators[rid] += (rtg / 60.0) * duration
                if self.accumulators[rid] >= 1.0:
                    added = int(self.accumulators[rid])
                    current = self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
                    capacity = self.mib.get(f"{self.base}.3.1.5.{rid}", 999)
                    if current + added <= capacity:
                        self.mib[f"{self.base}.3.1.6.{rid}"] = current + added
                    self.accumulators[rid] -= added

        # 2. Distribuição / Viragens nos Cruzamentos
        # Agrupa os links por origem para processar vias com multiplos destinos
        links_by_src = {}
        for link in self.cfg.get('links', []):
            links_by_src.setdefault(link['src'], []).append(link)

        for src, links in links_by_src.items():
            color = self.mib.get(f"{self.base}.4.1.3.{src}", 1) 
            
            # Passa no Verde (2) ou Amarelo (3)
            if color in [2, 3]: 
                v_src = self.mib.get(f"{self.base}.3.1.6.{src}", 0)
                if v_src > 0:
                    # Determina quantos carros passam no total neste 'tick'
                    total_flow = sum(l.get('flowRate', 10) for l in links)
                    cars_to_move = max(1, int((total_flow / 60.0) * duration))
                    actual_move = min(v_src, cars_to_move)

                    if actual_move > 0:
                        self.mib[f"{self.base}.3.1.6.{src}"] -= actual_move
                        
                        # Distribui os carros que passaram pelos destinos disponíveis
                        for _ in range(actual_move):
                            # Escolhe o destino baseado na probabilidade do flowRate (Roleta)
                            rand = random.uniform(0, total_flow)
                            acumulado = 0
                            for link in links:
                                acumulado += link.get('flowRate', 10)
                                if rand <= acumulado:
                                    dest = link['dest']
                                    # 1. Atualiza contador da Via Destino
                                    v_dest = self.mib.get(f"{self.base}.3.1.6.{dest}", 0)
                                    self.mib[f"{self.base}.3.1.6.{dest}"] = v_dest + 1
                                    
                                    # 2. Atualiza o contador de Passagens Específicas (Avisa a CMC da viragem!)
                                    link_oid = f"{self.base}.5.1.4.{src}.{dest}"
                                    self.mib[link_oid] = self.mib.get(link_oid, 0) + 1
                                    break