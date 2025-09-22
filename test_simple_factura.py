#!/usr/bin/env python3
"""
Script simple para probar el endpoint validar-factura
"""

import base64
import requests
import json
import time

def test_simple():
    """Prueba simple del endpoint"""
    
    # Leer solo los primeros 50KB del PDF para prueba rápida
    pdf_path = r"C:\Users\Nexti\sources\api-forense\helpers\IMG\Factura_imagen.pdf"
    
    try:
        with open(pdf_path, 'rb') as f:
            # Leer solo una parte del archivo para prueba rápida
            pdf_bytes = f.read(50000)  # Solo 50KB
        
        print(f"✅ Archivo PDF leído (primeros 50KB)")
        print(f"   Tamaño: {len(pdf_bytes)} bytes")
        
        # Convertir a base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        print(f"✅ PDF convertido a base64")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Preparar la petición
    url = "http://localhost:8001/validar-factura"
    payload = {
        "pdfbase64": pdf_base64
    }
    
    print(f"\n🚀 Enviando petición a: {url}")
    
    try:
        # Hacer la petición con timeout corto
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=30)  # 30 segundos
        end_time = time.time()
        
        print(f"✅ Respuesta recibida en {end_time - start_time:.2f} segundos")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n📊 RESULTADO:")
            print(f"   SRI Verificado: {result.get('sri_verificado', 'N/A')}")
            print(f"   Mensaje: {result.get('mensaje', 'N/A')}")
            print(f"   Tipo Archivo: {result.get('tipo_archivo', 'N/A')}")
            
            factura = result.get('factura', {})
            print(f"\n📋 FACTURA:")
            print(f"   RUC: {factura.get('ruc', 'N/A')}")
            print(f"   Clave Acceso: {factura.get('claveAcceso', 'N/A')}")
            print(f"   Total: {factura.get('importeTotal', 'N/A')}")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}...")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout: La petición tardó más de 30 segundos")
    except requests.exceptions.ConnectionError:
        print(f"🔌 Error de conexión: ¿Está el servidor ejecutándose en localhost:8001?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 PRUEBA SIMPLE DEL ENDPOINT VALIDAR-FACTURA")
    print("=" * 50)
    test_simple()
