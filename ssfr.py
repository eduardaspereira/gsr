class SistemaSimulacao:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        # Acumuladores para lidar com frações de veículos por segundo
        self.accumulators = {r['id']: 0.0 for r in config['roads']}

    def run_step(self, duration):
        # 1. Geração de veículos por RTG (Vias de entrada) 
        for road in self.cfg['roads']:
            rid = road['id']
            rtg = self.mib.get(f"{self.base}.3.1.4.{rid}", 0)
            if rtg > 0:
                self.accumulators[rid] += (rtg / 60.0) * duration
                if self.accumulators[rid] >= 1.0:
                    added = int(self.accumulators[rid])
                    current = self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
                    capacity = self.mib.get(f"{self.base}.3.1.5.{rid}", 999)
                    # Só adiciona se houver espaço [cite: 46]
                    if current + added <= capacity:
                        self.mib[f"{self.base}.3.1.6.{rid}"] = current + added
                    self.accumulators[rid] -= added

        # 2. Movimentação entre vias (Através de Links e Semáforos) [cite: 45, 52]
        for link in self.cfg['links']:
            src, dest = link['src'], link['dest']
            # Verifica a cor do semáforo da via de origem [cite: 52]
            # OID: trafficLightTable.trafficLightEntry.tlColor.roadIndex
            color = self.mib.get(f"{self.base}.4.1.3.{src}", 1) # Default: Red
            
            if color in [2, 3]: # Green (2) ou Yellow (3) permitem passagem [cite: 79]
                v_src = self.mib.get(f"{self.base}.3.1.6.{src}", 0)
                v_dest = self.mib.get(f"{self.base}.3.1.6.{dest}", 0)
                cap_dest = self.mib.get(f"{self.base}.3.1.5.{dest}", 999)
                
                # Fluxo baseado no linkFlowRate (veíc/min) [cite: 46]
                flow_rate = link.get('flowRate', 10)
                cars_to_move = int((flow_rate / 60.0) * duration)
                if cars_to_move < 1 and v_src > 0: cars_to_move = 1 # Garante movimento mínimo

                actual_move = min(v_src, cars_to_move, cap_dest - v_dest)
                if actual_move > 0:
                    self.mib[f"{self.base}.3.1.6.{src}"] = v_src - actual_move
                    self.mib[f"{self.base}.3.1.6.{dest}"] = v_dest + actual_move