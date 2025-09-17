import base64
import io
import re
import time
import json
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pdfminer.high_level import extract_text
from difflib import SequenceMatcher
import requests

from config import (
    MAX_PDF_BYTES,
    SRI_TIMEOUT,
    PRICE_EPS,
    QTY_EPS,
    TOTAL_EPS,
    MATCH_THRESHOLD,
)
from utils import log_step, normalize_comprobante_xml, strip_accents, _to_float
from pdf_extract import extract_clave_acceso_from_text, extract_invoice_fields_from_text
from ocr import easyocr_text_from_pdf, HAS_EASYOCR
from sri import sri_autorizacion_por_clave, parse_autorizacion_response, factura_xml_to_json
from riesgo import evaluar_riesgo_factura, detectar_texto_sobrepuesto_avanzado

import fitz  # para chequeo de PDF escaneado


router = APIRouter()


class Peticion(BaseModel):
    pdfbase64: str


def is_scanned_image_pdf(pdf_bytes: bytes, extracted_text: str) -> bool:
    """Copia local para validar si un PDF es escaneado (poco texto + imágenes)."""
    text_len = len((extracted_text or "").strip())
    little_text = text_len < 50
    try:
        sample = pdf_bytes[: min(len(pdf_bytes), 2_000_000)]
        img_hits = len(re.findall(rb"/Subtype\s*/Image", sample)) or len(re.findall(rb"/Image\b", sample))
        has_image_objs = img_hits > 0
    except Exception:
        has_image_objs = False
    return little_text and has_image_objs


