from abc import ABC, abstractmethod
from typing import List
from domain.entities.ocr_text import OCRText


class OCRServicePort(ABC):
    """Puerto (interfaz) para el servicio de OCR"""
    
    @abstractmethod
    def extract_text_from_image(self, image_base64: str) -> OCRText:
        """Extrae texto de una imagen codificada en base64"""
        pass
    
    @abstractmethod
    def extract_text_from_pdf(self, pdf_base64: str) -> List[OCRText]:
        """Extrae texto de un PDF codificado en base64"""
        pass
    
    @abstractmethod
    def validate_text_quality(self, ocr_text: OCRText) -> bool:
        """Valida la calidad del texto extraído"""
        pass
