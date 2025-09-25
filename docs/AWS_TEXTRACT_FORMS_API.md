# 📋 API AWS Textract - Extracción de Formularios

Esta documentación explica cómo usar los endpoints específicos para extraer pares clave-valor de formularios con AWS Textract, similar al CSV que generas en la web de AWS.

## 🚀 Endpoints Disponibles

### 1. Extracción de Formularios (JSON)
```
POST /aws-textract-forms
```

### 2. Extracción de Formularios (CSV)
```
POST /aws-textract-forms-csv
```

### 3. OCR General (con soporte para formularios)
```
POST /aws-textract-ocr
```

---

## 📝 Modelos de Datos

### **PeticionTextract** (entrada)
```json
{
    "documentobase64": "string",
    "tipo_analisis": "ANALYZE_DOCUMENT",
    "features": ["FORMS"]
}
```

### **ParClaveValor** (elemento de respuesta)
```json
{
    "pagina": 1,
    "clave": "NOMBRE:",
    "valor": "Mia Martinez Vera",
    "confianza_clave": 61.99964142,
    "confianza_valor": 61.99964142,
    "key_id": "key-123",
    "value_id": "value-456",
    "selection_status": "NOT_SELECTED"
}
```

### **RespuestaFormularios** (respuesta JSON)
```json
{
    "total_pares": 150,
    "pares_clave_valor": [
        {
            "pagina": 1,
            "clave": "NOMBRE:",
            "valor": "Mia Martinez Vera",
            "confianza_clave": 61.99964142,
            "confianza_valor": 61.99964142,
            "key_id": "key-123",
            "value_id": "value-456",
            "selection_status": "NOT_SELECTED"
        }
    ],
    "confianza_promedio_claves": 85.5,
    "confianza_promedio_valores": 78.3,
    "tipo_documento": "PDF",
    "mensaje": "Se extrajeron 150 pares clave-valor del formulario..."
}
```

---

## 🎯 **Ejemplo 1: Endpoint JSON**

### **Petición:**
```bash
curl -X POST "http://localhost:8000/aws-textract-forms" \
     -H "Content-Type: application/json" \
     -d '{
       "documentobase64": "JVBERi0xLjQK..."
     }'
```

### **Respuesta:**
```json
{
    "total_pares": 416,
    "pares_clave_valor": [
        {
            "pagina": 1,
            "clave": "NOMBRE:",
            "valor": "Mia Martinez Vera",
            "confianza_clave": 61.99964142,
            "confianza_valor": 61.99964142,
            "key_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "value_id": "f9e8d7c6-b5a4-3210-9876-543210fedcba",
            "selection_status": "NOT_SELECTED"
        },
        {
            "pagina": 1,
            "clave": "FECHA:",
            "valor": "26/08/2025",
            "confianza_clave": 96.75117493,
            "confianza_valor": 96.75117493,
            "key_id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
            "value_id": "g8f7e6d5-c4b3-2109-8765-432109edcba9",
            "selection_status": "NOT_SELECTED"
        },
        {
            "pagina": 1,
            "clave": "BIOMETRÍA HEMÁTICA",
            "valor": "SELECTED",
            "confianza_clave": 96.07025146,
            "confianza_valor": 69.82421875,
            "key_id": "c3d4e5f6-g7h8-9012-cdef-345678901234",
            "value_id": "h7g6f5e4-d3c2-1098-7654-321098dcba87",
            "selection_status": "SELECTED"
        }
    ],
    "confianza_promedio_claves": 85.2,
    "confianza_promedio_valores": 78.8,
    "tipo_documento": "PDF",
    "mensaje": "Se extrajeron 416 pares clave-valor del formulario. Confianza promedio: claves 85.2%, valores 78.8%"
}
```

---

## 📄 **Ejemplo 2: Endpoint CSV**

### **Petición:**
```bash
curl -X POST "http://localhost:8000/aws-textract-forms-csv" \
     -H "Content-Type: application/json" \
     -d '{
       "documentobase64": "JVBERi0xLjQK..."
     }' \
     --output keyValues.csv
```

### **Respuesta CSV:**
```csv
'Page number,'Key,'Value,'Confidence Score % (Key),'Confidence Score % (Value)
"'1","'NOMBRE:","'Mia Martinez Vera","'61.99964142","'61.99964142"
"'1","'FECHA:","'26/08/2025","'96.75117493","'96.75117493"
"'1","'EDAD:","'6 años","'94.33649445","'94.33649445"
"'1","'BIOMETRÍA HEMÁTICA","'SELECTED","'96.07025146","'69.82421875"
"'1","'HEMATOCRITO","'SELECTED","'95.43112946","'52.19726563"
"'1","'HEMOGLOBINA","'NOT_SELECTED","'96.25675964","'68.65234375"
```

