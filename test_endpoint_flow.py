#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el flujo completo del endpoint validar-factura
"""

import base64
import tempfile
import time
from helpers.pdf_factura_parser import extraer_datos_factura_pdf
from helpers.sri_validator import integrar_validacion_sri
from riesgo import evaluar_riesgo_factura

def test_endpoint_flow():
    """Prueba el flujo completo del endpoint"""
    
    # Leer el PDF de prueba
    pdf_path = "helpers/IMG/Factura_imagen.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            archivo_bytes = f.read()
        
        print(f"✅ PDF leído: {len(archivo_bytes)} bytes")
        
        # Crear archivo temporal (como en el endpoint)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(archivo_bytes)
            temp_path = temp_file.name
        
        print(f"📁 Archivo temporal creado: {temp_path}")
        
        try:
            # 1) Análisis robusto del PDF con OCR y validación SRI
            print("🔍 Analizando PDF con parser robusto...")
            t0 = time.perf_counter()
            
            # Usar el parser robusto que incluye OCR, corrección de errores y validación SRI
            factura_data = extraer_datos_factura_pdf(archivo_bytes)
            
            # Extraer datos principales
            access_key = factura_data.get("claveAcceso")
            ruc = factura_data.get("ruc")
            razon_social = factura_data.get("razonSocial")
            fecha_emision = factura_data.get("fechaEmision")
            numero_factura = factura_data.get("numeroFactura")
            total = factura_data.get("total")
            subtotal_0 = factura_data.get("subtotal_0")
            subtotal_15 = factura_data.get("subtotal_15")
            iva_15 = factura_data.get("iva_15")
            full_text = factura_data.get("texto_ocr", "")
            fuentes = factura_data.get("fuentes", {})
            claves_barcode = fuentes.get("claves_barcode", [])
            
            print(f"✅ PDF analizado con OCR robusto")
            print(f"   RUC: {ruc}")
            print(f"   Razón Social: {razon_social}")
            print(f"   Fecha: {fecha_emision}")
            print(f"   Número: {numero_factura}")
            print(f"   Clave Acceso: {access_key}")
            print(f"   Total: {total}")
            print(f"   Fuente barcode: {fuentes.get('barcode', False)}")
            print(f"   Claves barcode: {claves_barcode}")
            
            t1 = time.perf_counter()
            print(f"⏱️  Tiempo análisis PDF: {t1-t0:.2f}s")
            
            # 2) Validación SRI
            print("🔍 Validando con SRI...")
            t0 = time.perf_counter()
            
            factura_con_sri = integrar_validacion_sri(factura_data)
            
            t1 = time.perf_counter()
            print(f"⏱️  Tiempo validación SRI: {t1-t0:.2f}s")
            
            print(f"✅ Validación SRI completada")
            print(f"   SRI Verificado: {factura_con_sri.get('sri_verificado', False)}")
            print(f"   Mensaje: {factura_con_sri.get('mensaje', 'N/A')}")
            
            # 3) Evaluación de riesgo
            print("🔍 Evaluando riesgo...")
            t0 = time.perf_counter()
            
            riesgo_result = evaluar_riesgo_factura(archivo_bytes, full_text, factura_con_sri, factura_con_sri.get("sri_verificado", False))
            
            t1 = time.perf_counter()
            print(f"⏱️  Tiempo evaluación riesgo: {t1-t0:.2f}s")
            
            print(f"✅ Evaluación de riesgo completada")
            print(f"   Score: {riesgo_result.get('score', 0)}")
            print(f"   Nivel: {riesgo_result.get('nivel', 'N/A')}")
            print(f"   Es Falso Probable: {riesgo_result.get('es_falso_probable', False)}")
            
            # 4) Preparar respuesta final
            print("📋 Preparando respuesta final...")
            
            respuesta = {
                "sri_verificado": factura_con_sri.get("sri_verificado", False),
                "mensaje": factura_con_sri.get("mensaje", "Análisis completado"),
                "tipo_archivo": "PDF",
                "coincidencia": "si" if factura_con_sri.get("sri_verificado", False) else "no",
                "diferencias": factura_con_sri.get("diferencias", {}),
                "diferenciasProductos": factura_con_sri.get("diferenciasProductos", []),
                "resumenProductos": factura_con_sri.get("resumenProductos", {}),
                "factura": factura_con_sri,
                "riesgo": riesgo_result,
                "texto_extraido": full_text[:1000] + "..." if len(full_text) > 1000 else full_text,
                "analisis_detallado": {
                    "metadatos_pdf": {
                        "titulo": "N/A",
                        "autor": "N/A",
                        "creador": "N/A",
                        "productor": "N/A",
                        "fecha_creacion": "N/A",
                        "fecha_modificacion": "N/A"
                    },
                    "fuentes_texto": fuentes,
                    "claves_barcode": claves_barcode
                }
            }
            
            print(f"\n📊 RESULTADO FINAL:")
            print(f"   SRI Verificado: {respuesta['sri_verificado']}")
            print(f"   Mensaje: {respuesta['mensaje']}")
            print(f"   RUC: {respuesta['factura'].get('ruc', 'N/A')}")
            print(f"   Razón Social: {respuesta['factura'].get('razonSocial', 'N/A')}")
            print(f"   Fecha Emisión: {respuesta['factura'].get('fechaEmision', 'N/A')}")
            print(f"   Importe Total: {respuesta['factura'].get('total', 'N/A')}")
            print(f"   Clave Acceso: {respuesta['factura'].get('claveAcceso', 'N/A')}")
            print(f"   Score Riesgo: {respuesta['riesgo'].get('score', 0)}")
            print(f"   Nivel Riesgo: {respuesta['riesgo'].get('nivel', 'N/A')}")
            
        finally:
            # Limpiar archivo temporal
            import os
            try:
                os.unlink(temp_path)
                print(f"🗑️  Archivo temporal eliminado: {temp_path}")
            except:
                pass
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_endpoint_flow()
