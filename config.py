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

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") 
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

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
        },
        "math_consistency": {
            "valor": 10,
            "descripcion": "Consistencia aritmética: subtotal + impuestos − descuentos − retenciones = total",
            "explicacion": "Descuadres contables evidencian manipulación o error."
        },
        "sri_verificacion": {
            "valor": 20,
            "descripcion": "Verificación exitosa contra el SRI (Servicio de Rentas Internas)",
            "explicacion": "La capacidad de verificar el documento contra registros oficiales del SRI aumenta significativamente la confiabilidad."
        },
        "extraccion_texto_ocr": {
            "valor": 30,
            "descripcion": "Extracción de texto mediante OCR (Reconocimiento Óptico de Caracteres)",
            "explicacion": "La incapacidad de extraer texto legible de una imagen puede indicar manipulación, baja calidad o formato no estándar."
        },
        "inconsistencias_ruido_bordes": {
            "valor": 18,
            "descripcion": "Inconsistencias en patrones de ruido y bordes",
            "explicacion": "Patrones de ruido inconsistentes pueden indicar edición local, clonado o pegado de elementos."
        },
        "analisis_ela_sospechoso": {
            "valor": 12,
            "descripcion": "Análisis ELA (Error Level Analysis) sospechoso",
            "explicacion": "El ELA detecta áreas de la imagen que han sido editadas o re-comprimidas, indicando posible manipulación."
        },
        "metadatos_sospechosos": {
            "valor": 5,
            "descripcion": "Metadatos EXIF/IPTC/XMP sospechosos o inconsistentes",
            "explicacion": "Metadatos faltantes, inconsistentes o con información sospechosa pueden indicar manipulación."
        },
        "texto_superpuesto": {
            "valor": 25,
            "descripcion": "Detección de texto superpuesto en imagen",
            "explicacion": "Texto superpuesto puede indicar que se agregó información sobre el documento original."
        },
        "capas_ocultas": {
            "valor": 20,
            "descripcion": "Presencia de capas ocultas en formatos que las soportan",
            "explicacion": "Capas ocultas pueden contener información no visible que modifica el contenido aparente del documento."
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
