import io
from typing import Any, Dict, List, Tuple, Union

import cv2
import numpy as np
from PIL import Image


def _to_gray_u8(img_or_bytes: Union[bytes, np.ndarray]) -> np.ndarray:
    """Devuelve imagen en escala de grises uint8."""
    if isinstance(img_or_bytes, (bytes, bytearray)):
        arr = np.frombuffer(img_or_bytes, np.uint8)
        im = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if im is None:
            raise ValueError("Bytes no representan una imagen válida.")
    else:
        im = img_or_bytes
    if im.ndim == 2:
        gray = im
    else:
        if im.shape[2] == 4:
            im = cv2.cvtColor(im, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    return gray


def _blocks_dct(gray: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcula DCT 8x8 por bloques sobre Y (gray). Devuelve:
      - dc: coeficiente (0,0) por bloque  -> forma (N,)
      - ac: coeficientes AC bajos         -> forma (N, K)
    K = número de índices AC evaluados.
    """
    h, w = gray.shape
    h8, w8 = h - (h % 8), w - (w % 8)
    y = (gray[:h8, :w8].astype(np.float32) - 128.0)

    # índices AC de baja frecuencia (más informativos)
    ac_idx = [(0,1), (1,0), (1,2), (2,1), (2,2), (0,2), (2,0)]
    K = len(ac_idx)

    # extrae por bloques
    bs = 8
    blocks_y = y.reshape(h8//bs, bs, w8//bs, bs).swapaxes(1,2).reshape(-1, bs, bs)

    dc = np.empty((blocks_y.shape[0],), np.float32)
    ac = np.empty((blocks_y.shape[0], K), np.float32)

    for i, blk in enumerate(blocks_y):
        c = cv2.dct(blk)
        dc[i] = c[0, 0]
        for k, (r, cidx) in enumerate(ac_idx):
            ac[i, k] = c[r, cidx]

    return dc, ac


def _hist_fft_periodicity(vals: np.ndarray,
                          bin_width: float = 1.0,
                          max_abs: int = 60,
                          min_peak_prominence: float = 6.0) -> Tuple[bool, int, float]:
    """
    Prueba de periodicidad en histograma de coeficientes (doble cuantización).
    - Discretiza en bins enteros [-max_abs, max_abs]
    - FFT del histograma (sin DC) -> detecta picos periódicos
    Devuelve: (periodicidad, num_peaks, freq_ganadora)
    """
    # recorta valores extremos y cuantiza a entero
    v = np.clip(vals, -max_abs, max_abs)
    vq = np.rint(v / bin_width).astype(np.int32)

    # histograma simétrico
    rng = np.arange(-max_abs, max_abs + 1)
    hist, _ = np.histogram(vq, bins=rng.size, range=(-max_abs, max_abs))

    # suavizado ligero para reducir ruido
    k = np.array([1, 2, 3, 2, 1], dtype=np.float32)
    k = k / k.sum()
    hist_s = np.convolve(hist.astype(np.float32), k, mode="same")

    # espectro (quitamos DC)
    spec = np.abs(np.fft.rfft(hist_s))[1:]
    if spec.size == 0:
        return False, 0, 0.0

    # umbral relativo por robustez
    med = np.median(spec)
    mad = np.median(np.abs(spec - med)) + 1e-6
    thr = med + min_peak_prominence * (1.4826 * mad)

    # picos por encima de thr
    peaks = np.where(spec > thr)[0]
    num_peaks = int(peaks.size)
    main_freq = float((peaks[0] + 1) / len(hist_s)) if num_peaks > 0 else 0.0

    periodic = num_peaks >= 3  # varios armónicos
    return periodic, num_peaks, main_freq


def detectar_doble_compresion(
    img_or_bytes: Union[bytes, np.ndarray],
    jpeg_only: bool = False,
    ac_components_to_use: int = 5,   # usa las primeras K columnas de AC
) -> Dict[str, Any]:
    """
    Detector de DOBLE COMPRESIÓN (SECUNDARIO).
    Señales:
      - Periocidad clara en hist AC (≥3 picos espectrales en varias componentes)
      - Consistencia entre varias componentes AC
    OJO: apps de mensajería / capturas generan doble compresión sin edición.

    Retorna un dict con:
      - tiene_doble_compresion (bool)
      - periodicidad_detectada (bool)
      - num_peaks (int, máximo en componentes)
      - consistencia (ratio de componentes con periodicidad)
      - ac_variance, dc_variance
      - confianza ('ALTA'/'MEDIA'/'BAJA')
      - detalles por componente
      - info_jpeg (formato, tablas de cuantización si hay)
    """
    gray = _to_gray_u8(img_or_bytes)

    # (opcional) si solo queremos evaluar JPEG de origen real
    is_jpeg = False
    qtables = None
    try:
        if isinstance(img_or_bytes, (bytes, bytearray)):
            im = Image.open(io.BytesIO(img_or_bytes))
        else:
            # re-encode a memoria para que PIL pueda ver metadatos si es JPEG original
            ok, enc = cv2.imencode(".jpg", cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
            im = Image.open(io.BytesIO(enc.tobytes()))
        is_jpeg = (im.format or "").upper() == "JPEG"
        qtables = im.info.get("quantization")
    except Exception:
        pass
    if jpeg_only and not is_jpeg:
        return {
            "tiene_doble_compresion": False,
            "periodicidad_detectada": False,
            "confianza": "BAJA",
            "motivo": "No es JPEG de origen; prueba no aplica",
            "info_jpeg": {"is_jpeg": is_jpeg, "qtables": None},
        }

    # DCT por bloques
    dc, ac = _blocks_dct(gray)
    N, Ktot = ac.shape
    K = max(1, min(ac_components_to_use, Ktot))

    # varianzas (útiles como features de apoyo / logging)
    dc_var = float(np.var(dc))
    ac_var = float(np.var(ac[:, :K]))

    # test de periodicidad por componente
    comp_results: List[Dict[str, Any]] = []
    hits = 0
    max_peaks = 0
    for k in range(K):
        periodic, n_peaks, main_freq = _hist_fft_periodicity(ac[:, k])
        comp_results.append({
            "comp_index": k,
            "periodicidad": periodic,
            "num_peaks": n_peaks,
            "main_freq": main_freq
        })
        max_peaks = max(max_peaks, n_peaks)
        if periodic:
            hits += 1

    consistencia = hits / float(K)
    periodicidad_detectada = consistencia >= 0.5 and max_peaks >= 3

    # heurística de confianza:
    # ALTA: periodicidad clara en ≥60% de comps y ≥4 picos
    # MEDIA: periodicidad en 40–60% o ≥3 picos
    # BAJA: resto
    if periodicidad_detectada and consistencia >= 0.6 and max_peaks >= 4:
        confianza = "ALTA"
    elif periodicidad_detectada:
        confianza = "MEDIA"
    else:
        confianza = "BAJA"

    # señal binaria para tu pipeline
    tiene_doble = periodicidad_detectada

    return {
        "tiene_doble_compresion": bool(tiene_doble),
        "periodicidad_detectada": bool(periodicidad_detectada),
        "num_peaks": int(max_peaks),
        "consistencia_componentes": float(consistencia),
        "ac_variance": ac_var,
        "dc_variance": dc_var,
        "confianza": confianza,
        "detalles_componentes": comp_results,
        "info_jpeg": {
            "is_jpeg": is_jpeg,
            "qtables_disponibles": qtables is not None,
            "num_qtables": (len(qtables) if qtables else 0),
        },
        "nota": "Úsalo como apoyo; mensajería/capturas suelen mostrar doble compresión sin edición."
    }
