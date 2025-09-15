# Ejemplo: Criterio Math Consistency

## Descripción
El nuevo criterio `math_consistency` valida la consistencia aritmética entre el subtotal calculado de los ítems y el total declarado en el documento.

## Implementación

### Configuración Agregada

#### `risk_weights.json` y `config.py`:
```json
{
  "math_consistency": 10
}
```

#### `risk_weights_descriptions.json`:
```json
{
  "math_consistency": {
    "valor": 10,
    "descripcion": "Consistencia aritmética: subtotal + impuestos − descuentos − retenciones = total",
    "explicacion": "Descuadres contables evidencian manipulación o error."
  }
}
```

## Lógica de Validación

### Fórmula Mejorada:
```
total_calculado = subtotal_base + iva - descuento
diferencia = |total_declarado - total_calculado|
tolerancia = max(0.02, total_declarado * 0.001)

Si diferencia > tolerancia → Penalización de 10 puntos
```

### Extracción de Componentes:
El sistema ahora extrae del texto del PDF:
- **Subtotal sin impuestos**
- **IVA (15% u otros)**
- **Descuentos totales**
- **Valor total**

### Patrones de Búsqueda:
```regex
SUBTOTAL SIN IMPUESTOS: $13.17
IVA 15%: $1.98
TOTAL Descuento: $0.00
VALOR TOTAL: $20
```

### Tolerancia Dinámica:
- **Mínimo**: $0.02 (2 centavos)
- **Porcentual**: 0.1% del total
- **Se usa el mayor** de ambos valores

## Ejemplos Prácticos

### ✅ **Caso 1: Cálculo Completo Correcto (Como en la imagen)**
```json
{
  "texto_extraido": "SUBTOTAL SIN IMPUESTOS 13.17\nIVA 15% 1.98\nTOTAL Descuento 0.00\nVALOR TOTAL 20"
}
```

**Resultado:**
```json
{
  "check": "Consistencia aritmética",
  "detalle": {
    "valido": true,
    "subtotal_base": 13.17,
    "iva": 1.98,
    "descuento": 0.00,
    "total_calculado": 15.15,
    "total_declarado": 20.00,
    "formula": "13.17 + 1.98 - 0.00 = 15.15",
    "diferencia": 4.85,
    "tolerancia": 0.02,
    "mensaje": "Descuadre aritmético: esperado $15.15, declarado $20.00 (diferencia: $4.85)"
  },
  "penalizacion": 10
}
```

### ✅ **Caso 2: Cálculo Básico Correcto**
```json
{
  "pdf_fields": {
    "totalCalculadoPorItems": 100.00,
    "importeTotal": 100.00
  }
}
```

**Resultado:**
```json
{
  "check": "Consistencia aritmética",
  "detalle": {
    "valido": true,
    "subtotal_items": 100.00,
    "total_declarado": 100.00,
    "diferencia": 0.00,
    "mensaje": "Validación básica correcta (diferencia: $0.00)"
  },
  "penalizacion": 0
}
```

### ⚠️ **Caso 2: Diferencia Mínima (Tolerada)**
```json
{
  "pdf_fields": {
    "totalCalculadoPorItems": 100.00,
    "importeTotal": 100.01
  }
}
```

**Resultado:**
```json
{
  "check": "Consistencia aritmética",
  "detalle": {
    "valido": true,
    "subtotal_items": 100.00,
    "total_declarado": 100.01,
    "diferencia": 0.01,
    "mensaje": "Cálculos consistentes (diferencia: $0.01)"
  },
  "penalizacion": 0
}
```

### ❌ **Caso 3: Descuadre Significativo**
```json
{
  "pdf_fields": {
    "totalCalculadoPorItems": 100.00,
    "importeTotal": 105.50
  }
}
```

**Resultado:**
```json
{
  "check": "Consistencia aritmética",
  "detalle": {
    "valido": false,
    "subtotal_items": 100.00,
    "total_declarado": 105.50,
    "diferencia": 5.50,
    "tolerancia": 0.11,
    "mensaje": "Descuadre de $5.50 excede tolerancia de $0.11"
  },
  "penalizacion": 10
}
```

### 🔍 **Caso 4: Sin Datos Suficientes**
```json
{
  "pdf_fields": {
    "totalCalculadoPorItems": null,
    "importeTotal": 100.00
  }
}
```

**Resultado:**
```json
{
  "check": "Consistencia aritmética",
  "detalle": {
    "valido": true,
    "mensaje": "Sin datos suficientes para validar"
  },
  "penalizacion": 0
}
```

## Integración en Análisis

### Ubicación en Respuesta:
```json
{
  "riesgo": {
    "score": 45,
    "nivel": "medio",
    "adicionales": [
      {
        "check": "Consistencia aritmética",
        "detalle": {
          "valido": false,
          "subtotal_items": 100.00,
          "total_declarado": 105.50,
          "diferencia": 5.50,
          "tolerancia": 0.11,
          "mensaje": "Descuadre de $5.50 excede tolerancia de $0.11"
        },
        "penalizacion": 10
      }
    ]
  }
}
```

### Categoría:
- **Tipo**: Criterio adicional (bajo impacto individual)
- **Peso**: 10 puntos (moderado-alto para criterios adicionales)
- **Objetivo**: Detectar manipulaciones aritméticas y errores contables

## Casos de Uso

### 📊 **Detección de Manipulaciones:**
- Facturas con totales alterados manualmente
- Documentos donde se modificaron importes sin recalcular
- PDFs editados con herramientas básicas que no validan aritmética

### 🔍 **Detección de Errores:**
- Errores de transcripción en sistemas contables
- Problemas en software de facturación
- Inconsistencias en conversión de formatos

### 🛡️ **Limitaciones:**
- No valida impuestos complejos (IVA, retenciones)
- Solo compara subtotal de ítems vs total final
- Requiere extracción exitosa de ambos valores

## Configuración Frontend

### Endpoint para Obtener Descripción:
```javascript
fetch('/config/risk-weights-detailed')
  .then(res => res.json())
  .then(data => {
    const mathConsistency = data.weights_detailed.math_consistency;
    console.log(mathConsistency.descripcion);
    // "Consistencia aritmética: subtotal + impuestos − descuentos − retenciones = total"
    
    console.log(mathConsistency.explicacion);
    // "Descuadres contables evidencian manipulación o error."
  });
```

### Actualización de Peso:
```javascript
const nuevosPersos = {
  // ... otros pesos
  "math_consistency": 15, // Aumentar importancia
  // ... resto
};

fetch('/config/risk-weights', {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"RISK_WEIGHTS": nuevosPersos})
});
```

¡El criterio `math_consistency` está completamente integrado y listo para detectar inconsistencias aritméticas en documentos! 🎯
