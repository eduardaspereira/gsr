import asyncio

class SistemaDecisao:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        
        # Estrutura interna para gerir o ciclo dos cruzamentos
        self.crossroads = {}
        for c in config['crossroads']:
            self.crossroads[c['id']] = {
                'eixo_ativo': 2, # Começa a dar Verde ao Eixo 2 (Oeste-Este)
                'cor_eixo': 2,   # 2 = Verde
                'tempo_restante': self.mib.get(f"{self.base}.1.4.0", 15)
            }

    async def start(self):
        print("[SD] Componente de Decisão (Ciclo Fixo) iniciado.")
        while True:
            await asyncio.sleep(1) # Atualiza a cada segundo
            self.update()

    def update(self):
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        green_time = self.mib.get(f"{self.base}.1.4.0", 15)

        # 1. Máquina de Estados dos Cruzamentos
        for cr_id, cr in self.crossroads.items():
            cr['tempo_restante'] -= 1
            if cr['tempo_restante'] <= 0:
                if cr['cor_eixo'] == 2: # Verde passa a Amarelo
                    cr['cor_eixo'] = 3
                    cr['tempo_restante'] = yellow_time
                elif cr['cor_eixo'] == 3: # Amarelo passa a Verde (e troca o eixo)
                    cr['cor_eixo'] = 2
                    cr['tempo_restante'] = green_time
                    cr['eixo_ativo'] = 1 if cr['eixo_ativo'] == 2 else 2

        # 2. Refletir o estado na MIB para cada semáforo
        for tl in self.cfg['trafficLights']:
            rid = tl['roadIndex']
            crid = tl['crID']
            axis = tl['axis']
            
            cr = self.crossroads[crid]
            if axis == cr['eixo_ativo']:
                self.mib[f"{self.base}.4.1.3.{rid}"] = cr['cor_eixo']
            else:
                self.mib[f"{self.base}.4.1.3.{rid}"] = 1 # Vermelho para o eixo inativo