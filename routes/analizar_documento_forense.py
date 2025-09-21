#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoint de análisis forense de documentos
Implementa la misma lógica que doc_forensics_pro.py
"""

import base64
import io
import json
import math
import os
import re
import zlib
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List, Union

import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ExifTags
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Optional imports
try:
    import cv2
except Exception:
    cv2 = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:
    pdfminer_extract_text = None

try:
    from pdf2image import convert_from_path as pdf2img_convert_from_path
except Exception:
    pdf2img_convert_from_path = None

router = APIRouter()

# ------------------------ Data structures ------------------------

@dataclass
class Metric:
    name: str
    value: float
    unit: str
    meaning: str
    interpretation: str

class PeticionDocumento(BaseModel):
    documento_base64: str
    tipo_archivo: Optional[str] = None  # "imagen" o "pdf"

# ------------------------ Helpers generales ------------------------

def to_np_gray(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.float32)

def resave_jpeg(img: Image.Image, quality: int = 90) -> Image.Image:
    from io import BytesIO
    buf = BytesIO()
    try:
        img.save(buf, format="JPEG", quality=quality, optimize=True, subsampling=0)
    except Exception:
        img.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    return Image.open(buf).convert("RGB")

def ensure_jpeg_working_copy(img: Image.Image) -> Tuple[Image.Image, str]:
    note = ""
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    
    # Para PNG/TIFF/WebP, crear una copia JPEG con fondo blanco
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
        note = "Archivo convertido a JPEG para análisis ELA"
    elif img.mode == "L":
        img = img.convert("RGB")
        note = "Imagen en escala de grises convertida a RGB"
    
    return img, note

# ------------------------ ELA y métricas imagen ------------------------

def compute_ela(original: Image.Image, quality: int = 90, enhance_factor: float = 20.0):
    resaved = resave_jpeg(original, quality=quality)
    diff = ImageChops.difference(original.convert("RGB"), resaved)
    diff_gray = diff.convert("L")
    
    diff_array = np.asarray(diff_gray, dtype=np.float32)
    diff_normalized = np.clip(diff_array / 255.0, 0, 1)
    diff_thresholded = np.where(diff_normalized > 0.01, diff_normalized * 255, 0)
    
    ela_vis = ImageEnhance.Brightness(Image.fromarray(diff_thresholded.astype(np.uint8), mode="L")).enhance(enhance_factor)
    ela_np = diff_thresholded.astype(np.float32)
    
    return ela_vis, ela_np

def compute_edges(gray_np: np.ndarray, threshold: float = None) -> np.ndarray:
    img = Image.fromarray(gray_np.astype(np.uint8), mode="L").filter(ImageFilter.FIND_EDGES)
    arr = np.asarray(img, dtype=np.float32)
    if threshold is None:
        threshold = np.percentile(arr, 75)
    mask = (arr >= threshold).astype(np.uint8)
    return mask

def block_stats(ela_np: np.ndarray, block: int = 8):
    h, w = ela_np.shape
    bh = h // block; bw = w // block
    trimmed = ela_np[:bh*block, :bw*block]
    reshaped = trimmed.reshape(bh, block, bw, block)
    block_means = reshaped.mean(axis=(1, 3))
    mu = float(block_means.mean())
    sigma = float(block_means.std())
    return block_means, mu, sigma

def local_outlier_rate(block_means: np.ndarray, z_thresh: float = 3.0) -> float:
    mu = float(block_means.mean())
    sigma = float(block_means.std() + 1e-6)
    z = (block_means - mu) / sigma
    return float((np.abs(z) > z_thresh).mean())

def quality_slope(original: Image.Image, q_list=(95, 90, 85, 80)) -> float:
    means = []; xs = []
    for q in q_list:
        _, ela_np = compute_ela(original, quality=q, enhance_factor=1.0)
        means.append(float(ela_np.mean()))
        xs.append(float(100 - q))
    x = np.array(xs); y = np.array(means)
    x = x - x.mean(); y = y - y.mean()
    denom = (x**2).sum() + 1e-9
    slope = float((x*y).sum() / denom)
    return slope

# ------------------------ Copy-Move (OpenCV ORB) ------------------------

def copy_move_orb(img_array: np.ndarray) -> Dict[str, Any]:
    """Detecta clonado buscando coincidencias ORB dentro de la misma imagen."""
    if cv2 is None:
        return {"available": False, "reason": "OpenCV no instalado", "matches": 0}

    if img_array is None:
        return {"available": False, "reason": "No se pudo procesar imagen", "matches": 0}

    # Convertir PIL a OpenCV
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    orb = cv2.ORB_create(nfeatures=5000, scoreType=cv2.ORB_HARRIS_SCORE)
    kps, des = orb.detectAndCompute(gray, None)
    if des is None or len(kps) < 50:
        return {"available": True, "matches": 0, "note": "Muy pocos keypoints/descriptores"}

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des, des, k=2)

    good = []
    for m, n in matches:
        if m.trainIdx == m.queryIdx:
            continue
        if m.distance < 0.75 * n.distance:
            p1 = np.array(kps[m.queryIdx].pt)
            p2 = np.array(kps[m.trainIdx].pt)
            if np.linalg.norm(p1 - p2) > 20.0:
                good.append((m.queryIdx, m.trainIdx))

    good = list(set(tuple(sorted(x)) for x in good))
    match_count = len(good)

    # Score heurístico: densidad de matches normalizada por área
    H, W = gray.shape
    density = match_count / max(1.0, (H * W) / (1000 * 1000))
    cm_score = min(1.0, density / 200.0)
    
    return {
        "available": True,
        "matches": int(match_count),
        "density_per_MPx": float(density),
        "score_0_1": float(cm_score)
    }

# ------------------------ OCR + Reglas ------------------------

DATE_REGEXES = [
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
]

AMOUNT_REGEX = r"(?:\$?\s*)?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2})?)"
ID10_REGEX = r"\b\d{10}\b"
ID13_REGEX = r"\b\d{13}\b"

def norm_amount(s: str) -> Optional[float]:
    s = s.strip().replace(" ", "")
    s = s.replace(",", ".")
    try:
        parts = s.split(".")
        if len(parts) > 2:
            s = "".join(parts[:-1]) + "." + parts[-1]
        return float(s)
    except Exception:
        return None

def validate_ec_cedula(ced: str) -> bool:
    if not (ced.isdigit() and len(ced) == 10):
        return False
    prov = int(ced[:2])
    if prov < 1 or prov > 24:
        return False
    coef = [2,1,2,1,2,1,2,1,2]
    total = 0
    for i in range(9):
        n = int(ced[i]) * coef[i]
        if n > 9: n -= 9
        total += n
    ver = (10 - (total % 10)) % 10
    return ver == int(ced[9])

def validate_ec_ruc(ruc: str) -> bool:
    if not (ruc.isdigit() and len(ruc) == 13):
        return False
    prov = int(ruc[:2])
    if prov < 1 or prov > 24:
        return False
    tercer = int(ruc[2])
    if tercer < 6:
        return validate_ec_cedula(ruc[:10]) and ruc.endswith("001")
    if tercer == 6:
        coef = [3,2,7,6,5,4,3,2]
        total = sum(int(ruc[i]) * coef[i] for i in range(8))
        ver = 11 - (total % 11)
        if ver == 11: ver = 0
        return ver == int(ruc[8]) and ruc.endswith("0001")
    if tercer == 9:
        coef = [4,3,2,7,6,5,4,3,2]
        total = sum(int(ruc[i]) * coef[i] for i in range(9))
        ver = 11 - (total % 11)
        if ver == 11: ver = 0
        return ver == int(ruc[9]) and ruc.endswith("001")
    return False

def ocr_text_from_image(img: Image.Image) -> str:
    if pytesseract is None:
        return ""
    try:
        txt = pytesseract.image_to_string(img, lang="spa+eng", config="--oem 3 --psm 6")
        return txt
    except Exception:
        return ""

def extract_semantic_rules(text: str) -> Dict[str, Any]:
    res: Dict[str, Any] = {"dates": [], "amounts": {}, "ids": {"cedulas": [], "rucs": [], "invalid": []}, "checks": {}}
    if not text:
        return res

    # Dates
    dates = []
    for rx in DATE_REGEXES:
        dates += re.findall(rx, text)
    res["dates"] = list(sorted(set(dates)))

    # Amounts by keywords
    def find_amount(keyword_variants: List[str]) -> Optional[float]:
        for kw in keyword_variants:
            pattern = rf"{kw}\s*[:\-]?\s*{AMOUNT_REGEX}"
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                val = norm_amount(m.group(1))
                if val is not None:
                    return val
        return None

    subtotal = find_amount(["subtotal", "sub total"])
    iva = find_amount(["iva", "impuesto", "tax", "vat"])
    total = find_amount(["total", "valor total", "importe total"])

    if total is None:
        nums = [norm_amount(x) for x in re.findall(AMOUNT_REGEX, text)]
        nums = [x for x in nums if x is not None]
        if nums:
            total = max(nums)

    res["amounts"] = {"subtotal": subtotal, "iva": iva, "total": total}

    # Consistency check
    consistent = None
    if subtotal is not None and total is not None:
        if iva is None:
            consistent = abs(subtotal - total) < max(0.02, 0.01 * total)
        else:
            consistent = abs((subtotal + iva) - total) < max(0.02, 0.01 * total)
    res["checks"]["amounts_consistent"] = consistent

    # IDs
    cedulas = re.findall(ID10_REGEX, text)
    rucs = re.findall(ID13_REGEX, text)
    invalids = []
    for c in set(cedulas):
        if not validate_ec_cedula(c):
            invalids.append(("cedula", c))
    for r in set(rucs):
        if not validate_ec_ruc(r):
            invalids.append(("ruc", r))
    res["ids"]["cedulas"] = list(sorted(set(cedulas)))
    res["ids"]["rucs"] = list(sorted(set(rucs)))
    res["ids"]["invalid"] = invalids

    return res

# ------------------------ PDF analysis ------------------------

def pdf_structure_analysis(pdf_bytes: bytes) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "available": PyPDF2 is not None,
        "meta": {},
        "xobjects_per_page": [],
        "flags": {"incremental_updates": False, "layers_ocg": False},
        "counts": {"startxref": 0, "eof": 0, "xobject_tokens": 0},
        "text_extract_available": False,
        "text_excerpt": ""
    }
    
    # Análisis de bytes
    out["counts"]["startxref"] = len(re.findall(br"startxref", pdf_bytes))
    out["counts"]["eof"] = len(re.findall(br"%%EOF", pdf_bytes))
    out["flags"]["incremental_updates"] = out["counts"]["startxref"] > 1 or out["counts"]["eof"] > 1
    out["flags"]["layers_ocg"] = bool(re.search(br"/OCG|/OCProperties|/OCGs", pdf_bytes))
    out["counts"]["xobject_tokens"] = len(re.findall(br"/XObject", pdf_bytes))

    if PyPDF2 is None:
        out["available"] = False
        return out

    try:
        from io import BytesIO
        pdf_stream = BytesIO(pdf_bytes)
        
        try:
            reader = PyPDF2.PdfReader(pdf_stream)
            meta = reader.metadata or {}
        except AttributeError:
            reader = PyPDF2.PdfFileReader(pdf_stream)
            meta = reader.getDocumentInfo() or {}
        
        # Convertir metadatos
        meta_str = {}
        if meta:
            for k, v in meta.items():
                if v is not None:
                    meta_str[str(k)] = str(v)
        
        out["meta"] = meta_str

        # Extraer texto
        try:
            tx = ""
            pages = reader.pages if hasattr(reader, 'pages') else [reader.getPage(i) for i in range(min(3, reader.numPages))]
            for p in pages:
                tx += (p.extract_text() or "")
            out["text_extract_available"] = bool(tx.strip())
            out["text_excerpt"] = tx[:2000]
        except Exception:
            pass

    except Exception as e:
        out["error"] = str(e)

    return out

# ------------------------ EXIF y metadatos ------------------------

def extract_exif(img: Image.Image):
    try:
        raw = img.getexif()
        if not raw or len(raw) == 0:
            return False, "", {}, {}
        
        exif = {ExifTags.TAGS.get(k, k): v for k, v in raw.items()}
        software = str(exif.get("Software", "")).strip()
        
        exif_dates = {
            "exif_DateTimeOriginal": str(exif.get("DateTimeOriginal", "")).strip(),
            "exif_DateTimeDigitized": str(exif.get("DateTimeDigitized", "")).strip(),
            "exif_DateTime": str(exif.get("DateTime", "")).strip(),
            "exif_ModifyDate": str(exif.get("ModifyDate", "")).strip(),
            "exif_CreateDate": str(exif.get("CreateDate", "")).strip(),
        }
        
        exif_meta = {
            "Make": str(exif.get("Make", "")).strip(),
            "Model": str(exif.get("Model", "")).strip(),
            "Software": software,
            "Artist": str(exif.get("Artist", "")).strip(),
            "Copyright": str(exif.get("Copyright", "")).strip(),
            "ImageDescription": str(exif.get("ImageDescription", "")).strip(),
            "Orientation": exif.get("Orientation", 0),
            "XResolution": exif.get("XResolution", 0),
            "YResolution": exif.get("YResolution", 0),
            "ResolutionUnit": exif.get("ResolutionUnit", 0),
            "ColorSpace": exif.get("ColorSpace", 0),
            "ExifVersion": str(exif.get("ExifVersion", "")).strip(),
            "Flash": exif.get("Flash", 0),
            "FocalLength": exif.get("FocalLength", 0),
            "FNumber": exif.get("FNumber", 0),
            "ExposureTime": exif.get("ExposureTime", 0),
            "ISOSpeedRatings": exif.get("ISOSpeedRatings", 0),
            "WhiteBalance": exif.get("WhiteBalance", 0),
        }
        
        return True, software, exif_dates, exif_meta
    except Exception:
        return False, "", {}, {}

# ------------------------ Scoring ------------------------

def suspicion_label(score: float) -> str:
    if score < 25:
        return "Baja (poco probable manipulación)"
    elif score < 50:
        return "Media (revisar con más pruebas)"
    elif score < 75:
        return "Alta (indicios claros, validar)"
    else:
        return "Muy alta (probable manipulación)"

def craft_conclusion(score: float, label: str) -> str:
    pct = round(score, 2)
    base = f"Nivel de sospecha: {pct}% → {label}. "
    if score < 25:
        tip = "Baja probabilidad de alteración. Conserve evidencias y valide procedencia si es crítico."
    elif score < 50:
        tip = "Señales moderadas. Revise EXIF/XMP/PDF, OCR y consistencia de sellos/firmas."
    elif score < 75:
        tip = "Indicios claros de posible edición. Sume copy-move, doble JPEG, reglas de negocio y pericia adicional."
    else:
        tip = "Alta probabilidad de manipulación. Escalar a peritaje formal y preservar cadena de custodia."
    return base + tip

# ------------------------ Análisis de imagen ------------------------

def analyze_image(img: Image.Image) -> Dict[str, Any]:
    fmt = (getattr(img, "format", None) or "").upper()
    exif_ok, exif_soft, exif_dates, exif_meta = extract_exif(img)

    # ELA
    work_img, note = ensure_jpeg_working_copy(img)
    gray_np = to_np_gray(work_img)
    ela_vis, ela_np = compute_ela(work_img, quality=90, enhance_factor=20.0)
    edge_mask = compute_edges(gray_np)
    blocks, _, _ = block_stats(ela_np, block=8)
    outlier_rate = local_outlier_rate(blocks, 3.0)

    ela_mean = float(ela_np.mean())
    ela_std = float(ela_np.std())
    ela_p95 = float(np.percentile(ela_np, 95))
    ela_edge_mean = float(ela_np[edge_mask == 1].mean()) if edge_mask.sum() > 0 else ela_mean
    ela_smooth_mean = float(ela_np[edge_mask == 0].mean()) if (edge_mask == 0).sum() > 0 else ela_mean
    ela_ratio = float((ela_smooth_mean + 1e-6) / (ela_edge_mean + 1e-6))
    slope = quality_slope(work_img, (95, 90, 85, 80))

    # Copy-Move
    img_array = np.asarray(work_img)
    cm = copy_move_orb(img_array)

    # OCR + Reglas
    text = ocr_text_from_image(img) if pytesseract else ""
    rules = extract_semantic_rules(text)

    # Score
    r_score = float(np.clip((ela_ratio - 0.6) / (1.2 - 0.6), 0, 1) * 25)
    o_score = float(np.clip(outlier_rate / 0.15, 0, 1) * 20)
    e_score = float(np.clip((ela_p95 / 255.0 - 0.12) / (0.28 - 0.12), 0, 1) * 10)
    if slope >= 0:
        s_score = float(np.clip(0.08 - slope, 0, 0.08) / 0.08 * 8)
    else:
        s_score = float(np.clip(abs(slope), 0, 0.1) / 0.1 * 8)
    
    cm_score = float((cm.get("score_0_1", 0.0)) * 22)
    
    inc = rules.get("checks", {}).get("amounts_consistent")
    ocr_score = 0.0
    if inc is False:
        ocr_score = 10.0

    # Editor hints
    editor_hit = False
    editor_names = ("photoshop", "gimp", "affinity", "pixelmator", "lightroom", "illustrator", "acrobat")
    if exif_soft and any(s in exif_soft.lower() for s in editor_names):
        editor_hit = True
    exif_score = 5.0 if editor_hit else (0.0 if exif_ok else 2.0)

    total = float(r_score + o_score + e_score + s_score + cm_score + ocr_score + exif_score)
    total = max(0.0, min(100.0, total))
    label = suspicion_label(total)
    conclusion = craft_conclusion(total, label)

    return {
        "type": "image",
        "format": fmt,
        "meta": {
            "exif_present": exif_ok,
            "exif_software": exif_soft,
            "exif_metadata": exif_meta,
            "exif_dates": exif_dates
        },
        "ela": {
            "mean": ela_mean, "std": ela_std, "p95": ela_p95,
            "smooth_edge_ratio": ela_ratio, "outlier_rate": float(outlier_rate),
            "quality_slope": float(slope)
        },
        "copy_move": cm,
        "ocr_rules": {"available": pytesseract is not None, "text_excerpt": text[:1000], "analysis": rules},
        "suspicion": {
            "score_0_100": round(total,2), 
            "label": label, 
            "certeza_falsificacion_pct": round(total,2),
            "breakdown": {
                "ela_ratio": round(r_score, 2),
                "outliers": round(o_score, 2),
                "ela_intensity": round(e_score, 2),
                "quality_slope": round(s_score, 2),
                "copy_move": round(cm_score, 2),
                "ocr_inconsistency": round(ocr_score, 2),
                "editor_software": round(exif_score, 2)
            }
        },
        "conclusion": conclusion,
        "notes": note
    }

# ------------------------ Análisis de PDF ------------------------

def analyze_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    pdf_info = pdf_structure_analysis(pdf_bytes)
    
    # Extraer texto
    text = ""
    if pdf_info.get("text_extract_available"):
        text = pdf_info.get("text_excerpt", "")
    elif pdfminer_extract_text:
        try:
            from io import BytesIO
            text = pdfminer_extract_text(BytesIO(pdf_bytes))[:5000]
        except Exception:
            text = ""

    rules = extract_semantic_rules(text)

    # Suspicion score
    s = 0.0
    issues = []
    warnings = []
    
    if pdf_info["flags"]["incremental_updates"]:
        s += 25.0
        issues.append("Actualizaciones incrementales detectadas")
    
    startxref_count = pdf_info["counts"]["startxref"]
    eof_count = pdf_info["counts"]["eof"]
    if startxref_count > 1:
        s += 20.0
        issues.append(f"Múltiples startxref ({startxref_count})")
    if eof_count > 1:
        s += 15.0
        issues.append(f"Múltiples EOF ({eof_count})")
    
    if pdf_info["flags"]["layers_ocg"]:
        s += 15.0
        issues.append("Capas OCG detectadas")
    
    xobject_count = pdf_info["counts"]["xobject_tokens"]
    if xobject_count > 20:
        s += 10.0
        warnings.append(f"Muchos XObjects ({xobject_count})")
    elif xobject_count > 50:
        s += 15.0
        issues.append(f"Exceso de XObjects ({xobject_count})")
    
    if not pdf_info.get("meta") or len(pdf_info.get("meta", {})) == 0:
        s += 8.0
        warnings.append("Sin metadatos PDF")
    
    if pdf_info.get("error"):
        s += 5.0
        warnings.append("Error en análisis PDF")
    
    if not pdf_info.get("text_extract_available") and not text.strip():
        s += 10.0
        warnings.append("Sin texto extraíble")
    
    if rules.get("checks", {}).get("amounts_consistent") is False:
        s += 15.0
        issues.append("Inconsistencias en totales/montos detectadas")

    s = max(0.0, min(100.0, s))
    label = suspicion_label(s)
    conclusion = craft_conclusion(s, label)

    return {
        "type": "pdf",
        "pdf": pdf_info,
        "text_excerpt": text[:2000] if text else "",
        "ocr_rules": {"available": bool(text), "analysis": rules},
        "pdf_validation": {
            "issues": issues,
            "warnings": warnings,
            "score": round(s, 2)
        },
        "suspicion": {
            "score_0_100": round(s,2), 
            "label": label, 
            "certeza_falsificacion_pct": round(s,2),
            "breakdown": {
                "incremental_updates": 25.0 if pdf_info["flags"]["incremental_updates"] else 0.0,
                "multiple_startxref": 20.0 if startxref_count > 1 else 0.0,
                "multiple_eof": 15.0 if eof_count > 1 else 0.0,
                "layers_ocg": 15.0 if pdf_info["flags"]["layers_ocg"] else 0.0,
                "xobjects": min(15.0, max(0.0, (xobject_count - 20) * 0.5)) if xobject_count > 20 else 0.0,
                "no_metadata": 8.0 if not pdf_info.get("meta") or len(pdf_info.get("meta", {})) == 0 else 0.0,
                "extraction_error": 5.0 if pdf_info.get("error") else 0.0,
                "no_text": 10.0 if not pdf_info.get("text_extract_available") and not text.strip() else 0.0,
                "business_rules": 15.0 if rules.get("checks", {}).get("amounts_consistent") is False else 0.0
            }
        },
        "conclusion": conclusion,
        "notes": "Análisis forense PDF: incrementos, startxref múltiples, capas OCG, XObjects, metadatos."
    }

# ------------------------ Endpoint principal ------------------------

@router.post("/analizar-documento-forense")
async def analizar_documento_forense(req: PeticionDocumento):
    """
    Análisis forense completo de documentos (imagen/PDF)
    Implementa la misma lógica que doc_forensics_pro.py
    """
    try:
        # Decodificar base64
        documento_bytes = base64.b64decode(req.documento_base64, validate=True)
        
        # Detectar tipo de archivo
        if req.tipo_archivo:
            tipo = req.tipo_archivo.lower()
        else:
            # Detectar por contenido
            if documento_bytes.startswith(b'%PDF'):
                tipo = "pdf"
            else:
                tipo = "imagen"
        
        # Procesar según tipo
        if tipo == "pdf":
            resultado = analyze_pdf(documento_bytes)
        else:
            # Procesar como imagen
            img = Image.open(io.BytesIO(documento_bytes))
            resultado = analyze_image(img)
        
        return JSONResponse(
            status_code=200,
            content={
                "exito": True,
                "tipo_documento": tipo,
                "analisis_forense": resultado,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "exito": False,
                "error": f"Error en análisis forense: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )
