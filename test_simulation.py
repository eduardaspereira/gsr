#!/usr/bin/env python3
"""
Script de teste do GSR - Simula tráfego por 30 segundos.
"""

import logging
import time
import sys

from src.central_system import TrafficManagementSystem

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Executa teste de simulação."""
    logger.info("="*70)
    logger.info("TESTE GSR - Sistema de Gestão de Tráfego Rodoviário")
    logger.info("="*70)
    
    # Criar sistema
    system = TrafficManagementSystem(snmp_port=10161)
    
    # Startup
    if not system.startup():
        logger.error("Falha ao iniciar sistema")
        return False
    
    # Iniciar simuladores
    logger.info("\nIniciando simuladores...")
    system.ssfr.start()
    system.decision_system.start()
    
    logger.info("✓ Simuladores iniciados")
    logger.info("Simulando por 30 segundos...\n")
    
    try:
        # Simular por 30 segundos
        for i in range(6):
            time.sleep(5)
            logger.info(f"\n[T={i*5+5}s] Atualizando status...")
            system.print_status_detailed()
    
    except KeyboardInterrupt:
        logger.info("\nInterrompido pelo utilizador")
    
    finally:
        # Parar
        logger.info("\nParando sistema...")
        system.stop()
        logger.info("✓ Teste concluído")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
