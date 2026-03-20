"""
Sistema de Decisão (SD) - Controlo de Semáforos.
Calcula tempos de verde/amarelo/vermelho para cada semáforo.

Algoritmos disponíveis:
1. FixedCycle - Tempo fixo (baseline)
2. OccupancyHeuristic - Proporcional à lotação de cada via
3. BackpressureControl - Verifica espaço na via destino
4. ReinforcementLearning - (opcional, versão simplificada)
"""

import logging
import threading
import time
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from enum import IntEnum

from src.mib_objects import TrafficMIB, TrafficColor

logger = logging.getLogger(__name__)


class AlgorithmType(IntEnum):
    """Tipos de algoritmos disponíveis."""
    FIXED_CYCLE = 1
    OCCUPANCY_HEURISTIC = 2
    BACKPRESSURE = 3
    REINFORCEMENT_LEARNING = 4


class Decision:
    """Decisão de semáforo para uma via."""
    
    def __init__(self, road_index: int, color: TrafficColor, duration: int):
        """
        Args:
            road_index: Índice da via
            color: Verde/amarelo/vermelho
            duration: Duração em segundos
        """
        self.road_index = road_index
        self.color = color
        self.duration = duration
    
    def __repr__(self):
        return f"Decision(road={self.road_index}, color={self.color.name}, dur={self.duration}s)"


class TrafficLightAlgorithm(ABC):
    """Classe base para algoritmos de controlo de semáforos."""
    
    def __init__(self, mib: TrafficMIB):
        """
        Args:
            mib: Instância da MIB
        """
        self.mib = mib
    
    @abstractmethod
    def calculate_decisions(self) -> List[Decision]:
        """
        Calcula decisões de semáforo para todas as vias.
        
        Returns:
            Lista de decisões (uma por via)
        """
        pass
    
    def _get_normal_roads(self) -> List:
        """Retorna vias normais (não source/sink)."""
        from src.mib_objects import RoadType
        return [r for r in self.mib.get_all_roads() if r.roadType == RoadType.NORMAL]
    
    def _get_input_roads(self) -> List:
        """Retorna vias de entrada que têm ligações saindo."""
        roads_with_links = set()
        for link in self.mib.get_all_road_links():
            roads_with_links.add(link.linkSourceIndex)
        
        roads = []
        for road in self.mib.get_all_roads():
            if road.roadIndex in roads_with_links:
                roads.append(road)
        
        return roads
    
    def _apply_decisions(self, decisions: List[Decision]):
        """Aplica decisões à MIB."""
        for decision in decisions:
            self.mib.set_traffic_light_color(decision.road_index, decision.color)
            self.mib.set_traffic_light_time_remaining(decision.road_index, decision.duration)
            self.mib.set_green_duration(decision.road_index, 
                                      decision.duration if decision.color == TrafficColor.GREEN else 0)


class FixedCycleAlgorithm(TrafficLightAlgorithm):
    """
    Algoritmo de baseline - ciclo fixo.
    Alterna GREEN/YELLOW/RED com tempos fixos para todas as vias.
    """
    
    def __init__(self, mib: TrafficMIB):
        super().__init__(mib)
        self.cycle_step = 0
        logger.info("FixedCycle Algorithm activated")
    
    def calculate_decisions(self) -> List[Decision]:
        """
        Ciclo: via0 GREEN, via1 RED → via1 GREEN, via0 RED, etc.
        """
        decisions = []
        roads = self._get_input_roads()
        
        if not roads:
            return decisions
        
        min_green = self.mib.get_algo_min_green_time()
        yellow_time = self.mib.get_algo_yellow_time()
        
        # Qual via tem GREEN neste ciclo
        green_road_idx = self.cycle_step % len(roads)
        
        for i, road in enumerate(roads):
            if i == green_road_idx:
                # Esta via fica GREEN
                decision = Decision(road.roadIndex, TrafficColor.GREEN, min_green)
                logger.debug(f"[FixedCycle] Via {road.roadIndex}: GREEN {min_green}s")
            else:
                # Outras vias ficam RED
                decision = Decision(road.roadIndex, TrafficColor.RED, min_green)
                logger.debug(f"[FixedCycle] Via {road.roadIndex}: RED")
            
            decisions.append(decision)
        
        self.cycle_step += 1
        return decisions


