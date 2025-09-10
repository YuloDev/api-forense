# -*- coding: utf-8 -*-
"""
Validador SRI + OCR (EasyOCR) + Comparación completa (cabecera + productos)
+ Evaluación de Riesgo Heurístico cuando no se puede verificar en el SRI.

- Extrae clave de acceso del PDF / OCR.
- Consulta SRI y parsea el XML → JSON.
- Extrae campos del PDF/OCR (ruc, razón social, fecha, total, etc.) y también
  la tabla de productos (descripción, cantidad, precioUnitario, precioTotal).
- Compara SRI vs PDF: cabecera + productos + totales.
- Si NO se puede verificar SRI (sin clave / timeout / error / no autorizado):
  ejecuta Validaciones Prioritarias y Secundarias (y algunas extra) para
  evaluar el riesgo de adulteración.

Respuesta (SRI no disponible):
    {
      "sri_verificado": false,
      "mensaje": "...",
      "riesgo": {
         "score": 0..100,
         "nivel": "bajo|medio|alto",
         "prioritarias": [...],
         "secundarias": [...],
         "adicionales": [...]
      },
      "pdfFacturaJsonB64": "...",
      "claveAccesoDetectada": "...." | null
    }

Requisitos extra OCR:
  pip install easyocr pymupdf pillow torch torchvision
"""

import os
import io
import re
import time
import json
import base64
import html
import math
import statistics
import unicodedata
from datetime import datetime, date, timedelta
from typing import Dict, Tuple, Optional, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from pdfminer.high_level import extract_text
from zeep import Client
from zeep.transports import Transport
import requests
import xml.etree.ElementTree as ET
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
from PIL import Image
try:
    import easyocr
    HAS_EASYOCR = True
except Exception:
    HAS_EASYOCR = False

from difflib import SequenceMatcher

try:
    from importlib.metadata import version as pkg_version
except Exception:
    pkg_version = None

# --------------------------- CONFIG ----------------------------------
SRI_WSDL = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
MAX_PDF_BYTES = int(os.getenv("MAX_PDF_BYTES", 10 * 1024 * 1024))  # 10 MB
SRI_TIMEOUT = float(os.getenv("SRI_TIMEOUT", "12"))
TEXT_MIN_LEN_FOR_DOC = int(os.getenv("TEXT_MIN_LEN_FOR_DOC", "50"))
RENDER_DPI = int(os.getenv("RENDER_DPI", "260"))
EASYOCR_LANGS = os.getenv("EASYOCR_LANGS", "es,en").split(",")
EASYOCR_GPU = os.getenv("EASYOCR_GPU", "false").lower() == "true"

# Tolerancias comparación SRI vs PDF
QTY_EPS = float(os.getenv("CMP_QTY_EPS", "0.001"))
PRICE_EPS = float(os.getenv("CMP_PRICE_EPS", "0.01"))
TOTAL_EPS = float(os.getenv("CMP_TOTAL_EPS", "0.02"))
MATCH_THRESHOLD = float(os.getenv("CMP_MATCH_THRESHOLD", "0.60"))

# Umbrales / pesos para RIESGO (ajustables)
RISK_WEIGHTS = {
    # PRIORITARIAS
    "fecha_creacion_vs_emision": 15,
    "fecha_mod_vs_creacion": 12,
    "software_conocido": 12,
    "num_paginas": 10,
    "capas_multiples": 10,
    # SECUNDARIAS
    "consistencia_fuentes": 8,
    "dpi_uniforme": 8,
    "compresion_estandar": 6,
    "alineacion_texto": 6,
    "tamano_esperado": 6,
    # ADICIONALES
    "anotaciones_o_formularios": 3,
    "javascript_embebido": 2,
    "archivos_incrustados": 3,
    "firmas_pdf": -4,       # resta riesgo si hay firma
    "actualizaciones_incrementales": 3,
    "cifrado_permisos_extra": 2,
}
RISK_LEVELS = {"bajo": (0, 29), "medio": (30, 59), "alto": (60, 100)}

# Heurística fechas
MAX_DIAS_CREACION_EMISION_OK = int(os.getenv("MAX_DIAS_CREACION_EMISION_OK", "30"))
MAX_DIAS_MOD_VS_CREACION_OK = int(os.getenv("MAX_DIAS_MOD_VS_CREACION_OK", "10"))

