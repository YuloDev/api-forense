"""
Puerto para el servicio de análisis de actualizaciones incrementales.

Define la interfaz que debe implementar el servicio de análisis de actualizaciones incrementales.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_actualizaciones_incrementales_result import ActualizacionesIncrementalesResult


class ActualizacionesIncrementalesServicePort(ABC):
    """Puerto para el servicio de análisis de actualizaciones incrementales"""
    
    @abstractmethod
    def analyze_pdf_actualizaciones(self, pdf_bytes: bytes) -> ActualizacionesIncrementalesResult:
        """
        Analiza actualizaciones incrementales en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            ActualizacionesIncrementalesResult: Resultado del análisis de actualizaciones incrementales
        """
        pass
    
    @abstractmethod
    def analyze_image_actualizaciones(self, image_bytes: bytes) -> ActualizacionesIncrementalesResult:
        """
        Analiza actualizaciones incrementales en una imagen (siempre retorna sin actualizaciones).
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            ActualizacionesIncrementalesResult: Resultado del análisis de actualizaciones incrementales
        """
        pass
