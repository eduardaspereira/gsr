#!/usr/bin/env python3
# ======================================================================================================
# Autores: Grupo de Mestrado em Engenharia Informática
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: cmc_grafica.py
# 
# Descrição: Consola de Monitorização e Controlo (CMC) com interface gráfica.
#            Realiza pedidos GET periódicos à MIB (via SNMP ou snmp_bridge) para
#            monitorizar veículos (roadVehicleCount), semáforos (roadTLColor),
#            e métricas globais (globalVehicleCount, globalAvgWaitTime).
#            Desenha mapa ASCII dinâmico com códigos ANSI para ilustrar o fluxo de tráfego.
# ========================================================================================================

import os
import sys
import time
import threading
from typing import Dict, Optional
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.snmp_bridge import get_global_mib
    USE_BRIDGE = True
except Exception:
    USE_BRIDGE = False


class TrafficMapDisplay:
    """Desenha o mapa ASCII da rede de tráfego com cores ANSI."""
    
    # Cores ANSI
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Blocos de semáforo
    LIGHT_RED = f"{RED}●{RESET}"
    LIGHT_GREEN = f"{GREEN}●{RESET}"
    LIGHT_YELLOW = f"{YELLOW}●{RESET}"
    
    # Setas e linhas
    ARROW_DOWN = "↓"
    ARROW_UP = "↑"
    ARROW_RIGHT = "→"
    ARROW_LEFT = "←"
    LINE_H = "─"
    LINE_V = "│"
    CROSS = "┼"
    
    def __init__(self):
        """Inicializa o display."""
        self.width = 100
        self.height = 30
    
    def clear_console(self):
        """Limpa o console."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_traffic_light_symbol(self, color_code: int) -> str:
        """
        Converte código de cor da MIB em símbolo ANSI.
        1 = RED, 2 = YELLOW, 3 = GREEN
        """
        if color_code == 1:
            return self.LIGHT_RED
        elif color_code == 2:
            return self.LIGHT_YELLOW
        elif color_code == 3:
            return self.LIGHT_GREEN
        return "○"
    
    def get_occupancy_bar(self, current: int, max_capacity: int, width: int = 20) -> str:
        """Desenha barra de ocupação colorida."""
        if max_capacity == 0:
            percentage = 0
        else:
            percentage = (current / max_capacity) * 100
        
        filled = int((percentage / 100) * width)
        empty = width - filled
        
        if percentage < 30:
            color = self.GREEN
        elif percentage < 70:
            color = self.YELLOW
        else:
            color = self.RED
        
        bar = f"{color}{'█' * filled}{self.RESET}{'░' * empty}"
        return f"{bar} {percentage:5.1f}%"
    
    def draw_header(self, timestamp: str, algorithm: str, status: str) -> str:
        """Desenha cabeçalho."""
        header = f"""
{self.BOLD}{'='*100}{self.RESET}
{self.BOLD}{self.CYAN}SISTEMA DE GESTÃO DE TRÁFEGO RODOVIÁRIO (GSR){self.RESET}
{self.BOLD}{self.CYAN}Universidade do Minho - Mestrado em Engenharia Informática{self.RESET}
{self.BOLD}{'='*100}{self.RESET}
{self.BOLD}[{timestamp}]  Status: {status}  |  Algoritmo: {algorithm}{self.RESET}
{self.BOLD}{'-'*100}{self.RESET}
"""
        return header
    
    def draw_topology(self, roads_data: Dict) -> str:
        """
        Desenha topologia da rede.
        roads_data: {via_index: {'name': str, 'count': int, 'capacity': int, 'color': int, 'type': str}}
        """
        via1 = roads_data.get(1, {})
        via2 = roads_data.get(2, {})
        via3 = roads_data.get(3, {})
        
        # Determinar cores dos semáforos
        light1 = self.get_traffic_light_symbol(via1.get('color', 1))
        light2 = self.get_traffic_light_symbol(via2.get('color', 1))
        
        # Dados de ocupação
        count1 = via1.get('count', 0)
        cap1 = via1.get('capacity', 100)
        count2 = via2.get('count', 0)
        cap2 = via2.get('capacity', 50)
        count3 = via3.get('count', 0)
        cap3 = via3.get('capacity', 200)
        
        # Barras de ocupação
        bar1 = self.get_occupancy_bar(count1, cap1, 15)
        bar2 = self.get_occupancy_bar(count2, cap2, 15)
        bar3 = self.get_occupancy_bar(count3, cap3, 15)
        
        topology = f"""
{self.BOLD}{self.CYAN}┌─ TOPOLOGIA DA REDE ─────────────────────────────────────────────────────────────────────────────┐{self.RESET}

    {self.BOLD}VIA 1 (Avenida Principal - ENTRADA){self.RESET}         {self.BOLD}VIA 2 (Rua Secundária - ENTRADA){self.RESET}
    Carros: {count1:3d} / {cap1:3d}  [{bar1}]         Carros: {count2:3d} / {cap2:3d}  [{bar2}]
       {self.ARROW_DOWN}                                        {self.ARROW_DOWN}
       {light1}  {self.LIGHT_GREEN if via1.get('color') == 3 else self.LIGHT_RED}                                    {light2}  {self.LIGHT_GREEN if via2.get('color') == 3 else self.LIGHT_RED}
       {self.LINE_V}                                        {self.LINE_V}
       {self.LINE_V}         ╔════════════════╗               {self.LINE_V}
       {self.LINE_V}         ║   CRUZAMENTO   ║               {self.LINE_V}
       {self.LINE_V}         ║      (ID: 1)   ║               {self.LINE_V}
       {self.LINE_V}         ╚════════════════╝               {self.LINE_V}
       {self.ARROW_DOWN}         {self.LINE_V}         {self.LINE_V}               {self.ARROW_DOWN}
       {self.ARROW_DOWN}         {self.CROSS}─────────{self.CROSS}               {self.ARROW_DOWN}
       {self.ARROW_DOWN}         {self.LINE_V}         {self.LINE_V}               {self.ARROW_DOWN}
       {self.ARROW_DOWN}         {self.ARROW_DOWN}         {self.ARROW_DOWN}
    
                        {self.BOLD}VIA 3 (Estrada Nacional - SAÍDA){self.RESET}
                        Carros: {count3:3d} / {cap3:3d}  [{bar3}]
                           {self.ARROW_DOWN}
                     {self.LINE_V}   {self.LINE_V}   {self.LINE_V}
                  (Saem da rede)

