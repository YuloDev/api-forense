"""
Helper para análisis de capas en PDFs.

Maneja la detección de overlay usando análisis por capas (streams, anotaciones, OCGs).
"""

import io
import pikepdf
from typing import Dict, Any
from .image_renderer import render_png, diff_ratio
from .stream_analyzer import get_page_streams, set_page_stream_prefix

# Constantes para análisis por capas
PIX_DIFF_THRESHOLD = 0.05  # 5% de píxeles distintos => consideramos que "cambió"


def get_annots(pdf: pikepdf.Pdf, page_index: int):
    """Obtiene las anotaciones de una página"""
    page = pdf.pages[page_index]
    arr = page.obj.get("/Annots", None)
    if arr is None:
        return []
    return list(arr)


def set_annots_prefix(pdf_bytes: bytes, page_index: int, k: int) -> bytes:
    """Deja solo las primeras k anotaciones en /Annots."""
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_index]
        ann = page.obj.get("/Annots", None)
        if ann is not None:
            page.obj["/Annots"] = pikepdf.Array(list(ann)[:k])
        bio = io.BytesIO()
        pdf.save(bio)
        return bio.getvalue()


def get_ocgs(pdf: pikepdf.Pdf):
    """Obtiene los Optional Content Groups del PDF"""
    ocp = pdf.Root.get("/OCProperties", None)
    if not ocp:
        return []
    ocgs = ocp.get("/OCGs", None)
    return list(ocgs) if ocgs else []


def set_ocg_on_prefix(pdf_bytes: bytes, k: int) -> bytes:
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
        baseline = render_png(pdf_bytes, page_index, dpi)
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
            streams = get_page_streams(pdf, page_index)
        
        prev_img = None
        for k in range(1, len(streams) + 1):
            bytes_k = set_page_stream_prefix(pdf_bytes, page_index, k)
            img_k = render_png(bytes_k, page_index, dpi)
            # compara contra k-1 (o baseline si k==1)
            base = baseline if k == 1 else prev_img
            ratio = diff_ratio(img_k, base)
            report["by_stream"].append({
                "k": k,
                "changed": ratio > PIX_DIFF_THRESHOLD,
                "diff_ratio": ratio
            })
            prev_img = img_k

        # --- 2) Capas: /Annots (encima del contenido) ---
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            annots = get_annots(pdf, page_index)
        
        if annots:
            prev_bytes = set_annots_prefix(pdf_bytes, page_index, 0)  # sin annots
            prev_img = render_png(prev_bytes, page_index, dpi)
            for k in range(1, len(annots) + 1):
                bytes_k = set_annots_prefix(pdf_bytes, page_index, k)
                img_k = render_png(bytes_k, page_index, dpi)
                ratio = diff_ratio(img_k, prev_img)
                report["by_annot"].append({
                    "k": k,
                    "changed": ratio > PIX_DIFF_THRESHOLD,
                    "diff_ratio": ratio
                })
                prev_img = img_k

        # --- 3) Capas: OCG (si hay) ---
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            ocgs = get_ocgs(pdf)
        
        if ocgs:
            prev_bytes = set_ocg_on_prefix(pdf_bytes, 0)
            prev_img = render_png(prev_bytes, page_index, dpi)
            for k in range(1, len(ocgs) + 1):
                bytes_k = set_ocg_on_prefix(pdf_bytes, k)
                img_k = render_png(bytes_k, page_index, dpi)
                ratio = diff_ratio(img_k, prev_img)
                report["by_ocg"].append({
                    "k": k,
                    "changed": ratio > PIX_DIFF_THRESHOLD,
                    "diff_ratio": ratio
                })
                prev_img = img_k

        return report
        
    except Exception as e:
        return {"error": f"Error en análisis por capas: {str(e)}"}
