#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del endpoint validar_imagen con la corrección del sri_verificado
"""

import requests
import json
import os

def test_endpoint_corregido():
    """Test del endpoint validar_imagen con sri_verificado corregido"""
    print("🔬 TEST ENDPOINT CON SRI_VERIFICADO CORREGIDO")
    print("=" * 60)
    
    # URL del endpoint
    url = "http://localhost:8000/validar-imagen"
    
    # Imagen de prueba
    img_path = "helpers/IMG/Captura de pantalla 2025-09-19 120741.png"
    
    if not os.path.exists(img_path):
        print(f"❌ No se encontró la imagen: {img_path}")
        return
    
    print(f"📸 Procesando imagen: {img_path}")
    
    # Leer imagen
    with open(img_path, 'rb') as f:
        files = {'file': (img_path, f, 'image/png')}
        
        try:
            # Hacer petición
            response = requests.post(url, files=files)
            
            if response.status_code == 200:
                result = response.json()
                
                print("✅ Respuesta exitosa!")
                
                # Verificar sri_verificado principal
                sri_verificado_principal = result.get('sri_verificado', False)
                mensaje_principal = result.get('mensaje', 'N/A')
                
                print(f"\n🔑 VALIDACIÓN SRI PRINCIPAL:")
                print(f"   sri_verificado: {sri_verificado_principal}")
                print(f"   mensaje: {mensaje_principal}")
                
                # Verificar sri_verificado en factura
                if 'factura' in result:
                    factura = result['factura']
                    sri_verificado_factura = factura.get('sri_verificado', False)
                    mensaje_factura = factura.get('mensaje', 'N/A')
                    
                    print(f"\n📄 VALIDACIÓN SRI EN FACTURA:")
                    print(f"   sri_verificado: {sri_verificado_factura}")
                    print(f"   mensaje: {mensaje_factura}")
                    
                    # Verificar validacion_sri
                    if 'validacion_sri' in factura:
                        validacion = factura['validacion_sri']
                        print(f"\n🔍 DETALLES VALIDACIÓN SRI:")
                        print(f"   válido: {validacion.get('valido', False)}")
                        print(f"   clave_acceso: {validacion.get('clave_acceso', 'N/A')}")
                        
                        if validacion.get('consulta_sri'):
                            sri = validacion['consulta_sri']
                            print(f"   estado: {sri.get('estado', 'N/A')}")
                            print(f"   fecha_autorizacion: {sri.get('fecha_autorizacion', 'N/A')}")
                
                # Verificar consistencia
                if sri_verificado_principal == sri_verificado_factura:
                    print(f"\n✅ CONSISTENCIA: Los valores de sri_verificado coinciden")
                else:
                    print(f"\n❌ INCONSISTENCIA: Los valores de sri_verificado NO coinciden")
                    print(f"   Principal: {sri_verificado_principal}")
                    print(f"   Factura: {sri_verificado_factura}")
                
            else:
                print(f"❌ Error en la respuesta: {response.status_code}")
                print(f"Respuesta: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Error de conexión. ¿Está ejecutándose el servidor?")
            print("Ejecuta: python main.py")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_endpoint_corregido()
