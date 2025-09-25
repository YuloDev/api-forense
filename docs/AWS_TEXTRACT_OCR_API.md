# API AWS Textract OCR

Este endpoint utiliza AWS Textract para realizar OCR (Reconocimiento Óptico de Caracteres) en documentos.

## 🚀 Endpoints Disponibles

### 1. OCR con AWS Textract
```
POST /aws-textract-ocr
```

### 2. Health Check
```
GET /aws-textract-ocr/health
```

## 📝 Modelos de Datos

### Petición (PeticionTextract)
```python
{
    "documentobase64": "string",           # Documento en base64 (requerido)
    "tipo_analisis": "string",             # Tipo de análisis (opcional, default: DETECT_DOCUMENT_TEXT)
    "features": ["string"]                 # Features para ANALYZE_DOCUMENT (opcional)
}
```

### Respuesta (RespuestaTextract)
```python
{
    "texto_extraido": "string",            # Texto extraído del documento
    "confianza_promedio": 0.0,             # Confianza promedio (0-100)
    "total_bloques": 0,                    # Total de bloques detectados
    "metadata": {},                        # Información adicional
    "mensaje": "string"                    # Mensaje descriptivo
}
```

## 🎛️ Tipos de Análisis

### 1. DETECT_DOCUMENT_TEXT
- **Descripción**: Extracción básica de texto
- **Uso**: Para documentos simples con solo texto
- **Ventajas**: Más rápido y económico

### 2. ANALYZE_DOCUMENT
- **Descripción**: Análisis avanzado con extracción de estructuras
- **Uso**: Para documentos complejos con tablas, formularios
- **Features disponibles**:
  - `TABLES`: Extrae información de tablas
  - `FORMS`: Extrae campos de formularios
  - `SIGNATURES`: Detecta firmas
  - `LAYOUT`: Analiza diseño del documento

## 📄 Tipos de Documentos Soportados

- **PDF**: Documentos PDF
- **JPEG**: Imágenes JPEG
- **PNG**: Imágenes PNG
- **GIF**: Imágenes GIF
- **BMP**: Imágenes BMP
- **WEBP**: Imágenes WebP

## 🔧 Configuración AWS

### Variables de Entorno
```bash
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_DEFAULT_REGION=us-east-1
```

