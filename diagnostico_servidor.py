#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Diagnóstico del servidor para verificar por qué no está usando el código actualizado
"""

import requests
import json
import base64
import os

def test_endpoint_directo():
    """Probar el endpoint directamente"""
    print("🔍 DIAGNÓSTICO DEL SERVIDOR")
    print("=" * 50)
    
    # Leer el archivo PDF
    pdf_path = r"C:\Users\Nexti\sources\api-forense\helpers\IMG\Factura_imagen.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Archivo no encontrado: {pdf_path}")
        return
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # Preparar la petición
    url = "http://localhost:8001/validar-factura"
    payload = {"pdfbase64": pdf_base64}
    
    print(f"📁 Archivo: {pdf_path}")
    print(f"📊 Tamaño: {len(pdf_bytes)} bytes")
    print(f"🔗 URL: {url}")
    print(f"📦 Payload size: {len(json.dumps(payload))} caracteres")
    
    try:
        print(f"\n🚀 Enviando petición...")
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"✅ Respuesta recibida")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📋 ESTRUCTURA DE LA RESPUESTA:")
            print(f"   Claves principales: {list(data.keys())}")
            
            # Verificar si tiene la sección factura
            if 'factura' in data:
                print(f"   ✅ Sección 'factura' presente")
                factura = data['factura']
                if isinstance(factura, dict):
                    print(f"   📊 Datos en factura: {len(factura)} claves")
                    print(f"   🏢 RUC: {factura.get('ruc', 'N/A')}")
                    print(f"   🔑 Clave Acceso: {factura.get('claveAcceso', 'N/A')}")
                    print(f"   💰 Total: {factura.get('total', 'N/A')}")
                else:
                    print(f"   ❌ Sección 'factura' no es un diccionario: {type(factura)}")
            else:
                print(f"   ❌ Sección 'factura' NO presente")
            
            # Verificar otros campos importantes
            print(f"\n📊 CAMPOS PRINCIPALES:")
            print(f"   SRI Verificado: {data.get('sri_verificado', 'N/A')}")
            print(f"   Mensaje: {data.get('mensaje', 'N/A')}")
            print(f"   Tipo Archivo: {data.get('tipo_archivo', 'N/A')}")
            
            # Verificar si hay errores en la respuesta
            if 'error' in data:
                print(f"   ❌ Error en respuesta: {data['error']}")
            
            # Guardar respuesta completa
            with open('diagnostico_respuesta.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Respuesta completa guardada en: diagnostico_respuesta.json")
            
        else:
            print(f"❌ Error del servidor: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Error de conexión: El servidor no está ejecutándose")
        print(f"   Asegúrate de que el servidor esté ejecutándose en el puerto 8001")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_endpoint_directo()