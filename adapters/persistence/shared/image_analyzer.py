"""
Helper para análisis de imágenes en PDFs.

Maneja la detección de parches sospechosos y análisis de imágenes.
"""

import io
import re
import hashlib
import numpy as np
import imagehash
import fitz
import pikepdf
from PIL import Image
from helpers.type_conversion import ensure_python_bool


def sha256(b: bytes) -> str:
    """Calcula SHA256 de bytes"""
    return hashlib.sha256(b).hexdigest()


def png_from_pdf_image(img_bytes: bytes, color_space: str = None) -> Image.Image:
    """Convierte bytes de imagen del PDF a PIL Image"""
    # Pillow suele abrir bien JPEG/JPX/Flate ya decodificados por PyMuPDF.
    return Image.open(io.BytesIO(img_bytes)).convert("RGBA")


def detectar_parche_sospechoso(pil_img: Image.Image, img_array: np.ndarray) -> bool:
    """
    Detecta si una imagen es un parche sospechoso que podría ocultar texto.
    
    Criterios:
    - Imagen muy pequeña (posible parche)
    - Colores uniformes (posible fondo para tapar)
    - Bordes rectangulares perfectos
    """
    try:
        # Criterio 1: Tamaño muy pequeño
        if pil_img.width < 50 or pil_img.height < 50:
            return True
            
        # Criterio 2: Variación de color muy baja (imagen uniforme)
        if len(img_array.shape) == 3:
            color_variance = np.var(img_array, axis=(0, 1))
            if np.mean(color_variance) < 10:  # Muy poca variación de color
                return True
                
        # Criterio 3: Bordes perfectamente rectangulares
        if tiene_bordes_rectangulares(img_array):
            return True
            
        return False
        
    except:
        return False


def tiene_bordes_rectangulares(img_array: np.ndarray) -> bool:
    """Detecta si la imagen tiene bordes perfectamente rectangulares"""
    try:
        if len(img_array.shape) == 3:
            # Convertir a escala de grises para análisis de bordes
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array
            
        # Detectar bordes usando gradientes
        grad_x = np.abs(np.diff(gray, axis=1))
        grad_y = np.abs(np.diff(gray, axis=0))
        
        # Si hay muchos bordes rectos, es sospechoso
        straight_edges_x = np.sum(grad_x > 50) / grad_x.size
        straight_edges_y = np.sum(grad_y > 50) / grad_y.size
        
        return ensure_python_bool(straight_edges_x > 0.1 or straight_edges_y > 0.1)
        
    except:
        return False


def buscar_bbox_correspondiente(name: str, block_bboxes: list) -> list:
    """Busca el bbox correspondiente a una imagen en los bloques de texto"""
    # Por ahora retorna bbox vacío, se puede mejorar con más lógica
    return [0, 0, 0, 0]


def determinar_orden_capa(name: str, xobjects: dict) -> int:
    """Determina el orden de capa de una imagen (aproximado)"""
    # Por ahora retorna orden basado en el nombre, se puede mejorar
    try:
        # Extraer número del nombre si existe
        numbers = re.findall(r'\d+', str(name))
        if numbers:
            return int(numbers[0])
        return 0
    except:
        return 0


def inventariar_imagenes(pdf_bytes: bytes, page_idx: int = 0) -> dict:
    """
    Inventaria todas las imágenes en una página del PDF.
    
    Args:
        pdf_bytes: PDF como bytes
        page_idx: Índice de la página (0-based)
        
    Returns:
        Dict con información detallada de las imágenes encontradas
    """
    out = {
        "page": page_idx + 1,
        "streams": 0,
        "images": []  # [{name,xref,bbox,layer_order,bytes,sha256,phash,mean,var,is_patch}]
    }

    try:
        # 1) BBoxes donde el motor de texto ve imágenes (orden de pintura)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_idx]
        raw = page.get_text("rawdict")
        img_blocks = [b for b in raw["blocks"] if b.get("type", 0) == 1]
        # Mapa de bboxes de imagen por orden
        block_bboxes = [b["bbox"] for b in img_blocks]
        doc.close()

        # 2) Streams y XObjects por PDF (pikepdf)
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            page_obj = pdf.pages[page_idx]
            resources = page_obj.get("/Resources", {})
            xobjects = resources.get("/XObject", {})
            
            out["streams"] = len(xobjects)
            
            for name, xobj in xobjects.items():
                if xobj.get("/Subtype") == "/Image":
                    try:
                        # Extraer bytes de la imagen
                        img_bytes = bytes(xobj.read_bytes())
                        
                        # Convertir a PIL Image
                        pil_img = png_from_pdf_image(img_bytes)
                        
                        # Calcular hash perceptual
                        phash = str(imagehash.phash(pil_img))
                        
                        # Estadísticas de la imagen
                        img_array = np.array(pil_img)
                        mean_val = float(np.mean(img_array))
                        var_val = float(np.var(img_array))
                        
                        # Detectar si es un parche sospechoso
                        is_patch = detectar_parche_sospechoso(pil_img, img_array)
                        
                        # Buscar bbox correspondiente
                        bbox = buscar_bbox_correspondiente(name, block_bboxes)
                        
                        # Determinar orden de capa (aproximado)
                        layer_order = determinar_orden_capa(name, xobjects)
                        
                        img_info = {
                            "name": str(name),
                            "xref": str(xobj.objgen),
                            "bbox": bbox,
                            "layer_order": layer_order,
                            "bytes": len(img_bytes),
                            "sha256": sha256(img_bytes),
                            "phash": phash,
                            "mean": mean_val,
                            "var": var_val,
                            "is_patch": is_patch,
                            "width": pil_img.width,
                            "height": pil_img.height,
                            "format": pil_img.format
                        }
                        
                        out["images"].append(img_info)
                        
                    except Exception as e:
                        # Si hay error procesando una imagen específica, continuar
                        continue

        return out
        
    except Exception as e:
        return {"error": f"Error en inventario de imágenes: {str(e)}"}