{self.BOLD}{self.CYAN}└────────────────────────────────────────────────────────────────────────────────────────────────────┘{self.RESET}
"""
        return topology
    
    def draw_traffic_lights(self, roads_data: Dict) -> str:
        """Desenha estado dos semáforos em detalhe."""
        via1 = roads_data.get(1, {})
        via2 = roads_data.get(2, {})
        
        colors_map = {1: "VERMELHO", 2: "AMARELO", 3: "VERDE"}
        color1_name = colors_map.get(via1.get('color', 1), "DESCONHECIDO")
        color2_name = colors_map.get(via2.get('color', 1), "DESCONHECIDO")
        time1 = via1.get('time_remaining', 0)
        time2 = via2.get('time_remaining', 0)
        
        lights = f"""
{self.BOLD}{self.MAGENTA}┌─ SEMÁFOROS (Traffic Lights) ───────────────────────────────────────────────────────────────────────┐{self.RESET}

    {self.BOLD}Cruzamento 1{self.RESET}

    Via 1 (Avenida Principal):
      Estado: {self.get_traffic_light_symbol(via1.get('color', 1))} {color1_name:12s} | Tempo restante: {time1:3d}s | Duração Verde: {via1.get('green_duration', 30):2d}s
      RGT (entrada): {via1.get('rgt', 0):3d} carros/min | Tipo: {via1.get('type', 'NORMAL')}

    Via 2 (Rua Secundária):
      Estado: {self.get_traffic_light_symbol(via2.get('color', 1))} {color2_name:12s} | Tempo restante: {time2:3d}s | Duração Verde: {via2.get('green_duration', 30):2d}s
      RGT (entrada): {via2.get('rgt', 0):3d} carros/min | Tipo: {via2.get('type', 'NORMAL')}

{self.BOLD}{self.MAGENTA}└────────────────────────────────────────────────────────────────────────────────────────────────────┘{self.RESET}
"""
        return lights
    
    def draw_statistics(self, global_data: Dict) -> str:
        """Desenha estatísticas globais."""
        stats = f"""
{self.BOLD}{self.BLUE}┌─ ESTATÍSTICAS GLOBAIS ──────────────────────────────────────────────────────────────────────────────┐{self.RESET}

    {self.BOLD}Resumo da Simulação:{self.RESET}
      • Total de carros na rede: {global_data.get('total_vehicles', 0):4d}
      • Tempo médio de espera: {global_data.get('avg_wait_time', 0.0):6.2f}s
      • Total de carros que entraram: {global_data.get('total_entered', 0):4d}
      • Total de carros que saíram: {global_data.get('total_exited', 0):4d}
      • Tempo decorrido: {global_data.get('elapsed_seconds', 0):4d}s
      • Algoritmo ativo: {global_data.get('algorithm', 1)} ({global_data.get('algorithm_name', 'Desconhecido')})

{self.BOLD}{self.BLUE}└────────────────────────────────────────────────────────────────────────────────────────────────────┘{self.RESET}
"""
        return stats
    
    def draw_controls(self) -> str:
        """Desenha secção de controlos."""
        controls = f"""
{self.BOLD}{self.GREEN}┌─ CONTROLO & COMANDOS ───────────────────────────────────────────────────────────────────────────────┐{self.RESET}

    {self.BOLD}Comandos disponíveis:{self.RESET}
      • 'a <1|2|3>'    : Muda algoritmo (1=FixedCycle, 2=OccupancyHeuristic, 3=BackpressureControl)
      • 'r <via> <rgt>' : Muda RGT (rate) da via (ex: 'r 1 50' = Via 1 a 50 carros/min)
      • 's'             : Atualiza estatísticas
      • 'h'             : Mostra esta ajuda
      • 'q'             : Sai do programa