# Heurística tamaño esperado (por página)
ONEPAGE_MIN_BYTES = int(os.getenv("ONEPAGE_MIN_BYTES", "20000"))   # 20KB
ONEPAGE_MAX_BYTES_TEXTUAL = int(os.getenv("ONEPAGE_MAX_BYTES_TEXTUAL", "1200000"))  # 1.2MB
ONEPAGE_MAX_BYTES_ESCANEADO = int(os.getenv("ONEPAGE_MAX_BYTES_ESCANEADO", "3500000"))  # 3.5MB

KNOWN_PRODUCERS = [
    "adobe", "itext", "apache pdfbox", "libreoffice", "microsoft",
    "wkhtmltopdf", "reportlab", "foxit", "tcpdf", "aspose", "prince", "weasyprint"
]

STD_IMAGE_FILTERS = {"DCTDecode", "FlateDecode", "JPXDecode", "JBIG2Decode", "CCITTFaxDecode", "RunLengthDecode", "LZWDecode"}

app = FastAPI(title="Validador SRI + OCR + Comparación productos + Riesgo", version="1.50.0-risk")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # debe ser False si usas "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------- UTILS -----------------------------------
def log_step(step: str, t0: float):
    print(f"[TIMING] {step}: {time.perf_counter() - t0:.3f}s")

def normalize_comprobante_xml(x: str) -> str:
    if not isinstance(x, str):
        x = str(x or "")
    s = x.strip()
    if s.startswith("<![CDATA[") and s.endswith("]]>"):
        s = s[9:-3].strip()
    if "&lt;" in s or "&gt;" in s or "&amp;" in s:
        s = html.unescape(s)
    if s.startswith("\ufeff"):
        s = s.lstrip("\ufeff")
    return s

def strip_accents(s: str) -> str:
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')

def is_scanned_image_pdf(pdf_bytes: bytes, extracted_text: str) -> bool:
    text_len = len((extracted_text or "").strip())
    little_text = text_len < TEXT_MIN_LEN_FOR_DOC
    try:
        sample = pdf_bytes[: min(len(pdf_bytes), 2_000_000)]
        img_hits = len(re.findall(rb"/Subtype\s*/Image", sample)) or len(re.findall(rb"/Image\b", sample))
        has_image_objs = img_hits > 0
    except Exception:
        has_image_objs = False
    return little_text and has_image_objs

def _to_float(x: Optional[str]) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except:
        return None

# ------------------ Clave de Acceso (robusto) ------------------------
DIGITS49_FLEX = r"((?:\d[\s-]*){49})"

def _normalize_digits(block: str) -> Optional[str]:
    if not block:
        return None
    only = re.sub(r"\D", "", block)
    return only if len(only) == 49 else None

def _search_after_label(text: str, labels: List[str], window_chars: int = 2000) -> Tuple[Optional[str], bool]:
    for label_regex in labels:
        for m in re.finditer(label_regex, text, flags=re.I | re.UNICODE):
            start = m.end()
            window = text[start:start + window_chars]
            m1 = re.search(r"[:\s-]*" + DIGITS49_FLEX, window)
            if m1:
                clave = _normalize_digits(m1.group(1))
                if clave:
                    return clave, True
            m2 = re.search(r"[\r\n]+[:\s-]*" + DIGITS49_FLEX, window)
            if m2:
                clave = _normalize_digits(m2.group(1))
                if clave:
                    return clave, True
    return None, False

def extract_clave_acceso_from_text(raw_text: str) -> Tuple[Optional[str], bool]:
    if not raw_text:
        return None, False
    t = strip_accents(raw_text)
    t = re.sub(r"[ \t]+", " ", t)
    labels = [
        r"\bCLAVE\s*DE\s*ACCESO\s*DOCUMENTO\s*ELECTRONICO\b",
        r"\bCLAVE\s*ACCESO\s*DOCUMENTO\s*ELECTRONICO\b",
        r"\bCLAVE\s*DE\s*ACCESO\b",
        r"\bCLAVE\s*ACCESO\b",
    ]
    clave, found = _search_after_label(t, labels, window_chars=2000)
    if found and clave:
        return clave, True
    for m in re.finditer(r"DOCUMENTO\s*ELECTRONICO", t, flags=re.I):
        start = m.end()
        window = t[start:start + 2000]
        mnum = re.search(DIGITS49_FLEX, window)
        if mnum:
            clave = _normalize_digits(mnum.group(1))
            if clave:
                return clave, True
    return None, False

# ------------- Extracción de campos e ÍTEMS desde texto --------------
def parse_money(token: str) -> Optional[float]:
    return _to_float(token)

