"""
Puerto para el servicio de análisis de alineación de texto.

Define la interfaz que debe implementar el servicio de análisis de alineación de texto.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_alineacion_texto_result import AlineacionTextoResult


class AlineacionTextoServicePort(ABC):
    """Puerto para el servicio de análisis de alineación de texto"""
    
    @abstractmethod
    def analyze_text_alignment(self, ocr_result: Dict[str, Any], source_type: str) -> AlineacionTextoResult:
        """
        Analiza la alineación de texto basado en resultado OCR.
        
        Args:
            ocr_result: Resultado del análisis OCR
            source_type: Tipo de archivo ("pdf" o "image")
            
        Returns:
            AlineacionTextoResult: Resultado del análisis de alineación de texto
        """
        pass
