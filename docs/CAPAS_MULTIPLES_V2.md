# Sistema Modular de Detección de Capas Múltiples V2

## 🎯 Resumen del Upgrade

El sistema de detección de capas múltiples ha sido **completamente refactorizado** en un helper modular con sistema de pesos dinámicos mejorado. 

### 📈 Mejoras Implementadas

1. **🏗️ Arquitectura Modular**: Helper separado en `helpers/deteccion_capas.py`
2. **⚖️ Pesos Dinámicos**: Sistema de penalización proporcional al riesgo real  
3. **🔧 Componentes Especializados**: Análisis dividido en 4 módulos independientes
4. **📊 Múltiples Métodos**: Combinación de análisis proporcional y escalonado
5. **🎚️ Peso Base Recomendado**: 15 puntos (vs 5-10 anterior)

---

## 📁 Estructura del Sistema

### **Archivo Principal: `helpers/deteccion_capas.py`**

```
├── LayerPatterns          # Configuración de patrones de detección
├── RiskWeights           # Configuración de pesos y umbrales
├── OCGAnalyzer          # Análisis de Optional Content Groups
├── OverlayAnalyzer      # Análisis de objetos superpuestos
├── TextOverlapAnalyzer  # Análisis de superposición de texto
├── StructureAnalyzer    # Análisis de estructura PDF
├── RiskCalculator       # Cálculo de riesgo dinámico
└── LayerDetector        # Clase principal (orquestador)
```

### **Integración en `riesgo.py`**

- ✅ **Función refactorizada**: `_detect_layers_advanced()` usa el nuevo helper
- ✅ **Sistema de pesos mejorado**: Implementado en `evaluar_riesgo()`
- ✅ **Funciones de conveniencia**: `evaluar_capas_multiples_completo()`, `calcular_penalizacion_capas_optimizada()`
- ✅ **Compatibilidad total**: Mantiene la API existente

---

## 🔍 Análisis por Componentes

### **1. OCGAnalyzer (35% del peso)**
**Detecta**: Optional Content Groups oficiales del PDF
- Patrones: `/OCGs`, `/OCProperties`, `/ON [`, `/OFF [`
- **Confianza**:
  - 5+ objetos → 60-95%
  - 2-4 objetos → 40-70%  
  - 1 objeto → 20%

### **2. OverlayAnalyzer (25% del peso)**
**Detecta**: Objetos superpuestos y transparencias
- Patrones: `/Type /XObject`, `/Subtype /Form`, `/S /Transparency`
- Efectos: Blend modes, valores alpha, operadores gráficos
- **Score**: `min(1.0, overlay_count / 20.0)`

### **3. TextOverlapAnalyzer (25% del peso)**
**Detecta**: Superposición y duplicación de texto
- Líneas duplicadas exactas
- Líneas similares (70%+ coincidencia)
- Formato sospechoso (espaciado inusual, caracteres de control)
- **Probabilidad**: Calculada por evidencias acumuladas

### **4. StructureAnalyzer (15% del peso)**
**Detecta**: Anomalías en estructura PDF
- Exceso de objetos por página (>50)
- Bloques de texto superpuestos
- Operadores gráficos sospechosos
- **Score**: Basado en densidad de objetos

---

## ⚖️ Sistema de Pesos Dinámicos

### **Configuración Recomendada**
```python
# En risk_weights.json
"capas_multiples": 15  # Aumentado de 5-10 a 15
```

### **Métodos de Cálculo**

#### **Método 1: Proporcional**
```python
penalizacion = (probabilidad_porcentaje / 100) * peso_base
# Ejemplo: 39.5% × 15 = 5.9 puntos
```

#### **Método 2: Escalonado**
```python
multiplicadores = {
    "VERY_HIGH": 1.0,   # 80%+ → 15 puntos
    "HIGH": 0.8,        # 60-79% → 12 puntos  
    "MEDIUM": 0.6,      # 40-59% → 9 puntos
    "LOW": 0.4,         # 20-39% → 6 puntos
    "VERY_LOW": 0.2     # 0-19% → 3 puntos
}
```

#### **Método Final: Max de Ambos**
```python
penalizacion_final = max(proporcional, escalonado)
```

---

## 📊 Comparación de Resultados

### **Tu Ejemplo: 39.5% de Probabilidad**

| Sistema | Peso Base | Penalización | Método |
|---------|-----------|-------------|--------|
| **Anterior** | 10 pts | ~4 pts | Solo proporcional |
| **Nuevo V2** | 15 pts | **6 pts** | Max(proporcional, escalonado) |

### **Casos Extremos**

