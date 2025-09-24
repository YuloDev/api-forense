# Parser Avanzado de Facturas SRI

## Descripción

Se ha implementado un parser avanzado de facturas SRI que integra análisis OCR, decodificación de códigos QR/barras, y validaciones financieras en el endpoint `validar-imagen`. Esta funcionalidad permite extraer información detallada de facturas capturadas como imágenes.

## Características Principales

### 🔍 **Extracción Avanzada de Datos**
- **OCR Robusto**: Reconocimiento óptico de caracteres con múltiples mejoras:
  - **Aplanado de Transparencia**: Convierte PNG RGBA a fondo blanco
  - **Escalado Inteligente**: Aumenta resolución 2.5x para mejor reconocimiento
  - **Múltiples Configuraciones**: Prueba diferentes PSM/OEM de Tesseract
  - **Binarización Adaptativa**: Usa umbrales Otsu y adaptativos
  - **Fallback EasyOCR**: Si Tesseract falla, usa EasyOCR como respaldo
- **Códigos QR/Barras**: Decodificación automática de códigos de barras y QR
- **Metadatos Técnicos**: Extracción de dimensiones, DPI, formato, y hash SHA256
- **Campos de Factura**: RUC, razón social, fecha de emisión, totales, clave de acceso

### 💰 **Validaciones Financieras**
- **Suma de Ítems vs Subtotal**: Verifica que la suma de ítems coincida con el subtotal sin impuestos
- **Total Recompuesto vs Declarado**: Valida que el total calculado coincida con el total declarado
- **Cálculo de Impuestos**: Verifica aplicación correcta de IVA 15% y otros impuestos
- **Descuentos**: Valida aplicación correcta de descuentos

### 🎯 **Detección de Manipulación**
- **Inconsistencias Financieras**: Detecta discrepancias en cálculos matemáticos
- **Análisis de Patrones**: Identifica patrones sospechosos en la estructura de la factura
- **Validación de Coherencia**: Verifica coherencia entre diferentes campos de la factura

## Estructura de Respuesta

### **Parser Avanzado**
```json
{
  "parser_avanzado": {
    "disponible": true,
    "barcodes_detectados": 2,
    "items_detectados": 5,
    "validaciones_financieras": {
      "sum_items": 150.00,
      "items_vs_subtotal_sin_impuestos": true,
      "recomputed_total": 172.50,
      "recomputed_total_vs_total": true
    },
    "metadatos_avanzados": {
      "ruc": "1234567890001",
      "invoice_number": "001-001-000123456",
      "authorization": "1234567890123456789012345678901234567890123456789",
      "environment": "PRODUCCION",
      "buyer_id": "0987654321",
      "emitter_name": "FARMACIAS FYBECA",
      "file_metadata": {
        "sha256": "abc123...",
        "width": 800,
        "height": 1200,
        "dpi": [300, 300],
        "mode": "RGB",
        "format": "PNG"
      }
    }
  }
}
```

### **Validaciones Financieras**
```json
{
  "financial_checks": {
    "sum_items": 150.00,
    "items_vs_subtotal_sin_impuestos": true,
    "recomputed_total": 172.50,
    "recomputed_total_vs_total": true
  }
}
```

### **Totales Detallados**
```json
{
  "totals": {
    "subtotal15": 100.00,
    "subtotal0": 50.00,
    "subtotal_no_objeto": 0.00,
    "subtotal_sin_impuestos": 150.00,
    "descuento": 0.00,
    "iva15": 15.00,
    "total": 172.50
  }
}
```

### **Ítems de Factura**
```json
{
  "detalles": [
    {
      "cantidad": 2,
      "descripcion": "Producto A",
      "precioTotal": 100.00
    },
    {
      "cantidad": 1,
      "descripcion": "Producto B",
      "precioTotal": 50.00
    }
  ]
}
```

## Checks de Riesgo Nuevos

### **🔴 Prioritarias**
1. **Inconsistencia financiera: ítems vs subtotal** (penalización: 25)
   - Detecta cuando la suma de ítems no coincide con el subtotal sin impuestos
   - Indica posible manipulación de totales

2. **Inconsistencia financiera: total recompuesto vs declarado** (penalización: 30)
   - Detecta cuando el total calculado no coincide con el total declarado
   - Indica manipulación financiera

## Dependencias Instaladas

```bash
pip install pytesseract pyzbar opencv-python-headless python-dateutil
pip install easyocr  # Opcional, para fallback
```

