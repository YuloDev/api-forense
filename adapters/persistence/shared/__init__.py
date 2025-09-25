"""
Módulos compartidos para análisis forense.

Contiene helpers modulares para diferentes aspectos del análisis de documentos.
"""

from .image_renderer import render_png, diff_ratio, calculate_image_stats
from .stream_analyzer import localizar_overlay_por_stream
from .layer_analyzer import stack_compare
from .annotation_analyzer import inspeccionar_overlay_avanzado, analyze_annotations
from .image_analyzer import analyze_images, inventariar_imagenes
from .text_overlay_detector import TextOverlayDetector, detectar_texto_superpuesto_detallado

__all__ = [
    'render_png',
    'diff_ratio', 
    'calculate_image_stats',
    'localizar_overlay_por_stream',
    'stack_compare',
    'inspeccionar_overlay_avanzado',
    'analyze_annotations',
    'analyze_images',
    'inventariar_imagenes',
    'TextOverlayDetector',
    'detectar_texto_superpuesto_detallado'
]
