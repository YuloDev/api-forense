"""
Caso de uso para análisis de compresión estándar.

Orquesta el análisis de compresión estándar en documentos PDF e imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_compresion_estandar_service import CompresionEstandarServicePort
from domain.entities.forensic_analysis.check_compresion_estandar_result import CompresionEstandarResult


class AnalyzeCompresionEstandarUseCase:
    """Caso de uso para análisis de compresión estándar"""
    
    def __init__(self, compression_service: CompresionEstandarServicePort):
        self.compression_service = compression_service
    
    def execute_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de compresión estándar para un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.compression_service.analyze_pdf_compression(pdf_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = CompresionEstandarResult.create_error_result(
                f"Error en análisis de compresión PDF: {str(e)}"
            )
            return error_result.to_dict()
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de compresión estándar para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.compression_service.analyze_image_compression(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = CompresionEstandarResult.create_error_result(
                f"Error en análisis de compresión de imagen: {str(e)}"
            )
            return error_result.to_dict()
