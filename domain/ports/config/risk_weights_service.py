"""
Puerto para el servicio de gestión de risk weights.

Define la interfaz que debe implementar el servicio de risk weights.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from domain.entities.config.risk_weights_collection import RiskWeightsCollection
from domain.entities.config.risk_weight import RiskWeight


class RiskWeightsServicePort(ABC):
    """Puerto para el servicio de gestión de risk weights"""
    
    @abstractmethod
    def get_all_risk_weights(self) -> RiskWeightsCollection:
        """
        Obtiene todos los risk weights.
        
        Returns:
            RiskWeightsCollection: Colección completa de risk weights
        """
        pass
    
    @abstractmethod
    def get_risk_weight(self, key: str) -> Optional[RiskWeight]:
        """
        Obtiene un risk weight específico por su clave.
        
        Args:
            key: Clave del risk weight
            
        Returns:
            RiskWeight: El risk weight solicitado o None si no existe
        """
        pass
    
    @abstractmethod
    def update_risk_weight(self, key: str, weight: RiskWeight) -> bool:
        """
        Actualiza un risk weight existente.
        
        Args:
            key: Clave del risk weight
            weight: Nuevo risk weight
            
        Returns:
            bool: True si se actualizó correctamente, False si no existe
        """
        pass
    
    @abstractmethod
    def create_risk_weight(self, key: str, weight: RiskWeight) -> bool:
        """
        Crea un nuevo risk weight.
        
        Args:
            key: Clave del risk weight
            weight: Risk weight a crear
            
        Returns:
            bool: True si se creó correctamente, False si ya existe
        """
        pass
    
    @abstractmethod
    def delete_risk_weight(self, key: str) -> bool:
        """
        Elimina un risk weight.
        
        Args:
            key: Clave del risk weight a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False si no existe
        """
        pass
    
    @abstractmethod
    def save_risk_weights(self, weights: RiskWeightsCollection) -> bool:
        """
        Guarda la colección completa de risk weights.
        
        Args:
            weights: Colección de risk weights a guardar
            
        Returns:
            bool: True si se guardó correctamente
        """
        pass
