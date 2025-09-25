"""
Puerto para el servicio de análisis de fecha modificación vs creación.

Define la interfaz que debe implementar el servicio de análisis temporal.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_fecha_mod_vs_creacion_result import FechaModVsCreacionResult


class FechaModVsCreacionServicePort(ABC):
    """Puerto para el servicio de análisis de fecha modificación vs creación"""
    
    @abstractmethod
    def analyze_pdf_dates(self, pdf_bytes: bytes) -> FechaModVsCreacionResult:
        """
        Analiza las fechas de creación y modificación de un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            FechaModVsCreacionResult: Resultado del análisis temporal
        """
        pass
    
    @abstractmethod
    def analyze_image_dates(self, image_bytes: bytes) -> FechaModVsCreacionResult:
        """
        Analiza las fechas de creación y modificación de una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            FechaModVsCreacionResult: Resultado del análisis temporal
        """
        pass