def analyze_images(doc, page_count: int, pdf_bytes: bytes) -> dict:
    """Análisis de imágenes en el PDF para detectar parches sospechosos"""
    try:
        resultados_paginas = []
        total_imagenes = 0
        total_parches_sospechosos = 0
        total_bytes_imagenes = 0
        
        for page_num in range(page_count):
            inventario = inventariar_imagenes(pdf_bytes, page_num)
            
            if "error" in inventario:
                resultados_paginas.append({
                    "pagina": page_num + 1,
                    "error": inventario["error"]
                })
                continue
            
            # Contar imágenes y parches sospechosos
            imagenes = inventario.get("images", [])
            parches_sospechosos = [img for img in imagenes if img.get("is_patch", False)]
            
            total_imagenes += len(imagenes)
            total_parches_sospechosos += len(parches_sospechosos)
            total_bytes_imagenes += sum(img.get("bytes", 0) for img in imagenes)
            
            # Análisis de la página
            analisis_pagina = {
                "pagina": page_num + 1,
                "total_imagenes": len(imagenes),
                "parches_sospechosos": len(parches_sospechosos),
                "bytes_imagenes": sum(img.get("bytes", 0) for img in imagenes),
                "imagenes": imagenes,
                "indicadores_sospechosos": {
                    "tiene_parches": len(parches_sospechosos) > 0,
                    "imagenes_pequenas": len([img for img in imagenes if img.get("width", 0) < 50 or img.get("height", 0) < 50]) > 0,
                    "imagenes_uniformes": len([img for img in imagenes if img.get("var", 0) < 10]) > 0,
                    "imagenes_rectangulares": len([img for img in imagenes if img.get("is_patch", False)]) > 0
                }
            }
            
            resultados_paginas.append(analisis_pagina)
        
        # Calcular probabilidad de superposición basada en imágenes
        probabilidad_imagenes = 0.0
        if total_imagenes > 0:
            probabilidad_imagenes = total_parches_sospechosos / total_imagenes
        
        # Determinar nivel de riesgo
        if probabilidad_imagenes >= 0.5:
            nivel_riesgo = "HIGH"
        elif probabilidad_imagenes >= 0.2:
            nivel_riesgo = "MEDIUM"
        else:
            nivel_riesgo = "LOW"
        
        return {
            "total_paginas_analizadas": page_count,
            "total_imagenes": total_imagenes,
            "total_parches_sospechosos": total_parches_sospechosos,
            "total_bytes_imagenes": total_bytes_imagenes,
            "probabilidad_overlay_imagenes": round(probabilidad_imagenes, 3),
            "nivel_riesgo_imagenes": nivel_riesgo,
            "detalles_por_pagina": resultados_paginas,
            "indicadores_clave": {
                "tiene_imagenes": total_imagenes > 0,
                "tiene_parches_sospechosos": total_parches_sospechosos > 0,
                "imagenes_pequenas_detectadas": any(
                    any(img.get("width", 0) < 50 or img.get("height", 0) < 50 for img in p.get("imagenes", []))
                    for p in resultados_paginas
                ),
                "imagenes_uniformes_detectadas": any(
                    any(img.get("var", 0) < 10 for img in p.get("imagenes", []))
                    for p in resultados_paginas
                )
            }
        }
        
    except Exception as e:
        return {"error": f"Error en análisis de imágenes: {str(e)}"}
