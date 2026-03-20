"""
Sistema Central (SC) - Gerenciador Principal de Tráfego.
Integra:
  - Parser de configuração
  - MIB e objectos SNMP
  - Servidor SNMP
  - Simulação de tráfego (futuro: SSFR e SD)
"""

import logging
import sys
import json
from pathlib import Path
from typing import Optional

from src.config_parser import ConfigParser
from src.mib_objects import TrafficMIB, SimOperStatus
from src.snmp_server import TrafficSNMPServer
from src.ssfr import TrafficFlowSimulator
from src.decision_system import DecisionSystem, AlgorithmType
from src.snmp_bridge import set_global_mib


# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrafficManagementSystem:
    """
    Sistema Central de Gestão de Tráfego.
    Responsável pela orquestração de componentes.
    """
    
    def __init__(self, config_path: Optional[str] = None, 
                 snmp_host: str = "127.0.0.1", snmp_port: int = 10161):
        """
        Inicializa o Sistema Central.
        
        Args:
            config_path: Caminho para ficheiro de configuração
            snmp_host: Host para servidor SNMP
            snmp_port: Porta para servidor SNMP
        """
        self.config_path = config_path or "config.json"
        self.snmp_host = snmp_host
        self.snmp_port = snmp_port
        
        self.config_parser = None
        self.mib = None
        self.snmp_server = None
        
        # Componentes de simulação
        self.ssfr = None  # Traffic Flow Simulator
        self.decision_system = None  # Traffic Light Decision System
        
        logger.info("=== Sistema Central de Gestão de Tráfego Inicializado ===")
    
    def load_configuration(self) -> bool:
        """
        Carrega e valida a configuração do sistema.
        
        Returns:
            True se sucesso, False caso contrário
        """
        logger.info(f"Carregando configuração de {self.config_path}...")
        
        try:
            self.config_parser = ConfigParser(self.config_path)
            config = self.config_parser.parse()
            
            logger.info("✓ Configuração carregada e validada com sucesso")
            logger.info(f"  - Vias: {len(self.config_parser.get_roads())}")
            logger.info(f"  - Cruzamentos: {len(self.config_parser.get_crossroads())}")
            logger.info(f"  - Ligações: {len(self.config_parser.get_road_links())}")
            
            return True
        
        except FileNotFoundError as e:
            logger.error(f"✗ Ficheiro não encontrado: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"✗ Erro JSON: {e}")
            return False
        except ValueError as e:
            logger.error(f"✗ Erro de validação: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Erro inesperado: {e}")
            return False
    
    def initialize_mib(self) -> bool:
        """
        Inicializa a MIB com dados da configuração.
        
        Returns:
            True se sucesso, False caso contrário
        """
        logger.info("Inicializando MIB...")
        
        try:
            self.mib = TrafficMIB()
            
            # Carrega parâmetros gerais
            tg = self.config_parser.get_traffic_general()
            self.mib.traffic_general.simStepDuration = tg.get("simStepDuration", 5)
            self.mib.traffic_general.algoMinGreenTime = tg.get("algoMinGreenTime", 15)
            self.mib.traffic_general.algoMaxGreenTime = tg.get("algoMaxGreenTime", 60)
            self.mib.traffic_general.algoYellowTime = tg.get("algoYellowTime", 3)
            self.mib.traffic_general.currentAlgorithm = tg.get("currentAlgorithm", 1)
            
            # Carrega cruzamentos
            for cr_data in self.config_parser.get_crossroads():
                self.mib.add_crossroad(cr_data)
            
            # Carrega vias
            for road_data in self.config_parser.get_roads():
                self.mib.add_road(road_data)
            
            # Carrega ligações
            for link_data in self.config_parser.get_road_links():
                self.mib.add_road_link(link_data)
            
            logger.info("✓ MIB inicializada com sucesso")
            logger.info(f"  - Cruzamentos: {len(self.mib.get_all_crossroads())}")
            logger.info(f"  - Vias: {len(self.mib.get_all_roads())}")
            logger.info(f"  - Ligações: {len(self.mib.get_all_road_links())}")
            
            # Compartilhar MIB globalmente
            set_global_mib(self.mib)
            
            return True
        
        except Exception as e:
            logger.error(f"✗ Erro ao inicializar MIB: {e}")
            return False
    
    def initialize_snmp_server(self) -> bool:
        """
        Inicializa o servidor SNMP.
        
        Returns:
            True se sucesso, False caso contrário
        """
        logger.info(f"Inicializando servidor SNMP em {self.snmp_host}:{self.snmp_port}...")
        
        try:
            self.snmp_server = TrafficSNMPServer(
                self.mib,
                host=self.snmp_host,
                port=self.snmp_port
            )
            logger.info("✓ Servidor SNMP inicializado com sucesso")
            return True
        
        except Exception as e:
            logger.error(f"✗ Erro ao inicializar servidor SNMP: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def initialize_simulators(self) -> bool:
        """
        Inicializa os simuladores (SSFR e SD).
        
        Returns:
            True se sucesso, False caso contrário
        """
        logger.info("Inicializando simuladores de tráfego...")
        
        try:
            # Inicializar SSFR
            self.ssfr = TrafficFlowSimulator(self.mib)
            logger.info("✓ SSFR (Traffic Flow Simulator) inicializado")
            
            # Inicializar DecisionSystem
            algo_type = AlgorithmType(self.mib.get_current_algorithm())
            self.decision_system = DecisionSystem(self.mib, algo_type)
            logger.info(f"✓ DecisionSystem iniciado com algoritmo {algo_type.name}")
            
            return True
        
        except Exception as e:
            logger.error(f"✗ Erro ao inicializar simuladores: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def startup(self) -> bool:
        """
        Executa sequência completa de inicialização.
        
        Returns:
            True se sucesso, False caso contrário
        """
        logger.info("\n=== Iniciando Sistema Central ===\n")
        
        # Passo 1: Carregue configuração
        if not self.load_configuration():
            logger.error("Falha ao carregar configuração. Abortando.")
            return False
        
        # Passo 2: Inicialize MIB
        if not self.initialize_mib():
            logger.error("Falha ao inicializar MIB. Abortando.")
            return False
        
        # Passo 3: Inicialize servidor SNMP
        if not self.initialize_snmp_server():
            logger.error("Falha ao inicializar servidor SNMP. Abortando.")
            return False
        
        # Passo 4: Inicialize simuladores (SSFR + SD)
        if not self.initialize_simulators():
            logger.error("Falha ao inicializar simuladores. Abortando.")
            return False
        
        logger.info("\n=== Sistema Central Pronto ===\n")
        return True
    
    def run(self):
        """Inicia o sistema (bloqueante)."""
        if not self.startup():
            sys.exit(1)
        
        # Iniciar simuladores
        logger.info("\nIniciando simuladores...")
        self.ssfr.start()
        self.decision_system.start()
        
        logger.info("Simuladores em execução. Pressione Ctrl+C para parar.\n")
        
        try:
            # Inicia servidor SNMP (bloqueante)
            self.snmp_server.run()
        except KeyboardInterrupt:
            logger.info("\nParando sistema...")
            self.stop()
    
    def stop(self):
        """Para todos os componentes do sistema."""
        logger.info("Parando componentes...")
        
        if self.ssfr:
            self.ssfr.stop()
        
        if self.decision_system:
            self.decision_system.stop()
        
        if self.snmp_server:
            self.snmp_server.stop()
        
        logger.info("✓ Sistema parado")
    
    def print_status_detailed(self):
        """Imprime status detalhado do sistema com estatísticas."""
        if not self.ssfr:
            logger.warning("Sistema não iniciado")
            return
        
        logger.info("\n" + "="*60)
        logger.info("STATUS DETALHADO DO SISTEMA")
        logger.info("="*60)
        
        # Estatísticas gerais
        stats = self.ssfr.get_statistics()
        logger.info(f"\nESTATÍSTICAS GERAIS:")
        logger.info(f"  Passo de simulação: {stats['simulation_steps']}")
        logger.info(f"  Tempo decorrido: {stats['elapsed_seconds']}s")
        logger.info(f"  Veículos na rede: {stats['vehicles_in_network']}")
        logger.info(f"  Tempo médio espera: {stats['avg_wait_time']:.1f}s")
        logger.info(f"  Total entering: {stats['total_entered']}")
        logger.info(f"  Total exiting: {stats['total_exited']}")
        
        # Detalhes por via
        logger.info(f"\nDETALHES POR VIA:")
        for road in self.mib.get_all_roads():
            road_details = self.ssfr.get_road_details(road.roadIndex)
            if road_details:
                logger.info(f"  [{road.roadIndex}] {road_details['road_name']}")
                logger.info(f"      Veículos: {road_details['vehicles_count']}/{road_details['capacity']} ({road_details['occupancy_percent']:.0f}%)")
                logger.info(f"      Semáforo: {road_details['traffic_light']}")
                logger.info(f"      Tempo médio espera: {road_details['avg_wait_time']:.1f}s")
        
        logger.info("="*60 + "\n")
    
    def print_system_status(self):
        """Imprime status atual do sistema."""
        if not self.mib:
            logger.warning("Sistema não inicializado")
            return
        
        logger.info("\n" + "-"*60)
        logger.info("STATUS DO SISTEMA")
        logger.info("-"*60)
        logger.info(f"Simulação: {self.mib.get_sim_status().name}")
        logger.info(f"Tempo decorrido: {self.mib.get_sim_elapsed_seconds()}s")
        logger.info(f"Veículos na rede: {self.mib.get_global_vehicle_count()}")
        logger.info(f"Entrados: {self.mib.get_total_entered_vehicles()}")
        logger.info(f"Saídos: {self.mib.get_total_exited_vehicles()}")
        logger.info(f"Algoritmo atual: {self.mib.get_current_algorithm()}")
        logger.info("-"*60)
        
        logger.info("Vias:")
        for road in self.mib.get_all_roads():
            logger.info(f"  [{road.roadIndex}] {road.roadName}: "
                       f"{road.roadVehicleCount}/{road.roadMaxCapacity} veículos")


def main():
    """Ponto de entrada principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sistema Central de Gestão de Tráfego Rodoviário"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Ficheiro de configuração (default: config.json)"
    )
    parser.add_argument(
        "-H", "--host",
        default="127.0.0.1",
        help="Host SNMP (default: 127.0.0.1)"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=10161,
        help="Porta SNMP (default: 10161)"
    )
    
    args = parser.parse_args()
    
    # Cria e executa sistema
    system = TrafficManagementSystem(
        config_path=args.config,
        snmp_host=args.host,
        snmp_port=args.port
    )
    
    system.run()


if __name__ == "__main__":
    main()
