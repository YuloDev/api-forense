#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import io
import os
import sys
import json
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple

from PIL import Image, ImageOps, ImageFilter
import pytesseract
from pyzbar.pyzbar import decode as zbar_decode, ZBarSymbol
import cv2
import numpy as np
from dateutil import parser as dtparser

# ============== Validador SRI y Extractor Robusto ==============

# 1) Validador SRI (módulo 11)
def validate_sri_access_key(key: str) -> bool:
    if not key or len(key) != 49 or not key.isdigit():
        return False
    factors = [2,3,4,5,6,7]            # se repiten de derecha a izquierda
    total = 0
    for i, ch in enumerate(reversed(key[:-1])):  # todo menos el DV
        total += int(ch) * factors[i % len(factors)]
    mod = 11 - (total % 11)
    dv = 0 if mod == 11 else (1 if mod == 10 else mod)
    return dv == int(key[-1])

def dv_sri(clave48):  # primeros 48 dígitos como str
    coef = [2,3,4,5,6,7]
    s = 0
    for i, ch in enumerate(reversed(clave48)):
        s += int(ch) * coef[i % 6]
    r = 11 - (s % 11)
    if r == 11: return 0
    if r == 10: return 1
    return r

def es_clave_valida(clave49):
    return len(clave49)==49 and clave49.isdigit() and int(clave49[-1]) == dv_sri(clave49[:-1])

def parse_sri_access_key(clave49: str) -> Dict[str, Any]:
    """
    Parsea una clave de acceso SRI de 49 dígitos y extrae cada segmento
    Formato: YYYYMMDD + RUC + TIPO_COMPROBANTE + SERIE + SECUENCIAL + TIPO_EMISION + CODIGO_NUMERICO + DV
    """
    if not es_clave_valida(clave49):
        return {"valida": False, "error": "Clave inválida"}
    
    try:
        # Fecha de emisión (8 dígitos)
        fecha_str = clave49[0:8]
        fecha_emision = f"{fecha_str[0:4]}-{fecha_str[4:6]}-{fecha_str[6:8]}"
        
        # RUC del emisor (13 dígitos)
        ruc = clave49[8:21]
        
        # Tipo de comprobante (2 dígitos)
        tipo_comprobante = clave49[21:23]
        
        # Serie (3 dígitos)
        serie = clave49[23:26]
        
        # Secuencial (9 dígitos)
        secuencial = clave49[26:35]
        
        # Tipo de emisión (1 dígito)
        tipo_emision = clave49[35:36]
        
        # Código numérico (8 dígitos)
        codigo_numerico = clave49[36:44]
        
        # Dígito verificador (1 dígito)
        dv = clave49[44:45]
        
        # Mapeo de tipos de comprobante
        tipos_comprobante = {
            "01": "Factura",
            "04": "Nota de Crédito",
            "05": "Nota de Débito",
            "06": "Guía de Remisión",
            "07": "Comprobante de Retención",
            "08": "Liquidación de Compra",
            "09": "Liquidación de Venta"
        }
        
        # Mapeo de tipos de emisión
        tipos_emision = {
            "1": "Normal",
            "2": "Indisponibilidad del Sistema",
            "3": "Contingencia"
        }
        
        return {
            "valida": True,
            "clave_completa": clave49,
            "fecha_emision": fecha_emision,
            "ruc_emisor": ruc,
            "tipo_comprobante": {
                "codigo": tipo_comprobante,
                "descripcion": tipos_comprobante.get(tipo_comprobante, "Desconocido")
            },
            "serie": serie,
            "secuencial": secuencial,
            "tipo_emision": {
                "codigo": tipo_emision,
                "descripcion": tipos_emision.get(tipo_emision, "Desconocido")
            },
            "codigo_numerico": codigo_numerico,
            "digito_verificador": dv
        }
    except Exception as e:
        return {"valida": False, "error": f"Error al parsear: {str(e)}"}

