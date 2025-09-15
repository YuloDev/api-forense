import re
import statistics
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter
from difflib import SequenceMatcher

import fitz  # PyMuPDF

from config import (
    TEXT_MIN_LEN_FOR_DOC,
    ONEPAGE_MIN_BYTES,
    ONEPAGE_MAX_BYTES_TEXTUAL,
    ONEPAGE_MAX_BYTES_ESCANEADO,
    RISK_WEIGHTS,
    RISK_LEVELS,
    STD_IMAGE_FILTERS,
)
from utils import _to_float


# ---------------------- helpers internos de PDF ----------------------

def _pdf_date_to_dt(s: Optional[str]) -> Optional[datetime]:
    """Convierte fechas PDF tipo D:YYYYMMDDHHmmSSOHH'mm' a datetime."""
    if not s:
        return None
    s = s.strip()
    if s.startswith("D:"):
        s = s[2:]
    pat = re.compile(r"^(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?")
    m = pat.match(s)
    if not m:
        return None
    y = int(m.group(1))
    mo = int(m.group(2) or "1")
    d = int(m.group(3) or "1")
    hh = int(m.group(4) or "0")
    mi = int(m.group(5) or "0")
    ss = int(m.group(6) or "0")
    try:
        return datetime(y, mo, d, hh, mi, ss)
    except ValueError:
        try:
            return datetime(y, min(mo, 12), min(d, 28), hh, mi, ss)
        except Exception:
            return None


