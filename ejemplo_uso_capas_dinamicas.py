"""
Ejemplo de uso del nuevo sistema modular de detección de capas múltiples.

Este archivo demuestra cómo usar el helper helpers/deteccion_capas.py
y las nuevas funciones integradas en riesgo.py.
"""

from helpers.deteccion_capas import LayerDetector, calculate_dynamic_penalty, RiskWeights
from riesgo import evaluar_capas_multiples_completo, calcular_penalizacion_capas_optimizada


def ejemplo_analisis_basico():
    """Ejemplo básico de análisis de capas múltiples."""
    print("=== EJEMPLO 1: Análisis Básico ===")
    
    # Simular datos de un PDF (en uso real serían bytes del archivo)
    pdf_bytes = b"PDF content here..."  # Datos reales del PDF
    extracted_text = "Texto extraído del PDF con posibles superposiciones..."
    
    try:
        # Usar el detector modular directamente
        detector = LayerDetector(pdf_bytes, extracted_text, base_weight=15)
        resultado = detector.analyze()
        
        print(f"Capas detectadas: {resultado['has_layers']}")
        print(f"Probabilidad: {resultado['probability_percentage']:.1f}%")
        print(f"Nivel de riesgo: {resultado['risk_level']}")
        print(f"Confianza: {resultado['confidence']:.3f}")
        print(f"Penalización calculada: {resultado['penalty_points']} puntos")
        print(f"Indicadores: {resultado['indicators']}")
        
        # Desglose técnico
        print("\n--- Desglose Técnico ---")
        print(f"Objetos OCG: {resultado['ocg_objects']}")
        print(f"Objetos superpuestos: {resultado['overlay_objects']}")
        print(f"Content streams: {resultado['content_streams']}")
        print(f"Estimación de capas: {resultado['layer_count_estimate']}")
        
    except Exception as e:
        print(f"Error en análisis: {e}")


def ejemplo_analisis_completo():
    """Ejemplo usando la función de conveniencia integrada."""
    print("\n=== EJEMPLO 2: Análisis Completo con Función de Conveniencia ===")
    
    pdf_bytes = b"PDF content here..."
    extracted_text = "Texto con superposiciones detectadas..."
    
    # Usar función de conveniencia
    resultado = evaluar_capas_multiples_completo(pdf_bytes, extracted_text, base_weight=15)
    
    if "error" not in resultado:
        print(f"✅ Análisis exitoso")
        print(f"📊 Probabilidad: {resultado['probability_percentage']:.1f}%")
        print(f"⚠️ Nivel: {resultado['risk_level']}")
        print(f"💰 Penalización: {resultado['penalty_points']} puntos")
        
        # Información de configuración
        config = resultado.get('configuration', {})
        print(f"🔧 Versión: {config.get('analysis_version')}")
        print(f"🔧 Componentes: {config.get('components_analyzed')}")
        print(f"🔧 Peso base: {config.get('base_weight_used')}")
        
        # Desglose de puntuación
        if 'score_breakdown' in resultado:
            print("\n--- Desglose de Puntuación ---")
            breakdown = resultado['score_breakdown']
            for component, score in breakdown.items():
                print(f"  {component}: {score:.3f}")
    else:
        print(f"❌ Error: {resultado['error']}")


def ejemplo_calculo_penalizacion():
    """Ejemplo de cálculo de penalización optimizada."""
    print("\n=== EJEMPLO 3: Cálculo de Penalización Optimizada ===")
    
    # Casos de prueba con diferentes probabilidades
    casos_prueba = [
        {"prob": 15.0, "nivel": "VERY_LOW"},
        {"prob": 39.5, "nivel": "LOW"},      # Tu caso del ejemplo
        {"prob": 65.0, "nivel": "HIGH"},
        {"prob": 85.0, "nivel": "VERY_HIGH"},
        {"prob": 100.0, "nivel": "VERY_HIGH"}
    ]
    
    for caso in casos_prueba:
        resultado = calcular_penalizacion_capas_optimizada(
            probability_percentage=caso["prob"],
            risk_level=caso["nivel"],
            base_weight=15
        )
        
        print(f"\n📊 Probabilidad: {caso['prob']:.1f}% ({caso['nivel']})")
        print(f"💰 Penalización: {resultado['penalty_points']} puntos")
        print(f"📝 {resultado['explanation']}")
        
        # Desglose del cálculo
        breakdown = resultado['calculation_breakdown']
        print(f"   - Método proporcional: {breakdown['proportional_method']} pts")
        print(f"   - Método escalonado: {breakdown['scaled_method']} pts")
        print(f"   - Método usado: {breakdown['method_used']}")


def ejemplo_comparacion_pesos():
    """Ejemplo comparando diferentes pesos base."""
    print("\n=== EJEMPLO 4: Comparación de Pesos Base ===")
    
    probability = 39.5  # Tu ejemplo
    pesos_a_probar = [5, 10, 15, 20]  # Pesos actuales vs recomendados
    
    print(f"Para una probabilidad de {probability:.1f}%:\n")
    
    for peso in pesos_a_probar:
        penalizacion = calculate_dynamic_penalty(probability, peso)
        print(f"Peso base {peso:2d}: {penalizacion:2d} puntos")
    
    print(f"\n🎯 Recomendación: Usar peso base {RiskWeights.BASE_WEIGHT} puntos")
    print(f"   Genera penalizaciones proporcionales al riesgo real")


def ejemplo_analisis_componentes():
    """Ejemplo mostrando análisis detallado por componentes."""
    print("\n=== EJEMPLO 5: Análisis Detallado por Componentes ===")
    
    # Mostrar configuración de pesos
    print("🔧 Configuración de Pesos por Componente:")
    for componente, peso in RiskWeights.COMPONENT_WEIGHTS.items():
        print(f"   {componente}: {peso:.2%}")
    
    print(f"\n🎯 Umbrales de Riesgo:")
    for nivel, umbral in RiskWeights.RISK_THRESHOLDS.items():
        print(f"   {nivel}: {umbral:.1%}+")
    
    print(f"\n⚖️ Multiplicadores de Penalización:")
    for nivel, mult in RiskWeights.RISK_MULTIPLIERS.items():
        print(f"   {nivel}: {mult:.1%} del peso base")


def main():
    """Ejecuta todos los ejemplos."""
    print("🔍 SISTEMA MODULAR DE DETECCIÓN DE CAPAS MÚLTIPLES")
    print("=" * 60)
    
    # Ejemplos de análisis
    ejemplo_analisis_basico()
    ejemplo_analisis_completo()
    
    # Ejemplos de cálculos
    ejemplo_calculo_penalizacion()
    ejemplo_comparacion_pesos()
    
    # Información de configuración
    ejemplo_analisis_componentes()
    
    print("\n" + "=" * 60)
    print("✅ Todos los ejemplos ejecutados correctamente")
    print("📖 Documentación completa en helpers/deteccion_capas.py")


if __name__ == "__main__":
    main()
