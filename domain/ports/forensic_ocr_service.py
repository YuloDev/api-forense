from abc import ABC, abstractmethod
from typing import List
from domain.entities.forensic_ocr_details import ForensicOCRDetails


class ForensicOCRServicePort(ABC):
    """Puerto (interfaz) para el servicio forense de OCR"""
    
    @abstractmethod
    def extract_forensic_details_from_image(self, image_base64: str) -> ForensicOCRDetails:
        """Extrae detalles forenses de una imagen codificada en base64"""
        pass
    
    @abstractmethod
    def extract_forensic_details_from_pdf(self, pdf_base64: str) -> ForensicOCRDetails:
        """Extrae detalles forenses de un PDF codificado en base64"""
        pass
