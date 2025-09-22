#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para debuggear los datos de la factura
"""

import base64
import tempfile
import time
from helpers.pdf_factura_parser import extraer_datos_factura_pdf
from helpers.sri_validator import integrar_validacion_sri

def debug_factura_data():
    """Debuggea los datos de la factura"""
    
    print("🔍 DEBUGGEANDO DATOS DE LA FACTURA")
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
            print(f"   Texto OCR: {len(factura_data.get('texto_ocr', ''))} caracteres")
            
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
            
            # 3. Verificar estructura de factura_con_sri
            print(f"\n📋 ESTRUCTURA DE FACTURA_CON_SRI:")
            print(f"   Tipo: {type(factura_con_sri)}")
            print(f"   Claves: {list(factura_con_sri.keys()) if isinstance(factura_con_sri, dict) else 'No es dict'}")
            
            # 4. Verificar datos específicos
            if isinstance(factura_con_sri, dict):
                print(f"\n📊 DATOS EN FACTURA_CON_SRI:")
                for key, value in factura_con_sri.items():
                    if key in ['ruc', 'razonSocial', 'fechaEmision', 'total', 'claveAcceso']:
                        print(f"   {key}: {value}")
            
            # 5. Función clean_for_json
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
            
            # 6. Aplicar clean_for_json
            print(f"\n🔍 APLICANDO CLEAN_FOR_JSON")
            print("-" * 30)
            
            factura_con_sri_clean = clean_for_json(factura_con_sri)
            
            print(f"📊 DATOS DESPUÉS DE CLEAN_FOR_JSON:")
            print(f"   Tipo: {type(factura_con_sri_clean)}")
            print(f"   Claves: {list(factura_con_sri_clean.keys()) if isinstance(factura_con_sri_clean, dict) else 'No es dict'}")
            
            if isinstance(factura_con_sri_clean, dict):
                print(f"\n📊 DATOS EN FACTURA_CON_SRI_CLEAN:")
                for key, value in factura_con_sri_clean.items():
                    if key in ['ruc', 'razonSocial', 'fechaEmision', 'total', 'claveAcceso']:
                        print(f"   {key}: {value}")
            
            # 7. Verificar si los datos están presentes
            print(f"\n✅ VERIFICACIÓN FINAL:")
            if isinstance(factura_con_sri_clean, dict):
                ruc = factura_con_sri_clean.get('ruc', 'N/A')
                clave_acceso = factura_con_sri_clean.get('claveAcceso', 'N/A')
                total = factura_con_sri_clean.get('total', 'N/A')
                
                if ruc != 'N/A' and clave_acceso != 'N/A':
                    print(f"   ✅ Los datos están presentes en factura_con_sri_clean")
                    print(f"   ✅ RUC: {ruc}")
                    print(f"   ✅ Clave Acceso: {clave_acceso}")
                    print(f"   ✅ Total: {total}")
                else:
                    print(f"   ❌ Los datos NO están presentes en factura_con_sri_clean")
                    print(f"   ❌ RUC: {ruc}")
                    print(f"   ❌ Clave Acceso: {clave_acceso}")
                    print(f"   ❌ Total: {total}")
            else:
                print(f"   ❌ factura_con_sri_clean no es un diccionario")
            
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
    debug_factura_data()
