# API de Gestión de Niveles de Riesgo

## Descripción

Nuevos endpoints para gestionar los rangos de puntuación que determinan los niveles de riesgo ("bajo", "medio", "alto") en el análisis forense de documentos.

## Endpoints Disponibles

### 1. GET `/risk-levels`
**Obtener configuración actual de niveles de riesgo**

```bash
curl -X GET "http://127.0.0.1:8005/risk-levels"
```

**Respuesta:**
```json
{
  "RISK_LEVELS": {
    "bajo": [0, 29],
    "medio": [30, 59], 
    "alto": [60, 100]
  },
  "descripcion": "Rangos de puntuación para clasificar el nivel de riesgo de documentos",
  "niveles_disponibles": ["bajo", "medio", "alto"]
}
```

### 2. PUT `/risk-levels`
**Actualizar rangos de niveles de riesgo**

```bash
curl -X PUT "http://127.0.0.1:8005/risk-levels" \
  -H "Content-Type: application/json" \
  -d '{
    "RISK_LEVELS": {
      "bajo": [0, 39],
      "medio": [40, 69],
      "alto": [70, 100]
    }
  }'
```

**Respuesta:**
```json
{
  "message": "Niveles de riesgo actualizados correctamente",
  "RISK_LEVELS": {
    "bajo": [0, 39],
    "medio": [40, 69],
    "alto": [70, 100]
  },
  "archivo_guardado": "risk_levels_config.json"
}
```

### 3. GET `/risk-levels/example`
**Obtener ejemplos de configuración para maquetado**

```bash
curl -X GET "http://127.0.0.1:8005/risk-levels/example"
```

**Respuesta:**
```json
{
  "ejemplo_configuracion_actual": {
    "descripcion": "Configuración actual de niveles de riesgo",
    "valores": {
      "bajo": [0, 29],
      "medio": [30, 59],
      "alto": [60, 100]
    }
  },
  "ejemplo_payload_actualizacion": {
    "descripcion": "Estructura para actualizar niveles de riesgo", 
    "endpoint": "PUT /risk-levels",
    "content_type": "application/json",
    "payload": {
      "RISK_LEVELS": {
        "bajo": [0, 29],
        "medio": [30, 59],
        "alto": [60, 100]
      }
    }
  },
  "ejemplo_payload_personalizado": {
    "descripcion": "Ejemplo de configuración personalizada",
    "payload": {
      "RISK_LEVELS": {
        "bajo": [0, 39],
        "medio": [40, 69], 
        "alto": [70, 100]
      }
    }
  },
  "ejemplo_respuesta_analisis": {
    "descripcion": "Cómo se usa en el análisis de documentos",
    "estructura": {
      "riesgo": {
        "score": 45,
        "nivel": "medio",
        "es_falso": true,
        "prioritarias": [],
        "secundarias": [],
        "adicionales": []
      }
    }
  },
  "validaciones": {
    "rangos_validos": "Valores entre 0 y 100",
    "no_solapamiento": "Los rangos no pueden solaparse", 
    "orden_requerido": "min < max para cada nivel",
    "niveles_obligatorios": ["bajo", "medio", "alto"]
  }
}
```

### 4. GET `/risk-levels/validate`
**Validar configuración actual**

```bash
curl -X GET "http://127.0.0.1:8005/risk-levels/validate"
```

**Respuesta:**
```json
{
  "es_valido": true,
  "errores": [],
  "advertencias": [],
  "configuracion_actual": {
    "bajo": [0, 29],
    "medio": [30, 59],
    "alto": [60, 100]
  }
}
```

### 5. POST `/risk-levels/reset`
**Restaurar a valores por defecto**

```bash
curl -X POST "http://127.0.0.1:8005/risk-levels/reset"
```

**Respuesta:**
```json
{
  "message": "Niveles de riesgo restaurados a valores por defecto",
  "RISK_LEVELS": {
    "bajo": [0, 29],
    "medio": [30, 59],
    "alto": [60, 100]
  },
  "archivo_eliminado": null
}
```

## Reglas de Validación

### Formato de Datos
- **Niveles obligatorios**: "bajo", "medio", "alto"
- **Formato de rango**: `[min, max]` donde ambos son enteros
- **Rango válido**: 0 ≤ min < max ≤ 100

### Validaciones Automáticas
1. **Sin solapamientos**: Los rangos no pueden superponerse
2. **Orden lógico**: min < max para cada nivel
3. **Cobertura**: Se recomienda cubrir todo el rango 0-100
4. **Consistencia**: Los niveles deben estar ordenados lógicamente

## Ejemplos de Configuraciones Válidas

### Configuración Conservadora
```json
{
  "RISK_LEVELS": {
    "bajo": [0, 39],
    "medio": [40, 69],
    "alto": [70, 100]
  }
}
```

### Configuración Estricta
```json
{
  "RISK_LEVELS": {
    "bajo": [0, 19],
    "medio": [20, 49],
    "alto": [50, 100]
  }
}
```

### Configuración Equilibrada
```json
{
  "RISK_LEVELS": {
    "bajo": [0, 33],
    "medio": [34, 66],
    "alto": [67, 100]
  }
}
```

## Casos de Error

### Error: Solapamiento de Rangos
```json
{
  "RISK_LEVELS": {
    "bajo": [0, 30],
    "medio": [25, 60],  // Error: solapa con "bajo"
    "alto": [61, 100]
  }
}
```

**Respuesta:**
```json
{
  "detail": "Los rangos de 'bajo' y 'medio' no pueden solaparse"
}
```

### Error: Rango Inválido
```json
{
  "RISK_LEVELS": {
    "bajo": [0, 29],
    "medio": [50, 40],  // Error: min > max
    "alto": [70, 100]
  }
}
```

**Respuesta:**
```json
{
  "detail": "El valor mínimo de 'medio' debe ser menor que el máximo"
}
```

### Error: Valores Fuera de Rango
```json
{
  "RISK_LEVELS": {
    "bajo": [-5, 29],   // Error: valor negativo
    "medio": [30, 59],
    "alto": [60, 150]   // Error: > 100
  }
}
```

**Respuesta:**
```json
{
  "detail": "Los valores de 'bajo' deben estar entre 0 y 100"
}
```

## Integración con el Análisis

Los niveles de riesgo configurados se usan automáticamente en:

1. **Endpoint `/validar-factura`**: Clasifica el score calculado
2. **Endpoint `/validar-documento`**: Determina el nivel de riesgo
3. **Campo `nivel`**: En la respuesta del análisis de riesgo

### Flujo de Clasificación
```
Score calculado: 45
↓
Comparar con RISK_LEVELS:
- bajo: [0, 29] → NO
- medio: [30, 59] → SÍ ✓
- alto: [60, 100] → NO
↓
Resultado: nivel = "medio"
```

## Persistencia

- **Archivo de configuración**: `risk_levels_config.json`
- **Carga automática**: Al reiniciar el servidor
- **Valores por defecto**: Si no existe configuración personalizada

## Compatibilidad

- **Endpoints existentes**: No se modifican
- **Configuración legacy**: Se mantiene compatible
- **API independiente**: Funciona sin afectar otros endpoints
