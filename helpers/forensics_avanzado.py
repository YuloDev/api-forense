#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Análisis forense avanzado para imágenes
Integra técnicas del doc_forensics_pro.py para detección de alteraciones
"""

import numpy as np
import cv2
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ExifTags
from typing import Dict, Any, Optional, Tuple, List
import re
from datetime import datetime
import os

def compute_ela_advanced(original: Image.Image, quality: int = 90, enhance_factor: float = 20.0) -> Tuple[Image.Image, np.ndarray]:
    """
    ELA avanzado con mejor detección de recompresiones
    """
    # Convertir a JPEG para análisis ELA
    from io import BytesIO
    buf = BytesIO()
    try:
        original.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True, subsampling=0)
    except Exception:
        original.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    resaved = Image.open(buf).convert("RGB")
    
    # Calcular diferencia
    diff = ImageChops.difference(original.convert("RGB"), resaved)
    diff_gray = diff.convert("L")
    
    # Procesamiento avanzado
    diff_array = np.asarray(diff_gray, dtype=np.float32)
    diff_normalized = np.clip(diff_array / 255.0, 0, 1)
    diff_thresholded = np.where(diff_normalized > 0.01, diff_normalized * 255, 0)
    
    ela_vis = ImageEnhance.Brightness(Image.fromarray(diff_thresholded.astype(np.uint8), mode="L")).enhance(enhance_factor)
    ela_np = diff_thresholded.astype(np.float32)
    
    return ela_vis, ela_np

def compute_edges_advanced(gray_np: np.ndarray, threshold: float = None) -> np.ndarray:
    """
    Detección de bordes mejorada
    """
    img = Image.fromarray(gray_np.astype(np.uint8), mode="L").filter(ImageFilter.FIND_EDGES)
    arr = np.asarray(img, dtype=np.float32)
    if threshold is None:
        threshold = np.percentile(arr, 75)
    mask = (arr >= threshold).astype(np.uint8)
    return mask

def block_stats_advanced(ela_np: np.ndarray, block: int = 8) -> Tuple[np.ndarray, float, float]:
    """
    Análisis estadístico de bloques ELA
    """
    h, w = ela_np.shape
    bh = h // block; bw = w // block
    trimmed = ela_np[:bh*block, :bw*block]
    reshaped = trimmed.reshape(bh, block, bw, block)
    block_means = reshaped.mean(axis=(1, 3))
    mu = float(block_means.mean())
    sigma = float(block_means.std())
    return block_means, mu, sigma

def local_outlier_rate_advanced(block_means: np.ndarray, z_thresh: float = 3.0) -> float:
    """
    Detección de outliers locales en bloques ELA
    """
    mu = float(block_means.mean())
    sigma = float(block_means.std() + 1e-6)
    z = (block_means - mu) / sigma
    return float((np.abs(z) > z_thresh).mean())

def quality_slope_analysis(original: Image.Image, q_list=(95, 90, 85, 80)) -> float:
    """
    Análisis de pendiente de calidad para detectar recompresiones
    """
    means = []; xs = []
    for q in q_list:
        _, ela_np = compute_ela_advanced(original, quality=q, enhance_factor=1.0)
        means.append(float(ela_np.mean()))
        xs.append(float(100 - q))
    x = np.array(xs); y = np.array(means)
    x = x - x.mean(); y = y - y.mean()
    denom = (x**2).sum() + 1e-9
    slope = float((x*y).sum() / denom)
    return slope

def copy_move_detection_orb(image_path: str) -> Dict[str, Any]:
    """
    Detección de copy-move usando ORB/RANSAC
    """
    if cv2 is None:
        return {"available": False, "reason": "OpenCV no instalado", "matches": 0}

    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return {"available": False, "reason": "No se pudo leer imagen", "matches": 0}
    
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Detectar características con ORB
    orb = cv2.ORB_create(nfeatures=5000, scoreType=cv2.ORB_HARRIS_SCORE)
    kps, des = orb.detectAndCompute(gray, None)
    
    if des is None or len(kps) < 50:
        return {"available": True, "matches": 0, "note": "Muy pocos keypoints"}

    # Matching con BFMatcher
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des, des, k=2)

    # Filtrar matches buenos
    good = []
    for m, n in matches:
        if m.trainIdx == m.queryIdx:
            continue
        if m.distance < 0.75 * n.distance:
            p1 = np.array(kps[m.queryIdx].pt)
            p2 = np.array(kps[m.trainIdx].pt)
            if np.linalg.norm(p1 - p2) > 20.0:  # Evitar matches muy cercanos
                good.append((m.queryIdx, m.trainIdx))

    good = list(set(tuple(sorted(x)) for x in good))  # dedup
    match_count = len(good)

    # Calcular densidad de matches
    H, W = gray.shape
    density = match_count / max(1.0, (H * W) / (1000 * 1000))  # matches por megapixel
    cm_score = min(1.0, density / 200.0)  # normalizar a 0-1

    return {
        "available": True,
        "matches": int(match_count),
        "density_per_MPx": float(density),
        "score_0_1": float(cm_score)
    }

def extract_exif_advanced(img: Image.Image) -> Tuple[bool, str, Dict[str, str], Dict[str, Any]]:
    """
    Extracción avanzada de metadatos EXIF
    """
    try:
        raw = img.getexif()
        if not raw or len(raw) == 0:
            return False, "", {}, {}
        
        exif = {ExifTags.TAGS.get(k, k): v for k, v in raw.items()}
        software = str(exif.get("Software", "")).strip()
        
        # Fechas EXIF
        exif_dates = {
            "exif_DateTimeOriginal": str(exif.get("DateTimeOriginal", "")).strip(),
            "exif_DateTimeDigitized": str(exif.get("DateTimeDigitized", "")).strip(),
            "exif_DateTime": str(exif.get("DateTime", "")).strip(),
            "exif_ModifyDate": str(exif.get("ModifyDate", "")).strip(),
            "exif_CreateDate": str(exif.get("CreateDate", "")).strip(),
        }
        
        # Metadatos adicionales
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
    """
    Extraer metadatos XMP de bytes
    """
    m = re.search(br"<x:xmpmeta[^>]*>.*?</x:xmpmeta>", b, flags=re.DOTALL)
    if m:
        try:
            return m.group(0).decode("utf-8", errors="ignore")
        except Exception:
            return None
    return None

def parse_xmp_dates(xmp: str) -> Dict[str, str]:
    """
    Parsear fechas de XMP
    """
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
    """
    Parsear fechas con múltiples formatos
    """
    if not s: return None
    s = s.strip()
    fmts = ["%Y:%m:%d %H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S","%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%S.%f%z","%Y-%m-%d"]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue
    return None

def validate_date_consistency_advanced(exif_dates: Dict[str, str], xmp_fields: Dict[str, str], file_modified: Optional[datetime] = None, exif_meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Validación avanzada de consistencia temporal
    """
    validation = {
        "score": 0.0,
        "issues": [],
        "warnings": [],
        "date_analysis": {},
        "suspicious_patterns": []
    }
    
    # Recopilar todas las fechas
    all_dates = {}
    all_dates.update({k: v for k, v in exif_dates.items() if v})
    all_dates.update({k: v for k, v in xmp_fields.items() if v})
    
    if file_modified:
        all_dates["file_modified"] = file_modified.strftime("%Y:%m:%d %H:%M:%S")
    
    # Parsear fechas
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
    
    # DETECCIÓN: Sin fechas EXIF es sospechoso
    exif_date_count = sum(1 for v in exif_dates.values() if v.strip())
    if exif_date_count == 0:
        validation["issues"].append("Sin fechas EXIF - posible imagen procesada/editada")
        validation["score"] += 15.0
        validation["suspicious_patterns"].append("no_exif_dates")
    
    # DETECCIÓN: EXIF mínimo es sospechoso
    if exif_meta:
        non_empty_fields = sum(1 for k, v in exif_meta.items() if v and str(v).strip() and v != 0)
        if non_empty_fields <= 2:
            validation["issues"].append("EXIF mínimo - posible imagen re-procesada")
            validation["score"] += 10.0
            validation["suspicious_patterns"].append("minimal_exif")
    
    # DETECCIÓN: Ausencia de metadatos de cámara
    if exif_meta:
        camera_fields = ["Make", "Model", "Software", "Artist"]
        camera_data = sum(1 for field in camera_fields if exif_meta.get(field, "").strip())
        if camera_data == 0:
            validation["warnings"].append("Sin metadatos de cámara/dispositivo")
            validation["score"] += 5.0
            validation["suspicious_patterns"].append("no_camera_metadata")
    
    # Análisis de consistencia temporal
    dates_list = list(parsed_dates.values())
    dates_list.sort()
    
    # Verificar orden lógico
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
    
    # Verificar fechas futuras
    now = datetime.now()
    for key, date in parsed_dates.items():
        if date > now:
            validation["issues"].append(f"Fecha futura detectada en {key}: {date.isoformat()}")
            validation["score"] += 20.0
            validation["suspicious_patterns"].append("future_date")
    
    # Verificar fechas idénticas (sospechoso)
    if len(set(parsed_dates.values())) == 1:
        validation["issues"].append("Todas las fechas son idénticas - posible manipulación")
        validation["score"] += 12.0
        validation["suspicious_patterns"].append("identical_dates")
    
    # Detectar software de edición
    if exif_meta:
        editor_names = ("photoshop", "gimp", "affinity", "pixelmator", "lightroom", "illustrator", "acrobat")
        software = str(exif_meta.get("Software", "")).lower()
        if any(s in software for s in editor_names):
            validation["warnings"].append(f"Software de edición detectado: {software}")
            validation["score"] += 8.0
            validation["suspicious_patterns"].append("editor_software")
    
    validation["score"] = min(validation["score"], 50.0)  # Cap a 50 puntos máximo
    return validation

