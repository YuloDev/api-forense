"""
Caso de uso para análisis de JavaScript embebido.

Orquesta el análisis de JavaScript embebido en documentos PDF e imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_javascript_embebido_service import JavascriptEmbebidoServicePort
from domain.entities.forensic_analysis.check_javascript_embebido_result import JavascriptEmbebidoResult


class AnalyzeJavascriptEmbebidoUseCase:
    """Caso de uso para análisis de JavaScript embebido"""
    
    def __init__(self, javascript_service: JavascriptEmbebidoServicePort):
        self.javascript_service = javascript_service
    
    def execute_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de JavaScript embebido para un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.javascript_service.analyze_pdf_javascript(pdf_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = JavascriptEmbebidoResult.create_error_result(
                f"Error en análisis de JavaScript PDF: {str(e)}"
            )
            return error_result.to_dict()
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de JavaScript embebido para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.javascript_service.analyze_image_javascript(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = JavascriptEmbebidoResult.create_error_result(
                f"Error en análisis de JavaScript de imagen: {str(e)}"
            )
            return error_result.to_dict()
