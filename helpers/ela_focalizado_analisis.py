import io
import math
from typing import Any, Dict, List, Tuple, Union

import cv2
import numpy as np

# Importar detector de texto superpuesto
try:
    from .texto_superpuesto_analisis import detectar_texto_superpuesto
except ImportError:
    # Fallback si no se puede importar
    detectar_texto_superpuesto = None


# ----------------------------- utilidades base -----------------------------

def _to_gray_u8(img: Union[np.ndarray, bytes]) -> np.ndarray:
    if isinstance(img, (bytes, bytearray)):
        arr = np.frombuffer(img, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError("Bytes no representan una imagen válida.")
    if img.ndim == 2:
        gray = img
    else:
        # descarta alfa si existe y pasa a GRAY
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # estabiliza contraste en documentos
    return cv2.equalizeHist(gray)


def _robust_thr(ela: np.ndarray, k: float = 3.0) -> float:
    med = np.median(ela)
    mad = np.median(np.abs(ela - med)) + 1e-6
    thr = float(med + k * 1.4826 * mad)  # ≈ 3σ robusto
    return max(5.0, min(thr, 255.0))


def _connected_components(mask: np.ndarray, min_sz: int) -> List[np.ndarray]:
    ny, nx = mask.shape
    seen = np.zeros_like(mask, bool)
    comps = []
    for j in range(ny):
        for i in range(nx):
            if not mask[j, i] or seen[j, i]:
                continue
            stack = [(j, i)]
            seen[j, i] = True
            comp = []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    yy, xx = y+dy, x+dx
                    if 0<=yy<ny and 0<=xx<nx and mask[yy,xx] and not seen[yy,xx]:
                        seen[yy,xx] = True
                        stack.append((yy,xx))
            if len(comp) >= min_sz:
                comps.append(np.asarray(comp))
    return comps


def _detect_text_boxes(gray: np.ndarray) -> List[Tuple[int,int,int,int]]:
    """
    Devuelve cajas (x0,y0,x1,y1) con alta probabilidad de texto.
    MSER sobre gray y su invertido + unión morfológica.
    """
    h, w = gray.shape
    mser = cv2.MSER_create(delta=5, min_area=60, max_area=int(0.25*h*w))
    regions1, _ = mser.detectRegions(gray)
    regions2, _ = mser.detectRegions(255 - gray)
    regions = regions1 + regions2

    boxes = []
    for pts in regions:
        x, y, ww, hh = cv2.boundingRect(pts.reshape(-1, 1, 2))
        # filtros rápidos: tamaño razonable y aspecto no extremo
        if ww < 8 or hh < 8:
            continue
        ar = ww / float(hh)
        if 0.3 <= ar <= 15 and ww*hh < 0.3*h*w:
            boxes.append((x, y, x + ww, y + hh))

    # fusiona solapamientos (NMS blando por dilatación en un mapa binario)
    mask = np.zeros((h, w), np.uint8)
    for (x0,y0,x1,y1) in boxes:
        mask[y0:y1, x0:x1] = 255
    if mask.any():
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
        mask = cv2.dilate(mask, kernel, iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        fused = []
        for c in contours:
            x,y,ww,hh = cv2.boundingRect(c)
            fused.append((x,y,x+ww,y+hh))
        return fused
    return []


def _ocr_digits_optional(gray: np.ndarray, boxes: List[Tuple[int,int,int,int]]) -> List[Tuple[int,int,int,int,str]]:
    """
    Si está pytesseract, intenta leer dígitos en cada caja. Si no, devuelve texto="?".
    """
    out = []
    try:
        import pytesseract
        cfg = "--psm 6 -c tessedit_char_whitelist=0123456789.,-"
        for (x0,y0,x1,y1) in boxes:
            roi = gray[max(0,y0):min(gray.shape[0],y1), max(0,x0):min(gray.shape[1],x1)]
            if roi.size == 0:
                out.append((x0,y0,x1,y1,""))
                continue
            # suaviza y binariza suave
            roi_b = cv2.GaussianBlur(roi, (3,3), 0)
            _, roi_b = cv2.threshold(roi_b, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV)
            txt = pytesseract.image_to_string(roi_b, lang="eng", config=cfg)
            txt = "".join(ch for ch in txt if ch.isdigit() or ch in ".,-")
            out.append((x0,y0,x1,y1, txt.strip()))
    except Exception:
        for b in boxes:
            out.append((*b, ""))  # sin OCR disponible
    return out


# ----------------------------- análisis ELA -----------------------------

def analizar_ela_focalizado(
    img: Union[np.ndarray, bytes],
    quality: int = 90,
    grid_min: int = 64,
    perc_thr: float = 0.10,     # 10% (rango recomendado 0.08–0.12)
    ela_max_thr: float = 60.0,  # ELA_max "alto" (0–255)
    robust_k: float = 3.0,      # k para umbral robusto (MAD)
) -> Dict[str, Any]:
    """
    ELA (Error Level Analysis) focalizado:
      - Marca tiles donde (porcentaje_sospechoso >= perc_thr) y (ELA_max >= ela_max_thr).
      - Agrupa tiles en clústeres; si hay clúster/es localizados y se solapan con texto/números,
        marca editada (PRIORITARIO). Si no hay texto, queda SECUNDARIO.

    Retorna métricas completas + decisión.
    """
    gray = _to_gray_u8(img)
    h, w = gray.shape

    # prepara imagen BGR para (re)comprensión JPEG
    bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    ok, enc = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, int(np.clip(quality, 50, 98))])
    if not ok:
        raise RuntimeError("No se pudo recomprimir a JPEG para ELA.")
    jpg = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    jpg_gray = cv2.cvtColor(jpg, cv2.COLOR_BGR2GRAY)

    # mapa ELA y estadísticas globales
    ela_map = cv2.absdiff(gray, jpg_gray).astype(np.float32)
    ela_mean = float(ela_map.mean())
    ela_std  = float(ela_map.std())
    ela_max  = float(ela_map.max())

    thr = _robust_thr(ela_map, k=robust_k)
    sus_mask = (ela_map > thr).astype(np.uint8)

    # grid
    tile = max(grid_min, min(h, w) // 16)
    nx = max(4, w // tile)
    ny = max(4, h // tile)
    tile_w = w // nx
    tile_h = h // ny

    perc = np.zeros((ny, nx), np.float32)
    tmax = np.zeros((ny, nx), np.float32)

    for j in range(ny):
        for i in range(nx):
            y0, y1 = j * tile_h, (j + 1) * tile_h
            x0, x1 = i * tile_w, (i + 1) * tile_w
            roi_m = sus_mask[y0:y1, x0:x1]
            roi_e = ela_map[y0:y1, x0:x1]
            area = roi_m.size or 1
            perc[j, i] = float(roi_m.sum()) / (255.0 * area)  # como proporción (0..1)
            tmax[j, i] = float(roi_e.max()) if roi_e.size else 0.0

    # tiles sospechosos por ELA
    sus_tiles = (perc >= perc_thr) & (tmax >= ela_max_thr)

    # clústeres de tiles sospechosos (localización)
    comps = _connected_components(sus_tiles.astype(np.uint8), min_sz=3)
    clusters = []
    for comp in comps:
        ys, xs = comp[:, 0], comp[:, 1]
        x0 = int(xs.min() * tile_w); y0 = int(ys.min() * tile_h)
        x1 = int(min(w, (xs.max() + 1) * tile_w)); y1 = int(min(h, (ys.max() + 1) * tile_h))
        bbox_area = (x1 - x0) * (y1 - y0)
        tiles_area = comp.shape[0] * tile_w * tile_h
        compactness = float(bbox_area) / float(tiles_area + 1e-6)
        clusters.append({
            "size_tiles": int(comp.shape[0]),
            "bbox": [x0, y0, x1, y1],
            "perc_mean": float(perc[ys, xs].mean()),
            "ela_max_cluster": float(tmax[ys, xs].max()),
            "compactness": compactness,
        })

    localized = [c for c in clusters if c["compactness"] < 6.0]

    # texto / números
    text_boxes = _detect_text_boxes(gray)
    ocr_boxes = _ocr_digits_optional(gray, text_boxes)

    def _overlap(a, b) -> bool:
        ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
        return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)

    overlap_text = False
    overlap_digits = False
    peak_hits = 0

    for c in localized:
        cb = tuple(c["bbox"])
        for (x0,y0,x1,y1,txt) in ocr_boxes:
            tb = (x0,y0,x1,y1)
            if _overlap(cb, tb):
                overlap_text = True
                if any(ch.isdigit() for ch in txt) and len(txt) >= 2:
                    overlap_digits = True
                # ¿pico dentro de la caja?
                # tomamos ELA máx en la intersección rápida aproximando por el ELA máx del clúster
                if c["ela_max_cluster"] >= ela_max_thr:
                    peak_hits += 1

    # --- INTEGRACIÓN CON DETECTOR DE TEXTO SUPERPUESTO ---
    texto_superpuesto_info = None
    if detectar_texto_superpuesto is not None:
        try:
            # Convertir gray a BGR para el detector
            bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
            # Preparar tokens OCR si están disponibles
            ocr_tokens = []
            for (x0,y0,x1,y1,txt) in ocr_boxes:
                if txt.strip():  # Solo tokens con texto
                    ocr_tokens.append({
                        "text": txt.strip(),
                        "bbox": [x0, y0, x1-x0, y1-y0]  # Convertir a formato [x,y,w,h]
                    })
            
            # Ejecutar detector de texto superpuesto
            texto_superpuesto_info = detectar_texto_superpuesto(bgr, ocr_tokens=ocr_tokens if ocr_tokens else None)
            
            # Si detecta texto superpuesto, refuerza la decisión
            if texto_superpuesto_info.get("match", False):
                # Verificar si hay overlap con clusters ELA
                sospechosos = texto_superpuesto_info.get("sospechosos", [])
                for sospechoso in sospechosos:
                    sospechoso_bbox = sospechoso.get("bbox", [])
                    if len(sospechoso_bbox) == 4:
                        sx, sy, sw, sh = sospechoso_bbox
                        sospechoso_rect = (sx, sy, sx+sw, sy+sh)
                        
                        # Verificar overlap con clusters localizados
                        for c in localized:
                            cb = tuple(c["bbox"])
                            if _overlap(sospechoso_rect, cb):
                                # Refuerzo: si hay texto superpuesto en cluster ELA
                                marca_editada = True
                                overlap_text = True
                                if sospechoso.get("metricas", {}).get("is_numeric", False):
                                    overlap_digits = True
                                break
        except Exception as e:
            print(f"Error en detector de texto superpuesto: {e}")
            texto_superpuesto_info = None

    # decisión
    tiene_clusters = len(localized) > 0
    marca_editada = bool(tiene_clusters and overlap_text and peak_hits > 0)

    nivel = "SECUNDARIO"
    if marca_editada:
        # sube a PRIORITARIO si además hay dígitos o mucha intensidad ELA
        cond_intenso = any(c["perc_mean"] >= (perc_thr + 0.05) or c["ela_max_cluster"] >= (ela_max_thr + 20)
                           for c in localized)
        if overlap_digits or cond_intenso:
            nivel = "PRIORITARIO"
    elif tiene_clusters:
        nivel = "SECUNDARIO"  # hay señales ELA locales pero sin texto confirmado

    return {
        "ela": {
            "quality": quality,
            "thr_robusto": thr,
            "global": {"mean": ela_mean, "std": ela_std, "max": ela_max},
            "suspicious_global_ratio": float((sus_mask > 0).mean()),
            "grid": {"nx": nx, "ny": ny, "tile_px": [tile_w, tile_h]},
            "per_tile": {
                "porcentaje_sospechoso": perc.tolist(),
                "ela_max": tmax.tolist(),
                "mask_tiles": sus_tiles.astype(np.uint8).tolist()
            },
            "clusters": {
                "total": len(clusters),
                "localized": len(localized),
                "detalle": localized,
            },
            "texto": {
                "num_boxes": len(text_boxes),
                "num_ocr_boxes": len(ocr_boxes),
                "overlap_text": overlap_text,
                "overlap_digits": overlap_digits,
                "peak_hits": peak_hits
            },
            "criterios": {
                "perc_thr": perc_thr,
                "ela_max_thr": ela_max_thr,
                "regla_marca_editada": "clúster ELA local ∧ overlap texto ∧ pico ELA en el clúster"
            },
            "marca_editada": marca_editada,
            "nivel_sospecha": nivel,
            "texto_superpuesto": texto_superpuesto_info if texto_superpuesto_info else None
        }
    }
