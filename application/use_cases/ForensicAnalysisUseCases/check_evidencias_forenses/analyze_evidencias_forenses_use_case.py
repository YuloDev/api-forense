"""
Caso de uso para análisis de evidencias forenses.

Orquesta el análisis de evidencias forenses en imágenes usando la lógica existente.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_evidencias_forenses_service import EvidenciasForensesServicePort
from domain.entities.forensic_analysis.check_evidencias_forenses_result import EvidenciasForensesResult


class AnalyzeEvidenciasForensesUseCase:
    """Caso de uso para análisis de evidencias forenses"""
    
    def __init__(self, evidencias_forenses_service: EvidenciasForensesServicePort):
        self.evidencias_forenses_service = evidencias_forenses_service
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de evidencias forenses para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.evidencias_forenses_service.analyze_image_evidencias_forenses(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = EvidenciasForensesResult.create_error_result(
                f"Error en análisis de evidencias forenses: {str(e)}"
            )
            return error_result.to_dict()
