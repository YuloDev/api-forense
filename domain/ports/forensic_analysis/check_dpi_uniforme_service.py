"""
Puerto para el servicio de análisis de uniformidad DPI.

Define la interfaz que debe implementar el servicio de análisis de uniformidad DPI.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_dpi_uniforme_result import DpiUniformeResult


class DpiUniformeServicePort(ABC):
    """Puerto para el servicio de análisis de uniformidad DPI"""
    
    @abstractmethod
    def analyze_pdf_dpi(self, pdf_bytes: bytes) -> DpiUniformeResult:
        """
        Analiza la uniformidad DPI de un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            DpiUniformeResult: Resultado del análisis de uniformidad DPI
        """
        pass
    
    @abstractmethod
    def analyze_image_dpi(self, image_bytes: bytes) -> DpiUniformeResult:
        """
        Analiza la uniformidad DPI de una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            DpiUniformeResult: Resultado del análisis de uniformidad DPI
        """
        pass
