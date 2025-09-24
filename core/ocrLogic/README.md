# OCR Logic - Servicio de Reconocimiento Óptico de Caracteres

## 📁 Estructura del Proyecto

```
core/
└── ocrLogic/
    ├── servicios/
    │   └── ocr_service.py      # Lógica de negocio del OCR
    └── README.md              # Esta documentación

routes/
└── ocr.py                     # Endpoints de la API
```

## 🚀 Endpoints Disponibles

### 1. **POST /ocr/extract-image**
Extraer texto de una imagen usando OCR

**Parámetros:**
- `image_base64` (string): Imagen codificada en base64
- `language` (string, opcional): Idioma para OCR (default: "spa+eng")
- `min_confidence` (int, opcional): Confianza mínima (default: 30)

**Ejemplo de uso:**
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "language": "spa+eng",
  "min_confidence": 50
}
```

**Respuesta:**
```json
{
  "success": true,
  "text": "Texto extraído de la imagen",
  "language": "spa+eng",
  "confidence": 85.5,
  "word_count": 5,
  "processing_time": 0.234,
  "error": null
}
```

### 2. **POST /ocr/extract-pdf**
Extraer texto de un PDF usando OCR

**Parámetros:**
- `pdf_base64` (string): PDF codificado en base64
- `language` (string, opcional): Idioma para OCR (default: "spa+eng")
- `min_confidence` (int, opcional): Confianza mínima (default: 30)
- `page_range` (string, opcional): Rango de páginas (default: "all")
  - `"all"`: Todas las páginas
  - `"1"`: Solo página 1
  - `"1-3"`: Páginas 1 a 3
  - `"1,3,5"`: Páginas 1, 3 y 5

**Ejemplo de uso:**
```json
{
  "pdf_base64": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCg==",
  "language": "spa+eng",
  "min_confidence": 50,
  "page_range": "1-3"
}
```

**Respuesta:**
```json
{
  "success": true,
  "pages": [
    {
      "page_number": 1,
      "text": "Texto de la página 1",
      "confidence": 85.5,
      "word_count": 25,
      "image_size": [800, 600]
    },
    {
      "page_number": 2,
      "text": "Texto de la página 2",
      "confidence": 82.3,
      "word_count": 30,
      "image_size": [800, 600]
    }
  ],
  "total_pages": 5,
  "total_text": "Texto de la página 1\n\nTexto de la página 2",
  "language": "spa+eng",
  "average_confidence": 83.9,
  "total_word_count": 55,
  "processing_time": 1.234,
  "error": null
}
```

## 🔧 Funcionalidades

### **Para Imágenes:**
- ✅ **Extracción de texto** de imágenes (PNG, JPEG, TIFF, BMP)
- ✅ **Filtrado por confianza** (solo palabras con confianza >= min_confidence)
- ✅ **Soporte multiidioma** (español, inglés, combinaciones)
- ✅ **Estadísticas básicas** (confianza promedio, conteo de palabras)
- ✅ **Manejo de errores** robusto
- ✅ **Tiempo de procesamiento** incluido

### **Para PDFs:**
- ✅ **Extracción de texto** de PDFs usando OCR
- ✅ **Procesamiento por páginas** con estadísticas individuales
- ✅ **Selección de rango de páginas** (todas, específicas, rangos)
- ✅ **Alta resolución** (2x) para mejor calidad de OCR
- ✅ **Estadísticas globales** y por página
- ✅ **Texto consolidado** de todas las páginas
- ✅ **Manejo de errores** robusto

## 🛠️ Configuración

El servicio utiliza la configuración global de Tesseract:
- **Ruta**: `/usr/bin/tesseract`
- **Idiomas**: Español + Inglés por defecto
- **Configuración**: `--oem 3 --psm 6`
- **Dependencias**: PyMuPDF (fitz) para procesamiento de PDFs

## 📝 Notas de Uso

1. **Formato de imagen**: PNG, JPEG, TIFF, BMP
2. **Formato de PDF**: PDF estándar
3. **Codificación**: Base64 para ambos
4. **Tamaño máximo**: Depende de la configuración del servidor
5. **Idiomas**: Soporta español, inglés y combinaciones
6. **Confianza mínima**: Filtra palabras con baja confianza
7. **Rango de páginas**: Formato flexible para PDFs

## 🔍 Casos de Uso

- **Extracción de texto** de documentos escaneados
- **Procesamiento de facturas** y formularios
- **Análisis de documentos PDF** con OCR
- **Procesamiento por lotes** de páginas específicas
- **Integración** con otros servicios del sistema
