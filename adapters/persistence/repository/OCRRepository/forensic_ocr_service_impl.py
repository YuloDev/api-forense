import time
import base64
import io
import hashlib
from typing import Dict, Any
from datetime import datetime
from PIL import Image
import fitz  # PyMuPDF

import config
from domain.ports.forensic_ocr_service import ForensicOCRServicePort
from domain.entities.forensic_ocr_details import (
    ForensicOCRDetails, SourceInfo, OCRInfo, MetricasOCR, 
    Normalizaciones, ForenseInfo, ResumenForense, TiemposMS
)
from adapters.persistence.helpers import (
    ImageProcessor, EntityExtractor, ForensicAnalyzer, TesseractProcessor
)

class ForensicOCRServiceAdapter(ForensicOCRServicePort):
    """Adaptador para el servicio de OCR forense usando Tesseract y OpenCV"""

    def __init__(self, language: str = "spa+eng", min_confidence: int = 30):
        self.language = language
        self.min_confidence = min_confidence
        self.tesseract_processor = TesseractProcessor(language)

    def _get_tesseract_version(self) -> str:
        """Obtiene la versión de Tesseract"""
        try:
            import pytesseract
            return pytesseract.get_tesseract_version()
        except:
            return "unknown"

    def _calculate_file_hash(self, file_bytes: bytes) -> str:
        """Calcula el hash SHA256 del archivo"""
        return hashlib.sha256(file_bytes).hexdigest()

    def extract_forensic_details_from_image(self, image_base64: str, tipo: str) -> ForensicOCRDetails:
        """Extrae detalles forenses de una imagen"""
        start_time = time.time()
        
        try:
            # Decodificar imagen
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            
            # Información de la fuente
            width, height = image.size
            dpi_x, dpi_y = ImageProcessor.estimate_dpi(image)
            rotation = ImageProcessor.detect_skew_angle(image)
            
            source = SourceInfo(
                filename=f"image_{int(time.time())}.png",
                mime="image/png",
                width_px=width,
                height_px=height,
                dpi_estimado=dpi_x,
                rotation_deg=rotation
            )
            
            # Procesar con Tesseract
            preprocess_start = time.time()
            texto_full, bloques, zonas_baja_confianza, conf_avg, conf_std = self.tesseract_processor.process_image_with_tesseract(image)
            ocr_time = time.time() - preprocess_start
            
            # Calcular métricas
            densidad_lineas = len(bloques[0].lineas) * 1000 / width if bloques else 0
            porcentaje_texto = sum(b.bbox.w * b.bbox.h for b in bloques) / (width * height) if bloques else 0
            
            metricas = MetricasOCR(
                skew_deg=rotation,
                densidad_lineas_por_1000px=densidad_lineas,
                porcentaje_area_texto=porcentaje_texto,
                zonas_baja_confianza=zonas_baja_confianza
            )
            
            # Información OCR
            ocr_info = OCRInfo(
                engine="tesseract",
                lang_detected=[self.language.split('+')[0]],
                confidence_avg=conf_avg,
                confidence_std=conf_std,
                texto_full=texto_full,
                bloques=bloques,
                metricas=metricas
            )
            
            # Extraer entidades
            postprocess_start = time.time()
            fechas, monedas, identificadores = EntityExtractor.extract_entities(texto_full)
            campos_clave = EntityExtractor.extract_financial_totals(texto_full)
            
            normalizaciones = Normalizaciones(
                fechas=fechas,
                monedas=monedas,
                identificadores=identificadores,
                campos_clave=campos_clave,
                items_detectados=[]  # Se puede implementar más adelante
            )
            
            # Análisis forense
            alertas, resumen = ForensicAnalyzer.analyze_forensic_heuristics(bloques)
            forense = ForenseInfo(alertas=alertas, resumen=resumen)
            
            postprocess_time = time.time() - postprocess_start
            total_time = time.time() - start_time
            
            tiempos = TiemposMS(
                preprocesado=int((preprocess_start - start_time) * 1000),
                ocr=int(ocr_time * 1000),
                postprocesado=int(postprocess_time * 1000)
            )
            
            return ForensicOCRDetails(
                source=source,
                ocr=ocr_info,
                normalizaciones=normalizaciones,
                forense=forense,
                version="ocr-forense-1.0.0",
                tiempos_ms=tiempos,
                success=True
            )
            
        except Exception as e:
            return ForensicOCRDetails(
                source=SourceInfo("", "", 0, 0, 0.0, 0.0),
                ocr=OCRInfo("", [], 0.0, 0.0, "", [], MetricasOCR(0.0, 0.0, 0.0, [])),
                normalizaciones=Normalizaciones([], [], [], [], []),
                forense=ForenseInfo([], ResumenForense(0.0, 0.0, False, False)),
                version="ocr-forense-1.0.0",
                tiempos_ms=TiemposMS(0, 0, 0),
                success=False,
                error=str(e)
            )

    def extract_forensic_details_from_pdf(self, pdf_base64: str, tipo: str) -> ForensicOCRDetails:
        """Extrae detalles forenses de un PDF"""
        start_time = time.time()
        
        try:
            # Decodificar PDF
            pdf_data = base64.b64decode(pdf_base64)
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            
            # Procesar primera página (simplificado para este ejemplo)
            if len(pdf_document) > 0:
                page = pdf_document[0]
                mat = fitz.Matrix(2.0, 2.0)  # Aumentar resolución
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data)).convert("RGB")
                
                # Usar el mismo procesamiento que para imágenes
                return self.extract_forensic_details_from_image(
                    base64.b64encode(img_data).decode('utf-8'), 
                    tipo
                )
            else:
                raise Exception("PDF vacío")
                
        except Exception as e:
            return ForensicOCRDetails(
                source=SourceInfo("", "", 0, 0, 0.0, 0.0),
                ocr=OCRInfo("", [], 0.0, 0.0, "", [], MetricasOCR(0.0, 0.0, 0.0, [])),
                normalizaciones=Normalizaciones([], [], [], [], []),
                forense=ForenseInfo([], ResumenForense(0.0, 0.0, False, False)),
                version="ocr-forense-1.0.0",
                tiempos_ms=TiemposMS(0, 0, 0),
                success=False,
                error=str(e)
            )