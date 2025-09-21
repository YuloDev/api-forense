#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test para debuggear la validación SRI en PDFs escaneados
"""

import requests
import json
import os
import base64

def test_pdf_sri():
    """Test del endpoint validar_factura con PDF escaneado"""
    
    # URL del endpoint
    url = "http://localhost:8001/validar-factura"
    
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
            
            print("📤 Enviando request al endpoint...")
            response = requests.post(url, json=pdf_base64, timeout=60)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                print("\n" + "="*60)
                print("📋 RESULTADO DE LA VALIDACIÓN")
                print("="*60)
                
                # Información básica
                print(f"✅ Validación exitosa: {result.get('validacion_exitosa', 'N/A')}")
                print(f"📄 Tipo de documento: {result.get('tipo_documento', 'N/A')}")
                print(f"📊 Nivel de riesgo: {result.get('nivel_riesgo', 'N/A')}")
                
                # Información del PDF
                pdf_info = result.get('pdf_info', {})
                print(f"\n📄 INFORMACIÓN DEL PDF:")
                print(f"   Páginas procesadas: {pdf_info.get('pages_processed', 'N/A')}")
                print(f"   Métodos de extracción: {pdf_info.get('text_methods', 'N/A')}")
                print(f"   Longitud del texto: {pdf_info.get('text_length', 'N/A')}")
                
                # Clave de acceso
                access_key = result.get('access_key')
                print(f"\n🔑 CLAVE DE ACCESO:")
                print(f"   Clave encontrada: {access_key}")
                print(f"   Longitud: {len(access_key) if access_key else 0}")
                
                # Validación SRI
                sri_validation = result.get('sri_validation', {})
                print(f"\n🏛️ VALIDACIÓN SRI:")
                print(f"   Es documento SRI: {sri_validation.get('es_documento_sri', 'N/A')}")
                print(f"   Clave válida: {sri_validation.get('clave_valida', 'N/A')}")
                print(f"   Longitud correcta: {sri_validation.get('longitud_correcta', 'N/A')}")
                print(f"   Método de extracción: {sri_validation.get('metodo_extraccion', 'N/A')}")
                
                # Códigos de barras
                barcodes = result.get('barcodes', [])
                print(f"\n📊 CÓDIGOS DE BARRAS:")
                print(f"   Cantidad encontrados: {len(barcodes)}")
                for i, barcode in enumerate(barcodes):
                    print(f"   Barcode {i+1}: {barcode}")
                
                # Análisis de riesgo
                riesgo = result.get('riesgo', {})
                print(f"\n⚠️ ANÁLISIS DE RIESGO:")
                print(f"   Nivel: {riesgo.get('nivel_riesgo', 'N/A')}")
                print(f"   Puntuación: {riesgo.get('puntuacion', 'N/A')}")
                print(f"   Grado de confianza: {riesgo.get('grado_confianza', 'N/A')}")
                
                # Checks prioritarios
                prioritarias = riesgo.get('prioritarias', [])
                print(f"\n🔴 CHECKS PRIORITARIOS ({len(prioritarias)}):")
                for i, check in enumerate(prioritarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} - Penalización: {check.get('penalizacion', 'N/A')}")
                
                # Checks secundarios
                secundarias = riesgo.get('secundarias', [])
                print(f"\n🟡 CHECKS SECUNDARIOS ({len(secundarias)}):")
                for i, check in enumerate(secundarias):
                    print(f"   {i+1}. {check.get('check', 'N/A')} - Penalización: {check.get('penalizacion', 'N/A')}")
                
                print("\n" + "="*60)
                
            else:
                print(f"❌ Error en la respuesta: {response.status_code}")
                print(f"📄 Contenido: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión. ¿Está ejecutándose el servidor?")
        print("💡 Ejecuta: python main.py")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_pdf_sri()
