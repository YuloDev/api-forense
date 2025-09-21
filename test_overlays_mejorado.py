#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del detector de overlays coloreados mejorado para reducir falsos positivos
"""

import requests
import json
import os
import base64

def test_overlays_mejorado():
    """Test del detector de overlays coloreados mejorado"""
    print("🎨 TEST OVERLAYS COLOREADOS MEJORADO")
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
                        print(f"      ✅ OVERLAYS COLOREADOS ENCONTRADO")
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Score parcial: {detalle.get('score_parcial', 'N/A')}")
                        print(f"      Color ratio: {detalle.get('color_ratio', 'N/A'):.4f}")
                        print(f"      Número de componentes: {detalle.get('num_componentes_coloreados', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                        print(f"      Recomendación: {detalle.get('recomendacion', 'N/A')}")
                        
                        # Mostrar criterios mejorados
                        criterios = detalle.get('criterios', {})
                        if criterios:
                            print(f"      Criterios mejorados:")
                            for criterio, descripcion in criterios.items():
                                print(f"        - {criterio}: {descripcion}")
                        
                        # Mostrar componentes disparados
                        componentes = detalle.get('componentes_disparados', [])
                        if componentes:
                            print(f"      Componentes disparados:")
                            for j, comp in enumerate(componentes[:5]):  # Mostrar solo los primeros 5
                                print(f"        {j+1}. Bbox: {comp.get('bbox', 'N/A')}")
                                print(f"           Área: {comp.get('area', 'N/A')}, Aspect: {comp.get('aspect', 'N/A'):.2f}")
                                print(f"           Edge ratio: {comp.get('edge_ratio', 'N/A'):.3f}, W_cv: {comp.get('w_cv', 'N/A'):.3f}")
                                print(f"           Solidity: {comp.get('solidity', 'N/A'):.3f}, ROI inter: {comp.get('roi_inter', 'N/A'):.3f}")
                        else:
                            print(f"      No hay componentes disparados específicos")
                        
                        # Mostrar análisis detallado
                        analisis_detallado = detalle.get('analisis_detallado', {})
                        if analisis_detallado:
                            print(f"      Análisis detallado:")
                            print(f"        - Metodología: {analisis_detallado.get('metodologia', 'N/A')}")
                            print(f"        - Componentes disparados: {len(analisis_detallado.get('componentes_disparados', []))}")
                
                if not overlays_encontrado:
                    print(f"\nℹ️  OVERLAYS COLOREADOS NO ENCONTRADO EN PRIORITARIAS")
                    print(f"   Esto indica que la imagen no tiene overlays coloreados sospechosos")
                    print(f"   (posible reducción de falsos positivos por logos)")
                
                # Verificar que el análisis de texto sintético también está presente
                texto_sintetico_encontrado = False
                for check in prioritarias:
                    if check.get('check') == "Texto sintético aplanado":
                        texto_sintetico_encontrado = True
                        print(f"\n✅ TEXTO SINTÉTICO APLANADO TAMBIÉN PRESENTE")
                        print(f"   Esto confirma que las cajas de texto se están compartiendo correctamente")
                        break
                
                if not texto_sintetico_encontrado:
                    print(f"\n⚠️  TEXTO SINTÉTICO APLANADO NO ENCONTRADO")
                    print(f"   Esto podría afectar la calidad del análisis de overlays coloreados")
            
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
    test_overlays_mejorado()
