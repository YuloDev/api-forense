#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del análisis de overlays coloreados
"""

import requests
import json
import os
import base64

def test_overlays_coloreados():
    """Test del análisis de overlays coloreados"""
    print("🔬 TEST ANÁLISIS DE OVERLAYS COLORADOS")
    print("=" * 60)
    
    # URL del endpoint
    url = "http://localhost:8000/validar-imagen"
    
    # Imagen de prueba
    img_path = "helpers/IMG/Captura de pantalla 2025-09-19 120741.png"
    
    if not os.path.exists(img_path):
        print(f"❌ No se encontró la imagen: {img_path}")
        return
    
    print(f"📸 Procesando imagen: {img_path}")
    
    # Leer imagen y convertir a base64
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    # Datos de la petición
    data = {
        "imagen_base64": img_base64
    }
    
    try:
        # Hacer petición
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Respuesta exitosa!")
            
            # Verificar prioritarias
            if 'riesgo' in result:
                riesgo = result['riesgo']
                prioritarias = riesgo.get('prioritarias', [])
                
                print(f"\n🔍 PRIORITARIAS ({len(prioritarias)}):")
                
                overlays_encontrado = False
                for i, check in enumerate(prioritarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    if check.get('check') == "Overlays coloreados (strokes/garabatos)":
                        overlays_encontrado = True
                        detalle = check.get('detalle', {})
                        print(f"      ✅ OVERLAYS COLORADOS ENCONTRADO EN PRIORITARIAS")
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Score parcial: {detalle.get('score_parcial', 'N/A')}")
                        print(f"      Ratio de color: {detalle.get('color_ratio', 'N/A')}")
                        print(f"      Componentes coloreados: {detalle.get('num_componentes_coloreados', 'N/A')}")
                        print(f"      Componentes disparados: {len(detalle.get('componentes_disparados', []))}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                        print(f"      Recomendación: {detalle.get('recomendacion', 'N/A')}")
                        
                        # Mostrar criterios
                        criterios = detalle.get('criterios', {})
                        if criterios:
                            print(f"      Criterios:")
                            for criterio, valor in criterios.items():
                                print(f"        - {criterio}: {valor}")
                        
                        # Mostrar componentes disparados
                        componentes = detalle.get('componentes_disparados', [])
                        if componentes:
                            print(f"      Componentes disparados:")
                            for j, comp in enumerate(componentes[:5]):  # Mostrar solo los primeros 5
                                print(f"        {j+1}. Bbox: {comp.get('bbox', 'N/A')}, Area: {comp.get('area', 'N/A')}, Aspect: {comp.get('aspect', 'N/A'):.2f}")
                                print(f"           W_mean: {comp.get('w_mean', 'N/A'):.2f}, W_cv: {comp.get('w_cv', 'N/A'):.3f}, Edge_ratio: {comp.get('edge_ratio', 'N/A'):.3f}")
                
                if not overlays_encontrado:
                    print(f"\nℹ️  OVERLAYS COLORADOS NO ENCONTRADO EN PRIORITARIAS")
                    print(f"   Esto indica que la imagen no tiene elementos coloreados superpuestos")
                
                # Verificar secundarias
                secundarias = riesgo.get('secundarias', [])
                print(f"\n🔍 SECUNDARIAS ({len(secundarias)}):")
                
                for i, check in enumerate(secundarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
            
        else:
            print(f"❌ Error en la respuesta: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión. ¿Está ejecutándose el servidor?")
        print("Ejecuta: python main.py")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_overlays_coloreados()
