import io
import re
from typing import Any, Dict, List, Tuple, Union

import cv2
import numpy as np
from PIL import Image

# Importar detector de texto inyectado
try:
    from .texto_inyectado_analisis import detectar_texto_inyectado
except ImportError:
    # Fallback si no se puede importar
    detectar_texto_inyectado = None


# ---------------------- Utilidades ----------------------

def _to_bgr(img_or_bytes: Union[bytes, np.ndarray]) -> np.ndarray:
    if isinstance(img_or_bytes, (bytes, bytearray)):
        arr = np.frombuffer(img_or_bytes, np.uint8)
        im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if im is None:
            raise ValueError("Bytes no representan una imagen válida.")
        return im
    im = img_or_bytes
    if im.ndim == 2:
        return cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    return im


def _merge_overlaps(boxes: List[Tuple[int,int,int,int]], iou_thr: float = 0.2) -> List[Tuple[int,int,int,int]]:
    """Une cajas solapadas para no contar mil fragmentos del mismo texto."""
    if not boxes:
        return []
    boxes = np.array(boxes, dtype=np.float32)
    x1 = boxes[:,0]; y1 = boxes[:,1]; w = boxes[:,2]; h = boxes[:,3]
    x2 = x1 + w; y2 = y1 + h

    order = np.argsort(y1 + 0.1*x1)  # orden estable (aprox. por filas)
    keep = []
    used = np.zeros(len(order), np.bool_)
    for idx in order:
        if used[idx]: 
            continue
        xx1 = np.maximum(x1[idx], x1[~used])
        yy1 = np.maximum(y1[idx], y1[~used])
        xx2 = np.minimum(x2[idx], x2[~used])
        yy2 = np.minimum(y2[idx], y2[~used])
        inter = np.maximum(0, xx2-xx1) * np.maximum(0, yy2-yy1)
        area_i = (x2[idx]-x1[idx])*(y2[idx]-y1[idx])
        area_j = (x2[~used]-x1[~used])*(y2[~used]-y1[~used])
        iou = inter / (area_i + area_j - inter + 1e-6)
        used[np.where(~used)[0][iou > iou_thr]] = True
        used[idx] = True
        keep.append((int(x1[idx]), int(y1[idx]), int(w[idx]), int(h[idx])))
    return keep


def _stroke_width_stats(bin_box: np.ndarray) -> Tuple[float,float,int]:
    """
    Proxy de SWT: distancia al fondo dentro del texto.
    - Binariza (texto=1, fondo=0), DT sobre fondo invertido.
    - Estima ancho de trazo como 2*DT en máximos locales (esqueleto aproximado).
    """
    # asegúrate de que texto sea blanco (255) sobre negro (0)
    if bin_box.mean() < 127:
        bin_box = 255 - bin_box

    inv = 255 - bin_box
    dt = cv2.distanceTransform(inv, cv2.DIST_L2, 3)
    # "crestas" (máximos locales) ≈ eje medial del trazo
    dil = cv2.dilate(dt, np.ones((3,3), np.uint8))
    skeleton_mask = (dt >= dil - 1e-6) & (dt > 0.5)
    widths = (2.0 * dt[skeleton_mask]).ravel()
    widths = widths[(widths > 0.8) & (widths < 80)]  # limpia outliers obvios
    if widths.size < 10:
        return 0.0, 0.0, int(widths.size)
    return float(widths.mean()), float(widths.std()), int(widths.size)


def _color_purity(gray_box: np.ndarray, edge_mask: np.ndarray) -> Tuple[float, bool]:
    """
    Promedio de gris en el trazo (cerca de bordes) y si es "casi puro" (≈negro o ≈blanco).
    """
    band = cv2.dilate(edge_mask.astype(np.uint8)*255, np.ones((3,3), np.uint8), iterations=1) > 0
    vals = gray_box[band]
    if vals.size == 0:
        return 0.0, False
    mean = float(vals.mean()); std = float(vals.std())
    # "casi puro" si muy cerca de 0 o 255 y poca varianza
    near_black = (mean < 40 and std < 30)
    near_white = (mean > 215 and std < 30)
    return mean, bool(near_black or near_white)


