"""
Casos de uso relacionados con OCR
"""
from .extract_forensic_details import ExtractForensicDetailsUseCase
from .validate_ocr_text import ValidateOCRTextUseCase

__all__ = [
    'ExtractForensicDetailsUseCase',
    'ValidateOCRTextUseCase'
]
