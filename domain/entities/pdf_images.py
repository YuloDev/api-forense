from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class PageImage:
    """Representa una imagen de página PDF"""
    page_number: int
    image_base64: str
    width_px: int
    height_px: int
    dpi: int
    file_size_bytes: int
    
    def get_resolution_info(self) -> str:
        """Retorna información de resolución"""
        return f"{self.width_px}x{self.height_px} @ {self.dpi}DPI"


@dataclass
class PDFSourceInfo:
    """Información del PDF fuente"""
    filename: str
    file_size_bytes: int
    total_pages: int
    pdf_version: Optional[str] = None
    is_encrypted: bool = False
    has_text_layer: bool = False
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None


@dataclass
class ConversionMetrics:
    """Métricas del proceso de conversión"""
    processing_time_ms: int
    dpi_requested: int
    dpi_actual: int
    total_output_size_bytes: int
    average_page_size_bytes: int
    pages_converted: int
    pages_failed: int
    
    def get_success_rate(self) -> float:
        """Calcula la tasa de éxito de conversión"""
        total_attempted = self.pages_converted + self.pages_failed
        if total_attempted == 0:
            return 0.0
        return (self.pages_converted / total_attempted) * 100


@dataclass
class ConversionError:
    """Error durante la conversión"""
    page_number: Optional[int]
    error_type: str
    error_message: str
    error_details: Optional[str] = None


@dataclass
class PDFToImagesResult:
    """Resultado completo de la conversión PDF a imágenes"""
    success: bool
    source_info: PDFSourceInfo
    pages: List[PageImage]
    metrics: ConversionMetrics
    errors: List[ConversionError] = field(default_factory=list)
    message: str = ""
    version: str = "pdf-parser-1.0.0"
    
    def get_total_pages(self) -> int:
        """Retorna el número total de páginas convertidas"""
        return len(self.pages)
    
    def get_successful_pages(self) -> List[PageImage]:
        """Retorna solo las páginas convertidas exitosamente"""
        return [page for page in self.pages if page.image_base64]
    
    def has_errors(self) -> bool:
        """Verifica si hay errores en la conversión"""
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a diccionario para serialización JSON"""
        return {
            "success": self.success,
            "source_info": {
                "filename": self.source_info.filename,
                "file_size_bytes": self.source_info.file_size_bytes,
                "total_pages": self.source_info.total_pages,
                "pdf_version": self.source_info.pdf_version,
                "is_encrypted": self.source_info.is_encrypted,
                "has_text_layer": self.source_info.has_text_layer,
                "creation_date": self.source_info.creation_date.isoformat() if self.source_info.creation_date else None,
                "modification_date": self.source_info.modification_date.isoformat() if self.source_info.modification_date else None
            },
            "pages": [
                {
                    "page_number": page.page_number,
                    "image_base64": page.image_base64,
                    "width_px": page.width_px,
                    "height_px": page.height_px,
                    "dpi": page.dpi,
                    "file_size_bytes": page.file_size_bytes,
                    "resolution_info": page.get_resolution_info()
                } for page in self.pages
            ],
            "metrics": {
                "processing_time_ms": self.metrics.processing_time_ms,
                "dpi_requested": self.metrics.dpi_requested,
                "dpi_actual": self.metrics.dpi_actual,
                "total_output_size_bytes": self.metrics.total_output_size_bytes,
                "average_page_size_bytes": self.metrics.average_page_size_bytes,
                "pages_converted": self.metrics.pages_converted,
                "pages_failed": self.metrics.pages_failed,
                "success_rate": self.metrics.get_success_rate()
            },
            "errors": [
                {
                    "page_number": error.page_number,
                    "error_type": error.error_type,
                    "error_message": error.error_message,
                    "error_details": error.error_details
                } for error in self.errors
            ],
            "total_paginas": self.get_total_pages(),
            "imagenes": [page.image_base64 for page in self.get_successful_pages()],
            "mensaje": self.message,
            "version": self.version
        }


@dataclass
class PDFParsingRequest:
    """Petición para parsear PDF"""
    pdf_base64: str
    dpi: int = 150
    filename: str = ""
    include_metadata: bool = True
    
    def validate(self) -> tuple[bool, str]:
        """Valida la petición"""
        if not self.pdf_base64:
            return False, "PDF base64 es requerido"
        
        if self.dpi < 72 or self.dpi > 600:
            return False, "DPI debe estar entre 72 y 600"
        
        return True, ""