class OccupancyHeuristicAlgorithm(TrafficLightAlgorithm):
    """
    Algoritmo heurístico baseado em ocupação.
    Distribui tempo de GREEN proporcional ao número de veículos.
    """
    
    def __init__(self, mib: TrafficMIB):
        super().__init__(mib)
        logger.info("OccupancyHeuristic Algorithm activated")
    
    def calculate_decisions(self) -> List[Decision]:
        """
        Tempo verde proporcional à lotação da via.
        """
        decisions = []
        roads = self._get_input_roads()
        
        if not roads:
            return decisions
        
        min_green = self.mib.get_algo_min_green_time()
        max_green = self.mib.get_algo_max_green_time()
        
        # Calcular lotações
        total_vehicles = sum(r.roadVehicleCount for r in roads)
        
        if total_vehicles == 0:
            # Nenhum tráfego - todos GREEN igual
            for road in roads:
                decision = Decision(road.roadIndex, TrafficColor.GREEN, min_green)
                decisions.append(decision)
        else:
            # Distribuir tempo proporcional
            for road in roads:
                occupancy = road.roadVehicleCount / max(road.roadMaxCapacity, 1)
                proportion = road.roadVehicleCount / total_vehicles
                
                # Tempo entre min e max proporcional
                green_time = min_green + int((max_green - min_green) * proportion)
                
                decision = Decision(road.roadIndex, TrafficColor.GREEN, green_time)
                logger.debug(f"[Occupancy] Via {road.roadIndex}: GREEN {green_time}s "
                           f"(occ={occupancy:.1%})")
                decisions.append(decision)
        
        return decisions


class BackpressureAlgorithm(TrafficLightAlgorithm):
    """
    Algoritmo de backpressure.
    Verifica se há espaço na via destino antes de dar GREEN.
    """
    
    def __init__(self, mib: TrafficMIB):
        super().__init__(mib)
        logger.info("Backpressure Algorithm activated")
    
    def calculate_decisions(self) -> List[Decision]:
        """
        Se via destino está cheia → RED na via origem.
        Se há espaço → GREEN proporcional à lotação.
        """
        decisions = []
        roads = self._get_input_roads()
        
        if not roads:
            return decisions
        
        min_green = self.mib.get_algo_min_green_time()
        max_green = self.mib.get_algo_max_green_time()
        yellow_time = self.mib.get_algo_yellow_time()
        
        for road in roads:
            # Obter vias destino
            links = self.mib.get_links_from_road(road.roadIndex)
            
            if not links:
                # Sem destino - RED
                decision = Decision(road.roadIndex, TrafficColor.RED, min_green)
                logger.debug(f"[Backpressure] Via {road.roadIndex}: RED (sem destino)")
                decisions.append(decision)
                continue
            
            # Verificar espaço nas vias destino
            has_space = False
            avg_dest_occupancy = 0.0
            
            for link in links:
                dest_road = self.mib.get_road(link.linkDestIndex)
                if dest_road:
                    occupancy = dest_road.roadVehicleCount / max(dest_road.roadMaxCapacity, 1)
                    avg_dest_occupancy += occupancy
                    
                    if dest_road.roadVehicleCount < dest_road.roadMaxCapacity:
                        has_space = True
            
            avg_dest_occupancy /= len(links)
            
            if not has_space:
                # Backpressure! Via destino cheia - dar RED
                decision = Decision(road.roadIndex, TrafficColor.RED, min_green)
                logger.debug(f"[Backpressure] Via {road.roadIndex}: RED (backpressure, dest_occ={avg_dest_occupancy:.1%})")
            else:
                # Há espaço - dar GREEN
                # Mais tempo se há muitos veículos na origem
                origin_occupancy = road.roadVehicleCount / max(road.roadMaxCapacity, 1)
                green_time = min_green + int((max_green - min_green) * origin_occupancy)
                
                decision = Decision(road.roadIndex, TrafficColor.GREEN, green_time)
                logger.debug(f"[Backpressure] Via {road.roadIndex}: GREEN {green_time}s "
                           f"(orig_occ={origin_occupancy:.1%}, dest_occ={avg_dest_occupancy:.1%})")
            
            decisions.append(decision)
        
        return decisions


