import base64
import io
import re
import time
import json
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pdfminer.high_level import extract_text
from difflib import SequenceMatcher
import requests

from config import (
    MAX_PDF_BYTES,
    SRI_TIMEOUT,
    PRICE_EPS,
    QTY_EPS,
    TOTAL_EPS,
    MATCH_THRESHOLD,
)
from utils import log_step, normalize_comprobante_xml, strip_accents, _to_float
from pdf_extract import extract_clave_acceso_from_text, extract_invoice_fields_from_text
from helpers.type_conversion import safe_serialize_dict
from helpers.firma_digital import analizar_firmas_digitales_avanzado
from helpers.validacion_firma_digital import detectar_firmas_pdf_simple
from helpers.deteccion_firma_simple import detectar_firma_desde_base64
from routes.validacion_firma_universal import _extraer_numero_autorizacion_pdf
from helpers.analisis_sri_ride import analizar_documento_sri
from helpers.validacion_xades import validar_xades
from sri import sri_autorizacion_por_clave, parse_autorizacion_response

# Funciones para validación SRI (copiadas del endpoint universal)
async def _comparar_valores_totales_pdf_xml(pdf_bytes: bytes, xml_content: str) -> Dict[str, Any]:
    """Compara los valores totales entre PDF y XML del SRI"""
    
    try:
        # Extraer valor del PDF
        valor_pdf_result = _extraer_valor_total_pdf(pdf_bytes)
        valor_pdf = valor_pdf_result.get("valor_total", 0)
        
        # Extraer valor del XML
        valor_xml_result = _extraer_valor_total_xml(xml_content)
        valor_xml = valor_xml_result.get("valor_total", 0)
        
        # Calcular diferencia
        diferencia = abs(valor_pdf - valor_xml)
        porcentaje_diferencia = (diferencia / valor_xml * 100) if valor_xml > 0 else 0
        valores_coinciden = diferencia < 0.01  # Tolerancia de 1 centavo
        
        return {
            "valores_coinciden": valores_coinciden,
            "valor_pdf": valor_pdf,
            "valor_xml": valor_xml,
            "diferencia": diferencia,
            "porcentaje_diferencia": porcentaje_diferencia,
            "detalles_pdf": valor_pdf_result,
            "detalles_xml": valor_xml_result,
            "validacion": "EXITOSA" if valores_coinciden else "FALLO"
        }
        
    except Exception as e:
        return {
            "valores_coinciden": False,
            "error": f"Error comparando valores: {str(e)}",
            "validacion": "ERROR"
        }

