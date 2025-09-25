from typing import Dict, Any
from domain.entities.ocr_text import OCRText
from domain.ports.ocr_service import OCRServicePort


class ValidateOCRTextUseCase:
    """Caso de uso para validar texto extraído por OCR"""
    
    def __init__(self, ocr_service: OCRServicePort):
        self.ocr_service = ocr_service
    
    def execute_image(self, image_base64: str) -> Dict[str, Any]:
        """Ejecuta la validación de texto OCR para una imagen"""
        try:
            # Extraer texto de la imagen
            ocr_text = self.ocr_service.extract_text_from_image(image_base64)
            
            # Validar calidad del texto
            is_valid = self.ocr_service.validate_text_quality(ocr_text)
            
            return {
                "success": True,
                "text_raw": ocr_text.get_raw_text(),
                "text_normalized": ocr_text.get_clean_text()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text_raw": "",
                "text_normalized": ""
            }
    
    def execute_pdf(self, pdf_base64: str) -> Dict[str, Any]:
        """Ejecuta la validación de texto OCR para un PDF"""
        try:
            # Extraer texto de todas las páginas del PDF
            ocr_texts = self.ocr_service.extract_text_from_pdf(pdf_base64)
            
            if not ocr_texts:
                return {
                    "success": False,
                    "error": "No se pudo extraer texto del PDF",
                    "text_raw": "",
                    "text_normalized": ""
                }
            
            # Combinar texto de todas las páginas
            combined_text_raw = "\n".join([text.get_raw_text() for text in ocr_texts])
            combined_text_normalized = "\n".join([text.get_clean_text() for text in ocr_texts])
            
            return {
                "success": True,
                "text_raw": combined_text_raw,
                "text_normalized": combined_text_normalized
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text_raw": "",
                "text_normalized": ""
            }
