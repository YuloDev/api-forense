# API de Pesos de Riesgo con Descripciones

## Descripción

Endpoints actualizados para gestionar los pesos de riesgo (`RISK_WEIGHTS`) ahora incluyen descripciones comprensibles para el usuario, manteniendo toda la funcionalidad existente.

## Nuevos Endpoints Disponibles

### 1. GET `/config/risk-weights` (ACTUALIZADO)
**Obtener pesos de riesgo CON descripciones**

```bash
curl -X GET "http://127.0.0.1:8005/config/risk-weights"
```

**Respuesta:**
```json
{
  "RISK_WEIGHTS": {
    "fecha_creacion_vs_emision": 15,
    "fecha_mod_vs_creacion": 12,
    "software_conocido": 12,
    "num_paginas": 10,
    "capas_multiples": 10,
    "consistencia_fuentes": 8,
    "dpi_uniforme": 8,
    "compresion_estandar": 6,
    "alineacion_texto": 6,
    "tamano_esperado": 6,
    "anotaciones_o_formularios": 3,
    "javascript_embebido": 2,
    "archivos_incrustados": 3,
    "firmas_pdf": -4,
    "actualizaciones_incrementales": 3,
    "cifrado_permisos_extra": 2
  },
  "RISK_WEIGHTS_DESCRIPTIONS": {
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
    // ... resto de descripciones
  }
}
```

### 2. GET `/config/risk-weights-descriptions` (NUEVO)
**Obtener solo las descripciones**

```bash
curl -X GET "http://127.0.0.1:8005/config/risk-weights-descriptions"
```

**Respuesta:**
```json
{
  "RISK_WEIGHTS_DESCRIPTIONS": {
    "fecha_creacion_vs_emision": {
      "valor": 15,
      "descripcion": "Diferencia entre la fecha de creación del PDF y la fecha de emisión del documento",
      "explicacion": "Un documento legítimo debería crearse cerca de su fecha de emisión. Diferencias grandes pueden indicar manipulación."
    },
    // ... resto de criterios
  }
}
```

### 3. GET `/config/risk-weights-detailed` (NUEVO)
**Formato optimizado para frontend**

```bash
curl -X GET "http://127.0.0.1:8005/config/risk-weights-detailed"
```

**Respuesta:**
```json
{
  "weights_detailed": {
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
    // ... resto de criterios
  },
  "total_criterios": 16,
  "peso_maximo_positivo": 15,
  "peso_maximo_negativo": -4
}
```

## Ejemplos de Integración Frontend

### JavaScript/React - Mostrar Lista de Criterios

```jsx
import React, { useState, useEffect } from 'react';

const RiskWeightsManager = () => {
  const [weightsData, setWeightsData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWeightsDetailed();
  }, []);

  const fetchWeightsDetailed = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8005/config/risk-weights-detailed');
      const data = await response.json();
      setWeightsData(data);
    } catch (error) {
      console.error('Error:', error);
    }
    setLoading(false);
  };

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="risk-weights-container">
      <h2>Criterios de Análisis de Riesgo</h2>
      <p>Total de criterios: {weightsData.total_criterios}</p>
      
      <div className="weights-grid">
        {Object.entries(weightsData.weights_detailed).map(([key, data]) => (
          <div key={key} className={`weight-item ${data.valor < 0 ? 'positive' : 'negative'}`}>
            <div className="weight-header">
              <h3>{data.descripcion}</h3>
              <span className="weight-value">
                {data.valor > 0 ? '+' : ''}{data.valor} puntos
              </span>
            </div>
            <p className="weight-explanation">{data.explicacion}</p>
            <div className="weight-key">
              <small>Criterio: {key}</small>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RiskWeightsManager;
```

### JavaScript - Actualizar Pesos (Funcionalidad existente)

```javascript
// La funcionalidad de actualización sigue igual
const updateWeights = async (newWeights) => {
  try {
    const response = await fetch('http://127.0.0.1:8005/config/risk-weights', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        "RISK_WEIGHTS": newWeights
      })
    });
    
    const data = await response.json();
    console.log(data.message);
    return data;
  } catch (error) {
    console.error('Error:', error);
  }
};

// Ejemplo de uso
const nuevosPersos = {
  "fecha_creacion_vs_emision": 20,  // Aumentar importancia
  "software_conocido": 15,
  // ... resto de pesos
};

updateWeights(nuevosPersos);
```

## Descripciones Disponibles

### Criterios Prioritarios (Alto Impacto)
- **fecha_creacion_vs_emision** (15 pts): Diferencia temporal entre creación y emisión
- **fecha_mod_vs_creacion** (12 pts): Modificaciones posteriores a la creación  
- **software_conocido** (12 pts): Uso de software confiable
- **num_paginas** (10 pts): Número de páginas esperado
- **capas_multiples** (10 pts): Presencia de capas OCG

### Criterios Secundarios (Impacto Medio)
- **consistencia_fuentes** (8 pts): Uniformidad tipográfica
- **dpi_uniforme** (8 pts): Consistencia en resolución de imágenes
- **compresion_estandar** (6 pts): Métodos de compresión normales
- **alineacion_texto** (6 pts): Alineación correcta de elementos
- **tamano_esperado** (6 pts): Tamaño de archivo apropiado

### Criterios Adicionales (Bajo Impacto)
- **anotaciones_o_formularios** (3 pts): Elementos interactivos
- **archivos_incrustados** (3 pts): Archivos adjuntos ocultos
- **actualizaciones_incrementales** (3 pts): Múltiples modificaciones
- **javascript_embebido** (2 pts): Código JavaScript
- **cifrado_permisos_extra** (2 pts): Restricciones especiales

### Criterios Positivos (Reducen Riesgo)
- **firmas_pdf** (-4 pts): Firmas digitales válidas

## Archivos de Configuración

### `risk_weights.json` (Existente)
```json
{
  "fecha_creacion_vs_emision": 15,
  "fecha_mod_vs_creacion": 12,
  // ... solo valores numéricos
}
```

### `risk_weights_descriptions.json` (Nuevo)
```json
{
  "fecha_creacion_vs_emision": {
    "valor": 15,
    "descripcion": "Diferencia entre la fecha de creación del PDF y la fecha de emisión del documento",
    "explicacion": "Un documento legítimo debería crearse cerca de su fecha de emisión..."
  }
  // ... descripciones completas
}
```

## Compatibilidad

✅ **Toda la funcionalidad existente se mantiene**
- Los endpoints originales funcionan igual
- La variable `RISK_WEIGHTS` no cambia
- El análisis de riesgo usa los mismos valores
- Los archivos de configuración legacy siguen siendo válidos

✅ **Nuevas funcionalidades agregadas**
- Descripciones comprensibles para usuarios
- Endpoints optimizados para frontend
- Información contextual sobre cada criterio
- Estadísticas adicionales (máximos, totales, etc.)

## URLs Completas

```javascript
const endpoints = {
  // Existentes (actualizados)
  weights: 'http://127.0.0.1:8005/config/risk-weights',
  updateWeights: 'http://127.0.0.1:8005/config/risk-weights',
  
  // Nuevos
  descriptions: 'http://127.0.0.1:8005/config/risk-weights-descriptions',
  detailed: 'http://127.0.0.1:8005/config/risk-weights-detailed'
};
```

¡Perfecto para crear interfaces de usuario más comprensibles y amigables! 🎯
