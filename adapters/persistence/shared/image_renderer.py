"""
Helper para renderizado de imágenes desde PDFs.

Maneja la conversión de páginas PDF a imágenes PNG para análisis visual.
"""

import fitz
import numpy as np
from PIL import ImageChops, Image
from helpers.type_conversion import ensure_python_float


def render_png(pdf_bytes: bytes, page_index: int = 0, dpi: int = 144) -> Image.Image:
    """
    Renderiza una página del PDF como imagen PNG.
    
    Args:
        pdf_bytes: PDF como bytes
        page_index: Índice de la página a renderizar
        dpi: Resolución para el renderizado
        
    Returns:
        PIL Image en formato RGB
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi)
    doc.close()
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def diff_ratio(img_a: Image.Image, img_b: Image.Image) -> float:
    """
    Calcula el porcentaje de píxeles diferentes entre dos imágenes.
    
    Args:
        img_a: Primera imagen
        img_b: Segunda imagen
        
    Returns:
        Porcentaje de píxeles diferentes (0.0 a 1.0)
    """
    d = ImageChops.difference(img_a, img_b).convert("L")
    arr = np.array(d)
    return ensure_python_float((arr > 0).mean())


def calculate_image_stats(img: Image.Image) -> dict:
    """
    Calcula estadísticas básicas de una imagen.
    
    Args:
        img: PIL Image
        
    Returns:
        Dict con estadísticas de la imagen
    """
    img_array = np.array(img)
    
    if len(img_array.shape) == 3:
        mean_val = float(np.mean(img_array))
        var_val = float(np.var(img_array))
        color_variance = np.var(img_array, axis=(0, 1))
        mean_color_variance = float(np.mean(color_variance))
    else:
        mean_val = float(np.mean(img_array))
        var_val = float(np.var(img_array))
        mean_color_variance = var_val
    
    return {
        "width": img.width,
        "height": img.height,
        "mean": mean_val,
        "variance": var_val,
        "color_variance": mean_color_variance,
        "format": img.format
    }
