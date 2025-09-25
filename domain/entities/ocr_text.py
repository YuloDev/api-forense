from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class OCRText:
    """Entidad que representa el texto extraído por OCR"""
    
    text_raw: str
    text_normalized: str
    confidence: float
    language: str
    processing_time: float
    created_at: datetime
    source_type: str  # 'image' o 'pdf'
    page_number: Optional[int] = None  # Para PDFs
    
    def is_valid(self) -> bool:
        """Valida si el texto OCR es válido"""
        return (
            self.text_raw is not None 
            and len(self.text_raw.strip()) > 0 
            and self.confidence > 0
        )
    
    def get_clean_text(self) -> str:
        """Retorna el texto normalizado limpio"""
        return self.text_normalized.strip() if self.text_normalized else ""
    
    def get_raw_text(self) -> str:
        """Retorna el texto crudo sin procesar"""
        return self.text_raw.strip() if self.text_raw else ""
    
    def get_confidence_percentage(self) -> float:
        """Retorna la confianza como porcentaje"""
        return round(self.confidence, 2)
