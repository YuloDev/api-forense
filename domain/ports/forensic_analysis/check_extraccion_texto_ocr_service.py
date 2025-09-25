"""
Puerto para el servicio de análisis de extracción de texto OCR.

Define la interfaz que debe implementar el servicio de análisis de extracción de texto OCR.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_extraccion_texto_ocr_result import ExtraccionTextoOcrResult


class ExtraccionTextoOcrServicePort(ABC):
    """Puerto para el servicio de análisis de extracción de texto OCR"""
    
    @abstractmethod
    def analyze_image_ocr_extraction(self, image_bytes: bytes) -> ExtraccionTextoOcrResult:
        """
        Analiza la extracción de texto OCR en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            ExtraccionTextoOcrResult: Resultado del análisis de extracción de texto OCR
        """
        pass
