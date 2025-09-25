"""
Implementación del servicio de gestión de risk weights.

Utiliza el helper RiskWeightsFileHandler para la persistencia.
"""

from typing import Dict, Optional
from domain.ports.config.risk_weights_service import RiskWeightsServicePort
from domain.entities.config.risk_weights_collection import RiskWeightsCollection
from domain.entities.config.risk_weight import RiskWeight
from adapters.persistence.helpers.ConfigHelpers.risk_weights_file_handler import RiskWeightsFileHandler


class RiskWeightsServiceAdapter(RiskWeightsServicePort):
    """Adaptador para el servicio de gestión de risk weights"""
    
    def __init__(self, file_path: str = "risk_weights_descriptions.json"):
        self.file_handler = RiskWeightsFileHandler(file_path)
    
    def get_all_risk_weights(self) -> RiskWeightsCollection:
        """
        Obtiene todos los risk weights.
        
        Returns:
            RiskWeightsCollection: Colección completa de risk weights
        """
        return self.file_handler.load_risk_weights()
    
    def get_risk_weight(self, key: str) -> Optional[RiskWeight]:
        """
        Obtiene un risk weight específico por su clave.
        
        Args:
            key: Clave del risk weight
            
        Returns:
            RiskWeight: El risk weight solicitado o None si no existe
        """
        return self.file_handler.get_risk_weight(key)
    
    def update_risk_weight(self, key: str, weight: RiskWeight) -> bool:
        """
        Actualiza un risk weight existente.
        
        Args:
            key: Clave del risk weight
            weight: Nuevo risk weight
            
        Returns:
            bool: True si se actualizó correctamente, False si no existe
        """
        return self.file_handler.update_risk_weight(key, weight)
    
    def create_risk_weight(self, key: str, weight: RiskWeight) -> bool:
        """
        Crea un nuevo risk weight.
        
        Args:
            key: Clave del risk weight
            weight: Risk weight a crear
            
        Returns:
            bool: True si se creó correctamente, False si ya existe
        """
        return self.file_handler.create_risk_weight(key, weight)
    
    def delete_risk_weight(self, key: str) -> bool:
        """
        Elimina un risk weight.
        
        Args:
            key: Clave del risk weight a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False si no existe
        """
        return self.file_handler.delete_risk_weight(key)
    
    def save_risk_weights(self, weights: RiskWeightsCollection) -> bool:
        """
        Guarda la colección completa de risk weights.
        
        Args:
            weights: Colección de risk weights a guardar
            
        Returns:
            bool: True si se guardó correctamente
        """
        return self.file_handler.save_risk_weights(weights)
