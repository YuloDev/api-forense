#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para comparar el endpoint vs el servidor
"""

import base64
import tempfile
import time
import json
import requests
from helpers.pdf_factura_parser import extraer_datos_factura_pdf
from helpers.sri_validator import integrar_validacion_sri
from riesgo import evaluar_riesgo_factura

def comparar_endpoint_vs_servidor():
    """Compara el endpoint vs el servidor"""
    
    print("🔍 COMPARANDO ENDPOINT VS SERVIDOR")
    print("=" * 50)
    
    # Leer PDF de prueba
    pdf_path = "helpers/IMG/Factura_imagen.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            archivo_bytes = f.read()
        
        print(f"✅ PDF leído: {len(archivo_bytes)} bytes")
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(archivo_bytes)
            temp_path = temp_file.name
        
        try:
            # 1. Simular endpoint localmente
            print("\n🔍 SIMULANDO ENDPOINT LOCALMENTE")
            print("-" * 30)
            
            # Análisis PDF con OCR
            factura_data = extraer_datos_factura_pdf(archivo_bytes)
            
            # Validación SRI
            factura_con_sri = integrar_validacion_sri(factura_data)
            
            # Evaluación de Riesgo
            riesgo_result = evaluar_riesgo_factura(
                archivo_bytes, 
                factura_data.get('texto_ocr', ''), 
                factura_con_sri, 
                factura_con_sri.get("sri_verificado", False)
            )
            
            # Función clean_for_json
            def clean_for_json(obj):
                if isinstance(obj, dict):
                    return {k: clean_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_for_json(item) for item in obj]
                elif isinstance(obj, bytes):
                    try:
                        return obj.decode('utf-8')
                    except UnicodeDecodeError:
                        return base64.b64encode(obj).decode('utf-8')
                elif isinstance(obj, (str, int, float, bool, type(None))):
                    return obj
                else:
                    return str(obj)
            
            # Limpiar datos
            factura_con_sri_clean = clean_for_json(factura_con_sri)
            riesgo_result_clean = clean_for_json(riesgo_result)
            
            # Construir respuesta local
            response_local = {
                "sri_verificado": factura_con_sri.get("sri_verificado", False),
                "mensaje": factura_con_sri.get("mensaje", "No disponible"),
                "tipo_archivo": "PDF",
                "coincidencia": "si" if factura_con_sri.get("sri_verificado", False) else "no",
                "diferencias": {},
                "diferenciasProductos": [],
                "resumenProductos": {
                    "num_sri": 0,
                    "num_imagen": 0,
                    "total_sri_items": 0,
                    "total_imagen_items": 0
                },
                "factura": factura_con_sri_clean,
                "clave_acceso_parseada": {},
                "riesgo": riesgo_result_clean,
                "validacion_firmas": {
                    "resumen": {
                        "total_firmas": 0,
                        "firmas_validas": 0,
                        "firmas_invalidas": 0,
                        "con_certificados": 0,
                        "con_timestamps": 0,
                        "con_politicas": 0,
                        "porcentaje_validas": 0
                    },
                    "dependencias": {
                        "asn1crypto": False,
                        "oscrypto": False,
                        "certvalidator": False
                    },
                    "analisis_sri": {},
                    "validacion_pdf": {
                        "firma_detectada": False,
                        "tipo_firma": "ninguna",
                        "es_pades": False,
                        "metadatos": {
                            "numero_firmas": 0
                        }
                    },
                    "tipo_documento": "pdf",
                    "firma_detectada": False
                }
            }
            
            print(f"📊 RESPUESTA LOCAL:")
            print(f"   SRI Verificado: {response_local.get('sri_verificado', 'N/A')}")
            print(f"   Mensaje: {response_local.get('mensaje', 'N/A')}")
            print(f"   Claves: {list(response_local.keys())}")
            
            # Verificar sección factura local
            factura_local = response_local.get('factura', {})
            print(f"\n📋 SECCIÓN FACTURA LOCAL:")
            print(f"   Tipo: {type(factura_local)}")
            print(f"   Claves: {list(factura_local.keys()) if isinstance(factura_local, dict) else 'No es dict'}")
            
            if isinstance(factura_local, dict):
                print(f"   RUC: {factura_local.get('ruc', 'N/A')}")
                print(f"   Clave Acceso: {factura_local.get('claveAcceso', 'N/A')}")
                print(f"   Total: {factura_local.get('total', 'N/A')}")
            
            # 2. Probar servidor
            print("\n🔍 PROBANDO SERVIDOR")
            print("-" * 30)
            
            # Convertir a base64
            pdf_base64 = base64.b64encode(archivo_bytes).decode('utf-8')
            payload = {"pdfbase64": pdf_base64}
            
            try:
                response_server = requests.post(
                    "http://localhost:8001/validar-factura",
                    json=payload,
                    timeout=30
                )
                
                if response_server.status_code == 200:
                    data_server = response_server.json()
                    
                    print(f"📊 RESPUESTA SERVIDOR:")
                    print(f"   SRI Verificado: {data_server.get('sri_verificado', 'N/A')}")
                    print(f"   Mensaje: {data_server.get('mensaje', 'N/A')}")
                    print(f"   Claves: {list(data_server.keys())}")
                    
                    # Verificar sección factura servidor
                    factura_server = data_server.get('factura', {})
                    print(f"\n📋 SECCIÓN FACTURA SERVIDOR:")
                    print(f"   Tipo: {type(factura_server)}")
                    print(f"   Claves: {list(factura_server.keys()) if isinstance(factura_server, dict) else 'No es dict'}")
                    
                    if isinstance(factura_server, dict):
                        print(f"   RUC: {factura_server.get('ruc', 'N/A')}")
                        print(f"   Clave Acceso: {factura_server.get('claveAcceso', 'N/A')}")
                        print(f"   Total: {factura_server.get('total', 'N/A')}")
                    else:
                        print(f"   ❌ Sección 'factura' NO presente en servidor")
                    
                    # 3. Comparar respuestas
                    print(f"\n🔍 COMPARACIÓN:")
                    print(f"   Local tiene 'factura': {'factura' in response_local}")
                    print(f"   Servidor tiene 'factura': {'factura' in data_server}")
                    
                    if 'factura' in response_local and 'factura' in data_server:
                        print(f"   ✅ Ambos tienen sección 'factura'")
                    elif 'factura' in response_local and 'factura' not in data_server:
                        print(f"   ❌ Solo local tiene sección 'factura'")
                        print(f"   ❌ Servidor NO tiene sección 'factura'")
                    elif 'factura' not in response_local and 'factura' in data_server:
                        print(f"   ❌ Solo servidor tiene sección 'factura'")
                        print(f"   ❌ Local NO tiene sección 'factura'")
                    else:
                        print(f"   ❌ Ninguno tiene sección 'factura'")
                    
                    # Guardar respuestas
                    with open("respuesta_local.json", "w", encoding="utf-8") as f:
                        json.dump(response_local, f, indent=2, ensure_ascii=False)
                    
                    with open("respuesta_servidor.json", "w", encoding="utf-8") as f:
                        json.dump(data_server, f, indent=2, ensure_ascii=False)
                    
                    print(f"\n💾 Respuestas guardadas:")
                    print(f"   - respuesta_local.json")
                    print(f"   - respuesta_servidor.json")
                    
                else:
                    print(f"❌ Error del servidor: {response_server.status_code}")
                    print(f"   Respuesta: {response_server.text}")
                    
            except requests.exceptions.ConnectionError:
                print(f"❌ Error de conexión: El servidor no está ejecutándose")
            except requests.exceptions.Timeout:
                print(f"❌ Timeout: El servidor tardó más de 30 segundos")
            except Exception as e:
                print(f"❌ Error: {e}")
            
        finally:
            # Limpiar archivo temporal
            import os
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    comparar_endpoint_vs_servidor()
