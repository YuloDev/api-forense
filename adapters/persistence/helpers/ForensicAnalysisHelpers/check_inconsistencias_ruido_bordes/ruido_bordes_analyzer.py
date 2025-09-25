"""
Helper para análisis de inconsistencias en ruido y bordes.

Analiza inconsistencias en patrones de ruido y bordes que pueden indicar edición local.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import cv2
import io
from scipy import ndimage
from skimage import filters, measure, segmentation
from skimage.feature import local_binary_pattern
from skimage.morphology import disk, binary_erosion, binary_dilation


class RuidoBordesAnalyzer:
    """Analizador de inconsistencias en ruido y bordes"""
    
    def __init__(self):
        # Parámetros para análisis de ruido
        self.noise_threshold = 0.1
        self.noise_variance_threshold = 0.05
        
        # Parámetros para análisis de bordes
        self.edge_threshold = 0.1
        self.edge_continuity_threshold = 0.8
        
        # Parámetros para detección de inconsistencias
        self.inconsistency_threshold = 0.3
        self.area_min_size = 100  # píxeles mínimos para considerar un área
        
        # Parámetros para análisis de textura
        self.texture_window_size = 8
        self.lbp_radius = 1
        self.lbp_n_points = 8
    
    def analyze_image_ruido_bordes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza inconsistencias en ruido y bordes en una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de inconsistencias y análisis
        """
        try:
            # Cargar imagen
            image = Image.open(io.BytesIO(image_bytes))
            image_array = np.array(image.convert('L'))  # Convertir a escala de grises
            
            # Analizar patrones de ruido
            noise_analysis = self._analyze_noise_patterns(image_array)
            
            # Analizar bordes
            edge_analysis = self._analyze_edges(image_array)
            
            # Detectar inconsistencias
            inconsistency_analysis = self._detect_inconsistencies(image_array, noise_analysis, edge_analysis)
            
            # Analizar textura local
            texture_analysis = self._analyze_local_texture(image_array)
            
            # Combinar resultados
            areas_detectadas = inconsistency_analysis.get("areas", [])
            patrones_ruido = noise_analysis.get("patrones", [])
            bordes_analizados = edge_analysis.get("bordes", [])
            
            # Calcular métricas generales
            areas_sospechosas = len([area for area in areas_detectadas if area.get("sospechosa", False)])
            patrones_ruido_inconsistentes = len([patron for patron in patrones_ruido if patron.get("inconsistente", False)])
            bordes_irregulares = len([borde for borde in bordes_analizados if borde.get("irregular", False)])
            
            # Determinar si hay inconsistencias
            inconsistencias_detectadas = (areas_sospechosas > 0 or 
                                        patrones_ruido_inconsistentes > 0 or 
                                        bordes_irregulares > 0)
            
            # Determinar nivel de inconsistencia
            nivel_inconsistencia = self._determine_inconsistency_level(
                areas_sospechosas, patrones_ruido_inconsistentes, bordes_irregulares
            )
            
            # Generar indicadores sospechosos
            indicadores_sospechosos = self._generate_suspicious_indicators(
                inconsistencias_detectadas, nivel_inconsistencia, areas_sospechosas,
                patrones_ruido_inconsistentes, bordes_irregulares
            )
            
            return {
                "inconsistencias_detectadas": inconsistencias_detectadas,
                "nivel_inconsistencia": nivel_inconsistencia,
                "areas_sospechosas": areas_sospechosas,
                "patrones_ruido_inconsistentes": patrones_ruido_inconsistentes,
                "bordes_irregulares": bordes_irregulares,
                "areas_detectadas": areas_detectadas,
                "patrones_ruido": patrones_ruido,
                "bordes_analizados": bordes_analizados,
                "indicadores_sospechosos": indicadores_sospechosos
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando inconsistencias de ruido y bordes: {str(e)}",
                "inconsistencias_detectadas": False,
                "nivel_inconsistencia": "bajo",
                "areas_sospechosas": 0,
                "patrones_ruido_inconsistentes": 0,
                "bordes_irregulares": 0
            }
    
    def _analyze_noise_patterns(self, image: np.ndarray) -> Dict[str, Any]:
        """Analiza patrones de ruido en la imagen"""
        try:
            patrones = []
            
            # Calcular ruido usando filtro Laplaciano
            laplacian = cv2.Laplacian(image, cv2.CV_64F)
            noise_variance = np.var(laplacian)
            
            # Detectar áreas con ruido alto
            noise_mask = np.abs(laplacian) > self.noise_threshold
            noise_regions = self._find_regions(noise_mask)
            
            for region in noise_regions:
                if region['area'] > self.area_min_size:
                    # Calcular características del ruido
                    region_noise = laplacian[region['bbox'][0]:region['bbox'][2], 
                                           region['bbox'][1]:region['bbox'][3]]
                    
                    # Verificar consistencia del ruido
                    noise_std = np.std(region_noise)
                    noise_mean = np.mean(np.abs(region_noise))
                    
                    inconsistente = (noise_std > self.noise_variance_threshold or 
                                   noise_mean > self.noise_threshold * 2)
                    
                    patrones.append({
                        "tipo": "ruido",
                        "area": region['area'],
                        "bbox": region['bbox'],
                        "variance": float(noise_variance),
                        "std": float(noise_std),
                        "mean": float(noise_mean),
                        "inconsistente": inconsistente,
                        "sospechoso": inconsistente
                    })
            
            return {
                "patrones": patrones,
                "variance_total": float(noise_variance),
                "regiones_detectadas": len(noise_regions)
            }
            
        except Exception as e:
            return {"patrones": [], "variance_total": 0.0, "regiones_detectadas": 0}
    
    def _analyze_edges(self, image: np.ndarray) -> Dict[str, Any]:
        """Analiza bordes en la imagen"""
        try:
            bordes = []
            
            # Detectar bordes usando Canny
            edges = cv2.Canny(image, 50, 150)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > self.area_min_size:
                    # Calcular características del borde
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                    else:
                        circularity = 0
                    
                    # Calcular suavidad del borde
                    smoothness = self._calculate_edge_smoothness(contour)
                    
                    # Verificar irregularidad
                    irregular = (circularity < 0.3 or smoothness < self.edge_continuity_threshold)
                    
                    # Obtener bounding box
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    bordes.append({
                        "tipo": "borde",
                        "area": int(area),
                        "perimeter": float(perimeter),
                        "circularity": float(circularity),
                        "smoothness": float(smoothness),
                        "bbox": [x, y, x + w, y + h],
                        "irregular": irregular,
                        "sospechoso": irregular
                    })
            
            return {
                "bordes": bordes,
                "total_contours": len(contours),
                "edges_detected": np.sum(edges > 0)
            }
            
        except Exception as e:
            return {"bordes": [], "total_contours": 0, "edges_detected": 0}
    
    def _detect_inconsistencies(self, image: np.ndarray, noise_analysis: Dict, 
                               edge_analysis: Dict) -> Dict[str, Any]:
        """Detecta inconsistencias en la imagen"""
        try:
            areas = []
            
            # Combinar máscaras de ruido y bordes
            noise_mask = np.zeros_like(image, dtype=bool)
            edge_mask = np.zeros_like(image, dtype=bool)
            
            # Crear máscara de ruido
            for patron in noise_analysis.get("patrones", []):
                if patron.get("inconsistente", False):
                    bbox = patron["bbox"]
                    noise_mask[bbox[0]:bbox[2], bbox[1]:bbox[3]] = True
            
            # Crear máscara de bordes irregulares
            for borde in edge_analysis.get("bordes", []):
                if borde.get("irregular", False):
                    bbox = borde["bbox"]
                    edge_mask[bbox[0]:bbox[2], bbox[1]:bbox[3]] = True
            
            # Combinar máscaras
            combined_mask = noise_mask | edge_mask
            
            # Encontrar regiones de inconsistencia
            inconsistency_regions = self._find_regions(combined_mask)
            
            for region in inconsistency_regions:
                if region['area'] > self.area_min_size:
                    # Calcular características de la región
                    bbox = region['bbox']
                    region_image = image[bbox[0]:bbox[2], bbox[1]:bbox[3]]
                    
                    # Calcular métricas de inconsistencia
                    variance = np.var(region_image)
                    mean_intensity = np.mean(region_image)
                    
                    # Determinar si es sospechosa
                    sospechosa = (variance > self.inconsistency_threshold or 
                                region['area'] > self.area_min_size * 2)
                    
                    areas.append({
                        "tipo": "inconsistencia",
                        "area": region['area'],
                        "bbox": bbox,
                        "variance": float(variance),
                        "mean_intensity": float(mean_intensity),
                        "sospechosa": sospechosa
                    })
            
            return {"areas": areas}
            
        except Exception as e:
            return {"areas": []}
    
    def _analyze_local_texture(self, image: np.ndarray) -> Dict[str, Any]:
        """Analiza textura local de la imagen"""
        try:
            # Calcular Local Binary Pattern
            lbp = local_binary_pattern(image, self.lbp_n_points, self.lbp_radius, method='uniform')
            
            # Calcular histograma de LBP
            hist, _ = np.histogram(lbp.ravel(), bins=self.lbp_n_points + 2, 
                                 range=(0, self.lbp_n_points + 2))
            hist = hist.astype(float)
            hist /= (hist.sum() + 1e-7)
            
            # Calcular entropía de textura
            entropy = -np.sum(hist * np.log2(hist + 1e-7))
            
            # Detectar áreas con textura inconsistente
            texture_inconsistency = self._detect_texture_inconsistency(lbp)
            
            return {
                "entropy": float(entropy),
                "texture_inconsistency": texture_inconsistency,
                "lbp_histogram": hist.tolist()
            }
            
        except Exception as e:
            return {"entropy": 0.0, "texture_inconsistency": 0.0, "lbp_histogram": []}
    
    def _detect_texture_inconsistency(self, lbp: np.ndarray) -> float:
        """Detecta inconsistencias en la textura local"""
        try:
            # Calcular varianza local de LBP
            kernel = np.ones((self.texture_window_size, self.texture_window_size))
            local_variance = ndimage.generic_filter(lbp, np.var, 
                                                  footprint=kernel, mode='constant')
            
            # Calcular umbral de inconsistencia
            threshold = np.percentile(local_variance, 95)
            inconsistent_pixels = np.sum(local_variance > threshold)
            total_pixels = lbp.size
            
            return float(inconsistent_pixels / total_pixels) if total_pixels > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _find_regions(self, mask: np.ndarray) -> List[Dict[str, Any]]:
        """Encuentra regiones conectadas en una máscara"""
        try:
            # Etiquetar regiones conectadas
            labeled_array, num_features = measure.label(mask, return_num=True)
            
            regions = []
            for i in range(1, num_features + 1):
                region_mask = labeled_array == i
                coords = np.where(region_mask)
                
                if len(coords[0]) > 0:
                    y_min, y_max = np.min(coords[0]), np.max(coords[0])
                    x_min, x_max = np.min(coords[1]), np.max(coords[1])
                    
                    regions.append({
                        "area": int(np.sum(region_mask)),
                        "bbox": [y_min, x_min, y_max, x_max]
                    })
            
            return regions
            
        except Exception:
            return []
    
    def _calculate_edge_smoothness(self, contour: np.ndarray) -> float:
        """Calcula la suavidad de un contorno"""
        try:
            if len(contour) < 3:
                return 0.0
            
            # Calcular derivadas del contorno
            contour = contour.reshape(-1, 2)
            dx = np.diff(contour[:, 0])
            dy = np.diff(contour[:, 1])
            
            # Calcular ángulos
            angles = np.arctan2(dy, dx)
            
            # Calcular diferencias de ángulos
            angle_diffs = np.abs(np.diff(angles))
            angle_diffs = np.minimum(angle_diffs, 2 * np.pi - angle_diffs)
            
            # La suavidad es la inversa de la varianza de los ángulos
            smoothness = 1.0 / (1.0 + np.var(angle_diffs))
            
            return float(smoothness)
            
        except Exception:
            return 0.0
    
    def _determine_inconsistency_level(self, areas_sospechosas: int, 
                                     patrones_ruido_inconsistentes: int, 
                                     bordes_irregulares: int) -> str:
        """Determina el nivel de inconsistencia basado en las métricas"""
        
        total_inconsistencias = areas_sospechosas + patrones_ruido_inconsistentes + bordes_irregulares
        
        if total_inconsistencias == 0:
            return "bajo"
        elif total_inconsistencias <= 2:
            return "medio"
        elif total_inconsistencias <= 5:
            return "alto"
        else:
            return "muy_alto"
    
    def _generate_suspicious_indicators(self, inconsistencias_detectadas: bool, 
                                      nivel_inconsistencia: str, areas_sospechosas: int,
                                      patrones_ruido_inconsistentes: int, 
                                      bordes_irregulares: int) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if inconsistencias_detectadas:
            indicators.append("Inconsistencias detectadas en patrones de ruido y bordes")
        
        if nivel_inconsistencia in ["alto", "muy_alto"]:
            indicators.append(f"Nivel alto de inconsistencia: {nivel_inconsistencia}")
        
        if areas_sospechosas > 0:
            indicators.append(f"{areas_sospechosas} áreas sospechosas detectadas")
        
        if patrones_ruido_inconsistentes > 0:
            indicators.append(f"{patrones_ruido_inconsistentes} patrones de ruido inconsistentes")
        
        if bordes_irregulares > 0:
            indicators.append(f"{bordes_irregulares} bordes irregulares detectados")
        
        if areas_sospechosas > 3:
            indicators.append("Múltiples áreas sospechosas - posible edición local")
        
        if patrones_ruido_inconsistentes > 2:
            indicators.append("Múltiples patrones de ruido inconsistentes - posible clonado")
        
        if bordes_irregulares > 2:
            indicators.append("Múltiples bordes irregulares - posible pegado de elementos")
        
        return indicators