| Probabilidad | Nivel | Anterior | Nuevo V2 | Mejora |
|-------------|-------|----------|----------|--------|
| 15% | VERY_LOW | 1.5 pts | **3 pts** | +100% |
| 65% | HIGH | 6.5 pts | **12 pts** | +85% |
| 85% | VERY_HIGH | 8.5 pts | **15 pts** | +76% |

---

## 🚀 Uso del Nuevo Sistema

### **Análisis Básico**
```python
from helpers.deteccion_capas import LayerDetector

detector = LayerDetector(pdf_bytes, extracted_text, base_weight=15)
resultado = detector.analyze()

print(f"Probabilidad: {resultado['probability_percentage']:.1f}%")
print(f"Penalización: {resultado['penalty_points']} puntos")
print(f"Nivel: {resultado['risk_level']}")
```

### **Función Integrada**
```python
from riesgo import evaluar_capas_multiples_completo

resultado = evaluar_capas_multiples_completo(pdf_bytes, extracted_text)
# Resultado completo con configuración incluida
```

### **Cálculo de Penalización**
```python
from riesgo import calcular_penalizacion_capas_optimizada

penalizacion = calcular_penalizacion_capas_optimizada(39.5, "LOW", 15)
# {'penalty_points': 6, 'explanation': '...', 'calculation_breakdown': {...}}
```

---

## 🔧 Configuración Avanzada

### **Personalizar Pesos de Componentes**
```python
from helpers.deteccion_capas import RiskWeights

# Modificar pesos por componente
RiskWeights.COMPONENT_WEIGHTS = {
    "ocg_confidence": 0.40,      # Más peso a OCG
    "overlay_presence": 0.30,    # Más peso a overlays  
    "text_overlapping": 0.20,    # Menos peso a texto
    "structure_suspicious": 0.10 # Menos peso a estructura
}
```

### **Personalizar Umbrales**
```python
# Modificar umbrales de clasificación
RiskWeights.RISK_THRESHOLDS = {
    "VERY_HIGH": 0.75,   # Más estricto
    "HIGH": 0.55,        
    "MEDIUM": 0.35,      
    "LOW": 0.15,         
    "VERY_LOW": 0.0      
}
```

---

## 📈 Beneficios del Nuevo Sistema

### **✅ Para Desarrolladores**
- **Modularidad**: Cada componente es independiente y testeable
- **Extensibilidad**: Fácil agregar nuevos tipos de análisis
- **Configurabilidad**: Pesos y umbrales personalizables
- **Trazabilidad**: Desglose completo de cálculos

### **✅ Para Detección de Fraude**
- **Mayor precisión**: 4 tipos de análisis complementarios
- **Penalizaciones proporcionales**: Castigo ajustado al riesgo real
- **Menos falsos negativos**: Peso base aumentado captura más casos
- **Mejor graduación**: Sistema escalonado evita penalizaciones excesivas

### **✅ Para Operaciones**
- **Compatibilidad total**: API existente sigue funcionando
- **Información detallada**: Más contexto para toma de decisiones  
- **Configuración flexible**: Ajustes sin cambios de código
- **Documentación completa**: Sistema autodocumentado

---

## 🎯 Recomendaciones de Implementación

### **Paso 1: Actualizar Configuración**
```json
// En risk_weights.json
{
  "capas_multiples": 15  // Cambiar de 5-10 a 15
}
```

### **Paso 2: Validar con Casos Reales**
- Ejecutar análisis en PDFs conocidos
- Comparar resultados con sistema anterior
- Ajustar umbrales si es necesario

### **Paso 3: Monitorear Resultados**
- Revisar distribución de penalizaciones
- Verificar correlación con casos reales de fraude
- Ajustar pesos de componentes según necesidad

---

## 📚 Archivos de Referencia

- **`helpers/deteccion_capas.py`**: Helper principal modular
- **`riesgo.py`**: Integración con sistema existente  
- **`ejemplo_uso_capas_dinamicas.py`**: Ejemplos de uso completos
- **`CAPAS_MULTIPLES_V2.md`**: Esta documentación

---

## 🎉 Conclusión

El nuevo sistema representa una **mejora significativa** en:

1. **🎯 Precisión**: Análisis más detallado y especializado
2. **⚖️ Proporcionalidad**: Penalizaciones ajustadas al riesgo real
3. **🏗️ Mantenibilidad**: Código modular y bien documentado
4. **🔧 Flexibilidad**: Configuración avanzada sin cambios de código

**Resultado**: Detección de fraude más efectiva con penalizaciones justas y sistema escalable para futuras mejoras.
