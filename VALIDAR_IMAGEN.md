# Endpoint Validar Imagen

## Descripción

El endpoint `/validar-imagen` está diseñado para analizar imágenes de facturas y documentos fiscales utilizando análisis forense avanzado. Proporciona la misma estructura de respuesta que el endpoint `validar-factura` pero enfocado específicamente en imágenes.

## Características

- ✅ **Soporte para múltiples formatos de imagen**: PNG, JPEG, JPG, TIFF, BMP, WEBP
- ✅ **OCR integrado**: Extracción de texto usando Tesseract
- ✅ **Análisis forense completo**: Metadatos, capas, superposición de texto
- ✅ **Detección de manipulación**: ELA, doble compresión, análisis de ruido
- ✅ **Checks específicos para imágenes**: Similar a los checks de PDF
- ✅ **Evaluación de riesgo**: Basada en múltiples indicadores forenses

## Endpoint

```
POST /validar-imagen
```

## Parámetros de Entrada

```json
{
  "imagen_base64": "string"  // Imagen codificada en base64
}
```

## Respuesta

### Estructura Principal

```json
{
  "sri_verificado": false,
  "mensaje": "Análisis forense de imagen PNG completado. No se puede validar con SRI (solo PDFs).",
  "tipo_archivo": "PNG",
  "coincidencia": "no",
  "diferencias": {},
  "diferenciasProductos": [],
  "resumenProductos": {
    "num_sri": 0,
    "num_imagen": 3,
    "total_sri_items": 0,
    "total_imagen_items": 150.00
  },
  "factura": {
    "ruc": "1234567890123",
    "razonSocial": "Empresa de Prueba",
    "fechaEmision": "01/01/2024",
    "importeTotal": 100.00,
    "claveAcceso": "1234567890123456789012345678901234567890123456789",
    "detalles": [
      {
        "cantidad": 2,
        "descripcion": "Producto A",
        "precioTotal": 50.00
      }
    ]
  },
  "riesgo": {
    "nivel": "MEDIO",
    "puntuacion": 45,
    "indicadores": [
      "Poco o ningún texto extraído de la imagen",
      "No se encontró clave de acceso válida"
    ],
    "probabilidad_manipulacion": 0.45,
    "analisis_forense": { ... },
    "campos_faltantes": ["claveAcceso"],
    "texto_extraido": 120
  },
  "validacion_firmas": {
    "resumen": {
      "total_firmas": 0,
      "firmas_validas": 0,
      "firmas_invalidas": 0,
      "con_certificados": 0,
      "con_timestamps": 0,
      "con_politicas": 0,
      "porcentaje_validas": 0
    },
    "dependencias": {
      "asn1crypto": false,
      "oscrypto": false,
      "certvalidator": false
    },
    "analisis_sri": {
      "es_documento_sri": false,
      "ruc_emisor": null,
      "razon_social": null,
      "numero_documento": null,
      "fecha_emision": null,
      "clave_acceso": null,
      "ambiente": null,
      "tipo_emision": null
    },
    "validacion_pdf": {
      "firma_detectada": false,
      "tipo_firma": "ninguna",
      "es_pades": false,
      "metadatos": {
        "numero_firmas": 0
      }
    },
    "tipo_documento": "png",
    "firma_detectada": false
  },
  "analisis_detallado": { ... },
  "checks_imagen": [
    {
      "check": "JavaScript embebido",
      "detalle": false,
      "penalizacion": 0
    },
    {
      "check": "Metadatos sospechosos",
      "detalle": true,
      "penalizacion": 15
    },
    {
      "check": "Texto superpuesto",
      "detalle": false,
      "penalizacion": 0
    },
    {
      "check": "Capas ocultas",
      "detalle": true,
      "penalizacion": 15
    },
    {
      "check": "Evidencias forenses de manipulación",
      "detalle": false,
      "penalizacion": 0
    },
    {
      "check": "Análisis ELA sospechoso",
      "detalle": true,
      "penalizacion": 20
    },
    {
      "check": "Doble compresión detectada",
      "detalle": false,
      "penalizacion": 0
    },
    {
      "check": "Inconsistencias en ruido y bordes",
      "detalle": false,
      "penalizacion": 0
    },
    {
      "check": "Análisis perceptual hash sospechoso",
      "detalle": false,
      "penalizacion": 0
    },
    {
      "check": "Análisis SSIM regional sospechoso",
      "detalle": false,
      "penalizacion": 0
    }
  ],
  "texto_extraido": "FACTURA\nRUC: 1234567890123\n..."
}
```

