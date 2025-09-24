# API de OCR para PDFs

Este módulo proporciona endpoints para realizar OCR (Reconocimiento Óptico de Caracteres) en documentos PDF usando PyMuPDF y Tesseract.

## Características

- ✅ **Extracción inteligente**: Usa texto embebido del PDF cuando está disponible, OCR cuando es necesario
- ✅ **Múltiples idiomas**: Soporta español, inglés y combinaciones (ej: "spa+eng")
- ✅ **Configuración flexible**: Múltiples modos PSM y OEM de Tesseract
- ✅ **Dos formatos de entrada**: Base64 o upload directo de archivo
- ✅ **Información detallada**: Reporte de método usado por página, tiempo de procesamiento

## Endpoints Disponibles

### 1. `/ocr-pdf` - OCR con Base64

**POST** `/ocr-pdf`

Procesa un PDF codificado en base64.

#### Request Body:
```json
{
  "pdf_base64": "JVBERi0xLjQK...",
  "lang": "spa",              // Opcional: idioma(s) para Tesseract
  "oem": 3,                   // Opcional: OEM mode (0-3)
  "psm": 3,                   // Opcional: PSM mode (0-13)
  "dpi": 300,                 // Opcional: DPI hint
  "force_ocr": false,         // Opcional: forzar OCR
  "min_embedded_chars": 40    // Opcional: mínimo chars para texto embebido
}
```

#### Response:
```json
{
  "success": true,
  "text": "---- PÁGINA 1/1 (embedded) ----\n\nTexto extraído...",
  "pages": 1,
  "method_per_page": [
    {
      "page": 1,
      "method": "embedded",
      "chars": 1250
    }
  ],
  "total_chars": 1250,
  "processing_time": 0.45,
  "error": null
}
```

### 2. `/ocr-pdf-upload` - OCR con Upload

**POST** `/ocr-pdf-upload`

Acepta upload directo de archivo PDF.

#### Form Data:
- `file`: Archivo PDF
- `lang`: Idioma (opcional, default: "spa")
- `oem`: OEM mode (opcional, default: 3)
- `psm`: PSM mode (opcional, default: 3)
- `dpi`: DPI hint (opcional, default: 300)
- `force_ocr`: Forzar OCR (opcional, default: false)
- `min_embedded_chars`: Mínimo chars embebidos (opcional, default: 40)

#### Response:
```json
{
  "success": true,
  "text": "Texto extraído del PDF...",
  "pages": 2,
  "method_per_page": [...],
  "total_chars": 2150,
  "processing_time": 1.23,
  "filename": "documento.pdf",
  "file_size": 245760,
  "error": null
}
```

### 3. `/ocr-info` - Información del Sistema

**GET** `/ocr-info`

Devuelve información sobre las capacidades de OCR.

#### Response:
```json
{
  "tesseract_available": true,
  "tesseract_version": "5.3.0",
  "available_languages": ["eng", "spa", "osd"],
  "supported_formats": ["PDF"],
  "max_file_size_mb": 50.0,
  "default_config": {
    "lang": "spa",
    "oem": 3,
    "psm": 3,
    "dpi": 300,
    "force_ocr": false,
    "min_embedded_chars": 40
  },
  "psm_modes": {
    "3": "Fully automatic page segmentation, but no OSD (Default)",
    "6": "Assume a single uniform block of text",
    "7": "Treat the image as a single text line",
    ...
  },
  "oem_modes": {
    "3": "Default, based on what is available (Default)",
    ...
  }
}
```

## Parámetros de Configuración

### Idiomas (`lang`)
- `"spa"`: Español
- `"eng"`: Inglés  
- `"spa+eng"`: Español + Inglés
- Ver `/ocr-info` para idiomas disponibles

### PSM Modes (`psm`)
- `3`: Segmentación automática completa (Default)
- `6`: Bloque uniforme de texto
- `7`: Línea única de texto
- `8`: Palabra única
- `11`: Texto disperso (sparse)

### OEM Modes (`oem`)
- `0`: Solo motor legacy
- `1`: Solo LSTM neural
- `2`: Legacy + LSTM
- `3`: Por defecto basado en disponibilidad (Default)

## Ejemplos de Uso

### Ejemplo con cURL - Base64:
```bash
curl -X POST "http://localhost:8000/ocr-pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_base64": "JVBERi0xLjQK...",
    "lang": "spa",
    "force_ocr": true
  }'
```

### Ejemplo con cURL - Upload:
```bash
curl -X POST "http://localhost:8000/ocr-pdf-upload" \
  -F "file=@documento.pdf" \
  -F "lang=spa+eng" \
  -F "psm=6"
```

### Ejemplo con Python:
```python
import requests
import base64

# Leer PDF
with open("documento.pdf", "rb") as f:
    pdf_data = base64.b64encode(f.read()).decode()

# Enviar request
response = requests.post("http://localhost:8000/ocr-pdf", json={
    "pdf_base64": pdf_data,
    "lang": "spa",
    "force_ocr": False
})

result = response.json()
print(f"Texto extraído: {result['text'][:100]}...")
print(f"Páginas: {result['pages']}")
print(f"Tiempo: {result['processing_time']:.2f}s")
```

## Requisitos del Sistema

### Software Requerido:
- **Tesseract OCR**: Debe estar instalado en el sistema
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki
  - macOS: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`

### Paquetes de Idiomas (Opcional):
- **Español**: `tesseract-ocr-spa`
- **Inglés**: Incluido por defecto

### Dependencias Python:
```bash
pip install pytesseract pillow PyMuPDF
```

## Límites y Restricciones

- **Tamaño máximo**: Definido por `MAX_PDF_BYTES` en config
- **Formatos soportados**: Solo PDF
- **Dependencia externa**: Requiere Tesseract instalado

## Estrategia de Procesamiento

1. **Verificación de texto embebido**: Si el PDF tiene texto extraíble de calidad, lo usa directamente
2. **OCR como fallback**: Solo aplica OCR cuando el texto embebido es insuficiente
3. **Procesamiento por página**: Cada página puede usar un método diferente
4. **Optimización de calidad**: Renderiza a alta resolución para mejor OCR

## Manejo de Errores

- **400**: PDF base64 inválido, parámetros incorrectos
- **413**: Archivo demasiado grande
- **500**: Tesseract no disponible, error de procesamiento

La API está diseñada para ser robusta y proporcionar información detallada sobre el proceso de extracción de texto.
