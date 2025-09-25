import base64
import io
import time
from datetime import datetime
from typing import List
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from domain.entities.ocr_text import OCRText
from domain.ports.ocr_service import OCRServicePort


class OCRServiceAdapter(OCRServicePort):
    """Adaptador que implementa el servicio de OCR usando Tesseract"""
    
    def __init__(self, language: str = "spa+eng", min_confidence: int = 50):
        self.language = language
        self.min_confidence = min_confidence
    
    def extract_text_from_image(self, image_base64: str) -> OCRText:
        """Extrae texto de una imagen codificada en base64"""
        start_time = time.time()
        
        try:
            # Decodificar imagen base64
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            
            # Extraer texto con Tesseract optimizado para imágenes
            # Configuración específica para imágenes
            config = '--oem 3 --psm 3'  # OCR Engine Mode 3, Page Segmentation Mode 3
            text_raw = pytesseract.image_to_string(image, lang=self.language, config=config)
            
            # Normalizar el texto (limpiar espacios, saltos de línea, etc.)
            text_normalized = self._normalize_text(text_raw)
            
            # Obtener datos de confianza
            data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            return OCRText(
                text_raw=text_raw,
                text_normalized=text_normalized,
                confidence=avg_confidence,
                language=self.language,
                processing_time=processing_time,
                created_at=datetime.now(),
                source_type="image"
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return OCRText(
                text_raw="",
                text_normalized="",
                confidence=0.0,
                language=self.language,
                processing_time=processing_time,
                created_at=datetime.now(),
                source_type="image"
            )
    
    def extract_text_from_pdf(self, pdf_base64: str) -> List[OCRText]:
        """Extrae texto de un PDF codificado en base64"""
        start_time = time.time()
        ocr_texts = []
        
        try:
            # Decodificar PDF base64
            pdf_data = base64.b64decode(pdf_base64)
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            
            for page_num in range(len(pdf_document)):
                page_start_time = time.time()
                
                # Convertir página a imagen con alta resolución para PDFs escaneados
                page = pdf_document[page_num]
                # Matriz de alta resolución para mejorar OCR en PDFs escaneados
                mat = fitz.Matrix(3.0, 3.0)  # Aumentar resolución para mejor OCR
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("png")
                
                # Crear imagen PIL
                image = Image.open(io.BytesIO(img_data)).convert("RGB")
                
                # Extraer texto con Tesseract optimizado para PDFs escaneados
                # Configuración específica para documentos escaneados
                config = '--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
                text_raw = pytesseract.image_to_string(image, lang=self.language, config=config)
                
                # Normalizar el texto (limpiar espacios, saltos de línea, etc.)
                text_normalized = self._normalize_text(text_raw)
                
                # Obtener datos de confianza
                data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                page_processing_time = time.time() - page_start_time
                
                ocr_text = OCRText(
                    text_raw=text_raw,
                    text_normalized=text_normalized,
                    confidence=avg_confidence,
                    language=self.language,
                    processing_time=page_processing_time,
                    created_at=datetime.now(),
                    source_type="pdf",
                    page_number=page_num + 1
                )
                
                ocr_texts.append(ocr_text)
            
            pdf_document.close()
            
        except Exception as e:
            # En caso de error, retornar al menos un OCRText vacío
            processing_time = time.time() - start_time
            ocr_texts.append(OCRText(
                text_raw="",
                text_normalized="",
                confidence=0.0,
                language=self.language,
                processing_time=processing_time,
                created_at=datetime.now(),
                source_type="pdf"
            ))
        
        return ocr_texts
    
    def validate_text_quality(self, ocr_text: OCRText) -> bool:
        """Valida la calidad del texto extraído"""
        return (
            ocr_text.is_valid() and
            ocr_text.confidence >= self.min_confidence and
            len(ocr_text.get_clean_text()) > 0
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza el texto extraído por OCR"""
        if not text:
            return ""
        
        # Limpiar espacios múltiples y saltos de línea
        import re
        
        # Reemplazar múltiples espacios con uno solo
        text = re.sub(r'\s+', ' ', text)
        
        # Reemplazar múltiples saltos de línea con uno solo
        text = re.sub(r'\n+', '\n', text)
        
        # Limpiar espacios al inicio y final
        text = text.strip()
        
        # Remover caracteres de control no deseados
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text
