"""
Helper para análisis de extracción de texto OCR.

Analiza la incapacidad de extraer texto legible mediante OCR que puede indicar manipulación.
"""

import re
from typing import Dict, Any, List, Optional
from PIL import Image
import io
import pytesseract
from adapters.persistence.helpers.OCRHelpers.tesseract_processor import TesseractProcessor


class OcrExtractionAnalyzer:
    """Analizador de extracción de texto OCR"""
    
    def __init__(self):
        self.tesseract_processor = TesseractProcessor()
        
        # Patrones de texto sospechoso o ilegible
        self.suspicious_patterns = [
            r'[^\w\s]',  # Caracteres no alfanuméricos
            r'\s{3,}',   # Múltiples espacios
            r'[a-zA-Z]{20,}',  # Palabras muy largas
            r'\d{10,}',  # Números muy largos
            r'[^a-zA-Z0-9\s]{3,}',  # Múltiples caracteres especiales
        ]
        
        # Caracteres considerados legibles
        self.legible_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        
        # Palabras comunes en español para validación
        self.common_words = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez'
        }
    
    def analyze_image_ocr_extraction(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza la extracción de texto OCR en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de extracción OCR y análisis
        """
        try:
            # Procesar imagen con Tesseract
            ocr_result = self.tesseract_processor.process_image_with_tesseract(image_bytes)
            
            if not ocr_result or not ocr_result.success:
                return {
                    "error": "Error en procesamiento OCR de la imagen",
                    "texto_extraido": False,
                    "calidad_extraccion": "muy_mala",
                    "confianza_promedio": 0.0,
                    "cantidad_palabras": 0,
                    "cantidad_caracteres": 0
                }
            
            # Extraer información del resultado OCR
            palabras_detectadas = []
            confianza_total = 0.0
            caracteres_legibles = 0
            caracteres_no_legibles = 0
            
            if hasattr(ocr_result, 'palabras') and ocr_result.palabras:
                for palabra in ocr_result.palabras:
                    palabra_info = {
                        "texto": palabra.texto,
                        "confianza": palabra.confidence,
                        "bbox": palabra.bbox,
                        "es_legible": self._is_legible_word(palabra.texto),
                        "es_palabra_comun": palabra.texto.lower() in self.common_words
                    }
                    palabras_detectadas.append(palabra_info)
                    
                    # Calcular confianza total
                    confianza_total += palabra.confidence
                    
                    # Contar caracteres legibles/no legibles
                    for char in palabra.texto:
                        if char in self.legible_chars:
                            caracteres_legibles += 1
                        else:
                            caracteres_no_legibles += 1
            
            # Calcular métricas
            cantidad_palabras = len(palabras_detectadas)
            cantidad_caracteres = caracteres_legibles + caracteres_no_legibles
            confianza_promedio = confianza_total / cantidad_palabras if cantidad_palabras > 0 else 0.0
            
            # Determinar si se extrajo texto
            texto_extraido = cantidad_palabras > 0 and cantidad_caracteres > 0
            
            # Determinar calidad de extracción
            calidad_extraccion = self._determine_extraction_quality(
                confianza_promedio, cantidad_palabras, caracteres_legibles, caracteres_no_legibles
            )
            
            # Generar indicadores sospechosos
            indicadores_sospechosos = self._generate_suspicious_indicators(
                texto_extraido, calidad_extraccion, confianza_promedio, 
                cantidad_palabras, caracteres_legibles, caracteres_no_legibles
            )
            
            return {
                "texto_extraido": texto_extraido,
                "calidad_extraccion": calidad_extraccion,
                "confianza_promedio": confianza_promedio,
                "cantidad_palabras": cantidad_palabras,
                "cantidad_caracteres": cantidad_caracteres,
                "palabras_detectadas": palabras_detectadas,
                "caracteres_legibles": caracteres_legibles,
                "caracteres_no_legibles": caracteres_no_legibles,
                "indicadores_sospechosos": indicadores_sospechosos
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando extracción OCR de imagen: {str(e)}",
                "texto_extraido": False,
                "calidad_extraccion": "muy_mala",
                "confianza_promedio": 0.0,
                "cantidad_palabras": 0,
                "cantidad_caracteres": 0
            }
    
    def _is_legible_word(self, word: str) -> bool:
        """Determina si una palabra es legible"""
        if not word or len(word.strip()) == 0:
            return False
        
        # Verificar si contiene caracteres legibles
        legible_chars = sum(1 for char in word if char in self.legible_chars)
        total_chars = len(word)
        
        # Si más del 70% de los caracteres son legibles, consideramos la palabra legible
        return (legible_chars / total_chars) >= 0.7 if total_chars > 0 else False
    
    def _determine_extraction_quality(self, confianza_promedio: float, cantidad_palabras: int, 
                                    caracteres_legibles: int, caracteres_no_legibles: int) -> str:
        """Determina la calidad de extracción basada en métricas"""
        
        # Si no hay texto extraído
        if cantidad_palabras == 0 or (caracteres_legibles + caracteres_no_legibles) == 0:
            return "muy_mala"
        
        # Calcular ratio de caracteres legibles
        total_caracteres = caracteres_legibles + caracteres_no_legibles
        ratio_legibles = caracteres_legibles / total_caracteres if total_caracteres > 0 else 0.0
        
        # Determinar calidad basada en confianza y ratio de legibilidad
        if confianza_promedio >= 0.8 and ratio_legibles >= 0.9:
            return "excelente"
        elif confianza_promedio >= 0.6 and ratio_legibles >= 0.7:
            return "buena"
        elif confianza_promedio >= 0.4 and ratio_legibles >= 0.5:
            return "regular"
        elif confianza_promedio >= 0.2 and ratio_legibles >= 0.3:
            return "mala"
        else:
            return "muy_mala"
    
    def _generate_suspicious_indicators(self, texto_extraido: bool, calidad_extraccion: str, 
                                      confianza_promedio: float, cantidad_palabras: int, 
                                      caracteres_legibles: int, caracteres_no_legibles: int) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if not texto_extraido:
            indicators.append("No se pudo extraer texto de la imagen")
            indicators.append("Posible manipulación o formato no estándar")
        else:
            if calidad_extraccion == "muy_mala":
                indicators.append("Calidad de extracción muy mala - posible manipulación")
            elif calidad_extraccion == "mala":
                indicators.append("Calidad de extracción mala - posible alteración")
            
            if confianza_promedio < 0.3:
                indicators.append("Confianza de OCR muy baja - posible manipulación")
            elif confianza_promedio < 0.5:
                indicators.append("Confianza de OCR baja - posible alteración")
            
            if cantidad_palabras < 3:
                indicators.append("Muy pocas palabras detectadas - posible manipulación")
            elif cantidad_palabras < 10:
                indicators.append("Pocas palabras detectadas - posible alteración")
            
            if caracteres_no_legibles > caracteres_legibles:
                indicators.append("Más caracteres ilegibles que legibles - posible manipulación")
            elif caracteres_no_legibles > caracteres_legibles * 0.5:
                indicators.append("Alto número de caracteres ilegibles - posible alteración")
            
            if cantidad_palabras > 0:
                total_caracteres = caracteres_legibles + caracteres_no_legibles
                if total_caracteres < 10:
                    indicators.append("Muy pocos caracteres detectados - posible manipulación")
                elif total_caracteres < 50:
                    indicators.append("Pocos caracteres detectados - posible alteración")
        
        return indicators
