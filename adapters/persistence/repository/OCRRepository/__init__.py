"""
Repositorios relacionados con OCR
"""
from .forensic_ocr_service_impl import ForensicOCRServiceAdapter
from .ocr_service_impl import OCRServiceAdapter

__all__ = [
    'ForensicOCRServiceAdapter',
    'OCRServiceAdapter'
]
