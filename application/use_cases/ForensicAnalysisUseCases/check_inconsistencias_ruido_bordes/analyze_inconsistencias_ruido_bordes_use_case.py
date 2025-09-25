"""
Caso de uso para análisis de inconsistencias en ruido y bordes.

Orquesta el análisis de inconsistencias en ruido y bordes en imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_inconsistencias_ruido_bordes_service import InconsistenciasRuidoBordesServicePort
from domain.entities.forensic_analysis.check_inconsistencias_ruido_bordes_result import InconsistenciasRuidoBordesResult


class AnalyzeInconsistenciasRuidoBordesUseCase:
    """Caso de uso para análisis de inconsistencias en ruido y bordes"""
    
    def __init__(self, ruido_bordes_service: InconsistenciasRuidoBordesServicePort):
        self.ruido_bordes_service = ruido_bordes_service
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de inconsistencias en ruido y bordes para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.ruido_bordes_service.analyze_image_ruido_bordes(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = InconsistenciasRuidoBordesResult.create_error_result(
                f"Error en análisis de inconsistencias de ruido y bordes: {str(e)}"
            )
            return error_result.to_dict()
