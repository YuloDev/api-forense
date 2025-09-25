"""
Caso de uso para análisis de software conocido.

Orquesta el análisis de software usado para crear PDFs.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_software_conocido_service import SoftwareConocidoServicePort
from domain.entities.forensic_analysis.check_software_conocido_result import SoftwareConocidoResult


class AnalyzeSoftwareConocidoUseCase:
    """Caso de uso para análisis de software conocido"""
    
    def __init__(self, software_service: SoftwareConocidoServicePort):
        self.software_service = software_service
    
    def execute_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de software para un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.software_service.analyze_pdf_software(pdf_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = SoftwareConocidoResult.create_error_result(
                f"Error en análisis PDF: {str(e)}"
            )
            return error_result.to_dict()
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de software para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.software_service.analyze_image_software(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = SoftwareConocidoResult.create_error_result(
                f"Error en análisis de imagen: {str(e)}"
            )
            return error_result.to_dict()