def norm_desc(s: str) -> str:
    s = strip_accents(s or "")
    s = re.sub(r"[^A-Za-z0-9\s\.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s

def extract_items_from_text(raw_text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not raw_text:
        return items

    text = strip_accents(raw_text)
    start_idx = re.search(r"\bDESCRIPCION\b", text, re.I)
    if start_idx:
        text = text[start_idx.start():]

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    patt1 = re.compile(
        r"^(?P<desc>.+?)\s+(?P<cant>\d+(?:[.,]\d+)?)\s+(?P<unit>\d+(?:[.,]\d+)?)\s+(?P<tot>\d+(?:[.,]\d+)?)$"
    )
    patt2 = re.compile(
        r"^(?P<desc>.+?)\s+(?P<cant>\d+(?:[.,]\d+)?)\s+.*?(?P<unit>\d+(?:[.,]\d+)?)\s+(?P<tot>\d+(?:[.,]\d+)?)$"
    )

    for ln in lines:
        if re.search(r"(DESCRIPCION|CANTIDAD|PRE\.?U|UNI|PRE\.?TOT|TOTAL|SUBTOTAL|IVA|TARIFA)", ln, re.I):
            continue
        m = patt1.match(ln) or patt2.match(ln)
        if m:
            desc = m.group("desc")
            cant = _to_float(m.group("cant"))
            unit = parse_money(m.group("unit"))
            tot = parse_money(m.group("tot"))
            if cant is not None and unit is not None and tot is not None and cant > 0 and unit >= 0 and tot >= 0:
                items.append({
                    "descripcion": desc.strip(),
                    "cantidad": cant,
                    "precioUnitario": unit,
                    "precioTotal": tot,
                })

    uniq = []
    seen = set()
    for it in items:
        key = (norm_desc(it["descripcion"]), round(it["cantidad"], 4),
               round(it["precioUnitario"], 4), round(it["precioTotal"], 4))
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    return uniq

def extract_invoice_fields_from_text(raw_text: str, clave_acceso: Optional[str]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if not raw_text:
        if clave_acceso:
            data["claveAcceso"] = clave_acceso
        data["detalles"] = []
        return data

    text = strip_accents(raw_text)

    # RUC
    m = re.search(r"\bRUC[:\s]*([0-9]{13})\b", text, re.I) or re.search(r"\b([0-9]{13})\b", text)
    if m:
        data["ruc"] = m.group(1)

    # Fecha
    m = re.search(r"fecha\s*(?:de\s*)?emision[:\s]*([0-3]?\d[/-][01]?\d[/-]\d{2,4})", text, re.I) or \
        re.search(r"\b([0-3]?\d[/-][01]?\d[/-]\d{2,4})\b", text)
    if m:
        f = m.group(1).replace("-", "/")
        parts = f.split("/")
        if len(parts[2]) == 2:
            parts[2] = "20" + parts[2]
        data["fechaEmision"] = "/".join(parts)

    # Total a pagar o TOTAL
    m = re.search(r"total\s*a\s*pagar[:\s]*\$?\s*([0-9]+[\.,][0-9]{2})", text, re.I) or \
        re.search(r"\bTOTAL\b[^0-9]{0,15}\$?\s*([0-9]+[\.,][0-9]{2})", text, re.I)
    if m:
        data["importeTotal"] = _to_float(m.group(1))

    # Razon Social (heurística líneas cerca de RUC)
    try:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        ruc_idx = next((i for i,l in enumerate(lines) if re.search(r"\bRUC\b", l, re.I)), None)
        if ruc_idx and ruc_idx > 0:
            block = " ".join(lines[max(0, ruc_idx-3):ruc_idx])
            block = re.sub(r"^(DIRECCION|SUCURSAL|MATRIZ).*$", "", block, flags=re.I)
            data["razonSocial"] = " ".join(block.split())[:120]
    except Exception:
        pass

    if clave_acceso:
        data["claveAcceso"] = clave_acceso

    # Ítems
    data["detalles"] = extract_items_from_text(raw_text)

    # Total calculado por ítems (si hay)
    if data["detalles"]:
        data["totalCalculadoPorItems"] = round(sum(_to_float(i["precioTotal"]) or 0.0 for i in data["detalles"]), 2)

    return data

# ------------------- OCR con EasyOCR -------------------
_reader_cache: Optional[Any] = None
def _easyocr_reader():
    global _reader_cache
    if _reader_cache is None:
        _reader_cache = easyocr.Reader(EASYOCR_LANGS, gpu=EASYOCR_GPU, verbose=False)
    return _reader_cache

def easyocr_text_from_pdf(pdf_bytes: bytes, dpi: int = RENDER_DPI) -> str:
    if not HAS_EASYOCR:
        return ""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    reader = _easyocr_reader()
    chunks: List[str] = []
    import numpy as np
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        np_img = np.array(img)
        try:
            results = reader.readtext(np_img, detail=0, paragraph=True)
            if results:
                chunks.append("\n".join(results))
        except Exception:
            continue
    return "\n".join(chunks).strip()

# ------------------------ SRI & XML --------------------
def factura_xml_to_json(xml_str: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_str.encode("utf-8"))

    it = root.find("infoTributaria")
    info_trib: Dict[str, Any] = {}
    if it is not None:
        def tx(tag: str) -> Optional[str]:
            v = it.findtext(tag)
            return v.strip() if isinstance(v, str) else v
        info_trib = {
            "ambiente": tx("ambiente"),
            "tipoEmision": tx("tipoEmision"),
            "razonSocial": tx("razonSocial"),
            "nombreComercial": tx("nombreComercial"),
            "ruc": tx("ruc"),
            "claveAcceso": tx("claveAcceso"),
            "codDoc": tx("codDoc"),
            "estab": tx("estab"),
            "ptoEmi": tx("ptoEmi"),
            "secuencial": tx("secuencial"),
            "dirMatriz": tx("dirMatriz"),
            "agenteRetencion": tx("agenteRetencion"),
        }

    inf = root.find("infoFactura")
    info_fact: Dict[str, Any] = {}
    if inf is not None:
        def fx(tag: str) -> Optional[str]:
            v = inf.findtext(tag)
            return v.strip() if isinstance(v, str) else v

        total_con_imps: List[Dict[str, Any]] = []
        tci = inf.find("totalConImpuestos")
        if tci is not None:
            for ti in tci.findall("totalImpuesto"):
                total_con_imps.append({
                    "codigo": (ti.findtext("codigo") or "").strip(),
                    "codigoPorcentaje": (ti.findtext("codigoPorcentaje") or "").strip(),
                    "baseImponible": _to_float(ti.findtext("baseImponible")),
                    "valor": _to_float(ti.findtext("valor")),
                })

        pagos_out: List[Dict[str, Any]] = []
        pagos = inf.find("pagos")
        if pagos is not None:
            for p in pagos.findall("pago"):
                pagos_out.append({
                    "formaPago": (p.findtext("formaPago") or "").strip(),
                    "total": _to_float(p.findtext("total")),
                    "plazo": (p.findtext("plazo") or "").strip(),
                    "unidadTiempo": (p.findtext("unidadTiempo") or "").strip(),
                })

        info_fact = {
            "fechaEmision": fx("fechaEmision"),
            "dirEstablecimiento": fx("dirEstablecimiento"),
            "obligadoContabilidad": fx("obligadoContabilidad"),
            "tipoIdentificacionComprador": fx("tipoIdentificacionComprador"),
            "razonSocialComprador": fx("razonSocialComprador"),
            "identificacionComprador": fx("identificacionComprador"),
            "direccionComprador": fx("direccionComprador"),
            "totalSinImpuestos": _to_float(inf.findtext("totalSinImpuestos")),
            "totalDescuento": _to_float(inf.findtext("totalDescuento")),
            "totalConImpuestos": total_con_imps,
            "propina": _to_float(inf.findtext("propina")),
            "importeTotal": _to_float(inf.findtext("importeTotal")),
            "moneda": fx("moneda"),
            "pagos": pagos_out,
        }

    detalles_out: List[Dict[str, Any]] = []
    dets = root.find("detalles")
    if dets is not None:
        for d in dets.findall("detalle"):
            imp_list: List[Dict[str, Any]] = []
            imps = d.find("impuestos")
            if imps is not None:
                for imp in imps.findall("impuesto"):
                    imp_list.append({
                        "codigo": (imp.findtext("codigo") or "").strip(),
                        "codigoPorcentaje": (imp.findtext("codigoPorcentaje") or "").strip(),
                        "tarifa": _to_float(imp.findtext("tarifa")),
                        "baseImponible": _to_float(imp.findtext("baseImponible")),
                        "valor": _to_float(imp.findtext("valor")),
                    })
            detalles_out.append({
                "codigoPrincipal": (d.findtext("codigoPrincipal") or "").strip(),
                "codigoAuxiliar": (d.findtext("codigoAuxiliar") or "").strip(),
                "descripcion": (d.findtext("descripcion") or "").strip(),
                "cantidad": _to_float(d.findtext("cantidad")),
                "precioUnitario": _to_float(d.findtext("precioUnitario")),
                "descuento": _to_float(d.findtext("descuento")),
                "precioTotalSinImpuesto": _to_float(d.findtext("precioTotalSinImpuesto")),
                "impuestos": imp_list,
            })

    info_adic: Dict[str, Any] = {}
    ia = root.find("infoAdicional")
    if ia is not None:
        for c in ia.findall("campoAdicional"):
            nombre = c.attrib.get("nombre")
            valor = (c.text or "").strip()
            if nombre:
                info_adic[nombre] = valor

    return {
        "infoTributaria": info_trib,
        "infoFactura": info_fact,
        "detalles": detalles_out,
        "infoAdicional": info_adic,
    }

def sri_autorizacion_por_clave(clave: str, timeout: float = SRI_TIMEOUT):
    session = requests.Session()
    transport = Transport(session=session, timeout=timeout)
    client = Client(wsdl=SRI_WSDL, transport=transport)
    return client.service.autorizacionComprobante(clave)

def parse_autorizacion_response(resp) -> Tuple[bool, str, Optional[str], Dict]:
    try:
        raw = {
            "claveAccesoConsultada": getattr(resp, "claveAccesoConsultada", None),
            "numeroComprobantes": getattr(resp, "numeroComprobantes", None),
            "autorizaciones": None,
        }
        auts = getattr(resp, "autorizaciones", None)
        aut_list = list(auts.autorizacion) if auts and hasattr(auts, "autorizacion") else []

        raw_auts = []
        xml = None
        estado = ""
        for a in aut_list:
            d = {
                "estado": getattr(a, "estado", None),
                "numeroAutorizacion": getattr(a, "numeroAutorizacion", None),
                "fechaAutorizacion": str(getattr(a, "fechaAutorizacion", None)),
                "ambiente": getattr(a, "ambiente", None),
            }
            raw_auts.append(d)
            if not xml and hasattr(a, "comprobante"):
                xml = a.comprobante
            if hasattr(a, "estado") and a.estado:
                estado = a.estado
        raw["autorizaciones"] = raw_auts

        ok = (len(aut_list) > 0 and str(estado).upper() == "AUTORIZADO")
        return ok, estado, xml, raw
    except Exception:
        try:
            raw = dict(resp)
        except Exception:
            raw = {"_repr": str(resp)}
        return False, "", None, raw

# =============== RIESGO: utilidades de análisis de PDF =================

def _pdf_date_to_dt(s: Optional[str]) -> Optional[datetime]:
    """Convierte fechas PDF tipo D:YYYYMMDDHHmmSSOHH'mm' a datetime."""
    if not s:
        return None
    s = s.strip()
    if s.startswith("D:"):
        s = s[2:]
    # Basico: YYYY MM DD HH mm SS
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
            return datetime(y, min(mo,12), min(d,28), hh, mi, ss)
        except:
            return None

def _parse_fecha_emision(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    s = s.strip().replace("-", "/")
    try:
        # formatos: dd/mm/yyyy
        d, m, y = s.split("/")
        if len(y) == 2:
            y = "20" + y
        return date(int(y), int(m), int(d))
    except:
        return None

def _detect_layers(pdf_bytes: bytes) -> bool:
    """Heurística: busca OCG / OCProperties en bytes."""
    sample = pdf_bytes[: min(4_000_000, len(pdf_bytes))]
    return (b"/OCGs" in sample) or (b"/OCProperties" in sample) or re.search(rb"/OC\s", sample) is not None

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

    # alineación: porcentaje de líneas cuyo margen-izq cae cerca de uno de los 2 modos principales
    align_score = 1.0
    if left_margins:
        # cluster simple por redondeo a 1pt
        counts = {}
        for v in left_margins:
            counts[v] = counts.get(v, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:2]
        top_total = sum(c for _, c in top)
        align_score = top_total / max(1, len(left_margins))

    # direcciones de texto (rotaciones raras)
    non_horizontal = 0
    for d in dirs:
        # (1, 0) ~ horizontal; permitir pequeñas variaciones
        if abs(d[0] - 1.0) > 0.05 or abs(d[1]) > 0.05:
            non_horizontal += 1
    rot_ratio = non_horizontal / max(1, len(dirs)) if dirs else 0.0

    return fonts, {
        "alineacion_score": round(align_score, 3),  # 1.0=alineado, <0.7=disperso
        "rotacion_ratio": round(rot_ratio, 3),     # >0.2 = muchas rotaciones
        "num_lineas": len(left_margins)
    }

def _collect_images_info(doc: fitz.Document) -> Dict[str, Any]:
    """Extrae DPI, filtros de compresión y tamaño de imágenes colocadas."""
    dpis = []
    filters = []
    try:
        for pno in range(doc.page_count):
            page = doc.load_page(pno)
            # mapeo xref -> bbox para DPI
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
                # calcular DPI usando bbox (si tenemos)
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

    res = {
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
    return any(k in prod for k in KNOWN_PRODUCERS)

def _fonts_consistency(fonts_all_pages: List[str]) -> Dict[str, Any]:
    total = len(fonts_all_pages)
    uniq = {}
    for f in fonts_all_pages:
        uniq[f] = uniq.get(f, 0) + 1
    uniq_count = len(uniq)
    dom_ratio = 0.0
    if total > 0:
        dom_ratio = max(uniq.values())/total
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
        # permitir algo más por múltiples páginas
        max_ok = (ONEPAGE_MAX_BYTES_ESCANEADO if scanned else ONEPAGE_MAX_BYTES_TEXTUAL) * 1.5
        ok = (per_page >= ONEPAGE_MIN_BYTES * 0.6) and (per_page <= max_ok)
    return {
        "ok": bool(ok),
        "bytes_total": size_bytes,
        "bytes_por_pagina": int(per_page),
        "limite_max": int(max_ok),
        "tipo": "escaneado" if scanned else "textual"
    }

def evaluar_riesgo(pdf_bytes: bytes, fuente_texto: str, pdf_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula score y desglose de validaciones."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    meta = doc.metadata or {}
    pages = doc.page_count
    size_bytes = len(pdf_bytes)
    scanned = is_scanned_image_pdf(pdf_bytes, fuente_texto or "")

    # --- fechas ---
    fecha_emision = _parse_fecha_emision(pdf_fields.get("fechaEmision"))
    dt_cre = _pdf_date_to_dt(meta.get("creationDate") or meta.get("CreationDate"))
    dt_mod = _pdf_date_to_dt(meta.get("modDate") or meta.get("ModDate"))

    # --- software ---
    prod_ok = _is_known_producer(meta)

    # --- capas ---
    has_layers = _detect_layers(pdf_bytes)

    # --- fuentes y alineación ---
    all_fonts = []
    align_metrics = []
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
    unknown_filters = []
    for f in filters_set:
        # algunos filtros vienen como 'DCTDecode,FlateDecode' -> partir por coma si aparece
        for tok in re.split(r"[,\s]+", f):
            if tok and tok not in STD_IMAGE_FILTERS:
                unknown_filters.append(tok)
    if unknown_filters:
        comp_ok = False

    # --- alineación global ---
    # usar promedio de align_score y rot_ratio
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
    is_encrypted = False
    try:
        is_encrypted = doc.is_encrypted
    except Exception:
        pass

    # ================= SCORING =================
    score = 0
    details_prior = []
    details_sec = []
    details_extra = []

    # PRIORITARIAS
    # 1) Fecha creación vs fecha emisión
    penal = 0
    msg = "sin datos suficientes"
    if fecha_emision and dt_cre:
        dias = abs((dt_cre.date() - fecha_emision).days)
        msg = f"{dias} día(s) entre creación PDF y emisión"
        if dias <= MAX_DIAS_CREACION_EMISION_OK:
            penal = 0
        elif dias <= MAX_DIAS_CREACION_EMISION_OK + 30:
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
        elif diff <= MAX_DIAS_MOD_VS_CREACION_OK:
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

    # 5) Presencia de capas múltiples (OCG)
    penal = RISK_WEIGHTS["capas_multiples"] if has_layers else 0
    details_prior.append({"check": "Presencia de capas múltiples", "detalle": has_layers, "penalizacion": penal})
    score += penal

    # SECUNDARIAS
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
        penal = int(RISK_WEIGHTS["alineacion_texto"] * 0.6)
    details_sec.append({"check": "Alineación de elementos de texto", "detalle": {"alineacion_promedio": align_score_mean, "rotacion_promedio": rot_ratio_mean}, "penalizacion": penal})
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

    # Normalizar score a [0, 100]
    score = max(0, min(100, score))

    nivel = "bajo"
    for k, (lo, hi) in RISK_LEVELS.items():
        if lo <= score <= hi:
            nivel = k
            break

    return {
        "score": score,
        "nivel": nivel,
        "prioritarias": details_prior,
        "secundarias": details_sec,
        "adicionales": details_extra,
        "metadatos": meta,
        "paginas": pages,
        "escaneado_aprox": scanned,
        "imagenes": img_info
    }

# --------------------------- API -------------------------------------
class Peticion(BaseModel):
    pdfbase64: str

@app.get("/health")
def health():
    def safe_ver(pkg):
        try:
            return pkg_version(pkg) if pkg_version else None
        except Exception:
            return None
    return {
        "ok": True,
        "mode": "json + easyocr + compare-products + risk",
        "pdfminer": safe_ver("pdfminer.six"),
        "pymupdf": safe_ver("pymupdf"),
        "easyocr": safe_ver("easyocr"),
        "torch": safe_ver("torch"),
        "Pillow": safe_ver("Pillow"),
        "zeep": safe_ver("zeep"),
        "max_pdf_bytes": MAX_PDF_BYTES,
        "sri_timeout_sec": SRI_TIMEOUT,
        "app_version": "1.50.0-risk",
    }

@app.post("/validar-factura")
async def validar_factura(req: Peticion):
    t_all = time.perf_counter()

    # 1) decode
    t0 = time.perf_counter()
    try:
        pdf_bytes = base64.b64decode(req.pdfbase64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="El campo 'pdfbase64' no es base64 válido.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail=f"El PDF excede el tamaño máximo permitido ({MAX_PDF_BYTES} bytes).")
    log_step("1) decode base64", t0)

    # 2) texto directo
    t0 = time.perf_counter()
    try:
        text = extract_text(io.BytesIO(pdf_bytes))
    except Exception:
        text = ""
    log_step("2) extract_text(pdfminer)", t0)

    # 3) clave acceso (OCR si aplica)
    clave, etiqueta_encontrada = extract_clave_acceso_from_text(text or "")
    ocr_text = ""
    if not etiqueta_encontrada and is_scanned_image_pdf(pdf_bytes, text or "") and HAS_EASYOCR:
        t_ocr = time.perf_counter()
        ocr_text = easyocr_text_from_pdf(pdf_bytes, dpi=RENDER_DPI)
        log_step("3b) EasyOCR total", t_ocr)
        clave_ocr, etiqueta_ocr = extract_clave_acceso_from_text(ocr_text or "")
        if etiqueta_ocr and clave_ocr:
            clave = clave_ocr
            etiqueta_encontrada = True

    # Fuente de texto para extracción de campos y riesgo
    fuente_texto = text if text and not is_scanned_image_pdf(pdf_bytes, text) else (ocr_text or text)

    # Extraer campos del PDF/OCR aún si no hay clave
    pdf_fields = extract_invoice_fields_from_text(fuente_texto or "", clave)
    pdf_fields_b64 = base64.b64encode(json.dumps(pdf_fields, ensure_ascii=False).encode("utf-8")).decode("utf-8")

    # Si no hay clave o no válida, ejecutar RIESGO y retornar
    if not etiqueta_encontrada or not clave or not re.fullmatch(r"\d{49}", str(clave)):
        riesgo = evaluar_riesgo(pdf_bytes, fuente_texto or "", pdf_fields)
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

    # 4) SRI
    t0 = time.perf_counter()
    try:
        resp = sri_autorizacion_por_clave(clave, timeout=SRI_TIMEOUT)
    except requests.exceptions.Timeout:
        # Timeout → ejecutar riesgo
        riesgo = evaluar_riesgo(pdf_bytes, fuente_texto or "", pdf_fields)
        log_step("TOTAL (RIESGO por timeout SRI)", t_all)
        return JSONResponse(
            status_code=200,
            content={
                "sri_verificado": False,
                "mensaje": f"Tiempo de espera agotado consultando SRI (>{SRI_TIMEOUT:.0f}s). Se ejecutó evaluación de riesgo.",
                "riesgo": riesgo,
                "pdfFacturaJsonB64": pdf_fields_b64,
                "claveAccesoDetectada": clave
            }
        )
    except Exception as e:
        # Error genérico → ejecutar riesgo
        riesgo = evaluar_riesgo(pdf_bytes, fuente_texto or "", pdf_fields)
        log_step("TOTAL (RIESGO por error SRI)", t_all)
        return JSONResponse(
            status_code=200,
            content={
                "sri_verificado": False,
                "mensaje": f"Error consultando SRI: {str(e)}. Se ejecutó evaluación de riesgo.",
                "riesgo": riesgo,
                "pdfFacturaJsonB64": pdf_fields_b64,
                "claveAccesoDetectada": clave
            }
        )
    log_step("4) SRI autorizacion", t0)

    ok_aut, estado, xml_comprobante, raw = parse_autorizacion_response(resp)
    if not ok_aut:
        # No AUTORIZADO o sin XML → realizar riesgo y devolver
        riesgo = evaluar_riesgo(pdf_bytes, fuente_texto or "", pdf_fields)
        log_step("TOTAL (RIESGO por no AUTORIZADO)", t_all)
        return JSONResponse(
            status_code=200,
            content={
                "sri_verificado": False,
                "mensaje": "El comprobante no está AUTORIZADO en el SRI o no tiene XML legible. Se ejecutó evaluación de riesgo.",
                "sri_estado": estado,
                "riesgo": riesgo,
                "pdfFacturaJsonB64": pdf_fields_b64,
                "respuesta": raw,
                "claveAccesoDetectada": clave,
                "textoAnalizado": fuente_texto
            }
        )

    # 5) XML → JSON (SRI)
    xml_src = normalize_comprobante_xml(xml_comprobante)
    try:
        sri_json = factura_xml_to_json(xml_src)
    except Exception as e:
        # Aunque está autorizado, no pude parsear: igual devuelvo riesgo + xml
        riesgo = evaluar_riesgo(pdf_bytes, fuente_texto or "", pdf_fields)
        log_step("TOTAL (AUTORIZADO sin parse + RIESGO)", t_all)
        return JSONResponse(status_code=200, content={
            "sri_verificado": True,
            "mensaje": "AUTORIZADO en el SRI. No se pudo convertir completamente a JSON.",
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
        return SequenceMatcher(None, norm_desc(a), norm_desc(b)).ratio()

    emparejamientos = []
    usados_pdf = set()

    for i, s in enumerate(sri_items):
        best_j, best_score = None, -1.0
        for j, p in enumerate(pdf_items):
            if j in usados_pdf:
                continue
            sc = sim(s.get("descripcion",""), p.get("descripcion",""))
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
        # cantidad
        s_qty = _to_float(s.get("cantidad"))
        p_qty = _to_float(p.get("cantidad"))
        if s_qty is not None and p_qty is not None and abs(s_qty - p_qty) > QTY_EPS:
            dif["cantidad"] = {"sri": s_qty, "pdf": p_qty}
        # precio unitario
        s_unit = _to_float(s.get("precioUnitario"))
        p_unit = _to_float(p.get("precioUnitario"))
        if s_unit is not None and p_unit is not None and abs(s_unit - p_unit) > PRICE_EPS:
            dif["precioUnitario"] = {"sri": s_unit, "pdf": p_unit}
        # precio total (sin impuesto)
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

    # Items en PDF que no se usaron
    sobrantes_pdf = [pdf_items[j] for j in range(len(pdf_items)) if j not in usados_pdf]
    for p in sobrantes_pdf:
        diferenciasProductos.append({
            "descripcion_pdf": p.get("descripcion"),
            "match": "no_encontrado_en_sri"
        })

    # Totales por ítems (PDF vs SRI)
    total_pdf_items = round(sum(_to_float(it.get("precioTotal")) or 0 for it in pdf_items), 2) if pdf_items else None
    total_sri_items = round(sum(_to_float(it.get("precioTotalSinImpuesto")) or 0 for it in sri_items), 2) if sri_items else None
    totales_ok = True
    if total_pdf_items is not None and total_sri_items is not None:
        if abs(total_pdf_items - total_sri_items) > TOTAL_EPS:
            totales_ok = False
            diferencias["totalItems"] = {"sri": total_sri_items, "pdf": total_pdf_items}

    # Coincidencia global
    coincidencia = "si" if (not diferencias and not diferenciasProductos and totales_ok) else "no"

    log_step("TOTAL (AUTORIZADO+JSON+COMPARE+PRODUCTOS)", t_all)
    return JSONResponse(
        status_code=200,
        content={
            "sri_verificado": True,
            "mensaje": "El código de acceso del comprobante es AUTORIZADO en el SRI.",
            "coincidencia": coincidencia,
            "diferencias": diferencias,  # cabecera + totales ítems si difiere
            "diferenciasProductos": diferenciasProductos,
            "resumenProductos": {
                "num_sri": len(sri_items),
                "num_pdf": len(pdf_items),
                "total_sri_items": total_sri_items,
                "total_pdf_items": total_pdf_items
            },
            "pdfFacturaJsonB64": pdf_fields_b64,
            "factura": sri_json,
            "respuesta": raw,
            "claveAccesoDetectada": clave,
            "textoAnalizado": fuente_texto
        },
    )

# --------------------------- RUN -------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("prueba:app", host="127.0.0.1", port=8000, reload=True)
