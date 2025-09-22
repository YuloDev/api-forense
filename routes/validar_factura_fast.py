#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Endpoint RÁPIDO para validar facturas PDF (nativas y escaneadas)
Versión optimizada que evita OCR lento cuando no es necesario
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

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF
from helpers.sri_validator import integrar_validacion_sri

router = APIRouter()

class PeticionFactura(BaseModel):
    pdfbase64: str

def extraer_texto_pdf_rapido(archivo_bytes: bytes) -> str:
    """Extrae texto del PDF de forma rápida, con OCR si es necesario"""
    try:
        doc = fitz.open(stream=archivo_bytes, filetype="pdf")
        texto_completo = ""
        
        # Primero intentar extracción nativa
        for page_num in range(doc.page_count):
            page = doc[page_num]
            texto_pagina = page.get_text()
            texto_completo += texto_pagina + "\n"
        
        doc.close()
        
        # Si el texto es muy corto (menos de 100 caracteres), probablemente es una imagen escaneada
        if len(texto_completo.strip()) < 100:
            print("📄 PDF parece ser imagen escaneada, usando OCR...")
            try:
                import pytesseract
                from PIL import Image
                import io
                
                # Convertir PDF a imagen y usar OCR
                doc = fitz.open(stream=archivo_bytes, filetype="pdf")
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    # Convertir página a imagen
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom para mejor OCR
                    img_data = pix.tobytes("png")
                    
                    # Usar OCR en la imagen
                    img = Image.open(io.BytesIO(img_data))
                    texto_ocr = pytesseract.image_to_string(img, lang='spa+eng')
                    texto_completo += texto_ocr + "\n"
                
                doc.close()
                print(f"✅ OCR completado: {len(texto_completo)} caracteres extraídos")
                
            except ImportError:
                print("⚠️ pytesseract no disponible, usando texto nativo")
            except Exception as e:
                print(f"⚠️ Error en OCR: {e}, usando texto nativo")
        
        return texto_completo
    except Exception as e:
        print(f"Error extrayendo texto PDF: {e}")
        return ""

