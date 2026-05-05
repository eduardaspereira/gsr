import asyncio
import random

class SistemaSimulacao:
    def __init__(self, shared_mib, config):
        self.mib = shared_mib
        self.cfg = config
        self.base = "1.3.6.1.3.2026.1"
        # Acumulador para a entrada de carros (RTG) nas Vias
        self.in_accumulators = {r['id']: 0.0 for r in config['roads']}
        # Acumulador para o escoamento dos Semáforos (Origens)
        self.out_accumulators = {r['id']: 0.0 for r in config['roads']}

    async def start(self):
        print("[SSFR] Motor de Geração e Distribuição iniciado.")
        dt = 0.5 
        while True:
            await asyncio.sleep(dt)
            self.run_step(dt)

    def run_step(self, duration):
        # ====================================================================
        # 1. GERAÇÃO DE TRÁFEGO (Entrada de tráfego de fora do mapa)
        # ====================================================================
        for road in self.cfg['roads']:
            rid = road['id']
            rtg = self.mib.get(f"{self.base}.3.1.4.{rid}", 0)
            if rtg > 0:
                if self.mib.get(f"{self.base}.4.1.3.{rid}", 2) == 2:
                    rtg = rtg / 2.0 # Abranda no amarelo
                
                self.in_accumulators[rid] += (rtg / 60.0) * duration
                
                if self.in_accumulators[rid] >= 1.0:
                    added = int(self.in_accumulators[rid])
                    current = self.mib.get(f"{self.base}.3.1.6.{rid}", 0)
                    capacity = self.mib.get(f"{self.base}.3.1.5.{rid}", 999)
                    
                    if current + added <= capacity:
                        self.mib[f"{self.base}.3.1.6.{rid}"] = current + added
                    
                    self.in_accumulators[rid] -= added

        # ====================================================================
        # 2. DISTRIBUIÇÃO E ESCOAMENTO NOS CRUZAMENTOS
        # ====================================================================
        links_by_src = {}
        for link in self.cfg.get('links', []):
            links_by_src.setdefault(link['src'], []).append(link)

        # Iteramos sobre todas as vias para garantir que até as vias de Saída são processadas
        for road in self.cfg['roads']:
            src = road['id']
            links = links_by_src.get(src, [])
            
            # ===== CASO 1: Via de Saída da Rede (Sem links de destino) =====
            if len(links) == 0:
                v_src = self.mib.get(f"{self.base}.3.1.6.{src}", 0)
                if v_src > 0:
                    # Usa o roadMaxCapacity (ou um RTG de saída) como ritmo de escoamento.
                    # Exemplo: Assume que uma saída escoa 60 carros por minuto por defeito.
                    exit_flow = self.mib.get(f"{self.base}.3.1.4.{src}", 60) 
                    
                    self.out_accumulators[src] += (exit_flow / 60.0) * duration
                    
                    if self.out_accumulators[src] >= 1.0:
                        cars_to_exit = int(self.out_accumulators[src])
                        actual_exit = min(v_src, cars_to_exit)
                        
                        if actual_exit > 0:
                            # Carros saem diretamente (sem destino, sem backpressure)
                            self.mib[f"{self.base}.3.1.6.{src}"] -= actual_exit
                            # Decrementa apenas pelos carros que realmente saíram
                            self.out_accumulators[src] -= actual_exit
            
            # ===== CASO 2: Via Normal com Semáforo e Destinos =====
            else:
                color = self.mib.get(f"{self.base}.4.1.3.{src}", 1) 
                
                # Só passa se a luz estiver Verde (2) ou Amarela (3)
                if color in [2, 3]: 
                    v_src = self.mib.get(f"{self.base}.3.1.6.{src}", 0)
                    if v_src > 0:
                        # O ritmo do semáforo é a soma de todos os fluxos possíveis
                        total_flow = sum(l.get('flowRate', 10) for l in links)
                        
                        self.out_accumulators[src] += (total_flow / 60.0) * duration
                        
                        if self.out_accumulators[src] >= 1.0:
                            cars_to_move = int(self.out_accumulators[src])
                            actual_move = min(v_src, cars_to_move)

                            if actual_move > 0:
                                # 1. Retira os carros da via de origem (vão passar o semáforo)
                                self.mib[f"{self.base}.3.1.6.{src}"] -= actual_move
                                
                                # 2. Distribui cada carro (Roleta) e verifica Backpressure
                                # Conta quantos realmente conseguem passar (sem spillback)
                                cars_actually_moved = 0
                                
                                for _ in range(actual_move):
                                    rand = random.uniform(0, total_flow)
                                    acumulado = 0
                                    for link in links:
                                        acumulado += link.get('flowRate', 10)
                                        if rand <= acumulado:
                                            dest = link['dest']
                                            
                                            v_dest = self.mib.get(f"{self.base}.3.1.6.{dest}", 0)
                                            cap_dest = self.mib.get(f"{self.base}.3.1.5.{dest}", 999)

                                            if v_dest < cap_dest:
                                                # Cabe na rua! Segue viagem.
                                                self.mib[f"{self.base}.3.1.6.{dest}"] = v_dest + 1
                                                
                                                # Atualiza estatística de viragem
                                                link_oid = f"{self.base}.5.1.4.{src}.{dest}"
                                                self.mib[link_oid] = self.mib.get(link_oid, 0) + 1
                                                
                                                # Marca como movido com sucesso
                                                cars_actually_moved += 1
                                            else:
                                                # Rua cheia! Spillback. O carro bate no trânsito e é devolvido.
                                                self.mib[f"{self.base}.3.1.6.{src}"] += 1
                                            
                                            break # Carro tratado
                                
                                # Decrementa acumulador APENAS pelos carros que realmente passaram
                                # Os que deram spillback voltam à origem e "compensam" o acumulador
                                self.out_accumulators[src] -= cars_actually_moved