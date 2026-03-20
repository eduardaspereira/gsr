"""
Módulo de leitura e validação da configuração do sistema de tráfego rodoviário.
Lê um ficheiro JSON com parâmetros de simulação, vias, cruzamentos e ligações.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigParser:
    """Parser e validador de ficheiro de configuração JSON."""
    
    DEFAULT_CONFIG_PATH = "config.json"
    
    REQUIRED_TRAFFIC_GENERAL = {
        "simStepDuration": int,
        "algoYellowTime": int,
        "algoMinGreenTime": int,
        "algoMaxGreenTime": int,
        "currentAlgorithm": int,
    }
    
    REQUIRED_ROAD_FIELDS = {
        "roadIndex": int,
        "roadName": str,
        "roadType": int,
        "roadRTG": int,
        "roadMaxCapacity": int,
        "roadVehicleCount": int,
        "roadCrossroadID": int,
    }
    
    ROAD_TYPES = {
        1: "normal",      # Via normal
        2: "sink",        # Saída (sumidouro)
        3: "source",      # Entrada (fonte)
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o parser com um ficheiro de configuração.
        
        Args:
            config_path: Caminho para ficheiro config.json (default: config.json)
        """
        self.config_path = Path(config_path or self.DEFAULT_CONFIG_PATH)
        self.config = {}
        
    def parse(self) -> Dict[str, Any]:
        """
        Lê e valida o ficheiro de configuração.
        
        Returns:
            Dicionário com configuração validada
            
        Raises:
            FileNotFoundError: Se ficheiro não existe
            json.JSONDecodeError: Se JSON é inválido
            ValueError: Se validação falha
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Ficheiro de configuração não encontrado: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON inválido em {self.config_path}: {e.msg}", 
                                      e.doc, e.pos)
        
        self._validate_config()
        return self.config
    
    def _validate_config(self):
        """Valida a estrutura geral da configuração."""
        if not isinstance(self.config, dict):
            raise ValueError("Configuração deve ser um objeto JSON")
        
        # Valida trafficGeneral
        if "trafficGeneral" not in self.config:
            raise ValueError("Secção 'trafficGeneral' é obrigatória")
        
        self._validate_traffic_general()
        
        # Valida tabelas (opcional, mas recomendado)
        if "crossroads" in self.config:
            self._validate_crossroads()
        
        if "roads" in self.config:
            self._validate_roads()
        
        if "roadLinks" in self.config:
            self._validate_road_links()
    
    def _validate_traffic_general(self):
        """Valida parâmetros gerais de tráfego."""
        tg = self.config["trafficGeneral"]
        
        if not isinstance(tg, dict):
            raise ValueError("'trafficGeneral' deve ser um objeto")
        
        for field, field_type in self.REQUIRED_TRAFFIC_GENERAL.items():
            if field not in tg:
                raise ValueError(f"Campo obrigatório ausente: trafficGeneral.{field}")
            
            if not isinstance(tg[field], field_type):
                raise ValueError(f"Campo {field} deve ser {field_type.__name__}")
            
            if field != "currentAlgorithm" and tg[field] <= 0:
                raise ValueError(f"Campo {field} deve ser positivo")
        
        # Validações adicionais
        if tg["algoMinGreenTime"] > tg["algoMaxGreenTime"]:
            raise ValueError("algoMinGreenTime não pode ser maior que algoMaxGreenTime")
        
        if tg["algoYellowTime"] <= 0:
            raise ValueError("algoYellowTime deve ser positivo")
    
    def _validate_crossroads(self):
        """Valida tabela de cruzamentos."""
        crossroads = self.config["crossroads"]
        
        if not isinstance(crossroads, list):
            raise ValueError("'crossroads' deve ser uma lista")
        
        indices = set()
        for i, cr in enumerate(crossroads):
            if not isinstance(cr, dict):
                raise ValueError(f"Cruzamento {i} deve ser um objeto")
            
            if "crossroadIndex" not in cr:
                raise ValueError(f"Cruzamento {i}: campo 'crossroadIndex' obrigatório")
            
            idx = cr["crossroadIndex"]
            if idx in indices:
                raise ValueError(f"Índice de cruzamento duplicado: {idx}")
            
            indices.add(idx)
            
            if "crossroadMode" not in cr:
                raise ValueError(f"Cruzamento {idx}: campo 'crossroadMode' obrigatório")
    
    def _validate_roads(self):
        """Valida tabela de vias."""
        roads = self.config["roads"]
        
        if not isinstance(roads, list):
            raise ValueError("'roads' deve ser uma lista")
        
        indices = set()
        for i, road in enumerate(roads):
            if not isinstance(road, dict):
                raise ValueError(f"Via {i} deve ser um objeto")
            
            # Valida campos obrigatórios
            for field, field_type in self.REQUIRED_ROAD_FIELDS.items():
                if field not in road:
                    raise ValueError(f"Via {i}: campo '{field}' obrigatório")
                
                if not isinstance(road[field], field_type):
                    raise ValueError(f"Via {i}, campo {field}: deve ser {field_type.__name__}")
            
            idx = road["roadIndex"]
            if idx in indices:
                raise ValueError(f"Índice de via duplicado: {idx}")
            
            indices.add(idx)
            
            # Valida tipo de via
            road_type = road["roadType"]
            if road_type not in self.ROAD_TYPES:
                raise ValueError(f"Via {idx}: tipo inválido {road_type}")
            
            # Valida capacidade
            if road["roadMaxCapacity"] <= 0:
                raise ValueError(f"Via {idx}: roadMaxCapacity deve ser positivo")
            
            if road["roadVehicleCount"] > road["roadMaxCapacity"]:
                raise ValueError(f"Via {idx}: veículos iniciais excedem capacidade")
            
            if road["roadRTG"] < 0:
                raise ValueError(f"Via {idx}: roadRTG não pode ser negativo")
    
    def _validate_road_links(self):
        """Valida tabela de ligações entre vias."""
        links = self.config["roadLinks"]
        
        if not isinstance(links, list):
            raise ValueError("'roadLinks' deve ser uma lista")
        
        indices = set()
        road_indices = {r["roadIndex"] for r in self.config.get("roads", [])}
        
        for i, link in enumerate(links):
            if not isinstance(link, dict):
                raise ValueError(f"Ligação {i} deve ser um objeto")
            
            required = ["linkIndex", "linkSourceIndex", "linkDestIndex"]
            for field in required:
                if field not in link:
                    raise ValueError(f"Ligação {i}: campo '{field}' obrigatório")
            
            link_idx = link["linkIndex"]
            if link_idx in indices:
                raise ValueError(f"Índice de ligação duplicado: {link_idx}")
            
            indices.add(link_idx)
            
            # Valida referências de vias
            src = link["linkSourceIndex"]
            dst = link["linkDestIndex"]
            
            if src not in road_indices:
                raise ValueError(f"Ligação {link_idx}: via origem {src} não existe")
            
            if dst not in road_indices:
                raise ValueError(f"Ligação {link_idx}: via destino {dst} não existe")
    
    def get_traffic_general(self) -> Dict[str, int]:
        """Retorna parâmetros gerais de tráfego."""
        return self.config.get("trafficGeneral", {})
    
    def get_roads(self) -> List[Dict[str, Any]]:
        """Retorna lista de vias."""
        return self.config.get("roads", [])
    
    def get_crossroads(self) -> List[Dict[str, Any]]:
        """Retorna lista de cruzamentos."""
        return self.config.get("crossroads", [])
    
    def get_road_links(self) -> List[Dict[str, Any]]:
        """Retorna lista de ligações entre vias."""
        return self.config.get("roadLinks", [])
    
    def get_road_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Retorna via por índice."""
        for road in self.get_roads():
            if road["roadIndex"] == index:
                return road
        return None
