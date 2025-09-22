import re, io, sys, json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from PIL import Image
import fitz  # PyMuPDF
import pytesseract
from pyzbar.pyzbar import decode as zbar_decode

# --- (Windows) descomenta si no está en PATH ---
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ========== OCR helpers ==========
def render_page_image(page, dpi=300) -> Image.Image:
    zoom = dpi/72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def ocr_image(img: Image.Image) -> str:
    # Config genérico: psm 6 (bloques), preserva espacios
    config = "--oem 3 --psm 6 -c preserve_interword_spaces=1"
    try:
        return pytesseract.image_to_string(img, lang="spa+eng", config=config)
    except Exception:
        return ""

# ========== SRI access key extractor ==========
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

def validate_sri_access_key(key: str) -> bool:
    return es_clave_valida(key)

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

TRANS = str.maketrans({'O':'0','o':'0','S':'5','s':'5','I':'1','l':'1','|':'1','B':'8'})
HDR = re.compile(r'(?:N[ÚU]MERO\s+DE\s+AUTORIZACI[ÓO]N|AUTORIZACI[ÓO]N|CLAVE\s+DE\s+ACCESO)', re.I)

def extract_access_key(text: str) -> Optional[str]:
    t = text.translate(TRANS)
    cands = []
    m = HDR.search(t)
    if m:
        win = t[m.end(): m.end()+400]
        cands += re.findall(r'(?:\d[\s\-.]{0,2}){44,55}', win)
    cands += re.findall(r'(?:\d[\s\-.]{0,2}){44,55}', t)
    cleaned = [''.join(re.findall(r'\d', c)) for c in cands if c]
    cleaned = [c for c in cleaned if len(c) >= 44]
    cleaned.sort(key=len, reverse=True)

    for c in cleaned:
        for i in range(0, len(c)-48):
            key = c[i:i+49]
            if validate_sri_access_key(key):
                return key
    if cleaned:
        best = cleaned[0]
        return best[:49] if len(best) >= 49 else None
    return None

# ========== PDF pipeline ==========
@dataclass
class PageResult:
    page_index: int
    method: str   # "text" o "ocr"
    text_len: int

def extract_text_smart(pdf_path: str) -> Dict[str, Any]:
    doc = fitz.open(pdf_path)
    all_text = []
    pages_info: List[PageResult] = []
    barcodes: List[str] = []

    for i, page in enumerate(doc):
        txt = page.get_text("text") or ""
        if len(txt.strip()) >= 80:  # umbral: hay texto nativo suficiente
            all_text.append(txt)
            pages_info.append(PageResult(i, "text", len(txt)))
        else:
            img = render_page_image(page, dpi=300)
            # intentar decodificar código de barras por si es la clave completa
            for sym in zbar_decode(img):
                data = sym.data.decode("utf-8", "ignore")
                if data and data.isdigit():
                    barcodes.append(data)
            ocr = ocr_image(img)
            all_text.append(ocr)
            pages_info.append(PageResult(i, "ocr", len(ocr)))

    full_text = "\n".join(all_text)
    key = None
    key_parsed = None
    
    # 1) si algún barcode tiene 49 dígitos válidos, úsalo
    for b in barcodes:
        if len(b) == 49 and validate_sri_access_key(b):
            key = b
            break
    # 2) si no, extrae del texto
    if not key:
        key = extract_access_key(full_text)
    
    # 3) parsear la clave si es válida
    if key and validate_sri_access_key(key):
        key_parsed = parse_sri_access_key(key)

    return {
        "pages": [asdict(p) for p in pages_info],
        "text_length": len(full_text.strip()),
        "access_key": key,
        "access_key_parsed": key_parsed,
        "barcodes": barcodes,
        "text": full_text  # elimina si no quieres el texto completo
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pdf_smart_text.py factura.pdf")
        sys.exit(1)
    res = extract_text_smart(sys.argv[1])
    print(json.dumps(res, ensure_ascii=False, indent=2))

