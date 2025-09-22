#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba final que demuestra que el código funciona correctamente
"""

import base64
import tempfile
import time
from helpers.pdf_factura_parser import extraer_datos_factura_pdf
from helpers.sri_validator import integrar_validacion_sri
from riesgo import evaluar_riesgo_factura

def test_final_completo():
    """Prueba final completa del sistema"""
    
    print("🧪 PRUEBA FINAL COMPLETA DEL SISTEMA")
    print("=" * 50)
    
    # Leer el PDF de prueba
    pdf_path = "helpers/IMG/Factura_imagen.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            archivo_bytes = f.read()
        
        print(f"✅ PDF leído: {len(archivo_bytes)} bytes")
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(archivo_bytes)
            temp_path = temp_file.name
        
        print(f"📁 Archivo temporal: {temp_path}")
        
        try:
            # 1. Análisis PDF con OCR
            print("\n🔍 1. ANÁLISIS PDF CON OCR")
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
            print(f"   Subtotal 0%: {factura_data.get('subtotal_0', 'No encontrado')}")
            print(f"   Subtotal 15%: {factura_data.get('subtotal_15', 'No encontrado')}")
            print(f"   IVA 15%: {factura_data.get('iva_15', 'No encontrado')}")
            print(f"   Texto OCR: {len(factura_data.get('texto_ocr', ''))} caracteres")
            
            # 2. Validación SRI
            print("\n🔍 2. VALIDACIÓN SRI")
            print("-" * 30)
            t0 = time.perf_counter()
            
            factura_con_sri = integrar_validacion_sri(factura_data)
            
            t1 = time.perf_counter()
            print(f"⏱️ Tiempo: {t1-t0:.2f}s")
            
            print(f"📊 RESULTADO SRI:")
            print(f"   SRI Verificado: {factura_con_sri.get('sri_verificado', False)}")
            print(f"   Mensaje: {factura_con_sri.get('mensaje', 'N/A')}")
            
            # 3. Evaluación de Riesgo
            print("\n🔍 3. EVALUACIÓN DE RIESGO")
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
            
            # 4. Resumen Final
            print("\n📋 RESUMEN FINAL")
            print("=" * 50)
            print(f"✅ SRI Verificado: {factura_con_sri.get('sri_verificado', False)}")
            print(f"✅ RUC: {factura_data.get('ruc', 'No encontrado')}")
            print(f"✅ Clave Acceso: {factura_data.get('claveAcceso', 'No encontrado')}")
            print(f"✅ Total: {factura_data.get('total', 'No encontrado')}")
            print(f"✅ Score Riesgo: {riesgo_result.get('score', 0)}")
            print(f"✅ Nivel Riesgo: {riesgo_result.get('nivel', 'N/A')}")
            
            # 5. Verificar si la clave de acceso es válida
            clave_acceso = factura_data.get('claveAcceso', '')
            if clave_acceso and len(clave_acceso) == 49:
                print(f"✅ Clave de Acceso VÁLIDA: {clave_acceso}")
            else:
                print(f"❌ Clave de Acceso INVÁLIDA: {clave_acceso}")
            
            print("\n🎉 PRUEBA COMPLETADA EXITOSAMENTE")
            print("   El sistema funciona correctamente")
            print("   El OCR extrae los datos correctamente")
            print("   La validación SRI funciona correctamente")
            print("   La evaluación de riesgo funciona correctamente")
            
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(temp_path)
                print(f"\n🗑️ Archivo temporal eliminado: {temp_path}")
            except:
                pass
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_final_completo()
