#!/usr/bin/env python3
"""Quick test of SSFR and DecisionSystem."""

import time
import logging
from src.central_system import TrafficManagementSystem

logging.basicConfig(level=logging.WARNING)

system = TrafficManagementSystem(snmp_port=10161)

print("\n" + "="*70)
print("TESTE RÁPIDO: SSFR + DecisionSystem")
print("="*70 + "\n")

if system.startup():
    system.ssfr.start()
    system.decision_system.start()
    
    print("Iniciado. Coletando dados por 30 segundos...\n")
    print("-"*70)
    
    for i in range(3):
        time.sleep(10)
        stats = system.ssfr.get_statistics()
        elapsed = stats['elapsed_seconds']
        vehicles = stats['vehicles_in_network']
        entered = stats['total_entered']
        exited = stats['total_exited']
        wait = stats['avg_wait_time']
        
        status = f"T={elapsed:3d}s | "
        status += f"Veículos={vehicles:2d} | "
        status += f"Entrada={entered:2d} | "
        status += f"Saída={exited:2d} | "
        status += f"Espera med={wait:5.1f}s"
        
        print(status)
    
    print("-"*70)
    
    system.stop()
    print("\n✓ Teste concluído com sucesso!")
    print("="*70 + "\n")
else:
    print("✗ Erro ao inicializar sistema")
