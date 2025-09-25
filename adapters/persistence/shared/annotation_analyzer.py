"""
Helper para análisis de anotaciones en PDFs.

Maneja la detección de overlay usando análisis avanzado de anotaciones.
"""

import re
import fitz
from typing import Dict, Any, List


def iou(a, b):
    """Calcula Intersection over Union entre dos bounding boxes"""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / area


def shape_bbox(dr):
    """Extrae bounding box de un drawing"""
    if dr.get("rect"):
        r = dr["rect"]
        return [r.x0, r.y0, r.x1, r.y1]
    xs, ys = [], []
    for it in dr.get("items", []):
        pts = it[1]
        xs += pts[::2]
        ys += pts[1::2]
    return [min(xs), min(ys), max(xs), max(ys)] if xs else None


def inspeccionar_overlay_avanzado(pdf_bytes: bytes, page_index: int = 0, buscar_texto: str = None) -> Dict[str, Any]:
    """
    Inspección avanzada de overlay usando la lógica mejorada.
    
    Devuelve dónde está el overlay:
    - annots: lista de anotaciones (rect, subtype)
    - sospechosos: imágenes/figuras que tapan texto (pintadas después)
    - contents_tail: últimos tokens del stream (para ver BT/Tj o 're f')
    - render_diff: True si al renderizar sin anotaciones desaparece algo (overlay en /Annots)
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_index]
        out = {
            "page": page_index + 1,
            "annots": [],
            "render_diff": False,
            "sospechosos": [],
            "contents_tail": "",
            "matches": []
        }

        # 1) Anotaciones
        a = page.first_annot
        while a:
            out["annots"].append({
                "subtype": a.type[1],
                "rect": list(a.rect),
                "flags": a.flags,
                "title": (a.info or {}).get("title"),
                "content": (a.info or {}).get("content")
            })
            a = a.next

        # 2) Diff visual con/sin anotaciones
        try:
            pm1 = page.get_pixmap()  # con anotaciones
            pm2 = page.get_pixmap(annots=False)  # sin anotaciones
            out["render_diff"] = (pm1.samples != pm2.samples)
        except Exception:
            pass

        # 3) Heurística de sobreposición en orden de pintura
        raw = page.get_text("rawdict")
        text_boxes = [b["bbox"] for b in raw["blocks"] if b.get("type", 0) == 0]
        
        # imágenes que tapan texto
        for b in raw["blocks"]:
            if b.get("type", 0) == 1:
                if any(iou(b["bbox"], tb) > 0.5 for tb in text_boxes):
                    out["sospechosos"].append({"type": "image", "bbox": b["bbox"]})
        
        # figuras rellenas (rectángulos "blancos")
        for dr in page.get_drawings():
            if dr.get("fill"):
                rect = shape_bbox(dr)
                if rect and any(iou(rect, tb) > 0.5 for tb in text_boxes):
                    out["sospechosos"].append({"type": "shape", "bbox": rect})

        # 4) Mirar el final del contenido (últimos tokens de @/Contents)
        try:
            stream = page.get_contents()  # bytes concatenados del content stream
            tail = stream[-1200:] if len(stream) > 1200 else stream
            out["contents_tail"] = tail.decode("latin-1", "ignore")
            if buscar_texto:
                # Busca literal (como "23.15" o el nuevo valor)
                for m in re.finditer(re.escape(buscar_texto), out["contents_tail"]):
                    out["matches"].append({
                        "pos": m.start(),
                        "snippet": out["contents_tail"][max(0, m.start() - 40):m.end() + 40]
                    })
        except Exception:
            pass

        doc.close()
        return out
        
    except Exception as e:
        return {"error": f"Error en inspección avanzada: {str(e)}"}


def analyze_annotations(doc, page_num: int) -> Dict[str, Any]:
    """Analiza anotaciones en una página específica"""
    results = {
        "has_annotations": False,
        "total_annotations": 0,
        "annotation_types": {},
        "overlapping_annotations": [],
        "text_annotations": [],
        "rect_annotations": [],
        "suspicious_patterns": []
    }
    
    try:
        total_annotations = 0
        overlapping_count = 0
        
        page = doc[page_num]
        annotations = page.annots()
        
        for annot in annotations:
            total_annotations += 1
            annot_info = extract_annotation_info(annot, page_num)
            
            # Clasificar por tipo
            subtype = annot_info.get("subtype", "Unknown")
            if subtype not in results["annotation_types"]:
                results["annotation_types"][subtype] = 0
            results["annotation_types"][subtype] += 1
            
            # Detectar anotaciones de texto
            if subtype in ["FreeText", "Text", "Note"]:
                results["text_annotations"].append(annot_info)
            
            # Detectar anotaciones con rectángulos (posible tapado)
            if "rect" in annot_info and annot_info["rect"]:
                results["rect_annotations"].append(annot_info)
                
                # Verificar si se superpone con contenido de la página
                if check_annotation_overlap(annot_info, page, page_num):
                    overlapping_count += 1
                    results["overlapping_annotations"].append(annot_info)
            
            # Detectar patrones sospechosos
            if is_suspicious_annotation(annot_info):
                results["suspicious_patterns"].append(annot_info)
        
        results["has_annotations"] = total_annotations > 0
        results["total_annotations"] = total_annotations
        results["overlapping_count"] = overlapping_count
        
    except Exception as e:
        results["error"] = f"Error analizando anotaciones: {str(e)}"
    
    return results


def extract_annotation_info(annot, page_num: int) -> Dict[str, Any]:
    """Extrae información detallada de una anotación"""
    try:
        rect = annot.rect
        subtype = annot.type[1] if annot.type else "Unknown"
        
        # Obtener contenido de la anotación
        content = ""
        if hasattr(annot, 'content'):
            content = annot.content or ""
        
        # Obtener apariencia si existe
        appearance = ""
        if hasattr(annot, 'get_apn'):
            try:
                appearance = annot.get_apn()
            except:
                pass
        
        return {
            "page": page_num,
            "subtype": subtype,
            "rect": [rect.x0, rect.y0, rect.x1, rect.y1] if rect else None,
            "content": content,
            "appearance": appearance,
            "has_appearance": bool(appearance),
            "is_text_annotation": subtype in ["FreeText", "Text", "Note"],
            "is_rectangle_annotation": subtype in ["Square", "Rectangle", "Stamp"]
        }
    except Exception as e:
        return {"error": f"Error extrayendo info de anotación: {str(e)}"}


def check_annotation_overlap(annot_info: Dict[str, Any], page, page_num: int) -> bool:
    """Verifica si una anotación se superpone con contenido de la página"""
    try:
        if not annot_info.get("rect"):
            return False
        
        rect = annot_info["rect"]
        
        # Obtener bloques de texto de la página
        text_dict = page.get_text("dict")
        blocks = text_dict.get('blocks', [])
        
        for block in blocks:
            if block.get('type') == 0:  # Bloque de texto
                bbox = block.get('bbox')
                if bbox and rectangles_overlap(rect, bbox):
                    return True
        
        return False
    except:
        return False


def is_suspicious_annotation(annot_info: Dict[str, Any]) -> bool:
    """Detecta anotaciones sospechosas"""
    # Anotaciones muy grandes
    if annot_info.get("rect"):
        rect = annot_info["rect"]
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        if width > 200 or height > 50:  # Anotación muy grande
            return True
    
    # Anotaciones con contenido vacío pero con apariencia
    if (not annot_info.get("content") and 
        annot_info.get("has_appearance") and 
        annot_info.get("is_rectangle_annotation")):
        return True
    
    return False


def rectangles_overlap(rect1: List[float], rect2: List[float]) -> bool:
    """Verifica si dos rectángulos se superponen"""
    return (rect1[0] < rect2[2] and rect1[2] > rect2[0] and 
            rect1[1] < rect2[3] and rect1[3] > rect2[1])
