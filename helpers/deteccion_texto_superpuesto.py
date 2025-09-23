"""
Helper especializado para detección de texto superpuesto en PDFs.

Analiza las 4 zonas principales donde se puede "tapar" texto en un PDF:
1. Anotaciones (Annotations) sobre la página
2. Contenido nuevo en la propia página (Page Contents)
3. Form XObject llamado desde la página
4. Campo de formulario (AcroForm)

Autor: Sistema de Análisis de Documentos
Versión: 1.0
"""

import re
import base64
import fitz
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import json
import io
from .type_conversion import ensure_python_bool, ensure_python_float, safe_serialize_dict
import copy
import numpy as np
from PIL import ImageChops, Image
import pikepdf
import imagehash
import hashlib


# Constantes para análisis por stream
PA = 0.05  # umbral de % de píxeles distintos para decir "hay cambio" (aumentado de 1% a 5%)
PIX_DIFF_THRESHOLD = 0.05  # 5% de píxeles distintos => consideramos que "cambió" (aumentado de 1% a 5%)


def _render_png(pdf_bytes: bytes, page_index=0, dpi=144) -> Image.Image:
    """Renderiza una página del PDF como imagen PNG"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi)
    doc.close()
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _diff_ratio(img_a: Image.Image, img_b: Image.Image) -> float:
    """Calcula el porcentaje de píxeles diferentes entre dos imágenes"""
    d = ImageChops.difference(img_a, img_b).convert("L")
    arr = np.array(d)
    return ensure_python_float((arr > 0).mean())  # % píxeles distintos


def _get_page_streams(pdf: pikepdf.Pdf, page_index: int):
    """Obtiene los streams de contenido de una página"""
    page = pdf.pages[page_index]
    cont = page.obj.get("/Contents", None)
    streams = []
    if isinstance(cont, pikepdf.Array):
        for s in cont:
            streams.append(bytes(s.read_bytes()))
    elif isinstance(cont, pikepdf.Stream):
        streams = [bytes(cont.read_bytes())]
    return streams


def _set_page_stream_prefix(pdf_bytes: bytes, page_index: int, k: int) -> bytes:
    """Deja solo los primeros k streams en /Contents."""
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_index]
        cont = page.obj.get("/Contents", None)
        if not cont:
            bio = io.BytesIO()
            pdf.save(bio)
            return bio.getvalue()
        if isinstance(cont, pikepdf.Array):
            new_streams = [pikepdf.Stream(pdf, bytes(cont[i].read_bytes())) for i in range(k)]
            page.obj["/Contents"] = pikepdf.Array(new_streams)
        elif isinstance(cont, pikepdf.Stream):
            if k <= 0:
                page.obj["/Contents"] = pikepdf.Stream(pdf, b" ")  # stream vacío
            else:
                page.obj["/Contents"] = pikepdf.Stream(pdf, bytes(cont.read_bytes()))
        bio = io.BytesIO()
        pdf.save(bio)
        return bio.getvalue()


def _get_annots(pdf: pikepdf.Pdf, page_index: int):
    """Obtiene las anotaciones de una página"""
    page = pdf.pages[page_index]
    arr = page.obj.get("/Annots", None)
    if arr is None:
        return []
    return list(arr)


def _set_annots_prefix(pdf_bytes: bytes, page_index: int, k: int) -> bytes:
    """Deja solo las primeras k anotaciones en /Annots."""
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_index]
        ann = page.obj.get("/Annots", None)
        if ann is not None:
            page.obj["/Annots"] = pikepdf.Array(list(ann)[:k])
        bio = io.BytesIO()
        pdf.save(bio)
        return bio.getvalue()


def _get_ocgs(pdf: pikepdf.Pdf):
    """Obtiene los Optional Content Groups del PDF"""
    ocp = pdf.Root.get("/OCProperties", None)
    if not ocp:
        return []
    ocgs = ocp.get("/OCGs", None)
    return list(ocgs) if ocgs else []


def _set_ocg_on_prefix(pdf_bytes: bytes, k: int) -> bytes:
    """Activa solo los primeros k OCGs (los demás OFF)."""
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        ocp = pdf.Root.get("/OCProperties", None)
        if not ocp:
            bio = io.BytesIO()
            pdf.save(bio)
            return bio.getvalue()
        ocgs = list(ocp.get("/OCGs", []))
        d = ocp.get("/D", pikepdf.Dictionary())
        on_arr = pikepdf.Array(ocgs[:k])
        off_arr = pikepdf.Array(ocgs[k:])
        d["/ON"] = on_arr
        d["/OFF"] = off_arr
        ocp["/D"] = d
        bio = io.BytesIO()
        pdf.save(bio)
        return bio.getvalue()


def stack_compare(pdf_bytes: bytes, page_index: int = 0, dpi: int = 144) -> Dict[str, Any]:
    """
    Análisis por capas del PDF - método más avanzado y preciso.
    
    Analiza sistemáticamente:
    1. Streams de contenido (/Contents)
    2. Anotaciones (/Annots) 
    3. Optional Content Groups (OCG)
    
    Args:
        pdf_bytes: PDF como bytes
        page_index: Índice de la página a analizar
        dpi: Resolución para renderizado
        
    Returns:
        Dict con análisis detallado por capas
    """
    try:
        baseline = _render_png(pdf_bytes, page_index, dpi)
        report = {
            "page": page_index + 1,
            "by_stream": [],
            "by_annot": [],
            "by_ocg": [],
            "threshold": PIX_DIFF_THRESHOLD,
            "dpi": dpi
        }

        # --- 1) Capas: /Contents (streams) ---
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            streams = _get_page_streams(pdf, page_index)
        
        prev_img = None
        for k in range(1, len(streams) + 1):
            bytes_k = _set_page_stream_prefix(pdf_bytes, page_index, k)
            img_k = _render_png(bytes_k, page_index, dpi)
            # compara contra k-1 (o baseline si k==1)
            base = baseline if k == 1 else prev_img
            ratio = _diff_ratio(img_k, base)
            report["by_stream"].append({
                "k": k,
                "changed": ratio > PIX_DIFF_THRESHOLD,
                "diff_ratio": ratio
            })
            prev_img = img_k

        # --- 2) Capas: /Annots (encima del contenido) ---
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            annots = _get_annots(pdf, page_index)
        
        if annots:
            prev_bytes = _set_annots_prefix(pdf_bytes, page_index, 0)  # sin annots
            prev_img = _render_png(prev_bytes, page_index, dpi)
            for k in range(1, len(annots) + 1):
                bytes_k = _set_annots_prefix(pdf_bytes, page_index, k)
                img_k = _render_png(bytes_k, page_index, dpi)
                ratio = _diff_ratio(img_k, prev_img)
                report["by_annot"].append({
                    "k": k,
                    "changed": ratio > PIX_DIFF_THRESHOLD,
                    "diff_ratio": ratio
                })
                prev_img = img_k

        # --- 3) Capas: OCG (si hay) ---
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            ocgs = _get_ocgs(pdf)
        
        if ocgs:
            prev_bytes = _set_ocg_on_prefix(pdf_bytes, 0)
            prev_img = _render_png(prev_bytes, page_index, dpi)
            for k in range(1, len(ocgs) + 1):
                bytes_k = _set_ocg_on_prefix(pdf_bytes, k)
                img_k = _render_png(bytes_k, page_index, dpi)
                ratio = _diff_ratio(img_k, prev_img)
                report["by_ocg"].append({
                    "k": k,
                    "changed": ratio > PIX_DIFF_THRESHOLD,
                    "diff_ratio": ratio
                })
                prev_img = img_k

        return report
        
    except Exception as e:
        return {"error": f"Error en análisis por capas: {str(e)}"}


def localizar_overlay_por_stream(pdf_bytes: bytes, page_index: int = 0) -> Dict[str, Any]:
    """
    Localiza overlay analizando streams de contenido uno por uno.
    
    1) Render completo
    2) Por cada prefijo de streams (1..N) renderiza y compara
    3) Devuelve el índice del stream que introduce el cambio y su contenido
    
    Args:
        pdf_bytes: PDF como bytes
        page_index: Índice de la página a analizar
        
    Returns:
        Dict con información del stream que introduce el overlay
    """
    try:
        base_img = _render_png(pdf_bytes, page_index)

        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            page = pdf.pages[page_index]
            cont = page.obj.get("/Contents", None)

            # Normaliza a lista de streams
            streams = []
            if isinstance(cont, pikepdf.Array):
                for obj in cont:
                    streams.append(bytes(obj.read_bytes()))
            elif isinstance(cont, pikepdf.Stream):
                streams = [bytes(cont.read_bytes())]
            else:
                return {"streams": 0, "overlay_stream": None, "reason": "Sin /Contents"}

            overlay_idx = None
            overlay_ratio = None
            
            # Probar prefijos 1..N
            for k in range(1, len(streams) + 1):
                # Construir PDF clonado con sólo los primeros k streams
                with pikepdf.open(io.BytesIO(pdf_bytes)) as tmp:
                    p = tmp.pages[page_index]
                    # crea nuevos streams pikepdf con los bytes originales
                    new_streams = [pikepdf.Stream(tmp, s) for s in streams[:k]]
                    if len(new_streams) == 1:
                        p.obj["/Contents"] = new_streams[0]
                    else:
                        arr = pikepdf.Array(tmp, new_streams)
                        p.obj["/Contents"] = arr
                    bio = io.BytesIO()
                    tmp.save(bio)
                    test_bytes = bio.getvalue()

                img = _render_png(test_bytes, page_index)
                ratio = _diff_ratio(img, base_img)
                if ratio > PA:
                    overlay_idx = k - 1  # índice del stream que "introduce" diferencia
                    overlay_ratio = ratio
                    break

            # Vuelca el stream sospechoso (si existe)
            sospechoso = None
            if overlay_idx is not None:
                sospechoso = streams[overlay_idx].decode("latin-1", "ignore")

            return {
                "streams": len(streams),
                "overlay_stream": overlay_idx,    # 0..N-1
                "overlay_ratio": overlay_ratio,
                "overlay_ratio_formatted": None if overlay_idx is None else f">{overlay_ratio:.2%}",
                "stream_preview": None if sospechoso is None else sospechoso[-1200:],  # cola
                "stream_full": sospechoso,
                "threshold": PA,
                "detected": overlay_idx is not None
            }
            
    except Exception as e:
        return {"error": f"Error en análisis por stream: {str(e)}"}


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


def _shape_bbox(dr):
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
                rect = _shape_bbox(dr)
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


class TextOverlayDetector:
    """Detector especializado de texto superpuesto en PDFs"""
    
    def __init__(self, pdf_bytes: bytes):
        self.pdf_bytes = pdf_bytes
        self.doc = None
        self.analysis_results = {
            "zona_1_anotaciones": {},
            "zona_2_contenido_pagina": {},
            "zona_3_form_xobject": {},
            "zona_4_acroform": {},
            "resumen_general": {},
            "xml_estructura": {}
        }
    
    def analyze_pdf(self) -> Dict[str, Any]:
        """Ejecuta el análisis completo del PDF"""
        try:
            self.doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
            
            # Analizar cada zona
            self.analysis_results["zona_1_anotaciones"] = self._analyze_annotations()
            self.analysis_results["zona_2_contenido_pagina"] = self._analyze_page_contents()
            self.analysis_results["zona_3_form_xobject"] = self._analyze_form_xobjects()
            self.analysis_results["zona_4_acroform"] = self._analyze_acroform()
            
            # NUEVA: Análisis avanzado de overlay
            self.analysis_results["analisis_avanzado_overlay"] = self._analyze_advanced_overlay()
            
            # NUEVA: Análisis por stream (método más preciso)
            self.analysis_results["analisis_por_stream"] = self._analyze_stream_overlay()
            
            # NUEVA: Análisis por capas (método más avanzado)
            self.analysis_results["analisis_por_capas"] = self._analyze_stack_layers()
            
            # NUEVA: Análisis de imágenes
            self.analysis_results["analisis_imagenes"] = self._analyze_images()
            
            # Generar resumen general
            self.analysis_results["resumen_general"] = self._generate_summary()
            
            # Extraer XML/estructura del PDF
            self.analysis_results["xml_estructura"] = self._extract_pdf_structure()
            
            # Devolver la estructura original del análisis
            return self.analysis_results
            
        except Exception as e:
            return {"error": f"Error analizando PDF: {str(e)}"}
        finally:
            if self.doc:
                self.doc.close()
    
    def _analyze_annotations(self) -> Dict[str, Any]:
        """ZONA 1: Analiza anotaciones (Annotations) sobre la página"""
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
            
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                annotations = page.annots()
                
                for annot in annotations:
                    total_annotations += 1
                    annot_info = self._extract_annotation_info(annot, page_num)
                    
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
                        if self._check_annotation_overlap(annot_info, page_num):
                            overlapping_count += 1
                            results["overlapping_annotations"].append(annot_info)
                    
                    # Detectar patrones sospechosos
                    if self._is_suspicious_annotation(annot_info):
                        results["suspicious_patterns"].append(annot_info)
            
            results["has_annotations"] = total_annotations > 0
            results["total_annotations"] = total_annotations
            results["overlapping_count"] = overlapping_count
            
        except Exception as e:
            results["error"] = f"Error analizando anotaciones: {str(e)}"
        
        return results
    
    def _analyze_page_contents(self) -> Dict[str, Any]:
        """ZONA 2: Analiza contenido nuevo en la propia página"""
        results = {
            "has_multiple_streams": False,
            "stream_count": 0,
            "text_commands": [],
            "rectangle_commands": [],
            "color_commands": [],
            "suspicious_sequences": [],
            "overlapping_content": []
        }
        
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                
                # Obtener streams de contenido
                contents = page.get_contents()
                if contents:
                    if isinstance(contents, list):
                        results["stream_count"] += len(contents)
                        results["has_multiple_streams"] = len(contents) > 1
                    else:
                        results["stream_count"] = 1
                    
                    # Analizar cada stream
                    for stream_id in (contents if isinstance(contents, list) else [contents]):
                        stream_analysis = self._analyze_content_stream(stream_id, page_num)
                        
                        results["text_commands"].extend(stream_analysis["text_commands"])
                        results["rectangle_commands"].extend(stream_analysis["rectangle_commands"])
                        results["color_commands"].extend(stream_analysis["color_commands"])
                        results["suspicious_sequences"].extend(stream_analysis["suspicious_sequences"])
                        results["overlapping_content"].extend(stream_analysis["overlapping_content"])
        
        except Exception as e:
            results["error"] = f"Error analizando contenido de página: {str(e)}"
        
        return results
    
    def _analyze_form_xobjects(self) -> Dict[str, Any]:
        """ZONA 3: Analiza Form XObjects llamados desde la página"""
        results = {
            "has_form_xobjects": False,
            "xobject_count": 0,
            "form_xobjects": [],
            "text_xobjects": [],
            "suspicious_xobjects": []
        }
        
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                
                # Obtener recursos de la página
                resources = page.get_contents()
                if resources:
                    # Buscar XObjects en el diccionario de recursos
                    xobjects = self._extract_xobjects_from_page(page)
                    
                    for xobj_name, xobj_info in xobjects.items():
                        results["xobject_count"] += 1
                        results["form_xobjects"].append(xobj_info)
                        
                        # Analizar si contiene texto
                        if xobj_info.get("has_text", False):
                            results["text_xobjects"].append(xobj_info)
                        
                        # Detectar XObjects sospechosos
                        if self._is_suspicious_xobject(xobj_info):
                            results["suspicious_xobjects"].append(xobj_info)
            
            results["has_form_xobjects"] = results["xobject_count"] > 0
        
        except Exception as e:
            results["error"] = f"Error analizando Form XObjects: {str(e)}"
        
        return results
    
    def _analyze_acroform(self) -> Dict[str, Any]:
        """ZONA 4: Analiza campos de formulario (AcroForm)"""
        results = {
            "has_acroform": False,
            "form_fields": [],
            "widget_annotations": [],
            "text_fields": [],
            "overlapping_fields": []
        }
        
        try:
            # Verificar si el documento tiene AcroForm
            if hasattr(self.doc, 'metadata') and self.doc.metadata:
                # Buscar AcroForm en el catálogo
                acroform_info = self._extract_acroform_info()
                
                if acroform_info:
                    results["has_acroform"] = True
                    results["form_fields"] = acroform_info.get("fields", [])
                    
                    # Analizar campos de texto específicamente
                    for field in acroform_info.get("fields", []):
                        if field.get("type") == "text":
                            results["text_fields"].append(field)
                        
                        # Verificar si el campo se superpone con contenido
                        if self._check_field_overlap(field):
                            results["overlapping_fields"].append(field)
        
        except Exception as e:
            results["error"] = f"Error analizando AcroForm: {str(e)}"
        
        return results
    
    def _extract_annotation_info(self, annot, page_num: int) -> Dict[str, Any]:
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
    
    def _check_annotation_overlap(self, annot_info: Dict[str, Any], page_num: int) -> bool:
        """Verifica si una anotación se superpone con contenido de la página"""
        try:
            if not annot_info.get("rect"):
                return False
            
            page = self.doc[page_num]
            rect = annot_info["rect"]
            
            # Obtener bloques de texto de la página
            text_dict = page.get_text("dict")
            blocks = text_dict.get('blocks', [])
            
            for block in blocks:
                if block.get('type') == 0:  # Bloque de texto
                    bbox = block.get('bbox')
                    if bbox and self._rectangles_overlap(rect, bbox):
                        return True
            
            return False
        except:
            return False
    
    def _is_suspicious_annotation(self, annot_info: Dict[str, Any]) -> bool:
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
    
    def _analyze_content_stream(self, stream_id, page_num: int) -> Dict[str, Any]:
        """Analiza un stream de contenido específico"""
        results = {
            "text_commands": [],
            "rectangle_commands": [],
            "color_commands": [],
            "suspicious_sequences": [],
            "overlapping_content": []
        }
        
        try:
            # Obtener el contenido del stream
            stream_content = self.doc.get_page_content(stream_id)
            if not stream_content:
                return results
            
            # Convertir a string para análisis
            if isinstance(stream_content, bytes):
                stream_text = stream_content.decode('latin-1', errors='ignore')
            else:
                stream_text = str(stream_content)
            
            # Buscar comandos de texto
            text_pattern = r'BT\s+(.*?)\s+ET'
            text_matches = re.findall(text_pattern, stream_text, re.DOTALL)
            for match in text_matches:
                results["text_commands"].append({
                    "page": page_num,
                    "content": match[:100] + "..." if len(match) > 100 else match,
                    "full_content": match
                })
            
            # Buscar comandos de rectángulo
            rect_pattern = r'(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+re\s+f'
            rect_matches = re.findall(rect_pattern, stream_text)
            for match in rect_matches:
                results["rectangle_commands"].append({
                    "page": page_num,
                    "x": float(match[0]),
                    "y": float(match[1]),
                    "width": float(match[2]),
                    "height": float(match[3])
                })
            
            # Buscar comandos de color
            color_pattern = r'(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+rg'
            color_matches = re.findall(color_pattern, stream_text)
            for match in color_matches:
                results["color_commands"].append({
                    "page": page_num,
                    "r": float(match[0]),
                    "g": float(match[1]),
                    "b": float(match[2])
                })
            
            # Detectar secuencias sospechosas (rectángulo blanco + texto)
            suspicious_pattern = r'(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+re\s+1\s+1\s+1\s+rg\s+f\s+.*?BT\s+.*?Tj\s+ET'
            suspicious_matches = re.findall(suspicious_pattern, stream_text, re.DOTALL)
            for match in suspicious_matches:
                results["suspicious_sequences"].append({
                    "page": page_num,
                    "description": "Rectángulo blanco seguido de texto",
                    "rect": match[:4]
                })
        
        except Exception as e:
            results["error"] = f"Error analizando stream: {str(e)}"
        
        return results
    
    def _extract_xobjects_from_page(self, page) -> Dict[str, Dict[str, Any]]:
        """Extrae información de XObjects de una página"""
        xobjects = {}
        try:
            # Esta es una implementación simplificada
            # En una implementación completa, necesitarías acceder al diccionario de recursos
            return xobjects
        except Exception as e:
            return {}
    
    def _is_suspicious_xobject(self, xobj_info: Dict[str, Any]) -> bool:
        """Detecta XObjects sospechosos"""
        # Implementar lógica de detección de XObjects sospechosos
        return False
    
    def _extract_acroform_info(self) -> Optional[Dict[str, Any]]:
        """Extrae información del AcroForm del documento"""
        try:
            # Implementar extracción de AcroForm
            return None
        except Exception as e:
            return None
    
    def _check_field_overlap(self, field: Dict[str, Any]) -> bool:
        """Verifica si un campo se superpone con contenido"""
        # Implementar verificación de superposición de campos
        return False
    
    def _rectangles_overlap(self, rect1: List[float], rect2: List[float]) -> bool:
        """Verifica si dos rectángulos se superponen"""
        return (rect1[0] < rect2[2] and rect1[2] > rect2[0] and 
                rect1[1] < rect2[3] and rect1[3] > rect2[1])
    
    def _calcular_factor_contexto(self) -> float:
        """
        Calcula un factor de contexto para reducir falsos positivos.
        
        Considera:
        - Fechas de creación y modificación iguales (indica documento original)
        - Número de streams (muy pocos streams pueden ser normales)
        - Metadatos del PDF
        """
        try:
            factor = 1.0  # Factor base
            
            # Verificar fechas de creación y modificación
            if hasattr(self.doc, 'metadata') and self.doc.metadata:
                metadata = dict(self.doc.metadata)
                creation_date = metadata.get('creationDate', '')
                mod_date = metadata.get('modDate', '')
                
                # Si las fechas son iguales, es menos probable que sea editado
                if creation_date and mod_date and creation_date == mod_date:
                    factor *= 0.3  # Reducir significativamente la probabilidad
                
                # Si el productor es conocido (como iText), puede ser normal tener múltiples streams
                producer = metadata.get('producer', '').lower()
                if 'itext' in producer or 'adobe' in producer:
                    factor *= 0.7  # Reducir ligeramente
            
            # Verificar número de streams
            total_streams = 0
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                contents = page.get_contents()
                if contents:
                    if isinstance(contents, list):
                        total_streams += len(contents)
                    else:
                        total_streams += 1
            
            # Si hay muy pocos streams (1-2), es menos sospechoso
            if total_streams <= 2:
                factor *= 0.5
            
            return max(factor, 0.1)  # Mínimo factor de 0.1
            
        except Exception:
            return 1.0  # Si hay error, usar factor neutro
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Genera un resumen general del análisis con la nueva estructura"""
        
        # Obtener análisis de cada método
        analisis_avanzado = self.analysis_results.get("analisis_avanzado_overlay", {})
        analisis_stream = self.analysis_results.get("analisis_por_stream", {})
        analisis_capas = self.analysis_results.get("analisis_por_capas", {})
        analisis_imagenes = self.analysis_results.get("analisis_imagenes", {})
        
        # Calcular probabilidad general (usar la más alta)
        probabilidades = [
            analisis_avanzado.get("probabilidad_overlay", 0.0),
            analisis_stream.get("probabilidad_overlay", 0.0),
            analisis_capas.get("probabilidad_overlay", 0.0),
            analisis_imagenes.get("probabilidad_overlay_imagenes", 0.0)
        ]
        overlay_probability = max(probabilidades) if probabilidades else 0.0
        
        # Determinar nivel de riesgo (umbrales más altos para reducir falsos positivos)
        niveles_riesgo = [
            analisis_avanzado.get("nivel_riesgo", "LOW"),
            analisis_stream.get("nivel_riesgo", "LOW"),
            analisis_capas.get("nivel_riesgo", "LOW"),
            analisis_imagenes.get("nivel_riesgo_imagenes", "LOW")
        ]
        
        # Contar cuántos análisis indican HIGH
        high_count = niveles_riesgo.count("HIGH")
        
        # Lógica más sensible para detectar riesgo
        if high_count >= 1 or overlay_probability >= 0.6:
            risk_level = "HIGH"
            recommendations = ["Alto riesgo de texto superpuesto detectado"]
        elif overlay_probability >= 0.3:
            risk_level = "MEDIUM"
            recommendations = ["Riesgo medio de texto superpuesto"]
        else:
            risk_level = "LOW"
            recommendations = ["Bajo riesgo de texto superpuesto"]
        
        # Contar zonas con overlay
        zones_with_overlay = sum([
            1 for analisis in [analisis_avanzado, analisis_stream, analisis_capas, analisis_imagenes]
            if analisis.get("overlay_detectado", False) or analisis.get("tiene_parches_sospechosos", False)
        ])
        
        # Generar resumen con la nueva estructura
        resumen = {
            "probabilidad_manipulacion": overlay_probability,
            "nivel_riesgo": risk_level,
            "total_zones_analyzed": 8,
            "zones_with_overlay": zones_with_overlay,
            "overlay_probability": overlay_probability,
            "risk_level": risk_level,
            "recommendations": recommendations,
            "analisis_avanzado": {
                "total_anotaciones": analisis_avanzado.get("total_anotaciones", 0),
                "elementos_sospechosos": analisis_avanzado.get("total_elementos_sospechosos", 0),
                "diferencia_visual": analisis_avanzado.get("paginas_con_render_diff", 0),
                "probabilidad_overlay": analisis_avanzado.get("probabilidad_overlay", 0.0)
            },
            "analisis_por_stream": {
                "total_streams": analisis_stream.get("total_streams", 0),
                "streams_sospechosos": analisis_stream.get("streams_sospechosos", 0),
                "paginas_con_overlay": analisis_stream.get("paginas_con_overlay", 0),
                "probabilidad_overlay": analisis_stream.get("probabilidad_overlay", 0.0),
                "threshold_pixels": analisis_stream.get("threshold_pixels", 0.01)
            },
            "analisis_por_capas": {
                "total_streams": analisis_capas.get("total_streams", 0),
                "total_annots": analisis_capas.get("total_annots", 0),
                "total_ocgs": analisis_capas.get("total_ocgs", 0),
                "streams_con_cambios": analisis_capas.get("streams_con_cambios", 0),
                "annots_con_cambios": analisis_capas.get("annots_con_cambios", 0),
                "ocgs_con_cambios": analisis_capas.get("ocgs_con_cambios", 0),
                "probabilidad_overlay": analisis_capas.get("probabilidad_overlay", 0.0),
                "threshold_pixels": analisis_capas.get("threshold_pixels", 0.01)
            }
        }
        
        return resumen
    
    def _generate_restructured_json(self) -> Dict[str, Any]:
        """Genera el JSON con la nueva estructura solicitada"""
        
        # Obtener análisis de cada método
        analisis_avanzado = self.analysis_results.get("analisis_avanzado_overlay", {})
        analisis_stream = self.analysis_results.get("analisis_por_stream", {})
        analisis_capas = self.analysis_results.get("analisis_por_capas", {})
        analisis_imagenes = self.analysis_results.get("analisis_imagenes", {})
        resumen_general = self.analysis_results.get("resumen_general", {})
        
        # Generar detalles por página (usando análisis por stream)
        detalles_por_pagina = []
        if "detalles_por_pagina" in analisis_stream:
            for detalle in analisis_stream["detalles_por_pagina"]:
                detalles_por_pagina.append({
                    "streams": detalle.get("streams", 0),
                    "overlay_stream": detalle.get("overlay_stream", 0),
                    "overlay_ratio": detalle.get("overlay_ratio", 0.0),
                    "overlay_ratio_formatted": f">{detalle.get('overlay_ratio', 0.0) * 100:.2f}%",
                    "threshold": detalle.get("threshold", 0.01),
                    "detected": detalle.get("detected", False),
                    "page": detalle.get("page", 1)
                })
        
        # Generar indicadores clave
        indicadores_clave = {
            "overlay_detectado": any([
                analisis_avanzado.get("overlay_detectado", False),
                analisis_stream.get("overlay_detectado", False),
                analisis_capas.get("overlay_detectado", False),
                analisis_imagenes.get("tiene_parches_sospechosos", False)
            ]),
            "tiene_streams_cambios": analisis_stream.get("streams_con_cambios", 0) > 0,
            "tiene_annots_cambios": analisis_capas.get("annots_con_cambios", 0) > 0,
            "tiene_ocgs_cambios": analisis_capas.get("ocgs_con_cambios", 0) > 0,
            "metodo_mas_avanzado": True
        }
        
        # Generar resumen con la estructura exacta solicitada
        resumen = {
            "probabilidad_manipulacion": resumen_general.get("probabilidad_manipulacion", 0.0),
            "nivel_riesgo": resumen_general.get("nivel_riesgo", "LOW"),
            "total_zones_analyzed": resumen_general.get("total_zones_analyzed", 8),
            "zones_with_overlay": resumen_general.get("zones_with_overlay", 0),
            "overlay_probability": resumen_general.get("overlay_probability", 0.0),
            "risk_level": resumen_general.get("risk_level", "LOW"),
            "recommendations": resumen_general.get("recommendations", []),
            "analisis_avanzado": resumen_general.get("analisis_avanzado", {}),
            "analisis_por_stream": resumen_general.get("analisis_por_stream", {}),
            "analisis_por_capas": resumen_general.get("analisis_por_capas", {})
        }
        
        # Generar check de capas múltiples con penalización dinámica
        capas_check = self._generate_capas_check()
        
        # Estructura final del JSON
        resultado_final = {
            "resumen": resumen,
            "detalles_por_pagina": detalles_por_pagina,
            "indicadores_clave": indicadores_clave,
            "analisis_imagenes": resumen["analisis_imagenes"],
            "capas_multiples": capas_check
        }
        
        return safe_serialize_dict(resultado_final)
    
    def _generate_capas_check(self) -> Dict[str, Any]:
        """Genera el check de capas múltiples con penalización dinámica"""
        
        # Obtener análisis de capas
        analisis_capas = self.analysis_results.get("analisis_por_capas", {})
        resumen_general = self.analysis_results.get("resumen_general", {})
        
        # Calcular probabilidad y nivel de riesgo
        probabilidad = analisis_capas.get("probabilidad_overlay", 0.0)
        nivel_riesgo = analisis_capas.get("nivel_riesgo", "LOW")
        
        # Calcular penalización dinámica según nivel de riesgo
        peso_base = RISK_WEIGHTS.get("capas_multiples")  # Valor base de capas_multiples
        if nivel_riesgo == "HIGH":
            penalizacion = peso_base  # Penalización completa
        elif nivel_riesgo == "MEDIUM":
            penalizacion = peso_base  # Mitad de la penalización
        else:  # LOW
            penalizacion = 0  # Sin penalización
        
        # Generar explicación de penalización
        penalty_explanation = f"Penalización dinámica calculada: {penalizacion} puntos para {probabilidad*100:.1f}% de probabilidad (nivel: {nivel_riesgo})"
        
        # Generar check de capas
        capas_check = {
            "check": "Presencia de capas múltiples (análisis integrado)",
            "detalle": {
                "deteccion_avanzada": analisis_capas.get("overlay_detectado", False),
                "porcentaje_probabilidad": probabilidad * 100,
                "nivel_riesgo": nivel_riesgo,
                "confianza": probabilidad,
                "indicadores": analisis_capas.get("indicadores", []),
                "objetos_ocg": analisis_capas.get("total_ocgs", 0),
                "objetos_superpuestos": analisis_capas.get("objetos_superpuestos", 0),
                "objetos_transparencia": analisis_capas.get("objetos_transparencia", 0),
                "operadores_sospechosos": analisis_capas.get("operadores_sospechosos", 0),
                "content_streams": analisis_capas.get("content_streams", 0),
                "modos_fusion": analisis_capas.get("modos_mezcla", []),
                "valores_alpha": analisis_capas.get("valores_alpha", []),
                "desglose_puntuacion": analisis_capas.get("desglose_puntuacion", {}),
                "estimacion_capas": analisis_capas.get("estimacion_capas", 0),
                "analisis_detallado": analisis_capas.get("analisis_detallado", {}),
                "metodo_calculo": "sistema_dinamico_v2",
                "peso_base_usado": {"capas_multiples": peso_base},
                "penalty_method": "deteccion_texto_superpuesto_universal",
                "penalty_calculated": penalizacion,
                "penalty_explanation": penalty_explanation
            },
            "penalizacion": penalizacion
        }
        
        return capas_check
    
    def _extract_pdf_structure(self) -> Dict[str, Any]:
        """Extrae la estructura XML/PDF del documento"""
        structure = {
            "pdf_version": None,
            "page_count": 0,
            "metadata": {},
            "catalog_info": {},
            "xref_info": {}
        }
        
        try:
            # Información básica del PDF
            structure["page_count"] = self.doc.page_count
            
            # Metadatos
            if hasattr(self.doc, 'metadata') and self.doc.metadata:
                structure["metadata"] = dict(self.doc.metadata)
            
            # Información del catálogo (simplificada)
            structure["catalog_info"] = {
                "has_acroform": False,  # Se detectaría en análisis completo
                "has_outline": False,
                "has_pages": True
            }
            
        except Exception as e:
            structure["error"] = f"Error extrayendo estructura: {str(e)}"
        
        return structure
    
    def _analyze_advanced_overlay(self) -> Dict[str, Any]:
        """Análisis avanzado de overlay usando la lógica mejorada"""
        try:
            # Usar la función avanzada para cada página
            resultados_paginas = []
            
            for page_num in range(self.doc.page_count):
                resultado_pagina = inspeccionar_overlay_avanzado(
                    self.pdf_bytes, 
                    page_index=page_num
                )
                resultados_paginas.append(resultado_pagina)
            
            # Consolidar resultados
            total_annots = sum(len(p.get("annots", [])) for p in resultados_paginas)
            total_sospechosos = sum(len(p.get("sospechosos", [])) for p in resultados_paginas)
            paginas_con_render_diff = sum(1 for p in resultados_paginas if p.get("render_diff", False))
            
            # Calcular probabilidad de overlay
            probabilidad_overlay = 0.0
            if total_annots > 0:
                probabilidad_overlay += 0.4  # Anotaciones son indicador fuerte
            if total_sospechosos > 0:
                probabilidad_overlay += 0.3  # Elementos sospechosos
            if paginas_con_render_diff > 0:
                probabilidad_overlay += 0.3  # Diferencia visual
            
            # Determinar nivel de riesgo
            if probabilidad_overlay >= 0.7:
                nivel_riesgo = "HIGH"
            elif probabilidad_overlay >= 0.4:
                nivel_riesgo = "MEDIUM"
            else:
                nivel_riesgo = "LOW"
            
            return {
                "total_paginas_analizadas": self.doc.page_count,
                "total_anotaciones": total_annots,
                "total_elementos_sospechosos": total_sospechosos,
                "paginas_con_render_diff": paginas_con_render_diff,
                "probabilidad_overlay": round(probabilidad_overlay, 3),
                "nivel_riesgo": nivel_riesgo,
                "detalles_por_pagina": resultados_paginas,
                "indicadores_clave": {
                    "tiene_anotaciones": total_annots > 0,
                    "tiene_elementos_sospechosos": total_sospechosos > 0,
                    "tiene_diferencia_visual": paginas_con_render_diff > 0,
                    "overlay_detectado": probabilidad_overlay > 0.5
                }
            }
            
        except Exception as e:
            return {"error": f"Error en análisis avanzado: {str(e)}"}
    
    def _analyze_stream_overlay(self) -> Dict[str, Any]:
        """Análisis por stream para detectar overlay con máxima precisión"""
        try:
            resultados_paginas = []
            
            for page_num in range(self.doc.page_count):
                resultado_pagina = localizar_overlay_por_stream(
                    self.pdf_bytes, 
                    page_index=page_num
                )
                resultado_pagina["page"] = page_num + 1
                resultados_paginas.append(resultado_pagina)
            
            # Consolidar resultados
            total_streams = sum(p.get("streams", 0) for p in resultados_paginas)
            paginas_con_overlay = sum(1 for p in resultados_paginas if p.get("detected", False))
            streams_sospechosos = [p for p in resultados_paginas if p.get("overlay_stream") is not None]
            
            # Calcular probabilidad basada en detección por stream
            probabilidad_stream = 0.0
            if total_streams > 0:
                probabilidad_stream = len(streams_sospechosos) / len(resultados_paginas)
            
            # Aplicar factor de contexto para reducir falsos positivos
            factor_contexto = self._calcular_factor_contexto()
            probabilidad_stream *= factor_contexto
            
            # Determinar nivel de riesgo (umbrales ajustados)
            if probabilidad_stream >= 0.6:
                nivel_riesgo = "HIGH"
            elif probabilidad_stream >= 0.3:
                nivel_riesgo = "MEDIUM"
            else:
                nivel_riesgo = "LOW"
            
            return {
                "total_paginas_analizadas": self.doc.page_count,
                "total_streams": total_streams,
                "paginas_con_overlay": paginas_con_overlay,
                "streams_sospechosos": len(streams_sospechosos),
                "probabilidad_overlay": round(probabilidad_stream, 3),
                "nivel_riesgo": nivel_riesgo,
                "threshold_pixels": PA,
                "detalles_por_pagina": resultados_paginas,
                "indicadores_clave": {
                    "overlay_detectado": paginas_con_overlay > 0,
                    "tiene_streams_sospechosos": len(streams_sospechosos) > 0,
                    "metodo_mas_preciso": True
                }
            }
            
        except Exception as e:
            return {"error": f"Error en análisis por stream: {str(e)}"}
    
    def _analyze_stack_layers(self) -> Dict[str, Any]:
        """Análisis por capas - método más avanzado y preciso"""
        try:
            resultados_paginas = []
            
            for page_num in range(self.doc.page_count):
                resultado_pagina = stack_compare(
                    self.pdf_bytes, 
                    page_index=page_num
                )
                resultados_paginas.append(resultado_pagina)
            
            # Consolidar resultados
            total_streams = sum(len(p.get("by_stream", [])) for p in resultados_paginas)
            total_annots = sum(len(p.get("by_annot", [])) for p in resultados_paginas)
            total_ocgs = sum(len(p.get("by_ocg", [])) for p in resultados_paginas)
            
            # Contar cambios detectados
            streams_con_cambios = sum(
                sum(1 for s in p.get("by_stream", []) if s.get("changed", False))
                for p in resultados_paginas
            )
            annots_con_cambios = sum(
                sum(1 for a in p.get("by_annot", []) if a.get("changed", False))
                for p in resultados_paginas
            )
            ocgs_con_cambios = sum(
                sum(1 for o in p.get("by_ocg", []) if o.get("changed", False))
                for p in resultados_paginas
            )
            
            # Calcular probabilidad basada en análisis por capas
            total_cambios = streams_con_cambios + annots_con_cambios + ocgs_con_cambios
            total_elementos = total_streams + total_annots + total_ocgs
            
            probabilidad_capas = 0.0
            if total_elementos > 0:
                probabilidad_capas = total_cambios / total_elementos
            
            # Aplicar factor de contexto para reducir falsos positivos
            factor_contexto = self._calcular_factor_contexto()
            probabilidad_capas *= factor_contexto
            
            # Determinar nivel de riesgo (umbrales ajustados)
            if probabilidad_capas >= 0.6:
                nivel_riesgo = "HIGH"
            elif probabilidad_capas >= 0.3:
                nivel_riesgo = "MEDIUM"
            else:
                nivel_riesgo = "LOW"
            
            return {
                "total_paginas_analizadas": self.doc.page_count,
                "total_streams": total_streams,
                "total_annots": total_annots,
                "total_ocgs": total_ocgs,
                "streams_con_cambios": streams_con_cambios,
                "annots_con_cambios": annots_con_cambios,
                "ocgs_con_cambios": ocgs_con_cambios,
                "probabilidad_overlay": round(probabilidad_capas, 3),
                "nivel_riesgo": nivel_riesgo,
                "threshold_pixels": PIX_DIFF_THRESHOLD,
                "detalles_por_pagina": resultados_paginas,
                "indicadores_clave": {
                    "overlay_detectado": total_cambios > 0,
                    "tiene_streams_cambios": streams_con_cambios > 0,
                    "tiene_annots_cambios": annots_con_cambios > 0,
                    "tiene_ocgs_cambios": ocgs_con_cambios > 0,
                    "metodo_mas_avanzado": True
                }
            }
            
        except Exception as e:
            return {"error": f"Error en análisis por capas: {str(e)}"}

    def _analyze_images(self) -> Dict[str, Any]:
        """Análisis de imágenes en el PDF para detectar parches sospechosos"""
        try:
            resultados_paginas = []
            total_imagenes = 0
            total_parches_sospechosos = 0
            total_bytes_imagenes = 0
            
            for page_num in range(self.doc.page_count):
                inventario = inventariar_imagenes(self.pdf_bytes, page_num)
                
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
                "total_paginas_analizadas": self.doc.page_count,
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