## Mejoras de OCR Implementadas

### **Problemas Resueltos**
1. **PNG RGBA con Transparencia**: El OCR fallaba con imágenes PNG que tenían canal alfa
2. **Baja Resolución**: Imágenes pequeñas (646×817) no se leían correctamente
3. **Configuración Tesseract**: Uso de configuraciones subóptimas de PSM/OEM

### **Soluciones Implementadas**

#### **1. Aplanado de Transparencia**
```python
def flatten_rgba_to_white(pil_img: Image.Image) -> Image.Image:
    if pil_img.mode == "RGBA":
        bg = Image.new("RGB", pil_img.size, (255, 255, 255))
        bg.paste(pil_img, mask=pil_img.split()[3])  # alpha
        return bg
```

#### **2. Escalado Inteligente**
```python
def enhance_for_ocr(pil_img: Image.Image, scale=2.5) -> Image.Image:
    base = flatten_rgba_to_white(pil_img)
    w, h = base.size
    base = base.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    # + contraste y unsharp
```

#### **3. Múltiples Configuraciones**
```python
confs = [
    "--oem 3 --psm 6 -c preserve_interword_spaces=1",
    "--oem 3 --psm 4 -c preserve_interword_spaces=1", 
    "--oem 3 --psm 11 -c preserve_interword_spaces=1",
]
```

#### **4. Binarización Adaptativa**
- **Umbral Otsu**: Para imágenes con buen contraste
- **Umbral Adaptativo**: Para imágenes con iluminación variable

#### **5. Fallback EasyOCR**
```python
def easyocr_text(pil_img: Image.Image) -> str:
    reader = easyocr.Reader(['es', 'en'], gpu=False)
    res = reader.readtext(np_img, detail=0, paragraph=True)
    return "\n".join(res)
```

### **Scripts de Diagnóstico**
- `diagnostico_ocr.py`: Verifica instalación de Tesseract y dependencias
- `test_ocr_mejorado.py`: Prueba las mejoras de OCR con diferentes tipos de imagen

## Uso

### **Endpoint**
```
POST /validar-imagen
```

### **Request**
```json
{
  "imagen_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

### **Response**
La respuesta incluye toda la información del parser avanzado en el campo `parser_avanzado`, además de las validaciones financieras integradas en los checks de riesgo.

## Patrones de Extracción

### **RUC**
- `RUC[:\s]*(\d{13})`
- `R\.U\.C[:\s]*(\d{13})`

### **Número de Factura**
- `(?:FACTURA)\s*(?:No\.?|N[°º])?\s*([0-9]{3}-[0-9]{3}-[0-9]{9})`

### **Clave de Acceso**
- `(?:N[ÚU]MERO\s+DE\s+AUTORIZACI[ÓO]N|CLAVE\s+DE\s+ACCESO)\s*[: ]*\s*([0-9]{10,50})`

### **Totales**
- `Subtotal\s*15%\s*[: ]\s*([0-9.,]+)`
- `Subtotal\s*0%\s*[: ]\s*([0-9.,]+)`
- `SUBTOTAL\s+SIN\s+IMPUESTOS\s*[: ]\s*([0-9.,]+)`
- `IVA\s*15%?\s*[: ]\s*([0-9.,]+)`
- `(?:VALOR\s+TOTAL|TOTAL\s*FACTURA)\s*[: ]\s*([0-9.,]+)`

## Fallback

Si el parser avanzado falla, el sistema automáticamente recurre al método de extracción básico anterior, asegurando que el endpoint siempre funcione.

## Beneficios

1. **Mayor Precisión**: Extracción más precisa de datos de facturas
2. **Validaciones Financieras**: Detección automática de inconsistencias matemáticas
3. **Análisis Forense**: Integración con análisis forense existente
4. **Flexibilidad**: Soporte para múltiples formatos de imagen
5. **Robustez**: Sistema de fallback para garantizar funcionamiento

## Limitaciones

- Requiere Tesseract instalado en el sistema
- El OCR puede variar en precisión según la calidad de la imagen
- Los patrones de extracción están optimizados para facturas SRI ecuatorianas
- Las validaciones financieras asumen formato estándar de factura

## Próximas Mejoras

- Soporte para más formatos de factura internacional
- Mejoras en la precisión del OCR
- Validaciones adicionales de coherencia
- Integración con más servicios de validación gubernamental
