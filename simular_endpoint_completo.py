#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para simular el endpoint completo
"""

import base64
import tempfile
import time
import json
from helpers.pdf_factura_parser import extraer_datos_factura_pdf
from helpers.sri_validator import integrar_validacion_sri
from riesgo import evaluar_riesgo_factura

def simular_endpoint_completo():
    """Simula el endpoint completo"""
    
    print("🎯 SIMULANDO ENDPOINT COMPLETO")
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
            # 1. Análisis PDF con OCR
            print("\n🔍 ANÁLISIS PDF CON OCR")
            print("-" * 30)
            t0 = time.perf_counter()
            
            factura_data = extraer_datos_factura_pdf(archivo_bytes)
            
            t1 = time.perf_counter()
            print(f"⏱️ Tiempo: {t1-t0:.2f}s")
            
            # Mostrar datos extraídos
            print(f"📊 DATOS EXTRAÍDOS:")
            print(f"   RUC: {factura_data.get('ruc', 'No encontrado')}")
            print(f"   Razón Social: {factura_data.get('razonSocial', 'No encontrado')}")
            print(f"   Fecha Emisión: {factura_data.get('fechaEmision', 'No encontrado')}")
            print(f"   Número Factura: {factura_data.get('numeroFactura', 'No encontrado')}")
            print(f"   Clave Acceso: {factura_data.get('claveAcceso', 'No encontrado')}")
            print(f"   Total: {factura_data.get('total', 'No encontrado')}")
            
            # 2. Validación SRI
            print("\n🔍 VALIDACIÓN SRI")
            print("-" * 30)
            t0 = time.perf_counter()
            
            factura_con_sri = integrar_validacion_sri(factura_data)
            
            t1 = time.perf_counter()
            print(f"⏱️ Tiempo: {t1-t0:.2f}s")
            
            print(f"📊 RESULTADO SRI:")
            print(f"   SRI Verificado: {factura_con_sri.get('sri_verificado', False)}")
            print(f"   Mensaje: {factura_con_sri.get('mensaje', 'N/A')}")
            
            # 3. Evaluación de Riesgo
            print("\n🔍 EVALUACIÓN DE RIESGO")
            print("-" * 30)
            t0 = time.perf_counter()
            
            riesgo_result = evaluar_riesgo_factura(
                archivo_bytes, 
                factura_data.get('texto_ocr', ''), 
                factura_con_sri, 
                factura_con_sri.get("sri_verificado", False)
            )
            
            t1 = time.perf_counter()
            print(f"⏱️ Tiempo: {t1-t0:.2f}s")
            
            print(f"📊 RESULTADO RIESGO:")
            print(f"   Score: {riesgo_result.get('score', 0)}")
            print(f"   Nivel: {riesgo_result.get('nivel', 'N/A')}")
            print(f"   Es Falso Probable: {riesgo_result.get('es_falso_probable', False)}")
            
            # 4. Función clean_for_json (copiada del endpoint)
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
            
            # 5. Limpiar datos
            print(f"\n🔍 LIMPIANDO DATOS")
            print("-" * 30)
            
            factura_con_sri_clean = clean_for_json(factura_con_sri)
            riesgo_result_clean = clean_for_json(riesgo_result)
            
            # 6. Construir respuesta (simulando el endpoint)
            print(f"\n🔍 CONSTRUYENDO RESPUESTA")
            print("-" * 30)
            
            response = {
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
            
            # 7. Verificar respuesta
            print(f"\n📊 RESPUESTA CONSTRUIDA:")
            print(f"   SRI Verificado: {response.get('sri_verificado', 'N/A')}")
            print(f"   Mensaje: {response.get('mensaje', 'N/A')}")
            print(f"   Tipo Archivo: {response.get('tipo_archivo', 'N/A')}")
            
            # Verificar sección factura
            factura = response.get('factura', {})
            print(f"\n📋 SECCIÓN FACTURA:")
            print(f"   Tipo: {type(factura)}")
            print(f"   Claves: {list(factura.keys()) if isinstance(factura, dict) else 'No es dict'}")
            
            if isinstance(factura, dict):
                print(f"   RUC: {factura.get('ruc', 'N/A')}")
                print(f"   Razón Social: {factura.get('razonSocial', 'N/A')}")
                print(f"   Fecha Emisión: {factura.get('fechaEmision', 'N/A')}")
                print(f"   Importe Total: {factura.get('total', 'N/A')}")
                print(f"   Clave Acceso: {factura.get('claveAcceso', 'N/A')}")
            
            # 8. Guardar respuesta
            with open("respuesta_simulada.json", "w", encoding="utf-8") as f:
                json.dump(response, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Respuesta simulada guardada en: respuesta_simulada.json")
            
            # 9. Verificar si los datos están presentes
            print(f"\n✅ VERIFICACIÓN FINAL:")
            if isinstance(factura, dict):
                ruc = factura.get('ruc', 'N/A')
                clave_acceso = factura.get('claveAcceso', 'N/A')
                total = factura.get('total', 'N/A')
                
                if ruc != 'N/A' and clave_acceso != 'N/A':
                    print(f"   ✅ Los datos están presentes en la respuesta")
                    print(f"   ✅ RUC: {ruc}")
                    print(f"   ✅ Clave Acceso: {clave_acceso}")
                    print(f"   ✅ Total: {total}")
                else:
                    print(f"   ❌ Los datos NO están presentes en la respuesta")
                    print(f"   ❌ RUC: {ruc}")
                    print(f"   ❌ Clave Acceso: {clave_acceso}")
                    print(f"   ❌ Total: {total}")
            else:
                print(f"   ❌ La sección factura no es un diccionario")
            
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
    simular_endpoint_completo()
