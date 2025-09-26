from typing import Dict, Any, Optional
from domain.entities.ocr_text import OCRText
from domain.ports.ocr_service import OCRServicePort
from adapters.persistence.helpers.FacturaHelpers.factura_parser import FacturaParser
from adapters.persistence.helpers.RecetaHelpers.receta_parser import extract_receta_data
from adapters.persistence.helpers.LaboratorioHelpers.laboratorio_parser import extract_laboratorio_data


class ValidateOCRTextUseCase:
    """Caso de uso para validar texto extraído por OCR"""
    
    def __init__(self, ocr_service: OCRServicePort):
        self.ocr_service = ocr_service
        self.factura_parser = FacturaParser()
    
    def execute_image(self, image_base64: str, tipo: str = "imagen") -> Dict[str, Any]:
        """Ejecuta la validación de texto OCR para una imagen"""
        try:
            # Extraer texto de la imagen
            ocr_text = self.ocr_service.extract_text_from_image(image_base64)
            
            # Validar calidad del texto
            is_valid = self.ocr_service.validate_text_quality(ocr_text)
            
            result = {
                "success": True,
                "text_raw": ocr_text.get_raw_text(),
                "text_normalized": ocr_text.get_clean_text(),
                "confidence_percentage": ocr_text.get_confidence_percentage()
            }
            
            # Si es una factura, receta o laboratorio, parsear los detalles
            if tipo.lower() == "factura":
                detalle = self._parse_factura_details(ocr_text.get_clean_text())
                if detalle:
                    result["detalle"] = detalle
            elif tipo.lower() == "receta":
                detalle = self._parse_receta_details(ocr_text.get_clean_text())
                if detalle:
                    result["detalle"] = detalle
            elif tipo.lower() == "laboratorio":
                detalle = self._parse_laboratorio_details(ocr_text.get_clean_text())
                if detalle:
                    result["detalle"] = detalle
            
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text_raw": "",
                "text_normalized": "",
                "confidence_percentage": 0.0
            }
    
    def execute_pdf(self, pdf_base64: str, tipo: str = "pdf") -> Dict[str, Any]:
        """Ejecuta la validación de texto OCR para un PDF"""
        try:
            # Extraer texto de todas las páginas del PDF
            ocr_texts = self.ocr_service.extract_text_from_pdf(pdf_base64)
            
            if not ocr_texts:
                return {
                    "success": False,
                    "error": "No se pudo extraer texto del PDF",
                    "text_raw": "",
                    "text_normalized": "",
                    "confidence_percentage": 0.0
                }
            
            # Combinar texto de todas las páginas
            combined_text_raw = "\n".join([text.get_raw_text() for text in ocr_texts])
            combined_text_normalized = "\n".join([text.get_clean_text() for text in ocr_texts])
            
            # Calcular confianza promedio de todas las páginas
            confidences = [text.get_confidence_percentage() for text in ocr_texts if text.get_confidence_percentage() > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            result = {
                "success": True,
                "text_raw": combined_text_raw,
                "text_normalized": combined_text_normalized,
                "confidence_percentage": round(avg_confidence, 2)
            }
            
            # Si es una factura, receta o laboratorio, parsear los detalles
            if tipo.lower() == "factura":
                detalle = self._parse_factura_details(combined_text_normalized)
                if detalle:
                    result["detalle"] = detalle
            elif tipo.lower() == "receta":
                detalle = self._parse_receta_details(combined_text_normalized)
                if detalle:
                    result["detalle"] = detalle
            elif tipo.lower() == "laboratorio":
                detalle = self._parse_laboratorio_details(combined_text_normalized)
                if detalle:
                    result["detalle"] = detalle
            
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text_raw": "",
                "text_normalized": "",
                "confidence_percentage": 0.0
            }
    
    def _parse_factura_details(self, text: str) -> Optional[Dict[str, Any]]:
        """Parsea los detalles de una factura desde el texto OCR"""
        try:
            detalle_factura = self.factura_parser.parse_factura(text)
            if detalle_factura:
                return detalle_factura.to_dict()
            return None
        except Exception as e:
            print(f"Error parseando detalles de factura: {e}")
            return None
    
    def _parse_receta_details(self, text: str) -> Optional[Dict[str, Any]]:
        """Parsea los detalles de una receta médica desde el texto OCR"""
        try:
            detalle_receta = extract_receta_data(text)
            if detalle_receta:
                return detalle_receta
            return None
        except Exception as e:
            print(f"Error parseando detalles de receta: {e}")
            return None
    
    def _parse_laboratorio_details(self, text: str) -> Optional[Dict[str, Any]]:
        """Parsea los detalles de un formulario de laboratorio desde el texto OCR"""
        try:
            detalle_laboratorio = extract_laboratorio_data(text)
            if detalle_laboratorio:
                return detalle_laboratorio
            return None
        except Exception as e:
            print(f"Error parseando detalles de laboratorio: {e}")
            return None