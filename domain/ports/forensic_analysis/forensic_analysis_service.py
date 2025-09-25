"""
Puerto/Interface para servicios de análisis forense
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis import ForensicAnalysisResult, AnalysisType

class ForensicAnalysisServicePort(ABC):
    """Puerto para servicios de análisis forense"""
    
    @abstractmethod
    def analyze_pdf_forensic(self, pdf_base64: str) -> Dict[str, Any]:
        """
        Analiza un PDF desde el punto de vista forense
        
        Args:
            pdf_base64: PDF codificado en base64
            
        Returns:
            Dict con resultado del análisis forense
        """
        pass
    
    @abstractmethod
    def analyze_image_forensic(self, image_base64: str) -> Dict[str, Any]:
        """
        Analiza una imagen desde el punto de vista forense
        
        Args:
            image_base64: Imagen codificada en base64
            
        Returns:
            Dict con resultado del análisis forense
        """
        pass
    
    @abstractmethod
    def get_analysis_capabilities(self) -> Dict[str, Any]:
        """
        Obtiene las capacidades del servicio de análisis forense
        
        Returns:
            Dict con información de capacidades
        """
        pass
