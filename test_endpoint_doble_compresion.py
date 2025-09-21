#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del endpoint validar_imagen con doble compresión
"""

import requests
import json
import os
import base64

def test_endpoint_doble_compresion():
    """Test del endpoint validar_imagen con doble compresión"""
    print("🔬 TEST ENDPOINT CON DOBLE COMPRESIÓN")
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
            
            # Verificar riesgo y secundarias
            if 'riesgo' in result:
                riesgo = result['riesgo']
                print(f"\n⚠️  ANÁLISIS DE RIESGO:")
                print(f"   Score: {riesgo.get('score', 'N/A')}")
                print(f"   Nivel: {riesgo.get('nivel', 'N/A')}")
                print(f"   Es falso probable: {riesgo.get('es_falso_probable', 'N/A')}")
                
                # Verificar secundarias
                secundarias = riesgo.get('secundarias', [])
                print(f"\n🔍 SECUNDARIAS ({len(secundarias)}):")
                
                for i, check in enumerate(secundarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                    
                    # Mostrar detalles de doble compresión
                    if check.get('check') == "Doble compresión JPEG":
                        detalle = check.get('detalle', {})
                        print(f"      Detectado: {detalle.get('detectado', 'N/A')}")
                        print(f"      Periodicidad: {detalle.get('periodicidad_detectada', 'N/A')}")
                        print(f"      Confianza: {detalle.get('confianza', 'N/A')}")
                        print(f"      Número de picos: {detalle.get('num_peaks', 'N/A')}")
                        print(f"      Consistencia: {detalle.get('consistencia_componentes', 'N/A')}")
                        print(f"      Varianza AC: {detalle.get('ac_variance', 'N/A')}")
                        print(f"      Varianza DC: {detalle.get('dc_variance', 'N/A')}")
                        print(f"      Es JPEG: {detalle.get('is_jpeg', 'N/A')}")
                        print(f"      Interpretación: {detalle.get('interpretacion', 'N/A')}")
                        print(f"      Recomendación: {detalle.get('recomendacion', 'N/A')}")
                        print(f"      Nota importante: {detalle.get('nota_importante', 'N/A')}")
                
                # Verificar prioritarias
                prioritarias = riesgo.get('prioritarias', [])
                print(f"\n🔍 PRIORITARIAS ({len(prioritarias)}):")
                
                for i, check in enumerate(prioritarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} (penalización: {check.get('penalizacion', 0)})")
                
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
    test_endpoint_doble_compresion()
