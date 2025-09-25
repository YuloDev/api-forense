"""
Puerto para el servicio de detección de texto superpuesto.

Define la interfaz que debe implementar el servicio de detección de texto superpuesto.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from domain.entities.forensic_analysis.check_texto_superpuesto_result import TextoSuperpuestoResult


class TextoSuperpuestoServicePort(ABC):
    """Puerto para el servicio de detección de texto superpuesto"""
    
    @abstractmethod
    def analyze_image_texto_superpuesto(self, image_bytes: bytes, ocr_tokens: Optional[List[Dict[str, Any]]] = None) -> TextoSuperpuestoResult:
        """
        Analiza texto superpuesto en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            ocr_tokens: Lista opcional de tokens OCR con formato {"text": str, "bbox": [x,y,w,h]}
            
        Returns:
            TextoSuperpuestoResult: Resultado del análisis de texto superpuesto
        """
        pass
