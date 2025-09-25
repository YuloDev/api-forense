"""
Caso de uso para análisis de extracción de texto OCR.

Orquesta el análisis de extracción de texto OCR en imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_extraccion_texto_ocr_service import ExtraccionTextoOcrServicePort
from domain.entities.forensic_analysis.check_extraccion_texto_ocr_result import ExtraccionTextoOcrResult


class AnalyzeExtraccionTextoOcrUseCase:
    """Caso de uso para análisis de extracción de texto OCR"""
    
    def __init__(self, ocr_extraction_service: ExtraccionTextoOcrServicePort):
        self.ocr_extraction_service = ocr_extraction_service
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de extracción de texto OCR para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.ocr_extraction_service.analyze_image_ocr_extraction(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = ExtraccionTextoOcrResult.create_error_result(
                f"Error en análisis de extracción OCR de imagen: {str(e)}"
            )
            return error_result.to_dict()