class DecisionSystem:
    """
    Sistema de Decisão - Controlo de semáforos.
    Executa em thread separada, atualiza cores dos semáforos.
    """
    
    def __init__(self, mib: TrafficMIB, algorithm_type: AlgorithmType = AlgorithmType.OCCUPANCY_HEURISTIC):
        """
        Inicializa o SD.
        
        Args:
            mib: Instância da MIB
            algorithm_type: Algoritmo a usar
        """
        self.mib = mib
        self.running = False
        self.thread = None
        
        # Selecionar algoritmo
        self.algorithm = self._create_algorithm(algorithm_type)
        self.algorithm_type = algorithm_type
        
        # Sincronização (múltiplo do passo da simulação)
        self.decision_interval_multiplier = 1  # A cada quantos passos recalcular?
        self.steps_since_last_decision = 0
        
        logger.info(f"DecisionSystem initialized com algoritmo {algorithm_type.name}")
    
    def _create_algorithm(self, algo_type: AlgorithmType) -> TrafficLightAlgorithm:
        """Factory para criar algoritmo."""
        if algo_type == AlgorithmType.FIXED_CYCLE:
            return FixedCycleAlgorithm(self.mib)
        elif algo_type == AlgorithmType.OCCUPANCY_HEURISTIC:
            return OccupancyHeuristicAlgorithm(self.mib)
        elif algo_type == AlgorithmType.BACKPRESSURE:
            return BackpressureAlgorithm(self.mib)
        else:
            logger.warning(f"Algoritmo {algo_type} desconhecido, usando OCCUPANCY_HEURISTIC")
            return OccupancyHeuristicAlgorithm(self.mib)
    
    def set_algorithm(self, algo_type: AlgorithmType):
        """Muda o algoritmo em tempo de execução."""
        old_algo = self.algorithm_type
        self.algorithm = self._create_algorithm(algo_type)
        self.algorithm_type = algo_type
        logger.info(f"Algoritmo mudado de {old_algo.name} para {algo_type.name}")
    
    def start(self):
        """Inicia a thread de decisão."""
        if self.running:
            logger.warning("DecisionSystem já está em execução")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._decision_loop, daemon=False)
        self.thread.start()
        logger.info("✓ DecisionSystem thread iniciada")
    
    def stop(self):
        """Para a thread de decisão."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ DecisionSystem thread parada")
    
    def _decision_loop(self):
        """Loop de tomada de decisões."""
        logger.info("DecisionSystem loop started")
        
        try:
            while self.running:
                step_duration = self.mib.get_sim_step_duration()
                
                # Incrementa contador
                self.steps_since_last_decision += 1
                
                # A cada N passos, recalcular decisões
                if self.steps_since_last_decision >= self.decision_interval_multiplier:
                    self._make_decisions()
                    self.steps_since_last_decision = 0
                
                # Dorme até próximo passo
                time.sleep(step_duration)
        
        except Exception as e:
            logger.error(f"Erro no DecisionSystem loop: {e}", exc_info=True)
        finally:
            logger.info("DecisionSystem loop ended")
    
    def _make_decisions(self):
        """Calcula e aplica decisões de semáforo."""
        try:
            decisions = self.algorithm.calculate_decisions()
            self.algorithm._apply_decisions(decisions)
            
            logger.debug(f"Decisões aplicadas: {len(decisions)} vias")
        
        except Exception as e:
            logger.error(f"Erro ao fazer decisões: {e}", exc_info=True)
    
    def force_decision_now(self):
        """Força recalculação imediata de decisões."""
        try:
            decisions = self.algorithm.calculate_decisions()
            self.algorithm._apply_decisions(decisions)
            self.steps_since_last_decision = 0
            logger.info("Decisões forçadas imediatamente")
        except Exception as e:
            logger.error(f"Erro ao forçar decisões: {e}", exc_info=True)
