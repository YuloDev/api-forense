"""
Caso de uso para análisis de uniformidad DPI.

Orquesta el análisis de uniformidad DPI en documentos PDF e imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_dpi_uniforme_service import DpiUniformeServicePort
from domain.entities.forensic_analysis.check_dpi_uniforme_result import DpiUniformeResult


class AnalyzeDpiUniformeUseCase:
    """Caso de uso para análisis de uniformidad DPI"""
    
    def __init__(self, dpi_service: DpiUniformeServicePort):
        self.dpi_service = dpi_service
    
    def execute_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de uniformidad DPI para un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.dpi_service.analyze_pdf_dpi(pdf_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = DpiUniformeResult.create_error_result(
                f"Error en análisis DPI PDF: {str(e)}"
            )
            return error_result.to_dict()
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de uniformidad DPI para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.dpi_service.analyze_image_dpi(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = DpiUniformeResult.create_error_result(
                f"Error en análisis DPI de imagen: {str(e)}"
            )
            return error_result.to_dict()
