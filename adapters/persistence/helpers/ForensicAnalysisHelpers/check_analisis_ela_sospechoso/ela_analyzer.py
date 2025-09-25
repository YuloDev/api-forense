"""
Helper para análisis ELA sospechoso.

Analiza áreas de la imagen que han sido editadas o re-comprimidas mediante Error Level Analysis.
Utiliza la misma lógica que el helper existente en analisis_forense_avanzado.py
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import cv2
import io


class ElaAnalyzer:
    """Analizador de Error Level Analysis (ELA) usando la lógica existente del proyecto"""
    
    def __init__(self):
        # Parámetros para análisis ELA (usando los mismos valores del helper existente)
        self.ela_quality = 95  # Calidad de recompresión para ELA
        self.porcentaje_threshold_1 = 8.0  # Umbral bajo para porcentaje sospechoso
        self.porcentaje_threshold_2 = 15.0  # Umbral medio para porcentaje sospechoso
        self.porcentaje_threshold_3 = 25.0  # Umbral alto para porcentaje sospechoso
        self.edge_density_threshold_1 = 0.12  # Umbral bajo para densidad de bordes
        self.edge_density_threshold_2 = 0.13  # Umbral medio para densidad de bordes
        self.edge_density_threshold_3 = 0.18  # Umbral alto para densidad de bordes
        self.edge_density_threshold_4 = 0.25  # Umbral muy alto para densidad de bordes
    
    def analyze_image_ela(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza áreas ELA sospechosas en una imagen usando la misma lógica del helper existente.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de análisis ELA y sospechas
        """
        try:
            # Cargar imagen original
            img_original = Image.open(io.BytesIO(image_bytes))
            
            # Recompresión con calidad específica
            buffer_recomp = io.BytesIO()
            img_original.save(buffer_recomp, format='JPEG', quality=self.ela_quality, optimize=False)
            buffer_recomp.seek(0)
            img_recomp = Image.open(buffer_recomp)
            
            # Convertir a arrays numpy
            orig_array = np.array(img_original.convert('RGB'))
            recomp_array = np.array(img_recomp.convert('RGB'))
            
            # Calcular diferencia (ELA)
            ela_array = np.abs(orig_array.astype(np.float32) - recomp_array.astype(np.float32))
            ela_max = np.max(ela_array)
            
            # Normalizar ELA
            if ela_max > 0:
                ela_normalized = (ela_array / ela_max * 255).astype(np.uint8)
            else:
                ela_normalized = ela_array.astype(np.uint8)
            
            # Análisis estadístico
            ela_mean = np.mean(ela_array)
            ela_std = np.std(ela_array)
            ela_max_val = np.max(ela_array)
            
            # Detectar áreas sospechosas (valores altos en ELA) - Umbrales más conservadores
            threshold = ela_mean + 3 * ela_std  # Aumentado de 2 a 3 desviaciones estándar
            areas_sospechosas = np.sum(ela_array > threshold)
            porcentaje_sospechoso = (areas_sospechosas / ela_array.size) * 100
            
            # Detectar bordes en ELA (posibles ediciones) - Umbrales más estrictos
            gray_ela = cv2.cvtColor(ela_normalized, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray_ela, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Umbrales balanceados: evita falsos positivos pero detecta ediciones reales
            # Considera sospechoso si hay evidencia clara de edición
            tiene_ediciones = (porcentaje_sospechoso > self.porcentaje_threshold_1 and edge_density > self.edge_density_threshold_1) or \
                             (porcentaje_sospechoso > self.porcentaje_threshold_2) or \
                             (edge_density > self.edge_density_threshold_2)  # Reducido de 0.18 a 0.13 para detectar ediciones de Paint
            
            # Niveles de sospecha balanceados
            if porcentaje_sospechoso > self.porcentaje_threshold_3 or edge_density > self.edge_density_threshold_4:
                nivel_sospecha = "ALTO"
            elif porcentaje_sospechoso > self.porcentaje_threshold_2 or edge_density > self.edge_density_threshold_3:
                nivel_sospecha = "MEDIO"
            elif porcentaje_sospechoso > self.porcentaje_threshold_1 or edge_density > self.edge_density_threshold_2:  # Ajustado para detectar ediciones de Paint
                nivel_sospecha = "BAJO"
            else:
                nivel_sospecha = "NORMAL"
            
            # Convertir nivel de sospecha a formato esperado por la entidad
            nivel_sospecha_lower = nivel_sospecha.lower()
            
            # Generar indicadores sospechosos
            indicadores_sospechosos = self._generate_suspicious_indicators(
                tiene_ediciones, nivel_sospecha_lower, porcentaje_sospechoso, edge_density
            )
            
            # Crear áreas detectadas basadas en el análisis ELA
            areas_detectadas = self._create_areas_detected(ela_array, threshold)
            
            return {
                "areas_ela_detectadas": tiene_ediciones,
                "nivel_sospecha": nivel_sospecha_lower,
                "areas_sospechosas": int(areas_sospechosas),
                "nivel_compresion_inconsistente": 1 if tiene_ediciones else 0,
                "areas_recomprimidas": 1 if tiene_ediciones else 0,
                "areas_detectadas": areas_detectadas,
                "niveles_ela": [{
                    "tipo": "estadisticas_generales",
                    "mean": float(ela_mean),
                    "std": float(ela_std),
                    "max": float(ela_max_val),
                    "porcentaje_sospechoso": float(porcentaje_sospechoso),
                    "edge_density": float(edge_density)
                }],
                "patrones_compresion": [{
                    "tipo": "compresion_ela",
                    "threshold": float(threshold),
                    "areas_sospechosas": int(areas_sospechosas),
                    "porcentaje_sospechoso": float(porcentaje_sospechoso),
                    "edge_density": float(edge_density),
                    "tiene_ediciones": tiene_ediciones
                }],
                "indicadores_sospechosos": indicadores_sospechosos,
                "ela_mean": float(ela_mean),
                "ela_std": float(ela_std),
                "ela_max": float(ela_max_val),
                "porcentaje_sospechoso": float(porcentaje_sospechoso),
                "edge_density": float(edge_density),
                "tiene_ediciones": tiene_ediciones
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando ELA de imagen: {str(e)}",
                "areas_ela_detectadas": False,
                "nivel_sospecha": "bajo",
                "areas_sospechosas": 0,
                "nivel_compresion_inconsistente": 0,
                "areas_recomprimidas": 0
            }
    
    def _create_areas_detected(self, ela_array: np.ndarray, threshold: float) -> List[Dict[str, Any]]:
        """Crea áreas detectadas basadas en el análisis ELA"""
        try:
            areas = []
            
            # Crear máscara de áreas sospechosas
            suspicious_mask = ela_array > threshold
            
            # Encontrar regiones conectadas
            contours, _ = cv2.findContours(suspicious_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 50:  # Área mínima
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Calcular métricas de la región
                    region_ela = ela_array[y:y+h, x:x+w]
                    mean_ela = np.mean(region_ela)
                    max_ela = np.max(region_ela)
                    std_ela = np.std(region_ela)
                    
                    areas.append({
                        "tipo": "ela_sospechosa",
                        "area": int(area),
                        "bbox": [y, x, y+h, x+w],
                        "mean_ela": float(mean_ela),
                        "max_ela": float(max_ela),
                        "std_ela": float(std_ela),
                        "sospechosa": True,
                        "recomprimida": mean_ela > threshold * 2
                    })
            
            return areas
            
        except Exception:
            return []
    
    def _generate_suspicious_indicators(self, tiene_ediciones: bool, nivel_sospecha: str, 
                                      porcentaje_sospechoso: float, edge_density: float) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if tiene_ediciones:
            indicators.append("Áreas ELA sospechosas detectadas en la imagen")
        
        if nivel_sospecha in ["alto", "muy_alto"]:
            indicators.append(f"Nivel alto de sospecha ELA: {nivel_sospecha}")
        elif nivel_sospecha == "medio":
            indicators.append(f"Nivel medio de sospecha ELA: {nivel_sospecha}")
        elif nivel_sospecha == "bajo":
            indicators.append(f"Nivel bajo de sospecha ELA: {nivel_sospecha}")
        
        if porcentaje_sospechoso > self.porcentaje_threshold_3:
            indicators.append(f"Porcentaje muy alto de área sospechosa: {porcentaje_sospechoso:.1f}%")
        elif porcentaje_sospechoso > self.porcentaje_threshold_2:
            indicators.append(f"Porcentaje alto de área sospechosa: {porcentaje_sospechoso:.1f}%")
        elif porcentaje_sospechoso > self.porcentaje_threshold_1:
            indicators.append(f"Porcentaje moderado de área sospechosa: {porcentaje_sospechoso:.1f}%")
        
        if edge_density > self.edge_density_threshold_4:
            indicators.append(f"Densidad muy alta de bordes: {edge_density:.3f}")
        elif edge_density > self.edge_density_threshold_3:
            indicators.append(f"Densidad alta de bordes: {edge_density:.3f}")
        elif edge_density > self.edge_density_threshold_2:
            indicators.append(f"Densidad moderada de bordes: {edge_density:.3f}")
        
        if tiene_ediciones and porcentaje_sospechoso > self.porcentaje_threshold_2:
            indicators.append("Posible manipulación extensa detectada")
        
        if tiene_ediciones and edge_density > self.edge_density_threshold_3:
            indicators.append("Posible edición con herramientas de pintura detectada")
        
        return indicators
