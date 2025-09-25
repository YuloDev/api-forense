#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Endpoint para análisis forense de imágenes
Incluye: ELA, Copy-Move, OCR, validación de metadatos
"""

import io
import json
import math
import os
import re
import zlib
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ExifTags
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

# Optional sklearn import
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# --- Optional imports ---
try:
    import cv2
except Exception:
    cv2 = None

# Usar configuración global de Tesseract
import config

try:
    import pytesseract
except Exception:
    pytesseract = None

router = APIRouter()

# ------------------------ Tesseract Configuration ------------------------

def configure_tesseract():
    """Configura Tesseract si no está ya configurado"""
    if pytesseract is None:
        return False
    
    try:
        # Verificar si ya está configurado
        if hasattr(pytesseract.pytesseract, 'tesseract_cmd') and pytesseract.pytesseract.tesseract_cmd:
            return True
        
        # Configurar Tesseract
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        # Verificar que funciona
        pytesseract.get_tesseract_version()
        return True
        
    except Exception as e:
        print(f"Error configurando Tesseract: {e}")
        return False

# Configurar Tesseract al importar el módulo
configure_tesseract()

# ------------------------ Data structures ------------------------

@dataclass
class Metric:
    name: str
    value: float
    unit: str
    meaning: str
    interpretation: str

# ------------------------ Helpers ------------------------

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
    
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
        note = "Imagen RGBA convertida a JPEG para análisis ELA."
    
    return img, note

# ------------------------ ELA Analysis ------------------------

def compute_ela(original: Image.Image, quality: int = 90, enhance_factor: float = 20.0):
    resaved = resave_jpeg(original, quality=quality)
    diff = ImageChops.difference(original.convert("RGB"), resaved)
    diff_gray = diff.convert("L")
    
    diff_array = np.asarray(diff_gray, dtype=np.float32)
    diff_normalized = np.clip(diff_array / 255.0, 0, 1)
    diff_thresholded = np.where(diff_normalized > 0.01, diff_normalized * 255, 0)
    
    ela_vis = ImageEnhance.Brightness(Image.fromarray(diff_thresholded.astype(np.uint8)).convert("L")).enhance(enhance_factor)
    ela_np = diff_thresholded.astype(np.float32)
    
    return ela_vis, ela_np

def compute_edges(gray_np: np.ndarray, threshold: float = None) -> np.ndarray:
    img = Image.fromarray(gray_np.astype(np.uint8)).convert("L").filter(ImageFilter.FIND_EDGES)
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

# ------------------------ Copy-Move Detection ------------------------

def copy_move_orb(img_array: np.ndarray) -> Dict[str, Any]:
    if cv2 is None:
        return {"available": False, "reason": "OpenCV no instalado", "matches": 0}

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

    H, W = gray.shape
    heat = np.zeros((H, W), dtype=np.float32)
    for qi, ti in good:
        x1, y1 = kps[qi].pt
        x2, y2 = kps[ti].pt
        for (x, y) in [(x1, y1), (x2, y2)]:
            xi, yi = int(round(x)), int(round(y))
            cv2.circle(heat, (xi, yi), 10, 1.0, -1)

    density = match_count / max(1.0, (H * W) / (1000 * 1000))
    cm_score = min(1.0, density / 200.0)
    
    return {
        "available": True,
        "matches": int(match_count),
        "density_per_MPx": float(density),
        "score_0_1": float(cm_score)
    }

# ------------------------ Text Overlay Detection ------------------------

def detect_text_overlays(img: Image.Image) -> Dict[str, Any]:
    """
    Detecta texto superpuesto analizando bordes, varianza y consistencia de fuentes
    """
    if pytesseract is None or cv2 is None:
        return {"available": False, "reason": "OCR u OpenCV no disponibles", "detections": []}
    
    # Verificar configuración de Tesseract
    if not configure_tesseract():
        return {"available": False, "reason": "Tesseract no configurado correctamente", "detections": []}

    try:
        # Obtener datos detallados del OCR con coordenadas
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="spa+eng")
        
        # Convertir imagen a arrays para análisis
        img_array = np.array(img.convert("RGB"))
        gray_np = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Generar mapa de bordes con Canny
        edges = cv2.Canny(gray_np, 50, 150)
        
        suspicious_texts = []
        font_analysis = []
        
        for i, txt in enumerate(data["text"]):
            if not txt.strip() or len(txt.strip()) < 3:
                continue
                
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            conf = data["conf"][i]
            
            # Filtrar textos con muy baja confianza
            if conf < 30:
                continue
                
            # Extraer ROI para análisis
            if y + h <= gray_np.shape[0] and x + w <= gray_np.shape[1]:
                roi = gray_np[y:y+h, x:x+w]
                
                if roi.size > 0:
                    # 1. Análisis de varianza de intensidad
                    var_intensity = float(np.var(roi))
                    mean_intensity = float(np.mean(roi))
                    
                    # 2. Análisis de bordes en la región
                    roi_edges = edges[y:y+h, x:x+w]
                    edge_density = float(np.sum(roi_edges > 0) / max(roi.size, 1))
                    
                    # 3. Análisis de contraste
                    roi_contrast = float(np.max(roi) - np.min(roi))
                    
                    # 4. Análisis de uniformidad (texto digital suele ser muy uniforme)
                    roi_std = float(np.std(roi))
                    
                    # 5. Verificar si el texto coincide con bordes naturales
                    bbox_edges = edges[y:y+h, x:x+w]
                    natural_edge_alignment = float(np.sum(bbox_edges > 0) / max(bbox_edges.size, 1))
                    
                    # Criterios de sospecha
                    suspicious_score = 0
                    reasons = []
                    
                    # Texto superpuesto suele tener varianza muy baja
                    if var_intensity < 50:
                        suspicious_score += 3
                        reasons.append("baja_varianza")
                    
                    # Texto digital tiene bordes duros
                    if roi_contrast > 200 and roi_std < 30:
                        suspicious_score += 2
                        reasons.append("bordes_duros")
                    
                    # No alineado con bordes naturales
                    if natural_edge_alignment < 0.1:
                        suspicious_score += 2
                        reasons.append("no_alineado_bordes")
                    
                    # Muy uniforme (típico de texto digital)
                    if roi_std < 20:
                        suspicious_score += 1
                        reasons.append("muy_uniforme")
                    
                    # Contraste muy alto (típico de superposición)
                    if roi_contrast > 250:
                        suspicious_score += 1
                        reasons.append("alto_contraste")
                    
                    if suspicious_score >= 3:
                        suspicious_texts.append({
                            "text": txt.strip(),
                            "bbox": (x, y, w, h),
                            "confidence": conf,
                            "suspicious_score": suspicious_score,
                            "reasons": reasons,
                            "metrics": {
                                "var_intensity": var_intensity,
                                "mean_intensity": mean_intensity,
                                "edge_density": edge_density,
                                "contrast": roi_contrast,
                                "std": roi_std,
                                "natural_edge_alignment": natural_edge_alignment
                            }
                        })
                    
                    # Análisis de fuentes (tamaño y forma)
                    font_analysis.append({
                        "text": txt.strip(),
                        "width": w,
                        "height": h,
                        "aspect_ratio": w / max(h, 1),
                        "area": w * h
                    })
        
        # Análisis de consistencia de fuentes
        font_consistency = analyze_font_consistency(font_analysis)
        
        return {
            "available": True,
            "detections": suspicious_texts,
            "count": len(suspicious_texts),
            "font_analysis": font_consistency,
            "total_text_regions": len([t for t in data["text"] if t.strip()])
        }
        
    except Exception as e:
        return {"available": False, "reason": f"Error en detección: {str(e)}", "detections": []}

def analyze_font_consistency(font_data: List[Dict]) -> Dict[str, Any]:
    """
    Analiza la consistencia de fuentes para detectar texto agregado
    """
    if len(font_data) < 2:
        return {"suspicious": False, "reason": "insufficient_data"}
    
    # Agrupar por tamaños similares
    heights = [f["height"] for f in font_data]
    widths = [f["width"] for f in font_data]
    aspect_ratios = [f["aspect_ratio"] for f in font_data]
    
    # Calcular estadísticas
    height_std = float(np.std(heights))
    width_std = float(np.std(widths))
    aspect_std = float(np.std(aspect_ratios))
    
    # Detectar múltiples grupos de fuentes
    if SKLEARN_AVAILABLE:
        try:
            # Clustering por altura y ancho
            features = np.array([[h, w] for h, w in zip(heights, widths)])
            if len(features) >= 2:
                kmeans = KMeans(n_clusters=min(3, len(features)), random_state=42, n_init=10)
                clusters = kmeans.fit_predict(features)
                n_clusters = len(set(clusters))
            else:
                n_clusters = 1
        except:
            n_clusters = 1
    else:
        # Fallback sin sklearn: agrupar por rangos de tamaño
        height_ranges = []
        for h in heights:
            if h < np.mean(heights) * 0.8:
                height_ranges.append(0)  # Pequeño
            elif h > np.mean(heights) * 1.2:
                height_ranges.append(2)  # Grande
            else:
                height_ranges.append(1)  # Mediano
        n_clusters = len(set(height_ranges))
    
    suspicious = False
    reasons = []
    
    # Múltiples tipos de fuente
    if n_clusters > 2:
        suspicious = True
        reasons.append("multiples_tipografias")
    
    # Muy alta variabilidad en tamaños
    if height_std > np.mean(heights) * 0.5:
        suspicious = True
        reasons.append("tamaños_inconsistentes")
    
    # Muy alta variabilidad en proporciones
    if aspect_std > 0.5:
        suspicious = True
        reasons.append("proporciones_inconsistentes")
    
    return {
        "suspicious": suspicious,
        "reasons": reasons,
        "n_font_groups": n_clusters,
        "height_std": height_std,
        "width_std": width_std,
        "aspect_std": aspect_std,
        "height_mean": float(np.mean(heights)),
        "width_mean": float(np.mean(widths))
    }

# ------------------------ Enhanced Copy-Move Detection ------------------------

def enhanced_copy_move_detection(img_array: np.ndarray) -> Dict[str, Any]:
    """
    Detección mejorada de copy-move usando múltiples algoritmos
    """
    if cv2 is None:
        return {"available": False, "reason": "OpenCV no instalado", "matches": 0}

    results = {}
    
    try:
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # 1. ORB (ya implementado)
        orb_result = copy_move_orb(img_array)
        results["orb"] = orb_result
        
        # 2. SIFT si está disponible
        try:
            sift = cv2.SIFT_create()
            kp1, des1 = sift.detectAndCompute(gray, None)
            
            if des1 is not None and len(kp1) >= 50:
                # Buscar matches
                bf = cv2.BFMatcher()
                matches = bf.knnMatch(des1, des1, k=2)
                
                good_matches = []
                for m, n in matches:
                    if m.trainIdx == m.queryIdx:
                        continue
                    if m.distance < 0.75 * n.distance:
                        pt1 = np.array(kp1[m.queryIdx].pt)
                        pt2 = np.array(kp1[m.trainIdx].pt)
                        if np.linalg.norm(pt1 - pt2) > 20.0:
                            good_matches.append((m.queryIdx, m.trainIdx))
                
                good_matches = list(set(tuple(sorted(x)) for x in good_matches))
                
                results["sift"] = {
                    "available": True,
                    "matches": len(good_matches),
                    "keypoints": len(kp1)
                }
            else:
                results["sift"] = {"available": True, "matches": 0, "note": "Pocos keypoints SIFT"}
                
        except Exception as e:
            results["sift"] = {"available": False, "reason": f"SIFT error: {str(e)}"}
        
        # 3. Análisis de correlación por patches
        patch_correlation = analyze_patch_correlation(gray)
        results["patch_correlation"] = patch_correlation
        
        # Combinar resultados
        total_matches = orb_result.get("matches", 0) + results.get("sift", {}).get("matches", 0)
        combined_score = min(1.0, total_matches / 100.0)
        
        return {
            "available": True,
            "total_matches": total_matches,
            "combined_score": combined_score,
            "methods": results
        }
        
    except Exception as e:
        return {"available": False, "reason": f"Error en detección mejorada: {str(e)}"}

def analyze_patch_correlation(gray: np.ndarray) -> Dict[str, Any]:
    """
    Análisis de correlación por patches para detectar regiones similares
    """
    try:
        h, w = gray.shape
        patch_size = 32
        stride = 16
        
        patches = []
        positions = []
        
        # Extraer patches
        for y in range(0, h - patch_size, stride):
            for x in range(0, w - patch_size, stride):
                patch = gray[y:y+patch_size, x:x+patch_size]
                patches.append(patch.flatten())
                positions.append((x, y))
        
        if len(patches) < 2:
            return {"available": False, "reason": "insufficient_patches"}
        
        patches = np.array(patches)
        
        # Calcular matriz de correlación
        correlation_matrix = np.corrcoef(patches)
        
        # Encontrar correlaciones altas (excluyendo diagonal)
        high_corr_pairs = []
        for i in range(len(patches)):
            for j in range(i+1, len(patches)):
                if correlation_matrix[i, j] > 0.8:  # Umbral de correlación alta
                    high_corr_pairs.append({
                        "pos1": positions[i],
                        "pos2": positions[j],
                        "correlation": float(correlation_matrix[i, j])
                    })
        
        return {
            "available": True,
            "high_correlation_pairs": len(high_corr_pairs),
            "pairs": high_corr_pairs[:10]  # Limitar a 10 para no sobrecargar
        }
        
    except Exception as e:
        return {"available": False, "reason": f"Error en análisis de patches: {str(e)}"}

# ------------------------ PDF Layer Detection ------------------------

def detect_pdf_layers(image_bytes: bytes) -> Dict[str, Any]:
    """
    Detecta capas ocultas o múltiples streams en imágenes convertidas desde PDF
    """
    try:
        # Buscar patrones de PDF en los bytes
        pdf_patterns = [
            b"/OC",      # Optional Content
            b"/XObject", # External Objects
            b"/Form",    # Form Objects
            b"/Group",   # Group Objects
            b"/Transparency", # Transparency
            b"/Layer"    # Layers
        ]
        
        found_patterns = []
        for pattern in pdf_patterns:
            if pattern in image_bytes:
                found_patterns.append(pattern.decode('utf-8', errors='ignore'))
        
        # Buscar metadatos de PDF
        pdf_metadata = {}
        if b"PDF" in image_bytes[:100]:
            pdf_metadata["pdf_signature"] = True
        
        # Buscar streams múltiples
        stream_count = image_bytes.count(b"stream")
        endstream_count = image_bytes.count(b"endstream")
        
        return {
            "available": True,
            "pdf_patterns_found": found_patterns,
            "pdf_metadata": pdf_metadata,
            "stream_count": stream_count,
            "endstream_count": endstream_count,
            "suspicious": len(found_patterns) > 2 or stream_count > 5
        }
        
    except Exception as e:
        return {"available": False, "reason": f"Error detectando capas PDF: {str(e)}"}

# ------------------------ OCR and Rules ------------------------

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
    
    # Verificar configuración de Tesseract
    if not configure_tesseract():
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

    dates = []
    for rx in DATE_REGEXES:
        dates += re.findall(rx, text)
    res["dates"] = list(sorted(set(dates)))

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

    consistent = None
    if subtotal is not None and total is not None:
        if iva is None:
            consistent = abs(subtotal - total) < max(0.02, 0.01 * total)
        else:
            consistent = abs((subtotal + iva) - total) < max(0.02, 0.01 * total)
    res["checks"]["amounts_consistent"] = consistent

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

# ------------------------ Metadata Analysis ------------------------

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

def extract_xmp_from_bytes(b: bytes) -> Optional[str]:
    m = re.search(br"<x:xmpmeta[^>]*>.*?</x:xmpmeta>", b, flags=re.DOTALL)
    if m:
        try:
            return m.group(0).decode("utf-8", errors="ignore")
        except Exception:
            return None
    return None

def parse_xmp_dates(xmp: str) -> Dict[str, str]:
    tags = {
        "xmp_CreateDate": r"<xmp:CreateDate>([^<]+)</xmp:CreateDate>",
        "xmp_ModifyDate": r"<xmp:ModifyDate>([^<]+)</xmp:ModifyDate>",
        "photoshop_DateCreated": r"<photoshop:DateCreated>([^<]+)</photoshop:DateCreated>",
        "exif_DateTimeOriginal": r"<exif:DateTimeOriginal>([^<]+)</exif:DateTimeOriginal>",
        "exif_DateTimeDigitized": r"<exif:DateTimeDigitized>([^<]+)</exif:DateTimeDigitized>",
        "tiff_DateTime": r"<tiff:DateTime>([^<]+)</tiff:DateTime>",
        "CreatorTool": r"<xmp:CreatorTool>([^<]+)</xmp:CreatorTool>",
    }
    out: Dict[str, str] = {}
    for k, pattern in tags.items():
        m = re.search(pattern, xmp, flags=re.DOTALL)
        if m:
            out[k] = m.group(1).strip()
    return out

def try_parse_date(s: str) -> Optional[datetime]:
    if not s: return None
    s = s.strip()
    fmts = ["%Y:%m:%d %H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S","%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%S.%f%z","%Y-%m-%d"]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue
    return None

def validate_date_consistency(exif_dates: Dict[str, str], xmp_fields: Dict[str, str], exif_meta: Dict[str, Any] = None) -> Dict[str, Any]:
    validation = {
        "score": 0.0,
        "issues": [],
        "warnings": [],
        "date_analysis": {},
        "suspicious_patterns": []
    }
    
    all_dates = {}
    all_dates.update({k: v for k, v in exif_dates.items() if v})
    all_dates.update({k: v for k, v in xmp_fields.items() if v})
    
    parsed_dates = {}
    for key, date_str in all_dates.items():
        parsed = try_parse_date(date_str)
        if parsed:
            parsed_dates[key] = parsed
    
    validation["date_analysis"] = {
        "total_dates_found": len(parsed_dates),
        "dates_parsed": {k: v.isoformat() for k, v in parsed_dates.items()},
        "date_sources": list(parsed_dates.keys())
    }
    
    exif_date_count = sum(1 for v in exif_dates.values() if v.strip())
    if exif_date_count == 0:
        validation["issues"].append("Sin fechas EXIF - posible imagen procesada/editada")
        validation["score"] += 15.0
        validation["suspicious_patterns"].append("no_exif_dates")
    
    if exif_meta:
        non_empty_fields = sum(1 for k, v in exif_meta.items() if v and str(v).strip() and v != 0)
        if non_empty_fields <= 2:
            validation["issues"].append("EXIF mínimo - posible imagen re-procesada")
            validation["score"] += 10.0
            validation["suspicious_patterns"].append("minimal_exif")
    
    if exif_meta:
        camera_fields = ["Make", "Model", "Software", "Artist"]
        camera_data = sum(1 for field in camera_fields if exif_meta.get(field, "").strip())
        if camera_data == 0:
            validation["warnings"].append("Sin metadatos de cámara/dispositivo")
            validation["score"] += 5.0
            validation["suspicious_patterns"].append("no_camera_metadata")
    
    if len(parsed_dates) < 2:
        validation["warnings"].append("Muy pocas fechas para validación temporal")
    
    dates_list = list(parsed_dates.values())
    dates_list.sort()
    
    original = parsed_dates.get("exif_DateTimeOriginal")
    digitized = parsed_dates.get("exif_DateTimeDigitized") 
    modify = parsed_dates.get("exif_ModifyDate") or parsed_dates.get("exif_DateTime")
    
    if original and digitized and original > digitized:
        validation["issues"].append("DateTimeOriginal posterior a DateTimeDigitized")
        validation["score"] += 15.0
        validation["suspicious_patterns"].append("inconsistent_creation_digitization")
    
    if digitized and modify and digitized > modify:
        validation["issues"].append("DateTimeDigitized posterior a fecha de modificación")
        validation["score"] += 10.0
        validation["suspicious_patterns"].append("digitization_after_modification")
    
    max_diff = 0
    for i in range(len(dates_list) - 1):
        diff_days = (dates_list[i+1] - dates_list[i]).days
        max_diff = max(max_diff, diff_days)
        
        if diff_days > 365:
            validation["issues"].append(f"Diferencia temporal extrema: {diff_days} días entre fechas")
            validation["score"] += 8.0
            validation["suspicious_patterns"].append("extreme_time_difference")
    
    now = datetime.now()
    for key, date in parsed_dates.items():
        if date > now:
            validation["issues"].append(f"Fecha futura detectada en {key}: {date.isoformat()}")
            validation["score"] += 20.0
            validation["suspicious_patterns"].append("future_date")
    
    old_threshold = datetime(1990, 1, 1)
    for key, date in parsed_dates.items():
        if date < old_threshold:
            validation["warnings"].append(f"Fecha muy antigua en {key}: {date.isoformat()}")
            validation["score"] += 5.0
    
    software_dates = [k for k in parsed_dates.keys() if "software" in k.lower() or "creator" in k.lower()]
    if software_dates:
        validation["warnings"].append("Fechas de software detectadas - posible edición")
        validation["score"] += 3.0
    
    if len(set(parsed_dates.values())) == 1:
        validation["issues"].append("Todas las fechas son idénticas - posible manipulación")
        validation["score"] += 12.0
        validation["suspicious_patterns"].append("identical_dates")
    
    xmp_dates = [d for k, d in parsed_dates.items() if "xmp" in k.lower()]
    exif_dates_parsed = [d for k, d in parsed_dates.items() if "exif" in k.lower()]
    
    if xmp_dates and exif_dates_parsed:
        xmp_latest = max(xmp_dates)
        exif_latest = max(exif_dates_parsed)
        if xmp_latest > exif_latest:
            diff_hours = (xmp_latest - exif_latest).total_seconds() / 3600
            if diff_hours > 1:
                validation["issues"].append(f"XMP más reciente que EXIF por {diff_hours:.1f} horas")
                validation["score"] += 8.0
                validation["suspicious_patterns"].append("xmp_newer_than_exif")
    
    if exif_meta:
        if any(keyword in str(exif_meta.get("Software", "")).lower() for keyword in ["whatsapp", "telegram", "instagram"]):
            validation["warnings"].append("Imagen de aplicación de mensajería - posible compresión/edición")
            validation["score"] += 3.0
            validation["suspicious_patterns"].append("messaging_app_compression")
        
        x_res = exif_meta.get("XResolution", 0)
        y_res = exif_meta.get("YResolution", 0)
        if x_res > 0 and y_res > 0:
            if x_res != y_res:
                validation["warnings"].append("Resoluciones X/Y diferentes - posible re-escaneo")
                validation["score"] += 2.0
                validation["suspicious_patterns"].append("unequal_resolution")
        
        if exif_meta.get("Make", "") == "" and exif_meta.get("Model", "") == "":
            if any(exif_meta.get(field, "") for field in ["Software", "Artist", "Copyright"]):
                validation["issues"].append("Datos de cámara ausentes pero otros metadatos presentes")
                validation["score"] += 8.0
                validation["suspicious_patterns"].append("missing_camera_data_with_other_metadata")
    
    validation["score"] = min(validation["score"], 50.0)
    return validation

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

# ------------------------ Main Analysis Function ------------------------

def analyze_image_from_bytes(image_bytes: bytes) -> Dict[str, Any]:
    # Abrir imagen
    img = Image.open(io.BytesIO(image_bytes))
    fmt = (getattr(img, "format", None) or "").upper()
    
    # Metadata
    exif_ok, exif_soft, exif_dates, exif_meta = extract_exif(img)
    xmp_str = extract_xmp_from_bytes(image_bytes)
    xmp_fields = parse_xmp_dates(xmp_str) if xmp_str else {}
    
    date_validation = validate_date_consistency(exif_dates, xmp_fields, exif_meta)

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

    # Copy-Move mejorado
    img_array = np.array(img)
    cm = enhanced_copy_move_detection(img_array)

    # Detección de texto superpuesto
    text_overlays = detect_text_overlays(img)

    # Detección de capas PDF
    pdf_layers = detect_pdf_layers(image_bytes)

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
    
    # Copy-Move mejorado
    cm_score = float((cm.get("combined_score", 0.0)) * 15)
    
    # Texto superpuesto
    overlay_score = 0.0
    if text_overlays.get("available", False):
        overlay_count = text_overlays.get("count", 0)
        if overlay_count >= 3:
            overlay_score = 8.0
        elif overlay_count >= 1:
            overlay_score = 4.0
        
        # Análisis de fuentes sospechoso
        font_analysis = text_overlays.get("font_analysis", {})
        if font_analysis.get("suspicious", False):
            overlay_score += 3.0
    
    # Capas PDF sospechosas
    pdf_score = 0.0
    if pdf_layers.get("available", False) and pdf_layers.get("suspicious", False):
        pdf_score = 5.0
    
    inc = rules.get("checks", {}).get("amounts_consistent")
    ocr_score = 0.0
    if inc is False:
        ocr_score = 10.0

    editor_hit = False
    editor_names = ("photoshop", "gimp", "affinity", "pixelmator", "lightroom", "illustrator", "acrobat")
    if exif_soft and any(s in exif_soft.lower() for s in editor_names):
        editor_hit = True
    xmp_ct = (xmp_fields.get("CreatorTool") or "").lower()
    if any(s in xmp_ct for s in editor_names):
        editor_hit = True
    
    exif_score = 5.0 if editor_hit else (0.0 if exif_ok else 2.0)
    
    date_score = float(date_validation.get("score", 0.0))

    total = float(r_score + o_score + e_score + s_score + cm_score + overlay_score + pdf_score + ocr_score + exif_score + date_score)
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
            "exif_dates": exif_dates,
            "xmp_present": bool(xmp_str),
            "xmp_fields": xmp_fields
        },
        "date_validation": date_validation,
        "ela": {
            "mean": ela_mean, 
            "std": ela_std, 
            "p95": ela_p95,
            "smooth_edge_ratio": ela_ratio, 
            "outlier_rate": float(outlier_rate),
            "quality_slope": float(slope)
        },
        "copy_move": cm,
        "text_overlays": text_overlays,
        "pdf_layers": pdf_layers,
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
                "text_overlays": round(overlay_score, 2),
                "pdf_layers": round(pdf_score, 2),
                "ocr_inconsistency": round(ocr_score, 2),
                "editor_software": round(exif_score, 2),
                "date_validation": round(date_score, 2)
            }
        },
        "conclusion": conclusion,
        "notes": note
    }

# ------------------------ API Endpoints ------------------------

@router.post("/analizar-imagen-forense")
async def analizar_imagen_forense(file: UploadFile = File(...)):
    """
    Análisis forense completo de imágenes
    Incluye: ELA, Copy-Move, OCR, validación de metadatos
    """
    try:
        # Validar tipo de archivo
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
        
        # Leer contenido del archivo
        image_bytes = await file.read()
        
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío")
        
        # Realizar análisis forense
        resultado = analyze_image_from_bytes(image_bytes)
        
        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size": len(image_bytes),
            "analisis_forense": resultado
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error en análisis forense: {str(e)}",
                "filename": file.filename if file else "unknown"
            }
        )

@router.get("/analisis-forense-info")
async def info_analisis_forense():
    """
    Información sobre el análisis forense de imágenes
    """
    return {
        "endpoint": "/analizar-imagen-forense",
        "metodo": "POST",
        "descripcion": "Análisis forense completo de imágenes",
        "parametros": {
            "file": "Archivo de imagen (multipart/form-data)"
        },
        "analisis_incluidos": [
            "ELA (Error Level Analysis)",
            "Detección Copy-Move mejorada (ORB + SIFT + correlación)",
            "Detección de texto superpuesto",
            "Análisis de consistencia de fuentes",
            "Detección de capas PDF ocultas",
            "OCR y validación de reglas de negocio",
            "Análisis de metadatos EXIF/XMP",
            "Validación de consistencia temporal",
            "Detección de software de edición"
        ],
        "formatos_soportados": [
            "JPEG", "PNG", "TIFF", "BMP", "WEBP"
        ],
        "dependencias": {
            "opencv": cv2 is not None,
            "pytesseract": pytesseract is not None,
            "sklearn": SKLEARN_AVAILABLE,
            "pil": True
        }
    }
