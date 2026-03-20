#!/usr/bin/env python3
"""
Consola de Monitorização e Controlo (CMC) - Sistema GSR
Interface via terminal para monitorar e controlar o sistema de tráfego.
"""

import sys
import time
from pathlib import Path

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.snmp_bridge import get_global_mib


class MonitoringConsole:
    """Consola de monitorização e controlo do sistema de tráfego."""
    
    def __init__(self):
        """Inicializa a consola."""
        self.mib = get_global_mib()
        self.running = True
        
        if not self.mib:
            print("⚠️  Aviso: MIB não encontrada. Sistema não está a rodar?")
            print("   Inicia o Sistema Central primeiro:")
            print("   python3 -m src.central_system -H 127.0.0.1 -p 10161")
            sys.exit(1)
    
    def print_header(self):
        """Mostra cabeçalho."""
        print("\n" + "="*70)
        print("  Consola de Monitorização e Controlo (CMC)")
        print("  Sistema de Gestão de Tráfego Rodoviário (GSR)")
        print("="*70)
        print("  Digite 'help' para ver comandos disponíveis")
        print("="*70 + "\n")
    
    def cmd_help(self):
        """Mostra ajuda."""
        print("""
Comandos Disponíveis:

  map               - Desenha mapa da rede de tráfego
  display           - Mostra snapshot das métricas atuais
  monitor           - Monitorização contínua (Ctrl+C para parar)
  stats             - Estatísticas globais
  roads             - Lista de todas as vias
  crossroads        - Lista de cruzamentos
  set roadRTG <id> <value>  - Muda RGT (ritmo) de uma via
  set algorithm <1|2|3>     - Muda algoritmo de semáforo
  get <oid>         - Lê valor específico SNMP
  exit, quit, q     - Sai do programa
  help, h, ?        - Mostra esta ajuda
""")
    
    def cmd_map(self):
        """Desenha mapa da rede."""
        print("""
    ╔═══════════════════════════════════════╗
    ║    Rede de Tráfego Rodoviário        ║
    ║                                       ║
    ║    Via 1 (Entrada)  Via 2 (Ent)     ║
    ║    ════════════════ ═════════════   ║
    ║         ↓               ↓             ║
    ║         └────┬──────────┘             ║
    ║         🟢 Cruzamento 1               ║
    ║              ↓                       ║
    ║    Via 3 (Saída) ═════════════      ║
    ╚═══════════════════════════════════════╝

Legenda:
  Via 1: Avenida Principal (ENTRADA) - RGT = 30 carros/min
  Via 2: Rua Secundária (ENTRADA) - RGT = 10 carros/min
  Via 3: Estrada Nacional (SAÍDA) - Carros desaparecem
  🟢: Semáforo verde
  🔴: Semáforo vermelho
  🟡: Semáforo amarelo
""")
    
    def cmd_display(self):
        """Mostra snapshot das métricas."""
        try:
            roads = self.mib.get_all_roads()
            general = self.mib.traffic_general
            
            print("\n╔════════════════════════════════════════════════════════════╗")
            print("║ ESTADO ATUAL DO SISTEMA                                   ║")
            print("╠════════════════════════════════════════════════════════════╣")
            
            print(f"║ Status: RUNNING")
            print(f"║ Tempo Decorrido: {general.simElapsedSeconds}s")
            print(f"║ Total Carros na Rede: {general.globalVehicleCount}")
            print(f"║ Tempo Médio de Espera: {general.globalAvgWaitTime:.1f}s")
            print(f"║ Total Entrados: {general.totalEnteredVehicles}")
            print(f"║ Total Saídos: {general.totalExitedVehicles}")
            
            algo_names = {1: "FixedCycle", 2: "OccupancyHeuristic", 3: "BackpressureControl"}
            algo_name = algo_names.get(general.currentAlgorithm, "Desconhecido")
            print(f"║ Algoritmo: {algo_name}")
            
            print("╠════════════════════════════════════════════════════════════╣")
            print("║ VIAS                                                       ║")
            print("╠════════════════════════════════════════════════════════════╣")
            
            for road in roads:
                type_map = {1: "NORMAL", 2: "SINK", 3: "SOURCE"}
                color_map = {1: "🔴 RED", 2: "🟡 YELLOW", 3: "🟢 GREEN"}
                
                print(f"║ Via {road.roadIndex}: {road.roadName}")
                print(f"║   Tipo: {type_map.get(road.roadType.value, '?')}")
                print(f"║   Carros: {road.roadVehicleCount}/{road.roadMaxCapacity}")
                print(f"║   Espera média: {road.roadAvgWaitTime:.1f}s")
                if road.roadType.value == 3:  # SOURCE
                    print(f"║   RGT: {road.roadRTG} carros/min")
                print(f"║   Semáforo: {color_map.get(road.roadTLColor, '?')}")
                print("║")
            
            print("╚════════════════════════════════════════════════════════════╝\n")
            
        except Exception as e:
            print(f"❌ Erro ao ler dados: {e}")
    
    def cmd_monitor(self):
        """Monitorização contínua."""
        print("📡 Monitorização contínua (Ctrl+C para parar)...\n")
        try:
            while True:
                self.cmd_display()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n✓ Monitorização terminada")
    
    def cmd_stats(self):
        """Mostra estatísticas."""
        try:
            general = self.mib.traffic_general
            
            print(f"""
╔══════════════════════════════════════════════╗
║ ESTATÍSTICAS GLOBAIS                         ║
╠══════════════════════════════════════════════╣
║ Status: RUNNING
║ Tempo Decorrido: {general.simElapsedSeconds} segundos
║ Carros na Rede: {general.globalVehicleCount}
║ Tempo Médio Espera: {general.globalAvgWaitTime:.2f} segundos
║ Total Carros Entrados: {general.totalEnteredVehicles}
║ Total Carros Saídos: {general.totalExitedVehicles}
║ Algoritmo: {general.currentAlgorithm}
╚══════════════════════════════════════════════╝
""")
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def cmd_roads(self):
        """Lista todas as vias."""
        try:
            roads = self.mib.get_all_roads()
            
            print("\n╔═══════════════════════════════════════════════════════════════════╗")
            print("║ VIAS (ROADS)                                                      ║")
            print("╚═══════════════════════════════════════════════════════════════════╝\n")
            
            type_map = {1: "NORMAL", 2: "SINK", 3: "SOURCE"}
            color_map = {1: "🔴", 2: "🟡", 3: "🟢"}
            
            for road in roads:
                print(f"Via {road.roadIndex}: {road.roadName}")
                print(f"  Tipo: {type_map.get(road.roadType.value)}")
                print(f"  Carros: {road.roadVehicleCount}/{road.roadMaxCapacity}")
                print(f"  Semáforo: {color_map.get(road.roadTLColor)} (em {road.roadTLTimeRemaining}s)")
                print(f"  Espera média: {road.roadAvgWaitTime:.1f}s")
                if road.roadType.value == 3:
                    print(f"  RGT: {road.roadRTG} carros/min")
                print()
            
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def cmd_crossroads(self):
        """Lista cruzamentos."""
        try:
            crossroads = self.mib.get_all_crossroads()
            
            print("\n╔═══════════════════════════════════════════════════════════════════╗")
            print("║ CRUZAMENTOS (CROSSROADS)                                          ║")
            print("╚═══════════════════════════════════════════════════════════════════╝\n")
            
            for cr in crossroads:
                print(f"Cruzamento {cr.crossroadIndex}")
                print(f"  Modo: {cr.crossroadMode}")
                print()
            
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def cmd_set(self, args):
        """Define valores."""
        if not args or len(args) < 2:
            print("❌ Uso: set <param> <valor>")
            print("  Exemplos:")
            print("    set roadRTG 1 50     (muda RGT via 1 para 50)")
            print("    set algorithm 2      (muda algoritmo para 2)")
            return
        
        param = args[0]
        
        if param == "roadRTG" and len(args) >= 3:
            try:
                road_id = int(args[1])
                new_rgt = int(args[2])
                road = self.mib.get_road(road_id)
                if road:
                    road.roadRTG = new_rgt
                    print(f"✓ RGT da Via {road_id} alterado para {new_rgt} carros/minuto")
                else:
                    print(f"❌ Via {road_id} não encontrada")
            except (ValueError, IndexError) as e:
                print(f"❌ Erro: {e}")
        
        elif param == "algorithm" and len(args) >= 2:
            try:
                algo = int(args[1])
                if algo in [1, 2, 3]:
                    self.mib.traffic_general.currentAlgorithm = algo
                    algo_names = {1: "FixedCycle", 2: "OccupancyHeuristic", 3: "BackpressureControl"}
                    print(f"✓ Algoritmo alterado para {algo} ({algo_names[algo]})")
                else:
                    print("❌ Algoritmo deve ser 1, 2 ou 3")
            except (ValueError, IndexError) as e:
                print(f"❌ Erro: {e}")
        else:
            print("❌ Parâmetro desconhecido ou faltam argumentos")
    
    def cmd_get(self, args):
        """Lê valor específico."""
        if not args:
            print("❌ Uso: get <oid>")
            return
        
        oid = args[0]
        print(f"🔍 Valor de {oid}: [SNMP não implementado em modo demo]")
    
    def run(self):
        """Executa a consola."""
        self.print_header()
        
        while self.running:
            try:
                # Ler comando
                user_input = input("gsr> ").strip()
                
                if not user_input:
                    continue
                
                # Processar
                parts = user_input.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                # Comandos
                if cmd in ['help', 'h', '?']:
                    self.cmd_help()
                elif cmd == 'map':
                    self.cmd_map()
                elif cmd == 'display':
                    self.cmd_display()
                elif cmd == 'monitor':
                    self.cmd_monitor()
                elif cmd == 'stats':
                    self.cmd_stats()
                elif cmd == 'roads':
                    self.cmd_roads()
                elif cmd == 'crossroads':
                    self.cmd_crossroads()
                elif cmd == 'set':
                    self.cmd_set(args)
                elif cmd == 'get':
                    self.cmd_get(args)
                elif cmd in ['exit', 'quit', 'q']:
                    print("✓ Até logo!")
                    self.running = False
                else:
                    print(f"❌ Comando desconhecido: {cmd}")
                    print("   Digite 'help' para ver comandos disponíveis")
            
            except KeyboardInterrupt:
                print("\n✓ Consola terminada")
                self.running = False
            except EOFError:
                self.running = False
            except Exception as e:
                print(f"❌ Erro: {e}")


def main():
    """Ponto de entrada."""
    console = MonitoringConsole()
    console.run()


if __name__ == "__main__":
    main()