@router.post("/validar-factura")
async def validar_factura(req: Peticion):
    t_all = time.perf_counter()

    # 1) decode base64
    t0 = time.perf_counter()
    try:
        pdf_bytes = base64.b64decode(req.pdfbase64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="El campo 'pdfbase64' no es base64 válido.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail=f"El PDF excede el tamaño máximo permitido ({MAX_PDF_BYTES} bytes).")
    log_step("1) decode base64", t0)

    # 2) texto directo con pdfminer
    t0 = time.perf_counter()
    try:
        text = extract_text(io.BytesIO(pdf_bytes))
    except Exception:
        text = ""
    log_step("2) extract_text(pdfminer)", t0)

    # 3) clave de acceso
    clave, etiqueta_encontrada = extract_clave_acceso_from_text(text or "")
    ocr_text = ""
    if not etiqueta_encontrada and is_scanned_image_pdf(pdf_bytes, text or "") and HAS_EASYOCR:
        t_ocr = time.perf_counter()
        ocr_text = easyocr_text_from_pdf(pdf_bytes)
        log_step("3b) EasyOCR total", t_ocr)
        clave_ocr, etiqueta_ocr = extract_clave_acceso_from_text(ocr_text or "")
        if etiqueta_ocr and clave_ocr:
            clave = clave_ocr
            etiqueta_encontrada = True

    fuente_texto = text if text and not is_scanned_image_pdf(pdf_bytes, text) else (ocr_text or text)

    # 4) extraer campos del PDF
    pdf_fields = extract_invoice_fields_from_text(fuente_texto or "", clave)
    pdf_fields_b64 = base64.b64encode(json.dumps(pdf_fields, ensure_ascii=False).encode("utf-8")).decode("utf-8")

    # Si no hay clave válida → ejecutar riesgo con sri_ok=False
    if not etiqueta_encontrada or not clave or not re.fullmatch(r"\d{49}", str(clave)):
        riesgo = evaluar_riesgo_factura(pdf_bytes, fuente_texto or "", pdf_fields, sri_ok=False)
        log_step("TOTAL (RIESGO sin clave)", t_all)
        return JSONResponse(
            status_code=200,
            content={
                "sri_verificado": False,
                "mensaje": "No se pudo obtener una Clave de Acceso válida del PDF. Se ejecutó evaluación de riesgo.",
                "riesgo": riesgo,
                "pdfFacturaJsonB64": pdf_fields_b64,
                "claveAccesoDetectada": clave if clave and re.fullmatch(r'\d{49}', str(clave)) else None
            }
        )

    # 5) consulta al SRI
    t0 = time.perf_counter()
    try:
        resp = sri_autorizacion_por_clave(clave, timeout=SRI_TIMEOUT)
        print(f"[DEBUG] SRI Response tipo: {type(resp)}")
        print(f"[DEBUG] SRI Response contenido: {resp}")
    except requests.exceptions.Timeout:
        riesgo = evaluar_riesgo_factura(pdf_bytes, fuente_texto or "", pdf_fields, sri_ok=False)
        return JSONResponse(
            status_code=200,
            content={
                "sri_verificado": False,
                "mensaje": f"Timeout consultando SRI (>{SRI_TIMEOUT:.0f}s). Se ejecutó evaluación de riesgo.",
                "riesgo": riesgo,
                "pdfFacturaJsonB64": pdf_fields_b64,
                "claveAccesoDetectada": clave
            }
        )
    except Exception as e:
        print(f"[DEBUG] Error al consultar SRI: {e}")
        riesgo = evaluar_riesgo_factura(pdf_bytes, fuente_texto or "", pdf_fields, sri_ok=False)
        return JSONResponse(
            status_code=200,
            content={
                "sri_verificado": False,
                "mensaje": f"Error consultando SRI: {str(e)}",
                "riesgo": riesgo,
                "pdfFacturaJsonB64": pdf_fields_b64,
                "claveAccesoDetectada": clave
            }
        )
    log_step("4) SRI autorizacion", t0)

    ok_aut, estado, xml_comprobante, raw = parse_autorizacion_response(resp)
    
    # DEBUG: logs detallados del parseo
    print(f"[DEBUG] parse_autorizacion_response resultado:")
    print(f"[DEBUG]   ok_aut: {ok_aut}")
    print(f"[DEBUG]   estado: '{estado}'")
    print(f"[DEBUG]   xml_comprobante presente: {xml_comprobante is not None}")
    print(f"[DEBUG]   raw: {raw}")
    
    if not ok_aut:
        print(f"[DEBUG] Comprobante NO autorizado. Estado: '{estado}'")
        riesgo = evaluar_riesgo_factura(pdf_bytes, fuente_texto or "", pdf_fields, sri_ok=False)
        return JSONResponse(
            status_code=200,
            content={
                "sri_verificado": False,
                "mensaje": f"El comprobante no está AUTORIZADO en el SRI. Estado: '{estado}'",
                "sri_estado": estado,
                "riesgo": riesgo,
                "pdfFacturaJsonB64": pdf_fields_b64,
                "respuesta": raw,
                "claveAccesoDetectada": clave,
                "textoAnalizado": fuente_texto,
                "debug_info": {
                    "ok_aut": ok_aut,
                    "estado_recibido": estado,
                    "tiene_xml": xml_comprobante is not None
                }
            }
        )

    # 6) parsear XML del SRI
    xml_src = normalize_comprobante_xml(xml_comprobante)
    try:
        sri_json = factura_xml_to_json(xml_src)
    except Exception as e:
        riesgo = evaluar_riesgo_factura(pdf_bytes, fuente_texto or "", pdf_fields, sri_ok=True)
        return JSONResponse(status_code=200, content={
            "sri_verificado": True,
            "mensaje": "AUTORIZADO en el SRI, pero no se pudo convertir a JSON.",
            "detalle": str(e),
            "facturaXML": xml_src,
            "respuesta": raw,
            "riesgo": riesgo,
            "pdfFacturaJsonB64": pdf_fields_b64,
            "claveAccesoDetectada": clave
        })

    # --------- Comparación cabecera ----------
    sri_fields = {
        "ruc": (sri_json.get("infoTributaria") or {}).get("ruc"),
        "razonSocial": (sri_json.get("infoTributaria") or {}).get("razonSocial"),
        "fechaEmision": (sri_json.get("infoFactura") or {}).get("fechaEmision"),
        "importeTotal": (sri_json.get("infoFactura") or {}).get("importeTotal"),
        "claveAcceso": (sri_json.get("infoTributaria") or {}).get("claveAcceso"),
    }

    def _norm_name(s):
        return re.sub(r"\s+", " ", strip_accents((s or "").strip())).upper()

    diferencias: Dict[str, Dict[str, Any]] = {}
    if sri_fields["ruc"] and pdf_fields.get("ruc") and sri_fields["ruc"] != pdf_fields["ruc"]:
        diferencias["ruc"] = {"sri": sri_fields["ruc"], "pdf": pdf_fields["ruc"]}

    if sri_fields["fechaEmision"] and pdf_fields.get("fechaEmision"):
        s_sri = str(sri_fields["fechaEmision"]).replace("-", "/")
        s_pdf = str(pdf_fields["fechaEmision"]).replace("-", "/")
        if s_sri != s_pdf:
            diferencias["fechaEmision"] = {"sri": s_sri, "pdf": s_pdf}

    if sri_fields["importeTotal"] is not None and pdf_fields.get("importeTotal") is not None:
        s = float(sri_fields["importeTotal"])
        p = float(pdf_fields["importeTotal"])
        if abs(s - p) > PRICE_EPS:
            diferencias["importeTotal"] = {"sri": s, "pdf": p}

    if sri_fields["razonSocial"] and pdf_fields.get("razonSocial"):
        if _norm_name(sri_fields["razonSocial"]) != _norm_name(pdf_fields["razonSocial"]):
            diferencias["razonSocial"] = {"sri": sri_fields["razonSocial"], "pdf": pdf_fields["razonSocial"]}

    if sri_fields["claveAcceso"] and pdf_fields.get("claveAcceso") and sri_fields["claveAcceso"] != pdf_fields["claveAcceso"]:
        diferencias["claveAcceso"] = {"sri": sri_fields["claveAcceso"], "pdf": pdf_fields["claveAcceso"]}

    # --------- Comparación de productos ----------
    sri_items = sri_json.get("detalles") or []
    pdf_items = pdf_fields.get("detalles") or []

    def sim(a: str, b: str) -> float:
        return SequenceMatcher(None, _norm_name(a), _norm_name(b)).ratio()

    emparejamientos = []
    usados_pdf = set()
    for i, s in enumerate(sri_items):
        best_j, best_score = None, -1.0
        for j, p in enumerate(pdf_items):
            if j in usados_pdf:
                continue
            sc = sim(s.get("descripcion", ""), p.get("descripcion", ""))
            if sc > best_score:
                best_j, best_score = j, sc
        if best_j is not None and best_score >= MATCH_THRESHOLD:
            usados_pdf.add(best_j)
            emparejamientos.append((i, best_j, best_score))
        else:
            emparejamientos.append((i, None, 0.0))

    diferenciasProductos: List[Dict[str, Any]] = []
    for (i, j, score) in emparejamientos:
        s = sri_items[i]
        if j is None:
            diferenciasProductos.append({
                "descripcion_sri": s.get("descripcion"),
                "match": "no_encontrado_en_pdf"
            })
            continue
        p = pdf_items[j]
        dif: Dict[str, Any] = {}
        s_qty = _to_float(s.get("cantidad"))
        p_qty = _to_float(p.get("cantidad"))
        if s_qty is not None and p_qty is not None and abs(s_qty - p_qty) > QTY_EPS:
            dif["cantidad"] = {"sri": s_qty, "pdf": p_qty}
        s_unit = _to_float(s.get("precioUnitario"))
        p_unit = _to_float(p.get("precioUnitario"))
        if s_unit is not None and p_unit is not None and abs(s_unit - p_unit) > PRICE_EPS:
            dif["precioUnitario"] = {"sri": s_unit, "pdf": p_unit}
        s_tot = _to_float(s.get("precioTotalSinImpuesto"))
        p_tot = _to_float(p.get("precioTotal"))
        if s_tot is not None and p_tot is not None and abs(s_tot - p_tot) > TOTAL_EPS:
            dif["precioTotal"] = {"sri": s_tot, "pdf": p_tot}
        if dif:
            diferenciasProductos.append({
                "descripcion_sri": s.get("descripcion"),
                "descripcion_pdf": p.get("descripcion"),
                "similitud": round(score, 3),
                "diferencias": dif
            })

    sobrantes_pdf = [pdf_items[j] for j in range(len(pdf_items)) if j not in usados_pdf]
    for p in sobrantes_pdf:
        diferenciasProductos.append({
            "descripcion_pdf": p.get("descripcion"),
            "match": "no_encontrado_en_sri"
        })

    total_pdf_items = round(sum(_to_float(it.get("precioTotal")) or 0 for it in pdf_items), 2) if pdf_items else None
    total_sri_items = round(sum(_to_float(it.get("precioTotalSinImpuesto")) or 0 for it in sri_items), 2) if sri_items else None

    totales_ok = True
    if total_pdf_items is not None and total_sri_items is not None:
        if abs(total_pdf_items - total_sri_items) > TOTAL_EPS:
            totales_ok = False
            diferencias["totalItems"] = {"sri": total_sri_items, "pdf": total_pdf_items}

    coincidencia = (not diferencias and not diferenciasProductos and totales_ok)
    
    # DEBUG: logs para entender por qué no hay coincidencia
    print(f"[DEBUG COINCIDENCIA] diferencias: {diferencias}")
    print(f"[DEBUG COINCIDENCIA] diferenciasProductos: {len(diferenciasProductos)} elementos")
    print(f"[DEBUG COINCIDENCIA] totales_ok: {totales_ok}")
    print(f"[DEBUG COINCIDENCIA] coincidencia final: {coincidencia}")
    print(f"[DEBUG COINCIDENCIA] total_pdf_items: {total_pdf_items}")
    print(f"[DEBUG COINCIDENCIA] total_sri_items: {total_sri_items}")
    
    # 7) Análisis avanzado de texto sobrepuesto
    t0 = time.perf_counter()
    texto_sobrepuesto_analisis = detectar_texto_sobrepuesto_avanzado(pdf_bytes)
    log_step("7) Análisis texto sobrepuesto avanzado", t0)
    
    # Para la evaluación de riesgo, si el SRI está AUTORIZADO, eso debería ser suficiente
    # para considerarlo válido, independientemente de diferencias menores en el parseo
    sri_autorizado_ok = True  # Sabemos que llegamos aquí solo si está AUTORIZADO
    
    # Usar el XML del SRI para validación financiera mejorada
    xml_sri_data = None
    if sri_json:
        xml_sri_data = sri_json.copy()
        xml_sri_data["autorizado"] = True
    
    riesgo = evaluar_riesgo_factura(
        pdf_bytes, 
        fuente_texto or "", 
        pdf_fields, 
        sri_ok=sri_autorizado_ok,
        clave_acceso=clave,
        ejecutar_prueba_sri=False,  # Ya tenemos los datos
        xml_sri_data=xml_sri_data   # Pasar el XML del SRI
    )

    return JSONResponse(
        status_code=200,
        content={
            "sri_verificado": True,
            "mensaje": "El comprobante es AUTORIZADO en el SRI.",
            "coincidencia": "si" if coincidencia else "no",
            "diferencias": diferencias,
            "diferenciasProductos": diferenciasProductos,
            "resumenProductos": {
                "num_sri": len(sri_items),
                "num_pdf": len(pdf_items),
                "total_sri_items": total_sri_items,
                "total_pdf_items": total_pdf_items
            },
            "factura": sri_json,
            "respuesta": raw,
            "claveAccesoDetectada": clave,
            "textoAnalizado": fuente_texto,
            "riesgo": riesgo
        },
    )