## Checks Específicos para Imágenes

El endpoint incluye 10 checks específicos para análisis de imágenes:

### 1. JavaScript embebido
- **Descripción**: No aplica para imágenes
- **Penalización**: 0 (siempre)

### 2. Metadatos sospechosos
- **Descripción**: Detecta metadatos EXIF/IPTC/XMP sospechosos
- **Penalización**: 15 puntos si se detecta

### 3. Texto superpuesto
- **Descripción**: Detecta texto superpuesto en la imagen
- **Penalización**: 20 puntos si se detecta

### 4. Capas ocultas
- **Descripción**: Detecta capas ocultas en formatos que las soportan
- **Penalización**: 15 puntos si se detecta

### 5. Evidencias forenses de manipulación
- **Descripción**: Detecta evidencias generales de manipulación
- **Penalización**: 25 puntos si se detecta

### 6. Análisis ELA sospechoso
- **Descripción**: Error Level Analysis para detectar recompresión
- **Penalización**: 20 puntos si se detecta

### 7. Doble compresión detectada
- **Descripción**: Detecta si la imagen fue comprimida múltiples veces
- **Penalización**: 15 puntos si se detecta

### 8. Inconsistencias en ruido y bordes
- **Descripción**: Detecta inconsistencias en patrones de ruido
- **Penalización**: 18 puntos si se detecta

### 9. Análisis perceptual hash sospechoso
- **Descripción**: Detecta diferencias locales usando pHash
- **Penalización**: 12 puntos si se detecta

### 10. Análisis SSIM regional sospechoso
- **Descripción**: Detecta inconsistencias usando SSIM regional
- **Penalización**: 10 puntos si se detecta

## Niveles de Riesgo

- **ALTO**: Puntuación ≥ 80
- **MEDIO**: Puntuación 50-79
- **BAJO**: Puntuación < 50

## Campos Extraídos

El endpoint extrae automáticamente los siguientes campos de la imagen:

- **RUC**: Número de RUC del emisor
- **Razón Social**: Nombre de la empresa
- **Fecha de Emisión**: Fecha del documento
- **Importe Total**: Valor total de la factura
- **Clave de Acceso**: Clave de acceso del SRI
- **Detalles**: Lista de productos/servicios

## Dependencias

- **pytesseract**: Para OCR
- **PIL/Pillow**: Para procesamiento de imágenes
- **opencv-python**: Para análisis de imágenes
- **scikit-image**: Para análisis forense
- **imagehash**: Para análisis perceptual

## Ejemplo de Uso

```python
import requests
import base64

# Leer imagen
with open("factura.png", "rb") as f:
    imagen_bytes = f.read()
    imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')

# Enviar petición
response = requests.post(
    "http://127.0.0.1:8001/validar-imagen",
    json={"imagen_base64": imagen_base64}
)

result = response.json()
print(f"Nivel de riesgo: {result['riesgo']['nivel']}")
print(f"Puntuación: {result['riesgo']['puntuacion']}")
```

## Limitaciones

- No se puede validar con SRI (solo PDFs)
- Requiere OCR para extraer texto
- La precisión depende de la calidad de la imagen
- No detecta firmas digitales (solo en PDFs)

## Diferencias con validar-factura

| Característica | validar-factura | validar-imagen |
|----------------|-----------------|----------------|
| Tipo de archivo | Solo PDF | Solo imágenes |
| Validación SRI | ✅ Sí | ❌ No |
| OCR | Solo si es escaneado | ✅ Siempre |
| Análisis forense | Básico | ✅ Completo |
| Checks específicos | PDF | Imagen |
| Firmas digitales | ✅ Sí | ❌ No |
