#!/usr/bin/env python3
"""
Teste Simplificado - Validação do Sistema GSR
"""

import sys
import time
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_test(num, name):
    print(f"  [{num}] {name}...", end=" ", flush=True)

def print_pass():
    print("OK")

def print_fail(error=""):
    print("FAIL")
    if error:
        print(f"      Error: {error}")
    return False

# ============================================================================
# TESTES
# ============================================================================

def test_imports():
    """Teste 1: Importações básicas"""
    print_test(1, "Importações")
    try:
        from src.config_parser import ConfigParser
        from src.mib_objects import TrafficMIB, RoadType, TrafficColor
        from src.central_system import TrafficManagementSystem
        from src.snmp_server import TrafficSNMPServer
        from src.ssfr import TrafficFlowSimulator
        from src.decision_system import DecisionSystem, AlgorithmType
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

def test_config():
    """Teste 2: Carregar configuração"""
    print_test(2, "Configuração (config.json)")
    try:
        from src.config_parser import ConfigParser
        parser = ConfigParser("config.json")
        config_data = parser.parse()
        
        roads = parser.get_roads()
        crossroads = parser.get_crossroads()
        links = parser.get_road_links()
        
        assert len(roads) == 3, f"Expected 3 roads, got {len(roads)}"
        assert len(crossroads) == 1, f"Expected 1 crossroad, got {len(crossroads)}"
        assert len(links) == 2, f"Expected 2 links, got {len(links)}"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

def test_mib_creation():
    """Teste 3: Criação da MIB"""
    print_test(3, "MIB Creation")
    try:
        from src.config_parser import ConfigParser
        from src.mib_objects import TrafficMIB
        
        # Criar MIB
        mib = TrafficMIB()
        
        # Verificar estrutura inicial
        sim_status = mib.get_sim_status()
        assert sim_status is not None, "sim_status is None"
        
        # Adicionar estrada
        parser = ConfigParser("config.json")
        roads_config = parser.get_roads()
        
        for road_config in roads_config:
            from src.mib_objects import RoadEntry, RoadType
            road = RoadEntry(
                roadIndex=road_config['roadIndex'],
                roadName=road_config['roadName'],
                roadType=RoadType(road_config['roadType']),
                roadRTG=road_config.get('roadRTG', 0),
                roadMaxCapacity=road_config.get('roadMaxCapacity', 100),
            )
            mib.add_road(road)
        
        # Verificar vias adicionadas
        roads = mib.get_all_roads()
        assert len(roads) == 3, f"Expected 3 roads, got {len(roads)}"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

def test_algorithms():
    """Teste 4: Algoritmos"""
    print_test(4, "Algoritmos (3)")
    try:
        from src.decision_system import AlgorithmType
        
        # Verificar que os 3 algoritmos existem
        assert hasattr(AlgorithmType, 'FIXED_CYCLE'), "FIXED_CYCLE missing"
        assert hasattr(AlgorithmType, 'OCCUPANCY_HEURISTIC'), "OCCUPANCY_HEURISTIC missing"
        assert hasattr(AlgorithmType, 'BACKPRESSURE_CONTROL'), "BACKPRESSURE_CONTROL missing"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

def test_simulators():
    """Teste 5: Simuladores (30 segundos)"""
    print_test(5, "Simuladores (30s)")
    try:
        from src.central_system import TrafficManagementSystem
        import logging
        
        # Suprimir logs
        logging.getLogger().setLevel(logging.CRITICAL)
        
        # Criar e executar
        sc = TrafficManagementSystem("config.json", "127.0.0.1", 10161)
        sc.startup()
        
        print(end="\n", flush=True)
        
        # Deixar rodar 30 segundos
        for i in range(6):
            time.sleep(5)
            vehicles = mib.get_all_roads()[0].roadVehicleCount if hasattr(sc, 'mib') else 0
            print(f"      [{i*5}s] Running...", flush=True)
        
        sc.stop()
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

def test_snmp_server():
    """Teste 6: Servidor SNMP"""
    print_test(6, "Servidor SNMP")
    try:
        from src.mib_objects import TrafficMIB
        from src.snmp_server import TrafficSNMPServer
        
        mib = TrafficMIB()
        server = TrafficSNMPServer(mib, "127.0.0.1", 10161)
        
        assert server.mib is not None, "MIB not assigned"
        assert server.host == "127.0.0.1", "Host not set"
        assert server.port == 10161, "Port not set"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

def test_traffic_flow():
    """Teste 7: Fluxo de tráfego"""
    print_test(7, "Fluxo de Tráfego")
    try:
        from src.ssfr import TrafficFlowSimulator
        from src.mib_objects import TrafficMIB
        
        mib = TrafficMIB()
        simulator = TrafficFlowSimulator(mib, step_duration=5)
        
        assert simulator.mib is not None, "MIB not assigned"
        assert simulator.step_duration == 5, "Step duration not set"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

# ============================================================================
# MAIN
# ============================================================================

def main():
    print_header("🧪 TESTES SIMPLIFICADOS - SISTEMA GSR")
    print("Validando componentes principais...\n")
    
    results = []
    results.append(test_imports())
    results.append(test_config())
    results.append(test_mib_creation())
    results.append(test_algorithms())
    results.append(test_snmp_server())
    results.append(test_traffic_flow())
    
    # Teste com simuladores (mais tempo)
    print("\n⏱ Iniciando teste de simuladores (30 segundos)...")
    results.append(test_simulators())
    
    # Resumo
    print_header("📊 RESUMO DOS TESTES")
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"  Testes Passados: {passed}/{total}")
    print(f"  Taxa de Sucesso: {(passed/total)*100:.1f}%\n")
    
    if passed == total:
        print("  ✅ TODOS OS TESTES PASSARAM!")
        print("  Sistema está funcional! 🎉\n")
        return 0
    else:
        failed = total - passed
        print(f"  ❌ {failed} teste(s) falharam\n")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Testes interrompidos pelo utilizador")
        sys.exit(1)
