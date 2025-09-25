"""
Caso de uso para análisis de cifrado y permisos especiales.

Orquesta el análisis de cifrado y permisos especiales en documentos PDF e imágenes.
"""

from typing import Dict, Any
from domain.ports.forensic_analysis.check_cifrado_permisos_extra_service import CifradoPermisosExtraServicePort
from domain.entities.forensic_analysis.check_cifrado_permisos_extra_result import CifradoPermisosExtraResult


class AnalyzeCifradoPermisosExtraUseCase:
    """Caso de uso para análisis de cifrado y permisos especiales"""
    
    def __init__(self, cifrado_permisos_service: CifradoPermisosExtraServicePort):
        self.cifrado_permisos_service = cifrado_permisos_service
    
    def execute_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de cifrado y permisos especiales para un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.cifrado_permisos_service.analyze_pdf_cifrado_permisos(pdf_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = CifradoPermisosExtraResult.create_error_result(
                f"Error en análisis de cifrado y permisos PDF: {str(e)}"
            )
            return error_result.to_dict()
    
    def execute_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Ejecuta el análisis de cifrado y permisos especiales para una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con el resultado del análisis
        """
        try:
            result = self.cifrado_permisos_service.analyze_image_cifrado_permisos(image_bytes)
            return result.to_dict()
        except Exception as e:
            error_result = CifradoPermisosExtraResult.create_error_result(
                f"Error en análisis de cifrado y permisos de imagen: {str(e)}"
            )
            return error_result.to_dict()
