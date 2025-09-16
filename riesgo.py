import re
import statistics
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import json
from typing import Optional
import fitz  # PyMuPDF
# from defauld import detectar_texto_sobrepuesto_base64 # No necesario, usamos la función local
 

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


from sri import (
    sri_autorizacion_por_clave,
    parse_autorizacion_response,
    factura_xml_to_json,
    validar_clave_acceso_interna,
)

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
from helpers.validacion_financiera import validar_contenido_financiero
from helpers.firma_digital import analizar_firmas_digitales, tiene_firma_digital
from helpers.deteccion_capas import LayerDetector, detect_layers_advanced, calculate_dynamic_penalty


def verificar_sri_para_riesgo(
    clave_acceso: str,
    guardar_json: bool = False,
) -> Dict[str, Any]:
    """
    Ejecuta la validación interna + consulta SRI + parseo XML->JSON.
    No imprime nada; retorna un dict con todo lo necesario para scoring y trazabilidad.
    """
    resultado: Dict[str, Any] = {
        "validacion_interna": None,
        "consulta_ok": False,
        "autorizado": False,
        "estado": "",
        "raw": None,
        "factura_json": None,
        "error": None,
        "archivo_json": None,
        "clave": clave_acceso,
    }

    # 1) Validación interna (49 dígitos + módulo 11)
    try:
        es_valida, mensaje, detalles = validar_clave_acceso_interna(clave_acceso)
        resultado["validacion_interna"] = {
            "ok": bool(es_valida),
            "mensaje": mensaje,
            "detalles": detalles,
        }
        if not es_valida:
            # No seguimos con el WS si es manifiestamente inválida
            return resultado
    except Exception as e:
        resultado["validacion_interna"] = {
            "ok": False,
            "mensaje": f"Error en validación interna: {e}",
            "detalles": {},
        }
        # Aun así, intentamos el WS (como hacía tu test en el except)
        pass

    # 2) Consulta al SRI (selección de WSDL y timeouts ya los maneja sri_autorizacion_por_clave)
    try:
        resp = sri_autorizacion_por_clave(clave_acceso)
        # 3) Parseo robusto de respuesta
        autorizado, estado, xml_comprobante, raw_data = parse_autorizacion_response(resp)

        resultado["consulta_ok"] = True
        resultado["autorizado"] = bool(autorizado)
        resultado["estado"] = estado or ""
        resultado["raw"] = raw_data

        # 4) Si hay XML, convertir a JSON con los campos clave
        if xml_comprobante:
            try:
                factura_json = factura_xml_to_json(xml_comprobante)
                resultado["factura_json"] = factura_json

                # (opcional) guarda un JSON reducido de trazas
                if guardar_json:
                    nombre = f"sri_response_{clave_acceso[:10]}.json"
                    with open(nombre, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "clave_acceso": clave_acceso,
                                "autorizado": autorizado,
                                "estado": estado,
                                "raw_response": raw_data,
                                "factura_json": factura_json,
                            },
                            f,
                            indent=2,
                            ensure_ascii=False,
                        )
                    resultado["archivo_json"] = nombre

            except Exception as e:
                # XML presente pero error al convertir a JSON: lo devolvemos crudo en raw
                resultado["error"] = f"XML presente pero error en parsing JSON: {e}"

    except Exception as e:
        resultado["error"] = f"Error consultando SRI: {e}"

    return resultado



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

def _detect_layers_advanced(pdf_bytes: bytes, extracted_text: str = "") -> Dict[str, Any]:
    """
    Función refactorizada que usa el nuevo LayerDetector modular.
    Mantiene compatibilidad con código existente.
    """
    try:
        # Usar el nuevo detector modular
        detector = LayerDetector(pdf_bytes, extracted_text)
        result = detector.analyze()
        
        # Mapear campos para mantener compatibilidad con código existente
        if "penalty_points" in result:
            # El nuevo sistema ya calcula la penalización óptima
            result["penalty_calculated"] = result["penalty_points"]
        
        return result
        
    except Exception as e:
        # Fallback en caso de error
        return {
            "has_layers": False,
            "confidence": 0.0,
            "probability_percentage": 0.0,
            "risk_level": "VERY_LOW",
            "penalty_points": 0,
            "error": f"Error en detección de capas: {str(e)}",
            "indicators": [],
            "layer_count_estimate": 0,
            "ocg_objects": 0,
            "overlay_objects": 0,
            "transparency_objects": 0,
            "suspicious_operators": 0,
            "content_streams": 0,
            "blend_modes": [],
            "alpha_values": [],
            "score_breakdown": {},
            "weights_used": {"ocg_confidence": 0.35, "overlay_presence": 0.25, 
                           "text_overlapping": 0.25, "structure_suspicious": 0.15},
            "detailed_analysis": {}
        }


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


def _detect_text_overlapping(extracted_text: str) -> bool:
    """
    Analiza el texto extraído para detectar superposiciones y duplicaciones
    que pueden indicar capas múltiples.
    """
    if not extracted_text:
        return False  # No hay texto, no puede haber superposición
    lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
    # Detectar líneas duplicadas exactas
    line_counts = Counter(lines)
    duplicates = {line: count for line, count in line_counts.items() if count > 1}
    if duplicates:
        return True  # Si hay líneas duplicadas, hay superposición
    # Detectar líneas similares
    similar_pairs = []
    for i, line1 in enumerate(lines):
        for j, line2 in enumerate(lines[i+1:], i+1):
            similarity = SequenceMatcher(None, line1, line2).ratio()
            if 0.7 <= similarity < 1.0:  # Muy similar pero no idéntica
                similar_pairs.append((line1, line2, similarity))
    if similar_pairs:
        return True  # Si hay líneas similares, hay superposición
    return False  # Si no se encuentran duplicados ni líneas similares, no hay superposición


def _detect_layers(pdf_bytes: bytes) -> bool:
    """Función simplificada que mantiene la compatibilidad con el código existente."""
    advanced_result = _detect_layers_advanced(pdf_bytes)
    return advanced_result["has_layers"]


# ================= FUNCIONES DE CONVENIENCIA PARA EL NUEVO SISTEMA =================

