"""
Caso de uso para detección de capas ocultas.

Orquesta la detección de capas ocultas en imágenes usando la lógica existente.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_capas_ocultas_service import CapasOcultasServicePort
from domain.entities.forensic_analysis.check_capas_ocultas_result import CapasOcultasResult


class AnalyzeCapasOcultasUseCase:
    """Caso de uso para detección de capas ocultas"""
    
    def __init__(self, capas_ocultas_service: CapasOcultasServicePort):
        self.capas_ocultas_service = capas_ocultas_service
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta la detección de capas ocultas para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.capas_ocultas_service.analyze_image_capas_ocultas(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = CapasOcultasResult.create_error_result(
                f"Error en detección de capas ocultas: {str(e)}"
            )
            return error_result.to_dict()
