#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test simple para diagnosticar el problema con validar_factura
"""

import requests
import json
import base64
import os

def test_simple_pdf():
    """Test simple del endpoint validar_factura"""
    
    # URL del endpoint
    url = "http://localhost:8001/validar_factura"
    
    # Ruta del PDF
    pdf_path = "helpers/IMG/Factura_imagen.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: No se encuentra el archivo {pdf_path}")
        return
    
    print(f"🔍 Probando con PDF: {pdf_path}")
    print(f"📏 Tamaño del archivo: {os.path.getsize(pdf_path)} bytes")
    
    try:
        # Leer el PDF y convertirlo a base64
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            print(f"📤 Base64 length: {len(pdf_base64)}")
            
            # Test 1: JSON con base64
            print("\n=== TEST 1: JSON con base64 ===")
            try:
                response = requests.post(url, json={
                    'archivo_base64': pdf_base64,
                    'nombre_archivo': 'Factura_imagen.pdf',
                    'validar_sri': True
                }, timeout=30)
                
                print(f"✅ Status Code: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print("📄 Respuesta exitosa")
                    print(f"SRI verificado: {result.get('sri_verificado', 'N/A')}")
                else:
                    print(f"❌ Error: {response.text}")
                    
            except Exception as e:
                print(f"❌ Error en test JSON: {e}")
            
            # Test 2: Multipart form
            print("\n=== TEST 2: Multipart form ===")
            try:
                files = {'archivo': ('Factura_imagen.pdf', pdf_bytes, 'application/pdf')}
                data = {'validar_sri': True}
                
                response = requests.post(url, files=files, data=data, timeout=30)
                
                print(f"✅ Status Code: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print("📄 Respuesta exitosa")
                    print(f"SRI verificado: {result.get('sri_verificado', 'N/A')}")
                else:
                    print(f"❌ Error: {response.text}")
                    
            except Exception as e:
                print(f"❌ Error en test multipart: {e}")
                
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    test_simple_pdf()