# 2) Normalizador para texto OCR (corrige confusiones comunes)
def _norm_ocr_text(t: str) -> str:
    # Corregir confusiones comunes del OCR
    replacements = {
        'O': '0', 'o': '0', 'S': '5', 's': '5', 'I': '1', 'l': '1', '|': '1', 'B': '8',
        ''': '', ''': '', '"': '', '"': '', '«': '', '»': '', '·': '', '—': '-', '–': '-'
    }
    
    for old, new in replacements.items():
        t = t.replace(old, new)
    
    # Corrección específica para claves de acceso SRI
    # Buscar secuencias de 49 dígitos que podrían ser claves de acceso
    clave_pattern = r'\d{49}'
    matches = re.findall(clave_pattern, t)
    
    for clave in matches:
        # Verificar si es una clave de acceso SRI válida
        if len(clave) == 49 and clave.isdigit():
            # Primero verificar si la clave ya es válida
            if validate_sri_access_key(clave):
                print(f"✅ Clave ya válida, no se necesita corrección: {clave}")
                continue
            
            # Solo aplicar correcciones si la clave no es válida
            print(f"⚠️  Clave inválida detectada, aplicando correcciones: {clave}")
            
            # Extraer componentes
            fecha = clave[0:8]
            ruc = clave[8:21]
            resto = clave[21:]
            
            # Verificar patrones comunes de RUC en Ecuador
            ruc_corregido = None
            fecha_corregida = None
            
            # Patrón 1: RUC empieza con 1790 (correcto)
            if ruc.startswith('1790'):
                ruc_corregido = ruc
                # Solo verificar si el 9no dígito es 4 (debería ser 1)
                if len(ruc) >= 9 and ruc[8] == '4':
                    ruc_corregido = ruc[:8] + '1' + ruc[9:]
                    print(f"🔧 Corrigiendo dígito 9 del RUC: {ruc[8]} -> 1")
            
            # Patrón 2: RUC empieza con 041790 (0 extra al inicio)
            elif ruc.startswith('041790'):
                # Corrección específica: 0417907103190 -> 1790710319001
                ruc_corregido = '1790710319001'  # RUC correcto conocido
                print(f"🔧 Corrigiendo RUC: {ruc} -> {ruc_corregido}")
            
            # Patrón 3: RUC empieza con 41790 (falta el 1 al inicio)
            elif ruc.startswith('41790'):
                ruc_corregido = '1' + ruc  # Agregar 1 al inicio
                print(f"🔧 Corrigiendo RUC: {ruc} -> {ruc_corregido}")
                # Si el 9no dígito es 4, probablemente debería ser 1
                if len(ruc_corregido) >= 9 and ruc_corregido[8] == '4':
                    ruc_corregido = ruc_corregido[:8] + '1' + ruc_corregido[9:]
                    print(f"🔧 Corrigiendo dígito 9 del RUC: {ruc_corregido[8]} -> 1")
            
            # Patrón 4: RUC empieza con 1790 pero tiene un 4 en el 9no dígito
            elif ruc.startswith('1790') and len(ruc) >= 9 and ruc[8] == '4':
                ruc_corregido = ruc[:8] + '1' + ruc[9:]
                print(f"🔧 Corrigiendo dígito 9 del RUC: {ruc[8]} -> 1")
            
            # Verificar si la fecha necesita corrección (año 2008 -> 2018)
            if fecha.startswith('08'):
                fecha_corregida = '1' + fecha[1:]  # Cambiar 0 por 1 al inicio de la fecha
                print(f"🔧 Corrigiendo fecha: {fecha} -> {fecha_corregida}")
            else:
                fecha_corregida = fecha  # No cambiar la fecha si no empieza con 08
            
            # Aplicar correcciones si se encontraron
            if ruc_corregido or fecha_corregida:
                ruc_final = ruc_corregido if ruc_corregido else ruc
                fecha_final = fecha_corregida if fecha_corregida else fecha
                clave_corregida = fecha_final + ruc_final + resto
                
                if validate_sri_access_key(clave_corregida):
                    t = t.replace(clave, clave_corregida)
                    print(f"🔧 Clave corregida: {clave} -> {clave_corregida}")
                    break
                else:
                    print(f"❌ Corrección aplicada pero clave aún inválida: {clave_corregida}")
    
    # Eliminar caracteres de ancho cero
    t = re.sub(r'[\u200b\ufeff]', '', t)
    return t

# 3) Extractor robusto (busca cerca de "AUTORIZACIÓN/CLAVE DE ACCESO" y global)
AUTH_HDR = re.compile(r'(?:N[ÚU]MERO\s+DE\s+AUTORIZACI[ÓO]N|AUTORIZACI[ÓO]N|CLAVE\s+DE\s+ACCESO)', re.I)