def _halo_ratio(gray_box: np.ndarray, edge_mask: np.ndarray) -> float:
    """
    Relación de energía de borde fuera-dentro (anillo externo vs franja interna).
    >0.45 suele indicar "halo"/anti-aliasing muy limpio típico de texto renderizado.
    """
    edges = edge_mask.astype(np.uint8)
    inner = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
    outer = cv2.dilate(edges, np.ones((5,5), np.uint8), iterations=1)
    ring_out = (outer > 0) & (inner == 0)
    ring_in  = (inner > 0)

    # energía de gradiente
    gx = cv2.Sobel(gray_box, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray_box, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx*gx + gy*gy)

    out_e = float(mag[ring_out].mean()) if ring_out.any() else 0.0
    in_e  = float(mag[ring_in].mean())  if ring_in.any()  else 1e-6
    return out_e / (in_e + 1e-6)


def _many_lines_count(gray: np.ndarray) -> Tuple[int, int, float]:
    """
    Conteo ligero de "líneas" horizontales/verticales (texto impreso suele dar muchos segmentos).
    """
    edges = cv2.Canny(gray, 60, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=60, minLineLength=25, maxLineGap=6)
    n = 0 if lines is None else len(lines)
    horiz = 0 if lines is None else np.sum(np.abs(lines[:,0,1] - lines[:,0,3]) <= 1)
    vert  = 0 if lines is None else np.sum(np.abs(lines[:,0,0] - lines[:,0,2]) <= 1)
    dens = n / float(gray.shape[0]*gray.shape[1]) * 1e4  # segmentos por 10k px
    return int(n), int(horiz+vert), float(dens)


# ---------------------- Detector principal ----------------------

