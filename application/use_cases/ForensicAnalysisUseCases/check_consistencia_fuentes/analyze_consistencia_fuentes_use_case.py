"""
Caso de uso para análisis de consistencia de fuentes.

Orquesta el análisis de consistencia de fuentes usando el resultado del OCR.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_consistencia_fuentes_service import ConsistenciaFuentesServicePort
from domain.entities.forensic_analysis.check_consistencia_fuentes_result import ConsistenciaFuentesResult


class AnalyzeConsistenciaFuentesUseCase:
    """Caso de uso para análisis de consistencia de fuentes"""
    
    def __init__(self, font_consistency_service: ConsistenciaFuentesServicePort):
        self.font_consistency_service = font_consistency_service
    
    def execute(self, ocr_result: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        """
        Ejecuta el análisis de consistencia de fuentes.
        
        Args:
            ocr_result: Resultado del análisis OCR forense
            source_type: Tipo de fuente ("pdf" o "image")
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.font_consistency_service.analyze_font_consistency(ocr_result, source_type)
            return result.to_dict()
        except Exception as e:
            error_result = ConsistenciaFuentesResult.create_error_result(
                f"Error en análisis de consistencia de fuentes: {str(e)}"
            )
            return error_result.to_dict()
