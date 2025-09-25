"""
Entidad para la colección de risk weights.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from domain.entities.config.risk_weight import RiskWeight


@dataclass
class RiskWeightsCollection:
    """Entidad que representa la colección completa de risk weights"""
    
    weights: Dict[str, RiskWeight]
    
    def __post_init__(self):
        """Inicialización post-construcción"""
        if self.weights is None:
            self.weights = {}
    
    def get_weight(self, key: str) -> Optional[RiskWeight]:
        """Obtiene un risk weight por su clave"""
        return self.weights.get(key)
    
    def set_weight(self, key: str, weight: RiskWeight) -> None:
        """Establece un risk weight"""
        self.weights[key] = weight
    
    def remove_weight(self, key: str) -> bool:
        """Elimina un risk weight"""
        if key in self.weights:
            del self.weights[key]
            return True
        return False
    
    def get_all_keys(self) -> List[str]:
        """Obtiene todas las claves de risk weights"""
        return list(self.weights.keys())
    
    def get_all_weights(self) -> List[RiskWeight]:
        """Obtiene todos los risk weights"""
        return list(self.weights.values())
    
    def to_dict(self) -> Dict[str, dict]:
        """Convierte la colección a diccionario"""
        return {key: weight.to_dict() for key, weight in self.weights.items()}
    
    def to_json_dict(self) -> dict:
        """Convierte la colección a diccionario para serialización JSON"""
        return {key: weight.to_dict() for key, weight in self.weights.items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, dict]) -> 'RiskWeightsCollection':
        """Crea una instancia desde un diccionario"""
        weights = {}
        for key, weight_data in data.items():
            weights[key] = RiskWeight.from_dict(key, weight_data)
        return cls(weights=weights)
    
    def __len__(self) -> int:
        """Retorna el número de risk weights"""
        return len(self.weights)
    
    def __contains__(self, key: str) -> bool:
        """Verifica si existe un risk weight con la clave dada"""
        return key in self.weights
