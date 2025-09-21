import cv2
import numpy as np
import pytesseract
from pytesseract import Output

def _ela_map(bgr, quality=85):
    # mapa ELA normalizado [0..1]
    enc = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])[1]
    rec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    diff = cv2.absdiff(bgr, rec)
    g = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    g = cv2.normalize(g, None, 0.0, 1.0, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
    return g

def _stroke_stats(bin_roi):
    # skeleton + distance transform -> media y cv de grosor
    if bin_roi.sum() == 0:
        return 0.0, 999.0
    roi = (bin_roi*255).astype(np.uint8)
    skel = np.zeros_like(roi)
    tmp = roi.copy()
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
    while True:
        open_ = cv2.morphologyEx(tmp, cv2.MORPH_OPEN, element)
        temp = cv2.subtract(tmp, open_)
        eroded = cv2.erode(tmp, element)
        skel = cv2.bitwise_or(skel, temp)
        tmp = eroded
        if cv2.countNonZero(tmp) == 0:
            break
    dist = cv2.distanceTransform(roi, cv2.DIST_L2, 3)
    widths = dist[skel > 0] * 2.0
    if widths.size == 0:
        return 0.0, 999.0
    w_mean = float(np.mean(widths))
    w_cv   = float(np.std(widths) / (w_mean + 1e-6))
    return w_mean, w_cv

def detectar_texto_inyectado(img_bgr):
    """
    Marca texto numérico 'inyectado' (p.ej. '1726' añadido en Paint) comparando
    trazo/ELA/entropía/halo del token vs su entorno.
    """
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # OCR con boxes
    data = pytesseract.image_to_data(gray, lang='spa+eng', config='--oem 3 --psm 6', output_type=Output.DICT)

    # ELA global (una vez)
    ela = _ela_map(img_bgr, quality=85)

    TH_W_CV   = 0.55       # trazo casi constante
    TH_ELA_R  = 1.5        # ELA_roi >= 1.5x ELA_around
    TH_ENTROP = 3.0        # entropía baja → sospechoso
    TH_GRAD   = 0.18       # densidad de bordes en banda delgada
    TH_MIN_W  = 20         # ancho mínimo ROI para análisis estable

    sospechosos = []
    score_total = 0

    for i in range(len(data["text"])):
        txt = (data["text"][i] or "").strip()
        conf = int(data["conf"][i]) if data["conf"][i] is not None else -1
        x, y, bw, bh = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        if bw < TH_MIN_W or bh < 10 or conf < 40:
            continue

        # Solo números (o casi todo números)
        if not txt:
            continue
        digits_ratio = sum(c.isdigit() for c in txt) / len(txt)
        if digits_ratio < 0.6:
            continue

        # ROI y "around"
        x0 = max(0, x-6); y0 = max(0, y-6)
        x1 = min(w, x+bw+6); y1 = min(h, y+bh+6)
        roi = gray[y:y+bh, x:x+bw]
        aro = gray[y0:y1, x0:x1]

        # binariza ROI para stroke/halo
        bin_roi = cv2.adaptiveThreshold(roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY_INV, 21, 10)
        bin_roi = (bin_roi > 0).astype(np.uint8)

        # Stroke width stats
        w_mean, w_cv = _stroke_stats(bin_roi)

        # ELA local
        ela_roi = float(np.mean(ela[y:y+bh, x:x+bw]))
        ela_out = float(np.mean(ela[y0:y1, x0:x1]))
        ela_ratio = (ela_roi + 1e-6) / (ela_out + 1e-6)

        # Entropía de grises del ROI (texto renderizado suele ser de baja entropía)
        hist = cv2.calcHist([roi],[0],None,[256],[0,256]).ravel()
        p = hist / (hist.sum() + 1e-6)
        ent = float(-np.sum(p*(np.log(p+1e-12))))

        # Halo / bordes nítidos
        grad = cv2.morphologyEx(bin_roi, cv2.MORPH_GRADIENT, np.ones((3,3),np.uint8))
        grad_ratio = float(grad.mean())  # ~ densidad de borde en banda delgada [0..1]

        # Scoring
        s = 0; reasons = []
        if w_cv <= TH_W_CV and w_mean >= 1.0:
            s += 10; reasons.append(f"trazo_cv={w_cv:.2f}")
        if ela_ratio >= TH_ELA_R and ela_roi >= 0.02:
            s += 8; reasons.append(f"ELA_ratio={ela_ratio:.2f}")
        if ent <= TH_ENTROP:
            s += 6; reasons.append(f"entropía={ent:.2f}")
        if grad_ratio >= TH_GRAD:
            s += 6; reasons.append(f"halo/grad={grad_ratio:.2f}")

        if s >= 14:  # umbral de disparo por token
            sospechosos.append({
                "texto": txt, "conf": conf, "bbox": [int(x),int(y),int(bw),int(bh)],
                "score": int(s), "reasons": reasons,
                "metrics": {"w_mean":w_mean, "w_cv":w_cv, "ela_ratio":ela_ratio,
                            "ela_roi":ela_roi, "entropia":ent, "grad_ratio":grad_ratio}
            })
            score_total += s

    match = len(sospechosos) > 0
    nivel = "PRIORITARIO" if score_total >= 25 else ("MEDIO" if score_total >= 14 else "BAJO")

    return {
        "match": match,
        "nivel": nivel,
        "score": int(min(score_total, 100)),
        "sospechosos": sospechosos[:10]
    }