### IAM Permissions
El usuario/rol necesita los siguientes permisos:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "textract:DetectDocumentText",
                "textract:AnalyzeDocument"
            ],
            "Resource": "*"
        }
    ]
}
```

## 📋 Ejemplos de Uso

### 1. OCR Básico con DETECT_DOCUMENT_TEXT

#### Petición:
```json
{
    "documentobase64": "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4K...",
    "tipo_analisis": "DETECT_DOCUMENT_TEXT"
}
```

#### Respuesta:
```json
{
    "texto_extraido": "FACTURA\nEmpresa XYZ S.A.\nRUC: 1234567890\nFecha: 2024-01-15\nTotal: $150.00",
    "confianza_promedio": 98.5,
    "total_bloques": 25,
    "metadata": {
        "total_bloques": 25,
        "bloques_por_tipo": {
            "PAGE": 1,
            "LINE": 5,
            "WORD": 19
        },
        "documentos_detectados": 1,
        "confianza_minima": 95.2,
        "confianza_maxima": 99.8,
        "lineas_texto": 5,
        "tipo_documento": "PDF",
        "tamaño_bytes": 245760,
        "tipo_analisis": "DETECT_DOCUMENT_TEXT"
    },
    "mensaje": "OCR completado con AWS Textract. 85 caracteres extraídos con confianza promedio de 98.5%"
}
```

### 2. Análisis Avanzado con ANALYZE_DOCUMENT

#### Petición:
```json
{
    "documentobase64": "JVBERi0xLjQKMSAwIG9iago8LAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4K...",
    "tipo_analisis": "ANALYZE_DOCUMENT",
    "features": ["TABLES", "FORMS"]
}
```

#### Respuesta:
```json
{
    "texto_extraido": "FORMULARIO DE SOLICITUD\nNombre: Juan Pérez\nCédula: 1234567890\n\nProducto | Cantidad | Precio\nLaptop   | 1        | $800.00\nMouse    | 2        | $25.00\nTotal:             | $850.00",
    "confianza_promedio": 97.2,
    "total_bloques": 45,
    "metadata": {
        "total_bloques": 45,
        "bloques_por_tipo": {
            "PAGE": 1,
            "LINE": 8,
            "WORD": 24,
            "TABLE": 1,
            "CELL": 9,
            "KEY_VALUE_SET": 3
        },
        "documentos_detectados": 1,
        "confianza_minima": 93.1,
        "confianza_maxima": 99.9,
        "lineas_texto": 8,
        "tablas": [
            {
                "id": "table-1",
                "confianza": 98.5,
                "filas": 3,
                "columnas": 3
            }
        ],
        "campos_formulario": [
            {
                "id": "key-1",
                "texto": "Nombre:",
                "confianza": 99.1
            },
            {
                "id": "key-2", 
                "texto": "Cédula:",
                "confianza": 98.7
            }
        ],
        "total_tablas": 1,
        "total_campos": 2,
        "tipo_documento": "PDF",
        "tamaño_bytes": 189432,
        "tipo_analisis": "ANALYZE_DOCUMENT"
    },
    "mensaje": "OCR completado con AWS Textract. 165 caracteres extraídos con confianza promedio de 97.2%"
}
```

### 3. Health Check

#### Petición:
```bash
GET /aws-textract-ocr/health
```

#### Respuesta (Exitosa):
```json
{
    "status": "ok",
    "servicio": "AWS Textract",
    "region": "us-east-1",
    "mensaje": "Conexión AWS Textract funcionando correctamente"
}
```

#### Respuesta (Error):
```json
{
    "detail": "AWS Textract no disponible: Unable to locate credentials"
}
```

## 🚨 Códigos de Error

### 400 - Bad Request
- Base64 inválido
- Tipo de análisis inválido
- Error en parámetros de AWS

### 413 - Payload Too Large
- Documento excede el tamaño máximo

### 500 - Internal Server Error
- Error de configuración AWS
- Error inesperado de Textract

### 503 - Service Unavailable
- AWS Textract no disponible

## 💡 Consejos de Uso

1. **Calidad de Imagen**: Para mejores resultados, usa imágenes con:
   - Alta resolución (mínimo 150 DPI)
   - Buen contraste
   - Texto horizontal

2. **Tipo de Análisis**: 
   - Usa `DETECT_DOCUMENT_TEXT` para documentos simples
   - Usa `ANALYZE_DOCUMENT` solo cuando necesites tablas/formularios

3. **Costos**: AWS Textract cobra por página:
   - DETECT_DOCUMENT_TEXT: ~$0.0015 por página
   - ANALYZE_DOCUMENT: ~$0.05 por página

4. **Límites**:
   - Tamaño máximo: 10 MB
   - Páginas simultáneas: limitado por AWS

## 🔍 Ejemplos con cURL

### OCR Básico:
```bash
curl -X POST "http://localhost:8000/aws-textract-ocr" \
     -H "Content-Type: application/json" \
     -d '{
       "documentobase64": "JVBERi0xLjQK...",
       "tipo_analisis": "DETECT_DOCUMENT_TEXT"
     }'
```

### Análisis Avanzado:
```bash
curl -X POST "http://localhost:8000/aws-textract-ocr" \
     -H "Content-Type: application/json" \
     -d '{
       "documentobase64": "JVBERi0xLjQK...",
       "tipo_analisis": "ANALYZE_DOCUMENT",
       "features": ["TABLES", "FORMS"]
     }'
```

### Health Check:
```bash
curl -X GET "http://localhost:8000/aws-textract-ocr/health"
```
