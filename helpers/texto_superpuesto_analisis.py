import cv2
import numpy as np
import re

# --- utilidades ---
def _ela_heatmap(img_bgr, q=95):
    ok, jpg = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, q])
    ela = cv2.absdiff(img_bgr, cv2.imdecode(jpg, 1)).mean(axis=2).astype(np.float32)
    return ela

def _stroke_width_cv(bin_roi):
    # distancia medial ~ Stroke Width Transform (aprox)
    if bin_roi.sum() == 0:
        return 999.0, 0
    dist = cv2.distanceTransform(bin_roi, cv2.DIST_L2, 3)
    wvals = 2.0*dist[bin_roi > 0]
    if len(wvals) < 20:
        return 999.0, len(wvals)
    cv = float(np.std(wvals)/max(1e-6, np.mean(wvals)))
    return cv, len(wvals)

def _halo_ratio(grad, mask_fg):
    dil = cv2.dilate(mask_fg, np.ones((3,3),np.uint8), 1)
    ring = (dil & (~mask_fg.astype(bool))).astype(np.uint8)
    g_in  = grad[mask_fg>0]; g_ring = grad[ring>0]
    if g_in.size < 10 or g_ring.size < 10:
        return 0.0
    return float(np.mean(g_ring)/max(1e-6, np.mean(g_in)))

def _two_color_entropy(patch_bgr):
    # Entropía de luminancia y nº de colores dominantes (bajo -> texto render)
    gray = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray],[0],None,[256],[0,256]).ravel()
    p = hist / max(1, hist.sum())
    ent = float(-np.sum(p[p>0]*np.log2(p[p>0])))
    # cuenta de bins con p>1%
    dom = int((p > 0.01).sum())
    return ent, dom

def _edge_coherence(gradx, grady):
    ang = (np.rad2deg(np.arctan2(grady, gradx)) % 180).ravel()
    ang = ang[(~np.isnan(ang))]
    if ang.size == 0: return 0.0
    hist, _ = np.histogram(ang, bins=[0,15,30,45,60,75,90,105,120,135,150,165,180])
    return float(hist.max()/max(1, hist.sum()))  # 1 → muy coherente (textos)

def _boxes_union_mser(img_gray):
    mser = cv2.MSER_create(delta=5, min_area=30, max_area=10000)
    regions, _ = mser.detectRegions(img_gray)
    boxes = []
    for r in regions:
        x,y,w,h = cv2.boundingRect(r.reshape(-1,1,2))
        if w*h < 40: 
            continue
        ar = max(w,h)/max(1.0, min(w,h))
        if ar < 1.2 or ar > 40: 
            continue
        boxes.append([x,y,w,h])
    return boxes

def _iou(a,b):
    ax,ay,aw,ah = a; bx,by,bw,bh = b
    x1,y1 = max(ax,bx), max(ay,by)
    x2,y2 = min(ax+aw, bx+bw), min(ay+ah, by+bh)
    inter = max(0,x2-x1)*max(0,y2-y1)
    return inter/float(aw*ah + bw*bh - inter + 1e-6)

