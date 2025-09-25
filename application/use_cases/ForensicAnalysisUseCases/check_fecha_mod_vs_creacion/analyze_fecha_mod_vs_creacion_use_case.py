"""
Caso de uso para análisis de fecha modificación vs creación.

Orquesta el análisis temporal de documentos PDF e imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_fecha_mod_vs_creacion_service import FechaModVsCreacionServicePort
from domain.entities.forensic_analysis.check_fecha_mod_vs_creacion_result import FechaModVsCreacionResult


class AnalyzeFechaModVsCreacionUseCase:
    """Caso de uso para análisis de fecha modificación vs creación"""
    
    def __init__(self, fecha_service: FechaModVsCreacionServicePort):
        self.fecha_service = fecha_service
    
    def execute_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de fechas para un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.fecha_service.analyze_pdf_dates(pdf_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = FechaModVsCreacionResult.create_error_result(
                f"Error en análisis PDF: {str(e)}", 
                "pdf"
            )
            return error_result.to_dict()
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de fechas para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.fecha_service.analyze_image_dates(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = FechaModVsCreacionResult.create_error_result(
                f"Error en análisis imagen: {str(e)}", 
                "image"
            )
            return error_result.to_dict()
