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
DESCRIPTIONS_FILE = "risk_weights_descriptions.json"

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

# Cargar descripciones de RISK_WEIGHTS
if os.path.exists(DESCRIPTIONS_FILE):
    with open(DESCRIPTIONS_FILE, "r", encoding="utf-8") as f:
        RISK_WEIGHTS_DESCRIPTIONS = json.load(f)
else:
    # Descripciones por defecto si no existe el archivo
    RISK_WEIGHTS_DESCRIPTIONS = {
        "fecha_creacion_vs_emision": {
            "valor": 15,
            "descripcion": "Diferencia entre la fecha de creación del PDF y la fecha de emisión del documento",
            "explicacion": "Un documento legítimo debería crearse cerca de su fecha de emisión. Diferencias grandes pueden indicar manipulación."
        },
        "fecha_mod_vs_creacion": {
            "valor": 12,
            "descripcion": "Diferencia entre la fecha de modificación y creación del PDF",
            "explicacion": "Modificaciones posteriores a la creación pueden sugerir alteraciones del documento original."
        },
        "software_conocido": {
            "valor": 12,
            "descripcion": "Uso de software conocido y confiable para crear el PDF",
            "explicacion": "Documentos creados con software desconocido o poco común pueden ser sospechosos."
        },
        "num_paginas": {
            "valor": 10,
            "descripcion": "Número de páginas esperado para el tipo de documento",
            "explicacion": "Facturas típicamente tienen una página. Múltiples páginas pueden indicar manipulación."
        },
        "capas_multiples": {
            "valor": 10,
            "descripcion": "Presencia de capas múltiples (OCG) en el PDF",
            "explicacion": "Las capas pueden usarse para ocultar o superponer información, común en documentos manipulados."
        },
        "consistencia_fuentes": {
            "valor": 8,
            "descripcion": "Consistencia en el uso de fuentes tipográficas",
            "explicacion": "Mezcla excesiva de fuentes puede indicar que el documento fue compuesto de múltiples fuentes."
        },
        "dpi_uniforme": {
            "valor": 8,
            "descripcion": "Uniformidad en la resolución (DPI) de las imágenes",
            "explicacion": "Resoluciones muy diferentes pueden indicar inserción de imágenes de distintas fuentes."
        },
        "compresion_estandar": {
            "valor": 6,
            "descripcion": "Uso de métodos de compresión estándar",
            "explicacion": "Métodos de compresión inusuales pueden indicar manipulación o generación no estándar."
        },
        "alineacion_texto": {
            "valor": 6,
            "descripcion": "Alineación correcta de elementos de texto",
            "explicacion": "Texto mal alineado o con rotaciones extrañas puede indicar manipulación digital."
        },
        "tamano_esperado": {
            "valor": 6,
            "descripcion": "Tamaño de archivo apropiado para el tipo de documento",
            "explicacion": "Archivos muy grandes o pequeños para su contenido pueden ser sospechosos."
        },
        "anotaciones_o_formularios": {
            "valor": 3,
            "descripcion": "Presencia de anotaciones o campos de formulario",
            "explicacion": "Elementos interactivos en documentos oficiales pueden facilitar la manipulación."
        },
        "javascript_embebido": {
            "valor": 2,
            "descripcion": "Código JavaScript embebido en el PDF",
            "explicacion": "JavaScript en documentos oficiales es inusual y puede usarse para ocultar contenido."
        },
        "archivos_incrustados": {
            "valor": 3,
            "descripcion": "Archivos adjuntos o incrustados en el PDF",
            "explicacion": "Archivos ocultos dentro del PDF pueden contener información maliciosa o no autorizada."
        },
        "firmas_pdf": {
            "valor": -4,
            "descripcion": "Presencia de firmas digitales válidas",
            "explicacion": "Las firmas digitales aumentan la confiabilidad del documento (reduce el riesgo)."
        },
        "actualizaciones_incrementales": {
            "valor": 3,
            "descripcion": "Múltiples actualizaciones incrementales del PDF",
            "explicacion": "Muchas modificaciones pueden indicar alteraciones sucesivas del documento original."
        },
        "cifrado_permisos_extra": {
            "valor": 2,
            "descripcion": "Cifrado o permisos especiales aplicados",
            "explicacion": "Restricciones inusuales pueden usarse para ocultar el método de creación del documento."
        }
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
