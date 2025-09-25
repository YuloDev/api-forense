"""
Puerto para el servicio de análisis de JavaScript embebido.

Define la interfaz que debe implementar el servicio de análisis de JavaScript embebido.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_javascript_embebido_result import JavascriptEmbebidoResult


class JavascriptEmbebidoServicePort(ABC):
    """Puerto para el servicio de análisis de JavaScript embebido"""
    
    @abstractmethod
    def analyze_pdf_javascript(self, pdf_bytes: bytes) -> JavascriptEmbebidoResult:
        """
        Analiza JavaScript embebido en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            JavascriptEmbebidoResult: Resultado del análisis de JavaScript embebido
        """
        pass
    
    @abstractmethod
    def analyze_image_javascript(self, image_bytes: bytes) -> JavascriptEmbebidoResult:
        """
        Analiza JavaScript embebido en una imagen (siempre retorna sin JavaScript).
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            JavascriptEmbebidoResult: Resultado del análisis de JavaScript embebido
        """
        pass