# ------------------ DETECTOR PRINCIPAL ------------------ #
def detectar_texto_superpuesto(img_bgr, ocr_tokens=None):
    """
    Devuelve sospechas de texto/garabatos agregados (negro, gris o color).
    Cada sospecha trae métricas y un score.
    ocr_tokens: lista opcional de dicts {"text": str, "bbox":[x,y,w,h]}
    """
    H,W = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    ela  = _ela_heatmap(img_bgr, 95)

    # gradiente para halo y coherencia
    gx = cv2.Sobel(gray, cv2.CV_32F, 1,0,ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0,1,ksize=3)
    grad = cv2.magnitude(gx, gy)

    # 1) propuestas: OCR si existe, si no MSER
    boxes = []
    if ocr_tokens:
        for t in ocr_tokens:
            x,y,w,h = t["bbox"]
            if w*h > 40: boxes.append([x,y,w,h])
    else:
        boxes = _boxes_union_mser(gray)

    # filtra cabecera (logos): top 15%
    boxes = [b for b in boxes if b[1] > int(0.15*H)]

    # 2) evalúa cada caja
    sospechosos = []
    TH_SW_CV   = 0.55
    TH_HALO    = 0.45
    TH_ELA_BOOST = 1.8
    TH_NOISE_Z = -1.5
    TH_EDGE_COH = 0.22  # textos: > 0.22 aprox
    TH_OVERLAY_COLOR = 0.85  # umbral relativo de croma/saturación

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab).astype(np.float32)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    a = lab[...,1]-128; b = lab[...,2]-128
    C = np.sqrt(a*a + b*b); S = hsv[...,1]

    for (x,y,w,h) in boxes:
        x0,y0 = max(0,x-6), max(0,y-6); x1,y1 = min(W,x+w+6), min(H,y+h+6)
        roi_g = gray[y:y+h, x:x+w]
        if roi_g.size == 0: continue

        # binarizado adaptativo para SWT y bordes
        bin_roi = cv2.adaptiveThreshold(roi_g,255,cv2.ADAPTIVE_THRESH_MEAN_C,
                                        cv2.THRESH_BINARY_INV, 15, 6)
        sw_cv, nsw = _stroke_width_cv(bin_roi)

        # halo
        halo = _halo_ratio(grad[y0:y1, x0:x1], bin_roi)

        # ELA local
        ela_token   = ela[y:y+h, x:x+w].mean()
        ela_border  = ela[y0:y1, x0:x1].copy()
        ela_ring    = ela_border.copy()
        ela_ring[6:-6,6:-6] = 0
        ela_ring_m  = float(ela_ring.sum()/max(1,(ela_ring>0).sum()))
        ela_boost   = ela_token/max(1e-6, ela_ring_m)

        # ruido HF (laplace var) Z-score respecto al entorno
        hp_in  = float(cv2.Laplacian(roi_g, cv2.CV_32F).var())
        hp_env = float(cv2.Laplacian(gray[y0:y1, x0:x1], cv2.CV_32F).var())
        z_hf   = (hp_in - hp_env)/max(1e-6, np.sqrt(hp_env))

        # coherencia de bordes (ángulos repetidos)
        coh = _edge_coherence(gx[y:y+h,x:x+w], gy[y:y+h,x:x+w])

        # color (solo para garabatos/strokes)
        Croi = C[y:y+h, x:x+w]; Sroi = S[y:y+h, x:x+w]
        Cthr = np.percentile(Croi, 90)*TH_OVERLAY_COLOR
        Sthr = np.percentile(Sroi, 90)*TH_OVERLAY_COLOR
        colorish = bool((Croi>Cthr).mean()>0.15 and (Sroi>Sthr).mean()>0.15)

        # anti-aliased? (pocos tonos y baja entropía)
        ent, dom = _two_color_entropy(img_bgr[y:y+h, x:x+w])
        aa_low = (ent <= 4.0 and dom <= 25)

        # heurísticas finales
        is_numeric = False
        if ocr_tokens:
            # encuentra token OCR coincidente por IoU
            for t in ocr_tokens:
                if _iou([x,y,w,h], t["bbox"]) > 0.4:
                    is_numeric = bool(re.fullmatch(r"[0-9.,/:-]+", t["text"] or ""))
                    break

        flags = {
            "sw_cv_ok": sw_cv <= TH_SW_CV,
            "halo_ok":  halo >= TH_HALO,
            "ela_ok":   ela_boost >= TH_ELA_BOOST,
            "noise_ok": z_hf <= TH_NOISE_Z,
            "coh_ok":   coh >= TH_EDGE_COH,
            "aa_low":   aa_low,
            "colorish": colorish,
            "is_numeric": is_numeric
        }

        # reglas de decisión:
        # (A) texto negro/gris render: sw + (halo o ela) + noise + coherencia
        cond_neutro = flags["sw_cv_ok"] and (flags["halo_ok"] or flags["ela_ok"]) \
                      and flags["noise_ok"] and flags["coh_ok"]

        # (B) garabato/overlay color: colorish + trazo (sw) + borde
        cond_color  = flags["colorish"] and flags["sw_cv_ok"] and flags["coh_ok"]

        # refuerzo si es numérico (montos/fechas)
        bonus = 1 if flags["is_numeric"] else 0

        score = (3*flags["sw_cv_ok"] + 2*flags["halo_ok"] + 2*flags["ela_ok"] +
                 2*flags["noise_ok"] + 1*flags["coh_ok"] + 1*flags["aa_low"] +
                 2*flags["colorish"] + bonus)

        if cond_neutro or cond_color:
            sospechosos.append({
                "bbox":[x,y,w,h], "score": int(score),
                "tipo": "texto_neutro" if cond_neutro and not cond_color else
                        ("overlay_color" if cond_color and not cond_neutro else "mixto"),
                "metricas":{
                    "sw_cv": float(sw_cv), "halo": float(halo), "ela_boost": float(ela_boost),
                    "z_hf": float(z_hf), "edge_coherence": float(coh),
                    "entropy": float(ent), "dominant_bins": int(dom),
                    "colorish": bool(colorish), "is_numeric": bool(is_numeric)
                },
                "umbrales":{
                    "TH_SW_CV": TH_SW_CV, "TH_HALO": TH_HALO,
                    "TH_ELA_BOOST": TH_ELA_BOOST, "TH_NOISE_Z": TH_NOISE_Z,
                    "TH_EDGE_COH": TH_EDGE_COH
                }
            })

    # clusterización (evita falsos positivos aislados)
    # si hay >=2 sospechosos a <60px entre sí → "localizado"
    localized = False
    for i in range(len(sospechosos)):
        xi,yi,wi,hi = sospechosos[i]["bbox"]
        ci = np.array([xi+wi/2, yi+hi/2])
        vecinos = 0
        for j in range(len(sospechosos)):
            if i==j: continue
            xj,yj,wj,hj = sospechosos[j]["bbox"]
            cj = np.array([xj+wj/2, yj+hj/2])
            if np.linalg.norm(ci-cj) < 60:
                vecinos += 1
        if vecinos >= 1:
            localized = True; break

    return {
        "match": len(sospechosos) > 0,
        "localized": localized,
        "num_sospechosos": len(sospechosos),
        "sospechosos": sorted(sospechosos, key=lambda d: -d["score"])
    }