**El archivo se descarga automáticamente como `keyValues.csv`**

---

## 🔍 **Casos de Uso**

### **1. Formularios Médicos**
- Extraer datos de pacientes
- Procesar exámenes de laboratorio
- Identificar campos seleccionados/no seleccionados

### **2. Formularios Legales**
- Procesar contratos
- Extraer términos y condiciones
- Identificar firmas y campos obligatorios

### **3. Encuestas y Cuestionarios**
- Procesar respuestas de encuestas
- Extraer datos de evaluaciones
- Analizar patrones de respuesta

---

## 🎛️ **Campos Especiales**

### **selection_status**
- `"SELECTED"`: Checkbox marcado
- `"NOT_SELECTED"`: Checkbox no marcado
- `""`: Campo de texto normal

### **confianza_clave / confianza_valor**
- Rango: 0.0 - 100.0
- Valores altos (>90): Muy confiable
- Valores medios (70-90): Moderadamente confiable  
- Valores bajos (<70): Revisar manualmente

### **key_id / value_id**
- Identificadores únicos de AWS Textract
- Útiles para debugging y trazabilidad
- `value_id` puede ser `null` para checkboxes

---

## 💡 **Comparación con tu CSV Original**

| Campo CSV Original | Campo API | Descripción |
|-------------------|-----------|-------------|
| `Page number` | `pagina` | Número de página |
| `Key` | `clave` | Nombre del campo |
| `Value` | `valor` | Valor del campo |
| `Confidence Score % (Key)` | `confianza_clave` | Confianza de la clave |
| `Confidence Score % (Value)` | `confianza_valor` | Confianza del valor |

**✅ Formato idéntico**: El endpoint CSV genera exactamente el mismo formato que tu archivo original.

---

## 🚨 **Consideraciones Importantes**

### **1. Tipos de Documentos Soportados**
- ✅ PDF con formularios
- ✅ Imágenes de formularios (JPG, PNG)
- ✅ Documentos escaneados
- ❌ Documentos puramente textuales

### **2. Limitaciones**
- Máximo 10 MB por documento
- Funciona mejor con formularios estructurados
- Requiere campos claramente definidos

### **3. Costos AWS**
- ~$0.05 por página con ANALYZE_DOCUMENT + FORMS
- Más costoso que extracción básica de texto
- Ideal para casos de uso específicos

---

## 🔧 **Integración con tu Flujo de Trabajo**

### **1. Procesamiento Batch**
```python
import requests
import base64

def procesar_formularios(archivos_pdf):
    resultados = []
    
    for archivo in archivos_pdf:
        with open(archivo, 'rb') as f:
            pdf_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        response = requests.post('http://localhost:8000/aws-textract-forms', 
                               json={'documentobase64': pdf_b64})
        
        if response.status_code == 200:
            resultados.append(response.json())
    
    return resultados
```

### **2. Exportación a CSV**
```bash
# Directamente descargar CSV
curl -X POST "http://localhost:8000/aws-textract-forms-csv" \
     -H "Content-Type: application/json" \
     -d '{"documentobase64": "..."}' \
     --output resultado.csv
```

### **3. Filtrado de Resultados**
```python
def filtrar_campos_seleccionados(respuesta):
    """Obtener solo los campos marcados como SELECTED"""
    return [
        pair for pair in respuesta['pares_clave_valor'] 
        if pair['selection_status'] == 'SELECTED'
    ]

def filtrar_alta_confianza(respuesta, umbral=90):
    """Obtener solo campos con alta confianza"""
    return [
        pair for pair in respuesta['pares_clave_valor']
        if pair['confianza_clave'] >= umbral and pair['confianza_valor'] >= umbral
    ]
```

---

## 🎯 **Próximos Pasos**

1. **Probar con tu documento**: Usa el mismo documento que generó tu CSV
2. **Comparar resultados**: Verificar que los datos coincidan
3. **Integrar en tu flujo**: Usar el endpoint que mejor se adapte a tus necesidades
4. **Optimizar filtros**: Ajustar umbrales de confianza según tu caso de uso

¡El API está listo para reemplazar tu proceso manual de generación de CSV! 🚀
