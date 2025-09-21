#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test del endpoint validar_imagen con la nueva implementación
"""

import requests
import json
import os

def test_endpoint_completo():
    """Test del endpoint validar_imagen"""
    print("🔬 TEST ENDPOINT COMPLETO CON NUEVA IMPLEMENTACIÓN")
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
                print(f"📊 Status: {result.get('status')}")
                print(f"📊 Parser avanzado: {result.get('parser_avanzado', {}).get('disponible', False)}")
                
                # Mostrar información de la clave de acceso
                if 'parser_avanzado' in result and result['parser_avanzado']:
                    parser = result['parser_avanzado']
                    print(f"\n🔑 CLAVE DE ACCESO:")
                    print(f"   Clave: {parser.get('clave_acceso_parseada', {}).get('clave_completa', 'No disponible')}")
                    print(f"   Válida: {parser.get('clave_acceso_parseada', {}).get('valida', False)}")
                    
                    if parser.get('clave_acceso_parseada', {}).get('valida'):
                        parsed = parser['clave_acceso_parseada']
                        print(f"   Fecha: {parsed.get('fecha_emision', 'N/A')}")
                        print(f"   RUC: {parsed.get('ruc_emisor', 'N/A')}")
                        print(f"   Tipo: {parsed.get('tipo_comprobante', {}).get('descripcion', 'N/A')}")
                        print(f"   Serie: {parsed.get('serie', 'N/A')}")
                        print(f"   Secuencial: {parsed.get('secuencial', 'N/A')}")
                
                # Mostrar información de la factura
                if 'factura' in result:
                    factura = result['factura']
                    print(f"\n📄 FACTURA:")
                    print(f"   RUC: {factura.get('ruc', 'N/A')}")
                    print(f"   Razón Social: {factura.get('razonSocial', 'N/A')}")
                    print(f"   Fecha Emisión: {factura.get('fechaEmision', 'N/A')}")
                    print(f"   Importe Total: {factura.get('importeTotal', 'N/A')}")
                    print(f"   Clave Acceso: {factura.get('claveAcceso', 'N/A')}")
                
                # Mostrar información de riesgo
                if 'riesgo' in result:
                    riesgo = result['riesgo']
                    print(f"\n⚠️  RIESGO:")
                    print(f"   Puntuación: {riesgo.get('puntuacion', 'N/A')}")
                    print(f"   Nivel: {riesgo.get('nivel', 'N/A')}")
                    print(f"   Detalles: {riesgo.get('detalles', [])}")
                
            else:
                print(f"❌ Error en la respuesta: {response.status_code}")
                print(f"Respuesta: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Error de conexión. ¿Está ejecutándose el servidor?")
            print("Ejecuta: python main.py")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_endpoint_completo()
