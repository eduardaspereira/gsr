import asyncio

class SistemaDecisaoOcupacao:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        # Não precisamos de estado interno complexo, pois ele lê tudo da MIB em tempo real

    async def start(self):
        print("[SD-HEUR] Algoritmo de Ocupação (Heurística) preparado.")

    # Adicionado os argumentos para sincronizar com o sc.py
    async def update(self, current_step=None, fast_forward_step=None):
        # 1. Determina o passo de tempo
        step = current_step if current_step is not None else fast_forward_step
        if step is None: step = 0.5
        
        yellow_time = self.mib.get(f"{self.base}.1.5.0", 3)
        min_green = self.mib.get(f"{self.base}.1.4.0", 10)
        
        # 2. Varre todos os cruzamentos
        for cr in self.cfg['crossroads']:
            cr_id = cr['id']
            # Filtra os semáforos deste cruzamento (usa crID ou tlCrossroadID conforme o teu config)
            semaforos = [tl for tl in self.cfg['trafficLights'] if tl.get('crID') == cr_id or tl.get('tlCrossroadID') == cr_id]
            
            for tl in semaforos:
                rid = tl['roadIndex']
                oid_time = f"{self.base}.4.1.4.{rid}"
                oid_color = f"{self.base}.4.1.3.{rid}"
                oid_count = f"{self.base}.3.1.6.{rid}" 

                current_time_rem = self.mib.get(oid_time, 0) - step
                curr_color = self.mib.get(oid_color, 1)

                if current_time_rem <= 0:
                    if curr_color == 2: # Terminou o Verde -> Amarelo
                        self.mib[oid_color] = 3
                        self.mib[oid_time] = yellow_time
                        
                    elif curr_color == 3: # Terminou o Amarelo -> Vermelho
                        self.mib[oid_color] = 1
                        self.mib[oid_time] = 10 # Tempo de espera padrão no vermelho
                        
                    else: # Estava Vermelho -> Vai passar a Verde
                        # --- CÁLCULO HEURÍSTICO ---
                        carros_na_fila = self.mib.get(oid_count, 0)
                        
                        # Lógica: 2 segundos por cada carro + base de 10s
                        # Se houver 20 carros, dá 40s de verde.
                        tempo_calculado = max(min_green, carros_na_fila * 2)
                        
                        # Limite máximo de segurança (ex: 60s) para não bloquear o cruzamento
                        tempo_calculado = min(60, tempo_calculado)
                        
                        self.mib[oid_color] = 2 # Verde
                        self.mib[oid_time] = tempo_calculado
                        
                        if carros_na_fila > 0:
                            print(f"⚖️ [HEUR] Via {rid}: {carros_na_fila} carros -> Verde por {tempo_calculado}s")
                else:
                    # Apenas atualiza o tempo restante na MIB
                    self.mib[oid_time] = max(0, current_time_rem)