#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de debug para el análisis de texto sintético
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.texto_sintetico_analisis import detectar_texto_sintetico_aplanado
import numpy as np
import cv2

def test_texto_sintetico_debug():
    """Test de debug para el análisis de texto sintético"""
    print("🔬 DEBUG ANÁLISIS DE TEXTO SINTÉTICO")
    print("=" * 60)
    
    # Cargar imagen real
    img_path = "helpers/IMG/Captura de pantalla 2025-09-19 120741.png"
    
    if not os.path.exists(img_path):
        print(f"❌ No se encontró la imagen: {img_path}")
        return
    
    print(f"📸 Procesando imagen real: {img_path}")
    
    # Leer imagen
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
    
    # Analizar con texto OCR simulado
    texto_ocr = "FACTURA RUC: 1790710319001 TOTAL: $47.00 FECHA: 08/07/2025"
    
    try:
        resultado = detectar_texto_sintetico_aplanado(img_bytes, ocr_text=texto_ocr)
        
        print(f"\n📊 RESULTADOS DEL ANÁLISIS:")
        print(f"   Texto sintético detectado: {resultado.get('tiene_texto_sintetico', False)}")
        print(f"   Nivel de sospecha: {resultado.get('nivel_sospecha', 'N/A')}")
        
        # Análisis SWT
        swt = resultado.get('swt_analisis', {})
        print(f"\n🔍 ANÁLISIS SWT:")
        print(f"   Cajas detectadas: {swt.get('cajas_texto_detectadas', 0)}")
        print(f"   Grosor medio: {swt.get('stroke_width_mean', 0.0):.2f}")
        print(f"   Grosor std: {swt.get('stroke_width_std', 0.0):.2f}")
        print(f"   Grosor uniforme: {swt.get('stroke_width_uniforme', False)}")
        print(f"   CV grosor: {swt.get('cv_stroke_width', 0.0):.3f}")
        
        # Análisis de color
        color = resultado.get('color_antialias_analisis', {})
        print(f"\n🎨 ANÁLISIS DE COLOR:")
        print(f"   Color trazo promedio: {color.get('color_trazo_promedio', 0.0):.2f}")
        print(f"   Color casi puro: {color.get('color_casi_puro', False)}")
        print(f"   Ratio cajas puras: {color.get('ratio_cajas_puras', 0.0):.2%}")
        
        # Análisis de halo
        halo = resultado.get('halo_analisis', {})
        print(f"\n💫 ANÁLISIS DE HALO:")
        print(f"   Halo ratio promedio: {halo.get('halo_ratio_promedio', 0.0):.3f}")
        print(f"   Umbral halo: {halo.get('umbral_halo', 0.45)}")
        
        # Análisis de reguardado
        reguardado = resultado.get('reguardado_analisis', {})
        print(f"\n📏 ANÁLISIS DE REGUARDADO:")
        print(f"   Líneas totales: {reguardado.get('lineas_totales', 0)}")
        print(f"   Horiz/Vert: {reguardado.get('horiz_vert', 0)}")
        print(f"   Densidad líneas: {reguardado.get('densidad_lineas_10kpx', 0.0):.2f}")
        
        # Coincidencia con montos/fechas
        print(f"\n💰 COINCIDENCIA CON MONTOS/FECHAS:")
        print(f"   Coincide: {resultado.get('coincide_con_montos_fechas', False)}")
        
        # Criterios de decisión
        print(f"\n⚖️  CRITERIOS DE DECISIÓN:")
        cajas = swt.get('cajas_texto_detectadas', 0)
        densidad = reguardado.get('densidad_lineas_10kpx', 0.0)
        muchas_cajas = cajas >= 30 or densidad >= 0.8
        print(f"   Muchas cajas (≥30 o densidad ≥0.8): {muchas_cajas} (cajas: {cajas}, densidad: {densidad:.2f})")
        
        trazo_uniforme = swt.get('stroke_width_uniforme', False) and swt.get('stroke_width_mean', 0) >= 1.2
        print(f"   Trazo uniforme (CV<0.45 y mean≥1.2): {trazo_uniforme}")
        
        color_casi_puro = color.get('ratio_cajas_puras', 0.0) >= 0.6
        print(f"   Color casi puro (≥60%): {color_casi_puro} ({color.get('ratio_cajas_puras', 0.0):.2%})")
        
        halo_alto = halo.get('halo_ratio_promedio', 0.0) >= 0.45
        print(f"   Halo alto (≥0.45): {halo_alto} ({halo.get('halo_ratio_promedio', 0.0):.3f})")
        
        # Resultado final
        tiene_texto_sintetico = muchas_cajas and trazo_uniforme and color_casi_puro and halo_alto
        print(f"\n🎯 RESULTADO FINAL:")
        print(f"   Tiene texto sintético: {tiene_texto_sintetico}")
        print(f"   Criterios cumplidos: {sum([muchas_cajas, trazo_uniforme, color_casi_puro, halo_alto])}/4")
        
        if not tiene_texto_sintetico:
            print(f"\n❌ NO SE DETECTA TEXTO SINTÉTICO:")
            if not muchas_cajas:
                print(f"   - Faltan cajas de texto (necesita ≥30 o densidad ≥0.8)")
            if not trazo_uniforme:
                print(f"   - Trazo no uniforme (necesita CV<0.45 y mean≥1.2)")
            if not color_casi_puro:
                print(f"   - Color no casi puro (necesita ≥60% cajas puras)")
            if not halo_alto:
                print(f"   - Halo no alto (necesita ≥0.45)")
        
    except Exception as e:
        print(f"❌ Error en análisis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_texto_sintetico_debug()
