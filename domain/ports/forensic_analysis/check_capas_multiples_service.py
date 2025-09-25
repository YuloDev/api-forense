"""
Puerto/interfaz para el servicio de análisis de capas múltiples
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_capas_multiples_result import CapasMultiplesResult

class CheckCapasMultiplesServicePort(ABC):
    """Puerto para el servicio de análisis de capas múltiples"""
    
    @abstractmethod
    def analyze_capas_multiples(self, pdf_bytes: bytes, extracted_text: str = "") -> CapasMultiplesResult:
        """
        Analiza la presencia de capas múltiples en un PDF
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            extracted_text: Texto extraído del PDF (opcional)
            
        Returns:
            CapasMultiplesResult: Resultado del análisis
        """
        pass
