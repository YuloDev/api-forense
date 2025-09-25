"""
Puerto/interfaz para el servicio de niveles de riesgo.

Define el contrato para la gestión de niveles de riesgo del sistema.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from domain.entities.config.risk_level import RiskLevel
from domain.entities.config.risk_levels_collection import RiskLevelsCollection


class RiskLevelsServicePort(ABC):
    """Puerto para el servicio de niveles de riesgo"""
    
    @abstractmethod
    def get_all_levels(self) -> Dict[str, any]:
        """
        Obtiene todos los niveles de riesgo.
        
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def get_level_by_name(self, name: str) -> Dict[str, any]:
        """
        Obtiene un nivel de riesgo específico por nombre.
        
        Args:
            name: Nombre del nivel de riesgo
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def get_level_by_score(self, score: int) -> Dict[str, any]:
        """
        Obtiene el nivel de riesgo para un puntaje específico.
        
        Args:
            score: Puntaje a evaluar
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def update_level(self, name: str, level_data: Dict[str, any]) -> Dict[str, any]:
        """
        Actualiza un nivel de riesgo existente.
        
        Args:
            name: Nombre del nivel de riesgo
            level_data: Datos del nivel a actualizar
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def add_level(self, level_data: Dict[str, any]) -> Dict[str, any]:
        """
        Agrega un nuevo nivel de riesgo.
        
        Args:
            level_data: Datos del nuevo nivel
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def remove_level(self, name: str) -> Dict[str, any]:
        """
        Elimina un nivel de riesgo.
        
        Args:
            name: Nombre del nivel a eliminar
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def update_all_levels(self, levels_data: Dict[str, any]) -> Dict[str, any]:
        """
        Actualiza todos los niveles de riesgo.
        
        Args:
            levels_data: Datos de todos los niveles
            
        Returns:
            Dict con resultado de la operación
        """
        pass