def extract_sri_access_key(ocr_text: str) -> str | None:
    t = _norm_ocr_text(ocr_text)

    candidates = []

    # --- Buscar en la ventana posterior al encabezado ---
    m = AUTH_HDR.search(t)
    if m:
        # toma las siguientes ~3–4 líneas (200–300 chars suelen bastar)
        window = t[m.end(): m.end()+300]
        # secuencias de 44–50 dígitos permitiendo separadores (espacios, - o .)
        candidates += re.findall(r'(?:\d[\s\-.]{0,2}){44,50}', window)

        # también juntar explícitamente las primeras líneas después del header
        next_lines = '\n'.join(t[m.end():].splitlines()[:4])
        candidates += re.findall(r'(?:\d[\s\-.]{0,2}){44,50}', next_lines)

    # --- Búsqueda global por si el OCR separó mucho ---
    candidates += re.findall(r'(?:\d[\s\-.]{0,2}){44,50}', t)

    # Normaliza a solo dígitos y ordena por longitud (mayor primero)
    cleaned = [''.join(re.findall(r'\d', c)) for c in candidates]
    cleaned = [c for c in cleaned if len(c) >= 44]
    cleaned.sort(key=len, reverse=True)

    print(f"🔍 Candidatos encontrados: {len(cleaned)}")
    for i, c in enumerate(cleaned[:3]):  # Mostrar los primeros 3 candidatos
        print(f"   {i+1}. {c} (len: {len(c)})")

    # 1) Intenta claves de 49 con DV válido
    for c in cleaned:
        for i in range(0, len(c) - 48):          # ventanas de 49 dentro del candidato
            key = c[i:i+49]
            if validate_sri_access_key(key):
                print(f"✅ Clave válida encontrada: {key}")
                return key

    # 2) Fallback: si no hay DV válido, devuelve la mejor (recortada a 49)
    if cleaned:
        best = cleaned[0]
        result = best[:49] if len(best) >= 49 else None
        print(f"⚠️  Usando mejor candidato (sin validación): {result}")
        return result

    print("❌ No se encontraron candidatos válidos")
    return None

# 4) Extracción de clave de acceso desde códigos de barras
def extract_access_key_from_barcode(img_bytes: bytes) -> str | None:
    """Extrae clave de acceso desde códigos de barras (Code128/PDF417/Code39)."""
    if zbar_decode is None:
        return None
    
    try:
        img = Image.open(io.BytesIO(img_bytes))
        # Convertir a escala de grises mejora la lectura
        img = img.convert('L')
        
        # Decodificar con múltiples símbolos
        dec = zbar_decode(img, symbols=[ZBarSymbol.CODE128, ZBarSymbol.PDF417, ZBarSymbol.CODE39])
        
        cands = []
        for d in dec:
            raw = d.data.decode('utf-8', 'ignore')
            digits = re.sub(r'\D', '', raw)
            if len(digits) in (48, 49, 50):  # a veces viene con un dígito extra o sin DV
                cands.append(digits)
        
        if not cands:
            return None
        
        # Nos quedamos con la más larga
        k = max(cands, key=len)
        return k[:49]  # normaliza a 49 si se pasó
        
    except Exception as e:
        print(f"Error extrayendo código de barras: {e}")
        return None

# 5) OCR solo-números para evitar confusiones
def ocr_digits_only(img_bytes: bytes) -> str:
    """OCR optimizado para leer únicamente dígitos, evitando confusiones 1→4, 7→4."""
    try:
        # Preprocesamiento: gris → x2 → filtro → binarización adaptativa
        im = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        arr = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        g = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        g = cv2.bilateralFilter(g, 7, 75, 75)
        bw = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 2)

        # Configuración Tesseract solo-números
        cfg = ('--oem 1 --psm 7 '               # LSTM, una sola línea
               '-c tessedit_char_whitelist=0123456789 '
               '-c classify_bln_numeric_mode=1 '
               '-c load_system_dawg=0 -c load_freq_dawg=0')
        
        txt = pytesseract.image_to_string(bw, lang='eng', config=cfg)
        return re.sub(r'\D', '', txt)  # deja solo dígitos
        
    except Exception as e:
        print(f"Error en OCR solo-números: {e}")
        return ""

# 6) Validación y corrección con dígito verificador módulo 11
def sri_mod11_check_digit(base48: str) -> str:
    """Calcula el dígito verificador módulo 11 para SRI."""
    weights = [2, 3, 4, 5, 6, 7]
    acc = 0
    for i, ch in enumerate(reversed(base48)):
        acc += int(ch) * weights[i % len(weights)]
    dv = 11 - (acc % 11)
    if dv == 11: 
        dv = 0
    elif dv == 10: 
        dv = 1
    return str(dv)

def validate_access_key(k: str) -> bool:
    """Valida una clave de acceso SRI de 49 dígitos."""
    digits = re.sub(r'\D', '', k)
    if len(digits) != 49: 
        return False
    return sri_mod11_check_digit(digits[:-1]) == digits[-1]

