import cv2
import numpy as np

def detectar_overlays_coloreados(img_bgr: np.ndarray, text_boxes: list = None) -> dict:
    """
    Detecta overlays coloreados (strokes/garabatos/figuras) mejorado para reducir
    falsos positivos de logos y colores de plantilla.
    
    Reglas encadenadas:
    - Color local (solo en ROIs de texto), no global
    - Croma adaptativo (percentil 90 * 0.85)
    - Forma de trazo (aspect ratio 2-20, stroke width CV < 0.5)
    - Contexto de texto (intersección ≥ 10% con texto)
    - Descartar logos (área > 1.5%, encabezados, degradados)
    """
    h, w = img_bgr.shape[:2]
    
    # Si no se proporcionan text_boxes, usar detección básica
    if text_boxes is None:
        # Detección básica de texto con MSER
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        mser = cv2.MSER_create(delta=5, min_area=60, max_area=int(0.25*h*w))
        regions, _ = mser.detectRegions(gray)
        text_boxes = []
        for r in regions:
            x, y, bw, bh = cv2.boundingRect(r)
            if bw * bh > 80 and 0.15 <= bw/bh <= 15.0:
                text_boxes.append((x, y, bw, bh))
    
    # --- ROI de texto (dilatar cajas) ---
    roi_mask = np.zeros((h, w), np.uint8)
    for x, y, bw, bh in text_boxes:
        # Expandir 12px alrededor de cada caja de texto
        x1 = max(0, x - 12)
        y1 = max(0, y - 12)
        x2 = min(w, x + bw + 12)
        y2 = min(h, y + bh + 12)
        cv2.rectangle(roi_mask, (x1, y1), (x2, y2), 255, -1)
    
    # Excluir encabezado grande (logos) - top 15% de la altura
    cv2.rectangle(roi_mask, (0, 0), (w, int(0.15 * h)), 0, -1)
    
    # --- Color adaptativo en la ROI ---
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    a, b = lab[..., 1].astype(np.float32) - 128, lab[..., 2].astype(np.float32) - 128
    C = np.sqrt(a*a + b*b)  # Croma en Lab
    S = hsv[..., 1].astype(np.float32)  # Saturación en HSV
    
    # Solo analizar en ROI de texto
    C_roi = C[roi_mask > 0]
    S_roi = S[roi_mask > 0]
    
    if len(C_roi) == 0:
        return {"match": False, "score": 0, "color_ratio": 0.0, "num_componentes_coloreados": 0, "componentes_disparados": []}
    
    # Umbrales adaptativos (percentil 90 * 0.85)
    C_thr = np.percentile(C_roi, 90) * 0.85
    S_thr = np.percentile(S_roi, 90) * 0.85
    
    # Máscara de color solo en ROI
    color_mask = ((C > C_thr) & (S > S_thr) & (roi_mask > 0)).astype(np.uint8) * 255
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
    
    # --- Componentes y filtros de "trazo" ---
    contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    edges = cv2.Canny(img_bgr, 60, 120)
    
    sospechosos = []
    total_area = h * w
    
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        
        # Descartar microscópicos y logos grandes
        if area < 40 or area > 0.015 * total_area:
            continue
            
        # Aspect ratio de trazo (2-20)
        aspect = max(bw, bh) / max(1.0, min(bw, bh))
        if aspect < 2 or aspect > 20:
            continue
            
        # Máscara del componente
        comp_mask = np.zeros((h, w), np.uint8)
        cv2.drawContours(comp_mask, [contour], -1, 255, -1)
        
        # Edge ratio (píxeles de borde / área)
        edge_ratio = (edges[comp_mask > 0] > 0).mean()
        if edge_ratio < 0.6:
            continue
            
        # Stroke width aproximado via distance transform
        comp_edges = cv2.Canny(comp_mask, 0, 1)
        dist = cv2.distanceTransform(255 - comp_edges, cv2.DIST_L2, 3)
        w_vals = 2 * dist[comp_mask > 0]
        
        if len(w_vals) < 15:
            continue
            
        w_cv = np.std(w_vals) / max(1e-6, np.mean(w_vals))
        if w_cv >= 0.5:  # Ancho no constante
            continue
            
        # Intersección con texto (≥ 10%)
        roi_inter = (roi_mask[y:y+bh, x:x+bw] > 0).mean()
        if roi_inter < 0.10:
            continue
            
        # Análisis de solidez (evitar degradados)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = area / (hull_area + 1e-6)
        if solidity < 0.6:
            continue
            
        # Análisis de variación de tono (evitar degradados)
        roi_hsv = hsv[y:y+bh, x:x+bw]
        roi_mask_comp = comp_mask[y:y+bh, x:x+bw]
        hue_vals = roi_hsv[roi_mask_comp > 0, 0]
        if len(hue_vals) > 10:
            hue_var = np.var(hue_vals)
            if hue_var > 8:  # Mucha variación de tono = degradado
                continue
        
        sospechosos.append({
            "bbox": [int(x), int(y), int(bw), int(bh)],
            "area": int(area),
            "aspect": float(aspect),
            "edge_ratio": float(edge_ratio),
            "w_cv": float(w_cv),
            "solidity": float(solidity),
            "roi_inter": float(roi_inter)
        })
    
    # Criterios de decisión
    num_sospechosos = len(sospechosos)
    color_ratio = (color_mask > 0).sum() / (h * w)
    
    # Score basado en componentes válidos
    score = 0
    if num_sospechosos >= 1:
        score += 25
    if num_sospechosos >= 2:
        score += 15
    if num_sospechosos >= 3:
        score += 10
    
    # Penalizar si hay mucho color global (posible logo)
    if color_ratio > 0.05:
        score = max(0, score - 20)
    
    match = score >= 25 and num_sospechosos >= 1
    
    return {
        "match": match,
        "score": min(score, 100),
        "color_ratio": float(color_ratio),
        "num_componentes_coloreados": num_sospechosos,
        "componentes_disparados": sospechosos[:10],
        "criterios": {
            "C_thr": float(C_thr),
            "S_thr": float(S_thr),
            "roi_texto_ok": len(C_roi) > 0,
            "color_ratio_ok": color_ratio <= 0.05
        }
    }