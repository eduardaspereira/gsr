class SistemaDecisao:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        # Inicialização dos estados dos semáforos [cite: 89]
        for tl in config['trafficLights']:
            rid = tl['roadIndex']
            # Inicializa: Eixo EW (2) como Green, Eixo NS (1) como Red
            self.mib[f"{self.base}.4.1.3.{rid}"] = 2 if tl['axis'] == 2 else 1
            self.mib[f"{self.base}.4.1.4.{rid}"] = 15 # Tempo inicial

    def update(self):
        duration = self.mib.get(f"{self.base}.1.2.0", 5)
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        min_green = self.mib.get(f"{self.base}.1.4.0", 15)

        for tl in self.cfg['trafficLights']:
            rid = tl['roadIndex']
            oid_time = f"{self.base}.4.1.4.{rid}"
            oid_color = f"{self.base}.4.1.3.{rid}"
            
            time_left = self.mib.get(oid_time, 0) - duration
            
            if time_left <= 0:
                curr_color = self.mib.get(oid_color, 1)
                # Máquina de Estados: Green (2) -> Yellow (3) -> Red (1) -> Green (2)
                if curr_color == 2: # Green -> Yellow
                    self.mib[oid_color] = 3
                    time_left = yellow_time
                elif curr_color == 3: # Yellow -> Red
                    self.mib[oid_color] = 1
                    time_left = min_green # Simplificação: Red dura o mesmo que Green
                else: # Red -> Green
                    self.mib[oid_color] = 2
                    time_left = min_green
            
            self.mib[oid_time] = max(0, time_left)  