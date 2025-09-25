"""
Puerto para el servicio de análisis de cifrado y permisos especiales.

Define la interfaz que debe implementar el servicio de análisis de cifrado y permisos especiales.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_cifrado_permisos_extra_result import CifradoPermisosExtraResult


class CifradoPermisosExtraServicePort(ABC):
    """Puerto para el servicio de análisis de cifrado y permisos especiales"""
    
    @abstractmethod
    def analyze_pdf_cifrado_permisos(self, pdf_bytes: bytes) -> CifradoPermisosExtraResult:
        """
        Analiza cifrado y permisos especiales en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            CifradoPermisosExtraResult: Resultado del análisis de cifrado y permisos especiales
        """
        pass
    
    @abstractmethod
    def analyze_image_cifrado_permisos(self, image_bytes: bytes) -> CifradoPermisosExtraResult:
        """
        Analiza cifrado y permisos especiales en una imagen (siempre retorna sin cifrado).
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            CifradoPermisosExtraResult: Resultado del análisis de cifrado y permisos especiales
        """
        pass
