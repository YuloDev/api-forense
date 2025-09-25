"""
Caso de uso para análisis de alineación de texto.

Orquesta el análisis de alineación de texto basado en resultados OCR.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_alineacion_texto_service import AlineacionTextoServicePort
from domain.entities.forensic_analysis.check_alineacion_texto_result import AlineacionTextoResult


class AnalyzeAlineacionTextoUseCase:
    """Caso de uso para análisis de alineación de texto"""
    
    def __init__(self, alignment_service: AlineacionTextoServicePort):
        self.alignment_service = alignment_service
    
    def execute(self, ocr_result: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        """
        Ejecuta el análisis de alineación de texto.
        
        Args:
            ocr_result: Resultado del análisis OCR
            source_type: Tipo de archivo ("pdf" o "image")
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.alignment_service.analyze_text_alignment(ocr_result, source_type)
            return result.to_dict()
        except Exception as e:
            error_result = AlineacionTextoResult.create_error_result(
                f"Error en análisis de alineación de texto: {str(e)}"
            )
            return error_result.to_dict()
