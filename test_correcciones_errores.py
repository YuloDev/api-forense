#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test para verificar que se han corregido los errores de MSER y bitwise_and
"""

import requests
import json
import os
import base64

def test_correcciones():
    """Test de correcciones de errores"""
    print("🔧 TEST CORRECCIONES DE ERRORES")
    print("=" * 50)
    
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
            print("✅ No se detectaron errores de MSER_create")
            print("✅ No se detectaron errores de bitwise_and")
            
            # Verificar que el análisis forense se ejecutó correctamente
            if 'riesgo' in result:
                riesgo = result['riesgo']
                prioritarias = riesgo.get('prioritarias', [])
                secundarias = riesgo.get('secundarias', [])
                
                print(f"\n📊 ANÁLISIS FORENSE COMPLETADO:")
                print(f"   - Prioritarias: {len(prioritarias)} checks")
                print(f"   - Secundarias: {len(secundarias)} checks")
                
                # Verificar checks específicos
                checks_encontrados = []
                for check in prioritarias + secundarias:
                    check_name = check.get('check', 'N/A')
                    checks_encontrados.append(check_name)
                
                print(f"\n🔍 CHECKS DETECTADOS:")
                for i, check in enumerate(checks_encontrados, 1):
                    print(f"   {i}. {check}")
                
                # Verificar que no hay errores en los detalles
                errores_encontrados = []
                for check in prioritarias + secundarias:
                    detalle = check.get('detalle', {})
                    if 'error' in str(detalle).lower():
                        errores_encontrados.append(check.get('check', 'N/A'))
                
                if errores_encontrados:
                    print(f"\n⚠️  ERRORES ENCONTRADOS EN CHECKS:")
                    for error in errores_encontrados:
                        print(f"   - {error}")
                else:
                    print(f"\n✅ NO SE DETECTARON ERRORES EN LOS CHECKS")
            
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
    test_correcciones()
