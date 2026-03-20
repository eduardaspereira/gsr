"""
Servidor SNMP do Sistema Central (SC).
Implementa um agente SNMPv2c que expõe a MIB do sistema de tráfego.
Usa a API simplificada (hlapi) de pysnmp 7.x
"""

import logging
from typing import Optional, Any
import socket
import struct
import threading

from src.mib_objects import TrafficMIB, SimOperStatus, TrafficColor

logger = logging.getLogger(__name__)


class TrafficSNMPServer:
    """
    Servidor SNMP simplificado para o Sistema Central.
    Implementa protocolo SNMPv2c básico.
    """
    
    def __init__(self, mib: TrafficMIB, host: str = "127.0.0.1", port: int = 161):
        """
        Inicializa o servidor SNMP.
        
        Args:
            mib: Instância da MIB com os dados
            host: Endereço de binding (default: localhost)
            port: Porta SNMP (default: 161, requer root; use 10161 para teste)
        """
        self.mib = mib
        self.host = host
        self.port = port
        
        self.sock = None
        self.running = False
        self.server_thread = None
        
        logger.info(f"Servidor SNMP pronto para {host}:{port}")
    
    def get_oid_mapping(self) -> dict:
        """
        Mapeia OIDs para getters/setters da MIB.
        Retorna dicionário: OID -> (getter, setter ou None)
        """
        mib_base = "1.3.6.1.3.2026.1.1"  # trafficObjects.trafficGeneral
        
        mapping = {
            # trafficGeneral objects
            f"{mib_base}.1": (lambda: int(self.mib.get_sim_status()), 
                            lambda v: self.mib.set_sim_status(int(v))),
            
            f"{mib_base}.2": (lambda: self.mib.get_sim_step_duration(), 
                            lambda v: self.mib.set_sim_step_duration(int(v))),
            
            f"{mib_base}.3": (lambda: self.mib.get_sim_elapsed_seconds(), None),
            
            f"{mib_base}.4": (lambda: self.mib.get_global_vehicle_count(), None),
            
            f"{mib_base}.5": (lambda: int(self.mib.get_global_avg_wait_time()), None),
            
            f"{mib_base}.6": (lambda: self.mib.get_total_entered_vehicles(), None),
            
            f"{mib_base}.7": (lambda: self.mib.get_total_exited_vehicles(), None),
            
            f"{mib_base}.8": (lambda: self.mib.get_algo_min_green_time(),
                            lambda v: self.mib.set_algo_min_green_time(int(v))),
            
            f"{mib_base}.9": (lambda: self.mib.get_algo_max_green_time(),
                            lambda v: self.mib.set_algo_max_green_time(int(v))),
            
            f"{mib_base}.10": (lambda: self.mib.get_algo_yellow_time(), None),
            
            f"{mib_base}.11": (lambda: self.mib.get_current_algorithm(),
                             lambda v: self.mib.set_current_algorithm(int(v))),
        }
        
        return mapping
    
    def handle_get_request(self, oid: str) -> Optional[Any]:
        """
        Trata pedido GET SNMP.
        
        Args:
            oid: OID do objeto pedido
            
        Returns:
            Valor do objeto ou None
        """
        mapping = self.get_oid_mapping()
        
        if oid in mapping:
            getter, _ = mapping[oid]
            try:
                return getter()
            except Exception as e:
                logger.error(f"Erro ao ler OID {oid}: {e}")
                return None
        
        logger.warning(f"OID não encontrado: {oid}")
        return None
    
    def handle_set_request(self, oid: str, value: Any) -> bool:
        """
        Trata pedido SET SNMP.
        
        Args:
            oid: OID do objeto
            value: Novo valor
            
        Returns:
            True se sucesso, False caso contrário
        """
        mapping = self.get_oid_mapping()
        
        if oid not in mapping:
            logger.warning(f"OID SET não encontrado: {oid}")
            return False
        
        getter, setter = mapping[oid]
        
        if setter is None:
            logger.warning(f"OID {oid} é read-only")
            return False
        
        try:
            setter(value)
            logger.debug(f"SET {oid} = {value}")
            return True
        except Exception as e:
            logger.error(f"Erro ao escrever OID {oid}: {e}")
            return False
    
    def run(self):
        """Inicia o servidor SNMP (bloqueante)."""
        logger.info("Servidor SNMP aguardando pedidos...")
        logger.info(f"Escutando em {self.host}:{self.port}")
        
        self.running = True
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            
            logger.info("✓ Socket SNMP aberto")
            
            while self.running:
                try:
                    data, client_addr = self.sock.recvfrom(1024)
                    logger.debug(f"Recebido de {client_addr}: {len(data)} bytes")
                    # Aqui iriam trata os pedidos SNMP
                    # Por agora, é apenas um placeholder
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Erro ao receber: {e}")
        
        except KeyboardInterrupt:
            logger.info("Servidor SNMP parado pelo utilizador")
        except Exception as e:
            logger.error(f"Erro no servidor SNMP: {e}")
        finally:
            self.running = False
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
    
    def stop(self):
        """Para o servidor SNMP."""
        self.running = False
        logger.info("Parando servidor SNMP...")