def analizar_forensics_avanzado(image_path: str) -> Dict[str, Any]:
    """
    Análisis forense avanzado completo para imágenes
    """
    try:
        # Cargar imagen
        img = Image.open(image_path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        
        # Convertir a escala de grises para análisis
        gray_np = np.asarray(img.convert("L"), dtype=np.float32)
        
        # 1. ELA Avanzado
        ela_vis, ela_np = compute_ela_advanced(img, quality=90, enhance_factor=20.0)
        
        # 2. Análisis de bordes
        edge_mask = compute_edges_advanced(gray_np)
        
        # 3. Análisis de bloques ELA
        blocks, mu, sigma = block_stats_advanced(ela_np, block=8)
        outlier_rate = local_outlier_rate_advanced(blocks, 3.0)
        
        # 4. Análisis de calidad
        slope = quality_slope_analysis(img, (95, 90, 85, 80))
        
        # 5. Copy-Move Detection
        copy_move = copy_move_detection_orb(image_path)
        
        # 6. Metadatos EXIF
        exif_ok, exif_soft, exif_dates, exif_meta = extract_exif_advanced(img)
        
        # 7. Metadatos XMP
        with open(image_path, 'rb') as f:
            bts = f.read()
        xmp_str = extract_xmp_from_bytes(bts)
        xmp_fields = parse_xmp_dates(xmp_str) if xmp_str else {}
        
        # 8. Validación temporal
        file_modified = None
        try:
            file_modified = datetime.fromtimestamp(os.path.getmtime(image_path))
        except Exception:
            pass
        
        date_validation = validate_date_consistency_advanced(exif_dates, xmp_fields, file_modified, exif_meta)
        
        # 9. Cálculo de métricas ELA
        ela_mean = float(ela_np.mean())
        ela_std = float(ela_np.std())
        ela_p95 = float(np.percentile(ela_np, 95))
        ela_edge_mean = float(ela_np[edge_mask == 1].mean()) if edge_mask.sum() > 0 else ela_mean
        ela_smooth_mean = float(ela_np[edge_mask == 0].mean()) if (edge_mask == 0).sum() > 0 else ela_mean
        ela_ratio = float((ela_smooth_mean + 1e-6) / (ela_edge_mean + 1e-6))
        
        # 10. Cálculo de scores
        r_score = float(np.clip((ela_ratio - 0.6) / (1.2 - 0.6), 0, 1) * 25)
        o_score = float(np.clip(outlier_rate / 0.15, 0, 1) * 20)
        e_score = float(np.clip((ela_p95 / 255.0 - 0.12) / (0.28 - 0.12), 0, 1) * 10)
        
        if slope >= 0:
            s_score = float(np.clip(0.08 - slope, 0, 0.08) / 0.08 * 8)
        else:
            s_score = float(np.clip(abs(slope), 0, 0.1) / 0.1 * 8)
        
        cm_score = float((copy_move.get("score_0_1", 0.0)) * 22)
        date_score = float(date_validation.get("score", 0.0))
        
        # Detectar software de edición
        editor_hit = False
        editor_names = ("photoshop", "gimp", "affinity", "pixelmator", "lightroom", "illustrator", "acrobat")
        if exif_soft and any(s in exif_soft.lower() for s in editor_names):
            editor_hit = True
        xmp_ct = (xmp_fields.get("CreatorTool") or "").lower()
        if any(s in xmp_ct for s in editor_names):
            editor_hit = True
        
        exif_score = 5.0 if editor_hit else (0.0 if exif_ok else 2.0)
        
        # Score total
        total = float(r_score + o_score + e_score + s_score + cm_score + exif_score + date_score)
        total = max(0.0, min(100.0, total))
        
        # Clasificación
        if total < 25:
            label = "Baja (poco probable manipulación)"
        elif total < 50:
            label = "Media (revisar con más pruebas)"
        elif total < 75:
            label = "Alta (indicios claros, validar)"
        else:
            label = "Muy alta (probable manipulación)"
        
        return {
            "disponible": True,
            "score_total": round(total, 2),
            "nivel_sospecha": label,
            "metodologia": "forensics_avanzado",
            "metricas": {
                "ela_ratio": round(ela_ratio, 4),
                "outlier_rate": round(outlier_rate, 4),
                "ela_intensity": round(ela_p95, 2),
                "quality_slope": round(slope, 4),
                "copy_move_matches": copy_move.get("matches", 0),
                "copy_move_density": round(copy_move.get("density_per_MPx", 0), 2)
            },
            "scores_detallados": {
                "ela_ratio": round(r_score, 2),
                "outliers": round(o_score, 2),
                "ela_intensity": round(e_score, 2),
                "quality_slope": round(s_score, 2),
                "copy_move": round(cm_score, 2),
                "editor_software": round(exif_score, 2),
                "date_validation": round(date_score, 2)
            },
            "metadatos": {
                "exif_presente": exif_ok,
                "exif_software": exif_soft,
                "xmp_presente": bool(xmp_str),
                "fechas_encontradas": len(parsed_dates) if 'parsed_dates' in locals() else 0
            },
            "validacion_temporal": date_validation,
            "copy_move_analysis": copy_move,
            "interpretacion": {
                "ela_ratio_interpretacion": "Valores > 1.2 indican posible recompresión" if ela_ratio > 1.2 else "Valores normales",
                "outlier_interpretacion": "Alto porcentaje de outliers indica posible edición" if outlier_rate > 0.15 else "Distribución normal",
                "copy_move_interpretacion": "Regiones clonadas detectadas" if copy_move.get("matches", 0) > 0 else "Sin clonado detectado",
                "metadatos_interpretacion": "Metadatos completos" if exif_ok else "Metadatos incompletos o ausentes"
            }
        }
        
    except Exception as e:
        return {
            "disponible": False,
            "error": str(e),
            "metodologia": "forensics_avanzado"
        }

