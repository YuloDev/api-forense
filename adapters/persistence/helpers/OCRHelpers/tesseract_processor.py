"""
Helper para procesamiento con Tesseract
"""
import statistics
from typing import Tuple, List
from PIL import Image
import pytesseract
from pytesseract import Output
from domain.entities.forensic_ocr_details import (
    Bloque, Linea, Palabra, BBox, ZonaBajaConfianza
)
from .image_processor import ImageProcessor

class TesseractProcessor:
    """Helper para procesamiento con Tesseract"""
    
    def __init__(self, language: str = "spa+eng"):
        self.language = language

    def process_image_with_tesseract(self, image: Image.Image) -> Tuple[str, List[Bloque], List[ZonaBajaConfianza], float, float]:
        """Procesa imagen con Tesseract y extrae información estructurada"""
        # Obtener datos de Tesseract en formato TSV
        data = pytesseract.image_to_data(image, lang=self.language, output_type=Output.DICT)
        
        # Procesar datos para crear estructura jerárquica
        bloques = []
        zonas_baja_confianza = []
        confidences = []
        
        # Agrupar por bloque, línea y palabra
        current_block = None
        current_line = None
        current_words = []
        
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 0:  # Solo texto con confianza > 0
                conf = int(data['conf'][i])
                confidences.append(conf)
                
                text = data['text'][i].strip()
                if text:
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    bbox = BBox(x, y, w, h)
                    
                    # Estimar información de fuente basada en características del texto
                    font_info = self._estimate_font_info(text, w, h, conf)
                    
                    palabra = Palabra(
                        bbox=bbox, 
                        confidence=conf/100.0, 
                        texto=text,
                        font_family=font_info["font_family"],
                        font_size=font_info["font_size"],
                        font_style=font_info["font_style"],
                        font_weight=font_info["font_weight"]
                    )
                    current_words.append(palabra)
                    
                    # Detectar fin de línea (simplificado)
                    if i < len(data['text']) - 1 and data['top'][i+1] > y + h * 0.5:
                        if current_words:
                            # Crear línea
                            line_text = ' '.join([w.texto for w in current_words])
                            line_bbox = ImageProcessor.merge_bboxes([w.bbox for w in current_words])
                            current_line = Linea(
                                bbox=line_bbox,
                                confidence=float(statistics.mean([w.confidence for w in current_words])),
                                texto=line_text,
                                palabras=current_words.copy()
                            )
                            
                            if current_block is None:
                                current_block = Bloque(
                                    bbox=line_bbox,
                                    confidence=current_line.confidence,
                                    lang=self.language.split('+')[0],
                                    lineas=[]
                                )
                            
                            current_block.lineas.append(current_line)
                            current_words = []
                            current_line = None
        
        # Agregar última línea si existe
        if current_words:
            line_text = ' '.join([w.texto for w in current_words])
            line_bbox = ImageProcessor.merge_bboxes([w.bbox for w in current_words])
            current_line = Linea(
                bbox=line_bbox,
                confidence=float(statistics.mean([w.confidence for w in current_words])),
                texto=line_text,
                palabras=current_words.copy()
            )
            
            if current_block is None:
                current_block = Bloque(
                    bbox=line_bbox,
                    confidence=current_line.confidence,
                    lang=self.language.split('+')[0],
                    lineas=[]
                )
            
            current_block.lineas.append(current_line)
        
        if current_block:
            bloques.append(current_block)
        
        # Detectar zonas de baja confianza
        for bloque in bloques:
            for linea in bloque.lineas:
                if linea.confidence < 0.6:
                    zonas_baja_confianza.append(ZonaBajaConfianza(
                        bbox=linea.bbox,
                        confidence_avg=linea.confidence
                    ))
        
        # Calcular métricas
        confidence_avg = float(statistics.mean(confidences)) / 100.0 if confidences else 0.0
        confidence_std = float(statistics.stdev(confidences)) / 100.0 if len(confidences) > 1 else 0.0
        
        # Texto completo
        texto_full = ' '.join([bloque.lineas[i].texto for bloque in bloques for i in range(len(bloque.lineas))])
        
        return texto_full, bloques, zonas_baja_confianza, confidence_avg, confidence_std
    
    def _estimate_font_info(self, text: str, width: int, height: int, confidence: int) -> dict:
        """Estima información de fuente basada en características del texto"""
        import re
        
        # Estimar tamaño de fuente basado en altura
        font_size = max(height * 0.75, 8.0)  # Aproximación básica
        
        # Detectar estilo basado en patrones de texto
        font_style = "normal"
        font_weight = "normal"
        
        # Detectar texto en mayúsculas (posiblemente bold)
        if text.isupper() and len(text) > 2:
            font_weight = "bold"
        
        # Detectar texto con caracteres especiales (posiblemente italic)
        if any(char in text for char in ['/', '\\', '_', '-']) and len(text) > 3:
            font_style = "italic"
        
        # Detectar números (posiblemente monospace)
        if re.match(r'^[\d\s\.,]+$', text):
            font_family = "Courier New"
        # Detectar texto con caracteres especiales de facturación
        elif any(char in text for char in ['$', '€', '£', '¥', '₽', '₹']):
            font_family = "Arial"
        # Detectar texto con números y letras mixtas
        elif re.search(r'\d', text) and re.search(r'[a-zA-Z]', text):
            font_family = "Calibri"
        # Detectar texto en mayúsculas (posiblemente Times)
        elif text.isupper():
            font_family = "Times New Roman"
        # Detectar texto con caracteres especiales
        elif any(char in text for char in ['@', '#', '%', '&', '*']):
            font_family = "Arial"
        # Por defecto, usar fuente estándar
        else:
            font_family = "Arial"
        
        # Ajustar según confianza (menor confianza = fuente más genérica)
        if confidence < 50:
            font_family = "Unknown"
            font_style = "normal"
            font_weight = "normal"
        
        return {
            "font_family": font_family,
            "font_size": font_size,
            "font_style": font_style,
            "font_weight": font_weight
        }
