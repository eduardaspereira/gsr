"""
Sistema de Simulação do Fluxo Rodoviário (SSFR).
Simula movimento de veículos entre vias respeitando semáforos e capacidades.

Responsabilidades:
- Injetar veículos em vias-fonte (RGT)
- Mover veículos entre vias respeitando semáforos
- Atualizar contadores e métricas na MIB
- Thread de simulação com passo configurável
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import IntEnum

from src.mib_objects import TrafficMIB, TrafficColor, RoadType

logger = logging.getLogger(__name__)


@dataclass
class Vehicle:
    """Representa um veículo na rede."""
    vehicle_id: int
    entry_time: float  # timestamp quando entrou na rede
    current_road: int  # índice da via atual
    wait_time: float = 0.0  # tempo acumulado em espera


class TrafficFlowSimulator:
    """
    Simulador de fluxo de tráfego rodoviário.
    Executa em thread separada, atualizando MIB a cada passo.
    """
    
    def __init__(self, mib: TrafficMIB):
        """
        Inicializa o simulador.
        
        Args:
            mib: Instância da MIB a atualizar
        """
        self.mib = mib
        self.running = False
        self.thread = None
        
        # Veículos por via (road_index -> list de Vehicle)
        self.vehicles_by_road: Dict[int, List[Vehicle]] = defaultdict(list)
        
        # Contador de IDs de veículos
        self.next_vehicle_id = 1
        
        # Métricas de simulação
        self.total_wait_time = 0.0  # para cálculo de média
        self.simulation_step = 0
        
        logger.info("SSFR Simulator inicializado")
    
    def start(self):
        """Inicia a thread de simulação."""
        if self.running:
            logger.warning("SSFR já está em execução")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._simulation_loop, daemon=False)
        self.thread.start()
        logger.info("✓ SSFR thread iniciada")
    
    def stop(self):
        """Para a thread de simulação."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ SSFR thread parada")
    
    def _simulation_loop(self):
        """Loop principal de simulação (bloqueante)."""
        logger.info("SSFR loop started")
        
        try:
            while self.running:
                step_duration = self.mib.get_sim_step_duration()
                
                # Executa passo de simulação
                self._simulate_step()
                
                # Incrementa tempo decorrido
                self.mib.increment_elapsed_time(step_duration)
                self.simulation_step += 1
                
                # Log de debug a cada 10 passos (~50 segundos)
                if self.simulation_step % 10 == 0:
                    total_vehicles = sum(len(v) for v in self.vehicles_by_road.values())
                    logger.debug(f"[Step {self.simulation_step}] "
                               f"Veículos na rede: {total_vehicles}, "
                               f"Tempo: {self.mib.get_sim_elapsed_seconds()}s")
                
                # Dorme até próximo passo
                time.sleep(step_duration)
        
        except Exception as e:
            logger.error(f"Erro no SSFR loop: {e}", exc_info=True)
        finally:
            logger.info("SSFR loop ended")
    
    def _simulate_step(self):
        """Executa um passo de simulação."""
        try:
            # 1. Injetar novos veículos em vias-fonte
            self._inject_vehicles()
            
            # 2. Mover veículos entre vias
            self._move_vehicles()
            
            # 3. Remover veículos que saem da rede
            self._remove_exiting_vehicles()
            
            # 4. Atualizar métricas na MIB
            self._update_mib_metrics()
        
        except Exception as e:
            logger.error(f"Erro em passo de simulação: {e}", exc_info=True)
    
    def _inject_vehicles(self):
        """Injeta novos veículos em vias-fonte respeitando RGT."""
        current_time = time.time()
        step_duration = self.mib.get_sim_step_duration()
        
        for road in self.mib.get_all_roads():
            # Apenas vias-fonte injetam veículos
            if road.roadType != RoadType.SOURCE:
                continue
            
            rtg = road.roadRTG  # veículos por minuto
            
            # Converter RTG de veículos/minuto para veículos/passo_simulacao
            # RTG é em veículos/minuto, passo é em segundos
            vehicles_per_minuto = rtg
            vehicles_per_second = vehicles_per_minuto / 60.0
            vehicles_this_step = vehicles_per_second * step_duration
            
            # Injetar veículos (com rounding apropriado)
            num_to_inject = max(0, int(vehicles_this_step))
            
            # Testar se há espaço na via
            if (road.roadVehicleCount + num_to_inject) <= road.roadMaxCapacity:
                for _ in range(num_to_inject):
                    vehicle = Vehicle(
                        vehicle_id=self.next_vehicle_id,
                        entry_time=current_time,
                        current_road=road.roadIndex
                    )
                    self.next_vehicle_id += 1
                    
                    self.vehicles_by_road[road.roadIndex].append(vehicle)
                    self.mib.increment_entered_vehicles()
                
                if num_to_inject > 0:
                    logger.debug(f"Injetados {num_to_inject} veículos na via {road.roadIndex} "
                               f"(RTG={rtg} veic/min)")
            else:
                logger.debug(f"Via {road.roadIndex} cheia - não é possível injetar")
    
    def _move_vehicles(self):
        """Move veículos entre vias respeitando semáforos e capacidades."""
        step_duration = self.mib.get_sim_step_duration()
        current_time = time.time()
        
        # Processa cada via
        for road in self.mib.get_all_roads():
            if road.roadType == RoadType.SINK:
                # SINK não tem veículos que saem (saem da rede)
                continue
            
            vehicles = self.vehicles_by_road[road.roadIndex]
            
            if not vehicles:
                continue
            
            # Verificar cor do semáforo
            tl_color = road.roadTLColor
            
            if tl_color == TrafficColor.RED:
                # Semáforo vermelho - veículos esperam e acumulam wait_time
                for vehicle in vehicles:
                    vehicle.wait_time += step_duration
                continue
            
            # GREEN ou YELLOW - tentar mover veículos
            if tl_color in (TrafficColor.GREEN, TrafficColor.YELLOW):
                # Obter ligações desta via
                links = self.mib.get_links_from_road(road.roadIndex)
                
                if not links:
                    # Nenhuma ligação - via é dead-end ou sink
                    logger.warning(f"Via {road.roadIndex} não tem ligações de saída")
                    continue
                
                # Mover veículos para vias de destino
                # Simplificado: distribui igualmente entre ligações
                vehicles_to_move = min(len(vehicles), 10)  # max 10/passo
                
                for i, vehicle in enumerate(vehicles[:vehicles_to_move]):
                    # Escolher ligação (round-robin simples)
                    link_idx = i % len(links)
                    link = links[link_idx]
                    
                    dest_road = self.mib.get_road(link.linkDestIndex)
                    if not dest_road:
                        logger.error(f"Via destino {link.linkDestIndex} não existe")
                        continue
                    
                    # Verificar se há espaço na via destino
                    if dest_road.roadVehicleCount < dest_road.roadMaxCapacity:
                        # Mover veículo
                        vehicle.current_road = link.linkDestIndex
                        self.vehicles_by_road[link.linkDestIndex].append(vehicle)
                        self.mib.increment_passed_cars_link(link.linkIndex)
                        
                        logger.debug(f"Veículo {vehicle.vehicle_id}: "
                                   f"{road.roadIndex} → {link.linkDestIndex}")
                    else:
                        # Via destino cheia - backpressure: parar movimento
                        logger.debug(f"Via destino {link.linkDestIndex} cheia - parar")
                        vehicle.wait_time += step_duration
                        break
                
                # Remover veículos que foram movidos
                remaining = []
                moved_count = 0
                for vehicle in vehicles:
                    if vehicle.current_road == road.roadIndex:
                        remaining.append(vehicle)
                    else:
                        moved_count += 1
                
                self.vehicles_by_road[road.roadIndex] = remaining
                
                if moved_count > 0:
                    logger.debug(f"Movidos {moved_count} veículos da via {road.roadIndex}")
    
    def _remove_exiting_vehicles(self):
        """Remove veículos que saem da rede (via SINK)."""
        sinks = [r for r in self.mib.get_all_roads() if r.roadType == RoadType.SINK]
        
        for sink in sinks:
            vehicles = self.vehicles_by_road[sink.roadIndex]
            
            # Todos os veículos em SINK saem
            exiting = len(vehicles)
            
            if exiting > 0:
                self.mib.increment_exited_vehicles(exiting)
                self.total_wait_time += sum(v.wait_time for v in vehicles)
                
                logger.debug(f"{exiting} veículos saíram da rede via {sink.roadIndex}")
                
                # Limpar
                self.vehicles_by_road[sink.roadIndex] = []
    
    def _update_mib_metrics(self):
        """Atualiza métricas agregadas na MIB."""
        # Contar veículos totais
        total_vehicles = sum(len(v) for v in self.vehicles_by_road.values())
        self.mib.set_global_vehicle_count(total_vehicles)
        
        # Calcular tempo médio de espera
        all_vehicles = []
        for vehicles in self.vehicles_by_road.values():
            all_vehicles.extend(vehicles)
        
        if all_vehicles:
            avg_wait_time = sum(v.wait_time for v in all_vehicles) / len(all_vehicles)
            self.mib.set_global_avg_wait_time(avg_wait_time)
        else:
            self.mib.set_global_avg_wait_time(0.0)
        
        # Atualizar contadores de veículos em cada via
        for road in self.mib.get_all_roads():
            vehicle_count = len(self.vehicles_by_road[road.roadIndex])
            self.mib.set_vehicle_count(road.roadIndex, vehicle_count)
    
    def get_statistics(self) -> Dict:
        """Retorna estatísticas da simulação."""
        all_vehicles = []
        for vehicles in self.vehicles_by_road.values():
            all_vehicles.extend(vehicles)
        
        total_vehicles = len(all_vehicles)
        avg_wait_time = (sum(v.wait_time for v in all_vehicles) / total_vehicles 
                        if total_vehicles > 0 else 0.0)
        
        return {
            "vehicles_in_network": total_vehicles,
            "avg_wait_time": avg_wait_time,
            "total_entered": self.mib.get_total_entered_vehicles(),
            "total_exited": self.mib.get_total_exited_vehicles(),
            "simulation_steps": self.simulation_step,
            "elapsed_seconds": self.mib.get_sim_elapsed_seconds(),
        }
    
    def get_road_details(self, road_index: int) -> Dict:
        """Retorna detalhes de veículos numa via específica."""
        road = self.mib.get_road(road_index)
        if not road:
            return {}
        
        vehicles = self.vehicles_by_road[road_index]
        
        return {
            "road_index": road_index,
            "road_name": road.roadName,
            "vehicles_count": len(vehicles),
            "capacity": road.roadMaxCapacity,
            "occupancy_percent": (len(vehicles) / road.roadMaxCapacity * 100) if road.roadMaxCapacity > 0 else 0,
            "traffic_light": road.roadTLColor.name,
            "avg_wait_time": (sum(v.wait_time for v in vehicles) / len(vehicles) 
                            if vehicles else 0.0),
        }
