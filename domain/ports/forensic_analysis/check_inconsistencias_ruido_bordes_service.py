"""
Puerto para el servicio de análisis de inconsistencias en ruido y bordes.

Define la interfaz que debe implementar el servicio de análisis de inconsistencias en ruido y bordes.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_inconsistencias_ruido_bordes_result import InconsistenciasRuidoBordesResult


class InconsistenciasRuidoBordesServicePort(ABC):
    """Puerto para el servicio de análisis de inconsistencias en ruido y bordes"""
    
    @abstractmethod
    def analyze_image_ruido_bordes(self, image_bytes: bytes) -> InconsistenciasRuidoBordesResult:
        """
        Analiza inconsistencias en ruido y bordes en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            InconsistenciasRuidoBordesResult: Resultado del análisis de inconsistencias en ruido y bordes
        """
        pass
