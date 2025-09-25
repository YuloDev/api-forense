"""
Caso de uso para análisis de actualizaciones incrementales.

Orquesta el análisis de actualizaciones incrementales en documentos PDF e imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_actualizaciones_incrementales_service import ActualizacionesIncrementalesServicePort
from domain.entities.forensic_analysis.check_actualizaciones_incrementales_result import ActualizacionesIncrementalesResult


class AnalyzeActualizacionesIncrementalesUseCase:
    """Caso de uso para análisis de actualizaciones incrementales"""
    
    def __init__(self, actualizaciones_service: ActualizacionesIncrementalesServicePort):
        self.actualizaciones_service = actualizaciones_service
    
    def execute_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de actualizaciones incrementales para un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.actualizaciones_service.analyze_pdf_actualizaciones(pdf_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = ActualizacionesIncrementalesResult.create_error_result(
                f"Error en análisis de actualizaciones PDF: {str(e)}"
            )
            return error_result.to_dict()
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de actualizaciones incrementales para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.actualizaciones_service.analyze_image_actualizaciones(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = ActualizacionesIncrementalesResult.create_error_result(
                f"Error en análisis de actualizaciones de imagen: {str(e)}"
            )
            return error_result.to_dict()
