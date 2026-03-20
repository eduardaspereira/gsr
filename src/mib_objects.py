"""
Módulo com as estruturas de dados que representam a MIB do sistema.
Define objetos, tabelas e tipos de dados da MIB em SMIv2.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple
from enum import IntEnum
from dataclasses import dataclass, field


class SimOperStatus(IntEnum):
    """Estados operacionais da simulação."""
    STOPPED = 1
    RUNNING = 2
    PAUSED = 3


class TrafficColor(IntEnum):
    """Cores dos semáforos."""
    RED = 1
    YELLOW = 2
    GREEN = 3


class RoadType(IntEnum):
    """Tipos de vias."""
    NORMAL = 1
    SINK = 2
    SOURCE = 3


class LinkState(IntEnum):
    """Estados das ligações entre vias."""
    INACTIVE = 1
    ACTIVE = 2


@dataclass
class TrafficGeneralObjects:
    """Objetos trafficGeneral da MIB."""
    simStatus: SimOperStatus = SimOperStatus.STOPPED
    simStepDuration: int = 5  # segundos
    simElapsedSeconds: int = 0
    globalVehicleCount: int = 0
    globalAvgWaitTime: float = 0.0
    totalEnteredVehicles: int = 0
    totalExitedVehicles: int = 0
    algoMinGreenTime: int = 15
    algoMaxGreenTime: int = 60
    algoYellowTime: int = 3
    currentAlgorithm: int = 1


@dataclass
class CrossroadEntry:
    """Entrada na tabela de cruzamentos."""
    crossroadIndex: int
    crossroadMode: int = 1  # normal = 1
    rowStatus: int = 1  # active


@dataclass
class RoadEntry:
    """Entrada na tabela de vias."""
    roadIndex: int
    roadName: str
    roadType: RoadType
    roadRTG: int  # Ritmo Gerador de Tráfego (veículos/minuto)
    roadMaxCapacity: int
    roadVehicleCount: int = 0
    roadTotalPassedCars: int = 0
    roadAvgWaitTime: float = 0.0
    roadCrossroadID: int = 0
    roadTLColor: TrafficColor = TrafficColor.RED
    roadTLTimeRemaining: int = 0
    roadTLGreenDuration: int = 30
    rowStatus: int = 1  # active


@dataclass
class RoadLinkEntry:
    """Entrada na tabela de ligações entre vias."""
    linkIndex: int
    linkSourceIndex: int
    linkDestIndex: int
    linkFlowRate: float = 0.0  # carros/segundo
    linkActive: LinkState = LinkState.ACTIVE
    linkPassedCars: int = 0
    linkOccupancyPercent: float = 0.0
    rowStatus: int = 1  # active


class TrafficMIB:
    """
    Representa a MIB do sistema de gestão de tráfego.
    Acesso thread-safe a todos os objetos.
    """
    
    # OIDs base da MIB
    MIB_OID = "1.3.6.1.3.2026"  # iso.org.dod.internet.experimental.2026
    
    def __init__(self):
        """Inicializa a MIB."""
        self.lock = threading.RLock()
        
        # Objetos trafficGeneral
        self.traffic_general = TrafficGeneralObjects()
        
        # Tabelas
        self.crossroads: Dict[int, CrossroadEntry] = {}
        self.roads: Dict[int, RoadEntry] = {}
        self.road_links: Dict[int, RoadLinkEntry] = {}
        
        # Mapeamentos para acesso rápido
        self._road_index_to_name: Dict[int, str] = {}
    
    # =========== TRAFFIC GENERAL OBJECTS ===========
    
    def get_sim_status(self) -> SimOperStatus:
        """Retorna estado da simulação."""
        with self.lock:
            return self.traffic_general.simStatus
    
    def set_sim_status(self, status: SimOperStatus):
        """Define estado da simulação."""
        with self.lock:
            self.traffic_general.simStatus = SimOperStatus(status)
    
    def get_sim_step_duration(self) -> int:
        """Retorna duração do passo de simulação (segundos)."""
        with self.lock:
            return self.traffic_general.simStepDuration
    
    def set_sim_step_duration(self, duration: int):
        """Define duração do passo de simulação."""
        with self.lock:
            if duration > 0:
                self.traffic_general.simStepDuration = duration
            else:
                raise ValueError("simStepDuration deve ser positivo")
    
    def get_sim_elapsed_seconds(self) -> int:
        """Retorna tempo total decorrido da simulação."""
        with self.lock:
            return self.traffic_general.simElapsedSeconds
    
    def increment_elapsed_time(self, seconds: int):
        """Incrementa o tempo decorrido."""
        with self.lock:
            self.traffic_general.simElapsedSeconds += seconds
    
    def get_global_vehicle_count(self) -> int:
        """Retorna número total de veículos na rede."""
        with self.lock:
            return self.traffic_general.globalVehicleCount
    
    def set_global_vehicle_count(self, count: int):
        """Define número total de veículos (calculado internamente)."""
        with self.lock:
            self.traffic_general.globalVehicleCount = max(0, count)
    
    def get_global_avg_wait_time(self) -> float:
        """Retorna tempo médio de espera global."""
        with self.lock:
            return self.traffic_general.globalAvgWaitTime
    
    def set_global_avg_wait_time(self, time: float):
        """Define tempo médio de espera global."""
        with self.lock:
            self.traffic_general.globalAvgWaitTime = max(0.0, time)
    
    def get_total_entered_vehicles(self) -> int:
        """Retorna total acumulado de veículos que entraram."""
        with self.lock:
            return self.traffic_general.totalEnteredVehicles
    
    def increment_entered_vehicles(self, count: int = 1):
        """Incrementa contador de veículos entrados."""
        with self.lock:
            self.traffic_general.totalEnteredVehicles += count
    
    def get_total_exited_vehicles(self) -> int:
        """Retorna total acumulado de veículos que saíram."""
        with self.lock:
            return self.traffic_general.totalExitedVehicles
    
    def increment_exited_vehicles(self, count: int = 1):
        """Incrementa contador de veículos saídos."""
        with self.lock:
            self.traffic_general.totalExitedVehicles += count
    
    def get_algo_min_green_time(self) -> int:
        """Retorna limite mínimo de verde no algoritmo."""
        with self.lock:
            return self.traffic_general.algoMinGreenTime
    
    def set_algo_min_green_time(self, time: int):
        """Define limite mínimo de verde."""
        with self.lock:
            if time > 0 and time <= self.traffic_general.algoMaxGreenTime:
                self.traffic_general.algoMinGreenTime = time
    
    def get_algo_max_green_time(self) -> int:
        """Retorna limite máximo de verde no algoritmo."""
        with self.lock:
            return self.traffic_general.algoMaxGreenTime
    
    def set_algo_max_green_time(self, time: int):
        """Define limite máximo de verde."""
        with self.lock:
            if time > 0 and time >= self.traffic_general.algoMinGreenTime:
                self.traffic_general.algoMaxGreenTime = time
    
    def get_algo_yellow_time(self) -> int:
        """Retorna tempo fixo de amarelo."""
        with self.lock:
            return self.traffic_general.algoYellowTime
    
    def get_current_algorithm(self) -> int:
        """Retorna algoritmo atual (1=FixedCycle, 2=Occupancy, ...)."""
        with self.lock:
            return self.traffic_general.currentAlgorithm
    
    def set_current_algorithm(self, algo: int):
        """Define algoritmo atual."""
        with self.lock:
            if 1 <= algo <= 4:
                self.traffic_general.currentAlgorithm = algo
    
    # =========== CROSSROAD TABLE ===========
    
    def add_crossroad(self, cr_data: Dict) -> bool:
        """Adiciona um cruzamento à tabela."""
        with self.lock:
            idx = cr_data.get("crossroadIndex")
            if idx in self.crossroads:
                return False
            
            self.crossroads[idx] = CrossroadEntry(
                crossroadIndex=idx,
                crossroadMode=cr_data.get("crossroadMode", 1)
            )
            return True
    
    def get_crossroad(self, index: int) -> Optional[CrossroadEntry]:
        """Retorna cruzamento por índice."""
        with self.lock:
            return self.crossroads.get(index)
    
    def get_all_crossroads(self) -> List[CrossroadEntry]:
        """Retorna lista de todos os cruzamentos."""
        with self.lock:
            return list(self.crossroads.values())
    
    # =========== ROAD TABLE ===========
    
    def add_road(self, road_data: Dict) -> bool:
        """Adiciona uma via à tabela."""
        with self.lock:
            idx = road_data.get("roadIndex")
            if idx in self.roads:
                return False
            
            self.roads[idx] = RoadEntry(
                roadIndex=idx,
                roadName=road_data.get("roadName", f"Road {idx}"),
                roadType=RoadType(road_data.get("roadType", 1)),
                roadRTG=road_data.get("roadRTG", 0),
                roadMaxCapacity=road_data.get("roadMaxCapacity", 100),
                roadVehicleCount=road_data.get("roadVehicleCount", 0),
                roadCrossroadID=road_data.get("roadCrossroadID", 0)
            )
            self._road_index_to_name[idx] = self.roads[idx].roadName
            return True
    
    def get_road(self, index: int) -> Optional[RoadEntry]:
        """Retorna via por índice."""
        with self.lock:
            return self.roads.get(index)
    
    def get_all_roads(self) -> List[RoadEntry]:
        """Retorna lista de todas as vias."""
        with self.lock:
            return list(self.roads.values())
    
    def get_vehicle_count(self, road_index: int) -> int:
        """Retorna número de veículos numa via."""
        with self.lock:
            road = self.roads.get(road_index)
            return road.roadVehicleCount if road else 0
    
    def set_vehicle_count(self, road_index: int, count: int) -> bool:
        """Define número de veículos numa via."""
        with self.lock:
            road = self.roads.get(road_index)
            if road and 0 <= count <= road.roadMaxCapacity:
                road.roadVehicleCount = count
                return True
            return False
    
    def increment_vehicle_count(self, road_index: int, count: int = 1) -> bool:
        """Incrementa número de veículos numa via."""
        with self.lock:
            road = self.roads.get(road_index)
            if road:
                new_count = road.roadVehicleCount + count
                if 0 <= new_count <= road.roadMaxCapacity:
                    road.roadVehicleCount = new_count
                    return True
            return False
    
    def get_traffic_light_color(self, road_index: int) -> Optional[TrafficColor]:
        """Retorna cor do semáforo de uma via."""
        with self.lock:
            road = self.roads.get(road_index)
            return road.roadTLColor if road else None
    
    def set_traffic_light_color(self, road_index: int, color: TrafficColor) -> bool:
        """Define cor do semáforo de uma via."""
        with self.lock:
            road = self.roads.get(road_index)
            if road:
                road.roadTLColor = TrafficColor(color)
                return True
            return False
    
    def get_traffic_light_time_remaining(self, road_index: int) -> int:
        """Retorna segundos restantes até trocar cor."""
        with self.lock:
            road = self.roads.get(road_index)
            return road.roadTLTimeRemaining if road else 0
    
    def set_traffic_light_time_remaining(self, road_index: int, seconds: int) -> bool:
        """Define segundos restantes até trocar cor."""
        with self.lock:
            road = self.roads.get(road_index)
            if road:
                road.roadTLTimeRemaining = max(0, seconds)
                return True
            return False
    
    def set_green_duration(self, road_index: int, seconds: int) -> bool:
        """Define duração do verde atribuída pelo SD."""
        with self.lock:
            road = self.roads.get(road_index)
            if road:
                road.roadTLGreenDuration = max(0, seconds)
                return True
            return False
    
    # =========== ROAD LINK TABLE ===========
    
    def add_road_link(self, link_data: Dict) -> bool:
        """Adiciona uma ligação entre vias."""
        with self.lock:
            idx = link_data.get("linkIndex")
            if idx in self.road_links:
                return False
            
            self.road_links[idx] = RoadLinkEntry(
                linkIndex=idx,
                linkSourceIndex=link_data.get("linkSourceIndex"),
                linkDestIndex=link_data.get("linkDestIndex"),
                linkActive=LinkState(link_data.get("linkActive", 2))
            )
            return True
    
    def get_road_link(self, index: int) -> Optional[RoadLinkEntry]:
        """Retorna ligação por índice."""
        with self.lock:
            return self.road_links.get(index)
    
    def get_all_road_links(self) -> List[RoadLinkEntry]:
        """Retorna lista de todas as ligações."""
        with self.lock:
            return list(self.road_links.values())
    
    def get_links_from_road(self, road_index: int) -> List[RoadLinkEntry]:
        """Retorna ligações que partem de uma via."""
        with self.lock:
            return [link for link in self.road_links.values() 
                   if link.linkSourceIndex == road_index]
    
    def get_links_to_road(self, road_index: int) -> List[RoadLinkEntry]:
        """Retorna ligações que chegam a uma via."""
        with self.lock:
            return [link for link in self.road_links.values() 
                   if link.linkDestIndex == road_index]
    
    def increment_passed_cars_link(self, link_index: int, count: int = 1) -> bool:
        """Incrementa contador de carros passados numa ligação."""
        with self.lock:
            link = self.road_links.get(link_index)
            if link:
                link.linkPassedCars += count
                return True
            return False
