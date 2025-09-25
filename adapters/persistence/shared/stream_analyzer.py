"""
Helper para análisis de streams de contenido en PDFs.

Maneja la detección de overlay analizando streams de contenido uno por uno.
"""

import io
import pikepdf
from typing import Dict, Any
from .image_renderer import render_png, diff_ratio

# Constantes para análisis por stream
PA = 0.05  # umbral de % de píxeles distintos para decir "hay cambio"


def get_page_streams(pdf: pikepdf.Pdf, page_index: int):
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


def set_page_stream_prefix(pdf_bytes: bytes, page_index: int, k: int) -> bytes:
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
        base_img = render_png(pdf_bytes, page_index)

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

                img = render_png(test_bytes, page_index)
                ratio = diff_ratio(img, base_img)
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