def extraer_datos_factura_rapido(texto: str) -> Dict[str, Any]:
    """Extrae datos básicos de la factura del texto extraído"""
    
    # Patrones para extraer información básica
    patrones = {
        "ruc": [
            r"RUC[:\s]*(\d{13})",
            r"R\.U\.C[:\s]*(\d{13})",
            r"(\d{13})",
        ],
        "razonSocial": [
            r"Razón Social[:\s]*([^\n]+)",
            r"Razon Social[:\s]*([^\n]+)",
            r"Empresa[:\s]*([^\n]+)",
        ],
        "fechaEmision": [
            r"Fecha[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"Emisión[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        ],
        "importeTotal": [
            r"Total[:\s]*\$?(\d+[.,]\d{2})",
            r"Importe Total[:\s]*\$?(\d+[.,]\d{2})",
            r"Valor Total[:\s]*\$?(\d+[.,]\d{2})",
        ],
        "claveAcceso": [
            r"Clave de Acceso[:\s]*(\d{49})",
            r"Clave Acceso[:\s]*(\d{49})",
            r"(\d{49})",
        ]
    }
    
    datos = {}
    
    # Extraer cada campo
    for campo, patrones_campo in patrones.items():
        for patron in patrones_campo:
            import re
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                valor = match.group(1).strip()
                if campo == "importeTotal":
                    # Limpiar y convertir a float
                    valor_limpio = re.sub(r'[^\d.,]', '', valor)
                    valor_limpio = valor_limpio.replace(',', '.')
                    try:
                        datos[campo] = float(valor_limpio)
                    except:
                        pass
                else:
                    datos[campo] = valor
                break
    
    return datos

@router.post("/validar-factura-fast")
async def validar_factura_fast(req: PeticionFactura) -> JSONResponse:
    """
    Valida una factura PDF de forma RÁPIDA (sin OCR lento)
    Acepta solo archivo PDF en base64
    """
    try:
        print("🚀 Iniciando validación rápida de factura...")
        start_time = time.time()
        
        # Decodificar base64
        try:
            archivo_bytes = base64.b64decode(req.pdfbase64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error decodificando base64: {str(e)}")
        
        print(f"✅ PDF decodificado: {len(archivo_bytes)} bytes")
        
        # 1) Extraer texto del PDF (rápido, sin OCR)
        print("🔍 Extrayendo texto del PDF...")
        t0 = time.perf_counter()
        texto_completo = extraer_texto_pdf_rapido(archivo_bytes)
        t1 = time.perf_counter()
        print(f"✅ Texto extraído en {t1-t0:.2f}s: {len(texto_completo)} caracteres")
        
        # 2) Extraer datos básicos de la factura
        print("🔍 Extrayendo datos de la factura...")
        t0 = time.perf_counter()
        datos_factura = extraer_datos_factura_rapido(texto_completo)
        t1 = time.perf_counter()
        print(f"✅ Datos extraídos en {t1-t0:.2f}s")
        
        # Mostrar datos extraídos
        print(f"📋 Datos extraídos:")
        print(f"   RUC: {datos_factura.get('ruc', 'No encontrado')}")
        print(f"   Razón Social: {datos_factura.get('razonSocial', 'No encontrado')}")
        print(f"   Fecha: {datos_factura.get('fechaEmision', 'No encontrada')}")
        print(f"   Total: {datos_factura.get('importeTotal', 'No encontrado')}")
        print(f"   Clave Acceso: {datos_factura.get('claveAcceso', 'No encontrada')}")
        
        # 3) Preparar datos para validación SRI
        factura_data = {
            "ruc": datos_factura.get("ruc"),
            "razonSocial": datos_factura.get("razonSocial"),
            "fechaEmision": datos_factura.get("fechaEmision"),
            "importeTotal": datos_factura.get("importeTotal"),
            "claveAcceso": datos_factura.get("claveAcceso"),
            "detalles": [],
            "totals": {
                "subtotal15": None,
                "subtotal0": None,
                "subtotal_no_objeto": None,
                "subtotal_sin_impuestos": None,
                "descuento": None,
                "iva15": None,
                "total": datos_factura.get("importeTotal")
            },
            "barcodes": [],
            "financial_checks": {},
            "metadata": {
                "invoice_number": None,
                "authorization": datos_factura.get("claveAcceso"),
                "environment": "PRODUCCION" if datos_factura.get("claveAcceso") and len(datos_factura.get("claveAcceso", "")) > 23 and datos_factura.get("claveAcceso")[23] == "1" else "PRUEBAS",
                "buyer_id": None,
                "emitter_name": datos_factura.get("razonSocial"),
                "file_metadata": {
                    "sha256": None,
                    "pages_processed": 1,
                    "text_methods": ["pdf_native"],
                    "text_length": len(texto_completo)
                }
            }
        }
        
        # 4) Validación SRI
        print("🔍 Validando con SRI...")
        t0 = time.perf_counter()
        factura_con_sri = integrar_validacion_sri(factura_data)
        t1 = time.perf_counter()
        print(f"✅ Validación SRI completada en {t1-t0:.2f}s")
        
        # Extraer resultados
        sri_verificado = factura_con_sri.get("sri_verificado", False)
        mensaje_sri = factura_con_sri.get("mensaje", "No disponible")
        
        print(f"📊 Resultado SRI: {sri_verificado}")
        print(f"   Mensaje: {mensaje_sri}")
        
        # 5) Análisis de riesgo básico
        riesgo_result = {
            "nivel_riesgo": "BAJO" if sri_verificado else "ALTO",
            "puntuacion": 0 if sri_verificado else 50,
            "grado_confianza": "ALTO" if sri_verificado else "BAJO",
            "porcentaje_confianza": 100.0 if sri_verificado else 30.0,
            "prioritarias": [],
            "secundarias": [],
            "adicionales": []
        }
        
        # Agregar check de SRI
        if not sri_verificado:
            riesgo_result["prioritarias"].append({
                "check": "Validación SRI",
                "detalle": {
                    "sri_verificado": sri_verificado,
                    "clave_acceso": datos_factura.get("claveAcceso"),
                    "interpretacion": "Factura no validada con SRI - posible documento falso",
                    "posibles_causas": [
                        "Documento no autorizado por SRI",
                        "Clave de acceso inválida o corrupta",
                        "Documento modificado después de autorización",
                        "Error en extracción de datos",
                        "Documento de prueba o borrador"
                    ],
                    "recomendacion": "Documento no validado con SRI - alto riesgo de falsificación"
                },
                "penalizacion": 50
            })
        
        # 6) Construir respuesta
        total_time = time.time() - start_time
        print(f"✅ Validación completada en {total_time:.2f}s")
        
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
            "factura": factura_con_sri,
            "clave_acceso_parseada": {},
            "riesgo": riesgo_result,
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
                "analisis_sri": {
                    "es_documento_sri": bool(datos_factura.get("claveAcceso")),
                    "clave_acceso": datos_factura.get("claveAcceso"),
                    "clave_valida": sri_verificado,
                    "longitud_correcta": len(datos_factura.get("claveAcceso", "")) == 49,
                    "metodo_extraccion": "pdf_native"
                },
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
            },
            "texto_extraido": texto_completo[:1000] + "..." if len(texto_completo) > 1000 else texto_completo,
            "tiempo_procesamiento": total_time,
            "metodo_extraccion": "pdf_native_fast"
        }
        
        return JSONResponse(status_code=200, content=response)
        
    except Exception as e:
        print(f"❌ Error en validación: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
