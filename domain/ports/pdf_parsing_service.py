from abc import ABC, abstractmethod
from domain.entities.pdf_images import PDFToImagesResult, PDFParsingRequest


class PDFParsingServicePort(ABC):
    """Puerto (interfaz) para el servicio de parsing de PDF a imágenes"""
    
    @abstractmethod
    def convert_pdf_to_images(self, request: PDFParsingRequest) -> PDFToImagesResult:
        """
        Convierte un PDF a imágenes
        
        Args:
            request: Petición con los datos del PDF y configuración
            
        Returns:
            PDFToImagesResult: Resultado con las imágenes convertidas y metadatos
        """
        pass
    
    @abstractmethod
    def validate_pdf_content(self, pdf_base64: str) -> tuple[bool, str]:
        """
        Valida que el contenido sea un PDF válido
        
        Args:
            pdf_base64: PDF codificado en base64
            
        Returns:
            tuple[bool, str]: (es_válido, mensaje_error)
        """
        pass
    
    @abstractmethod
    def get_pdf_metadata(self, pdf_base64: str) -> dict:
        """
        Extrae metadatos básicos del PDF
        
        Args:
            pdf_base64: PDF codificado en base64
            
        Returns:
            dict: Metadatos del PDF
        """
        pass