def _extraer_valor_total_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extrae el valor total de la factura desde el PDF usando lógica robusta con análisis espacial"""
    
    try:
        import fitz
        
        # Abrir PDF desde bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Etiquetas para buscar
        LABELS = [
            "VALOR TOTAL", "IMPORTE TOTAL", "TOTAL A PAGAR", "TOTAL GENERAL",
            "VALOR TO", "IMPORTE TO", "TOTAL TO", "VALOR T", "IMPORTE T"
        ]
        
        # Patrones de números
        NUM_RE = re.compile(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)')
        
        def clean_amount(text):
            """Limpia y convierte texto de cantidad a float"""
            if not text:
                return None
            # Reemplazar comas por puntos para decimales
            cleaned = re.sub(r'(\d),(\d{2})$', r'\1.\2', text)
            # Remover comas de miles
            cleaned = re.sub(r'(\d),(\d{3})', r'\1\2', cleaned)
            try:
                return float(cleaned)
            except:
                return None
        
        def from_xml_embedded():
            """Buscar en XMLs embebidos"""
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Buscar objetos que puedan ser XML
                for obj in page.get_contents():
                    if obj:
                        try:
                            content = obj.decode('utf-8', errors='ignore')
                            if 'importeTotal' in content or 'totalConImpuestos' in content:
                                # Buscar patrones de total
                                matches = re.findall(r'<importeTotal>([^<]+)</importeTotal>', content)
                                if matches:
                                    val = clean_amount(matches[0])
                                    if val and val >= 100:  # Mínimo $100
                                        return val
                        except:
                            continue
            return None
        
        def lines():
            """Obtener líneas de texto con coordenadas"""
            all_lines = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                words = page.get_text("words")
                for word in words:
                    x0, y0, x1, y1, text = word[:5]
                    all_lines.append({
                        'text': text,
                        'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                        'page': page_num
                    })
            return all_lines
        
        def match_label(line_text, labels):
            """Encuentra la mejor coincidencia de etiqueta"""
            line_upper = line_text.upper()
            for label in labels:
                if label in line_upper:
                    return label
            return None
        
        def get_label_priority(label):
            """Asigna prioridad a las etiquetas"""
            if label in ["VALOR TOTAL", "IMPORTE TOTAL"]:
                return 100
            elif label in ["TOTAL A PAGAR", "TOTAL GENERAL"]:
                return 90
            elif label in ["VALOR TO", "IMPORTE TO", "TOTAL TO"]:
                return 80
            elif label in ["VALOR T", "IMPORTE T"]:
                return 70
            else:
                return 50
        
        def rightmost_amount(lines, label_line, tolerance=5):
            """Encuentra el número más a la derecha en la misma línea horizontal"""
            y_center = (label_line['y0'] + label_line['y1']) / 2
            candidates = []
            
            for line in lines:
                line_y_center = (line['y0'] + line['y1']) / 2
                if abs(line_y_center - y_center) <= tolerance:
                    # Buscar números en esta línea
                    numbers = NUM_RE.findall(line['text'])
                    for num_text in numbers:
                        val = clean_amount(num_text)
                        if val and val >= 100:  # Mínimo $100
                            candidates.append({
                                'valor': val,
                                'texto_linea': line['text'],
                                'x': line['x0'],
                                'metodo': 'busqueda_espacial'
                            })
            
            if candidates:
                # Ordenar por posición X (más a la derecha primero)
                candidates.sort(key=lambda x: x['x'], reverse=True)
                return candidates[0]
            return None
        
        # 1. Buscar en XML embebido
        valor_xml = from_xml_embedded()
        if valor_xml:
            return {
                "valor_total": valor_xml,
                "metodo": "xml_embebido",
                "valores_encontrados": [{"valor": valor_xml, "metodo": "xml_embebido"}],
                "total_encontrados": 1,
                "texto_extraido": f"Valor encontrado en XML embebido: {valor_xml}"
            }
        
        # 2. Análisis espacial
        all_lines = lines()
        candidatos = []
        
        for line in all_lines:
            matched_label = match_label(line['text'], LABELS)
            if matched_label:
                amount_info = rightmost_amount(all_lines, line)
                if amount_info:
                    amount_info['prioridad'] = get_label_priority(matched_label)
                    amount_info['label_encontrado'] = matched_label
                    candidatos.append(amount_info)
        
        # 3. Filtrar y priorizar candidatos
        if candidatos:
            # Filtrar por prioridad alta si hay
            high_priority = [c for c in candidatos if c.get('prioridad', 0) >= 90]
            if high_priority:
                candidatos = high_priority
            
            # Ordenar por prioridad y posición
            candidatos.sort(key=lambda x: (x.get('prioridad', 0), -x['x']), reverse=True)
            
            return {
                "valor_total": candidatos[0]['valor'],
                "metodo": candidatos[0]['metodo'],
                "valores_encontrados": candidatos,
                "total_encontrados": len(candidatos),
                "texto_extraido": f"Encontrados {len(candidatos)} candidatos"
            }
        
        # 4. Fallback: búsqueda general
        all_numbers = []
        for line in all_lines:
            numbers = NUM_RE.findall(line['text'])
            for num_text in numbers:
                val = clean_amount(num_text)
                if val and val >= 100:
                    all_numbers.append({
                        'valor': val,
                        'texto_linea': line['text'],
                        'metodo': 'busqueda_texto_fallback'
                    })
        
        if all_numbers:
            # Tomar el número más grande
            all_numbers.sort(key=lambda x: x['valor'], reverse=True)
            return {
                "valor_total": all_numbers[0]['valor'],
                "metodo": "busqueda_texto_fallback",
                "valores_encontrados": all_numbers,
                "total_encontrados": len(all_numbers),
                "texto_extraido": f"Encontrados {len(all_numbers)} números"
            }
        
        return {
            "valor_total": 0,
            "metodo": "no_encontrado",
            "valores_encontrados": [],
            "total_encontrados": 0,
            "texto_extraido": "No se encontró valor total"
        }
        
    except Exception as e:
        return {
            "valor_total": 0,
            "metodo": "error",
            "error": str(e),
            "valores_encontrados": [],
            "total_encontrados": 0,
            "texto_extraido": f"Error: {str(e)}"
        }

def _extraer_valor_total_xml(xml_content: str) -> Dict[str, Any]:
    """Extrae el valor total del XML del SRI"""
    
    try:
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring(xml_content)
        
        # Buscar importeTotal
        importe_total = root.find('.//importeTotal')
        if importe_total is not None:
            valor = float(importe_total.text)
            return {
                "valor_total": valor,
                "ubicaciones": [
                    {
                        "ubicacion": "infoFactura/importeTotal",
                        "valor": valor,
                        "texto": importe_total.text
                    }
                ],
                "total_ubicaciones": 1
            }
        
        # Si no hay importeTotal, calcular desde totalConImpuestos
        total_con_impuestos = root.find('.//totalConImpuestos')
        if total_con_impuestos is not None:
            total_impuestos = 0
            ubicaciones = []
            
            for impuesto in total_con_impuestos.findall('.//totalImpuesto'):
                valor_elem = impuesto.find('valor')
                if valor_elem is not None:
                    valor = float(valor_elem.text)
                    total_impuestos += valor
                    ubicaciones.append({
                        "ubicacion": "totalConImpuestos (suma)",
                        "valor": valor,
                        "texto": valor_elem.text
                    })
            
            # Buscar totalSinImpuestos
            total_sin_impuestos = root.find('.//totalSinImpuestos')
            if total_sin_impuestos is not None:
                valor_sin = float(total_sin_impuestos.text)
                ubicaciones.append({
                    "ubicacion": "totalSinImpuestos",
                    "valor": valor_sin,
                    "texto": total_sin_impuestos.text
                })
                valor_total = valor_sin + total_impuestos
            else:
                valor_total = total_impuestos
            
            return {
                "valor_total": valor_total,
                "ubicaciones": ubicaciones,
                "total_ubicaciones": len(ubicaciones)
            }
        
        return {
            "valor_total": 0,
            "ubicaciones": [],
            "total_ubicaciones": 0,
            "error": "No se encontró información de totales"
        }
        
    except Exception as e:
        return {
            "valor_total": 0,
            "ubicaciones": [],
            "total_ubicaciones": 0,
            "error": f"Error parseando XML: {str(e)}"
        }
async def _validar_autorizacion_sri_por_clave(clave_acceso: str, pdf_bytes: bytes = None) -> Dict[str, Any]:
    """Valida la autorización del SRI por clave de acceso"""
    
    try:
        print(f"[DEBUG] Iniciando validación SRI para clave: {clave_acceso[:20]}...")
        # Llamar al servicio del SRI
        autorizado, estado, xml_comprobante, raw_data = sri_autorizacion_por_clave(clave_acceso)
        print(f"[DEBUG] SRI response: autorizado={autorizado}, estado={estado[:50]}...")
        print(f"[DEBUG] XML comprobante: {xml_comprobante is not None}, longitud: {len(xml_comprobante) if xml_comprobante else 0}")
        
        resultado = {
            "autorizado": autorizado,
            "mensaje": estado,
            "clave_acceso": clave_acceso,
            "datos_autorizacion": raw_data
        }
        
        # Si está autorizado, validar la firma del XML usando la misma lógica que validar-firma-universal
        if autorizado and xml_comprobante:
            try:
                print(f"[DEBUG] Validando firma XAdES del XML usando lógica de validar-firma-universal")
                
                # Usar exactamente la misma lógica que el endpoint universal
                from routes.validacion_firma_universal import _validar_xml_universal
                
                # Convertir XML a bytes para la función universal
                xml_bytes = xml_comprobante.encode('utf-8')
                
                # Llamar a la función universal
                validacion_universal = await _validar_xml_universal(xml_bytes, validar_autorizacion_sri=False)
                
                print(f"[DEBUG] Validación universal completada: {type(validacion_universal)}")
                print(f"[DEBUG] Validación universal keys: {list(validacion_universal.keys())}")
                
                resultado["validacion_firma_xml"] = validacion_universal
                
            except Exception as e:
                print(f"[DEBUG] Error en validación XAdES: {str(e)}")
                import traceback
                traceback.print_exc()
                resultado["error_firma_xml"] = f"Error validando firma del XML: {str(e)}"
                resultado["validacion_firma_xml"] = False
        else:
            print(f"[DEBUG] No se ejecutó validación XAdES: autorizado={autorizado}, xml_comprobante={xml_comprobante is not None}")
        
        print(f"[DEBUG] Resultado final: {list(resultado.keys())}")
        return resultado
        
    except Exception as e:
        print(f"[DEBUG] Error general en validación SRI: {str(e)}")
        return {
            "autorizado": False,
            "error": f"Error en validación SRI: {str(e)}",
            "clave_acceso": clave_acceso
        }

# OCR functionality básica restaurada
def easyocr_text_from_pdf(pdf_bytes, lang=['es', 'en']):
    """
    Implementación básica de OCR usando PyMuPDF + pytesseract como fallback
    """
    try:
        import fitz
        import re
        
        # Primero intentar extracción de texto normal
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_extracted = ""
        
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            
            # Si la página tiene poco texto, intentar OCR de imágenes
            if len(page_text.strip()) < 50:
                try:
                    # Convertir página a imagen
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Aumentar resolución
                    img_data = pix.tobytes("png")
                    
                    # Intentar OCR con pytesseract si está disponible
                    try:
                        import pytesseract
                        from PIL import Image
                        import io
                        
                        img = Image.open(io.BytesIO(img_data))
                        ocr_text = pytesseract.image_to_string(img, lang='spa+eng')
                        text_extracted += f"\n--- OCR Página {page_num + 1} ---\n{ocr_text}\n"
                        
                    except ImportError:
                        # Si no hay pytesseract, usar extracción básica
                        text_extracted += f"\n--- Página {page_num + 1} (básico) ---\n{page_text}\n"
                        
                except Exception as e:
                    # Fallback a texto normal
                    text_extracted += f"\n--- Página {page_num + 1} ---\n{page_text}\n"
            else:
                text_extracted += f"\n--- Página {page_num + 1} ---\n{page_text}\n"
        
        doc.close()
        return text_extracted
        
    except Exception as e:
        print(f"Error en OCR básico: {e}")
        return ""

HAS_EASYOCR = True  # Habilitado con implementación básica
from sri import sri_autorizacion_por_clave, parse_autorizacion_response, factura_xml_to_json
from riesgo import evaluar_riesgo_factura, detectar_texto_sobrepuesto_avanzado

import fitz  # para chequeo de PDF escaneado


router = APIRouter()


class Peticion(BaseModel):
    pdfbase64: str  # Mantener compatibilidad con nombre existente


def is_scanned_image_pdf(pdf_bytes: bytes, extracted_text: str) -> bool:
    """Copia local para validar si un PDF es escaneado (poco texto + imágenes)."""
    text_len = len((extracted_text or "").strip())
    little_text = text_len < 50
    try:
        sample = pdf_bytes[: min(len(pdf_bytes), 2_000_000)]
        img_hits = len(re.findall(rb"/Subtype\s*/Image", sample)) or len(re.findall(rb"/Image\b", sample))
        has_image_objs = img_hits > 0
    except Exception:
        has_image_objs = False
    return little_text and has_image_objs


@router.post("/validar-factura")
async def validar_factura(req: Peticion):
    t_all = time.perf_counter()

    # 1) decode base64
    t0 = time.perf_counter()
    try:
        archivo_bytes = base64.b64decode(req.pdfbase64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="El campo 'pdfbase64' no es base64 válido.")
    if len(archivo_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail=f"El archivo excede el tamaño máximo permitido ({MAX_PDF_BYTES} bytes).")
    log_step("1) decode base64", t0)

    # Validar que sea un PDF válido
    t0 = time.perf_counter()
    try:
        # Intentar abrir como PDF para validar
        import fitz
        doc = fitz.open(stream=archivo_bytes, filetype="pdf")
        doc.close()
    except Exception:
        raise HTTPException(status_code=400, detail="El archivo no es un PDF válido.")
    log_step("1.1) validar PDF", t0)

    # 2) texto directo con pdfminer
    t0 = time.perf_counter()
    try:
        text = extract_text(io.BytesIO(archivo_bytes))
    except Exception:
        text = ""
    log_step("2) extract_text(pdfminer)", t0)

    # 3) clave de acceso
    clave, etiqueta_encontrada = extract_clave_acceso_from_text(text or "")
    ocr_text = ""
    if not etiqueta_encontrada and is_scanned_image_pdf(archivo_bytes, text or "") and HAS_EASYOCR:
        t_ocr = time.perf_counter()
        ocr_text = easyocr_text_from_pdf(archivo_bytes)
        log_step("3b) EasyOCR total", t_ocr)
        clave_ocr, etiqueta_ocr = extract_clave_acceso_from_text(ocr_text or "")
        if etiqueta_ocr and clave_ocr:
            clave = clave_ocr
            etiqueta_encontrada = True

    fuente_texto = text if text and not is_scanned_image_pdf(archivo_bytes, text) else (ocr_text or text)

    # 4) extraer campos del PDF
    pdf_fields = extract_invoice_fields_from_text(fuente_texto or "", clave)

    # Si no hay clave válida → ejecutar riesgo con sri_ok=False
    if not etiqueta_encontrada or not clave or not re.fullmatch(r"\d{49}", str(clave)):
        riesgo = evaluar_riesgo_factura(archivo_bytes, fuente_texto or "", pdf_fields, sri_ok=False)
        log_step("TOTAL (RIESGO sin clave)", t_all)
        return JSONResponse(
            status_code=200,
            content=safe_serialize_dict({
                "sri_verificado": False,
                "mensaje": "No se pudo obtener una Clave de Acceso válida del PDF. Se ejecutó evaluación de riesgo.",
                "riesgo": riesgo,
                "validacion_firmas": {
                    "resumen": {"total_firmas": 0, "firmas_validas": 0, "firmas_invalidas": 0, "con_certificados": 0, "con_timestamps": 0, "con_politicas": 0, "porcentaje_validas": 0},
                    "dependencias": {"asn1crypto": False, "oscrypto": False, "certvalidator": False},
                    "analisis_sri": {"es_documento_sri": False, "ruc_emisor": None, "razon_social": None, "numero_documento": None, "fecha_emision": None, "clave_acceso": None, "ambiente": None, "tipo_emision": None},
                    "validacion_pdf": {"firma_detectada": False, "tipo_firma": "ninguna", "es_pades": False, "metadatos": {"numero_firmas": 0}},
                    "tipo_documento": "pdf",
                    "firma_detectada": False
                }
            })
        )

    # 5) Validación SRI usando la lógica del endpoint universal
    t0 = time.perf_counter()
    try:
        print(f"[DEBUG] Llamando a _validar_autorizacion_sri_por_clave con clave: {clave[:20]}...")
        validacion_sri = await _validar_autorizacion_sri_por_clave(clave, archivo_bytes)
        print(f"[DEBUG] validacion_sri recibida: {type(validacion_sri)}")
        print(f"[DEBUG] validacion_sri keys: {list(validacion_sri.keys()) if isinstance(validacion_sri, dict) else 'No es dict'}")
        log_step("5) Validación SRI", t0)
        
        if not validacion_sri.get("autorizado", False):
            riesgo = evaluar_riesgo_factura(archivo_bytes, fuente_texto or "", pdf_fields, sri_ok=False)
            return JSONResponse(
                status_code=200,
                content=safe_serialize_dict({
                "sri_verificado": False,
                    "mensaje": "El comprobante no está AUTORIZADO en el SRI.",
                "riesgo": riesgo,
                    "validacion_firmas": {
                        "resumen": {"total_firmas": 0, "firmas_validas": 0, "firmas_invalidas": 0, "con_certificados": 0, "con_timestamps": 0, "con_politicas": 0, "porcentaje_validas": 0},
                        "dependencias": {"asn1crypto": False, "oscrypto": False, "certvalidator": False},
                        "analisis_sri": {"es_documento_sri": False, "ruc_emisor": None, "razon_social": None, "numero_documento": None, "fecha_emision": None, "clave_acceso": None, "ambiente": None, "tipo_emision": None},
                        "validacion_pdf": {"firma_detectada": False, "tipo_firma": "ninguna", "es_pades": False, "metadatos": {"numero_firmas": 0}},
                        "tipo_documento": "pdf",
                        "firma_detectada": False
                    }
                })
            )
        
        # Si está autorizado, continuar con el procesamiento
        raw = validacion_sri.get("datos_autorizacion", {})
        
    except Exception as e:
        print(f"[DEBUG] Error en validación SRI: {e}")
        riesgo = evaluar_riesgo_factura(archivo_bytes, fuente_texto or "", pdf_fields, sri_ok=False)
        return JSONResponse(
            status_code=200,
            content=safe_serialize_dict({
                "sri_verificado": False,
                "mensaje": f"Error consultando SRI: {str(e)}",
                "riesgo": riesgo,
                "validacion_firmas": {
                    "resumen": {"total_firmas": 0, "firmas_validas": 0, "firmas_invalidas": 0, "con_certificados": 0, "con_timestamps": 0, "con_politicas": 0, "porcentaje_validas": 0},
                    "dependencias": {"asn1crypto": False, "oscrypto": False, "certvalidator": False},
                    "analisis_sri": {"es_documento_sri": False, "ruc_emisor": None, "razon_social": None, "numero_documento": None, "fecha_emision": None, "clave_acceso": None, "ambiente": None, "tipo_emision": None},
                    "validacion_pdf": {"firma_detectada": False, "tipo_firma": "ninguna", "es_pades": False, "metadatos": {"numero_firmas": 0}},
                    "tipo_documento": "pdf",
                    "firma_detectada": False
                }
            })
        )

    # 6) parsear XML del SRI
    xml_src = normalize_comprobante_xml(validacion_sri.get("xml_autorizacion", ""))
    try:
        sri_json = factura_xml_to_json(xml_src)
    except Exception as e:
        riesgo = evaluar_riesgo_factura(archivo_bytes, fuente_texto or "", pdf_fields, sri_ok=True)
        return JSONResponse(status_code=200, content=safe_serialize_dict({
            "sri_verificado": True,
            "mensaje": "AUTORIZADO en el SRI, pero no se pudo convertir a JSON.",
            "detalle": str(e),
            "riesgo": riesgo,
            "validacion_firmas": {
                "resumen": {"total_firmas": 0, "firmas_validas": 0, "firmas_invalidas": 0, "con_certificados": 0, "con_timestamps": 0, "con_politicas": 0, "porcentaje_validas": 0},
                "dependencias": {"asn1crypto": False, "oscrypto": False, "certvalidator": False},
                "analisis_sri": {"es_documento_sri": False, "ruc_emisor": None, "razon_social": None, "numero_documento": None, "fecha_emision": None, "clave_acceso": None, "ambiente": None, "tipo_emision": None},
                "validacion_pdf": {"firma_detectada": False, "tipo_firma": "ninguna", "es_pades": False, "metadatos": {"numero_firmas": 0}},
                "tipo_documento": "pdf",
                "firma_detectada": False
            }
        }))

    # --------- Comparación cabecera ----------
    sri_fields = {
        "ruc": (sri_json.get("infoTributaria") or {}).get("ruc"),
        "razonSocial": (sri_json.get("infoTributaria") or {}).get("razonSocial"),
        "fechaEmision": (sri_json.get("infoFactura") or {}).get("fechaEmision"),
        "importeTotal": (sri_json.get("infoFactura") or {}).get("importeTotal"),
        "claveAcceso": (sri_json.get("infoTributaria") or {}).get("claveAcceso"),
    }

    def _norm_name(s):
        return re.sub(r"\s+", " ", strip_accents((s or "").strip())).upper()

    diferencias: Dict[str, Dict[str, Any]] = {}
    if sri_fields["ruc"] and pdf_fields.get("ruc") and sri_fields["ruc"] != pdf_fields["ruc"]:
        diferencias["ruc"] = {"sri": sri_fields["ruc"], "pdf": pdf_fields["ruc"]}

    if sri_fields["fechaEmision"] and pdf_fields.get("fechaEmision"):
        s_sri = str(sri_fields["fechaEmision"]).replace("-", "/")
        s_pdf = str(pdf_fields["fechaEmision"]).replace("-", "/")
        if s_sri != s_pdf:
            diferencias["fechaEmision"] = {"sri": s_sri, "pdf": s_pdf}

    if sri_fields["importeTotal"] is not None and pdf_fields.get("importeTotal") is not None:
        s = float(sri_fields["importeTotal"])
        p = float(pdf_fields["importeTotal"])
        if abs(s - p) > PRICE_EPS:
            diferencias["importeTotal"] = {"sri": s, "pdf": p}

    if sri_fields["razonSocial"] and pdf_fields.get("razonSocial"):
        if _norm_name(sri_fields["razonSocial"]) != _norm_name(pdf_fields["razonSocial"]):
            diferencias["razonSocial"] = {"sri": sri_fields["razonSocial"], "pdf": pdf_fields["razonSocial"]}

    if sri_fields["claveAcceso"] and pdf_fields.get("claveAcceso") and sri_fields["claveAcceso"] != pdf_fields["claveAcceso"]:
        diferencias["claveAcceso"] = {"sri": sri_fields["claveAcceso"], "pdf": pdf_fields["claveAcceso"]}

    # --------- Comparación de productos ----------
    sri_items = sri_json.get("detalles") or []
    pdf_items = pdf_fields.get("detalles") or []

    def sim(a: str, b: str) -> float:
        return SequenceMatcher(None, _norm_name(a), _norm_name(b)).ratio()

    emparejamientos = []
    usados_pdf = set()
    for i, s in enumerate(sri_items):
        best_j, best_score = None, -1.0
        for j, p in enumerate(pdf_items):
            if j in usados_pdf:
                continue
            sc = sim(s.get("descripcion", ""), p.get("descripcion", ""))
            if sc > best_score:
                best_j, best_score = j, sc
        if best_j is not None and best_score >= MATCH_THRESHOLD:
            usados_pdf.add(best_j)
            emparejamientos.append((i, best_j, best_score))
        else:
            emparejamientos.append((i, None, 0.0))

    diferenciasProductos: List[Dict[str, Any]] = []
    for (i, j, score) in emparejamientos:
        s = sri_items[i]
        if j is None:
            diferenciasProductos.append({
                "descripcion_sri": s.get("descripcion"),
                "match": "no_encontrado_en_pdf"
            })
            continue
        p = pdf_items[j]
        dif: Dict[str, Any] = {}
        s_qty = _to_float(s.get("cantidad"))
        p_qty = _to_float(p.get("cantidad"))
        if s_qty is not None and p_qty is not None and abs(s_qty - p_qty) > QTY_EPS:
            dif["cantidad"] = {"sri": s_qty, "pdf": p_qty}
        s_unit = _to_float(s.get("precioUnitario"))
        p_unit = _to_float(p.get("precioUnitario"))
        if s_unit is not None and p_unit is not None and abs(s_unit - p_unit) > PRICE_EPS:
            dif["precioUnitario"] = {"sri": s_unit, "pdf": p_unit}
        s_tot = _to_float(s.get("precioTotalSinImpuesto"))
        p_tot = _to_float(p.get("precioTotal"))
        if s_tot is not None and p_tot is not None and abs(s_tot - p_tot) > TOTAL_EPS:
            dif["precioTotal"] = {"sri": s_tot, "pdf": p_tot}
        if dif:
            diferenciasProductos.append({
                "descripcion_sri": s.get("descripcion"),
                "descripcion_pdf": p.get("descripcion"),
                "similitud": round(score, 3),
                "diferencias": dif
            })

    sobrantes_pdf = [pdf_items[j] for j in range(len(pdf_items)) if j not in usados_pdf]
    for p in sobrantes_pdf:
        diferenciasProductos.append({
            "descripcion_pdf": p.get("descripcion"),
            "match": "no_encontrado_en_sri"
        })

    total_pdf_items = round(sum(_to_float(it.get("precioTotal")) or 0 for it in pdf_items), 2) if pdf_items else None
    total_sri_items = round(sum(_to_float(it.get("precioTotalSinImpuesto")) or 0 for it in sri_items), 2) if sri_items else None

    totales_ok = True
    if total_pdf_items is not None and total_sri_items is not None:
        if abs(total_pdf_items - total_sri_items) > TOTAL_EPS:
            totales_ok = False
            diferencias["totalItems"] = {"sri": total_sri_items, "pdf": total_pdf_items}

    coincidencia = (not diferencias and not diferenciasProductos and totales_ok)
    
    # DEBUG: logs para entender por qué no hay coincidencia
    print(f"[DEBUG COINCIDENCIA] diferencias: {diferencias}")
    print(f"[DEBUG COINCIDENCIA] diferenciasProductos: {len(diferenciasProductos)} elementos")
    print(f"[DEBUG COINCIDENCIA] totales_ok: {totales_ok}")
    print(f"[DEBUG COINCIDENCIA] coincidencia final: {coincidencia}")
    print(f"[DEBUG COINCIDENCIA] total_pdf_items: {total_pdf_items}")
    print(f"[DEBUG COINCIDENCIA] total_sri_items: {total_sri_items}")
    
    # 7) Análisis avanzado de texto sobrepuesto
    t0 = time.perf_counter()
    texto_sobrepuesto_analisis = detectar_texto_sobrepuesto_avanzado(archivo_bytes)
    log_step("7) Análisis texto sobrepuesto avanzado", t0)
    
    # Para la evaluación de riesgo, si el SRI está AUTORIZADO, eso debería ser suficiente
    # para considerarlo válido, independientemente de diferencias menores en el parseo
    sri_autorizado_ok = True  # Sabemos que llegamos aquí solo si está AUTORIZADO
    
    # Usar el XML del SRI para validación financiera mejorada
    xml_sri_data = None
    if sri_json:
        xml_sri_data = sri_json.copy()
        xml_sri_data["autorizado"] = True
    
    # 7) Evaluación de riesgo (antes de validación de firmas para obtener firmas_pdf)
    t0 = time.perf_counter()
    riesgo = evaluar_riesgo_factura(
        archivo_bytes, 
        fuente_texto or "", 
        pdf_fields, 
        sri_ok=sri_autorizado_ok,
        clave_acceso=clave,
        ejecutar_prueba_sri=False,  # Ya tenemos los datos
        xml_sri_data=xml_sri_data,  # Pasar el XML del SRI
        firmas_pdf=False  # Se actualizará después de la validación de firmas
    )
    log_step("7) Evaluación de riesgo inicial", t0)

    # 8) Validación de firmas digitales (siempre para facturas)
    t0 = time.perf_counter()
    try:
        validacion_firmas = analizar_firmas_digitales_avanzado(
            archivo_bytes, 
            verify_crypto=True, 
            verify_chain=True
        )
        log_step("8) Validación de firmas digitales", t0)
    except Exception as e:
        print(f"[DEBUG] Error en validación de firmas: {e}")
        validacion_firmas = {
            "firma_detectada": False,
            "tipo_firma": "ninguna",
            "es_pades": False,
            "metadatos": {"numero_firmas": 0},
            "resumen": {
                "tiene_firma": False,
                "total_firmas": 0,
                "firmas_validas": 0,
                "firmas_pades": 0,
                "integridad_ok": 0,
                "crypto_ok": 0,
                "chain_ok": 0
            },
            "validacion_avanzada": {
                "firma_detectada": False,
                "firmas": [],
                "resumen": {
                    "total_firmas": 0,
                    "firmas_validas": 0,
                    "firmas_integridad_ok": 0,
                    "firmas_sin_modificaciones": 0,
                    "firmas_crypto_ok": 0,
                    "firmas_chain_ok": 0,
                    "firmas_pades": 0
                },
                "dependencias": {
                    "asn1crypto": False,
                    "oscrypto": False,
                    "certvalidator": False
                }
            },
            "cantidad_firmas_pades": 0
        }

    # 9) Actualizar evaluación de riesgo usando exactamente la misma lógica que el endpoint universal
    t0 = time.perf_counter()
    
    # Usar exactamente la misma lógica que _validar_pdf_universal
    # 1. Detección básica rápida
    deteccion_basica = detectar_firmas_pdf_simple(archivo_bytes)
    
    # 2. Detección con patrones
    deteccion_patrones = detectar_firma_desde_base64(req.pdfbase64)
    
    # 3. Análisis de documento SRI (ya tenemos analisis_sri)
    analisis_sri = analizar_documento_sri(archivo_bytes)
    
    # 4. Extracción robusta del número de autorización (ya tenemos extraccion_autorizacion)
    extraccion_autorizacion = _extraer_numero_autorizacion_pdf(archivo_bytes)
    
    # 5. Validación de autorización SRI (ya tenemos validacion_sri)
    
    # Combinar resultados usando la misma lógica que el endpoint universal
    resultado_universal = {
        "firma_detectada": deteccion_basica or deteccion_patrones.get("firma_detectada", False),
        "metodos_deteccion": {
            "deteccion_basica": deteccion_basica,
            "deteccion_patrones": deteccion_patrones.get("firma_detectada", False),
            "confianza_patrones": deteccion_patrones.get("confianza", 0.0)
        },
        "tipo_firma": deteccion_patrones.get("tipo_firma", "indeterminada"),
        "es_pades": False,
        "es_documento_sri": analisis_sri.get("tipo_documento") == "ride",
        "metadatos": deteccion_patrones.get("metadatos", {}),
        "resumen": {
            "tiene_firma": deteccion_basica or deteccion_patrones.get("firma_detectada", False),
            "es_ride": analisis_sri.get("tipo_documento") == "ride",
            "tipo_documento_sri": analisis_sri.get("tipo_documento", "no_sri"),
            "autorizado_sri": validacion_sri.get("autorizado", False) if validacion_sri else None
        },
        "extraccion_autorizacion": extraccion_autorizacion,
        "validacion_sri": validacion_sri  # Incluir la validacion_sri que ya tenemos
    }
    
    
    # Extraer información de firmas del resultado universal
    firmas_pdf_valido = resultado_universal.get("firma_detectada", False)
    
    # Crear info_firmas usando la información de validación XAdES del SRI
    validacion_firma_xml = validacion_sri.get("validacion_firma_xml", {})
    info_firmas = {
        "firma_detectada": validacion_firma_xml.get("firma_detectada", False),
        "tipo_firma": validacion_firma_xml.get("tipo_firma", "xades"),
        "metadatos": {"numero_firmas": validacion_firma_xml.get("resumen", {}).get("total_firmas", 0)},
        "firmas": validacion_firma_xml.get("firmas", []),
        "resumen": {
            "tiene_firma": validacion_firma_xml.get("firma_detectada", False),
            "total_firmas": validacion_firma_xml.get("resumen", {}).get("total_firmas", 0),
            "firmas_validas": validacion_firma_xml.get("resumen", {}).get("firmas_validas", 0),
            "integridad_ok": validacion_firma_xml.get("resumen", {}).get("firmas_validas", 0),
            "chain_ok": validacion_firma_xml.get("resumen", {}).get("con_certificados", 0)
        }
    }
    
    # Debug: verificar estructura de validacion_sri
    print(f"[DEBUG] validacion_sri existe: {validacion_sri is not None}")
    if validacion_sri:
        print(f"[DEBUG] validacion_sri keys: {list(validacion_sri.keys())}")
        if validacion_sri.get("validacion_firma_xml"):
            print(f"[DEBUG] validacion_firma_xml keys: {list(validacion_sri['validacion_firma_xml'].keys())}")
        else:
            print(f"[DEBUG] No hay validacion_firma_xml en validacion_sri")
    
    # Usar directamente la información de validacion_sri que ya tenemos
    if validacion_sri and validacion_sri.get("validacion_firma_xml"):
        validacion_firma_xml = validacion_sri["validacion_firma_xml"]
        if isinstance(validacion_firma_xml, dict) and validacion_firma_xml.get("validacion_xades"):
            validacion_xades = validacion_firma_xml["validacion_xades"]
            resumen_xades = validacion_xades.get("resumen", {})
            
            # Actualizar info_firmas con información XAdES
            info_firmas.update({
                "firma_detectada": validacion_xades.get("firma_detectada", False),
                "tipo_firma": validacion_xades.get("tipo_firma", "xades"),
                "metadatos": {"numero_firmas": resumen_xades.get("total_firmas", 0)},
                "firmas": validacion_xades.get("firmas", []),
                "resumen": {
                    "tiene_firma": validacion_xades.get("firma_detectada", False),
                    "total_firmas": resumen_xades.get("total_firmas", 0),
                    "firmas_validas": resumen_xades.get("firmas_validas", 0),
                    "integridad_ok": resumen_xades.get("firmas_validas", 0),
                    "chain_ok": resumen_xades.get("con_certificados", 0)
                }
            })
            
            # Actualizar firmas_pdf_valido con la información XAdES
            firmas_pdf_valido = validacion_xades.get("firma_detectada", False)
            
            print(f"[DEBUG] ✅ Usando información XAdES: firma_detectada={firmas_pdf_valido}, total_firmas={resumen_xades.get('total_firmas', 0)}")
        else:
            print(f"[DEBUG] ❌ No hay validacion_xades en validacion_firma_xml")
    else:
        print(f"[DEBUG] ❌ No hay validacion_sri o validacion_firma_xml")
    
    riesgo_actualizado = evaluar_riesgo_factura(
        archivo_bytes, 
        fuente_texto or "", 
        pdf_fields, 
        sri_ok=sri_autorizado_ok,
        clave_acceso=clave,
        ejecutar_prueba_sri=False,
        xml_sri_data=xml_sri_data,
        firmas_pdf=firmas_pdf_valido,
        info_firmas=info_firmas
    )
    log_step("9) Actualización de riesgo con firmas", t0)

    # 10) Preparar información completa de validación de firmas usando la misma lógica que validar-firma-universal
    t0 = time.perf_counter()
    
    # Obtener información de validación XAdES del SRI (ya viene del endpoint universal)
    validacion_firma_xml = validacion_sri.get("validacion_firma_xml", {})
    print(f"[DEBUG] validacion_firma_xml keys: {list(validacion_firma_xml.keys())}")
    print(f"[DEBUG] validacion_firma_xml resumen: {validacion_firma_xml.get('resumen', {})}")
    
    # Si validacion_firma_xml está vacío, usar la estructura directa del endpoint universal
    if not validacion_firma_xml:
        print(f"[DEBUG] validacion_firma_xml está vacío, usando estructura directa del endpoint universal")
        # La estructura viene directamente del endpoint universal
        validacion_firmas_completa = {
            "resumen": validacion_sri.get("resumen", {
                "total_firmas": 0,
                "firmas_validas": 0,
                "firmas_invalidas": 0,
                "con_certificados": 0,
                "con_timestamps": 0,
                "con_politicas": 0,
                "porcentaje_validas": 0
            }),
            "dependencias": validacion_sri.get("dependencias", {
                "asn1crypto": False,
                "oscrypto": False,
                "certvalidator": False
            }),
            "analisis_sri": validacion_sri.get("analisis_sri", {
                "es_documento_sri": False,
                "ruc_emisor": None,
                "razon_social": None,
                "numero_documento": None,
                "fecha_emision": None,
                "clave_acceso": None,
                "ambiente": None,
                "tipo_emision": None
            }),
            "validacion_pdf": validacion_firmas,
            "tipo_documento": "xml",  # Para documentos SRI siempre es XML
            "firma_detectada": validacion_sri.get("firma_detectada", False)
        }
    else:
        # Usar la estructura de validacion_firma_xml
        validacion_firmas_completa = {
            "resumen": validacion_firma_xml.get("resumen", {
                "total_firmas": 0,
                "firmas_validas": 0,
                "firmas_invalidas": 0,
                "con_certificados": 0,
                "con_timestamps": 0,
                "con_politicas": 0,
                "porcentaje_validas": 0
            }),
            "dependencias": validacion_firma_xml.get("dependencias", {
                "asn1crypto": False,
                "oscrypto": False,
                "certvalidator": False
            }),
            "analisis_sri": validacion_firma_xml.get("analisis_sri", {
                "es_documento_sri": False,
                "ruc_emisor": None,
                "razon_social": None,
                "numero_documento": None,
                "fecha_emision": None,
                "clave_acceso": None,
                "ambiente": None,
                "tipo_emision": None
            }),
            "validacion_pdf": validacion_firmas,
            "tipo_documento": "xml",  # Para documentos SRI siempre es XML
            "firma_detectada": validacion_firma_xml.get("firma_detectada", False)
        }
    
    print(f"[DEBUG] validacion_firmas_completa resumen: {validacion_firmas_completa['resumen']}")
    
    log_step("10) Preparación validación firmas completa", t0)

    return JSONResponse(
        status_code=200,
        content=safe_serialize_dict({
            "sri_verificado": True,
            "mensaje": "El comprobante es AUTORIZADO en el SRI.",
            "coincidencia": "si" if coincidencia else "no",
            "diferencias": diferencias,
            "diferenciasProductos": diferenciasProductos,
            "resumenProductos": {
                "num_sri": len(sri_items),
                "num_pdf": len(pdf_items),
                "total_sri_items": total_sri_items,
                "total_pdf_items": total_pdf_items
            },
            "factura": sri_json,
            "riesgo": riesgo_actualizado,
            "validacion_firmas": validacion_firmas_completa
        }),
    )


