"""
Puerto para el servicio de análisis de consistencia de fuentes.

Define la interfaz que debe implementar el servicio de análisis de consistencia de fuentes.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_consistencia_fuentes_result import ConsistenciaFuentesResult


class ConsistenciaFuentesServicePort(ABC):
    """Puerto para el servicio de análisis de consistencia de fuentes"""
    
    @abstractmethod
    def analyze_font_consistency(self, ocr_result: Dict[str, Any], source_type: str) -> ConsistenciaFuentesResult:
        """
        Analiza la consistencia de fuentes usando el resultado del OCR.
        
        Args:
            ocr_result: Resultado del análisis OCR forense
            source_type: Tipo de fuente ("pdf" o "image")
            
        Returns:
            ConsistenciaFuentesResult: Resultado del análisis de consistencia de fuentes
        """
        pass
