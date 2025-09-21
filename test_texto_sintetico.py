#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de la función de texto sintético aplanado
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.texto_sintetico_analisis import detectar_texto_sintetico_aplanado
import numpy as np
import cv2

def test_texto_sintetico():
    """Test de la función de texto sintético"""
    print("🔬 TEST ANÁLISIS DE TEXTO SINTÉTICO APLANADO")
    print("=" * 60)
    
    # Crear imagen de prueba sintética
    print("\n1️⃣ CREANDO IMAGEN DE PRUEBA SINTÉTICA")
    print("-" * 40)
    
    # Imagen base limpia
    img_limpia = np.ones((400, 600, 3), dtype=np.uint8) * 255
    
    # Agregar texto sintético (uniforme, limpio)
    cv2.putText(img_limpia, "FACTURA", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    cv2.putText(img_limpia, "RUC: 1790710319001", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    cv2.putText(img_limpia, "TOTAL: $47.00", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    cv2.putText(img_limpia, "FECHA: 08/07/2025", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    
    # Agregar más texto para simular muchas cajas
    for i in range(10):
        y = 300 + i * 20
        cv2.putText(img_limpia, f"Línea {i+1}: Texto sintético", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    
    # Agregar líneas
    cv2.line(img_limpia, (50, 280), (550, 280), (0, 0, 0), 2)
    cv2.line(img_limpia, (50, 320), (550, 320), (0, 0, 0), 1)
    
    print(f"Imagen sintética creada: {img_limpia.shape}")
    
    # Crear imagen natural para comparación
    print("\n2️⃣ CREANDO IMAGEN NATURAL PARA COMPARACIÓN")
    print("-" * 40)
    
    # Imagen con ruido y variaciones naturales
    img_natural = np.ones((400, 600, 3), dtype=np.uint8) * 255
    
    # Agregar ruido
    noise = np.random.normal(0, 10, img_natural.shape).astype(np.uint8)
    img_natural = np.clip(img_natural.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Agregar texto con variaciones
    cv2.putText(img_natural, "FACTURA", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    cv2.putText(img_natural, "RUC: 1790710319001", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    cv2.putText(img_natural, "TOTAL: $47.00", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    
    print(f"Imagen natural creada: {img_natural.shape}")
    
    # Analizar imagen sintética
    print("\n3️⃣ ANÁLISIS DE IMAGEN SINTÉTICA")
    print("-" * 40)
    
    try:
        resultado_sintetico = detectar_texto_sintetico_aplanado(img_limpia, ocr_text="FACTURA RUC: 1790710319001 TOTAL: $47.00 FECHA: 08/07/2025")
        
        print(f"Texto sintético detectado: {resultado_sintetico.get('tiene_texto_sintetico', False)}")
        print(f"Nivel de sospecha: {resultado_sintetico.get('nivel_sospecha', 'N/A')}")
        print(f"Cajas de texto detectadas: {resultado_sintetico.get('swt_analisis', {}).get('cajas_texto_detectadas', 0)}")
        print(f"Grosor uniforme: {resultado_sintetico.get('swt_analisis', {}).get('stroke_width_uniforme', False)}")
        print(f"CV grosor: {resultado_sintetico.get('swt_analisis', {}).get('cv_stroke_width', 0.0):.3f}")
        print(f"Color casi puro: {resultado_sintetico.get('color_antialias_analisis', {}).get('color_casi_puro', False)}")
        print(f"Ratio cajas puras: {resultado_sintetico.get('color_antialias_analisis', {}).get('ratio_cajas_puras', 0.0):.2%}")
        print(f"Halo ratio: {resultado_sintetico.get('halo_analisis', {}).get('halo_ratio_promedio', 0.0):.3f}")
        print(f"Coincide con montos/fechas: {resultado_sintetico.get('coincide_con_montos_fechas', False)}")
        print(f"Líneas totales: {resultado_sintetico.get('reguardado_analisis', {}).get('lineas_totales', 0)}")
        print(f"Densidad líneas: {resultado_sintetico.get('reguardado_analisis', {}).get('densidad_lineas_10kpx', 0.0):.2f}")
        
    except Exception as e:
        print(f"Error en análisis sintético: {e}")
        import traceback
        traceback.print_exc()
    
    # Analizar imagen natural
    print("\n4️⃣ ANÁLISIS DE IMAGEN NATURAL")
    print("-" * 40)
    
    try:
        resultado_natural = detectar_texto_sintetico_aplanado(img_natural, ocr_text="FACTURA RUC: 1790710319001 TOTAL: $47.00")
        
        print(f"Texto sintético detectado: {resultado_natural.get('tiene_texto_sintetico', False)}")
        print(f"Nivel de sospecha: {resultado_natural.get('nivel_sospecha', 'N/A')}")
        print(f"Cajas de texto detectadas: {resultado_natural.get('swt_analisis', {}).get('cajas_texto_detectadas', 0)}")
        print(f"Grosor uniforme: {resultado_natural.get('swt_analisis', {}).get('stroke_width_uniforme', False)}")
        print(f"CV grosor: {resultado_natural.get('swt_analisis', {}).get('cv_stroke_width', 0.0):.3f}")
        print(f"Color casi puro: {resultado_natural.get('color_antialias_analisis', {}).get('color_casi_puro', False)}")
        print(f"Ratio cajas puras: {resultado_natural.get('color_antialias_analisis', {}).get('ratio_cajas_puras', 0.0):.2%}")
        print(f"Halo ratio: {resultado_natural.get('halo_analisis', {}).get('halo_ratio_promedio', 0.0):.3f}")
        print(f"Coincide con montos/fechas: {resultado_natural.get('coincide_con_montos_fechas', False)}")
        print(f"Líneas totales: {resultado_natural.get('reguardado_analisis', {}).get('lineas_totales', 0)}")
        print(f"Densidad líneas: {resultado_natural.get('reguardado_analisis', {}).get('densidad_lineas_10kpx', 0.0):.2f}")
        
    except Exception as e:
        print(f"Error en análisis natural: {e}")
        import traceback
        traceback.print_exc()
    
    # Comparar resultados
    print("\n5️⃣ COMPARACIÓN DE RESULTADOS")
    print("-" * 40)
    
    if 'resultado_sintetico' in locals() and 'resultado_natural' in locals():
        sint_detectado = resultado_sintetico.get('tiene_texto_sintetico', False)
        nat_detectado = resultado_natural.get('tiene_texto_sintetico', False)
        
        print(f"Sintético - Detectado: {sint_detectado}")
        print(f"Natural - Detectado: {nat_detectado}")
        
        if sint_detectado and not nat_detectado:
            print("✅ DETECCIÓN CORRECTA: La función detecta correctamente el texto sintético")
        elif not sint_detectado and not nat_detectado:
            print("⚠️  DETECCIÓN PARCIAL: No detecta texto sintético en ninguna imagen")
        elif sint_detectado and nat_detectado:
            print("⚠️  DETECCIÓN PARCIAL: Detecta texto sintético en ambas imágenes")
        else:
            print("❌ DETECCIÓN INCORRECTA: La función no detecta correctamente el texto sintético")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_texto_sintetico()
