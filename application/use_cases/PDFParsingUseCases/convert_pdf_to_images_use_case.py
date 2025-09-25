from typing import Dict, Any
import time

from domain.entities.pdf_images import PDFToImagesResult, PDFParsingRequest, PDFSourceInfo, ConversionMetrics, ConversionError
from domain.ports.pdf_parsing_service import PDFParsingServicePort


class ConvertPDFToImagesUseCase:
    """Caso de uso para convertir PDF a imágenes"""
    
    def __init__(self, pdf_parsing_service: PDFParsingServicePort):
        self.pdf_parsing_service = pdf_parsing_service
    
    def execute(self, pdf_base64: str, dpi: int = 150, filename: str = "", include_metadata: bool = True) -> Dict[str, Any]:
        """
        Ejecuta la conversión de PDF a imágenes
        
        Args:
            pdf_base64: PDF codificado en base64
            dpi: DPI para la conversión (72-600)
            filename: Nombre del archivo (opcional)
            include_metadata: Si incluir metadatos del PDF
            
        Returns:
            Dict[str, Any]: Resultado de la conversión en formato dict
        """
        start_time = time.perf_counter()
        
        try:
            # Crear petición
            request = PDFParsingRequest(
                pdf_base64=pdf_base64,
                dpi=dpi,
                filename=filename,
                include_metadata=include_metadata
            )
            
            # Validar petición
            is_valid, error_message = request.validate()
            if not is_valid:
                return self._create_error_response(error_message, start_time)
            
            # Validar contenido PDF
            is_valid_pdf, pdf_error = self.pdf_parsing_service.validate_pdf_content(pdf_base64)
            if not is_valid_pdf:
                return self._create_error_response(pdf_error, start_time)
            
            # Ejecutar conversión
            result = self.pdf_parsing_service.convert_pdf_to_images(request)
            
            # Si la conversión fue exitosa, devolver el resultado completo
            if result.success:
                return result.to_dict()
            else:
                # Si hubo errores, crear respuesta de error
                error_details = "; ".join([error.error_message for error in result.errors])
                return self._create_error_response(f"Error en conversión: {error_details}", start_time)
                
        except Exception as e:
            return self._create_error_response(f"Error inesperado: {str(e)}", start_time)
    
    def _create_error_response(self, error_message: str, start_time: float) -> Dict[str, Any]:
        """Crea una respuesta de error estándar"""
        processing_time = int((time.perf_counter() - start_time) * 1000)
        
        # Crear entidades con valores por defecto para errores
        source_info = PDFSourceInfo(
            filename="",
            file_size_bytes=0,
            total_pages=0
        )
        
        metrics = ConversionMetrics(
            processing_time_ms=processing_time,
            dpi_requested=0,
            dpi_actual=0,
            total_output_size_bytes=0,
            average_page_size_bytes=0,
            pages_converted=0,
            pages_failed=0
        )
        
        error = ConversionError(
            page_number=None,
            error_type="validation_error",
            error_message=error_message
        )
        
        error_result = PDFToImagesResult(
            success=False,
            source_info=source_info,
            pages=[],
            metrics=metrics,
            errors=[error],
            message=error_message
        )
        
        return error_result.to_dict()