def detectar_texto_sintetico_aplanado(
    img_or_bytes: Union[bytes, np.ndarray],
    ocr_text: str = ""
) -> Dict[str, Any]:
    """
    Detector de TEXTO SINTÉTICO APLANADO.
    Señales fuertes: muchas cajas de texto + trazo con grosor casi constante + color casi puro + halo alto.
    Marca PRIORITARIO si además coincide con montos/fechas en el OCR.
    """
    bgr = _to_bgr(img_or_bytes)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # pre: preserva bordes, reduce ruido
    gray_f = cv2.bilateralFilter(gray, d=7, sigmaColor=25, sigmaSpace=7)

    # --- 1) Candidatos a texto con MSER ---
    mser = cv2.MSER_create(delta=5, min_area=60, max_area=int(0.05*gray.size))
    regions, _ = mser.detectRegions(gray_f)
    boxes = []
    H, W = gray.shape
    for r in regions:
        x,y,w,h = cv2.boundingRect(r)
        if w*h < 80: 
            continue
        ar = w / float(h)
        # filtros geométricos amplios para texto
        if 0.15 <= ar <= 15.0 and 8 <= h <= int(0.25 * H):
            boxes.append((x,y,w,h))

    boxes = _merge_overlaps(boxes, iou_thr=0.2)
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))

    # si hay poquísimas cajas, devolvemos temprano
    if len(boxes) == 0:
        n_lines, hv, dens = _many_lines_count(gray)
        return {
            "tiene_texto_sintetico": False,
            "nivel_sospecha": "BAJO",
            "swt_analisis": {"cajas_texto_detectadas": 0, "stroke_width_mean": 0, "stroke_width_std": 0, "stroke_width_uniforme": False},
            "color_antialias_analisis": {"color_trazo_promedio": 0, "color_casi_puro": False},
            "halo_analisis": {"halo_ratio_promedio": 0.0},
            "reguardado_analisis": {"lineas_totales": n_lines, "horiz_vert": hv, "densidad_lineas_10kpx": dens},
            "coincide_con_montos_fechas": False,
            "detalles_cajas": []
        }

    # --- 2) Métricas por caja ---
    details = []
    sw_means, sw_stds, purities, halos = [], [], [], []
    edges_global = cv2.Canny(gray_f, 80, 180)

    for (x,y,w,h) in boxes:
        crop_g = gray_f[max(0,y-2):min(H,y+h+2), max(0,x-2):min(W,x+w+2)]
        if crop_g.size == 0:
            continue
        # binariza local (texto vs fondo)
        _, bin_box = cv2.threshold(crop_g, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        # bordes locales
        edges = cv2.Canny(crop_g, 80, 180)

        sw_mean, sw_std, n_pts = _stroke_width_stats(bin_box)
        cmean, pure = _color_purity(crop_g, edges)
        halo = _halo_ratio(crop_g, edges)

        details.append({
            "bbox": (int(x),int(y),int(w),int(h)),
            "stroke_width_mean": sw_mean,
            "stroke_width_std": sw_std,
            "stroke_points": n_pts,
            "color_mean": cmean,
            "color_casi_puro": pure,
            "halo_ratio": halo
        })
        if n_pts >= 10:
            sw_means.append(sw_mean); sw_stds.append(sw_std)
        purities.append(pure); halos.append(halo)

    if len(details) == 0:
        n_lines, hv, dens = _many_lines_count(gray)
        return {
            "tiene_texto_sintetico": False,
            "nivel_sospecha": "BAJO",
            "swt_analisis": {"cajas_texto_detectadas": len(boxes), "stroke_width_mean": 0, "stroke_width_std": 0, "stroke_width_uniforme": False},
            "color_antialias_analisis": {"color_trazo_promedio": 0, "color_casi_puro": False},
            "halo_analisis": {"halo_ratio_promedio": 0.0},
            "reguardado_analisis": {"lineas_totales": n_lines, "horiz_vert": hv, "densidad_lineas_10kpx": dens},
            "coincide_con_montos_fechas": False,
            "detalles_cajas": []
        }

    # agregados
    sw_mean_all = float(np.mean(sw_means)) if sw_means else 0.0
    sw_std_all  = float(np.mean(sw_stds))  if sw_stds  else 0.0
    cv_sw = (sw_std_all / (sw_mean_all + 1e-6)) if sw_mean_all > 0 else 1.0
    stroke_uniform = cv_sw < 0.45  # umbral clave

    color_puro_ratio = float(np.mean(purities)) if purities else 0.0
    halo_mean = float(np.mean(halos)) if halos else 0.0

    n_lines, hv, dens = _many_lines_count(gray)

    # --- 3) Heurística de decisión (explicable) - MEJORADA ---
    muchas_cajas = len(boxes) >= 30 or dens >= 0.8
    trazo_uniforme = stroke_uniform and sw_mean_all >= 1.2
    color_casi_puro = color_puro_ratio >= 0.6
    halo_alto = halo_mean >= 0.45

    # Lógica más flexible: no requiere TODAS las condiciones
    # Si hay muchas cajas Y al menos 2 de las otras 3 condiciones
    condiciones_cumplidas = sum([trazo_uniforme, color_casi_puro, halo_alto])
    
    # Detección más flexible
    tiene_texto_sintetico = bool(
        muchas_cajas and (
            (trazo_uniforme and color_casi_puro) or  # Trazo uniforme + color puro
            (trazo_uniforme and halo_alto) or        # Trazo uniforme + halo alto
            (color_casi_puro and halo_alto) or       # Color puro + halo alto
            (condiciones_cumplidas >= 2 and len(boxes) >= 50)  # Muchas cajas + 2+ condiciones
        )
    )

    # (Opcional) cruza con OCR: ¿hay montos/fechas?
    coincide = False
    if ocr_text:
        ocr = ocr_text.lower()
        # montos: 12.34 / 1,234.56 / $ 45.00
        hay_montos = re.search(r'(?:\$?\s*)\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})', ocr) is not None
        # fechas: 01/02/2025, 2025-02-01, 01-02-25
        hay_fechas = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})', ocr) is not None
        coincide = bool(hay_montos or hay_fechas)

    # --- INTEGRACIÓN CON DETECTOR DE TEXTO INYECTADO ---
    texto_inyectado_info = None
    via_deteccion = "neutro"  # neutro, coloreado, ambos
    
    # Ejecutar detector de texto inyectado si está disponible
    if detectar_texto_inyectado is not None:
        try:
            texto_inyectado_info = detectar_texto_inyectado(bgr)
            
            # Si detecta texto inyectado, refuerza las métricas
            if texto_inyectado_info.get("match", False):
                tiene_texto_sintetico = True  # Forzar detección
                
                # Refuerzo de métricas con datos del detector de texto inyectado
                sospechosos = texto_inyectado_info.get("sospechosos", [])
                if sospechosos:
                    # Actualizar métricas de stroke width con datos del detector
                    w_means = [s["metrics"]["w_mean"] for s in sospechosos if "metrics" in s]
                    if w_means:
                        sw_mean_inyectado = np.mean(w_means)
                        sw_std_inyectado = np.std(w_means)
                        # Promedio ponderado con métricas existentes
                        sw_mean_all = (sw_mean_all + sw_mean_inyectado) / 2
                        sw_std_all = (sw_std_all + sw_std_inyectado) / 2
                        cv_sw = sw_std_all / (sw_mean_all + 1e-6)
                        stroke_uniform = cv_sw <= 0.4
                    
                    # Actualizar número de cajas detectadas
                    boxes.extend([(s["bbox"][0], s["bbox"][1], s["bbox"][2], s["bbox"][3]) for s in sospechosos])
                    
                    # Marcar como coincide con montos/fechas si hay tokens numéricos
                    coincide = True
                
                via_deteccion = "neutro"
        except Exception as e:
            print(f"Error en detector de texto inyectado: {e}")
            texto_inyectado_info = None
    
    # Nivel de sospecha (para tu scoring)
    if tiene_texto_sintetico and coincide:
        nivel = "ALTO"
    elif tiene_texto_sintetico:
        nivel = "MEDIO"
    elif (trazo_uniforme and (color_casi_puro or halo_alto)) or muchas_cajas:
        nivel = "BAJO"
    else:
        nivel = "BAJO"

    return {
        "tiene_texto_sintetico": bool(tiene_texto_sintetico),
        "nivel_sospecha": nivel,
        "via_deteccion": via_deteccion,
        "swt_analisis": {
            "cajas_texto_detectadas": int(len(boxes)),
            "metodo_deteccion": "MSER+filtros" + ("+texto_inyectado" if texto_inyectado_info and texto_inyectado_info.get("match") else ""),
            "stroke_width_mean": float(sw_mean_all),
            "stroke_width_std": float(sw_std_all),
            "stroke_width_uniforme": bool(stroke_uniform),
            "cv_stroke_width": float(cv_sw)
        },
        "color_antialias_analisis": {
            "color_trazo_promedio": float(np.mean([d["color_mean"] for d in details]) if details else 0.0),
            "color_casi_puro": bool(color_casi_puro),
            "ratio_cajas_puras": float(color_puro_ratio)
        },
        "halo_analisis": {
            "halo_ratio_promedio": float(halo_mean),
            "umbral_halo": 0.45
        },
        "reguardado_analisis": {
            "lineas_totales": int(n_lines),
            "horiz_vert": int(hv),
            "densidad_lineas_10kpx": float(dens)
        },
        "coincide_con_montos_fechas": bool(coincide),
        "detalles_cajas": details,
        "texto_inyectado": texto_inyectado_info if texto_inyectado_info else None,
        "cajas_texto": boxes  # Agregar cajas de texto para usar en otros análisis
    }
