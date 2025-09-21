#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de la función ELA focalizado
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.ela_focalizado_analisis import analizar_ela_focalizado
import numpy as np
import cv2

def test_ela_focalizado():
    """Test de la función ELA focalizado"""
    print("🔬 TEST ANÁLISIS ELA FOCALIZADO")
    print("=" * 50)
    
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
    
    # Crear imagen con edición local en área de texto
    print("\n2️⃣ CREANDO IMAGEN CON EDICIÓN LOCAL EN TEXTO")
    print("-" * 40)
    
    img_editada = img_limpia.copy()
    
    # Simular edición local en área de texto (cambiar monto)
    # Área donde está "TOTAL: $47.00"
    patch_y, patch_x = 180, 50
    patch_h, patch_w = 30, 200
    
    # Crear ruido/artefactos en el área de texto
    noise = np.random.normal(0, 15, (patch_h, patch_w, 3)).astype(np.uint8)
    img_editada[patch_y:patch_y+patch_h, patch_x:patch_x+patch_w] = np.clip(
        img_editada[patch_y:patch_y+patch_h, patch_x:patch_x+patch_w].astype(np.int16) + noise, 
        0, 255
    ).astype(np.uint8)
    
    # Sobrescribir el texto con uno diferente (simular cambio de monto)
    cv2.rectangle(img_editada, (patch_x, patch_y), (patch_x + patch_w, patch_y + patch_h), (255, 255, 255), -1)
    cv2.putText(img_editada, "TOTAL: $147.00", (patch_x, patch_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
    
    # Convertir a bytes
    _, img_bytes_editada = cv2.imencode('.png', img_editada)
    img_bytes_editada = img_bytes_editada.tobytes()
    
    print(f"Imagen editada creada: {len(img_bytes_editada)} bytes")
    
    # Analizar imagen limpia
    print("\n3️⃣ ANÁLISIS DE IMAGEN LIMPIA")
    print("-" * 40)
    
    try:
        resultado_limpia = analizar_ela_focalizado(img_bytes_limpia)
        ela_data = resultado_limpia.get("ela", {})
        
        print(f"Marca editada: {ela_data.get('marca_editada', False)}")
        print(f"Nivel sospecha: {ela_data.get('nivel_sospecha', 'N/A')}")
        print(f"Clústeres localizados: {ela_data.get('clusters', {}).get('localized', 0)}")
        print(f"Overlap con texto: {ela_data.get('texto', {}).get('overlap_text', False)}")
        print(f"Overlap con dígitos: {ela_data.get('texto', {}).get('overlap_digits', False)}")
        print(f"Peak hits: {ela_data.get('texto', {}).get('peak_hits', 0)}")
        print(f"ELA global mean: {ela_data.get('global', {}).get('mean', 0):.2f}")
        print(f"ELA global max: {ela_data.get('global', {}).get('max', 0):.2f}")
        print(f"Ratio sospechoso: {ela_data.get('suspicious_global_ratio', 0):.2%}")
        
    except Exception as e:
        print(f"Error en análisis de imagen limpia: {e}")
        import traceback
        traceback.print_exc()
    
    # Analizar imagen editada
    print("\n4️⃣ ANÁLISIS DE IMAGEN EDITADA")
    print("-" * 40)
    
    try:
        resultado_editada = analizar_ela_focalizado(img_bytes_editada)
        ela_data = resultado_editada.get("ela", {})
        
        print(f"Marca editada: {ela_data.get('marca_editada', False)}")
        print(f"Nivel sospecha: {ela_data.get('nivel_sospecha', 'N/A')}")
        print(f"Clústeres localizados: {ela_data.get('clusters', {}).get('localized', 0)}")
        print(f"Overlap con texto: {ela_data.get('texto', {}).get('overlap_text', False)}")
        print(f"Overlap con dígitos: {ela_data.get('texto', {}).get('overlap_digits', False)}")
        print(f"Peak hits: {ela_data.get('texto', {}).get('peak_hits', 0)}")
        print(f"ELA global mean: {ela_data.get('global', {}).get('mean', 0):.2f}")
        print(f"ELA global max: {ela_data.get('global', {}).get('max', 0):.2f}")
        print(f"Ratio sospechoso: {ela_data.get('suspicious_global_ratio', 0):.2%}")
        
        # Mostrar detalles de clústeres
        clusters = ela_data.get('clusters', {}).get('detalle', [])
        if clusters:
            print(f"\nDetalles de clústeres:")
            for i, cluster in enumerate(clusters):
                print(f"  Clúster {i+1}: bbox={cluster.get('bbox', [])}, tamaño={cluster.get('size_tiles', 0)}")
                print(f"    perc_mean: {cluster.get('perc_mean', 0):.2%}")
                print(f"    ela_max_cluster: {cluster.get('ela_max_cluster', 0):.2f}")
        
    except Exception as e:
        print(f"Error en análisis de imagen editada: {e}")
        import traceback
        traceback.print_exc()
    
    # Comparar resultados
    print("\n5️⃣ COMPARACIÓN DE RESULTADOS")
    print("-" * 40)
    
    if 'resultado_limpia' in locals() and 'resultado_editada' in locals():
        limpia_editada = resultado_limpia.get('ela', {}).get('marca_editada', False)
        editada_editada = resultado_editada.get('ela', {}).get('marca_editada', False)
        limpia_nivel = resultado_limpia.get('ela', {}).get('nivel_sospecha', 'N/A')
        editada_nivel = resultado_editada.get('ela', {}).get('nivel_sospecha', 'N/A')
        
        print(f"Imagen limpia - Marca editada: {limpia_editada}")
        print(f"Imagen limpia - Nivel: {limpia_nivel}")
        print(f"Imagen editada - Marca editada: {editada_editada}")
        print(f"Imagen editada - Nivel: {editada_nivel}")
        
        if not limpia_editada and editada_editada:
            print("✅ DETECCIÓN CORRECTA: La función detecta correctamente la edición local en texto")
        else:
            print("❌ DETECCIÓN INCORRECTA: La función no detecta correctamente la edición local en texto")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_ela_focalizado()
