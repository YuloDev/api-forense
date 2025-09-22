#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parser robusto para extraer datos de facturas PDF (nativas o escaneadas)
Incluye OCR, corrección de errores comunes y validación SRI
"""

import re
import io
import fitz
import numpy as np
import cv2
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    import pytesseract
    # Configurar ruta de Tesseract para Windows
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except Exception:
    pytesseract = None

try:
    from pyzbar.pyzbar import decode as zbar_decode
except Exception:
    zbar_decode = None

# --- utilidades ---
DIGIT_FIX = str.maketrans({
    'O':'0','o':'0','D':'0',
    'I':'1','l':'1','|':'1','!':'1',
    'Z':'2',
    'S':'5',
    'B':'8',
})

# intentos adicionales que suelen arreglar 1/4 y 7/4
_SWAP_CANDIDATES = [('4','1'),('1','4'),('7','4'),('4','7')]

def modulo11_ec(clave48):
    """DV ecuatoriano (módulo 11) para los primeros 48 dígitos de la clave."""
    pesos = [7,6,5,4,3,2]*8  # 48 pesos
    total = sum(int(d)*w for d,w in zip(clave48, pesos))
    dv = 11 - (total % 11)
    return {10:1, 11:0}.get(dv, dv)

def arreglar_ocr_digitos(s):
    """Normaliza confusiones comunes de OCR solo si debe ser numérico."""
    return s.translate(DIGIT_FIX)

def validar_clave_acceso(raw):
    cand = re.sub(r'\D','', raw)
    cand = cand[:49] if len(cand) >= 49 else cand
    if len(cand) == 49 and cand.isdigit():
        dv = modulo11_ec(cand[:48])
        return cand if int(cand[-1]) == dv else None
    return None

def intentar_corregir_clave(raw):
    base = arreglar_ocr_digitos(raw)
    if (ok := validar_clave_acceso(base)): 
        return ok
    # probar swaps puntuales de 1/4/7 en posiciones dudosas
    for a,b in _SWAP_CANDIDATES:
        cand = base.replace(a,b)
        if (ok := validar_clave_acceso(cand)): 
            return ok
    return None

def preprocess_for_ocr(img_bgr):
    """Preprocesamiento ligero para OCR"""
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    # ligera normalización y binarización adaptable
    g = cv2.bilateralFilter(g, 7, 40, 40)
    th = cv2.adaptiveThreshold(g,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 15)
    return th

def extraer_datos_factura_pdf(pdf_bytes: bytes, lang='spa+eng') -> Dict[str, Any]:
    """
    Extrae datos de factura PDF usando OCR robusto y validación SRI
    
    Args:
        pdf_bytes: Contenido del PDF como bytes
        lang: Idioma para OCR (default: 'spa+eng')
    
    Returns:
        Dict con los datos extraídos de la factura
    """
    if pytesseract is None:
        raise RuntimeError("Instala pytesseract y el binario de Tesseract para hacer OCR.")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texto_total = ""
    claves_barcodes = []
    
    for page in doc:
        # render a 200 dpi aprox
        pix = page.get_pixmap(dpi=200, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img_proc = preprocess_for_ocr(img)

        # OCR texto corrido
        conf = "--oem 3 --psm 6"
        texto = pytesseract.image_to_string(img_proc, lang=lang, config=conf)
        texto_total += "\n" + texto

        # (opcional) leer códigos de barras de la imagen original
        if zbar_decode:
            try:
                for bc in zbar_decode(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)):
                    s = bc.data.decode('utf-8', 'ignore')
                    if (ok := validar_clave_acceso(s)) or (ok := intentar_corregir_clave(s)):
                        claves_barcodes.append(ok)
            except Exception:
                pass  # Ignorar errores de barcode

    t = texto_total

    # patrones de extracción
    r_ruc   = re.search(r'(?:R\.?U\.?C\.?:?|RUC[:\s]*)\s*([0-9]{13})', t, re.I)
    r_razon = re.search(r'(Raz[oó]n Social.*?:\s*)([^\n\r]+)', t, re.I)
    r_fecha = re.search(r'(?:Fecha(?: de Emisi[oó]n)?[:\s]*)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', t, re.I)
    r_num   = re.search(r'(?:No\.?|N[uú]mero(?: de factura)?)[:\s]*([0-9]{3}[-–][0-9]{3}[-–][0-9]{6,9})', t, re.I)
    r_clave = re.search(r'(?:Clave.*Acceso|N[uú]mero de autorizaci[oó]n)[:\s]*([0-9\s]{45,60})', t, re.I)

    # limpieza y validación
    ruc = r_ruc.group(1) if r_ruc else None
    razon = r_razon.group(2).strip() if r_razon else None
    fecha = r_fecha.group(1).replace(' ', '') if r_fecha else None
    numero = r_num.group(1) if r_num else None

    clave = None
    candidates = []
    if r_clave:
        candidates.append(r_clave.group(1))
    # también barre secuencias de 49 dígitos por si el label no se detecta
    candidates += re.findall(r'\d[\d\s]{47,70}\d', t)

    for c in candidates:
        cfix = intentar_corregir_clave(c)
        if cfix:
            clave = cfix
            break
    
    # Priorizar códigos de barras si están disponibles
    if not clave and claves_barcodes:
        clave = claves_barcodes[0]

    # totales: toma el mayor número tipo xx,xx / xx.xx cercano a "VALOR TOTAL" / "TOTAL"
    total = None
    m_total = re.search(r'(VALOR\s+TOTAL|TOTAL)\D{0,30}([0-9]+[.,][0-9]{2})', t, re.I)
    if m_total:
        total_str = m_total.group(2)
        if re.search(r'\d{1,3}\.\d{3}[.,]\d{2}', total_str):
            # Formato con separador de miles
            total = float(total_str.replace('.', '').replace(',', '.'))
        else:
            total = float(total_str.replace(',', '.'))

    # Extraer subtotales e IVA
    subtotal_0 = None
    subtotal_15 = None
    iva_15 = None
    
    # Buscar subtotal 0%
    m_subtotal_0 = re.search(r'SUBTOTAL\s+0%[:\s]*([0-9]+[.,][0-9]{2})', t, re.I)
    if m_subtotal_0:
        subtotal_0 = float(m_subtotal_0.group(1).replace(',', '.'))
    
    # Buscar subtotal 15%
    m_subtotal_15 = re.search(r'SUBTOTAL\s+15%[:\s]*([0-9]+[.,][0-9]{2})', t, re.I)
    if m_subtotal_15:
        subtotal_15 = float(m_subtotal_15.group(1).replace(',', '.'))
    
    # Buscar IVA 15%
    m_iva_15 = re.search(r'IVA\s+15%[:\s]*([0-9]+[.,][0-9]{2})', t, re.I)
    if m_iva_15:
        iva_15 = float(m_iva_15.group(1).replace(',', '.'))

    return {
        "texto_ocr": t.strip(),
        "ruc": ruc,
        "razonSocial": razon,
        "fechaEmision": fecha,
        "numeroFactura": numero,
        "claveAcceso": clave,
        "total": total,
        "subtotal_0": subtotal_0,
        "subtotal_15": subtotal_15,
        "iva_15": iva_15,
        "fuentes": {
            "barcode": bool(claves_barcodes),
            "ocr": True,
            "claves_barcode": claves_barcodes
        }
    }
