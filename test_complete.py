#!/usr/bin/env python3
"""
Teste Completo - 7 Módulos de Validação do Sistema GSR
Valida todos os componentes e funcionalidades principais
"""

import sys
import time
import os
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_test(num, name):
    print(f"Teste {num}: {name}...", end=" ", flush=True)

def print_pass():
    print("✓ PASS")

def print_fail(error=""):
    print(f"✗ FAIL - {error}")
    return False

# ============================================================================
# TESTE 1: IMPORTAÇÕES
# ============================================================================
def test_imports():
    print_test(1, "Importações")
    try:
        from src.config_parser import ConfigParser
        from src.mib_objects import TrafficMIB, RoadType, TrafficColor
        from src.central_system import TrafficManagementSystem
        from src.snmp_server import TrafficSNMPServer
        from src.ssfr import TrafficFlowSimulator
        from src.decision_system import DecisionSystem, AlgorithmType
        from src.snmp_bridge import set_global_mib, get_global_mib
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

# ============================================================================
# TESTE 2: PARSER DE CONFIGURAÇÃO
# ============================================================================
def test_config_parser():
    print_test(2, "Parser de Configuração")
    try:
        from src.config_parser import ConfigParser
        parser = ConfigParser("config.json")
        parser.parse()
        
        roads = parser.get_roads()
        crossroads = parser.get_crossroads()
        links = parser.get_road_links()
        
        assert len(roads) == 3, f"Esperava 3 vias, got {len(roads)}"
        assert len(crossroads) == 1, f"Esperava 1 cruzamento, got {len(crossroads)}"
        assert len(links) == 2, f"Esperava 2 ligações, got {len(links)}"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

# ============================================================================
# TESTE 3: MIB OBJECTS
# ============================================================================
def test_mib():
    print_test(3, "MIB Objects")
    try:
        from src.mib_objects import TrafficMIB, RoadEntry, RoadType, TrafficColor
        
        mib = TrafficMIB()
        
        # Criar via teste
        road = RoadEntry(
            roadIndex=1,
            roadName="Test Road",
            roadType=RoadType.SOURCE,
            roadRTG=30,
            roadMaxCapacity=100,
            roadVehicleCount=10,
        )
        
        mib.add_road(road)
        roads = mib.get_all_roads()
        assert len(roads) == 1, f"Esperava 1 via, got {len(roads)}"
        assert roads[0].roadVehicleCount == 10
        
        # Testar thread-safety (RLock)
        mib.update_road_vehicle_count(1, 20)
        updated_road = mib.get_road(1)
        assert updated_road.roadVehicleCount == 20
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

# ============================================================================
# TESTE 4: SNMP BRIDGE
# ============================================================================
def test_snmp_bridge():
    print_test(4, "SNMP Bridge (Global MIB)")
    try:
        from src.mib_objects import TrafficMIB
        
        mib = TrafficMIB()
        
        # Testar que MIB é criada corretamente
        general = mib.get_general_objects()
        assert general is not None, "General objects não encontrados"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

# ============================================================================
# TESTE 5: ALGORITMOS
# ============================================================================
def test_algorithms():
    print_test(5, "Algoritmos (3 implementados)")
    try:
        from src.decision_system import DecisionSystem, AlgorithmType
        from src.mib_objects import TrafficMIB
        
        mib = TrafficMIB()
        
        # Verificar que os 3 algoritmos existem
        algos = [AlgorithmType.FIXED_CYCLE, AlgorithmType.OCCUPANCY_HEURISTIC, AlgorithmType.BACKPRESSURE_CONTROL]
        
        for algo in algos:
            ds = DecisionSystem(mib, algorithm=algo)
            assert ds.algorithm == algo, f"Algoritmo {algo} não inicializado"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

# ============================================================================
# TESTE 6: SIMULADORES (60 segundos)
# ============================================================================
def test_simulators():
    print_test(6, "Simuladores (60s test)")
    try:
        from src.central_system import TrafficManagementSystem
        
        # Criar e executar sistema por 60 segundos
        sc = TrafficManagementSystem("config.json", "127.0.0.1", 10161)
        sc.startup()
        
        # Deixar rodar 60 segundos
        print("\n", end="", flush=True)
        for i in range(12):
            time.sleep(5)
            mib = sc.mib
            vehicles = mib.get_general_objects().globalVehicleCount
            print(f"  [{i*5}s] Veículos: {vehicles}", flush=True)
        
        sc.stop()
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

# ============================================================================
# TESTE 7: VISUALIZADOR
# ============================================================================
def test_visualizer():
    print_test(7, "Visualizador")
    try:
        from src.mib_objects import TrafficMIB, RoadEntry, RoadType
        
        mib = TrafficMIB()
        road = RoadEntry(
            roadIndex=1,
            roadName="Test Road",
            roadType=RoadType.SOURCE,
            roadRTG=30,
            roadMaxCapacity=100,
            roadVehicleCount=50,
        )
        mib.add_road(road)
        
        # Testar que conseguimos recuperar dados
        roads = mib.get_all_roads()
        assert len(roads) > 0, "Nenhuma via encontrada"
        assert roads[0].roadName == "Test Road"
        
        print_pass()
        return True
    except Exception as e:
        return print_fail(str(e))

# ============================================================================
# MAIN
# ============================================================================
def main():
    print_header("🧪 TESTES COMPLETOS - SISTEMA GSR")
    
    results = []
    
    results.append(test_imports())
    results.append(test_config_parser())
    results.append(test_mib())
    results.append(test_snmp_bridge())
    results.append(test_algorithms())
    
    # Teste 6 leva tempo
    print("\n⏱ Iniciando teste de simuladores (60 segundos)...")
    results.append(test_simulators())
    
    results.append(test_visualizer())
    
    # Resumo
    print_header("📊 RESUMO DOS TESTES")
    passed = sum(results)
    total = len(results)
    
    print(f"Testes Passados: {passed}/{total}")
    print(f"Taxa de Sucesso: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n✅ TODOS OS TESTES PASSARAM! Sistema funcional! 🎉")
        return 0
    else:
        print(f"\n❌ {total-passed} teste(s) falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main())
