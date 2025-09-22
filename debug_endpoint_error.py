#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para debuggear errores en el endpoint
"""

import base64
import tempfile
import time
import json
import traceback
from helpers.pdf_factura_parser import extraer_datos_factura_pdf
from helpers.sri_validator import integrar_validacion_sri
from riesgo import evaluar_riesgo_factura

def debug_endpoint_error():
    """Debuggea errores en el endpoint"""
    
    print("🔍 DEBUGGEANDO ERRORES EN EL ENDPOINT")
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
            # Simular el endpoint paso a paso
            print("\n🔍 PASO 1: ANÁLISIS PDF CON OCR")
            print("-" * 30)
            
            try:
                factura_data = extraer_datos_factura_pdf(archivo_bytes)
                print(f"✅ Análisis PDF exitoso")
                print(f"   RUC: {factura_data.get('ruc', 'No encontrado')}")
                print(f"   Clave Acceso: {factura_data.get('claveAcceso', 'No encontrado')}")
                print(f"   Total: {factura_data.get('total', 'No encontrado')}")
            except Exception as e:
                print(f"❌ Error en análisis PDF: {e}")
                traceback.print_exc()
                return
            
            print("\n🔍 PASO 2: VALIDACIÓN SRI")
            print("-" * 30)
            
            try:
                factura_con_sri = integrar_validacion_sri(factura_data)
                print(f"✅ Validación SRI exitosa")
                print(f"   SRI Verificado: {factura_con_sri.get('sri_verificado', False)}")
                print(f"   Mensaje: {factura_con_sri.get('mensaje', 'N/A')}")
            except Exception as e:
                print(f"❌ Error en validación SRI: {e}")
                traceback.print_exc()
                return
            
            print("\n🔍 PASO 3: EVALUACIÓN DE RIESGO")
            print("-" * 30)
            
            try:
                riesgo_result = evaluar_riesgo_factura(
                    archivo_bytes, 
                    factura_data.get('texto_ocr', ''), 
                    factura_con_sri, 
                    factura_con_sri.get("sri_verificado", False)
                )
                print(f"✅ Evaluación de riesgo exitosa")
                print(f"   Score: {riesgo_result.get('score', 0)}")
                print(f"   Nivel: {riesgo_result.get('nivel', 'N/A')}")
            except Exception as e:
                print(f"❌ Error en evaluación de riesgo: {e}")
                traceback.print_exc()
                return
            
            print("\n🔍 PASO 4: FUNCIÓN CLEAN_FOR_JSON")
            print("-" * 30)
            
            def clean_for_json(obj):
                """Función recursiva para limpiar datos y hacerlos serializables a JSON"""
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
            
            try:
                factura_con_sri_clean = clean_for_json(factura_con_sri)
                riesgo_result_clean = clean_for_json(riesgo_result)
                print(f"✅ Limpieza de datos exitosa")
                print(f"   factura_con_sri_clean tipo: {type(factura_con_sri_clean)}")
                print(f"   riesgo_result_clean tipo: {type(riesgo_result_clean)}")
            except Exception as e:
                print(f"❌ Error en limpieza de datos: {e}")
                traceback.print_exc()
                return
            
            print("\n🔍 PASO 5: CONSTRUCCIÓN DE RESPUESTA")
            print("-" * 30)
            
            try:
                # Extraer variables necesarias
                sri_verificado = factura_con_sri.get("sri_verificado", False)
                mensaje_sri = factura_con_sri.get("mensaje", "No disponible")
                
                # Construir respuesta
                response = {
                    "sri_verificado": sri_verificado,
                    "mensaje": mensaje_sri,
                    "tipo_archivo": "PDF",
                    "coincidencia": "si" if sri_verificado else "no",
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
                
                print(f"✅ Construcción de respuesta exitosa")
                print(f"   Claves en respuesta: {list(response.keys())}")
                
                # Verificar sección factura
                if 'factura' in response:
                    print(f"   ✅ Sección 'factura' presente")
                    factura = response['factura']
                    if isinstance(factura, dict):
                        print(f"   ✅ Sección 'factura' es un diccionario")
                        print(f"   ✅ Claves en 'factura': {list(factura.keys())}")
                        
                        # Verificar datos específicos
                        ruc = factura.get('ruc', 'N/A')
                        clave_acceso = factura.get('claveAcceso', 'N/A')
                        total = factura.get('total', 'N/A')
                        
                        print(f"   ✅ RUC: {ruc}")
                        print(f"   ✅ Clave Acceso: {clave_acceso}")
                        print(f"   ✅ Total: {total}")
                    else:
                        print(f"   ❌ Sección 'factura' no es un diccionario: {type(factura)}")
                else:
                    print(f"   ❌ Sección 'factura' NO presente")
                
                # Guardar respuesta
                with open("respuesta_debug_endpoint.json", "w", encoding="utf-8") as f:
                    json.dump(response, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Respuesta guardada en: respuesta_debug_endpoint.json")
                
            except Exception as e:
                print(f"❌ Error en construcción de respuesta: {e}")
                traceback.print_exc()
                return
            
            print("\n✅ DEBUG COMPLETADO")
            print("   El endpoint debería funcionar correctamente")
            print("   Todos los pasos se ejecutaron sin errores")
            
        finally:
            # Limpiar archivo temporal
            import os
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_endpoint_error()
