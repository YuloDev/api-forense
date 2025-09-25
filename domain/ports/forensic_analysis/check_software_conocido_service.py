"""
Puerto para el servicio de análisis de software conocido.

Define la interfaz que debe implementar el servicio de análisis de software.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_software_conocido_result import SoftwareConocidoResult


class SoftwareConocidoServicePort(ABC):
    """Puerto para el servicio de análisis de software conocido"""
    
    @abstractmethod
    def analyze_pdf_software(self, pdf_bytes: bytes) -> SoftwareConocidoResult:
        """
        Analiza el software usado para crear un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            SoftwareConocidoResult: Resultado del análisis de software
        """
        pass
    
    @abstractmethod
    def analyze_image_software(self, image_bytes: bytes) -> SoftwareConocidoResult:
        """
        Analiza el software usado para crear una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            SoftwareConocidoResult: Resultado del análisis de software
        """
        pass
