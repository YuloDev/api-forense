# 🔍 Detección de Texto Superpuesto en PDFs

## Descripción

Este endpoint especializado analiza las **4 zonas principales** donde se puede "tapar" texto en un PDF, detectando posibles manipulaciones o superposiciones de contenido.

## 🎯 Zonas Analizadas

### 1. **Anotaciones (Annotations)** - Probabilidad ALTA
- **Ubicación**: `/Annots` (array) de cada página
- **Características**: 
  - `/Subtype` (FreeText, Square, Stamp, Widget, etc.)
  - `/Rect` (bounding box)
  - `/AP /N` (appearance stream - el contenido visual)
- **Uso común**: Comentarios, notas, sellos, campos de formulario

### 2. **Contenido de Página (Page Contents)** - Probabilidad ALTA  
- **Ubicación**: `/Contents` (stream o array de streams)
- **Características**:
  - `BT ... Tj/TJ ... ET` (comandos de texto)
  - `re f` (rectángulo relleno)
  - `rg/k` (colores)
- **Uso común**: Editores que "estampan" texto al final del stream

### 3. **Form XObject** - Probabilidad MEDIA
- **Ubicación**: `/Resources /XObject`
- **Características**:
  - Se invocan con `/Nombre Do`
  - No tocan el stream principal
- **Uso común**: Forma elegante de superponer bloques reutilizables

### 4. **AcroForm (Campos de Formulario)** - Probabilidad BAJA
- **Ubicación**: `/AcroForm /Fields`
- **Características**:
  - `/Subtype /Widget` en `/Annots`
  - `/AP /N` (apariencia del campo)
- **Uso común**: Campos de formulario específicos

### 5. **Análisis Avanzado de Overlay** ⭐ **NUEVO** - Probabilidad MUY ALTA
- **Render Diff**: Compara imagen con/sin anotaciones para detectar diferencias visuales
- **IoU Calculation**: Usa Intersection over Union para detectar superposiciones precisas
- **Stream Analysis**: Analiza el contenido del PDF en busca de patrones sospechosos
- **Elementos Sospechosos**: Detecta imágenes y figuras que tapan texto
- **Búsqueda de Texto**: Busca texto específico en el contenido del stream
- **Técnicas Combinadas**: Integra múltiples métodos para máxima precisión

### 6. **Análisis por Stream** 🎯 **MÁS PRECISO** - Probabilidad MÁXIMA
- **Stream-by-Stream**: Analiza cada stream de contenido individualmente
- **Pixel Comparison**: Compara píxeles con threshold preciso (1% por defecto)
- **Exact Detection**: Identifica el stream exacto que introduce el overlay
- **Visual Rendering**: Renderiza PDFs con diferentes combinaciones de streams
- **Mathematical Precision**: Usa comparación de píxeles para detección exacta
- **Maximum Accuracy**: Método más preciso disponible para detectar overlays

## 🚀 Endpoints Disponibles

### POST `/detectar-texto-superpuesto`
**Análisis principal del PDF**

**Parámetros:**
```json
{
  "pdfbase64": "string (requerido)",
  "incluir_reporte": "boolean (opcional, default: true)",
  "incluir_xml": "boolean (opcional, default: true)"
}
```

**Respuesta:**
```json
{
  "success": true,
  "mensaje": "Análisis completado exitosamente",
  "analisis_detallado": {
    "zona_1_anotaciones": { ... },
    "zona_2_contenido_pagina": { ... },
    "zona_3_form_xobject": { ... },
    "zona_4_acroform": { ... },
    "resumen_general": { ... },
    "xml_estructura": { ... }
  },
  "reporte_texto": "Reporte legible del análisis...",
  "xml_estructura": { ... },
  "resumen": {
    "probabilidad_superposicion": 0.75,
    "nivel_riesgo": "HIGH",
    "zonas_analizadas": 4,
    "zonas_con_superposicion": 2,
    "total_anotaciones": 3,
    "streams_contenido": 2,
    "form_xobjects": 0,
    "campos_formulario": 1,
    "recomendaciones": ["Alto riesgo de texto superpuesto detectado"]
  }
}
```

### GET `/detectar-texto-superpuesto/info`
**Información detallada sobre el endpoint**

### GET `/detectar-texto-superpuesto/ejemplo`
**Ejemplos de uso con curl y Python**

## 🔬 Análisis Avanzado de Overlay

El sistema ahora incluye un **análisis avanzado** que combina múltiples técnicas:

### **Técnicas Utilizadas:**
- **Render Diff**: Compara la imagen renderizada con/sin anotaciones
- **IoU Calculation**: Calcula Intersection over Union para detectar superposiciones precisas
- **Stream Analysis**: Analiza el contenido del PDF en busca de patrones sospechosos
- **Elementos Sospechosos**: Detecta imágenes y figuras que tapan texto
- **Búsqueda de Texto**: Busca texto específico en el contenido del stream

