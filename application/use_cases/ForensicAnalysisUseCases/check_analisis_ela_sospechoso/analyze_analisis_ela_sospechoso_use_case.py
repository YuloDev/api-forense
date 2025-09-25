"""
Caso de uso para análisis ELA sospechoso.

Orquesta el análisis de áreas ELA sospechosas en imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_analisis_ela_sospechoso_service import AnalisisElaSospechosoServicePort
from domain.entities.forensic_analysis.check_analisis_ela_sospechoso_result import AnalisisElaSospechosoResult


class AnalyzeAnalisisElaSospechosoUseCase:
    """Caso de uso para análisis ELA sospechoso"""
    
    def __init__(self, ela_service: AnalisisElaSospechosoServicePort):
        self.ela_service = ela_service
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis ELA sospechoso para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.ela_service.analyze_image_ela(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = AnalisisElaSospechosoResult.create_error_result(
                f"Error en análisis ELA sospechoso: {str(e)}"
            )
            return error_result.to_dict()
