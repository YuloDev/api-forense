"""
Puerto para el servicio de análisis de evidencias forenses.

Define la interfaz que debe implementar el servicio de evidencias forenses.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_evidencias_forenses_result import EvidenciasForensesResult


class EvidenciasForensesServicePort(ABC):
    """Puerto para el servicio de análisis de evidencias forenses"""
    
    @abstractmethod
    def analyze_image_evidencias_forenses(self, image_bytes: bytes) -> EvidenciasForensesResult:
        """
        Analiza evidencias forenses en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            EvidenciasForensesResult: Resultado del análisis de evidencias forenses
        """
        pass