def _parse_fecha_emision(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    s = s.strip().replace("-", "/")
    try:
        d, m, y = s.split("/")
        if len(y) == 2:
            y = "20" + y
        return date(int(y), int(m), int(d))
    except Exception:
        return None


# ==================== DETECCIÓN AVANZADA DE CAPAS ====================

def _detect_layers_advanced(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Detección avanzada de capas múltiples con múltiples heurísticas.
    Retorna un diccionario con el análisis detallado.
    """
    result = {
        "has_layers": False,
        "confidence": 0.0,
        "indicators": [],
        "layer_count_estimate": 0,
        "ocg_objects": 0,
        "suspicious_patterns": []
    }
    
    sample_size = min(6_000_000, len(pdf_bytes))
    sample = pdf_bytes[:sample_size]
    
    # 1. Detección básica de OCG (Optional Content Groups)
    ocg_patterns = [
        rb"/OCGs",
        rb"/OCProperties", 
        rb"/OC\s",
        rb"/ON\s+\[",
        rb"/OFF\s+\[",
        rb"/Order\s+\[",
        rb"/RBGroups",
        rb"/Locked\s+\["
    ]
    
    ocg_count = 0
    for pattern in ocg_patterns:
        matches = len(re.findall(pattern, sample))
        if matches > 0:
            ocg_count += matches
            result["indicators"].append(f"Patrón OCG encontrado: {pattern.decode('utf-8', errors='ignore')} ({matches} veces)")
    
    result["ocg_objects"] = ocg_count
    
    # 2. Detección de objetos superpuestos
    overlay_patterns = [
        rb"/Type\s*/XObject",
        rb"/Subtype\s*/Form",
        rb"/Group\s*<<",
        rb"/S\s*/Transparency"
    ]
    
    overlay_count = 0
    for pattern in overlay_patterns:
        matches = len(re.findall(pattern, sample))
        overlay_count += matches
    
    if overlay_count > 3:  # Umbral para objetos superpuestos
        result["indicators"].append(f"Objetos superpuestos detectados: {overlay_count}")
    
    # 3. Análisis de múltiples streams de contenido
    content_streams = len(re.findall(rb"stream\s", sample))
    if content_streams > 5:  # Para un PDF de 1 página, muchos streams pueden ser sospechosos
        result["indicators"].append(f"Múltiples content streams: {content_streams}")
    
    # 4. Detección de transformaciones de matriz sospechosas
    matrix_patterns = [
        rb"q\s+[\d\.\-\s]+cm",  # transformaciones de matriz
        rb"\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+cm"
    ]
    
    matrix_count = 0
    for pattern in matrix_patterns:
        matches = len(re.findall(pattern, sample))
        matrix_count += matches
    
    if matrix_count > 10:  # Muchas transformaciones pueden indicar capas
        result["indicators"].append(f"Transformaciones de matriz excesivas: {matrix_count}")
    
    # 5. Estimación de confianza
    confidence = 0.0
    if ocg_count > 0:
        confidence += 0.8  # OCG es el indicador más fuerte
    if overlay_count > 3:
        confidence += 0.4
    if content_streams > 5:
        confidence += 0.2
    if matrix_count > 10:
        confidence += 0.3
    
    confidence = min(1.0, confidence)
    result["confidence"] = round(confidence, 3)
    result["has_layers"] = confidence >= 0.5
    
    # 6. Estimación del número de capas
    if ocg_count > 0:
        result["layer_count_estimate"] = min(ocg_count // 2, 10)  # Estimación conservadora
    
    return result


def _detect_text_overlapping(extracted_text: str) -> Dict[str, Any]:
    """
    Analiza el texto extraído para detectar superposiciones y duplicaciones
    que pueden indicar capas múltiples.
    """
    if not extracted_text:
        return {"has_overlapping": False, "patterns": []}
    
    lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
    
    result = {
        "has_overlapping": False,
        "patterns": [],
        "duplicate_lines": {},
        "similar_lines": [],
        "suspicious_formatting": []
    }
    
    # 1. Detectar líneas duplicadas exactas
    line_counts = Counter(lines)
    duplicates = {line: count for line, count in line_counts.items() if count > 1}
    
    if duplicates:
        result["duplicate_lines"] = duplicates
        result["patterns"].append(f"Líneas duplicadas encontradas: {len(duplicates)}")
        result["has_overlapping"] = True
    
    # 2. Detectar líneas muy similares (posibles superposiciones)
    similar_pairs = []
    for i, line1 in enumerate(lines):
        for j, line2 in enumerate(lines[i+1:], i+1):
            similarity = SequenceMatcher(None, line1, line2).ratio()
            if 0.7 <= similarity < 1.0:  # Muy similar pero no idéntica
                similar_pairs.append((line1, line2, similarity))
    
    if similar_pairs:
        result["similar_lines"] = similar_pairs[:10]  # Limitar a 10 ejemplos
        result["patterns"].append(f"Líneas similares encontradas: {len(similar_pairs)}")
        result["has_overlapping"] = True
    
    # 3. Detectar patrones de formato sospechosos
    suspicious_patterns = []
    
    for line in lines:
        # Texto con palabras pegadas sin espacios apropiados
        if re.search(r'[A-ZÁÉÍÓÚ]+[a-záéíóú]+[A-ZÁÉÍÓÚ]+', line):
            suspicious_patterns.append(f"Formato sospechoso: {line}")
        
        # Mezcla extraña de mayúsculas y minúsculas
        words = line.split()
        for word in words:
            if re.match(r'^[A-Z]+[a-z]+[A-Z]+', word) and len(word) > 6:
                suspicious_patterns.append(f"Patrón de caso sospechoso: {word}")
    
    if suspicious_patterns:
        result["suspicious_formatting"] = suspicious_patterns[:5]  # Limitar ejemplos
        result["patterns"].append(f"Formatos sospechosos: {len(suspicious_patterns)}")
        result["has_overlapping"] = True
    
    return result


def _analyze_pdf_structure_layers(doc: fitz.Document) -> Dict[str, Any]:
    """
    Analiza la estructura interna del PDF para detectar indicios de capas múltiples.
    """
    result = {
        "suspicious_structure": False,
        "details": [],
        "object_analysis": {},
        "content_analysis": {}
    }
    
    try:
        total_objects = 0
        form_objects = 0
        transparency_objects = 0
        
        # Analizar cada página
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            # Obtener objetos de la página
            try:
                drawings = page.get_drawings()
                images = page.get_images()
                text_dict = page.get_text("dict")
                
                # Contar objetos por página
                page_objects = len(drawings) + len(images) + len(text_dict.get('blocks', []))
                total_objects += page_objects
                
                # Analizar bloques de texto para detectar superposiciones
                blocks = text_dict.get('blocks', [])
                overlapping_blocks = 0
                
                for i, block1 in enumerate(blocks):
                    if block1.get('type') != 0:  # Solo bloques de texto
                        continue
                    bbox1 = block1.get('bbox')
                    if not bbox1:
                        continue
                    
                    for j, block2 in enumerate(blocks[i+1:], i+1):
                        if block2.get('type') != 0:
                            continue
                        bbox2 = block2.get('bbox')
                        if not bbox2:
                            continue
                        
                        # Verificar si los bounding boxes se superponen
                        if (bbox1[0] < bbox2[2] and bbox1[2] > bbox2[0] and 
                            bbox1[1] < bbox2[3] and bbox1[3] > bbox2[1]):
                            overlapping_blocks += 1
                
                if overlapping_blocks > 2:  # Umbral para superposiciones sospechosas
                    result["details"].append(f"Página {page_num + 1}: {overlapping_blocks} bloques superpuestos")
                    result["suspicious_structure"] = True
                
            except Exception as e:
                result["details"].append(f"Error analizando página {page_num + 1}: {str(e)}")
        
        # Análisis global
        result["object_analysis"] = {
            "total_objects": total_objects,
            "objects_per_page": total_objects / max(1, doc.page_count),
            "form_objects": form_objects,
            "transparency_objects": transparency_objects
        }
        
        # Si hay demasiados objetos por página, puede ser sospechoso
        if total_objects / max(1, doc.page_count) > 50:
            result["details"].append(f"Exceso de objetos por página: {total_objects / doc.page_count:.1f}")
            result["suspicious_structure"] = True
            
    except Exception as e:
        result["details"].append(f"Error en análisis estructural: {str(e)}")
    
    return result


def _detect_layers(pdf_bytes: bytes) -> bool:
    """Función simplificada que mantiene la compatibilidad con el código existente."""
    advanced_result = _detect_layers_advanced(pdf_bytes)
    return advanced_result["has_layers"]


# ================= FUNCIONES AUXILIARES EXISTENTES =================

def _count_incremental_updates(pdf_bytes: bytes) -> int:
    """Número de 'startxref' → 1 = normal, >1 = actualizaciones incrementales."""
    return pdf_bytes.count(b"startxref")


def _has_js_embedded(pdf_bytes: bytes) -> bool:
    sample = pdf_bytes[: min(4_000_000, len(pdf_bytes))]
    return (b"/JavaScript" in sample) or (b"/JS" in sample)


def _has_embedded_files(pdf_bytes: bytes) -> bool:
    sample = pdf_bytes[: min(6_000_000, len(pdf_bytes))]
    return (b"/EmbeddedFiles" in sample) or (b"/FileAttachment" in sample)


def _has_forms_or_annots(pdf_bytes: bytes) -> bool:
    sample = pdf_bytes[: min(6_000_000, len(pdf_bytes))]
    return (b"/AcroForm" in sample) or (b"/Annots" in sample)


def _has_sig(pdf_bytes: bytes) -> bool:
    sample = pdf_bytes[: min(6_000_000, len(pdf_bytes))]
    return (b"/Sig" in sample) or (b"/DigitalSignature" in sample)


def _collect_fonts_and_alignment(page: fitz.Page) -> Tuple[List[str], Dict[str, Any]]:
    """Devuelve lista de fuentes vistas y un dict con métricas de alineación."""
    data = page.get_text("rawdict")
    fonts = []
    left_margins = []
    dirs = []
    try:
        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                if not line.get("spans"):
                    continue
                first_span = line["spans"][0]
                fm = first_span.get("font")
                if fm:
                    fonts.append(fm)
                ox, oy = first_span.get("origin", [None, None])
                if ox is not None:
                    left_margins.append(round(ox, 1))
                d = line.get("dir")
                if isinstance(d, list) and len(d) == 2:
                    dirs.append(tuple(d))
    except Exception:
        pass

    # alineación: porcentaje de líneas cuyo margen-izq cae en los 2 modos principales
    align_score = 1.0
    if left_margins:
        counts: Dict[float, int] = {}
        for v in left_margins:
            counts[v] = counts.get(v, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:2]
        top_total = sum(c for _, c in top)
        align_score = top_total / max(1, len(left_margins))

    # direcciones de texto
    non_horizontal = 0
    for d in dirs:
        if abs(d[0] - 1.0) > 0.05 or abs(d[1]) > 0.05:
            non_horizontal += 1
    rot_ratio = non_horizontal / max(1, len(dirs)) if dirs else 0.0

    return fonts, {
        "alineacion_score": round(align_score, 3),  # 1.0=alineado, <0.7=disperso
        "rotacion_ratio": round(rot_ratio, 3),      # >0.2 = muchas rotaciones
        "num_lineas": len(left_margins)
    }


def _collect_images_info(doc: fitz.Document) -> Dict[str, Any]:
    """Extrae DPI, filtros de compresión y tamaño de imágenes colocadas."""
    dpis: List[float] = []
    filters: List[str] = []
    try:
        for pno in range(doc.page_count):
            page = doc.load_page(pno)
            raw = page.get_text("rawdict")
            bbox_by_xref = {}
            for b in raw.get("blocks", []):
                if b.get("type") == 1 and "image" in b:
                    info = b["image"]
                    xref = info.get("xref")
                    bbox = b.get("bbox")
                    if xref and bbox:
                        bbox_by_xref[xref] = bbox

            for img in page.get_images(full=True):
                xref = img[0]
                w_px, h_px = img[2], img[3]
                filt = img[-1] if isinstance(img[-1], str) else None
                if filt:
                    filters.append(filt)
                bbox = bbox_by_xref.get(xref)
                if bbox:
                    width_pt = max(1e-6, bbox[2] - bbox[0])
                    height_pt = max(1e-6, bbox[3] - bbox[1])
                    dpi_x = (w_px * 72.0) / width_pt
                    dpi_y = (h_px * 72.0) / height_pt
                    dpi = (dpi_x + dpi_y) / 2.0
                    dpis.append(dpi)
    except Exception:
        pass

    res: Dict[str, Any] = {
        "dpis": [round(x, 1) for x in dpis],
        "filters": filters
    }
    if dpis:
        res["dpi_min"] = round(min(dpis), 1)
        res["dpi_max"] = round(max(dpis), 1)
        res["dpi_mean"] = round(statistics.mean(dpis), 1)
        if len(dpis) > 1:
            try:
                res["dpi_stdev"] = round(statistics.pstdev(dpis), 1)
            except Exception:
                pass
    return res


def _is_known_producer(meta: Dict[str, Any]) -> bool:
    prod = ((meta.get("producer") or meta.get("Producer") or "") + " " +
            (meta.get("creator") or meta.get("Creator") or "")).lower()
    # Cadena simple; la lista de productores conocidos vive en tu módulo de configuración original.
    # Aquí sólo comprobamos que exista algo (si no, penalizamos).
    return bool(prod.strip())


def _fonts_consistency(fonts_all_pages: List[str]) -> Dict[str, Any]:
    total = len(fonts_all_pages)
    uniq: Dict[str, int] = {}
    for f in fonts_all_pages:
        uniq[f] = uniq.get(f, 0) + 1
    uniq_count = len(uniq)
    dom_ratio = 0.0
    if total > 0:
        dom_ratio = max(uniq.values()) / total
    return {
        "num_fuentes_unicas": uniq_count,
        "total_spans": total,
        "dominante_ratio": round(dom_ratio, 3)
    }


def _file_size_expectation(size_bytes: int, pages: int, scanned: bool) -> Dict[str, Any]:
    if pages <= 0:
        return {"ok": True, "detalle": "sin páginas?"}
    per_page = size_bytes / pages
    if pages == 1:
        max_ok = ONEPAGE_MAX_BYTES_ESCANEADO if scanned else ONEPAGE_MAX_BYTES_TEXTUAL
        ok = (per_page >= ONEPAGE_MIN_BYTES) and (per_page <= max_ok)
    else:
        max_ok = (ONEPAGE_MAX_BYTES_ESCANEADO if scanned else ONEPAGE_MAX_BYTES_TEXTUAL) * 1.5
        ok = (per_page >= ONEPAGE_MIN_BYTES * 0.6) and (per_page <= max_ok)
    return {
        "ok": bool(ok),
        "bytes_total": size_bytes,
        "bytes_por_pagina": int(per_page),
        "limite_max": int(max_ok),
        "tipo": "escaneado" if scanned else "textual"
    }


def _is_scanned_image_pdf(pdf_bytes: bytes, extracted_text: str) -> bool:
    """
    Heurística básica: poco texto + presencia de objetos /Image.
    Dado que validar.py también necesita esto, allí incluimos una copia local
    para evitar dependencias cruzadas.
    """
    text_len = len((extracted_text or "").strip())
    little_text = text_len < TEXT_MIN_LEN_FOR_DOC
    try:
        sample = pdf_bytes[: min(len(pdf_bytes), 2_000_000)]
        img_hits = len(re.findall(rb"/Subtype\s*/Image", sample)) or len(re.findall(rb"/Image\b", sample))
        has_image_objs = img_hits > 0
    except Exception:
        has_image_objs = False
    return little_text and has_image_objs


# --------------------- evaluación principal de riesgo ---------------------

def evaluar_riesgo(pdf_bytes: bytes, fuente_texto: str, pdf_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula score y desglose de validaciones para el PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    meta = doc.metadata or {}
    pages = doc.page_count
    size_bytes = len(pdf_bytes)
    scanned = _is_scanned_image_pdf(pdf_bytes, fuente_texto or "")

    # --- ANÁLISIS AVANZADO DE CAPAS ---
    layers_analysis = _detect_layers_advanced(pdf_bytes)
    text_overlapping = _detect_text_overlapping(fuente_texto or "")
    structure_analysis = _analyze_pdf_structure_layers(doc)

    # --- fechas ---
    fecha_emision = _parse_fecha_emision(pdf_fields.get("fechaEmision"))
    dt_cre = _pdf_date_to_dt(meta.get("creationDate") or meta.get("CreationDate"))
    dt_mod = _pdf_date_to_dt(meta.get("modDate") or meta.get("ModDate"))

    # --- software ---
    prod_ok = _is_known_producer(meta)

    # --- capas (usando la detección mejorada) ---
    has_layers = layers_analysis["has_layers"]

    # --- fuentes y alineación ---
    all_fonts: List[str] = []
    align_metrics: List[Dict[str, Any]] = []
    for pno in range(pages):
        page = doc.load_page(pno)
        fonts, als = _collect_fonts_and_alignment(page)
        all_fonts += fonts
        align_metrics.append(als)
    fonts_info = _fonts_consistency(all_fonts)

    # --- imágenes ---
    img_info = _collect_images_info(doc)

    # --- compresión ---
    filters_set = set(img_info.get("filters") or [])
    comp_ok = True
    unknown_filters: List[str] = []
    for f in filters_set:
        for tok in re.split(r"[,\s]+", f):
            if tok and tok not in STD_IMAGE_FILTERS:
                unknown_filters.append(tok)
    if unknown_filters:
        comp_ok = False

    # --- alineación global ---
    align_score_vals = [m.get("alineacion_score", 1.0) for m in align_metrics if m]
    rot_ratio_vals = [m.get("rotacion_ratio", 0.0) for m in align_metrics if m]
    align_score_mean = statistics.mean(align_score_vals) if align_score_vals else 1.0
    rot_ratio_mean = statistics.mean(rot_ratio_vals) if rot_ratio_vals else 0.0

    # --- tamaño esperado ---
    size_expect = _file_size_expectation(size_bytes, pages, scanned)

    # --- otros marcadores ---
    has_js = _has_js_embedded(pdf_bytes)
    has_emb = _has_embedded_files(pdf_bytes)
    has_forms = _has_forms_or_annots(pdf_bytes)
    has_sig = _has_sig(pdf_bytes)
    incr_updates = _count_incremental_updates(pdf_bytes)
    try:
        is_encrypted = doc.is_encrypted
    except Exception:
        is_encrypted = False

    # ===================== SCORING MEJORADO =====================
    score = 0
    details_prior: List[Dict[str, Any]] = []
    details_sec: List[Dict[str, Any]] = []
    details_extra: List[Dict[str, Any]] = []

    # PRIORITARIAS
    # 1) Fecha creación vs fecha emisión
    penal = 0
    msg = "sin datos suficientes"
    if fecha_emision and dt_cre:
        dias = abs((dt_cre.date() - fecha_emision).days)
        msg = f"{dias} día(s) entre creación PDF y emisión"
        if dias <= 30:
            penal = 0
        elif dias <= 60:
            penal = int(RISK_WEIGHTS["fecha_creacion_vs_emision"] * 0.5)
        else:
            penal = RISK_WEIGHTS["fecha_creacion_vs_emision"]
    details_prior.append({"check": "Fecha de creación vs fecha de emisión", "detalle": msg, "penalizacion": penal})
    score += penal

    # 2) Fecha modificación vs creación
    penal = 0
    msg = "sin datos suficientes"
    if dt_mod and dt_cre:
        diff = (dt_mod - dt_cre).days
        msg = f"{diff} día(s) entre modificación y creación"
        if diff < 0:
            penal = RISK_WEIGHTS["fecha_mod_vs_creacion"]  # mod < cre → sospechoso
        elif diff <= 10:
            penal = 0
        else:
            penal = int(RISK_WEIGHTS["fecha_mod_vs_creacion"] * 0.7)
    details_prior.append({"check": "Fecha de modificación vs fecha de creación", "detalle": msg, "penalizacion": penal})
    score += penal

    # 3) Software conocido
    penal = 0 if prod_ok else RISK_WEIGHTS["software_conocido"]
    details_prior.append({"check": "Software de creación/producción conocido", "detalle": meta, "penalizacion": penal})
    score += penal

    # 4) Número de páginas esperado = 1
    penal = 0 if pages == 1 else RISK_WEIGHTS["num_paginas"]
    details_prior.append({"check": "Número de páginas esperado = 1", "detalle": f"{pages} pág(s)", "penalizacion": penal})
    score += penal

    # 5) Presencia de capas múltiples (MEJORADO)
    penal = 0
    layer_details = {
        "deteccion_basica": has_layers,
        "confianza": layers_analysis["confidence"],
        "indicadores": layers_analysis["indicators"],
        "objetos_ocg": layers_analysis["ocg_objects"],
        "superposicion_texto": text_overlapping["has_overlapping"],
        "estructura_sospechosa": structure_analysis["suspicious_structure"]
    }
    
    if has_layers:
        # Penalización base por capas
        penal = RISK_WEIGHTS["capas_multiples"]
        
        # Penalización adicional por alta confianza
        if layers_analysis["confidence"] >= 0.8:
            penal = int(penal * 1.3)
        
        # Penalización adicional por superposición de texto
        if text_overlapping["has_overlapping"]:
            penal = int(penal * 1.2)
        
        # Penalización adicional por estructura sospechosa
        if structure_analysis["suspicious_structure"]:
            penal = int(penal * 1.1)
    
    details_prior.append({
        "check": "Presencia de capas múltiples (análisis avanzado)", 
        "detalle": layer_details, 
        "penalizacion": penal
    })
    score += penal

    # SECUNDARIAS (continúan igual)
    # Consistencia de fuentes
    penal = 0
    f_det = fonts_info
    if f_det["num_fuentes_unicas"] > 12 or f_det["dominante_ratio"] < 0.4:
        penal = RISK_WEIGHTS["consistencia_fuentes"]
    elif f_det["num_fuentes_unicas"] > 6 or f_det["dominante_ratio"] < 0.6:
        penal = int(RISK_WEIGHTS["consistencia_fuentes"] * 0.6)
    details_sec.append({"check": "Consistencia de fuentes", "detalle": f_det, "penalizacion": penal})
    score += penal

    # Resolución/DPI uniforme
    penal = 0
    dpi_min = img_info.get("dpi_min", None)
    dpi_stdev = img_info.get("dpi_stdev", 0.0)
    if dpi_min is not None:
        if dpi_min < 90:
            penal = RISK_WEIGHTS["dpi_uniforme"]
        elif dpi_stdev and img_info.get("dpi_mean", 0) and (dpi_stdev / max(1e-6, img_info.get("dpi_mean"))) > 0.35:
            penal = int(RISK_WEIGHTS["dpi_uniforme"] * 0.6)
    details_sec.append({"check": "Resolución/DPI uniforme", "detalle": img_info, "penalizacion": penal})
    score += penal

    # Métodos de compresión estándar
    penal = 0 if comp_ok else RISK_WEIGHTS["compresion_estandar"]
    details_sec.append({"check": "Métodos de compresión estándar", "detalle": list(filters_set), "penalizacion": penal})
    score += penal

    # Alineación de elementos de texto
    penal = 0
    if align_score_mean < 0.7 or rot_ratio_mean > 0.2:
        penal = RISK_WEIGHTS["alineacion_texto"]
    elif align_score_mean < 0.85 or rot_ratio_mean > 0.1:
        penal = int(RISK_WEIGHTS["alineacion_texto"] * 0.6)
    details_sec.append({
        "check": "Alineación de elementos de texto",
        "detalle": {"alineacion_promedio": align_score_mean, "rotacion_promedio": rot_ratio_mean},
        "penalizacion": penal
    })
    score += penal

    # Tamaño de archivo esperado
    penal = 0 if size_expect.get("ok") else RISK_WEIGHTS["tamano_esperado"]
    details_sec.append({"check": "Tamaño de archivo esperado", "detalle": size_expect, "penalizacion": penal})
    score += penal

    # ADICIONALES
    # Anotaciones / Formularios
    penal = RISK_WEIGHTS["anotaciones_o_formularios"] if has_forms else 0
    details_extra.append({"check": "Anotaciones o Formularios", "detalle": has_forms, "penalizacion": penal})
    score += penal

    # JavaScript embebido
    penal = RISK_WEIGHTS["javascript_embebido"] if has_js else 0
    details_extra.append({"check": "JavaScript embebido", "detalle": has_js, "penalizacion": penal})
    score += penal

    # Archivos incrustados
    penal = RISK_WEIGHTS["archivos_incrustados"] if has_emb else 0
    details_extra.append({"check": "Archivos incrustados", "detalle": has_emb, "penalizacion": penal})
    score += penal

    # Firmas (reduce riesgo si existe)
    penal = RISK_WEIGHTS["firmas_pdf"] if has_sig else 0
    details_extra.append({"check": "Firma(s) digital(es) PDF", "detalle": has_sig, "penalizacion": penal})
    score += penal

    # Actualizaciones incrementales (>1 startxref)
    penal = 0
    if incr_updates > 1:
        penal = RISK_WEIGHTS["actualizaciones_incrementales"] if incr_updates >= 3 else int(RISK_WEIGHTS["actualizaciones_incrementales"] * 0.6)
    details_extra.append({"check": "Actualizaciones incrementales", "detalle": incr_updates, "penalizacion": penal})
    score += penal

    # Cifrado / permisos estrictos
    penal = RISK_WEIGHTS["cifrado_permisos_extra"] if is_encrypted else 0
    details_extra.append({"check": "Cifrado / Permisos", "detalle": {"encriptado": is_encrypted}, "penalizacion": penal})
    score += penal

    # NUEVAS VALIDACIONES ESPECÍFICAS PARA CAPAS
    # Superposición de texto detectada
    if text_overlapping["has_overlapping"] and not has_layers:
        # Si hay superposición de texto pero no se detectaron capas OCG, es sospechoso
        penal = int(RISK_WEIGHTS.get("capas_multiples", 15) * 0.5)
        details_extra.append({
            "check": "Superposición de texto sin capas OCG", 
            "detalle": text_overlapping["patterns"], 
            "penalizacion": penal
        })
        score += penal

    # Estructura sospechosa sin otras indicaciones
    if structure_analysis["suspicious_structure"] and not has_layers and not text_overlapping["has_overlapping"]:
        penal = int(RISK_WEIGHTS.get("capas_multiples", 15) * 0.3)
        details_extra.append({
            "check": "Estructura PDF sospechosa", 
            "detalle": structure_analysis["details"], 
            "penalizacion": penal
        })
        score += penal

    # Normalizar score a [0, 100]
    score = max(0, min(100, score))

    # Determinar si es falso (indicadores fuertes)
    es_falso = False
    if has_layers and layers_analysis["confidence"] >= 0.7:
        es_falso = True
    if dt_cre and dt_mod and dt_cre != dt_mod and abs((dt_mod - dt_cre).days) > 1:
        es_falso = True
    if text_overlapping["has_overlapping"] and len(text_overlapping.get("duplicate_lines", {})) > 2:
        es_falso = True

    # Determinar nivel de riesgo
    nivel = "bajo"
    for k, (lo, hi) in RISK_LEVELS.items():
        if lo <= score <= hi:
            nivel = k
            break

    return {
        "score": score,
        "nivel": nivel,
        "es_falso_probable": es_falso,
        "prioritarias": details_prior,
        "secundarias": details_sec,
        "adicionales": details_extra,
        "metadatos": meta,
        "paginas": pages,
        "escaneado_aprox": scanned,
        "imagenes": img_info,
        "analisis_capas": {
            "deteccion_avanzada": layers_analysis,
            "superposicion_texto": text_overlapping,
            "estructura_pdf": structure_analysis
        }
    }


def evaluar_riesgo_factura(pdf_bytes: bytes, fuente_texto: str, pdf_fields: Dict[str, Any], sri_ok: bool) -> Dict[str, Any]:
    """
    Igual que evaluar_riesgo, pero si el comprobante SRI no coincide,
    suma la penalización 'sri_verificacion'.
    """
    base = evaluar_riesgo(pdf_bytes, fuente_texto, pdf_fields)

    penal = 0 if sri_ok else RISK_WEIGHTS.get("sri_verificacion", 0)
    base["score"] = max(0, min(100, base["score"] + penal))
    base.setdefault("adicionales", []).append({
        "check": "Verificación contra SRI",
        "detalle": "Coincidencia" if sri_ok else "No coincide con SRI",
        "penalizacion": penal
    })

    # recalcular nivel
    for k, (lo, hi) in RISK_LEVELS.items():
        if lo <= base["score"] <= hi:
            base["nivel"] = k
            break

    return base


# ==================== FUNCIONES AUXILIARES PARA ANÁLISIS ====================

def generar_reporte_capas(layers_analysis: Dict[str, Any], text_overlapping: Dict[str, Any], 
                         structure_analysis: Dict[str, Any]) -> str:
    """
    Genera un reporte legible del análisis de capas múltiples.
    """
    reporte = []
    reporte.append("=== REPORTE DE ANÁLISIS DE CAPAS MÚLTIPLES ===\n")
    
    # Análisis principal
    if layers_analysis["has_layers"]:
        reporte.append(f"🔴 CAPAS DETECTADAS (Confianza: {layers_analysis['confidence']:.1%})")
        reporte.append(f"   Objetos OCG encontrados: {layers_analysis['ocg_objects']}")
        reporte.append(f"   Estimación de capas: {layers_analysis['layer_count_estimate']}")
        
        if layers_analysis["indicators"]:
            reporte.append("   Indicadores técnicos:")
            for indicator in layers_analysis["indicators"]:
                reporte.append(f"   - {indicator}")
    else:
        reporte.append("✅ No se detectaron capas OCG estándar")
    
    reporte.append("")
    
    # Análisis de texto
    if text_overlapping["has_overlapping"]:
        reporte.append("🟡 SUPERPOSICIÓN DE TEXTO DETECTADA:")
        
        if text_overlapping["duplicate_lines"]:
            reporte.append(f"   Líneas duplicadas: {len(text_overlapping['duplicate_lines'])}")
            for line, count in list(text_overlapping["duplicate_lines"].items())[:3]:
                reporte.append(f"   - '{line[:50]}...' aparece {count} veces")
        
        if text_overlapping["similar_lines"]:
            reporte.append(f"   Líneas similares: {len(text_overlapping['similar_lines'])}")
            for line1, line2, sim in text_overlapping["similar_lines"][:2]:
                reporte.append(f"   - Similitud {sim:.1%}: '{line1[:30]}...' ≈ '{line2[:30]}...'")
        
        if text_overlapping["suspicious_formatting"]:
            reporte.append("   Formato sospechoso detectado:")
            for fmt in text_overlapping["suspicious_formatting"][:3]:
                reporte.append(f"   - {fmt}")
    else:
        reporte.append("✅ No se detectó superposición de texto")
    
    reporte.append("")
    
    # Análisis estructural
    if structure_analysis["suspicious_structure"]:
        reporte.append("🟡 ESTRUCTURA PDF SOSPECHOSA:")
        for detail in structure_analysis["details"]:
            reporte.append(f"   - {detail}")
    else:
        reporte.append("✅ Estructura PDF normal")
    
    return "\n".join(reporte)


def detectar_capas_standalone(pdf_path: str) -> Dict[str, Any]:
    """
    Función standalone para detectar capas en un PDF específico.
    Útil para testing y análisis independiente.
    """
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        doc = fitz.open(pdf_path)
        extracted_text = ""
        for page in doc:
            extracted_text += page.get_text() + "\n"
        doc.close()
        
        # Ejecutar análisis
        layers_analysis = _detect_layers_advanced(pdf_bytes)
        text_overlapping = _detect_text_overlapping(extracted_text)
        
        doc = fitz.open(pdf_path)
        structure_analysis = _analyze_pdf_structure_layers(doc)
        doc.close()
        
        # Generar reporte
        reporte = generar_reporte_capas(layers_analysis, text_overlapping, structure_analysis)
        
        return {
            "archivo": pdf_path,
            "tiene_capas": layers_analysis["has_layers"],
            "confianza_total": layers_analysis["confidence"],
            "tiene_superposicion_texto": text_overlapping["has_overlapping"],
            "estructura_sospechosa": structure_analysis["suspicious_structure"],
            "analisis_detallado": {
                "capas": layers_analysis,
                "texto": text_overlapping,
                "estructura": structure_analysis
            },
            "reporte": reporte
        }
        
    except Exception as e:
        return {
            "archivo": pdf_path,
            "error": str(e),
            "tiene_capas": False,
            "confianza_total": 0.0
        }