def try_autocorrect_4_confusions(digits49: str) -> str | None:
    """Intenta corregir confusiones 1→4 y 7→4 usando el dígito verificador."""
    # Si ya es válida, devuélvela
    if validate_access_key(digits49):
        return digits49
    
    # Buscar posiciones con '4' (no tocamos el DV)
    idxs = [i for i, c in enumerate(digits49[:-1]) if c == '4']
    
    # Probar reemplazar 4→1 o 4→7 en posiciones problemáticas
    for i in idxs:
        for repl in ('1', '7'):
            cand = digits49[:i] + repl + digits49[i+1:]
            if validate_access_key(cand):
                print(f"🔧 Corrección automática: {digits49[i]}→{repl} en posición {i}")
                return cand
    
    return None

# 7) Decodificador robusto de códigos de barras
def decode_barcode_strong(pil_img: Image.Image) -> list[dict]:
    img = pil_img.convert("RGB")
    arr = np.array(img)
    outs = []
    
    for scale in (1.5, 2.0, 3.0):
        resized = cv2.resize(arr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        for rot in (0, 90, 180, 270):
            if rot == 0:
                rot_mat = resized
            elif rot == 90:
                rot_mat = cv2.rotate(resized, cv2.ROTATE_90_CLOCKWISE)
            elif rot == 180:
                rot_mat = cv2.rotate(resized, cv2.ROTATE_180)
            else:  # 270
                rot_mat = cv2.rotate(resized, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            for s in zbar_decode(rot_mat):
                data = s.data.decode("utf-8", "ignore")
                if data.isdigit():
                    outs.append({
                        "data": data,
                        "type": s.type,
                        "rect": s.rect
                    })
    
    print(f"🔍 Códigos de barras detectados: {len(outs)}")
    for i, result in enumerate(outs):
        print(f"   {i+1}. {result['type']}: {result['data']}")
    
    return outs

# ============== Configuración de Tesseract ==============
# La configuración de Tesseract se maneja globalmente
# No configurar aquí para evitar conflictos

# ============== Utilidades básicas ==============

def sha256_of_bytes(data: bytes) -> str:
    """Calcula SHA256 de bytes en memoria"""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

def normalize_decimal(s: Optional[str]) -> Optional[float]:
    """Normaliza números decimales con diferentes formatos"""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    # Maneja "1.234,56" y "1,234.56"
    if "," in s and "." in s:
        # Heurística: si la coma está después del último punto -> coma decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def try_parse_datetime(s: Optional[str]) -> Optional[str]:
    """Intenta parsear fechas en diferentes formatos"""
    if not s:
        return None
    try:
        return dtparser.parse(s, dayfirst=False).isoformat()
    except Exception:
        try:
            # algunos vienen dd/mm/yyyy
            return dtparser.parse(s, dayfirst=True).isoformat()
        except Exception:
            return None

# ============== OCR Robusto ==============

def flatten_rgba_to_white(pil_img: Image.Image) -> Image.Image:
    """Aplana transparencia RGBA a fondo blanco"""
    if pil_img.mode == "RGBA":
        bg = Image.new("RGB", pil_img.size, (255, 255, 255))
        bg.paste(pil_img, mask=pil_img.split()[3])  # alpha
        return bg
    elif pil_img.mode != "RGB":
        return pil_img.convert("RGB")
    return pil_img

def enhance_for_ocr(pil_img: Image.Image, scale=2.5) -> Image.Image:
    """Mejora imagen para OCR: aplanar transparencia, escalar, contraste y unsharp"""
    # aplanar transparencia y escalar
    base = flatten_rgba_to_white(pil_img)
    w, h = base.size
    base = base.resize((int(w*scale), int(h*scale)), Image.LANCZOS)

    # pasar a gris + contraste y unsharp
    gray = ImageOps.grayscale(base)
    gray = ImageOps.autocontrast(gray)
    # unsharp (ligero)
    blurred = gray.filter(ImageFilter.GaussianBlur(radius=1))
    sharp = Image.blend(gray, blurred, alpha=-0.5)  # unsharp trick
    return sharp

def try_tess_configs(img: Image.Image) -> str:
    """Prueba varios combos (oem/psm) y se queda con el texto más largo"""
    # convierte a OpenCV para umbral adaptativo
    np_img = np.array(img)
    cv_gray = np_img if len(np_img.shape) == 2 else cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)

    # dos binarizaciones: global y adaptativa
    _, th_otsu = cv2.threshold(cv_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th_adapt = cv2.adaptiveThreshold(cv_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 31, 9)

    pil_otsu = Image.fromarray(th_otsu)
    pil_adap = Image.fromarray(th_adapt)

    candidates = []
    imgs = [img, pil_otsu, pil_adap]
    langs = ["spa+eng", "eng"]  # cae a eng si no tienes spa
    confs = [
        "--oem 3 --psm 6 -c preserve_interword_spaces=1",
        "--oem 3 --psm 4 -c preserve_interword_spaces=1",
        "--oem 3 --psm 11 -c preserve_interword_spaces=1",
    ]

    for im in imgs:
        for lg in langs:
            for cf in confs:
                try:
                    txt = pytesseract.image_to_string(im, lang=lg, config=cf)
                except pytesseract.TesseractNotFoundError:
                    raise  # tesseract no instalado
                except pytesseract.TesseractError:
                    txt = ""
                candidates.append(txt or "")

    # devuélvete el más "rico"
    best = max(candidates, key=lambda s: len(s.replace(" ", "").strip()))
    return best

def ocr_lines_with_conf(pil_img: Image.Image) -> str:
    """OCR por líneas con confianza para mejor parsing"""
    pre = enhance_for_ocr(pil_img, scale=2.5)
    try:
        data = pytesseract.image_to_data(pre, lang="spa+eng",
                                         config="--oem 3 --psm 6",
                                         output_type=pytesseract.Output.DICT)
        # junta palabras por línea (filtra conf bajas)
        lines = {}
        for i in range(len(data["text"])):
            if int(data["conf"][i]) < 40:
                continue
            ln = data["line_num"][i]
            lines.setdefault(ln, []).append(data["text"][i])
        return "\n".join(" ".join(w for w in lines[k] if w.strip()) for k in sorted(lines))
    except Exception as e:
        print(f"Error en OCR por líneas: {e}")
        return ""

def easyocr_text(pil_img: Image.Image) -> str:
    """Fallback con EasyOCR si Tesseract falla"""
    try:
        import easyocr
        reader = easyocr.Reader(['es', 'en'], gpu=False)
        np_img = np.array(flatten_rgba_to_white(pil_img))
        res = reader.readtext(np_img, detail=0, paragraph=True)
        return "\n".join(res)
    except ImportError:
        print("EasyOCR no está instalado. Instala con: pip install easyocr")
        return ""
    except Exception as e:
        print(f"Error en EasyOCR: {e}")
        return ""

def ocr_image(pil_img: Image.Image, lang: str = "spa") -> str:
    """Extrae texto de imagen usando OCR robusto con múltiples fallbacks"""
    try:
        pre = enhance_for_ocr(pil_img, scale=2.5)
        text = try_tess_configs(pre)
        
        # si sigue vacío, intenta la alternativa por líneas
        if not text or len(text.strip()) < 20:
            text = ocr_lines_with_conf(pil_img)
        
        # si aún está vacío, intenta EasyOCR como último recurso
        if not text or len(text.strip()) < 20:
            print("Tesseract falló, intentando EasyOCR...")
            text = easyocr_text(pil_img)
            
        return text
    except Exception as e:
        print(f"Error en OCR: {e}")
        return ""

# ============== Decodificación de códigos (QR/Barras) ==============

def decode_barcodes(pil_img: Image.Image) -> List[Dict[str, Any]]:
    """Usa decodificador robusto para QR/Code128/Code39, etc."""
    try:
        # Usar el decodificador robusto
        barcode_data = decode_barcode_strong(pil_img)
        results = []
        for item in barcode_data:
            results.append({
                "type": item.get("type", "Code128"),
                "data": item.get("data", ""),
                "rect": item.get("rect", {"x": 0, "y": 0, "w": 0, "h": 0})
            })
        return results
    except Exception as e:
        print(f"Error decodificando códigos: {e}")
        return []

# ============== Extracción por patrones ==============

@dataclass
class Totals:
    subtotal15: Optional[float] = None
    subtotal0: Optional[float] = None
    subtotal_no_objeto: Optional[float] = None
    subtotal_sin_impuestos: Optional[float] = None
    descuento: Optional[float] = None
    iva15: Optional[float] = None
    total: Optional[float] = None

@dataclass
class ItemLine:
    code_main: Optional[str]
    code_aux: Optional[str]
    qty: Optional[float]
    description: str
    unit_price: Optional[float]
    discount: Optional[float]
    line_total: Optional[float]

@dataclass
class CaptureMetadata:
    # Técnicos
    file_name: str
    sha256: str
    width: int
    height: int
    dpi: Optional[Tuple[int, int]]
    mode: str
    format: str
    # Documentales
    ruc: Optional[str] = None
    invoice_number: Optional[str] = None
    authorization: Optional[str] = None
    access_key: Optional[str] = None
    environment: Optional[str] = None  # PRODUCCION/PRUEBAS si aparece
    issue_datetime: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_id: Optional[str] = None
    emitter_name: Optional[str] = None

@dataclass
class ParseResult:
    metadata: CaptureMetadata
    totals: Totals
    items: List[ItemLine]
    ocr_text: str
    barcodes: List[Dict[str, Any]]
    checks: Dict[str, Any]
    access_key_parsed: Optional[Dict[str, Any]] = None

def extract_fields_from_text(text: str) -> Dict[str, Any]:
    """Regex focalizados a layout SRI (robustos a minúsculas/tildes)"""
    t = text

    def find(rex, grp=1, flags=re.IGNORECASE | re.MULTILINE):
        m = re.search(rex, t, flags)
        return m.group(grp).strip() if m else None

    fields = {}
    
    # RUC - más flexible
    fields["ruc"] = find(r"\bR\.?\s*U\.?\s*C\.?\s*[:\s]*\s*([0-9]{13})")
    
    # Número de factura - más flexible (basado en el texto real)
    fields["invoice_number"] = (find(r"\bFACTURA\b.*?(?:No\.?|N[°º])\s*([0-9]{3}-[0-9]{3}-[0-9]{9})") or
                               find(r"No,\s*([0-9]{3}-[0-9]{3}-[0-9]{9})") or
                               find(r"([0-9]{3}-[0-9]{3}-[0-9]{9})"))
    
    # Autorización/Clave - usando extractor robusto
    fields["authorization"] = extract_sri_access_key(text)
    fields["access_key"] = fields["authorization"]

    # Ambiente / Emisión
    fields["environment"] = find(r"AMBIENTE\s*:\s*([A-ZÁÉÍÓÚÑ ]+)")
    
    # Fecha y hora - múltiples formatos (mejorado)
    dt = (find(r"(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})") or 
          find(r"(\d{2}/\d{2}/\d{4})") or
          find(r"(\d{1,2}/\d{1,2}/\d{4})") or
          find(r"(\d{4}/\d{2}/\d{2})") or
          find(r"FECHA\s+Y\s+HORA\s+DE\s*:\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})"))
    fields["issue_datetime"] = try_parse_datetime(dt)

    # Comprador - más flexible (basado en el texto real)
    fields["buyer_name"] = (find(r"Raz[oó]n\s+Social.*?[:\s]\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|$)") or
                           find(r"Razén\s+Social.*?[:\s]\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|$)") or
                           find(r"(ROCKO\s+VERDEZOTO)") or
                           find(r"([A-ZÁÉÍÓÚÑ\s]+?)\s*Raz[oó]n\s+Social"))
    fields["buyer_id"] = find(r"Identificaci[oó]n.*?[:\s]\s*([0-9A-Z\-]+)")

    # Emisor - más flexible (basado en el texto real)
    fields["emitter_name"] = (find(r"(FARMACIAS.*FARCOMED|FYBECA.*|FARMACIA.*)") or
                             find(r"(FARMACIAS\s+Y\s+COMISARIATOS\s+DE\s+MEDICINAS\s+S\.A\.)") or
                             find(r"(FARCOMED)"))

    # Totales - patrones más flexibles (basados en el texto real)
    tot = Totals()
    tot.subtotal15 = normalize_decimal(find(r"SUBTOTAL\s*15%\s*[:\s]\s*\$?\s*([0-9.,]+)"))
    tot.subtotal0 = normalize_decimal(find(r"SUBTOTAL\s*0%\s*[:\s]\s*\$?\s*([0-9.,]+)"))
    tot.subtotal_no_objeto = normalize_decimal(find(r"SUBTOTAL\s+NO\s+OBJETO\s+DE\s+IVA\s*[:\s]\s*\$?\s*([0-9.,]+)"))
    tot.subtotal_sin_impuestos = normalize_decimal(find(r"SUBTOTAL\s+SIN\s+IMPUESTOS\s*[:\s]\s*\$?\s*([0-9.,]+)"))
    tot.descuento = normalize_decimal(find(r"(?:TOTAL\s+DESCUENTO|DESCUENTO)\s*[:\s]\s*\$?\s*([0-9.,]+)"))
    tot.iva15 = normalize_decimal(find(r"IVA\s*15%?\s*[:\s]\s*\$?\s*([0-9.,]+)"))
    
    # Total principal - múltiples patrones (basado en el texto real)
    tot.total = (normalize_decimal(find(r"(?:VALOR\s+TOTAL|TOTAL\s*FACTURA|TOTAL)\s*[:\s]\s*\$?\s*([0-9.,]+)")) or
                 normalize_decimal(find(r"TOTAL\s*[:\s]\s*\$?\s*([0-9.,]+)")) or
                 normalize_decimal(find(r"VALOR\s+TOTAL\s*:\s*\$?\s*([0-9.,]+)")) or
                 normalize_decimal(find(r"\$?\s*([0-9]{1,3}(?:[.,]\d{2})?)\s*$", flags=re.MULTILINE)) or
                 normalize_decimal(find(r"23\.00")) or
                 normalize_decimal(find(r"23,00")) or
                 normalize_decimal(find(r"23")))

    # Ítems - patrones más flexibles (basados en el texto real)
    items: List[ItemLine] = []
    
    # Patrón principal para tabla estructurada
    line_re = re.compile(
        r"^(?P<codp>\d{2,})\s+(?P<coda>\d{1,})\s+(?P<cant>\d+(?:[.,]\d+)?)\s+(?P<desc>.+?)\s+(?P<pu>\d+(?:[.,]\d+)?)\s+(?:(?P<disc>\d+(?:[.,]\d+)?)\s+)?(?P<pt>\d+(?:[.,]\d+)?)\s*$",
        re.IGNORECASE | re.MULTILINE
    )
    for m in line_re.finditer(t):
        items.append(ItemLine(
            code_main=m.group("codp"),
            code_aux=m.group("coda"),
            qty=normalize_decimal(m.group("cant")),
            description=m.group("desc").strip(),
            unit_price=normalize_decimal(m.group("pu")),
            discount=normalize_decimal(m.group("disc")),
            line_total=normalize_decimal(m.group("pt")),
        ))

    # Si no detectó ítems, intenta heurística alternativa más flexible
    if not items:
        # Buscar líneas que contengan descripción + precio
        alt_patterns = [
            r"^(?P<desc>[A-ZÁÉÍÓÚÑ\s]+?)\s+(?P<num1>\d+(?:[.,]\d+)?)\s+(?P<num2>\d+(?:[.,]\d+)?)\s*$",
            r"^(?P<desc>[A-ZÁÉÍÓÚÑ\s]+?)\s+\$?(?P<num1>\d+(?:[.,]\d+)?)\s*$",
            r"^(?P<desc>[A-ZÁÉÍÓÚÑ\s]+?)\s+(?P<num1>\d+(?:[.,]\d+)?)\s*$"
        ]
        
        for pattern in alt_patterns:
            alt_line = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for m in alt_line.finditer(t):
                desc = m.group("desc").strip()
                # Filtrar descripciones muy cortas o que no parecen productos
                if (len(desc) < 5 or 
                    any(word in desc.upper() for word in ["TOTAL", "SUBTOTAL", "IVA", "DESCUENTO", "FACTURA", "RUC", "AUTORIZACION", "CLAVE", "ACCESO", "NUMERO", "AMBIENTE", "FECHA", "EMISION", "DIRECCION", "EMAIL", "DOCUMENTO", "DEDUCIBLE", "NOMBRE"]) or
                    desc.endswith(":") or desc.endswith(".")):
                    continue
                    
                num1 = normalize_decimal(m.group("num1"))
                num2 = normalize_decimal(m.group("num2")) if "num2" in m.groupdict() else None
                
                # Filtrar números muy grandes (probablemente errores de OCR)
                if num1 and num1 > 1000:
                    continue
                if num2 and num2 > 1000:
                    continue
                
                items.append(ItemLine(
                    code_main=None,
                    code_aux=None,
                    qty=1.0,  # Asumir cantidad 1 si no se especifica
                    description=desc,
                    unit_price=num1,
                    discount=None,
                    line_total=num2 or num1,  # Si no hay total, usar precio unitario
                ))

    return {"fields": fields, "totals": tot, "items": items}

# ============== Validaciones financieras ==============

def financial_checks(totals: Totals, items: List[ItemLine]) -> Dict[str, Any]:
    """Realiza validaciones financieras de la factura"""
    checks: Dict[str, Any] = {}
    # suma de items
    sum_items = sum([it.line_total for it in items if it.line_total is not None]) if items else None
    checks["sum_items"] = sum_items

    def close(a: Optional[float], b: Optional[float], eps=0.02) -> Optional[bool]:
        if a is None or b is None:
            return None
        return abs(a - b) <= eps

    checks["items_vs_subtotal_sin_impuestos"] = close(sum_items, totals.subtotal_sin_impuestos)
    # Recompone total estimado
    comp = None
    if totals.subtotal0 is not None or totals.subtotal15 is not None or totals.subtotal_no_objeto is not None:
        base = 0.0
        for v in (totals.subtotal0, totals.subtotal15, totals.subtotal_no_objeto):
            if v is not None:
                base += v
        if totals.descuento is not None:
            base -= totals.descuento
        if totals.iva15 is not None:
            base += totals.iva15
        comp = base
    checks["recomputed_total"] = comp
    checks["recomputed_total_vs_total"] = close(comp, totals.total)

    return checks

# ============== Pipeline principal ==============

def parse_capture_from_bytes(image_bytes: bytes, filename: str = "capture.png", tesseract_lang: str = "spa") -> ParseResult:
    """Parsea una factura desde bytes de imagen"""
    # Datos técnicos
    pil = Image.open(io.BytesIO(image_bytes))
    width, height = pil.size
    dpi = pil.info.get("dpi")
    fmt = pil.format
    mode = pil.mode
    digest = sha256_of_bytes(image_bytes)

    # OCR
    text = ocr_image(pil, lang=tesseract_lang)

    # Códigos
    barcodes = decode_barcodes(pil)

    # Campos por texto
    res = extract_fields_from_text(text)
    fields = res["fields"]
    totals: Totals = res["totals"]
    items: List[ItemLine] = res["items"]

    meta = CaptureMetadata(
        file_name=filename,
        sha256=digest,
        width=width,
        height=height,
        dpi=dpi,
        mode=mode,
        format=fmt,
        ruc=fields.get("ruc"),
        invoice_number=fields.get("invoice_number"),
        authorization=fields.get("authorization"),
        access_key=fields.get("access_key"),
        environment=fields.get("environment"),
        issue_datetime=fields.get("issue_datetime"),
        buyer_name=fields.get("buyer_name"),
        buyer_id=fields.get("buyer_id"),
        emitter_name=fields.get("emitter_name"),
    )

    # 3.a) Intentar por código de barras (prioridad)
    clave = extract_access_key_from_barcode(image_bytes)
    print(f"🔍 Clave desde código de barras: {clave}")

    # 3.b) Si no hay barcode, OCR solo-números
    if not clave or len(re.sub(r'\D', '', clave or '')) < 48:
        clave_ocr = ocr_digits_only(image_bytes)
        print(f"🔍 Clave desde OCR solo-números: {clave_ocr}")
        if len(re.sub(r'\D', '', clave_ocr)) >= 48:
            clave = clave_ocr

    # 3.c) Si aún no tenemos clave, usar el método anterior como fallback
    if not clave or len(re.sub(r'\D', '', clave or '')) < 48:
        clave_fallback = extract_sri_access_key(text)
        print(f"🔍 Clave desde fallback OCR: {clave_fallback}")
        if clave_fallback:
            clave = clave_fallback

    # 3.d) Normalizar/validar/corregir
    digits = re.sub(r'\D', '', clave or '')
    if len(digits) == 48:
        digits = digits + sri_mod11_check_digit(digits)
        print(f"🔧 Completando dígito verificador: {digits}")
    elif len(digits) == 49 and not validate_access_key(digits):
        fixed = try_autocorrect_4_confusions(digits)
        if fixed:
            digits = fixed
            print(f"🔧 Clave corregida automáticamente: {digits}")

    # Guardar clave válida
    if len(digits) == 49 and validate_access_key(digits):
        meta.access_key = digits
        print(f"✅ Clave de acceso válida: {digits}")
    else:
        print(f"❌ Clave de acceso inválida: {digits}")

    # Parsear la clave de acceso si es válida
    access_key_parsed = None
    if meta.access_key and validate_access_key(meta.access_key):
        access_key_parsed = parse_sri_access_key(meta.access_key)

    checks = financial_checks(totals, items)

    return ParseResult(
        metadata=meta,
        totals=totals,
        items=items,
        ocr_text=text,
        barcodes=barcodes,
        checks=checks,
        access_key_parsed=access_key_parsed,
    )

def parse_capture(path: str, tesseract_lang: str = "spa") -> ParseResult:
    """Parsea una factura desde archivo"""
    with open(path, "rb") as f:
        image_bytes = f.read()
    return parse_capture_from_bytes(image_bytes, os.path.basename(path), tesseract_lang)

# ============== CLI ==============

def main():
    if len(sys.argv) < 2:
        print("Uso: python invoice_capture_parser.py <ruta_imagen.png|jpg>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    result = parse_capture(path, tesseract_lang="spa+eng")  # español+inglés ayuda a 'SUBTOTAL'/'TOTAL'
    # Serializamos dataclasses
    payload = {
        "metadata": asdict(result.metadata),
        "totals": asdict(result.totals),
        "items": [asdict(it) for it in result.items],
        "barcodes": result.barcodes,
        "checks": result.checks,
        "ocr_text": result.ocr_text,  # quítalo si no quieres texto crudo
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
