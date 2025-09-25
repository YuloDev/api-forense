import base64
import time
from typing import List
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image

from domain.ports.pdf_parsing_service import PDFParsingServicePort
from domain.entities.pdf_images import (
    PDFToImagesResult, PDFParsingRequest, PDFSourceInfo, 
    PageImage, ConversionMetrics, ConversionError
)
from config import MAX_PDF_BYTES


class PDFParsingServiceAdapter(PDFParsingServicePort):
    """Adaptador para el servicio de parsing de PDF a imágenes usando PyMuPDF"""
    
    def __init__(self):
        self.max_pdf_size = MAX_PDF_BYTES
        self.supported_dpi_range = (72, 600)
    
    def convert_pdf_to_images(self, request: PDFParsingRequest) -> PDFToImagesResult:
        """
        Convierte un PDF a imágenes usando PyMuPDF
        
        Args:
            request: Petición con los datos del PDF y configuración
            
        Returns:
            PDFToImagesResult: Resultado con las imágenes convertidas y metadatos
        """
        start_time = time.perf_counter()
        pages = []
        errors = []
        
        try:
            # Decodificar PDF
            pdf_bytes = base64.b64decode(request.pdf_base64, validate=True)
            
            # Validar tamaño
            if len(pdf_bytes) > self.max_pdf_size:
                error = ConversionError(
                    page_number=None,
                    error_type="file_size_error",
                    error_message=f"El PDF excede el tamaño máximo permitido ({self.max_pdf_size} bytes)"
                )
                return self._create_error_result(request, [error], start_time)
            
            # Abrir PDF
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Obtener información del PDF
            source_info = self._get_pdf_source_info(doc, len(pdf_bytes), request.filename)
            
            # Convertir cada página
            total_output_size = 0
            pages_converted = 0
            pages_failed = 0
            
            for page_num in range(len(doc)):
                try:
                    page_image = self._convert_page_to_image(doc, page_num, request.dpi)
                    pages.append(page_image)
                    total_output_size += page_image.file_size_bytes
                    pages_converted += 1
                except Exception as e:
                    error = ConversionError(
                        page_number=page_num + 1,
                        error_type="page_conversion_error",
                        error_message=f"Error al convertir página {page_num + 1}: {str(e)}"
                    )
                    errors.append(error)
                    pages_failed += 1
            
            doc.close()
            
            # Calcular métricas
            processing_time = int((time.perf_counter() - start_time) * 1000)
            average_page_size = total_output_size // pages_converted if pages_converted > 0 else 0
            
            metrics = ConversionMetrics(
                processing_time_ms=processing_time,
                dpi_requested=request.dpi,
                dpi_actual=request.dpi,
                total_output_size_bytes=total_output_size,
                average_page_size_bytes=average_page_size,
                pages_converted=pages_converted,
                pages_failed=pages_failed
            )
            
            # Determinar si fue exitoso
            success = pages_converted > 0
            message = f"PDF convertido exitosamente: {pages_converted} páginas procesadas"
            if pages_failed > 0:
                message += f", {pages_failed} páginas fallaron"
            
            return PDFToImagesResult(
                success=success,
                source_info=source_info,
                pages=pages,
                metrics=metrics,
                errors=errors,
                message=message
            )
            
        except Exception as e:
            error = ConversionError(
                page_number=None,
                error_type="general_error",
                error_message=f"Error general al procesar PDF: {str(e)}"
            )
            return self._create_error_result(request, [error], start_time)
    
    def validate_pdf_content(self, pdf_base64: str) -> tuple[bool, str]:
        """
        Valida que el contenido sea un PDF válido
        
        Args:
            pdf_base64: PDF codificado en base64
            
        Returns:
            tuple[bool, str]: (es_válido, mensaje_error)
        """
        try:
            # Decodificar base64
            pdf_bytes = base64.b64decode(pdf_base64, validate=True)
            
            # Verificar cabecera PDF
            if not pdf_bytes.startswith(b'%PDF-'):
                return False, "El archivo no tiene una cabecera PDF válida"
            
            # Intentar abrir con PyMuPDF
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Verificar que tenga páginas
            if len(doc) == 0:
                doc.close()
                return False, "El PDF no contiene páginas"
            
            doc.close()
            return True, "PDF válido"
            
        except Exception as e:
            return False, f"Error al validar PDF: {str(e)}"
    
    def get_pdf_metadata(self, pdf_base64: str) -> dict:
        """
        Extrae metadatos básicos del PDF
        
        Args:
            pdf_base64: PDF codificado en base64
            
        Returns:
            dict: Metadatos del PDF
        """
        try:
            pdf_bytes = base64.b64decode(pdf_base64, validate=True)
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            metadata = doc.metadata
            page_count = len(doc)
            
            # Verificar si tiene capa de texto
            has_text_layer = False
            if page_count > 0:
                first_page = doc.load_page(0)
                text = first_page.get_text()
                has_text_layer = len(text.strip()) > 0
            
            doc.close()
            
            return {
                "page_count": page_count,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "has_text_layer": has_text_layer,
                "is_encrypted": metadata.get("encryption", 0) != 0
            }
            
        except Exception as e:
            return {"error": f"Error al extraer metadatos: {str(e)}"}
    
    def _convert_page_to_image(self, doc: fitz.Document, page_num: int, dpi: int) -> PageImage:
        """Convierte una página específica a imagen"""
        page = doc.load_page(page_num)
        
        # Crear matriz de transformación para el DPI deseado
        zoom = dpi / 72.0  # fitz usa 72 DPI por defecto
        mat = fitz.Matrix(zoom, zoom)
        
        # Renderizar la página como imagen
        pix = page.get_pixmap(matrix=mat)
        
        # Convertir a bytes PNG
        img_data = pix.tobytes("png")
        
        # Convertir a base64
        img_b64 = base64.b64encode(img_data).decode('utf-8')
        
        # Crear objeto PageImage
        page_image = PageImage(
            page_number=page_num + 1,
            image_base64=img_b64,
            width_px=pix.width,
            height_px=pix.height,
            dpi=dpi,
            file_size_bytes=len(img_data)
        )
        
        # Limpiar memoria
        pix = None
        
        return page_image
    
    def _get_pdf_source_info(self, doc: fitz.Document, file_size: int, filename: str) -> PDFSourceInfo:
        """Obtiene información del PDF fuente"""
        metadata = doc.metadata
        
        # Parsear fechas si están disponibles
        creation_date = None
        modification_date = None
        
        try:
            if metadata.get("creationDate"):
                # Las fechas de PyMuPDF vienen en formato específico, intentar parsear
                creation_date = datetime.now()  # Simplificado por ahora
        except (ValueError, TypeError):
            pass
        
        try:
            if metadata.get("modDate"):
                modification_date = datetime.now()  # Simplificado por ahora
        except (ValueError, TypeError):
            pass
        
        # Verificar si tiene capa de texto
        has_text_layer = False
        if len(doc) > 0:
            try:
                first_page = doc.load_page(0)
                text = first_page.get_text()
                has_text_layer = len(text.strip()) > 0
            except (RuntimeError, ValueError):
                pass
        
        return PDFSourceInfo(
            filename=filename or f"pdf_{int(time.time())}.pdf",
            file_size_bytes=file_size,
            total_pages=len(doc),
            pdf_version=metadata.get("format", "PDF"),
            is_encrypted=metadata.get("encryption", 0) != 0,
            has_text_layer=has_text_layer,
            creation_date=creation_date,
            modification_date=modification_date
        )
    
    def _create_error_result(self, request: PDFParsingRequest, errors: List[ConversionError], start_time: float) -> PDFToImagesResult:
        """Crea un resultado de error"""
        processing_time = int((time.perf_counter() - start_time) * 1000)
        
        source_info = PDFSourceInfo(
            filename=request.filename or "error.pdf",
            file_size_bytes=0,
            total_pages=0
        )
        
        metrics = ConversionMetrics(
            processing_time_ms=processing_time,
            dpi_requested=request.dpi,
            dpi_actual=0,
            total_output_size_bytes=0,
            average_page_size_bytes=0,
            pages_converted=0,
            pages_failed=1
        )
        
        error_message = "; ".join([error.error_message for error in errors])
        
        return PDFToImagesResult(
            success=False,
            source_info=source_info,
            pages=[],
            metrics=metrics,
            errors=errors,
            message=f"Error en conversión: {error_message}"
        )
