#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de la función de doble compresión JPEG
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.doble_compresion_analisis import detectar_doble_compresion
import numpy as np
import cv2

def test_doble_compresion():
    """Test de la función de doble compresión"""
    print("🔬 TEST ANÁLISIS DE DOBLE COMPRESIÓN JPEG")
    print("=" * 60)
    
    # Crear imagen de prueba sintética
    print("\n1️⃣ CREANDO IMAGEN DE PRUEBA SINTÉTICA")
    print("-" * 40)
    
    # Imagen base limpia
    img_limpia = np.ones((400, 600, 3), dtype=np.uint8) * 255
    
    # Agregar texto simulado
    cv2.putText(img_limpia, "FACTURA", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    cv2.putText(img_limpia, "RUC: 1790710319001", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    cv2.putText(img_limpia, "TOTAL: $47.00", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    
    # Agregar líneas
    cv2.line(img_limpia, (50, 250), (550, 250), (0, 0, 0), 2)
    cv2.line(img_limpia, (50, 300), (550, 300), (0, 0, 0), 1)
    
    # Convertir a JPEG (primera compresión)
    _, img_bytes_jpeg1 = cv2.imencode('.jpg', img_limpia, [cv2.IMWRITE_JPEG_QUALITY, 90])
    img_bytes_jpeg1 = img_bytes_jpeg1.tobytes()
    
    print(f"Imagen JPEG (primera compresión): {len(img_bytes_jpeg1)} bytes")
    
    # Crear doble compresión (recomprimir el JPEG)
    print("\n2️⃣ CREANDO DOBLE COMPRESIÓN")
    print("-" * 40)
    
    # Decodificar y volver a comprimir
    img_decoded = cv2.imdecode(np.frombuffer(img_bytes_jpeg1, np.uint8), cv2.IMREAD_COLOR)
    _, img_bytes_jpeg2 = cv2.imencode('.jpg', img_decoded, [cv2.IMWRITE_JPEG_QUALITY, 85])
    img_bytes_jpeg2 = img_bytes_jpeg2.tobytes()
    
    print(f"Imagen JPEG (doble compresión): {len(img_bytes_jpeg2)} bytes")
    
    # Crear imagen PNG para comparación
    print("\n3️⃣ CREANDO IMAGEN PNG PARA COMPARACIÓN")
    print("-" * 40)
    
    _, img_bytes_png = cv2.imencode('.png', img_limpia)
    img_bytes_png = img_bytes_png.tobytes()
    
    print(f"Imagen PNG: {len(img_bytes_png)} bytes")
    
    # Analizar imagen PNG
    print("\n4️⃣ ANÁLISIS DE IMAGEN PNG")
    print("-" * 40)
    
    try:
        resultado_png = detectar_doble_compresion(img_bytes_png)
        
        print(f"Doble compresión: {resultado_png.get('tiene_doble_compresion', False)}")
        print(f"Periodicidad detectada: {resultado_png.get('periodicidad_detectada', False)}")
        print(f"Confianza: {resultado_png.get('confianza', 'N/A')}")
        print(f"Número de picos: {resultado_png.get('num_peaks', 0)}")
        print(f"Consistencia: {resultado_png.get('consistencia_componentes', 0.0):.2%}")
        print(f"Varianza AC: {resultado_png.get('ac_variance', 0.0):.2f}")
        print(f"Varianza DC: {resultado_png.get('dc_variance', 0.0):.2f}")
        print(f"Es JPEG: {resultado_png.get('info_jpeg', {}).get('is_jpeg', False)}")
        
    except Exception as e:
        print(f"Error en análisis de PNG: {e}")
        import traceback
        traceback.print_exc()
    
    # Analizar primera compresión JPEG
    print("\n5️⃣ ANÁLISIS DE PRIMERA COMPRESIÓN JPEG")
    print("-" * 40)
    
    try:
        resultado_jpeg1 = detectar_doble_compresion(img_bytes_jpeg1)
        
        print(f"Doble compresión: {resultado_jpeg1.get('tiene_doble_compresion', False)}")
        print(f"Periodicidad detectada: {resultado_jpeg1.get('periodicidad_detectada', False)}")
        print(f"Confianza: {resultado_jpeg1.get('confianza', 'N/A')}")
        print(f"Número de picos: {resultado_jpeg1.get('num_peaks', 0)}")
        print(f"Consistencia: {resultado_jpeg1.get('consistencia_componentes', 0.0):.2%}")
        print(f"Varianza AC: {resultado_jpeg1.get('ac_variance', 0.0):.2f}")
        print(f"Varianza DC: {resultado_jpeg1.get('dc_variance', 0.0):.2f}")
        print(f"Es JPEG: {resultado_jpeg1.get('info_jpeg', {}).get('is_jpeg', False)}")
        
    except Exception as e:
        print(f"Error en análisis de JPEG1: {e}")
        import traceback
        traceback.print_exc()
    
    # Analizar doble compresión JPEG
    print("\n6️⃣ ANÁLISIS DE DOBLE COMPRESIÓN JPEG")
    print("-" * 40)
    
    try:
        resultado_jpeg2 = detectar_doble_compresion(img_bytes_jpeg2)
        
        print(f"Doble compresión: {resultado_jpeg2.get('tiene_doble_compresion', False)}")
        print(f"Periodicidad detectada: {resultado_jpeg2.get('periodicidad_detectada', False)}")
        print(f"Confianza: {resultado_jpeg2.get('confianza', 'N/A')}")
        print(f"Número de picos: {resultado_jpeg2.get('num_peaks', 0)}")
        print(f"Consistencia: {resultado_jpeg2.get('consistencia_componentes', 0.0):.2%}")
        print(f"Varianza AC: {resultado_jpeg2.get('ac_variance', 0.0):.2f}")
        print(f"Varianza DC: {resultado_jpeg2.get('dc_variance', 0.0):.2f}")
        print(f"Es JPEG: {resultado_jpeg2.get('info_jpeg', {}).get('is_jpeg', False)}")
        
        # Mostrar detalles de componentes
        detalles = resultado_jpeg2.get('detalles_componentes', [])
        if detalles:
            print(f"\nDetalles de componentes:")
            for i, comp in enumerate(detalles):
                print(f"  Componente {i+1}: periodicidad={comp.get('periodicidad', False)}, picos={comp.get('num_peaks', 0)}")
        
    except Exception as e:
        print(f"Error en análisis de JPEG2: {e}")
        import traceback
        traceback.print_exc()
    
    # Comparar resultados
    print("\n7️⃣ COMPARACIÓN DE RESULTADOS")
    print("-" * 40)
    
    if 'resultado_png' in locals() and 'resultado_jpeg1' in locals() and 'resultado_jpeg2' in locals():
        png_doble = resultado_png.get('tiene_doble_compresion', False)
        jpeg1_doble = resultado_jpeg1.get('tiene_doble_compresion', False)
        jpeg2_doble = resultado_jpeg2.get('tiene_doble_compresion', False)
        
        print(f"PNG - Doble compresión: {png_doble}")
        print(f"JPEG1 - Doble compresión: {jpeg1_doble}")
        print(f"JPEG2 - Doble compresión: {jpeg2_doble}")
        
        if not png_doble and not jpeg1_doble and jpeg2_doble:
            print("✅ DETECCIÓN CORRECTA: La función detecta correctamente la doble compresión")
        else:
            print("❌ DETECCIÓN INCORRECTA: La función no detecta correctamente la doble compresión")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_doble_compresion()
