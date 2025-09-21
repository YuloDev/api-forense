#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de la función robusta de análisis de ruido y bordes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.ruido_bordes_analisis import analizar_ruido_y_bordes
import numpy as np
import cv2

def test_ruido_bordes_robusto():
    """Test de la función robusta de análisis de ruido y bordes"""
    print("🔬 TEST ANÁLISIS ROBUSTO DE RUIDO Y BORDES")
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
    
    # Convertir a bytes
    _, img_bytes_limpia = cv2.imencode('.png', img_limpia)
    img_bytes_limpia = img_bytes_limpia.tobytes()
    
    print(f"Imagen limpia creada: {len(img_bytes_limpia)} bytes")
    
    # Crear imagen con edición local (área modificada)
    print("\n2️⃣ CREANDO IMAGEN CON EDICIÓN LOCAL")
    print("-" * 40)
    
    img_editada = img_limpia.copy()
    
    # Simular edición local en un área específica
    # Agregar ruido en un parche
    patch_y, patch_x = 100, 200
    patch_h, patch_w = 80, 120
    
    # Ruido gaussiano
    noise = np.random.normal(0, 20, (patch_h, patch_w, 3)).astype(np.uint8)
    img_editada[patch_y:patch_y+patch_h, patch_x:patch_x+patch_w] = np.clip(
        img_editada[patch_y:patch_y+patch_h, patch_x:patch_x+patch_w].astype(np.int16) + noise, 
        0, 255
    ).astype(np.uint8)
    
    # Agregar líneas artificiales en el área editada
    for i in range(5):
        y = patch_y + i * 15
        cv2.line(img_editada, (patch_x, y), (patch_x + patch_w, y), (100, 100, 100), 1)
    
    # Convertir a bytes
    _, img_bytes_editada = cv2.imencode('.png', img_editada)
    img_bytes_editada = img_bytes_editada.tobytes()
    
    print(f"Imagen editada creada: {len(img_bytes_editada)} bytes")
    
    # Analizar imagen limpia
    print("\n3️⃣ ANÁLISIS DE IMAGEN LIMPIA")
    print("-" * 40)
    
    try:
        resultado_limpia = analizar_ruido_y_bordes(img_bytes_limpia)
        
        print(f"Tiene edición local: {resultado_limpia['tiene_edicion_local']}")
        print(f"Nivel sospecha: {resultado_limpia['nivel_sospecha']}")
        print(f"Ratio outliers: {resultado_limpia['outliers']['ratio']:.2%}")
        print(f"Clústeres localizados: {resultado_limpia['clusters']['localized']}")
        print(f"Ratio halo: {resultado_limpia['halo_ratio']:.2%}")
        print(f"Líneas totales: {resultado_limpia['lines']['total']}")
        print(f"Grupos paralelos: {resultado_limpia['lines']['parallel_groups']}")
        print(f"Varianza Laplaciano: {resultado_limpia['laplacian_variance_global']:.2f}")
        print(f"Densidad bordes: {resultado_limpia['edge_density_global']:.2%}")
        
    except Exception as e:
        print(f"Error en análisis de imagen limpia: {e}")
        import traceback
        traceback.print_exc()
    
    # Analizar imagen editada
    print("\n4️⃣ ANÁLISIS DE IMAGEN EDITADA")
    print("-" * 40)
    
    try:
        resultado_editada = analizar_ruido_y_bordes(img_bytes_editada)
        
        print(f"Tiene edición local: {resultado_editada['tiene_edicion_local']}")
        print(f"Nivel sospecha: {resultado_editada['nivel_sospecha']}")
        print(f"Ratio outliers: {resultado_editada['outliers']['ratio']:.2%}")
        print(f"Clústeres localizados: {resultado_editada['clusters']['localized']}")
        print(f"Ratio halo: {resultado_editada['halo_ratio']:.2%}")
        print(f"Líneas totales: {resultado_editada['lines']['total']}")
        print(f"Grupos paralelos: {resultado_editada['lines']['parallel_groups']}")
        print(f"Varianza Laplaciano: {resultado_editada['laplacian_variance_global']:.2f}")
        print(f"Densidad bordes: {resultado_editada['edge_density_global']:.2%}")
        
        # Mostrar detalles de clústeres
        if resultado_editada['clusters']['localized'] > 0:
            print(f"\nDetalles de clústeres:")
            for i, bbox in enumerate(resultado_editada['clusters']['boxes']):
                print(f"  Clúster {i+1}: bbox={bbox}, tamaño={resultado_editada['clusters']['sizes'][i]}")
        
    except Exception as e:
        print(f"Error en análisis de imagen editada: {e}")
        import traceback
        traceback.print_exc()
    
    # Comparar resultados
    print("\n5️⃣ COMPARACIÓN DE RESULTADOS")
    print("-" * 40)
    
    if 'resultado_limpia' in locals() and 'resultado_editada' in locals():
        print(f"Imagen limpia - Edición local: {resultado_limpia['tiene_edicion_local']}")
        print(f"Imagen editada - Edición local: {resultado_editada['tiene_edicion_local']}")
        
        if resultado_limpia['tiene_edicion_local'] == False and resultado_editada['tiene_edicion_local'] == True:
            print("✅ DETECCIÓN CORRECTA: La función detecta correctamente la edición local")
        else:
            print("❌ DETECCIÓN INCORRECTA: La función no detecta correctamente la edición local")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_ruido_bordes_robusto()
