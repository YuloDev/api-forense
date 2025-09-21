import io
import math
from typing import Dict, Any, Tuple, List, Union

import cv2
import numpy as np


def _to_gray(img: Union[np.ndarray, bytes]) -> np.ndarray:
    """
    Acepta bytes o np.ndarray (BGR/RGB/GRAY) y devuelve GRAY uint8.
    """
    if isinstance(img, (bytes, bytearray)):
        arr = np.frombuffer(img, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Bytes no representan una imagen válida.")
    if img.ndim == 2:
        gray = img
    else:
        # Si viene RGB, OpenCV asume BGR: detectamos heurísticamente
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Normalizamos suavemente para estabilizar medidas
    gray = cv2.equalizeHist(gray)  # funciona bien en documentos/escaneos
    return gray


def _auto_canny(gray: np.ndarray, sigma: float = 0.33) -> np.ndarray:
    v = np.median(gray)
    lo = int(max(0, (1.0 - sigma) * v))
    hi = int(min(255, (1.0 + sigma) * v))
    edges = cv2.Canny(gray, lo, hi, L2gradient=True)
    return edges


def _robust_mad_z(x: np.ndarray, z_thr: float = 2.5) -> Tuple[np.ndarray, float, float]:
    """
    Z-score robusto con MAD. Devuelve z, mediana y MAD.
    z = 0.6745*(x-mediana)/MAD
    """
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    if mad < 1e-9:
        z = np.zeros_like(x, dtype=float)
    else:
        z = 0.6745 * (x - med) / mad
    return z, float(med), float(mad)


def _connected_components(mask: np.ndarray) -> List[np.ndarray]:
    """
    Componentes conexas 4-vecinas en una malla binaria (ny x nx).
    Devuelve lista de arrays (indices lineales) de cada componente.
    """
    ny, nx = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    comps = []
    for j in range(ny):
        for i in range(nx):
            if mask[j, i] and not visited[j, i]:
                stack = [(j, i)]
                visited[j, i] = True
                comp = []
                while stack:
                    y, x = stack.pop()
                    comp.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < ny and 0 <= xx < nx and mask[yy, xx] and not visited[yy, xx]:
                            visited[yy, xx] = True
                            stack.append((yy, xx))
                comps.append(np.array(comp))
    return comps


def _halo_ratio(gray: np.ndarray, edges: np.ndarray, max_dist: int = 3, grad_thr: float = 10.0,
                sample_cap: int = 50000) -> float:
    """
    Estima halo/aliasing alrededor de bordes.
    Para cada píxel de borde, toma la dirección del gradiente (Sobel) y
    muestrea ±d píxeles a lo largo de la normal. Si hay par (overshoot/undershoot)
    con |Δ|>grad_thr en ambos lados y signos opuestos → cuenta como halo.
    """
    # Gradiente
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy) + 1e-6

    ys, xs = np.where(edges > 0)
    n = len(ys)
    if n == 0:
        return 0.0
    if n > sample_cap:
        idx = np.random.choice(n, sample_cap, replace=False)
        ys, xs = ys[idx], xs[idx]
        n = sample_cap

    h, w = gray.shape
    halos = 0

    for y, x in zip(ys, xs):
        # Vector normal (dirección de mayor cambio)
        nx = gx[y, x] / mag[y, x]
        ny = gy[y, x] / mag[y, x]
        if not np.isfinite(nx) or not np.isfinite(ny):
            continue

        # Cuantizamos a 8 direcciones para acceso rápido
        dx = int(np.sign(nx))
        dy = int(np.sign(ny))

        # Si la normal es casi nula (poco fiable)
        if dx == 0 and dy == 0:
            continue

        # Tomamos el mejor de |dx|,|dy| según el valor absoluto del gradiente
        if abs(nx) >= abs(ny):
            dy = 0
        else:
            dx = 0

        # Muestra intensidades a ±d sobre la normal
        ok = False
        for d in range(1, max_dist + 1):
            x1 = np.clip(x + dx * d, 0, w - 1)
            y1 = np.clip(y + dy * d, 0, h - 1)
            x2 = np.clip(x - dx * d, 0, w - 1)
            y2 = np.clip(y - dy * d, 0, h - 1)
            diff1 = float(gray[y1, x1]) - float(gray[y, x])
            diff2 = float(gray[y2, x2]) - float(gray[y, x])
            # overshoot/undershoot (signos opuestos y magnitud suficiente)
            if abs(diff1) > grad_thr and abs(diff2) > grad_thr and (diff1 * diff2) < 0:
                ok = True
                break
        if ok:
            halos += 1

    return float(halos) / float(n)


