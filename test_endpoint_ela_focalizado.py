#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del endpoint validar_imagen con ELA focalizado
"""

import requests
import json
import os
import base64

def test_endpoint_ela_focalizado():
    """Test del endpoint validar_imagen con ELA focalizado"""
    print("🔬 TEST ENDPOINT CON ELA FOCALIZADO")
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
            
            # Verificar riesgo y prioritarias
            if 'riesgo' in result:
                riesgo = result['riesgo']
                print(f"\n⚠️  ANÁLISIS DE RIESGO:")
                print(f"   Score: {riesgo.get('score', 'N/A')}")
                print(f"   Nivel: {riesgo.get('nivel', 'N/A')}")
                print(f"   Es falso probable: {riesgo.get('es_falso_probable', 'N/A')}")
                
                # Verificar prioritarias
                prioritarias = riesgo.get('prioritarias', [])
                print(f"\n🔍 PRIORITARIAS ({len(prioritarias)}):")
                
                for i, check in enumerate(prioritarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    # Mostrar detalles de ELA focalizado
                    if check.get('check') == "ELA (Error Level Analysis) focalizado":
                        detalle = check.get('detalle', {})
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Nivel Sospecha: {detalle.get('nivel_sospecha', 'N/A')}")
                        print(f"      Clústeres Localizados: {detalle.get('clusters_localizados', 'N/A')}")
                        print(f"      Overlap Texto: {detalle.get('overlap_texto', 'N/A')}")
                        print(f"      Overlap Dígitos: {detalle.get('overlap_digitos', 'N/A')}")
                        print(f"      Peak Hits: {detalle.get('peak_hits', 'N/A')}")
                        print(f"      ELA Global Mean: {detalle.get('ela_global_mean', 'N/A')}")
                        print(f"      ELA Global Max: {detalle.get('ela_global_max', 'N/A')}")
                        print(f"      Ratio Sospechoso: {detalle.get('suspicious_ratio', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                        print(f"      Recomendación: {detalle.get('recomendacion', 'N/A')}")
                
                # Verificar secundarias
                secundarias = riesgo.get('secundarias', [])
                print(f"\n🔍 SECUNDARIAS ({len(secundarias)}):")
                
                for i, check in enumerate(secundarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    # Mostrar detalles de ELA focalizado en secundarias
                    if check.get('check') == "ELA (Error Level Analysis) focalizado":
                        detalle = check.get('detalle', {})
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Nivel Sospecha: {detalle.get('nivel_sospecha', 'N/A')}")
                        print(f"      Clústeres Localizados: {detalle.get('clusters_localizados', 'N/A')}")
                        print(f"      Overlap Texto: {detalle.get('overlap_texto', 'N/A')}")
                        print(f"      Overlap Dígitos: {detalle.get('overlap_digitos', 'N/A')}")
                        print(f"      Peak Hits: {detalle.get('peak_hits', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                        print(f"      Recomendación: {detalle.get('recomendacion', 'N/A')}")
                
                # Verificar adicionales
                adicionales = riesgo.get('adicionales', [])
                print(f"\n🔍 ADICIONALES ({len(adicionales)}):")
                for i, check in enumerate(adicionales):
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
    test_endpoint_ela_focalizado()
