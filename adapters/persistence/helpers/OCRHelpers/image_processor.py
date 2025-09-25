"""
Helper para procesamiento de imágenes en análisis forense OCR
"""
import cv2
import numpy as np
import statistics
from typing import Tuple, List
from PIL import Image
from domain.entities.forensic_ocr_details import BBox

class ImageProcessor:
    """Helper para procesamiento de imágenes"""
    
    @staticmethod
    def estimate_dpi(img: Image.Image) -> Tuple[float, float]:
        """Estima el DPI de la imagen"""
        width, height = img.size
        # Estimación básica basada en el tamaño
        if width > 2000 or height > 2000:
            return (300.0, 300.0)
        elif width > 1000 or height > 1000:
            return (200.0, 200.0)
        else:
            return (150.0, 150.0)

    @staticmethod
    def detect_skew_angle(img: Image.Image) -> float:
        """Detecta el ángulo de inclinación de la imagen"""
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            
            # Aplicar detección de bordes
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detectar líneas con Hough
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for line in lines:
                    rho, theta = line[0]
                    angle = float(np.degrees(theta)) - 90
                    if -45 <= angle <= 45:
                        angles.append(angle)
                
                if angles:
                    return float(statistics.median(angles))
            
            return 0.0
        except:
            return 0.0

    @staticmethod
    def merge_bboxes(bboxes: List[BBox]) -> BBox:
        """Combina múltiples bounding boxes en uno solo"""
        if not bboxes:
            return BBox(0, 0, 0, 0)
        
        min_x = min(b.x for b in bboxes)
        min_y = min(b.y for b in bboxes)
        max_x = max(b.x + b.w for b in bboxes)
        max_y = max(b.y + b.h for b in bboxes)
        
        return BBox(min_x, min_y, max_x - min_x, max_y - min_y)

    @staticmethod
    def boxes_overlap(box1: BBox, box2: BBox) -> bool:
        """Verifica si dos bounding boxes se superponen"""
        return not (box1.x + box1.w < box2.x or box2.x + box2.w < box1.x or
                   box1.y + box1.h < box2.y or box2.y + box2.h < box1.y)