def evaluar_capas_multiples_completo(pdf_bytes: bytes, extracted_text: str = "", 
                                   base_weight: int = None) -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar análisis completo de capas múltiples
    con el nuevo sistema modular.
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        extracted_text: Texto extraído del PDF (opcional)
        base_weight: Peso base personalizado (opcional, default: 15)
        
    Returns:
        Dict con análisis completo y penalización calculada
    """
    try:
        # Usar el nuevo sistema modular
        detector = LayerDetector(pdf_bytes, extracted_text, base_weight)
        result = detector.analyze()
        
        # Agregar información de configuración
        result["configuration"] = {
            "base_weight_used": base_weight or 15,
            "analysis_version": "modular_v2",
            "components_analyzed": ["OCG", "Overlays", "TextOverlap", "Structure"],
            "calculation_method": "dynamic_weighted"
        }
        
        return result
        
    except Exception as e:
        return {
            "error": f"Error en análisis completo: {str(e)}",
            "has_layers": False,
            "penalty_points": 0,
            "probability_percentage": 0.0
        }


def calcular_penalizacion_capas_optimizada(probability_percentage: float, 
                                         risk_level: str = None,
                                         base_weight: int = 15) -> Dict[str, Any]:
    """
    Calcula penalización optimizada usando múltiples métodos y retorna el análisis completo.
    
    Args:
        probability_percentage: Porcentaje de probabilidad (0-100)
        risk_level: Nivel de riesgo opcional (AUTO-detectado si no se proporciona)
        base_weight: Peso base para cálculos
        
    Returns:
        Dict con penalización y desglose detallado
    """
    # Método 1: Penalización proporcional
    proportional = round((probability_percentage / 100) * base_weight)
    
    # Método 2: Penalización escalonada
    if not risk_level:
        if probability_percentage >= 80:
            risk_level = "VERY_HIGH"
        elif probability_percentage >= 60:
            risk_level = "HIGH"
        elif probability_percentage >= 40:
            risk_level = "MEDIUM"
        elif probability_percentage >= 20:
            risk_level = "LOW"
        else:
            risk_level = "VERY_LOW"
    
    # Multiplicadores por nivel
    multipliers = {
        "VERY_HIGH": 1.0,
        "HIGH": 0.8,
        "MEDIUM": 0.6,
        "LOW": 0.4,
        "VERY_LOW": 0.2
    }
    
    scaled = round(base_weight * multipliers.get(risk_level, 0.2))
    
    # Usar el mayor de los dos métodos para ser más estricto
    final_penalty = max(proportional, scaled)
    
    return {
        "penalty_points": final_penalty,
        "calculation_breakdown": {
            "proportional_method": proportional,
            "scaled_method": scaled,
            "method_used": "max_of_both",
            "risk_level": risk_level,
            "base_weight": base_weight,
            "probability_percentage": probability_percentage
        },
        "explanation": f"Penalización de {final_penalty} puntos para {probability_percentage:.1f}% de probabilidad (nivel: {risk_level})"
    }


def detectar_texto_sobrepuesto_avanzado(pdf_bytes: bytes, tolerancia_solapamiento: float = 5.0) -> Dict[str, Any]:
    """
    Detecta texto sobrepuesto en un PDF comparando coordenadas de palabras.
    Usa la lógica exacta de defauld.py adaptada para trabajar con pdf_bytes.
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        tolerancia_solapamiento: Tolerancia en puntos para considerar texto sobrepuesto
        
    Returns:
        Dict con análisis detallado de texto sobrepuesto
    """
    resultado = {
        "texto_sobrepuesto_detectado": False,
        "alertas": [],
        "total_casos": 0,
        "paginas_afectadas": [],
        "metodo_usado": "pdfplumber_defauld",
        "estadisticas": {
            "total_palabras_analizadas": 0,
            "paginas_procesadas": 0
        },
        "error": None
    }
    
    if not PDFPLUMBER_AVAILABLE:
        resultado["metodo_usado"] = "fitz_fallback"
        resultado["error"] = "pdfplumber no disponible, usando método alternativo"
        return resultado
    
    try:
        import io
        
        # Crear stream de bytes para pdfplumber (igual que defauld.py línea 48)
        pdf_stream = io.BytesIO(pdf_bytes)
        
        with pdfplumber.open(pdf_stream) as pdf:
            for pagina_num, pagina in enumerate(pdf.pages, start=1):
                # Extraer palabras exactamente como en defauld.py (líneas 54-60)
                palabras = pagina.extract_words(
                    x_tolerance=1,
                    y_tolerance=1,
                    keep_blank_chars=True,
                    use_text_flow=False,
                    extra_attrs=["top", "bottom", "x0", "x1"]
                )
                
                if not palabras:
                    continue
                
                resultado["estadisticas"]["total_palabras_analizadas"] += len(palabras)
                
                # Agrupar por posición vertical aproximada (lógica de defauld.py)
                grupos_por_fila = defaultdict(list)
                for palabra in palabras:
                    # Redondear 'top' para agrupar en la misma línea
                    clave_fila = round(palabra['top'], 1)
                    grupos_por_fila[clave_fila].append(palabra)
                
                casos_pagina = 0
                
                # Comparar cada par de palabras en la misma fila (lógica exacta de defauld.py)
                for top, grupo in grupos_por_fila.items():
                    for i, p1 in enumerate(grupo):
                        for j, p2 in enumerate(grupo):
                            if i >= j:
                                continue  # Evitar comparar consigo mismo o repetir pares
                            
                            # Calcular solapamiento horizontal (líneas 50-52 de defauld.py)
                            solapamiento_x = max(0, min(p1['x1'], p2['x1']) - max(p1['x0'], p2['x0']))
                            ancho_promedio = (p1['x1'] - p1['x0'] + p2['x1'] - p2['x0']) / 2
                            
                            # Si solapamiento > 50% del ancho promedio → ALERTA (línea 55 de defauld.py)
                            if solapamiento_x > 0.5 * ancho_promedio:
                                casos_pagina += 1
                                
                                # Crear alerta con formato exacto de defauld.py (líneas 56-64)
                                alerta = {
                                    'pagina': pagina_num,
                                    'posicion': f"Y≈{top}",
                                    'texto1': p1['text'],
                                    'coord1': (p1['x0'], p1['top']),
                                    'texto2': p2['text'],
                                    'coord2': (p2['x0'], p2['top']),
                                    'solapamiento_px': round(solapamiento_x, 2)
                                }
                                
                                resultado["alertas"].append(alerta)
                
                if casos_pagina > 0:
                    resultado["paginas_afectadas"].append({
                        "pagina": pagina_num,
                        "casos": casos_pagina
                    })
                
                resultado["estadisticas"]["paginas_procesadas"] += 1
        
        # Determinar resultado final
        resultado["total_casos"] = len(resultado["alertas"])
        resultado["texto_sobrepuesto_detectado"] = resultado["total_casos"] > 0
        
    except Exception as e:
        resultado["error"] = f"Error al procesar el archivo PDF: {str(e)}"
        resultado["metodo_usado"] = "error"
    
    return resultado



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
    return meta.get("producer") == meta.get("Creator") == meta.get("author") or meta.get("Creator") !=  "" or  meta.get("author") == ""

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

def evaluar_riesgo_con_xml_sri(pdf_bytes: bytes, fuente_texto: str, pdf_fields: Dict[str, Any], xml_sri: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Versión de evaluar_riesgo que puede usar datos del XML del SRI para validación financiera más precisa.
    """
    # Simplemente llamamos a evaluar_riesgo pero actualizamos la validación financiera
    base_result = evaluar_riesgo(pdf_bytes, fuente_texto, pdf_fields)
    
    # Si tenemos XML del SRI, re-ejecutamos solo la validación financiera con esos datos (DESHABILITADO)
    # if xml_sri and xml_sri.get("autorizado"):
    #     print("DEBUG: Re-ejecutando validación financiera con XML del SRI")
    #     validacion_financiera_mejorada = validar_contenido_financiero(pdf_fields, fuente_texto or "", xml_sri)
    #     
    #     # Reemplazar la validación financiera en el resultado
    #     for i, check in enumerate(base_result.get("adicionales", [])):
    #         if check.get("check") == "Validación financiera completa":
    #             base_result["adicionales"][i] = {
    #                 "check": "Validación financiera completa",
    #                 "detalle": validacion_financiera_mejorada,
    #                 "penalizacion": RISK_WEIGHTS.get("validacion_financiera", 0) if not validacion_financiera_mejorada["validacion_general"]["valido"] else 0
    #             }
    #             break
    #     else:
    #         # Si no se encontró, agregarla
    #         base_result.setdefault("adicionales", []).append({
    #             "check": "Validación financiera completa",
    #             "detalle": validacion_financiera_mejorada,
    #             "penalizacion": RISK_WEIGHTS.get("validacion_financiera", 0) if not validacion_financiera_mejorada["validacion_general"]["valido"] else 0
    #         })
    
    return base_result


