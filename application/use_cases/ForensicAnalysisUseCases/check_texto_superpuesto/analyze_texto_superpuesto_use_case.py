"""
Caso de uso para detección de texto superpuesto.

Orquesta la detección de texto superpuesto en imágenes usando la lógica existente.
"""

from typing import Dict, Any, List, Optional
from domain.ports.forensic_analysis.check_texto_superpuesto_service import TextoSuperpuestoServicePort
from domain.entities.forensic_analysis.check_texto_superpuesto_result import TextoSuperpuestoResult


class AnalyzeTextoSuperpuestoUseCase:
    """Caso de uso para detección de texto superpuesto"""
    
    def __init__(self, texto_superpuesto_service: TextoSuperpuestoServicePort):
        self.texto_superpuesto_service = texto_superpuesto_service
    
    def execute_image(self, image_bytes: bytes, ocr_tokens: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Ejecuta la detección de texto superpuesto para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            ocr_tokens: Lista opcional de tokens OCR
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.texto_superpuesto_service.analyze_image_texto_superpuesto(image_bytes, ocr_tokens)
            return result.to_dict()
        except Exception as e:
            error_result = TextoSuperpuestoResult.create_error_result(
                f"Error en detección de texto superpuesto: {str(e)}"
            )
            return error_result.to_dict()
