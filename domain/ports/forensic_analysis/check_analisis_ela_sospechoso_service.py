"""
Puerto para el servicio de análisis ELA sospechoso.

Define la interfaz que debe implementar el servicio de análisis ELA sospechoso.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_analisis_ela_sospechoso_result import AnalisisElaSospechosoResult


class AnalisisElaSospechosoServicePort(ABC):
    """Puerto para el servicio de análisis ELA sospechoso"""
    
    @abstractmethod
    def analyze_image_ela(self, image_bytes: bytes) -> AnalisisElaSospechosoResult:
        """
        Analiza áreas ELA sospechosas en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            AnalisisElaSospechosoResult: Resultado del análisis ELA sospechoso
        """
        pass