### **Respuesta del Análisis Avanzado:**
```json
{
  "analisis_avanzado_overlay": {
    "total_paginas_analizadas": 1,
    "total_anotaciones": 2,
    "total_elementos_sospechosos": 1,
    "paginas_con_render_diff": 1,
    "probabilidad_overlay": 0.85,
    "nivel_riesgo": "HIGH",
    "indicadores_clave": {
      "tiene_anotaciones": true,
      "tiene_elementos_sospechosos": true,
      "tiene_diferencia_visual": true,
      "overlay_detectado": true
    },
    "detalles_por_pagina": [...]
  }
}
```

### **Respuesta del Análisis por Stream (MÁS PRECISO):**
```json
{
  "analisis_por_stream": {
    "total_paginas_analizadas": 1,
    "total_streams": 3,
    "streams_sospechosos": 1,
    "paginas_con_overlay": 1,
    "probabilidad_overlay": 0.95,
    "nivel_riesgo": "HIGH",
    "threshold_pixels": 0.01,
    "indicadores_clave": {
      "overlay_detectado": true,
      "tiene_streams_sospechosos": true,
      "metodo_mas_preciso": true
    },
    "detalles_por_pagina": [
      {
        "page": 1,
        "streams": 3,
        "overlay_stream": 2,
        "overlay_ratio": 0.15,
        "overlay_ratio_formatted": ">15.00%",
        "stream_preview": "100 600 200 30 re\n1 1 1 rg\nf\nBT\n/F1 12 Tf\n100 610 Td\n(Texto superpuesto: 999.99) Tj\nET",
        "detected": true
      }
    ]
  }
}
```

## 📊 Niveles de Riesgo

- **LOW**: Probabilidad < 40% - Bajo riesgo de superposición
- **MEDIUM**: Probabilidad 40-70% - Riesgo medio de superposición  
- **HIGH**: Probabilidad > 70% - Alto riesgo de superposición

> **Nota**: El análisis por stream es el método más preciso y puede detectar overlays que otros métodos no encuentran. Combina 6 técnicas diferentes para máxima precisión.

## 💻 Ejemplos de Uso

### Python
```python
import requests
import base64

# Leer PDF y codificar
with open("documento.pdf", "rb") as f:
    pdf_base64 = base64.b64encode(f.read()).decode()

# Enviar solicitud
response = requests.post(
    "http://localhost:8001/detectar-texto-superpuesto",
    json={
        "pdfbase64": pdf_base64,
        "incluir_reporte": True,
        "incluir_xml": True
    }
)

# Procesar respuesta
if response.status_code == 200:
    data = response.json()
    print(f"Probabilidad: {data['resumen']['probabilidad_superposicion']:.1%}")
    print(f"Riesgo: {data['resumen']['nivel_riesgo']}")
    print(f"Reporte: {data['reporte_texto']}")
```

### cURL
```bash
curl -X POST "http://localhost:8001/detectar-texto-superpuesto" \
  -H "Content-Type: application/json" \
  -d '{
    "pdfbase64": "JVBERi0xLjQKJcfsj6IK...",
    "incluir_reporte": true,
    "incluir_xml": true
  }'
```

## 🔧 Pruebas

Ejecutar el script de prueba:
```bash
python test_deteccion_texto.py
```

El script incluye:
- ✅ Prueba del endpoint principal
- ✅ Prueba del endpoint de información  
- ✅ Prueba del endpoint de ejemplo
- ✅ Prueba con diferentes tipos de PDF

## 📋 Detalles Técnicos

### Análisis de Anotaciones
- Detecta anotaciones superpuestas con contenido de página
- Clasifica por tipo (FreeText, Square, Stamp, etc.)
- Analiza appearance streams para contenido visual

### Análisis de Contenido
- Identifica múltiples streams de contenido
- Detecta comandos de texto y rectángulos
- Encuentra secuencias sospechosas (rectángulo blanco + texto)

### Análisis de XObjects
- Busca Form XObjects en recursos
- Detecta XObjects de texto
- Identifica XObjects sospechosos

### Análisis de AcroForm
- Verifica presencia de campos de formulario
- Analiza campos de texto específicamente
- Detecta campos superpuestos

## ⚠️ Limitaciones

- El análisis puede tomar varios segundos para PDFs grandes
- Algunas técnicas avanzadas de superposición pueden no detectarse
- La detección se basa en patrones conocidos y heurísticas

## 🎯 Casos de Uso

1. **Análisis forense** de documentos PDF
2. **Detección de manipulación** en facturas
3. **Validación de integridad** de documentos
4. **Auditoría de documentos** empresariales
5. **Investigación de fraudes** documentales

## 📚 Referencias

- [PDF Specification 1.7](https://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/pdf_reference_1-7.pdf)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