def _sha256(b: bytes) -> str:
    """Calcula SHA256 de bytes"""
    return hashlib.sha256(b).hexdigest()


def _png_from_pdf_image(img_bytes: bytes, color_space: str = None) -> Image.Image:
    """Convierte bytes de imagen del PDF a PIL Image"""
    # Pillow suele abrir bien JPEG/JPX/Flate ya decodificados por PyMuPDF.
    return Image.open(io.BytesIO(img_bytes)).convert("RGBA")


def inventariar_imagenes(pdf_bytes: bytes, page_idx: int = 0) -> Dict[str, Any]:
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
                        pil_img = _png_from_pdf_image(img_bytes)
                        
                        # Calcular hash perceptual
                        phash = str(imagehash.phash(pil_img))
                        
                        # Estadísticas de la imagen
                        img_array = np.array(pil_img)
                        mean_val = float(np.mean(img_array))
                        var_val = float(np.var(img_array))
                        
                        # Detectar si es un parche sospechoso
                        is_patch = _detectar_parche_sospechoso(pil_img, img_array)
                        
                        # Buscar bbox correspondiente
                        bbox = _buscar_bbox_correspondiente(name, block_bboxes)
                        
                        # Determinar orden de capa (aproximado)
                        layer_order = _determinar_orden_capa(name, xobjects)
                        
                        img_info = {
                            "name": str(name),
                            "xref": str(xobj.objgen),
                            "bbox": bbox,
                            "layer_order": layer_order,
                            "bytes": len(img_bytes),
                            "sha256": _sha256(img_bytes),
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


def _detectar_parche_sospechoso(pil_img: Image.Image, img_array: np.ndarray) -> bool:
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
        if _tiene_bordes_rectangulares(img_array):
            return True
            
        return False
        
    except:
        return False


def _tiene_bordes_rectangulares(img_array: np.ndarray) -> bool:
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


def _buscar_bbox_correspondiente(name: str, block_bboxes: List) -> List[float]:
    """Busca el bbox correspondiente a una imagen en los bloques de texto"""
    # Por ahora retorna bbox vacío, se puede mejorar con más lógica
    return [0, 0, 0, 0]


def _determinar_orden_capa(name: str, xobjects: dict) -> int:
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


def detectar_texto_superpuesto_detallado(pdf_base64: str) -> Dict[str, Any]:
    """
    Función principal para detectar texto superpuesto en un PDF.
    
    Args:
        pdf_base64: PDF codificado en base64
        
    Returns:
        Dict con análisis detallado de las 4 zonas de superposición
    """
    try:
        # Decodificar PDF
        pdf_bytes = base64.b64decode(pdf_base64)
        
        # Crear detector y analizar
        detector = TextOverlayDetector(pdf_bytes)
        results = detector.analyze_pdf()
        
        return safe_serialize_dict(results)
        
    except Exception as e:
        return {"error": f"Error procesando PDF: {str(e)}"}


def generar_reporte_texto_superpuesto(analysis_results: Dict[str, Any]) -> str:
    """Genera un reporte legible del análisis de texto superpuesto"""
    if "error" in analysis_results:
        return f"❌ Error en el análisis: {analysis_results['error']}"
    
    report = []
    report.append("=" * 80)
    report.append("🔍 REPORTE DE DETECCIÓN DE TEXTO SUPERPUESTO")
    report.append("=" * 80)
    
    # Resumen general
    summary = analysis_results.get("resumen_general", {})
    report.append(f"📊 Probabilidad de superposición: {summary.get('overlay_probability', 0):.1%}")
    report.append(f"⚠️  Nivel de riesgo: {summary.get('risk_level', 'UNKNOWN')}")
    report.append(f"🎯 Zonas con superposición: {summary.get('zones_with_overlay', 0)}/8")
    report.append("")
    
    # Análisis avanzado
    analisis_avanzado = analysis_results.get("analisis_avanzado_overlay", {})
    if analisis_avanzado and not analisis_avanzado.get("error"):
        report.append("🔬 ANÁLISIS AVANZADO DE OVERLAY:")
        report.append(f"   Páginas analizadas: {analisis_avanzado.get('total_paginas_analizadas', 0)}")
        report.append(f"   Anotaciones encontradas: {analisis_avanzado.get('total_anotaciones', 0)}")
        report.append(f"   Elementos sospechosos: {analisis_avanzado.get('total_elementos_sospechosos', 0)}")
        report.append(f"   Páginas con diferencia visual: {analisis_avanzado.get('paginas_con_render_diff', 0)}")
        report.append(f"   Probabilidad overlay: {analisis_avanzado.get('probabilidad_overlay', 0):.1%}")
        
        indicadores = analisis_avanzado.get("indicadores_clave", {})
        if indicadores.get("overlay_detectado"):
            report.append("   🚨 OVERLAY DETECTADO por análisis avanzado")
        report.append("")
    
    # Análisis por stream (método más preciso)
    analisis_stream = analysis_results.get("analisis_por_stream", {})
    if analisis_stream and not analisis_stream.get("error"):
        report.append("🔬 ANÁLISIS POR STREAM (MÉTODO MÁS PRECISO):")
        report.append(f"   Páginas analizadas: {analisis_stream.get('total_paginas_analizadas', 0)}")
        report.append(f"   Total streams: {analisis_stream.get('total_streams', 0)}")
        report.append(f"   Streams sospechosos: {analisis_stream.get('streams_sospechosos', 0)}")
        report.append(f"   Páginas con overlay: {analisis_stream.get('paginas_con_overlay', 0)}")
        report.append(f"   Probabilidad overlay: {analisis_stream.get('probabilidad_overlay', 0):.1%}")
        report.append(f"   Threshold píxeles: {analisis_stream.get('threshold_pixels', 0):.1%}")
        
        indicadores_stream = analisis_stream.get("indicadores_clave", {})
        if indicadores_stream.get("overlay_detectado"):
            report.append("   🚨 OVERLAY DETECTADO por análisis por stream (MÁS PRECISO)")
        
        # Mostrar detalles de streams sospechosos
        detalles_paginas = analisis_stream.get("detalles_por_pagina", [])
        for pagina in detalles_paginas:
            if pagina.get("detected", False):
                report.append(f"\n   📄 Página {pagina.get('page', 'N/A')}:")
                report.append(f"      - Streams totales: {pagina.get('streams', 0)}")
                report.append(f"      - Stream sospechoso: {pagina.get('overlay_stream', 'N/A')}")
                report.append(f"      - Ratio de diferencia: {pagina.get('overlay_ratio_formatted', 'N/A')}")
                
                # Mostrar preview del stream sospechoso
                preview = pagina.get("stream_preview", "")
                if preview:
                    report.append(f"      - Preview del stream:")
                    # Mostrar solo las primeras líneas del preview
                    lineas_preview = preview.split('\n')[:3]
                    for linea in lineas_preview:
                        report.append(f"        {linea[:80]}...")
        
        report.append("")
    
    # Análisis por capas (método más avanzado)
    analisis_capas = analysis_results.get("analisis_por_capas", {})
    if analisis_capas and not analisis_capas.get("error"):
        report.append("🔬 ANÁLISIS POR CAPAS (MÉTODO MÁS AVANZADO):")
        report.append(f"   Páginas analizadas: {analisis_capas.get('total_paginas_analizadas', 0)}")
        report.append(f"   Total streams: {analisis_capas.get('total_streams', 0)}")
        report.append(f"   Total anotaciones: {analisis_capas.get('total_annots', 0)}")
        report.append(f"   Total OCGs: {analisis_capas.get('total_ocgs', 0)}")
        report.append(f"   Streams con cambios: {analisis_capas.get('streams_con_cambios', 0)}")
        report.append(f"   Anotaciones con cambios: {analisis_capas.get('annots_con_cambios', 0)}")
        report.append(f"   OCGs con cambios: {analisis_capas.get('ocgs_con_cambios', 0)}")
        report.append(f"   Probabilidad overlay: {analisis_capas.get('probabilidad_overlay', 0):.1%}")
        report.append(f"   Threshold píxeles: {analisis_capas.get('threshold_pixels', 0):.1%}")
        
        indicadores_capas = analisis_capas.get("indicadores_clave", {})
        if indicadores_capas.get("overlay_detectado"):
            report.append("   🚨 OVERLAY DETECTADO por análisis por capas (MÁS AVANZADO)")
        
        # Mostrar detalles por página
        detalles_paginas = analisis_capas.get("detalles_por_pagina", [])
        for pagina in detalles_paginas:
            if pagina.get("by_stream") or pagina.get("by_annot") or pagina.get("by_ocg"):
                report.append(f"\n   📄 Página {pagina.get('page', 'N/A')}:")
                
                # Mostrar streams
                streams = pagina.get("by_stream", [])
                if streams:
                    report.append(f"      - Streams analizados: {len(streams)}")
                    for s in streams:
                        if s.get("changed", False):
                            report.append(f"        Stream {s.get('k', 'N/A')}: CAMBIO detectado ({s.get('diff_ratio', 0):.1%})")
                
                # Mostrar anotaciones
                annots = pagina.get("by_annot", [])
                if annots:
                    report.append(f"      - Anotaciones analizadas: {len(annots)}")
                    for a in annots:
                        if a.get("changed", False):
                            report.append(f"        Anotación {a.get('k', 'N/A')}: CAMBIO detectado ({a.get('diff_ratio', 0):.1%})")
                
                # Mostrar OCGs
                ocgs = pagina.get("by_ocg", [])
                if ocgs:
                    report.append(f"      - OCGs analizados: {len(ocgs)}")
                    for o in ocgs:
                        if o.get("changed", False):
                            report.append(f"        OCG {o.get('k', 'N/A')}: CAMBIO detectado ({o.get('diff_ratio', 0):.1%})")
        
        report.append("")
    
    # Análisis de imágenes
    analisis_imagenes = analysis_results.get("analisis_imagenes", {})
    if analisis_imagenes and not analisis_imagenes.get("error"):
        report.append("🖼️  ANÁLISIS DE IMÁGENES:")
        report.append(f"   Páginas analizadas: {analisis_imagenes.get('total_paginas_analizadas', 0)}")
        report.append(f"   Total imágenes: {analisis_imagenes.get('total_imagenes', 0)}")
        report.append(f"   Parches sospechosos: {analisis_imagenes.get('total_parches_sospechosos', 0)}")
        report.append(f"   Bytes totales imágenes: {analisis_imagenes.get('total_bytes_imagenes', 0):,}")
        report.append(f"   Probabilidad overlay: {analisis_imagenes.get('probabilidad_overlay_imagenes', 0):.1%}")
        
        indicadores_imagenes = analisis_imagenes.get("indicadores_clave", {})
        if indicadores_imagenes.get("tiene_parches_sospechosos"):
            report.append("   🚨 PARCHES SOSPECHOSOS DETECTADOS")
        if indicadores_imagenes.get("imagenes_pequenas_detectadas"):
            report.append("   ⚠️  Imágenes muy pequeñas detectadas")
        if indicadores_imagenes.get("imagenes_uniformes_detectadas"):
            report.append("   ⚠️  Imágenes uniformes detectadas")
        
        # Mostrar detalles por página
        detalles_paginas = analisis_imagenes.get("detalles_por_pagina", [])
        for pagina in detalles_paginas:
            if pagina.get("imagenes"):
                report.append(f"\n   📄 Página {pagina.get('pagina', 'N/A')}:")
                report.append(f"      - Imágenes: {pagina.get('total_imagenes', 0)}")
                report.append(f"      - Parches sospechosos: {pagina.get('parches_sospechosos', 0)}")
                report.append(f"      - Bytes: {pagina.get('bytes_imagenes', 0):,}")
                
                # Mostrar imágenes sospechosas
                imagenes = pagina.get("imagenes", [])
                parches = [img for img in imagenes if img.get("is_patch", False)]
                if parches:
                    report.append(f"      - Parches sospechosos encontrados:")
                    for parche in parches:
                        report.append(f"        • {parche.get('name', 'N/A')}: {parche.get('width', 0)}x{parche.get('height', 0)}px, var={parche.get('var', 0):.1f}")
        
        report.append("")
    
    # Zona 1: Anotaciones
    zona1 = analysis_results.get("zona_1_anotaciones", {})
    if zona1.get("has_annotations"):
        report.append("🔴 ZONA 1 - ANOTACIONES:")
        report.append(f"   Total anotaciones: {zona1.get('total_annotations', 0)}")
        report.append(f"   Anotaciones superpuestas: {zona1.get('overlapping_count', 0)}")
        report.append(f"   Tipos encontrados: {', '.join(zona1.get('annotation_types', {}).keys())}")
        report.append("")
    
    # Zona 2: Contenido de página
    zona2 = analysis_results.get("zona_2_contenido_pagina", {})
    if zona2.get("has_multiple_streams"):
        report.append("🟡 ZONA 2 - CONTENIDO DE PÁGINA:")
        report.append(f"   Streams de contenido: {zona2.get('stream_count', 0)}")
        report.append(f"   Comandos de texto: {len(zona2.get('text_commands', []))}")
        report.append(f"   Comandos de rectángulo: {len(zona2.get('rectangle_commands', []))}")
        report.append(f"   Secuencias sospechosas: {len(zona2.get('suspicious_sequences', []))}")
        report.append("")
    
    # Zona 3: Form XObjects
    zona3 = analysis_results.get("zona_3_form_xobject", {})
    if zona3.get("has_form_xobjects"):
        report.append("🟠 ZONA 3 - FORM XOBJECTS:")
        report.append(f"   XObjects encontrados: {zona3.get('xobject_count', 0)}")
        report.append(f"   XObjects de texto: {len(zona3.get('text_xobjects', []))}")
        report.append(f"   XObjects sospechosos: {len(zona3.get('suspicious_xobjects', []))}")
        report.append("")
    
    # Zona 4: AcroForm
    zona4 = analysis_results.get("zona_4_acroform", {})
    if zona4.get("has_acroform"):
        report.append("🟢 ZONA 4 - ACROFORM:")
        report.append(f"   Campos de formulario: {len(zona4.get('form_fields', []))}")
        report.append(f"   Campos de texto: {len(zona4.get('text_fields', []))}")
        report.append(f"   Campos superpuestos: {len(zona4.get('overlapping_fields', []))}")
        report.append("")
    
    # Estructura del PDF
    structure = analysis_results.get("xml_estructura", {})
    if structure:
        report.append("📄 ESTRUCTURA DEL PDF:")
        report.append(f"   Páginas: {structure.get('page_count', 0)}")
        report.append(f"   Versión PDF: {structure.get('pdf_version', 'N/A')}")
        if structure.get('metadata'):
            metadata = structure['metadata']
            report.append(f"   Creador: {metadata.get('creator', 'N/A')}")
            report.append(f"   Productor: {metadata.get('producer', 'N/A')}")
        report.append("")
    
    # Recomendaciones
    if summary.get("recommendations"):
        report.append("💡 RECOMENDACIONES:")
        for rec in summary["recommendations"]:
            report.append(f"   • {rec}")
        report.append("")
    
    report.append("=" * 80)
    
    return "\n".join(report)
