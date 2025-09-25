"""
Puerto para el servicio de detección de capas ocultas.

Define la interfaz que debe implementar el servicio de detección de capas ocultas.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.entities.forensic_analysis.check_capas_ocultas_result import CapasOcultasResult


class CapasOcultasServicePort(ABC):
    """Puerto para el servicio de detección de capas ocultas"""
    
    @abstractmethod
    def analyze_image_capas_ocultas(self, image_bytes: bytes) -> CapasOcultasResult:
        """
        Analiza capas ocultas en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            CapasOcultasResult: Resultado del análisis de capas ocultas
        """
        pass
