#!/usr/bin/env python3
"""
Script de prueba para verificar que la API-Forense funciona correctamente en local.
"""

import requests
import json
import base64
import sys
from pathlib import Path

def test_health():
    """Prueba el endpoint de health."""
    print("🔍 Probando endpoint /health...")
    try:
        response = requests.get("http://127.0.0.1:8005/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health OK")
            print(f"   - Versión: {data.get('app_version', 'N/A')}")
            print(f"   - Modo: {data.get('mode', 'N/A')}")
            print(f"   - EasyOCR: {data.get('easyocr', 'N/A')}")
            print(f"   - PyTorch: {data.get('torch', 'N/A')}")
            return True
        else:
            print(f"❌ Health falló: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servidor. ¿Está ejecutándose?")
        return False
    except Exception as e:
        print(f"❌ Error en health: {e}")
        return False

def test_config():
    """Prueba el endpoint de configuración."""
    print("\n🔍 Probando endpoint /config/risk-weights...")
    try:
        response = requests.get("http://127.0.0.1:8005/config/risk-weights", timeout=10)
        if response.status_code == 200:
            data = response.json()
            weights = data.get('RISK_WEIGHTS', {})
            print("✅ Config OK")
            print(f"   - Criterios configurados: {len(weights)}")
            print(f"   - Peso fecha_creacion_vs_emision: {weights.get('fecha_creacion_vs_emision', 'N/A')}")
            return True
        else:
            print(f"❌ Config falló: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en config: {e}")
        return False

def create_test_pdf():
    """Crea un PDF de prueba simple en base64."""
    # PDF mínimo válido en base64
    pdf_content = """%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
    
    return base64.b64encode(pdf_content.encode()).decode()

def test_validar_documento():
    """Prueba el endpoint de validar-documento."""
    print("\n🔍 Probando endpoint /validar-documento...")
    try:
        pdf_b64 = create_test_pdf()
        payload = {"pdfbase64": pdf_b64}
        
        response = requests.post(
            "http://127.0.0.1:8005/validar-documento", 
            json=payload, 
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Validar-documento OK")
            print(f"   - SRI verificado: {data.get('sri_verificado', 'N/A')}")
            print(f"   - Mensaje: {data.get('mensaje', 'N/A')}")
            
            riesgo = data.get('riesgo', {})
            if riesgo:
                print(f"   - Score de riesgo: {riesgo.get('score', 'N/A')}")
                print(f"   - Nivel de riesgo: {riesgo.get('nivel', 'N/A')}")
            
            return True
        else:
            print(f"❌ Validar-documento falló: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error en validar-documento: {e}")
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("🚀 Iniciando pruebas de API-Forense local")
    print("=" * 50)
    
    tests = [
        test_health,
        test_config,
        test_validar_documento
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Resultados: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La API está funcionando correctamente.")
        return 0
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa la configuración.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
