# Config layer - Configuración y DI

# Configuración de la aplicación
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10MB
SRI_TIMEOUT = 30  # 30 segundos

# Configuración de comparación de productos
PRICE_EPS = 0.01  # Épsilon para comparación de precios
QTY_EPS = 0.001   # Épsilon para comparación de cantidades
TOTAL_EPS = 0.01  # Épsilon para comparación de totales
MATCH_THRESHOLD = 0.8  # Umbral de coincidencia para productos

# Configuración de análisis de riesgo
TEXT_MIN_LEN_FOR_DOC = 100  # Longitud mínima de texto para considerar documento
ONEPAGE_MIN_BYTES = 50000  # Mínimo de bytes para página única
ONEPAGE_MAX_BYTES_TEXTUAL = 200000  # Máximo de bytes para PDF textual
ONEPAGE_MAX_BYTES_ESCANEADO = 500000  # Máximo de bytes para PDF escaneado

# Pesos de riesgo (desde risk_weights.json)
RISK_WEIGHTS = {
    "fecha_creacion_vs_emision": 16,
    "fecha_mod_vs_creacion": 12,
    "software_conocido": 12,
    "capas_multiples": 30,
    "consistencia_fuentes": 15,
    "dpi_uniforme": 15,
    "compresion_estandar": 6,
    "alineacion_texto": 15,
    "anotaciones_o_formularios": 3,
    "javascript_embebido": 2,
    "archivos_incrustados": 3,
    "firmas_pdf": 10,
    "actualizaciones_incrementales": 3,
    "cifrado_permisos_extra": 2,
    "math_consistency": 10,
    "validacion_financiera": 15,
    "sri_verificacion": 20,
    "extraccion_texto_ocr": 30,
    "inconsistencias_ruido_bordes": 5,
    "analisis_ela_sospechoso": 5,
    "metadatos_sospechosos": 5,
    "texto_superpuesto": 25,
    "capas_ocultas": 20,
    "evidencias_forenses": 15
}

# Niveles de riesgo (desde risk_levels_config.json)
RISK_LEVELS = {
    "bajo": [0, 25],
    "medio": [26, 42],
    "alto": [43, 100]
}

# Filtros estándar de imagen
STD_IMAGE_FILTERS = [
    "blur",
    "sharpen", 
    "contrast",
    "brightness"
]

# Descripciones de pesos de riesgo (desde risk_weights_descriptions.json)
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
        "valor": 4,
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
        "descripcion": "Consistencia aritmética y validación financiera completa",
        "explicacion": "Validación de coherencia en cálculos (subtotal + IVA - descuentos = total), items individuales, porcentajes de impuestos y detección de anomalías financieras. Errores matemáticos pueden indicar manipulación."
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
    },
    "evidencias_forenses": {
        "valor": 15,
        "descripcion": "Evidencias forenses generales de manipulación",
        "explicacion": "Indicadores técnicos que sugieren que la imagen ha sido modificada o manipulada digitalmente."
    }
}

# Archivo de configuración
CONFIG_FILE = "config.json"

# Configuración de Tesseract
import os
import platform

def configure_tesseract():
    """Configura Tesseract globalmente para Windows y Linux"""
    try:
        import pytesseract
        
        # Detectar el sistema operativo
        sistema = platform.system().lower()
        
        if sistema == "windows":
            # Configuración para Windows
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
                "tesseract"  # Si está en PATH
            ]
            
            tesseract_found = False
            for path in tesseract_paths:
                if os.path.exists(path) or path == "tesseract":
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✅ Tesseract configurado para Windows: {path}")
                    tesseract_found = True
                    break
            
            if not tesseract_found:
                print("❌ Tesseract no encontrado en Windows. Instala Tesseract-OCR")
                pytesseract.pytesseract.tesseract_cmd = "tesseract"  # Fallback
                
        else:
            # Configuración para Linux (Docker/producción)
            tesseract_paths = [
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract",
                "tesseract"  # Si está en PATH
            ]
            
            tesseract_found = False
            for path in tesseract_paths:
                if os.path.exists(path) or path == "tesseract":
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✅ Tesseract configurado para Linux: {path}")
                    tesseract_found = True
                    break
            
            if not tesseract_found:
                print("❌ Tesseract no encontrado en Linux. Instala tesseract-ocr")
                pytesseract.pytesseract.tesseract_cmd = "tesseract"  # Fallback
                
    except Exception as e:
        print(f"❌ Error configurando Tesseract: {e}")
        # Fallback
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = "tesseract"
        except:
            pass

# Configurar Tesseract al importar el módulo
configure_tesseract()