def evaluar_riesgo(pdf_bytes: bytes, fuente_texto: str, pdf_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula score y desglose de validaciones para el PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    meta = doc.metadata or {}
    pages = doc.page_count
    size_bytes = len(pdf_bytes)
    scanned = _is_scanned_image_pdf(pdf_bytes, fuente_texto or "")

    # --- ANÁLISIS AVANZADO DE CAPAS ---
    layers_analysis = _detect_layers_advanced(pdf_bytes, fuente_texto or "")
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

    # --- análisis avanzado de texto sobrepuesto (ejecutar una sola vez) ---
    texto_sobrepuesto_analisis_completo = detectar_texto_sobrepuesto_avanzado(pdf_bytes)
    
    # --- análisis financiero completo ---
    # TODO: Integrar XML del SRI cuando esté disponible
    validacion_financiera = validar_contenido_financiero(pdf_fields, fuente_texto or "")
    
    # --- consistencia matemática --- (DESHABILITADO)
    # print(f"DEBUG EVALUAR_RIESGO: Llamando _evaluar_consistencia_matematica con pdf_fields keys: {list(pdf_fields.keys()) if pdf_fields else 'None'}")
    # math_consistency_result = _evaluar_consistencia_matematica(pdf_fields, fuente_texto or "", validacion_financiera)
    # print(f"DEBUG EVALUAR_RIESGO: math_consistency_result = {math_consistency_result}")
    # print(f"DEBUG EVALUAR_RIESGO: math_consistency_result is None? {math_consistency_result is None}")
    # print(f"DEBUG EVALUAR_RIESGO: bool(math_consistency_result)? {bool(math_consistency_result)}")
    math_consistency_result = None  # Deshabilitado
    
    # --- análisis completo de firmas digitales ---
    analisis_firmas = analizar_firmas_digitales(pdf_bytes)

    # --- tamaño esperado ---
    size_expect = _file_size_expectation(size_bytes, pages, scanned)

    # --- otros marcadores ---
    has_js = _has_js_embedded(pdf_bytes)
    has_emb = _has_embedded_files(pdf_bytes)
    has_forms = _has_forms_or_annots(pdf_bytes)
    has_sig = tiene_firma_digital(pdf_bytes)
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
        if dias >= 0 and dias <= 10:
            penal = 0
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
        if diff != 0:
            penal = int(RISK_WEIGHTS["fecha_mod_vs_creacion"])
    details_prior.append({"check": "Fecha de modificación vs fecha de creación", "detalle": msg, "penalizacion": penal})
    score += penal

    # 3) Software conocido
    penal = 0 if prod_ok else RISK_WEIGHTS["software_conocido"]
    details_prior.append({"check": "Software de creación/producción conocido", "detalle": meta, "penalizacion": penal})
    score += penal


    # 5) Presencia de capas múltiples (ANÁLISIS INTEGRADO CON SISTEMA DINÁMICO)
    layer_details = {
        "deteccion_avanzada": layers_analysis["has_layers"],
        "porcentaje_probabilidad": layers_analysis["probability_percentage"],
        "nivel_riesgo": layers_analysis["risk_level"],
        "confianza": layers_analysis["confidence"],
        "indicadores": layers_analysis["indicators"],
        "objetos_ocg": layers_analysis["ocg_objects"],
        "objetos_superpuestos": layers_analysis["overlay_objects"],
        "objetos_transparencia": layers_analysis["transparency_objects"],
        "operadores_sospechosos": layers_analysis["suspicious_operators"],
        "content_streams": layers_analysis["content_streams"],
        "modos_fusion": layers_analysis["blend_modes"],
        "valores_alpha": layers_analysis["alpha_values"],
        "desglose_puntuacion": layers_analysis["score_breakdown"],
        "estimacion_capas": layers_analysis["layer_count_estimate"],
        "analisis_detallado": layers_analysis["detailed_analysis"],
        "metodo_calculo": "sistema_dinamico_v2"
    }
    
    # NUEVO SISTEMA DE PESOS DINÁMICOS MEJORADO
    # El LayerDetector ya calculó la penalización óptima usando múltiples métodos
    if "penalty_points" in layers_analysis:
        penal = layers_analysis["penalty_points"]
        layer_details["peso_base_usado"] = layers_analysis.get("weights_used", {})
        layer_details["penalty_method"] = "dynamic_calculated"
    else:
        # Fallback al método anterior si no está disponible
        probability_pct = layers_analysis["probability_percentage"]
        base_weight = RISK_WEIGHTS.get("capas_multiples", 15)  # Usar peso mejorado por defecto
        penal = calculate_dynamic_penalty(probability_pct, base_weight)
        layer_details["peso_base_usado"] = base_weight
        layer_details["penalty_method"] = "fallback_calculation"
    
    # Agregar información adicional del cálculo
    layer_details["penalty_calculated"] = penal
    layer_details["penalty_explanation"] = f"Penalización dinámica calculada: {penal} puntos para {layers_analysis['probability_percentage']:.1f}% de probabilidad (nivel: {layers_analysis['risk_level']})"

    details_prior.append({
        "check": "Presencia de capas múltiples (análisis integrado)", 
        "detalle": layer_details, 
        "penalizacion": penal
    })
    score += penal

    # SECUNDARIAS (continúan igual)
    # Consistencia de fuentes
    penal = 0
    f_det = fonts_info
    if f_det["num_fuentes_unicas"] > 2 or f_det["dominante_ratio"] < 0.4:
        penal = RISK_WEIGHTS["consistencia_fuentes"]
    elif f_det["num_fuentes_unicas"] > 2 or f_det["dominante_ratio"] < 0.6:
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

    # Alineación de elementos de texto (análisis completo con texto sobrepuesto)
    penal = 0
    
    # Calcular penalización basada en alineación tradicional
    if align_score_mean < 0.7 or rot_ratio_mean > 0.2:
        penal = RISK_WEIGHTS["alineacion_texto"]
    elif align_score_mean < 0.85 or rot_ratio_mean > 0.1:
        penal = int(RISK_WEIGHTS["alineacion_texto"] * 0.6)
    
    # Usar el análisis ya calculado para agregar información adicional
    texto_sobrepuesto = texto_sobrepuesto_analisis_completo
    
    # Construir detalle completo combinando alineación tradicional + texto sobrepuesto
    detalle_completo = {
        "alineacion_promedio": align_score_mean, 
        "rotacion_promedio": rot_ratio_mean,
        "alertas": texto_sobrepuesto.get("alertas", []),
            "texto_sobrepuesto_detectado": texto_sobrepuesto.get("texto_sobrepuesto_detectado", False),
            "total_casos": texto_sobrepuesto.get("total_casos", 0),
        "paginas_afectadas": texto_sobrepuesto.get("paginas_afectadas", []),
            "metodo_usado": texto_sobrepuesto.get("metodo_usado", "desconocido"),
            "estadisticas": texto_sobrepuesto.get("estadisticas", {})
    }
    
    # Agregar error si existe
    if texto_sobrepuesto.get("error"):
        detalle_completo["error"] = texto_sobrepuesto["error"]
    
    details_sec.append({
        "check": "Alineación de elementos de texto",
        "detalle": detalle_completo,
        "penalizacion": penal
    })
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

    # Firmas digitales (análisis completo)
    penal = 0
    if has_sig:
        # Bonificación base por tener firma
        penal = RISK_WEIGHTS["firmas_pdf"]
        
        # Ajustes basados en calidad de la firma
        if analisis_firmas["firmas_validas"] > 0:
            # Bonificación adicional por firmas válidas
            penal = int(penal * 1.5)
        
        if not analisis_firmas["integridad_documento"]["documento_integro"]:
            # Penalización si el documento fue modificado después de firmar
            penal = int(penal * 0.3)  # Reduce significativamente la bonificación
        
        if analisis_firmas["seguridad"]["nivel_seguridad"] == "alto":
            # Bonificación extra por alta seguridad
            penal = int(penal * 1.2)
    
    # Crear detalle completo de firma
    detalle_firma = {
        "firma_detectada": has_sig,
        "cantidad_firmas": analisis_firmas["cantidad_firmas"],
        "firmas_validas": analisis_firmas["firmas_validas"],
        "nivel_seguridad": analisis_firmas["seguridad"]["nivel_seguridad"],
        "documento_integro": analisis_firmas["integridad_documento"]["documento_integro"],
        "certificado_valido": analisis_firmas["cadena_confianza"]["certificado_raiz_valido"]
    }
    
    # Agregar vulnerabilidades si existen
    if analisis_firmas["seguridad"]["vulnerabilidades"]:
        detalle_firma["vulnerabilidades"] = analisis_firmas["seguridad"]["vulnerabilidades"]
    
    details_extra.append({
        "check": "Firma(s) digital(es) PDF", 
        "detalle": detalle_firma, 
        "penalizacion": penal
    })
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
 
    # Estructura sospechosa sin otras indicaciones
    has_text_overlapping = text_overlapping if isinstance(text_overlapping, bool) else text_overlapping.get("has_overlapping", False)
    if structure_analysis["suspicious_structure"] and not has_layers and not has_text_overlapping:
        penal = int(RISK_WEIGHTS.get("capas_multiples"))
        details_extra.append({
            "check": "Estructura PDF sospechosa", 
            "detalle": structure_analysis["details"], 
            "penalizacion": penal
        })
        score += penal

  

    # Estructura sospechosa sin otras indicaciones (segunda verificación - eliminar duplicado)
    # Esta línea es duplicada y se puede eliminar

    # Validación financiera completa (DESHABILITADO)
    # penal = 0
    # 
    # # Usar el análisis financiero ya calculado
    # if not validacion_financiera["validacion_general"]["valido"]:
    #     # Penalización basada en el score de validación financiera
    #     score_financiero = validacion_financiera["validacion_general"]["score_validacion"]
    #     penal = int(RISK_WEIGHTS.get("validacion_financiera", 15) * (100 - score_financiero) / 100)
    # 
    # # Solo mostrar el criterio si hay datos suficientes para validar
    # if (validacion_financiera["validacion_items"]["total_items"] > 0 or 
    #     validacion_financiera["validacion_totales"]["total_declarado"] > 0):
    #     
    #     details_extra.append({
    #         "check": "Validación financiera completa", 
    #         "detalle": validacion_financiera, 
    #         "penalizacion": penal
    #     })
    #     score += penal
    
    # 5.1) Math Consistency (check específico) - DESHABILITADO
    # penal_math = 0
    # math_valido = True
    # math_errores = []
    # 
    # # Siempre agregar el check de math_consistency si se ejecutó
    # if math_consistency_result is not None:
    #     math_valido = math_consistency_result.get("valido", True)
    #     math_errores = math_consistency_result.get("errores", [])
    #     
    #     if not math_valido:
    #         penal_math = RISK_WEIGHTS.get("math_consistency", 10)
    #     
    #     details_extra.append({
    #         "check": "Consistencia aritmética (math_consistency)",
    #         "detalle": math_consistency_result,
    #         "penalizacion": penal_math
    #     })
    #     score += penal_math
    #     print(f"DEBUG: Math consistency agregado - válido: {math_valido}, errores: {len(math_errores)}, penalización: {penal_math}")
    # else:
    #     print("DEBUG: math_consistency_result es None - no se agregó el check")

    # Normalizar score a [0, 100] y redondear
    score = round(max(0, min(100, score)), 2)

    # Determinar si es falso (indicadores fuertes)
    es_falso = False
    if has_layers and layers_analysis["confidence"] >= 0.7:
        es_falso = True
    if dt_cre and dt_mod and dt_cre != dt_mod and abs((dt_mod - dt_cre).days) > 1:
        es_falso = True
    # Manejar text_overlapping que puede ser bool o dict
    if isinstance(text_overlapping, bool):
        has_text_overlapping = text_overlapping
        duplicate_lines_count = 0
    else:
        duplicate_lines_count = len(text_overlapping.get("duplicate_lines", {}))
    
    if has_text_overlapping and duplicate_lines_count > 2:
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


def evaluar_riesgo_factura(
    pdf_bytes: bytes,
    fuente_texto: str,
    pdf_fields: Dict[str, Any],
    sri_ok: Optional[bool],                  # retrocompatible: si ya tienes el booleano de coincidencia
    clave_acceso: Optional[str] = None,      # si la pasas, podemos ejecutar el test SRI aquí mismo
    ejecutar_prueba_sri: bool = False,       # True => se ejecuta verificar_sri_para_riesgo(...)
    guardar_json_sri: bool = False,          # True => guarda archivo sri_response_*.json como hacía tu test
    xml_sri_data: Optional[Dict[str, Any]] = None  # Datos XML del SRI ya parseados
) -> Dict[str, Any]:
    """
    Igual que antes, pero ahora puede ejecutar el 'test SRI' integrado si así lo pides.
    - Si 'sri_ok' no es None, se usa tal cual (comportamiento anterior).
    - Si 'sri_ok' es None y 'ejecutar_prueba_sri' es True y hay 'clave_acceso',
      entonces se consulta SRI aquí y se construye el sri_ok a partir de esa respuesta.
    """
    # 1) Determinar sri_ok y obtener datos XML (preferencia: argumento explícito; si no, calcularlo aquí)
    sri_test_result: Optional[Dict[str, Any]] = None
    
    # Si ya nos pasaron xml_sri_data, usarlo directamente
    if xml_sri_data is None and sri_ok is None and ejecutar_prueba_sri and clave_acceso:
        sri_test_result = verificar_sri_para_riesgo(clave_acceso, guardar_json=guardar_json_sri)
        # sri_ok "técnico": que el SRI diga AUTORIZADO
        sri_ok = bool(sri_test_result.get("autorizado", False))
        
        # Extraer datos XML del SRI si está autorizado
        if sri_ok and sri_test_result.get("xml_data"):
            xml_sri_data = sri_test_result["xml_data"]
            xml_sri_data["autorizado"] = True

    elif sri_ok is None:
        # Si no nos dieron sri_ok ni nos pidieron probar, asumimos desconocido (no penalizamos por defecto)
        sri_ok = True  # si prefieres penalizar en incertidumbre, cámbialo a False

    # 2) Ejecuta el análisis base, pasando XML del SRI si está disponible
    base = evaluar_riesgo_con_xml_sri(pdf_bytes, fuente_texto, pdf_fields, xml_sri_data)

    # 3) Aplicar penalización por verificación contra SRI (igual que antes, pero usando sri_ok final)
    penal = 0 if sri_ok else RISK_WEIGHTS.get("sri_verificacion", 0)
    base["score"] = round(max(0, min(100, base["score"] + penal)), 2)
    base.setdefault("adicionales", []).append({
        "check": "Verificación contra SRI",
        "detalle": "Coincidencia" if sri_ok else "No coincide con SRI / No autorizado",
        "penalizacion": penal
    })

    # 4) (Nuevo) Adjuntar resumen del test SRI si lo ejecutamos aquí
    if sri_test_result is not None:
        # Arma un resumen legible y compacto
        info_trib = ((sri_test_result.get("factura_json") or {}).get("infoTributaria") or {})
        info_fact = ((sri_test_result.get("factura_json") or {}).get("infoFactura") or {})

        base["sri"] = {
            "ejecutado_aqui": True,
            "clave": sri_test_result.get("clave"),
            "validacion_interna": sri_test_result.get("validacion_interna"),
            "consulta_ok": sri_test_result.get("consulta_ok"),
            "autorizado": sri_test_result.get("autorizado"),
            "estado": sri_test_result.get("estado"),
            # Campos clave (si hubo XML->JSON)
            "ruc": info_trib.get("ruc"),
            "razonSocial": info_trib.get("razonSocial"),
            "fechaEmision": info_fact.get("fechaEmision"),
            "importeTotal": info_fact.get("importeTotal"),
            # Trazas
            "raw_estados": (sri_test_result.get("raw") or {}).get("estados"),
            "claveAccesoConsultada": (sri_test_result.get("raw") or {}).get("claveAccesoConsultada"),
            "archivo_json": sri_test_result.get("archivo_json"),
            "error": sri_test_result.get("error"),
        }
    else:
        base["sri"] = {
            "ejecutado_aqui": False,
            "usado_sri_ok_externo": True,
            "sri_ok": bool(sri_ok)
        }

    # 5) Recalcular nivel según score final (igual que en tu función)
    for k, (lo, hi) in RISK_LEVELS.items():
        if lo <= base["score"] <= hi:
            base["nivel"] = k
            break

    return base
    """
    Igual que evaluar_riesgo, pero si el comprobante SRI no coincide,
    suma la penalización 'sri_verificacion'.
    """
    base = evaluar_riesgo(pdf_bytes, fuente_texto, pdf_fields)

    penal = 0 if sri_ok else RISK_WEIGHTS.get("sri_verificacion", 0)
    base["score"] = round(max(0, min(100, base["score"] + penal)), 2)
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


# ==================== MATH CONSISTENCY ====================

def _evaluar_consistencia_matematica(pdf_fields: Dict[str, Any], fuente_texto: str, validacion_financiera: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluación específica de consistencia matemática para el check math_consistency.
    
    IMPORTANTE: Valida SOLO datos extraídos del PDF, ignorando información del SRI.
    Esto mide la coherencia matemática interna del documento PDF.
    
    Valida:
    1. Fórmula: subtotal + IVA - descuentos - retenciones + propina = total
    2. Coherencia de items individuales extraídos del PDF
    3. Porcentajes de IVA válidos (0%, 15% en Ecuador)
    4. Rangos razonables de valores
    5. Detección de anomalías aritméticas en el PDF
    
    Args:
        pdf_fields: Campos extraídos del PDF
        fuente_texto: Texto completo extraído del PDF
        validacion_financiera: Resultado del helper (IGNORADO si usa XML SRI)
    
    Returns:
        Dict con resultado de consistencia matemática del PDF
    """
    resultado = {
        "valido": True,
        "errores": [],
        "advertencias": [],
        "metrica_consistencia": 100,
        "fuentes_datos": {
            "pdf_fields": bool(pdf_fields),
            "texto_extraido": bool(fuente_texto),
            "validacion_financiera": bool(validacion_financiera)
        },
        "validacion_formula": {
            "formula_correcta": True,
            "diferencia": 0.0,
            "tolerancia": 0.02,
            "componentes": {}
        },
        "validacion_items": {
            "items_analizados": 0,
            "items_validos": 0,
            "errores_items": []
        },
        "validacion_impuestos": {
            "iva_coherente": True,
            "porcentaje_detectado": 0.0,
            "tasas_validas": [0, 15]  # Ecuador
        },
        "anomalias_detectadas": []
    }
    
    try:
        # DEBUG: Mostrar contenido de pdf_fields
        print("=== DEBUG MATH_CONSISTENCY (SOLO PDF) ===")
        print(f"PDF_FIELDS contenido: {pdf_fields}")
        print(f"PDF_FIELDS keys: {list(pdf_fields.keys()) if pdf_fields else 'None'}")
        if pdf_fields:
            for key, value in pdf_fields.items():
                print(f"  {key}: {value} (tipo: {type(value)})")
        print(f"FUENTE_TEXTO disponible: {bool(fuente_texto)} (longitud: {len(fuente_texto) if fuente_texto else 0})")
        if fuente_texto and len(fuente_texto) > 0:
            print(f"FUENTE_TEXTO preview: {fuente_texto[:200]}...")
        
        # Verificar si la validación financiera está usando XML del SRI
        metodo_usado = validacion_financiera.get("extraccion_texto", {}).get("metodo_usado", "")
        usando_sri = metodo_usado == "xml_sri_oficial"
        
        print(f"METODO_VALIDACION: {metodo_usado}")
        print(f"IGNORANDO_SRI_PARA_MATH_CONSISTENCY: {usando_sri}")
        print("=== FIN DEBUG ===")
        
        # ESTRATEGIA MEJORADA: Para facturas legítimas, usar valores de validación financiera cuando no usa SRI
        if validacion_financiera and not usando_sri:
            print("DEBUG: Usando valores de validación financiera (sin SRI) para math_consistency")
            # Extraer valores de la validación financiera que ya funcionó
            totales = validacion_financiera.get("validacion_totales", {})
            if totales and totales.get("formula_correcta", False):
                # Copiar valores que ya fueron validados correctamente
                resultado["validacion_formula"]["componentes"] = {
                    "subtotal": totales.get("subtotal", 0),
                    "iva": totales.get("iva", 0),
                    "descuentos": totales.get("descuentos", 0),
                    "retenciones": totales.get("retenciones", 0),
                    "propina": totales.get("propina", 0),
                    "total_calculado": totales.get("total_calculado", 0),
                    "total_declarado": totales.get("total_declarado", 0)
                }
                resultado["validacion_formula"]["formula_correcta"] = True
                resultado["validacion_formula"]["diferencia"] = totales.get("diferencia", 0)
                resultado["validacion_formula"]["tolerancia"] = totales.get("tolerancia", 0.02)
                
                # Copiar validación de items
                items_info = validacion_financiera.get("validacion_items", {})
                if items_info:
                    resultado["validacion_items"]["items_analizados"] = items_info.get("total_items", 0)
                    resultado["validacion_items"]["items_validos"] = items_info.get("items_validos", 0)
                    resultado["validacion_items"]["subtotal_calculado"] = items_info.get("subtotal_calculado", 0)
                
                # Copiar validación de impuestos
                impuestos_info = validacion_financiera.get("validacion_impuestos", {})
                if impuestos_info:
                    resultado["validacion_impuestos"]["iva_coherente"] = impuestos_info.get("iva_coherente", True)
                    resultado["validacion_impuestos"]["porcentaje_detectado"] = impuestos_info.get("porcentaje_iva_detectado", 0)
                
                print(f"DEBUG: Valores copiados - Subtotal: {resultado['validacion_formula']['componentes']['subtotal']}, IVA: {resultado['validacion_formula']['componentes']['iva']}, Total: {resultado['validacion_formula']['componentes']['total_declarado']}")
            else:
                # Si la validación financiera falló, usar extracción directa
                print("DEBUG: Validación financiera falló, usando extracción directa del PDF")
                _evaluar_matematica_desde_pdf(pdf_fields, fuente_texto, resultado)
        else:
            # 1. Ejecutar validación matemática independiente del PDF para math_consistency
            print("DEBUG: Ejecutando validación matemática independiente del PDF para math_consistency")
            # Hacer validación matemática directa desde PDF (independiente del SRI)
            _evaluar_matematica_desde_pdf(pdf_fields, fuente_texto, resultado)
        
        # 2. Validaciones cruzadas con datos directos
        if pdf_fields or fuente_texto:
            _validaciones_cruzadas(pdf_fields, fuente_texto, resultado)
        
        # 3. Detectar anomalías específicas
        _detectar_anomalias_matematicas(pdf_fields, fuente_texto, validacion_financiera, resultado)
        
        # 4. Calcular métrica final
        resultado["metrica_consistencia"] = _calcular_metrica_consistencia(resultado)
        resultado["valido"] = resultado["metrica_consistencia"] >= 70
        
    except Exception as e:
        resultado["valido"] = False
        resultado["errores"].append(f"Error en evaluación matemática: {str(e)}")
        resultado["metrica_consistencia"] = 0
    
    return resultado


def _evaluar_formula_financiera(validacion_financiera: Dict[str, Any], resultado: Dict[str, Any]):
    """Evalúa la fórmula: subtotal + IVA - descuentos - retenciones + propina = total"""
    totales = validacion_financiera.get("validacion_totales", {})
    
    formula_ok = totales.get("formula_correcta", False)
    diferencia = abs(totales.get("diferencia", 0))
    tolerancia = totales.get("tolerancia", 0.02)
    
    resultado["validacion_formula"]["formula_correcta"] = formula_ok
    resultado["validacion_formula"]["diferencia"] = diferencia
    resultado["validacion_formula"]["tolerancia"] = tolerancia
    resultado["validacion_formula"]["componentes"] = {
        "subtotal": totales.get("subtotal", 0),
        "iva": totales.get("iva", 0),
        "descuentos": totales.get("descuentos", 0),
        "retenciones": totales.get("retenciones", 0),
        "propina": totales.get("propina", 0),
        "total_calculado": totales.get("total_calculado", 0),
        "total_declarado": totales.get("total_declarado", 0)
    }
    
    if not formula_ok:
        resultado["errores"].append(f"Fórmula aritmética incorrecta: diferencia {diferencia:.2f} > tolerancia {tolerancia:.2f}")


def _evaluar_items_individuales(validacion_financiera: Dict[str, Any], resultado: Dict[str, Any]):
    """Evalúa coherencia de items individuales"""
    items = validacion_financiera.get("validacion_items", {})
    
    total_items = items.get("total_items", 0)
    items_validos = items.get("items_validos", 0)
    items_errores = items.get("items_con_errores", [])
    
    resultado["validacion_items"]["items_analizados"] = total_items
    resultado["validacion_items"]["items_validos"] = items_validos
    resultado["validacion_items"]["errores_items"] = items_errores
    
    if total_items > 0:
        porcentaje_validos = (items_validos / total_items) * 100
        if porcentaje_validos < 80:
            resultado["errores"].append(f"Solo {porcentaje_validos:.1f}% de items tienen cálculos correctos")
        elif porcentaje_validos < 95:
            resultado["advertencias"].append(f"Items con errores menores: {len(items_errores)}")


def _evaluar_coherencia_impuestos(validacion_financiera: Dict[str, Any], resultado: Dict[str, Any]):
    """Evalúa coherencia de impuestos (IVA ecuatoriano: 0% o 15%)"""
    impuestos = validacion_financiera.get("validacion_impuestos", {})
    
    iva_coherente = impuestos.get("iva_coherente", True)
    porcentaje = impuestos.get("porcentaje_iva_detectado", 0)
    
    resultado["validacion_impuestos"]["iva_coherente"] = iva_coherente
    resultado["validacion_impuestos"]["porcentaje_detectado"] = porcentaje
    
    if not iva_coherente:
        resultado["errores"].append(f"IVA no estándar: {porcentaje:.2f}% (esperado: 0% o 15%)")
    
    # Validar que el porcentaje esté en rangos válidos para Ecuador
    tasas_validas = [0, 15]
    if porcentaje > 0 and not any(abs(porcentaje - tasa) <= 1.0 for tasa in tasas_validas):
        resultado["advertencias"].append(f"Tasa IVA inusual para Ecuador: {porcentaje:.2f}%")


def _validaciones_cruzadas(pdf_fields: Dict[str, Any], fuente_texto: str, resultado: Dict[str, Any]):
    """Validaciones cruzadas con datos directos del PDF"""
    
    # Buscar números sospechosos en el texto
    if fuente_texto:
        import re
        numeros_grandes = re.findall(r'\b(\d{6,})\b', fuente_texto)
        if numeros_grandes:
            # Filtrar códigos de productos típicos
            numeros_sospechosos = [n for n in numeros_grandes if not any(
                palabra in fuente_texto.lower() for palabra in ['codigo', 'product', 'item', 'ref']
            )]
            if numeros_sospechosos:
                resultado["advertencias"].append(f"Números grandes detectados: {numeros_sospechosos[:3]}")
    
    # Validar coherencia de fechas vs montos
    if pdf_fields:
        fecha_emision = pdf_fields.get("fechaEmision")
        importe_total = pdf_fields.get("importeTotal")
        
        if fecha_emision and importe_total:
            try:
                from datetime import datetime
                if isinstance(fecha_emision, str):
                    # Intentar parsear fecha
                    fecha_dt = datetime.strptime(fecha_emision.split()[0], "%d/%m/%Y")
                    año = fecha_dt.year
                    
                    # Validar montos típicos por año (inflación)
                    if año >= 2020 and importe_total < 0.10:
                        resultado["advertencias"].append(f"Monto muy bajo para {año}: ${importe_total}")
                    elif año >= 2020 and importe_total > 100000:
                        resultado["advertencias"].append(f"Monto muy alto para factura: ${importe_total}")
            except:
                pass  # No es crítico si no se puede parsear


def _detectar_anomalias_matematicas(pdf_fields: Dict[str, Any], fuente_texto: str, validacion_financiera: Dict[str, Any], resultado: Dict[str, Any]):
    """Detecta anomalías matemáticas específicas"""
    
    anomalias = []
    
    # 1. Validar que el total no sea 0 o negativo
    if validacion_financiera:
        total = validacion_financiera.get("validacion_totales", {}).get("total_declarado", 0)
        if total <= 0:
            anomalias.append("Total declarado es 0 o negativo")
        elif total == int(total) and total > 100:  # Entero grande
            anomalias.append(f"Total sospechosamente redondo: ${int(total)}")
    
    # 2. Detectar duplicación de números en texto
    if fuente_texto:
        import re
        from collections import Counter
        
        numeros = re.findall(r'\d+[.,]\d{2}', fuente_texto)
        conteos = Counter(numeros)
        duplicados = [num for num, count in conteos.items() if count > 3]
        
        if duplicados:
            anomalias.append(f"Números repetidos excesivamente: {duplicados[:2]}")
    
    # 3. Validar proporciones IVA
    if validacion_financiera:
        totales = validacion_financiera.get("validacion_totales", {})
        subtotal = totales.get("subtotal", 0)
        iva = totales.get("iva", 0)
        
        if subtotal > 0 and iva > 0:
            proporcion = (iva / subtotal) * 100
            if proporcion > 20:  # IVA mayor al 20%
                anomalias.append(f"IVA excesivo: {proporcion:.1f}% del subtotal")
            elif 0 < proporcion < 1:  # IVA muy bajo
                anomalias.append(f"IVA muy bajo: {proporcion:.1f}% del subtotal")
    
    resultado["anomalias_detectadas"] = anomalias
    
    # Agregar a errores si hay anomalías críticas
    for anomalia in anomalias:
        if any(palabra in anomalia.lower() for palabra in ['0 o negativo', 'excesivo']):
            resultado["errores"].append(f"Anomalía crítica: {anomalia}")


def _evaluar_matematica_desde_pdf(pdf_fields: Dict[str, Any], fuente_texto: str, resultado: Dict[str, Any]):
    """
    Evalúa consistencia matemática extrayendo valores directamente del PDF.
    SISTEMA ROBUSTO: Funciona con cualquier formato de factura ecuatoriana.
    NO usa datos del SRI, solo lo que se puede extraer del documento.
    """
    import re
    
    print(f"DEBUG MATH_CONSISTENCY: ===== INICIANDO EXTRACCIÓN UNIVERSAL =====")
    print(f"DEBUG: Longitud del texto: {len(fuente_texto) if fuente_texto else 0} caracteres")
    
    # Extractor universal de valores financieros
    valores_pdf = {}
    
    # DEBUG: Mostrar una muestra del texto para diagnóstico
    if fuente_texto:
        # Mostrar las líneas que contienen números monetarios
        lineas_con_numeros = []
        for i, linea in enumerate(fuente_texto.split('\n')):
            if re.search(r'[0-9]+[.,][0-9]{2}', linea):
                lineas_con_numeros.append(f"L{i}: {linea.strip()}")
        print(f"DEBUG: Líneas con números (primeras 10): {lineas_con_numeros[:10]}")
        print(f"DEBUG: Líneas con números (últimas 10): {lineas_con_numeros[-10:]}")
    
    # ESTRATEGIA 1: Desde pdf_fields (primera prioridad)
    if pdf_fields:
        print(f"DEBUG: pdf_fields keys: {list(pdf_fields.keys())}")
        if "importeTotal" in pdf_fields:
            valores_pdf["total_declarado"] = float(pdf_fields["importeTotal"])
            print(f"DEBUG: Total desde pdf_fields: {valores_pdf['total_declarado']}")
        if "subtotal" in pdf_fields:
            valores_pdf["subtotal"] = float(pdf_fields["subtotal"])
            print(f"DEBUG: Subtotal desde pdf_fields: {valores_pdf['subtotal']}")
        if "iva" in pdf_fields:
            valores_pdf["iva"] = float(pdf_fields["iva"])
            print(f"DEBUG: IVA desde pdf_fields: {valores_pdf['iva']}")
        if "descuento" in pdf_fields:
            valores_pdf["descuentos"] = float(pdf_fields["descuento"])
    
    # ESTRATEGIA 2: Extracción agresiva del texto (cualquier formato)
    if fuente_texto:
        print(f"DEBUG MATH_CONSISTENCY: Analizando texto con {len(fuente_texto)} caracteres...")
        
        # === PATRONES UNIVERSALES PARA SUBTOTAL ===
        if "subtotal" not in valores_pdf or valores_pdf["subtotal"] == 0:
            subtotal_patterns = [
                # Formatos ecuatorianos estándar
                r"subtotal\s*(?:sin\s*)?(?:impuestos?)?\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"subtotal\s*(?:15%|0%)?\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"base\s*imponible\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                # Búsqueda por posición (después de palabras clave)
                r"sin\s*impuestos\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"(?:^|\n)\s*([0-9]+[.,][0-9]{2})\s*(?=\n|$)",  # Números aislados
                # Contexto de tabla
                r"subtotal.*?([0-9]+[.,][0-9]{2})",
            ]
            
            for i, pattern in enumerate(subtotal_patterns):
                print(f"DEBUG: Probando patrón subtotal {i}: {pattern}")
                matches = re.finditer(pattern, fuente_texto, re.I | re.M)
                matches_list = list(matches)
                print(f"DEBUG: Patrón {i} encontró {len(matches_list)} coincidencias")
                for match in matches_list:
                    try:
                        val = float(match.group(1).replace(",", "."))
                        print(f"DEBUG: Patrón {i} - Valor: {val}, Texto: '{match.group(0).strip()}'")
                        # Rango realista para subtotal
                        if 0.1 <= val <= 10000.0:
                            valores_pdf["subtotal"] = val
                            print(f"DEBUG: ✅ Subtotal ACEPTADO (patrón {i}): {val}")
                            break
                        else:
                            print(f"DEBUG: ❌ Subtotal RECHAZADO (fuera de rango): {val}")
                    except Exception as e:
                        print(f"DEBUG: ❌ Error procesando subtotal: {e}")
                        continue
                if "subtotal" in valores_pdf:
                    break
        
        # === PATRONES UNIVERSALES PARA IVA ===
        if "iva" not in valores_pdf or valores_pdf["iva"] == 0:
            iva_patterns = [
                # IVA específico ecuatoriano
                r"iva\s*(?:15%?|12%?)?\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"i\.?v\.?a\.?\s*(?:15%?)?\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"impuesto\s*(?:valor\s*agregado)?\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                # Después de porcentajes
                r"15%\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"12%\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                # Por contexto de tabla
                r"iva.*?([0-9]+[.,][0-9]{2})",
            ]
            
            for i, pattern in enumerate(iva_patterns):
                print(f"DEBUG: Probando patrón IVA {i}: {pattern}")
                matches = re.finditer(pattern, fuente_texto, re.I | re.M)
                matches_list = list(matches)
                print(f"DEBUG: Patrón IVA {i} encontró {len(matches_list)} coincidencias")
                for match in matches_list:
                    try:
                        val = float(match.group(1).replace(",", "."))
                        print(f"DEBUG: Patrón IVA {i} - Valor: {val}, Texto: '{match.group(0).strip()}'")
                        # Rango realista para IVA
                        if 0.0 <= val <= 5000.0:
                            valores_pdf["iva"] = val
                            print(f"DEBUG: ✅ IVA ACEPTADO (patrón {i}): {val}")
                            break
                        else:
                            print(f"DEBUG: ❌ IVA RECHAZADO (fuera de rango): {val}")
                    except Exception as e:
                        print(f"DEBUG: ❌ Error procesando IVA: {e}")
                        continue
                if "iva" in valores_pdf:
                    break
        
        # === PATRONES UNIVERSALES PARA TOTAL ===
        if "total_declarado" not in valores_pdf or valores_pdf["total_declarado"] == 0:
            total_patterns = [
                # Formatos estándar ecuatorianos MÁS ESPECÍFICOS
                r"valor\s*total\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"total\s*a\s*pagar\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"importe\s*total\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                r"gran\s*total\s*:?\s*\$?\s*([0-9]+[.,][0-9]{1,2})",
                # ESPECÍFICO para facturas con formato de tabla
                r"valor\s*total\s*\|?\s*([0-9]+[.,][0-9]{2})",
                r"total\s*\|\s*([0-9]+[.,][0-9]{2})",
                # Buscar en contexto de líneas finales de tabla
                r"total.*?([0-9]+[.,][0-9]{2})",
                # ESPECÍFICO: Números de 2-3 dígitos con decimales en posición de total
                r"(?:^|\n|\s)([2-9][0-9][.,][0-9]{2})(?:\s*\n|$|\s*$)",  # 20.00-99.99
                r"(?:^|\n|\s)([1-9][0-9]{2}[.,][0-9]{2})(?:\s*\n|$|\s*$)",  # 100.00-999.99
                # Búsqueda muy agresiva al final del documento
                r"(?:^|\n)\s*([0-9]{1,3}[.,][0-9]{2})\s*(?:\n|$)",
            ]
            
            valores_totales_candidatos = []
            for i, pattern in enumerate(total_patterns):
                matches = re.finditer(pattern, fuente_texto, re.I | re.M)
                for match in matches:
                    try:
                        val = float(match.group(1).replace(",", "."))
                        # Rango realista para total
                        if 0.1 <= val <= 15000.0:
                            valores_totales_candidatos.append({
                                "valor": val,
                                "patron": i,
                                "texto": match.group(0).strip()
                            })
                            print(f"DEBUG: Total candidato (patrón {i}): {val} de '{match.group(0).strip()}'")
                    except:
                        continue
            
            # Seleccionar el total más probable
            if valores_totales_candidatos:
                # Priorizar patrones específicos (primeros en la lista)
                valores_totales_candidatos.sort(key=lambda x: (x["patron"], -x["valor"]))
                total_seleccionado = valores_totales_candidatos[0]["valor"]
                valores_pdf["total_declarado"] = total_seleccionado
                print(f"DEBUG: Total seleccionado: {total_seleccionado}")
                
                # Detectar múltiples totales (posible manipulación)
                valores_unicos = list(set([c["valor"] for c in valores_totales_candidatos]))
                if len(valores_unicos) > 1:
                    valores_unicos.sort()
                    print(f"DEBUG: ⚠️ MÚLTIPLES TOTALES: {valores_unicos}")
                    resultado["anomalias_detectadas"].append(f"Múltiples valores de total detectados: {valores_unicos}")
    
    # ESTRATEGIA 3: Usar datos de validación financiera como fallback
    subtotal = valores_pdf.get("subtotal", 0.0)
    iva = valores_pdf.get("iva", 0.0)
    total_declarado = valores_pdf.get("total_declarado", 0.0)
    descuentos = valores_pdf.get("descuentos", 0.0)
    
    # FALLBACK FINAL: Si aún faltan valores, usar las últimas líneas numéricas del PDF
    if (subtotal == 0 or iva == 0) and fuente_texto:
        print("DEBUG: Fallback final - usando últimas líneas numéricas")
        lineas = fuente_texto.split('\n')
        ultimos_numeros = []
        
        # Buscar en las últimas 20 líneas (donde suelen estar los totales)
        for linea in lineas[-20:]:
            numeros = re.findall(r'([0-9]+[.,][0-9]{2})', linea)
            for num in numeros:
                try:
                    val = float(num.replace(",", "."))
                    if 0.01 <= val <= 100.0:
                        ultimos_numeros.append(val)
                except:
                    continue
        
        # Usar los valores típicos de facturas ecuatorianas
        ultimos_unicos = sorted(list(set(ultimos_numeros)))
        print(f"DEBUG: Últimos números únicos: {ultimos_unicos}")
        
        if len(ultimos_unicos) >= 3:
            # IVA suele ser el más pequeño > 0.01
            if iva == 0:
                candidatos_iva = [v for v in ultimos_unicos if 0.01 <= v <= 5.0]
                if candidatos_iva:
                    iva = min(candidatos_iva)
                    valores_pdf["iva"] = iva
                    print(f"DEBUG: IVA fallback: {iva}")
            
            # Subtotal suele estar cerca del total
            if subtotal == 0 and total_declarado > 0:
                candidatos_subtotal = [v for v in ultimos_unicos if abs(v - total_declarado) <= total_declarado * 0.2]
                if candidatos_subtotal:
                    subtotal = max([v for v in candidatos_subtotal if v < total_declarado], default=0)
                    if subtotal > 0:
                        valores_pdf["subtotal"] = subtotal
                        print(f"DEBUG: Subtotal fallback: {subtotal}")
    
    # Si los valores del PDF fallan, usar los de validación financiera (sin SRI) como referencia
    if (subtotal == 0 or iva == 0 or total_declarado == 0) and pdf_fields:
        print("DEBUG: Usando valores de pdf_fields como fallback final")
        if "subtotal" in pdf_fields and subtotal == 0:
            subtotal = float(pdf_fields["subtotal"])
            valores_pdf["subtotal"] = subtotal
            print(f"DEBUG: Subtotal desde pdf_fields: {subtotal}")
        if "iva" in pdf_fields and iva == 0:
            iva = float(pdf_fields["iva"])
            valores_pdf["iva"] = iva
            print(f"DEBUG: IVA desde pdf_fields: {iva}")
        if "importeTotal" in pdf_fields and total_declarado == 0:
            total_declarado = float(pdf_fields["importeTotal"])
            valores_pdf["total_declarado"] = total_declarado
            print(f"DEBUG: Total desde pdf_fields: {total_declarado}")
    
    # Si tenemos total pero no subtotal, intentar inferir
    if total_declarado > 0 and subtotal == 0:
        if iva > 0:
            # Inferir subtotal: total - iva
            subtotal_inferido = total_declarado - iva
            if subtotal_inferido > 0:
                subtotal = subtotal_inferido
                valores_pdf["subtotal"] = subtotal
                print(f"DEBUG: Subtotal inferido: {subtotal} (total - iva)")
        else:
            # Asumir que el total es subtotal + 15% de IVA
            subtotal_inferido = total_declarado / 1.15
            iva_inferido = total_declarado - subtotal_inferido
            if subtotal_inferido > 0:
                subtotal = subtotal_inferido
                iva = iva_inferido
                valores_pdf["subtotal"] = subtotal
                valores_pdf["iva"] = iva
                print(f"DEBUG: Valores inferidos - Subtotal: {subtotal}, IVA: {iva}")
    
    # Si tenemos subtotal pero no IVA, intentar inferir
    if subtotal > 0 and iva == 0 and total_declarado > subtotal:
        iva_inferido = total_declarado - subtotal
        if iva_inferido > 0:
            iva = iva_inferido
            valores_pdf["iva"] = iva
            print(f"DEBUG: IVA inferido: {iva} (total - subtotal)")
    
    # ESTRATEGIA 4: Búsqueda exhaustiva de números sospechosos
    if fuente_texto:
        print("DEBUG: Búsqueda exhaustiva de números...")
        lineas = fuente_texto.split('\n')
        numeros_encontrados = []
        numeros_sospechosos = []
        
        for i, linea in enumerate(lineas):
            # Buscar TODOS los números monetarios en cada línea
            numeros = re.findall(r'([0-9]+[.,][0-9]{2})', linea)
            for num in numeros:
                try:
                    val = float(num.replace(",", "."))
                    if 0.1 <= val <= 15000.0:
                        numeros_encontrados.append({
                            "valor": val,
                            "linea": i,
                            "contexto": linea.strip()
                        })
                        
                        # Detectar números que son REALMENTE candidatos a total
                        # SOLO incluir líneas que contengan palabras indicativas de TOTAL
                        linea_lower = linea.lower()
                        
                        # Palabras que indican que es un TOTAL real
                        es_total_real = any(palabra in linea_lower for palabra in [
                            "valor total", "total", "gran total", "importe total",
                            "total a pagar", "forma pago", "tarjeta", "efectivo", "credito"
                        ])
                        
                        # Excluir explícitamente líneas que NO son totales
                        es_numero_irrelevante = any(palabra in linea_lower for palabra in [
                            "deducible", "descuento", "documento", "interno", "folio", 
                            "email", "direccion", "telefono", "contribuyente", "ruc",
                            "cantidad", "precio", "unitario", "codigo", "subtotal",
                            "iva", "impuesto", "medicinas", "alimentos"
                        ])
                        
                        # SOLO incluir si es explícitamente un total Y no es irrelevante
                        if es_total_real and not es_numero_irrelevante and 20.0 <= val <= 100.0:
                            numeros_sospechosos.append({
                                "valor": val,
                                "linea": i,
                                "contexto": linea.strip(),
                                "es_total_candidato": True
                            })
                            print(f"DEBUG: ✅ Total candidato válido: {val} en '{linea.strip()}'")
                        elif 20.0 <= val <= 100.0:
                            print(f"DEBUG: ❌ Número excluido: {val} en '{linea.strip()}' (es_total_real={es_total_real}, es_irrelevante={es_numero_irrelevante})")
                except:
                    continue
        
        # Ordenar por línea y buscar patrones
        numeros_encontrados.sort(key=lambda x: x["linea"])
        numeros_sospechosos.sort(key=lambda x: x["linea"])
        
        print(f"DEBUG: Números encontrados ({len(numeros_encontrados)}): {[n['valor'] for n in numeros_encontrados[-10:]]}")
        print(f"DEBUG: Números sospechosos de total ({len(numeros_sospechosos)}): {[n['valor'] for n in numeros_sospechosos]}")
        
        # Si no tenemos total, buscar candidatos
        if total_declarado == 0 and numeros_sospechosos:
            # Priorizar números hacia el final del documento
            candidatos_finales = [n for n in numeros_sospechosos if n["linea"] > len(lineas) * 0.7]
            if candidatos_finales:
                total_candidato = candidatos_finales[-1]["valor"]  # Último del final
                valores_pdf["total_declarado"] = total_candidato
                total_declarado = total_candidato
                print(f"DEBUG: Total candidato por posición final: {total_candidato}")
            elif numeros_sospechosos:
                # Si no hay en la parte final, tomar el último número sospechoso
                total_candidato = numeros_sospechosos[-1]["valor"]
                valores_pdf["total_declarado"] = total_candidato
                total_declarado = total_candidato
                print(f"DEBUG: Total candidato por último sospechoso: {total_candidato}")
        
        # CORRECCIÓN INTELIGENTE: Usar valores sospechosos detectados
        if numeros_sospechosos:
            print(f"DEBUG: 🔧 CORRECCIÓN INTELIGENTE usando números sospechosos")
            
            # Inferir valores usando los números sospechosos (ordenados por línea)
            valores_candidatos = [n["valor"] for n in numeros_sospechosos]
            valores_candidatos.sort()  # Ordenar de menor a mayor
            
            print(f"DEBUG: Valores candidatos ordenados: {valores_candidatos}")
            
            # LÓGICA: En facturas ecuatorianas típicas:
            # - El más pequeño suele ser IVA
            # - El del medio suele ser subtotal  
            # - El más grande suele ser total
            
            if len(valores_candidatos) >= 3:
                # Si tenemos 3+ valores, usar heurística
                iva_candidato = min(valores_candidatos)  # El más pequeño
                total_candidato = max(valores_candidatos)  # El más grande
                # Subtotal: buscar uno que sea aprox total/1.15 o total-iva
                for val in valores_candidatos:
                    if abs(val - (total_candidato - iva_candidato)) < 0.5:
                        subtotal_candidato = val
                        break
                else:
                    subtotal_candidato = valores_candidatos[-2]  # Segundo más grande
                
                # Actualizar valores si son coherentes o usar heurística
                # Para IVA: buscar el valor más pequeño en el rango 0.01-5.0
                candidatos_iva = [v for v in valores_candidatos if 0.01 <= v <= 5.0]
                if candidatos_iva:
                    iva = min(candidatos_iva)  # El más pequeño suele ser IVA
                    valores_pdf["iva"] = iva
                    print(f"DEBUG: 🔧 IVA corregido: {iva}")
                
                # Para subtotal: buscar uno que sea coherente con total-iva
                candidatos_subtotal = [v for v in valores_candidatos if 15.0 <= v <= 50.0]
                if candidatos_subtotal:
                    # Preferir el que más se acerque a total - iva
                    total_menos_iva = total_candidato - (iva if 'iva' in locals() else 0)
                    subtotal = min(candidatos_subtotal, key=lambda x: abs(x - total_menos_iva))
                    valores_pdf["subtotal"] = subtotal
                    print(f"DEBUG: 🔧 Subtotal corregido: {subtotal}")
                
                if 20.0 <= total_candidato <= 100.0:
                    # AQUÍ detectamos manipulación SOLO si hay múltiples totales DIFERENTES
                    totales_detectados = [v for v in valores_candidatos if v >= total_candidato - 5.0]
                    valores_unicos_totales = list(set(totales_detectados))
                    
                    # Solo alertar si hay MÁS DE UN valor diferente (no duplicados del mismo valor)
                    if len(valores_unicos_totales) > 1:
                        diferencia_maxima = max(valores_unicos_totales) - min(valores_unicos_totales)
                        # Solo alertar si la diferencia es significativa (>$1)
                        if diferencia_maxima > 1.0:
                            print(f"DEBUG: 🚨 MÚLTIPLES TOTALES DIFERENTES: {valores_unicos_totales}")
                            resultado["errores"].append(f"⚠️ MÚLTIPLES TOTALES DIFERENTES DETECTADOS: {valores_unicos_totales} - Posible manipulación")
                            # Usar el más alto como sospechoso
                            total_declarado = max(valores_unicos_totales)
                        else:
                            print(f"DEBUG: ✅ Totales similares (diferencia mínima: ${diferencia_maxima:.2f})")
                            total_declarado = total_candidato
                    else:
                        print(f"DEBUG: ✅ Total único o duplicado legítimo: {total_candidato}")
                        total_declarado = total_candidato
                        
                    valores_pdf["total_declarado"] = total_declarado
                    print(f"DEBUG: 🔧 Total corregido: {total_declarado}")
        
        # BÚSQUEDA ESPECÍFICA para valores como 33.15 (manipulados)
        if total_declarado < 30.0:  # Si el total detectado es bajo, buscar valores más altos
            valores_altos = [n for n in numeros_encontrados if n["valor"] > 25.0]
            if valores_altos:
                print(f"DEBUG: ⚠️ VALORES ALTOS DETECTADOS (posible manipulación): {[v['valor'] for v in valores_altos]}")
                # Agregar como anomalía
                valores_manipulados = [v["valor"] for v in valores_altos]
                resultado["anomalias_detectadas"].append(f"Valores anómalamente altos detectados: {valores_manipulados}")
                
                # Si encontramos un valor significativamente mayor, es sospechoso
                valor_mas_alto = max(valores_altos, key=lambda x: x["valor"])
                if valor_mas_alto["valor"] > total_declarado * 1.2:  # 20% mayor
                    resultado["errores"].append(f"⚠️ VALOR SOSPECHOSO DETECTADO: ${valor_mas_alto['valor']:.2f} vs total ${total_declarado:.2f}")
                    print(f"DEBUG: 🚨 MANIPULACIÓN DETECTADA: {valor_mas_alto['valor']} vs {total_declarado}")
    
    # Actualizar resultado con valores extraídos
    resultado["validacion_formula"]["componentes"] = {
        "subtotal": subtotal,
        "iva": iva,
        "descuentos": descuentos,
        "retenciones": 0.0,
        "propina": 0.0,
        "total_calculado": subtotal + iva - descuentos,
        "total_declarado": total_declarado
    }
    
    # Evaluar fórmula matemática
    total_calculado = subtotal + iva - descuentos
    diferencia = abs(total_calculado - total_declarado)
    tolerancia = 0.05  # Aumentar tolerancia para diferentes formatos
    
    resultado["validacion_formula"]["formula_correcta"] = diferencia <= tolerancia
    resultado["validacion_formula"]["diferencia"] = diferencia
    resultado["validacion_formula"]["tolerancia"] = tolerancia
    
    if diferencia > tolerancia:
        resultado["errores"].append(f"Fórmula PDF incorrecta: {subtotal:.2f} + {iva:.2f} - {descuentos:.2f} = {total_calculado:.2f}, pero declara {total_declarado:.2f}")
    
    # Detección de manipulación visual
    pdf_total_extraido = pdf_fields.get("importeTotal", 0) if pdf_fields else 0
    if pdf_total_extraido != total_declarado and abs(pdf_total_extraido - total_declarado) > 0.1:
        diferencia_manipulacion = abs(pdf_total_extraido - total_declarado)
        resultado["errores"].append(f"⚠️ POSIBLE MANIPULACIÓN VISUAL: PDF muestra ${total_declarado:.2f} pero extrae ${pdf_total_extraido:.2f} (diferencia: ${diferencia_manipulacion:.2f})")
        resultado["anomalias_detectadas"].append(f"Discrepancia entre valor visual (${total_declarado:.2f}) y valor extraído (${pdf_total_extraido:.2f})")
    
    # Evaluar coherencia de IVA
    if subtotal > 0 and iva > 0:
        porcentaje_iva = (iva / subtotal) * 100
        resultado["validacion_impuestos"]["porcentaje_detectado"] = porcentaje_iva
        
        # Verificar si es IVA estándar ecuatoriano (15%, 12%, 0%)
        iva_coherente = (abs(porcentaje_iva - 15) <= 2.0 or 
                        abs(porcentaje_iva - 12) <= 2.0 or 
                        abs(porcentaje_iva) <= 0.5)
        resultado["validacion_impuestos"]["iva_coherente"] = iva_coherente
        
        if not iva_coherente:
            resultado["errores"].append(f"IVA no estándar: {porcentaje_iva:.2f}% (esperado: 0%, 12% o 15%)")
    
    print(f"DEBUG MATH_CONSISTENCY: ===== RESUMEN EXTRACCIÓN =====")
    print(f"DEBUG: Subtotal: {subtotal}, IVA: {iva}, Total: {total_declarado}")
    print(f"DEBUG: Fórmula válida: {resultado['validacion_formula']['formula_correcta']}")
    print(f"DEBUG: Diferencia: {diferencia:.3f} (tolerancia: {tolerancia})")
    print(f"DEBUG MATH_CONSISTENCY: ===== FIN EXTRACCIÓN =====")


def _evaluar_items_desde_pdf(detalles: List[Dict[str, Any]], resultado: Dict[str, Any]):
    """Evalúa ítems extraídos directamente del PDF."""
    if not detalles:
        return
    
    items_validos = 0
    items_con_errores = []
    subtotal_calculado = 0.0
    
    for i, item in enumerate(detalles):
        if item.get("DEBUG_INFO"):  # Saltar items de debug
            continue
            
        try:
            # Extraer valores desde el text_sample si está disponible
            text_sample = item.get("text_sample", "")
            if text_sample:
                # Buscar números en el text_sample
                import re
                numeros = re.findall(r'\b\d+\.\d{2}\b', text_sample)
                if len(numeros) >= 2:
                    # Asumir que el último número es el total del item
                    precio_total = float(numeros[-1])
                    subtotal_calculado += precio_total
                    items_validos += 1
                    continue
        except:
            pass
        
        # Si no pudimos extraer del text_sample, marcar como error
        items_con_errores.append({
            "item": i,
            "error": "No se pudo extraer información financiera del item PDF"
        })
    
    resultado["validacion_items"]["items_analizados"] = len(detalles) - sum(1 for d in detalles if d.get("DEBUG_INFO"))
    resultado["validacion_items"]["items_validos"] = items_validos
    resultado["validacion_items"]["items_con_errores"] = items_con_errores
    resultado["validacion_items"]["subtotal_calculado"] = subtotal_calculado


def _calcular_metrica_consistencia(resultado: Dict[str, Any]) -> int:
    """Calcula métrica final de consistencia (0-100)"""
    
    score = 100
    
    # Penalizaciones por errores
    num_errores = len(resultado["errores"])
    score -= num_errores * 15  # 15 puntos por error
    
    # Penalizaciones por advertencias
    num_advertencias = len(resultado["advertencias"])
    score -= num_advertencias * 5  # 5 puntos por advertencia
    
    # Penalizaciones por anomalías
    num_anomalias = len(resultado["anomalias_detectadas"])
    score -= num_anomalias * 10  # 10 puntos por anomalía
    
    # Bonus por validaciones exitosas
    if resultado["validacion_formula"]["formula_correcta"]:
        score += 5
    
    if resultado["validacion_impuestos"]["iva_coherente"]:
        score += 5
    
    # Bonus por items válidos
    items = resultado["validacion_items"]
    if items["items_analizados"] > 0:
        porcentaje_validos = (items["items_validos"] / items["items_analizados"]) * 100
        if porcentaje_validos >= 95:
            score += 10
        elif porcentaje_validos >= 80:
            score += 5
    
    return max(0, min(100, score))


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
    
    # Análisis de texto - manejar tanto bool como dict
    if isinstance(text_overlapping, bool):
        if text_overlapping:
            reporte.append("🟡 SUPERPOSICIÓN DE TEXTO DETECTADA (análisis básico)")
        else:
            reporte.append("✅ No se detectó superposición de texto")
    else:
        if text_overlapping.get("has_overlapping", False):
            reporte.append("🟡 SUPERPOSICIÓN DE TEXTO DETECTADA:")
            
            if text_overlapping.get("duplicate_lines"):
                reporte.append(f"   Líneas duplicadas: {len(text_overlapping['duplicate_lines'])}")
                for line, count in list(text_overlapping["duplicate_lines"].items())[:3]:
                    reporte.append(f"   - '{line[:50]}...' aparece {count} veces")
            
            if text_overlapping.get("similar_lines"):
                reporte.append(f"   Líneas similares: {len(text_overlapping['similar_lines'])}")
                for line1, line2, sim in text_overlapping["similar_lines"][:2]:
                    reporte.append(f"   - Similitud {sim:.1%}: '{line1[:30]}...' ≈ '{line2[:30]}...'")
            
            if text_overlapping.get("suspicious_formatting"):
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
 
        
        doc = fitz.open(pdf_path)
        structure_analysis = _analyze_pdf_structure_layers(doc)
        doc.close()
        
        # Generar reporte
        reporte = generar_reporte_capas(layers_analysis, text_overlapping, structure_analysis)
        
        return {
            "archivo": pdf_path,
            "tiene_capas": layers_analysis["has_layers"],
            "confianza_total": layers_analysis["confidence"],
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