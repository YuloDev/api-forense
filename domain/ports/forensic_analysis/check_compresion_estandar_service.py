"""
Puerto para el servicio de análisis de compresión estándar.

Define la interfaz que debe implementar el servicio de análisis de compresión estándar.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_compresion_estandar_result import CompresionEstandarResult


class CompresionEstandarServicePort(ABC):
    """Puerto para el servicio de análisis de compresión estándar"""
    
    @abstractmethod
    def analyze_pdf_compression(self, pdf_bytes: bytes) -> CompresionEstandarResult:
        """
        Analiza la compresión estándar de un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            CompresionEstandarResult: Resultado del análisis de compresión estándar
        """
        pass
    
    @abstractmethod
    def analyze_image_compression(self, image_bytes: bytes) -> CompresionEstandarResult:
        """
        Analiza la compresión estándar de una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            CompresionEstandarResult: Resultado del análisis de compresión estándar
        """
        pass