{self.BOLD}{self.GREEN}└────────────────────────────────────────────────────────────────────────────────────────────────────┘{self.RESET}
"""
        return controls
    
    def draw_footer(self) -> str:
        """Desenha rodapé."""
        return f"\n{self.BOLD}{self.WHITE}{'='*100}{self.RESET}\n"


class GraphicalCMC:
    """Consola de Monitorização e Controlo com interface gráfica."""
    
    def __init__(self):
        """Inicializa a CMC gráfica."""
        self.display = TrafficMapDisplay()
        self.mib = None
        self.running = True
        self.update_interval = 5  # segundos
        
        # Tentar obter MIB
        if USE_BRIDGE:
            self.mib = get_global_mib()
            if self.mib:
                print("✓ Conectado à MIB via snmp_bridge")
            else:
                print("⚠ MIB não disponível via snmp_bridge")
        else:
            print("⚠ snmp_bridge não disponível")
    
    def get_roads_data(self) -> Dict:
        """Extrai dados das vias da MIB."""
        roads_data = {}
        
        if not self.mib:
            # Dados de exemplo
            return {
                1: {'name': 'Avenida Principal', 'count': 15, 'capacity': 100, 'color': 3, 'type': 'SOURCE', 'rgt': 30, 'time_remaining': 25, 'green_duration': 40},
                2: {'name': 'Rua Secundária', 'count': 5, 'capacity': 50, 'color': 1, 'type': 'SOURCE', 'rgt': 10, 'time_remaining': 55, 'green_duration': 40},
                3: {'name': 'Estrada Nacional', 'count': 20, 'capacity': 200, 'color': 1, 'type': 'SINK', 'rgt': 0, 'time_remaining': 0, 'green_duration': 0},
            }
        
        try:
            roads = self.mib.get_all_roads()
            for road in roads:
                type_map = {1: 'NORMAL', 2: 'SINK', 3: 'SOURCE'}
                roads_data[road.roadIndex] = {
                    'name': road.roadName,
                    'count': road.roadVehicleCount,
                    'capacity': road.roadMaxCapacity,
                    'color': road.roadTLColor,
                    'type': type_map.get(road.roadType.value, 'UNKNOWN'),
                    'rgt': road.roadRTG,
                    'time_remaining': road.roadTLTimeRemaining,
                    'green_duration': road.roadTLGreenDuration,
                }
        except Exception as e:
            print(f"Erro a ler MIB: {e}")
        
        return roads_data
    
    def get_global_data(self) -> Dict:
        """Extrai dados globais da MIB."""
        if not self.mib:
            return {
                'total_vehicles': 40,
                'avg_wait_time': 12.5,
                'total_entered': 150,
                'total_exited': 110,
                'elapsed_seconds': 300,
                'algorithm': 1,
                'algorithm_name': 'FixedCycle'
            }
        
        try:
            general = self.mib.get_general_objects()
            algo_names = {1: 'FixedCycle', 2: 'OccupancyHeuristic', 3: 'BackpressureControl'}
            return {
                'total_vehicles': general.globalVehicleCount,
                'avg_wait_time': general.globalAvgWaitTime,
                'total_entered': general.totalEnteredVehicles,
                'total_exited': general.totalExitedVehicles,
                'elapsed_seconds': general.simElapsedSeconds,
                'algorithm': general.currentAlgorithm,
                'algorithm_name': algo_names.get(general.currentAlgorithm, 'Desconhecido')
            }
        except Exception as e:
            print(f"Erro a ler dados globais: {e}")
            return {}
    
    def display_dashboard(self):
        """Mostra o dashboard completo."""
        while self.running:
            try:
                self.display.clear_console()
                
                timestamp = time.strftime('%H:%M:%S')
                
                # Obter dados
                roads_data = self.get_roads_data()
                global_data = self.get_global_data()
                
                # Desenhar dashboard
                output = ""
                output += self.display.draw_header(
                    timestamp,
                    global_data.get('algorithm_name', 'Desconhecido'),
                    "RUNNING"
                )
                output += self.display.draw_topology(roads_data)
                output += self.display.draw_traffic_lights(roads_data)
                output += self.display.draw_statistics(global_data)
                output += self.display.draw_controls()
                output += self.display.draw_footer()
                
                print(output)
                print(f"⏱ Próxima atualização em {self.update_interval}s... (Pressiona Ctrl+C para sair)")
                
                time.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                self.running = False
                print("\n🛑 CMC Gráfica terminada.")
                break
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(1)
    
    def run(self):
        """Executa a CMC gráfica."""
        print("🚀 A iniciar Consola de Monitorização e Controlo (CMC) Gráfica...")
        print("📡 Conectando ao Sistema Central de Tráfego (SC)...")
        time.sleep(2)
        
        try:
            self.display_dashboard()
        except KeyboardInterrupt:
            print("\n🛑 CMC Gráfica terminada.")
            sys.exit(0)


def main():
    """Ponto de entrada."""
    cmc = GraphicalCMC()
    cmc.run()


if __name__ == "__main__":
    main()
