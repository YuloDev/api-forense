"""
Helper para análisis de uniformidad DPI.

Analiza la uniformidad en la resolución (DPI) de las imágenes en documentos.
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
from PIL.ExifTags import TAGS
import fitz  # PyMuPDF
import io


class DpiAnalyzer:
    """Analizador de uniformidad DPI"""
    
    def __init__(self):
        # DPI estándar comunes en documentos legítimos
        self.standard_dpi = [72, 96, 150, 200, 300, 600]
        
        # DPI sospechosos o inusuales
        self.suspicious_dpi = [1, 2, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 120, 180, 240, 360, 480, 720, 1200, 2400]
        
        # Umbrales para detección de variaciones
        self.variation_thresholds = {
            "low": 0.1,      # 10% de variación
            "medium": 0.2,   # 20% de variación
            "high": 0.3      # 30% de variación
        }
    
    def analyze_pdf_dpi(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza la uniformidad DPI de un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con información de DPI y análisis
        """
        try:
            # Abrir PDF con PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            dpi_values = []
            image_count = 0
            
            # Analizar cada página
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Obtener imágenes de la página
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Obtener datos de la imagen
                        xref = img[0]
                        pix = fitz.Pixmap(pdf_document, xref)
                        
                        if pix.n - pix.alpha < 4:  # GRAY o RGB
                            # Convertir a PIL Image para extraer DPI
                            img_data = pix.tobytes("png")
                            pil_image = Image.open(io.BytesIO(img_data))
                            
                            # Extraer DPI
                            dpi = self._extract_dpi_from_image(pil_image)
                            if dpi and dpi > 0:
                                dpi_values.append(dpi)
                                image_count += 1
                        
                        pix = None  # Liberar memoria
                        
                    except Exception as e:
                        # Continuar con la siguiente imagen si hay error
                        continue
            
            pdf_document.close()
            
            if not dpi_values:
                return {
                    "error": "No se encontraron imágenes con información DPI en el PDF",
                    "dpi_values": [],
                    "image_count": 0
                }
            
            # Realizar análisis de uniformidad
            analysis = self._analyze_dpi_uniformity(dpi_values, "pdf")
            analysis["image_count"] = image_count
            
            return analysis
            
        except Exception as e:
            return {
                "error": f"Error analizando DPI del PDF: {str(e)}",
                "dpi_values": [],
                "image_count": 0
            }
    
    def analyze_image_dpi(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza la uniformidad DPI de una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de DPI y análisis
        """
        try:
            # Abrir imagen con PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            # Extraer DPI
            dpi = self._extract_dpi_from_image(image)
            
            if not dpi or dpi <= 0:
                return {
                    "error": "No se encontró información DPI en la imagen",
                    "dpi_values": [],
                    "image_count": 0
                }
            
            # Realizar análisis de uniformidad
            analysis = self._analyze_dpi_uniformity([dpi], "image")
            analysis["image_count"] = 1
            
            return analysis
            
        except Exception as e:
            return {
                "error": f"Error analizando DPI de la imagen: {str(e)}",
                "dpi_values": [],
                "image_count": 0
            }
    
    def _extract_dpi_from_image(self, image: Image.Image) -> Optional[float]:
        """Extrae DPI de una imagen PIL"""
        try:
            # Intentar obtener DPI de metadatos
            dpi_x = image.info.get('dpi', (0, 0))[0]
            dpi_y = image.info.get('dpi', (0, 0))[1]
            
            if dpi_x > 0:
                return float(dpi_x)
            
            # Intentar obtener de EXIF
            if hasattr(image, '_getexif') and image._getexif() is not None:
                exif = image._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == 'XResolution' and value:
                        return float(value)
                    elif tag == 'YResolution' and value:
                        return float(value)
            
            # Estimar DPI basado en tamaño y resolución
            width, height = image.size
            if width > 0 and height > 0:
                # Estimación básica basada en tamaño típico
                if width > 2000 or height > 2000:
                    return 300.0  # Imagen de alta resolución
                elif width > 1000 or height > 1000:
                    return 150.0  # Imagen de resolución media
                else:
                    return 72.0   # Imagen de baja resolución
            
            return None
            
        except Exception:
            return None
    
    def _analyze_dpi_uniformity(self, dpi_values: List[float], source_type: str) -> Dict[str, Any]:
        """Analiza la uniformidad de los valores DPI"""
        if not dpi_values:
            return {
                "dpi_values": [],
                "dpi_promedio": 0.0,
                "dpi_estandar": 0,
                "variacion_dpi": 0.0,
                "uniformidad_score": 0.0,
                "dpi_detectados": [],
                "dpi_mas_comun": 0.0,
                "desviacion_estandar": 0.0,
                "rango_dpi": [],
                "dpi_sospechosos": [],
                "indicadores_sospechosos": []
            }
        
        # Calcular estadísticas básicas
        dpi_promedio = statistics.mean(dpi_values)
        dpi_estandar = self._find_standard_dpi(dpi_promedio)
        desviacion_estandar = statistics.stdev(dpi_values) if len(dpi_values) > 1 else 0.0
        
        # Calcular variación relativa
        variacion_dpi = desviacion_estandar / dpi_promedio if dpi_promedio > 0 else 0.0
        
        # Calcular score de uniformidad
        uniformidad_score = self._calculate_uniformity_score(dpi_values, variacion_dpi)
        
        # Detectar DPI sospechosos
        dpi_sospechosos = self._detect_suspicious_dpi(dpi_values)
        
        # Generar indicadores sospechosos
        indicadores_sospechosos = self._generate_suspicious_indicators(
            dpi_values, variacion_dpi, dpi_sospechosos, uniformidad_score
        )
        
        return {
            "dpi_values": dpi_values,
            "dpi_promedio": dpi_promedio,
            "dpi_estandar": dpi_estandar,
            "variacion_dpi": variacion_dpi,
            "uniformidad_score": uniformidad_score,
            "dpi_detectados": dpi_values.copy(),
            "dpi_mas_comun": max(set(dpi_values), key=dpi_values.count) if dpi_values else 0.0,
            "desviacion_estandar": desviacion_estandar,
            "rango_dpi": [min(dpi_values), max(dpi_values)] if dpi_values else [],
            "dpi_sospechosos": dpi_sospechosos,
            "indicadores_sospechosos": indicadores_sospechosos
        }
    
    def _find_standard_dpi(self, dpi_promedio: float) -> int:
        """Encuentra el DPI estándar más cercano al promedio"""
        if not dpi_promedio:
            return 0
        
        # Encontrar el DPI estándar más cercano
        closest_dpi = min(self.standard_dpi, key=lambda x: abs(x - dpi_promedio))
        return closest_dpi
    
    def _calculate_uniformity_score(self, dpi_values: List[float], variacion_dpi: float) -> float:
        """Calcula el score de uniformidad (0-1, donde 1 es máxima uniformidad)"""
        if not dpi_values:
            return 1.0
        
        # Factor 1: Variación relativa (menor variación = mayor uniformidad)
        variation_factor = max(0.0, 1.0 - variacion_dpi)
        
        # Factor 2: Consistencia con DPI estándar
        dpi_promedio = statistics.mean(dpi_values)
        closest_standard = min(self.standard_dpi, key=lambda x: abs(x - dpi_promedio))
        standard_deviation = abs(dpi_promedio - closest_standard) / closest_standard if closest_standard > 0 else 1.0
        standard_factor = max(0.0, 1.0 - standard_deviation)
        
        # Factor 3: Rango de DPI (menor rango = mayor uniformidad)
        dpi_range = max(dpi_values) - min(dpi_values)
        range_factor = max(0.0, 1.0 - (dpi_range / dpi_promedio)) if dpi_promedio > 0 else 1.0
        
        # Ponderar factores
        uniformity_score = (
            variation_factor * 0.5 +
            standard_factor * 0.3 +
            range_factor * 0.2
        )
        
        return min(max(uniformity_score, 0.0), 1.0)
    
    def _detect_suspicious_dpi(self, dpi_values: List[float]) -> List[float]:
        """Detecta DPI sospechosos o inusuales"""
        suspicious = []
        
        for dpi in dpi_values:
            # Verificar si está en la lista de DPI sospechosos
            if dpi in self.suspicious_dpi:
                suspicious.append(dpi)
            
            # Verificar si está muy lejos de DPI estándar
            closest_standard = min(self.standard_dpi, key=lambda x: abs(x - dpi))
            deviation = abs(dpi - closest_standard) / closest_standard if closest_standard > 0 else 1.0
            
            if deviation > 0.5:  # Más del 50% de desviación
                suspicious.append(dpi)
        
        return list(set(suspicious))  # Eliminar duplicados
    
    def _generate_suspicious_indicators(self, dpi_values: List[float], variacion_dpi: float, 
                                      dpi_sospechosos: List[float], uniformidad_score: float) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis DPI"""
        indicators = []
        
        if variacion_dpi > self.variation_thresholds["high"]:
            indicators.append(f"Variación DPI muy alta: {variacion_dpi:.1%}")
        elif variacion_dpi > self.variation_thresholds["medium"]:
            indicators.append(f"Variación DPI significativa: {variacion_dpi:.1%}")
        elif variacion_dpi > self.variation_thresholds["low"]:
            indicators.append(f"Variación DPI moderada: {variacion_dpi:.1%}")
        
        if dpi_sospechosos:
            indicators.append(f"DPI sospechosos detectados: {dpi_sospechosos}")
        
        if uniformidad_score < 0.3:
            indicators.append("Uniformidad DPI muy baja - posible inserción de imágenes")
        elif uniformidad_score < 0.6:
            indicators.append("Uniformidad DPI baja - posible manipulación")
        
        if len(dpi_values) > 1:
            dpi_range = max(dpi_values) - min(dpi_values)
            if dpi_range > 100:
                indicators.append(f"Rango DPI muy amplio: {dpi_range:.1f} puntos")
        
        return indicators
