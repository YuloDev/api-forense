#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Endpoint corregido para validar facturas PDF
"""

import os
import sys
import base64
import io
import tempfile
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Usar configuración global de Tesseract
import configurar_tesseract_global

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.pdf_factura_parser import extraer_datos_factura_pdf
from helpers.sri_validator import integrar_validacion_sri
from riesgo import evaluar_riesgo_factura

router = APIRouter()

class PeticionFactura(BaseModel):
    pdfbase64: str

@router.post("/validar-factura")
async def validar_factura(req: PeticionFactura) -> JSONResponse:
    """
    Valida una factura PDF usando análisis inteligente
    """
    try:
        print(f"🔍 Iniciando validación de factura...")
        
        # Decodificar base64
        try:
            archivo_bytes = base64.b64decode(req.pdfbase64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error decodificando base64: {str(e)}")
        
        print(f"✅ PDF decodificado: {len(archivo_bytes)} bytes")
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(archivo_bytes)
            temp_path = temp_file.name
        
        try:
            # 1. Análisis PDF con OCR
            print(f"🔍 Analizando PDF con OCR...")
            t0 = time.perf_counter()

            typeDocumento = "factura"
            
            factura_data = extraer_datos_factura_pdf(archivo_bytes)
            
            t1 = time.perf_counter()
            print(f"✅ Análisis PDF completado en {t1-t0:.2f}s")
            print(f"   RUC: {factura_data.get('ruc', 'No encontrado')}")
            print(f"   Clave Acceso: {factura_data.get('claveAcceso', 'No encontrado')}")
            print(f"   Total: {factura_data.get('total', 'No encontrado')}")
            
            # 2. Validación SRI
            print(f"🔍 Validando SRI...")
            t0 = time.perf_counter()
            
            factura_con_sri = integrar_validacion_sri(factura_data)
            
            t1 = time.perf_counter()
            print(f"✅ Validación SRI completada en {t1-t0:.2f}s")
            
            # Extraer resultados de la validación SRI
            sri_verificado = factura_con_sri.get("sri_verificado", False)
            mensaje_sri = factura_con_sri.get("mensaje", "No disponible")
            
            print(f"   SRI Verificado: {sri_verificado}")
            print(f"   Mensaje: {mensaje_sri}")
            
            # 3. Evaluación de Riesgo
            print(f"🔍 Evaluando riesgo...")
            t0 = time.perf_counter()
            
            riesgo_result = evaluar_riesgo_factura(
                archivo_bytes, 
                factura_data.get('texto_ocr', ''), 
                factura_con_sri, 
                factura_con_sri.get("sri_verificado", False),
                type=typeDocumento
            )
            
            t1 = time.perf_counter()
            print(f"✅ Evaluación de riesgo completada en {t1-t0:.2f}s")
            
            # 4. Función para limpiar datos JSON
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
            factura_con_sri_clean = clean_for_json(factura_con_sri)
            riesgo_result_clean = clean_for_json(riesgo_result)
            
            # 6. Construir respuesta
            print(f"🔍 Construyendo respuesta...")
            
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
            
            print(f"✅ Respuesta construida correctamente")
            print(f"   Claves en respuesta: {list(response.keys())}")
            print(f"   Sección 'factura' presente: {'factura' in response}")
            
            if 'factura' in response:
                factura = response['factura']
                if isinstance(factura, dict):
                    print(f"   ✅ Sección 'factura' es un diccionario con {len(factura)} claves")
                    print(f"   RUC en factura: {factura.get('ruc', 'N/A')}")
                    print(f"   Clave Acceso en factura: {factura.get('claveAcceso', 'N/A')}")
                    print(f"   Total en factura: {factura.get('total', 'N/A')}")
            
            return JSONResponse(content=response)
            
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Error en validar_factura: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")