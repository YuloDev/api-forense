import os
import json   

# --------------------------- CONFIG ----------------------------------
SRI_WSDL = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
MAX_PDF_BYTES = int(os.getenv("MAX_PDF_BYTES", 10 * 1024 * 1024))  # 10 MB
SRI_TIMEOUT = float(os.getenv("SRI_TIMEOUT", "12"))
TEXT_MIN_LEN_FOR_DOC = int(os.getenv("TEXT_MIN_LEN_FOR_DOC", "50"))
RENDER_DPI = int(os.getenv("RENDER_DPI", "260"))
EASYOCR_LANGS = os.getenv("EASYOCR_LANGS", "es,en").split(",")
EASYOCR_GPU = os.getenv("EASYOCR_GPU", "false").lower() == "true"

# Tolerancias comparación SRI vs PDF
QTY_EPS = float(os.getenv("CMP_QTY_EPS", "0.001"))
PRICE_EPS = float(os.getenv("CMP_PRICE_EPS", "0.01"))
TOTAL_EPS = float(os.getenv("CMP_TOTAL_EPS", "0.02"))
MATCH_THRESHOLD = float(os.getenv("CMP_MATCH_THRESHOLD", "0.60"))

CONFIG_FILE = "risk_weights.json"

# cargar desde json si existe
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        RISK_WEIGHTS = json.load(f)
else:
    RISK_WEIGHTS = {
        "fecha_creacion_vs_emision": 15,
        "fecha_mod_vs_creacion": 12,
        "software_conocido": 12,
        "num_paginas": 10,
        "capas_multiples": 10,
        "consistencia_fuentes": 8,
        "dpi_uniforme": 8,
        "compresion_estandar": 6,
        "alineacion_texto": 6,
        "tamano_esperado": 6,
        "anotaciones_o_formularios": 3,
        "javascript_embebido": 2,
        "archivos_incrustados": 3,
        "firmas_pdf": -4,
        "actualizaciones_incrementales": 3,
        "cifrado_permisos_extra": 2,
    }
    
# Cargar RISK_LEVELS (con persistencia)
RISK_LEVELS_FILE = "risk_levels_config.json"
if os.path.exists(RISK_LEVELS_FILE):
    with open(RISK_LEVELS_FILE, "r", encoding="utf-8") as f:
        risk_levels_data = json.load(f)
        # Convertir listas a tuplas
        RISK_LEVELS = {k: tuple(v) if isinstance(v, list) else v for k, v in risk_levels_data.items()}
else:
    RISK_LEVELS = {"bajo": (0, 29), "medio": (30, 59), "alto": (60, 100)}

# Heurística fechas
MAX_DIAS_CREACION_EMISION_OK = int(os.getenv("MAX_DIAS_CREACION_EMISION_OK", "30"))
MAX_DIAS_MOD_VS_CREACION_OK = int(os.getenv("MAX_DIAS_MOD_VS_CREACION_OK", "10"))

# Heurística tamaño esperado
ONEPAGE_MIN_BYTES = int(os.getenv("ONEPAGE_MIN_BYTES", "20000"))
ONEPAGE_MAX_BYTES_TEXTUAL = int(os.getenv("ONEPAGE_MAX_BYTES_TEXTUAL", "1200000"))
ONEPAGE_MAX_BYTES_ESCANEADO = int(os.getenv("ONEPAGE_MAX_BYTES_ESCANEADO", "3500000"))

KNOWN_PRODUCERS = [
    "adobe", "itext", "apache pdfbox", "libreoffice", "microsoft",
    "wkhtmltopdf", "reportlab", "foxit", "tcpdf", "aspose", "prince", "weasyprint"
]

STD_IMAGE_FILTERS = {
    "DCTDecode", "FlateDecode", "JPXDecode", "JBIG2Decode",
    "CCITTFaxDecode", "RunLengthDecode", "LZWDecode"
}