def analizar_ruido_y_bordes(
    img: Union[np.ndarray, bytes],
    tile_min: int = 64,
    z_thr: float = 2.5,
    outlier_min_ratio: float = 0.05,
    min_cluster_tiles: int = 4,
) -> Dict[str, Any]:
    """
    Analítica PRIORITARIA de ruido y bordes para detectar edición local.
    Criterio de decisión por defecto:
      - outlier_ratio > 5%  y  existen clústeres localizados (no dispersos).
      - Se eleva a MEDIO/ALTO si halo_ratio >= 0.45 y/o hay muchas líneas paralelas dentro de los clústeres.

    Returns:
      dict con métricas y decisión final.
    """
    gray = _to_gray(img)
    h, w = gray.shape

    # --- Bordes globales / Laplaciano global
    edges = _auto_canny(gray)
    edge_density_global = float(edges.mean())  # ~proporción de píxeles de borde (0..1)
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    lap_var_global = float(lap.var())

    # --- Malla de parches
    tile = max(tile_min, min(h, w) // 16)  # malla fina pero estable
    nx = max(4, w // tile)
    ny = max(4, h // tile)
    tile_w = w // nx
    tile_h = h // ny

    lap_vars = np.zeros((ny, nx), dtype=float)
    edge_dens = np.zeros((ny, nx), dtype=float)

    for j in range(ny):
        for i in range(nx):
            y0, y1 = j * tile_h, (j + 1) * tile_h
            x0, x1 = i * tile_w, (i + 1) * tile_w
            roi_g = gray[y0:y1, x0:x1]
            roi_e = edges[y0:y1, x0:x1]
            if roi_g.size == 0:
                continue
            lv = cv2.Laplacian(roi_g, cv2.CV_64F, ksize=3).var()
            ed = roi_e.mean()
            lap_vars[j, i] = lv
            edge_dens[j, i] = ed

    # --- Outliers robustos (MAD)
    z_lap, med_lap, mad_lap = _robust_mad_z(lap_vars, z_thr=z_thr)
    z_edge, med_edge, mad_edge = _robust_mad_z(edge_dens, z_thr=z_thr)

    # Outlier si cualquiera de las dos está alta (positiva)
    outlier_mask = ((z_lap > z_thr) | (z_edge > z_thr))
    outlier_ratio = float(outlier_mask.mean())

    # --- Clústeres en malla
    comps = _connected_components(outlier_mask.astype(np.uint8))
    clusters = []
    for comp in comps:
        size = comp.shape[0]
        if size < min_cluster_tiles:
            continue
        ys = comp[:, 0]
        xs = comp[:, 1]
        # bounding box en píxeles
        x0 = int(xs.min() * tile_w)
        y0 = int(ys.min() * tile_h)
        x1 = int(min(w, (xs.max() + 1) * tile_w))
        y1 = int(min(h, (ys.max() + 1) * tile_h))
        # compacidad: área bbox / (n_tiles * área_tile)
        bbox_area = (x1 - x0) * (y1 - y0)
        tiles_area = size * tile_w * tile_h
        compactness = float(bbox_area) / float(tiles_area + 1e-6)
        clusters.append({
            "size_tiles": int(size),
            "bbox": [x0, y0, x1, y1],
            "compactness": compactness,
        })

    localized_clusters = [c for c in clusters if c["compactness"] < 6.0]  # compacto → localizado

    # --- Halo ratio
    halo_ratio = _halo_ratio(gray, edges, max_dist=3, grad_thr=10.0)

    # --- Líneas paralelas (Hough)
    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180, threshold=80,
        minLineLength=max(20, min(h, w) // 12),
        maxLineGap=10
    )
    num_lines = 0
    ang_groups = {}  # ángulo redondeado a 5° -> lista de líneas
    lines_in_clusters = 0

    if lines is not None:
        lines = lines[:, 0, :]  # (N,4)
        num_lines = int(lines.shape[0])

        def _in_any_cluster(xa, ya, xb, yb) -> bool:
            for c in localized_clusters:
                x0, y0, x1, y1 = c["bbox"]
                # test rápido: ambos extremos dentro del bbox
                if (x0 <= xa <= x1 and y0 <= ya <= y1) or (x0 <= xb <= x1 and y0 <= yb <= y1):
                    return True
            return False

        for (x1, y1, x2, y2) in lines:
            ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
            ang = abs(ang) % 180.0
            key = int(round(ang / 5.0) * 5)  # bucket cada 5°
            ang_groups.setdefault(key, 0)
            ang_groups[key] += 1
            if localized_clusters and _in_any_cluster(x1, y1, x2, y2):
                lines_in_clusters += 1

    # Paralelas dominantes (2 grupos con muchas líneas)
    parallel_groups = sum(1 for k, c in ang_groups.items() if c >= max(3, num_lines // 10))
    in_cluster_ratio = float(lines_in_clusters) / float(num_lines) if num_lines else 0.0

    # --- Decisión / nivel
    tiene_clusters = len(localized_clusters) > 0
    criterio_base = (outlier_ratio > outlier_min_ratio) and tiene_clusters

    nivel = "BAJO"
    if criterio_base:
        # escalado por intensidad de señales adicionales
        score = 0
        if halo_ratio >= 0.45:
            score += 2
        if in_cluster_ratio >= 0.35 and parallel_groups >= 1:
            score += 1
        if outlier_ratio > 0.12:
            score += 1
        nivel = "MEDIO" if score <= 2 else "ALTO"

    resultado = {
        "tiene_edicion_local": bool(criterio_base),
        "nivel_sospecha": nivel,
        "laplacian_variance_global": lap_var_global,
        "edge_density_global": edge_density_global,
        "grid": {"nx": nx, "ny": ny, "tile_px": [tile_w, tile_h]},
        "robust_stats": {
            "lap": {"median": med_lap, "mad": mad_lap},
            "edge": {"median": np.median(edge_dens), "mad": np.median(np.abs(edge_dens - np.median(edge_dens)))},
            "z_thr": z_thr,
        },
        "per_tile": {
            "lap_var": lap_vars.tolist(),
            "edge_density": edge_dens.tolist(),
            "outlier_mask": outlier_mask.astype(np.uint8).tolist(),
        },
        "outliers": {
            "ratio": outlier_ratio,
            "total_tiles": int(nx * ny),
            "tiles_outlier": int(outlier_mask.sum()),
            "umbral_ratio": outlier_min_ratio,
        },
        "clusters": {
            "num_clusters": len(clusters),
            "localized": len(localized_clusters),
            "boxes": [c["bbox"] for c in localized_clusters],
            "sizes": [c["size_tiles"] for c in localized_clusters],
            "compactness": [c["compactness"] for c in localized_clusters],
        },
        "halo_ratio": halo_ratio,
        "lines": {
            "total": num_lines,
            "parallel_groups": parallel_groups,
            "in_cluster_ratio": in_cluster_ratio,
            "angle_hist": ang_groups,
        },
    }
    return resultado
