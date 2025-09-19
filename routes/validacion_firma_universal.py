"""
Endpoint universal para validación de firmas digitales.

Combina todas las formas de validar si un documento está firmado:
- Detección básica de firmas en PDFs
- Validación criptográfica avanzada (RSA/ECDSA)
- Detección de PAdES
- Validación de XAdES en XMLs
- Análisis de documentos del SRI

Autor: Sistema de Análisis Forense
Versión: 1.0
"""

from fastapi import APIRouter, HTTPException, Form, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import base64

from helpers.validacion_firma_digital import (
    validate_pdf_signatures,
    detectar_firmas_pdf_simple,
    generar_reporte_firmas
)
from helpers.validacion_xades import validar_xades, generar_reporte_xades
from helpers.analisis_sri_ride import analizar_documento_sri, validar_xml_firmado_sri
from helpers.deteccion_firma_simple import detectar_firma_desde_base64
from helpers.type_conversion import safe_serialize_dict
from sri import sri_autorizacion_por_clave, parse_autorizacion_response
import fitz  # PyMuPDF
import re

router = APIRouter()


class DocumentoRequest(BaseModel):
    """Modelo para solicitud de validación de documento"""
    documento_base64: str
    tipo_documento: str = "pdf"  # "pdf" o "xml"
    verificar_crypto: bool = False
    verificar_cadena: bool = False
    validar_autorizacion_sri: bool = False  # Validar autorización en el SRI


@router.post("/validar-firma-universal")
async def validar_firma_universal_endpoint(request: DocumentoRequest):
    """
    Validación universal de firmas digitales.
    
    Combina todas las formas de validar si un documento está firmado:
    - PDFs: Detección básica, validación criptográfica, PAdES
    - XMLs: Validación XAdES, análisis SRI
    
    Args:
        request: Solicitud con documento en base64 y opciones
        
    Returns:
        Resultado completo de validación de firmas
    """
    try:
        # Validar base64
        try:
            documento_bytes = base64.b64decode(request.documento_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="El campo 'documento_base64' no es base64 válido")
        
        # Determinar tipo de documento si no se especifica
        if request.tipo_documento == "auto":
            request.tipo_documento = _detectar_tipo_documento(documento_bytes)
        
        resultado = {}
        
        if request.tipo_documento.lower() == "pdf":
            # Validación para PDFs
            resultado = await _validar_pdf_universal(
                documento_bytes, 
                request.verificar_crypto, 
                request.verificar_cadena,
                request.validar_autorizacion_sri
            )
        elif request.tipo_documento.lower() == "xml":
            # Validación para XMLs
            resultado = await _validar_xml_universal(documento_bytes, request.validar_autorizacion_sri)
        else:
            raise HTTPException(status_code=400, detail="Tipo de documento no soportado. Use 'pdf' o 'xml'")
        
        return safe_serialize_dict({
            "success": True,
            "mensaje": "Validación universal de firmas completada",
            "tipo_documento": request.tipo_documento,
            "resultado": resultado
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


async def _validar_pdf_universal(pdf_bytes: bytes, verificar_crypto: bool, verificar_cadena: bool, validar_autorizacion_sri: bool = False) -> Dict[str, Any]:
    """Validación universal para PDFs"""
    
    # 1. Detección básica rápida
    deteccion_basica = detectar_firmas_pdf_simple(pdf_bytes)
    
    # 2. Detección con patrones
    deteccion_patrones = detectar_firma_desde_base64(base64.b64encode(pdf_bytes).decode('utf-8'))
    
    # 3. Validación avanzada (si se solicita)
    validacion_avanzada = None
    if verificar_crypto or verificar_cadena:
        validacion_avanzada = validate_pdf_signatures(
            pdf_bytes, 
            verify_crypto=verificar_crypto, 
            verify_chain=verificar_cadena
        )
    
    # 4. Análisis de documento SRI (si es un RIDE)
    analisis_sri = analizar_documento_sri(pdf_bytes)
    
    # 5. Extracción robusta del número de autorización
    extraccion_autorizacion = _extraer_numero_autorizacion_pdf(pdf_bytes)
    
    # 6. Validación de autorización SRI (si se solicita)
    validacion_sri = None
    if validar_autorizacion_sri:
        validacion_sri = await _validar_autorizacion_sri(analisis_sri, extraccion_autorizacion, pdf_bytes)
    
    # Combinar resultados
    resultado = {
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
        }
    }
    
    # Agregar información de validación avanzada si está disponible
    if validacion_avanzada:
        resultado["validacion_avanzada"] = validacion_avanzada
        resultado["firma_detectada"] = validacion_avanzada.get("firma_detectada", False)
        
        # Detectar PAdES
        firmas_pades = [f for f in validacion_avanzada.get("firmas", []) if f.get("es_pades", False)]
        resultado["es_pades"] = len(firmas_pades) > 0
        resultado["cantidad_firmas_pades"] = len(firmas_pades)
        
        # Actualizar resumen
        resultado["resumen"].update({
            "total_firmas": validacion_avanzada.get("resumen", {}).get("total_firmas", 0),
            "firmas_validas": validacion_avanzada.get("resumen", {}).get("firmas_validas", 0),
            "firmas_pades": validacion_avanzada.get("resumen", {}).get("firmas_pades", 0),
            "integridad_ok": validacion_avanzada.get("resumen", {}).get("firmas_integridad_ok", 0),
            "crypto_ok": validacion_avanzada.get("resumen", {}).get("firmas_crypto_ok", 0),
            "chain_ok": validacion_avanzada.get("resumen", {}).get("firmas_chain_ok", 0)
        })
    
    # Agregar información del SRI si es relevante
    if analisis_sri.get("tipo_documento") == "ride":
        resultado["sri_info"] = {
            "es_ride": True,
            "ruc_emisor": analisis_sri.get("analisis_basico", {}).get("ruc_emisor"),
            "razon_social": analisis_sri.get("analisis_basico", {}).get("razon_social"),
            "clave_acceso": analisis_sri.get("metadatos_fiscales", {}).get("clave_acceso"),
            "observaciones": analisis_sri.get("observaciones", [])
        }
    
    # Agregar información de extracción de autorización
    resultado["extraccion_autorizacion"] = extraccion_autorizacion
    
    # Agregar información de validación del SRI si está disponible
    if validacion_sri:
        resultado["validacion_sri"] = validacion_sri
    
    return resultado


async def _validar_xml_universal(xml_bytes: bytes, validar_autorizacion_sri: bool = False) -> Dict[str, Any]:
    """Validación universal para XMLs"""
    
    try:
        xml_content = xml_bytes.decode('utf-8')
    except Exception:
        raise HTTPException(status_code=400, detail="El contenido no es XML válido")
    
    # 1. Validación XAdES
    validacion_xades = validar_xades(xml_content)
    
    # 2. Validación específica del SRI
    validacion_sri = validar_xml_firmado_sri(xml_content)
    
    # 3. Validación de autorización SRI (si se solicita)
    autorizacion_sri = None
    if validar_autorizacion_sri and validacion_sri.get("es_documento_sri", False):
        # Extraer clave de acceso del XML
        clave_acceso = _extraer_clave_acceso_xml(xml_content)
        if clave_acceso:
            autorizacion_sri = await _validar_autorizacion_sri_por_clave(clave_acceso, None)
    
    # Combinar resultados
    resultado = {
        "firma_detectada": validacion_xades.get("firma_detectada", False) or validacion_sri.get("firma_valida", False),
        "tipo_firma": "xades" if validacion_xades.get("firma_detectada", False) else "ninguna",
        "es_documento_sri": validacion_sri.get("es_documento_sri", False),
        "validacion_xades": validacion_xades,
        "validacion_sri": validacion_sri,
        "resumen": {
            "tiene_firma": validacion_xades.get("firma_detectada", False) or validacion_sri.get("firma_valida", False),
            "es_xades": validacion_xades.get("firma_detectada", False),
            "es_sri": validacion_sri.get("es_documento_sri", False),
            "firmas_validas": validacion_xades.get("resumen", {}).get("firmas_validas", 0),
            "autorizado_sri": autorizacion_sri.get("autorizado", False) if autorizacion_sri else None
        }
    }
    
    # Agregar información de autorización del SRI si está disponible
    if autorizacion_sri:
        resultado["autorizacion_sri"] = autorizacion_sri
    
    return resultado


async def _validar_autorizacion_sri(analisis_sri: Dict[str, Any], extraccion_autorizacion: Dict[str, Any], pdf_bytes: bytes = None) -> Dict[str, Any]:
    """Valida la autorización del SRI para un documento RIDE"""
    
    try:
        # Priorizar la extracción robusta sobre el análisis SRI
        clave_acceso = extraccion_autorizacion.get("numero_autorizacion")
        
        # Fallback al análisis SRI si no se encontró en la extracción robusta
        if not clave_acceso:
            clave_acceso = analisis_sri.get("metadatos_fiscales", {}).get("clave_acceso")
        
        if not clave_acceso:
            return {
                "autorizado": False,
                "error": "No se encontró clave de acceso en el documento",
                "clave_acceso": None,
                "metodos_intentados": {
                    "extraccion_robusta": extraccion_autorizacion.get("total_encontrados", 0) > 0,
                    "analisis_sri": bool(analisis_sri.get("metadatos_fiscales", {}).get("clave_acceso"))
                }
            }
        
        # Validar con el SRI
        return await _validar_autorizacion_sri_por_clave(clave_acceso, pdf_bytes)
        
    except Exception as e:
        return {
            "autorizado": False,
            "error": f"Error en validación SRI: {str(e)}",
            "clave_acceso": None
        }


async def _validar_autorizacion_sri_por_clave(clave_acceso: str, pdf_bytes: bytes = None) -> Dict[str, Any]:
    """Valida la autorización del SRI por clave de acceso"""
    
    try:
        # Llamar al servicio del SRI
        autorizado, mensaje, xml_autorizacion, datos = sri_autorizacion_por_clave(clave_acceso)
        
        resultado = {
            "autorizado": autorizado,
            "mensaje": mensaje,
            "clave_acceso": clave_acceso,
            "xml_autorizacion": xml_autorizacion,
            "datos_autorizacion": datos
        }
        
        # Si está autorizado, validar la firma del XML y comparar valores
        if autorizado and xml_autorizacion:
            try:
                # Validar firma del XML autorizado
                validacion_xml = validar_xml_firmado_sri(xml_autorizacion)
                resultado["validacion_firma_xml"] = validacion_xml
                resultado["firma_xml_valida"] = validacion_xml.get("firma_valida", False)
                
                # Comparar valores totales entre PDF y XML (solo si tenemos PDF)
                if pdf_bytes:
                    comparacion_valores = await _comparar_valores_totales_pdf_xml(pdf_bytes, xml_autorizacion)
                    resultado["comparacion_valores"] = comparacion_valores
                
            except Exception as e:
                resultado["error_firma_xml"] = f"Error validando firma del XML: {str(e)}"
                resultado["firma_xml_valida"] = False
        
        return resultado
        
    except Exception as e:
        return {
            "autorizado": False,
            "error": f"Error en validación SRI: {str(e)}",
            "clave_acceso": clave_acceso
        }


def _extraer_valor_total_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extrae el valor total de la factura desde el PDF usando lógica robusta con análisis espacial"""
    
    try:
        # Abrir PDF desde bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Etiquetas para buscar
        LABELS = ["VALOR TOTAL", "IMPORTE TOTAL", "TOTAL A PAGAR"]
        NEG_ROW = re.compile(r"SIN\s+SUBSIDIO", re.I)
        NUM_RE = re.compile(r"[-+]?(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{2})?")
        
        def clean_amount(s: str) -> str | None:
            """Limpia y normaliza un valor monetario"""
            s = re.sub(r"[^\d\.,]", "", s)
            if not s: return None
            if s.count(".") + s.count(",") > 1:
                i = max(s.rfind("."), s.rfind(","))
                dec = s[i]; thou = "," if dec == "." else "."
                s = s.replace(thou, "").replace(dec, ".")
            else:
                s = s.replace(",", ".")
            try: 
                return f"{float(s):.2f}"
            except: 
                return None
        
        def from_xml_embedded(doc: fitz.Document) -> str | None:
            """Busca el valor total en XMLs embebidos (prioridad alta)"""
            for i in range(doc.embfile_count()):
                info = doc.embfile_info(i)
                name = (info.get("filename") or "").lower()
                data = doc.embfile_get(i)
                if name.endswith(".xml") or b"<factura" in data or b"<autorizacion" in data:
                    txt = data.decode("utf-8","ignore")
                    m = re.search(r"<importeTotal>\s*([0-9\.,]+)\s*</importeTotal>", txt, re.I)
                    if m:
                        val = clean_amount(m.group(1))
                        if val: return val
            return None
        
        # 1) Preferir XML incrustado (más confiable)
        valor_xml = from_xml_embedded(doc)
        if valor_xml:
            doc.close()
            return {
                "valor_total": float(valor_xml),
                "metodo": "xml_embebido",
                "valores_encontrados": [{"valor": float(valor_xml), "metodo": "xml_embebido"}],
                "total_encontrados": 1,
                "texto_extraido": "Valor extraído de XML embebido"
            }
        
        # 2) Búsqueda espacial por etiquetas
        candidatos = []
        for page in doc:
            words = page.get_text("words")  # x0,y0,x1,y1,word,block,line,word_no
            page_text = page.get_text()
            
            for label in LABELS:
                rects = page.search_for(label, quads=False)
                for r in rects:
                    # Banda vertical de la fila
                    y0, y1 = r.y0 - 3, r.y1 + 3
                    # Descartar si en esta banda aparece "SIN SUBSIDIO"
                    row_text = " ".join(w[4] for w in words if w[1] <= y1 and w[3] >= y0)
                    if NEG_ROW.search(row_text): 
                        continue
                    
                    # Números a la derecha del label, en la misma banda
                    nums = [(w[0], w[4]) for w in words
                            if (w[1] <= y1 and w[3] >= y0 and w[0] > r.x1 - 1 and NUM_RE.fullmatch(w[4]))]
                    if nums:
                        nums.sort(key=lambda t: t[0])      # izquierda -> derecha
                        raw = nums[-1][1]                  # el más a la derecha
                        val = clean_amount(raw)
                        if val:
                            candidatos.append({
                                "valor": float(val),
                                "texto_linea": f"{label}: {raw}",
                                "metodo": "busqueda_espacial",
                                "prioridad": 100
                            })
        
        # 3) Fallback por texto (si el layout es raro)
        if not candidatos:
            all_text = "\n".join(p.get_text() for p in doc)
            for m in re.finditer(r"(VALOR\s+TOTAL|IMPORTE\s+TOTAL|TOTAL\s+A\s+PAGAR)[^\d]{0,80}([0-9\.,]{1,20})",
                                 all_text, re.I | re.S):
                if NEG_ROW.search(all_text[m.start():m.end()+20]): 
                    continue
                val = clean_amount(m.group(2))
                if val: 
                    candidatos.append({
                        "valor": float(val),
                        "texto_linea": f"VALOR TOTAL: {val}",
                        "metodo": "busqueda_texto_fallback",
                        "prioridad": 90
                    })
                    break  # Tomar solo el primero encontrado
        
        doc.close()
        
        # 4) Resultado: el primero encontrado
        valor_final = None
        if candidatos:
            valor_final = candidatos[0]["valor"]
        
        # Información de debug
        debug_info = {
            "xml_embebido_encontrado": valor_xml is not None,
            "candidatos_espaciales": len([c for c in candidatos if c.get("metodo") == "busqueda_espacial"]),
            "candidatos_fallback": len([c for c in candidatos if c.get("metodo") == "busqueda_texto_fallback"]),
            "total_candidatos": len(candidatos),
            "todos_los_numeros": [c["valor"] for c in candidatos] if candidatos else []
        }
        
        return {
            "valor_total": valor_final,
            "metodo": "xml_embebido" if valor_xml else ("busqueda_espacial" if candidatos else "no_encontrado"),
            "valores_encontrados": candidatos,
            "total_encontrados": len(candidatos),
            "texto_extraido": f"Encontrados {len(candidatos)} candidatos",
            "debug_info": debug_info
        }
        
    except Exception as e:
        return {
            "valor_total": None,
            "metodo": "error",
            "valores_encontrados": [],
            "total_encontrados": 0,
            "error": str(e)
        }


def _extraer_valor_total_xml(xml_content: str) -> Dict[str, Any]:
    """Extrae el valor total del XML del SRI"""
    
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_content)
        
        # Buscar en diferentes ubicaciones posibles
        valor_total = None
        ubicaciones = []
        
        # 1. En infoFactura/importeTotal
        importe_total = root.find(".//importeTotal")
        if importe_total is not None and importe_total.text:
            try:
                valor = float(importe_total.text.strip())
                valor_total = valor
                ubicaciones.append({
                    "ubicacion": "infoFactura/importeTotal",
                    "valor": valor,
                    "texto": importe_total.text.strip()
                })
            except ValueError:
                pass
        
        # 2. En totalConImpuestos (sumar todos los valores)
        total_con_impuestos = root.find(".//totalConImpuestos")
        if total_con_impuestos is not None:
            suma_impuestos = 0.0
            for total_imp in total_con_impuestos.findall(".//totalImpuesto"):
                valor_elem = total_imp.find("valor")
                if valor_elem is not None and valor_elem.text:
                    try:
                        suma_impuestos += float(valor_elem.text.strip())
                    except ValueError:
                        pass
            if suma_impuestos > 0:
                ubicaciones.append({
                    "ubicacion": "totalConImpuestos (suma)",
                    "valor": suma_impuestos,
                    "texto": str(suma_impuestos)
                })
                if valor_total is None:
                    valor_total = suma_impuestos
        
        # 3. En totalSinImpuestos
        total_sin_impuestos = root.find(".//totalSinImpuestos")
        if total_sin_impuestos is not None and total_sin_impuestos.text:
            try:
                valor = float(total_sin_impuestos.text.strip())
                ubicaciones.append({
                    "ubicacion": "totalSinImpuestos",
                    "valor": valor,
                    "texto": total_sin_impuestos.text.strip()
                })
            except ValueError:
                pass
        
        return {
            "valor_total": valor_total,
            "ubicaciones": ubicaciones,
            "total_ubicaciones": len(ubicaciones)
        }
        
    except Exception as e:
        return {
            "valor_total": None,
            "ubicaciones": [],
            "total_ubicaciones": 0,
            "error": str(e)
        }


async def _comparar_valores_totales_pdf_xml(pdf_bytes: bytes, xml_content: str) -> Dict[str, Any]:
    """Compara los valores totales entre PDF y XML del SRI"""
    
    try:
        # Extraer valor del PDF
        valor_pdf = _extraer_valor_total_pdf(pdf_bytes)
        
        # Extraer valor del XML
        valor_xml = _extraer_valor_total_xml(xml_content)
        
        # Comparar valores
        valores_coinciden = False
        diferencia = None
        porcentaje_diferencia = None
        
        if valor_pdf.get("valor_total") is not None and valor_xml.get("valor_total") is not None:
            val_pdf = valor_pdf["valor_total"]
            val_xml = valor_xml["valor_total"]
            
            diferencia = abs(val_pdf - val_xml)
            porcentaje_diferencia = (diferencia / val_xml) * 100 if val_xml != 0 else None
            
            # Considerar que coinciden si la diferencia es menor a 0.01 (1 centavo)
            valores_coinciden = diferencia < 0.01
        
        return {
            "valores_coinciden": valores_coinciden,
            "valor_pdf": valor_pdf.get("valor_total"),
            "valor_xml": valor_xml.get("valor_total"),
            "diferencia": diferencia,
            "porcentaje_diferencia": porcentaje_diferencia,
            "detalles_pdf": valor_pdf,
            "detalles_xml": valor_xml,
            "validacion": "EXITOSA" if valores_coinciden else "FALLO"
        }
        
    except Exception as e:
        return {
            "valores_coinciden": False,
            "valor_pdf": None,
            "valor_xml": None,
            "diferencia": None,
            "porcentaje_diferencia": None,
            "error": str(e),
            "validacion": "ERROR"
        }


def _extraer_clave_acceso_xml(xml_content: str) -> Optional[str]:
    """Extrae la clave de acceso de un XML"""
    
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_content)
        
        # Buscar clave de acceso en diferentes ubicaciones posibles
        for elem in root.iter():
            if elem.text and len(elem.text.strip()) == 49 and elem.text.strip().isalnum():
                return elem.text.strip()
        
        # Buscar por atributos
        for elem in root.iter():
            for attr_name, attr_value in elem.attrib.items():
                if len(attr_value) == 49 and attr_value.isalnum():
                    return attr_value
        
        return None
        
    except Exception:
        return None


def _extraer_numero_autorizacion_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extrae el número de autorización de un PDF usando la lógica robusta"""
    
    try:
        # Patrones para buscar
        LABELS = r"(n[uú]mero\s*de\s*autorizaci[oó]n|clave\s*de\s*acceso)"
        # 49 dígitos permitiendo espacios, guiones o no-break spaces entre medio
        DIG49 = r"(?:\d[\s\-\u2009\u00A0]*){49}"
        
        def normaliza_num(s: str) -> str:
            return re.sub(r"\D", "", s)  # deja solo dígitos
        
        # Abrir PDF desde bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Buscar en texto del PDF
        hallados, cerca_label = set(), set()
        full = []
        
        for p in doc:
            full.append(p.get_text())
            # búsqueda "cerca de la etiqueta": ventana de 0–150 chars después
            t = p.get_text()
            for m in re.finditer(LABELS, t, flags=re.I):
                trozo = t[m.end(): m.end()+150]
                n = re.search(DIG49, trozo, flags=re.I)
                if n:
                    cerca_label.add(normaliza_num(n.group()))
        
        all_text = "\n".join(full)
        for m in re.finditer(DIG49, all_text, flags=re.I):
            n = normaliza_num(m.group())
            if len(n) == 49:
                hallados.add(n)
        
        # Buscar en adjuntos XML
        xml_nums = set()
        for i in range(doc.embfile_count()):
            info = doc.embfile_info(i)
            name = (info.get("filename") or f"adjunto_{i}").lower()
            data = doc.embfile_get(i)
            if name.endswith(".xml") or b"<autorizacion" in data or b"<factura" in data:
                txt = data.decode("utf-8", "ignore")
                # <numeroAutorizacion> o <claveAcceso>
                for pat in [r"<numeroAutorizacion>(\d{49})</numeroAutorizacion>",
                            r"<claveAcceso>(\d{49})</claveAcceso>"]:
                    for m in re.finditer(pat, txt, flags=re.I):
                        xml_nums.add(m.group(1))
        
        doc.close()
        
        # Heurística de prioridad: cerca de etiqueta > en adjunto > cualquier 49
        candidatos = (list(cerca_label) or list(xml_nums) or list(hallados))
        
        return {
            "cerca_de_etiqueta": list(cerca_label),
            "en_adjuntos_xml": list(xml_nums),
            "en_texto_global": list(hallados),
            "numero_autorizacion": candidatos[0] if candidatos else None,
            "total_encontrados": len(candidatos)
        }
        
    except Exception as e:
        return {
            "cerca_de_etiqueta": [],
            "en_adjuntos_xml": [],
            "en_texto_global": [],
            "numero_autorizacion": None,
            "total_encontrados": 0,
            "error": str(e)
        }


def _detectar_tipo_documento(documento_bytes: bytes) -> str:
    """Detecta automáticamente el tipo de documento"""
    
    # Verificar si es PDF
    if documento_bytes.startswith(b'%PDF'):
        return "pdf"
    
    # Verificar si es XML
    try:
        contenido = documento_bytes.decode('utf-8')
        if contenido.strip().startswith('<?xml') or '<' in contenido and '>' in contenido:
            return "xml"
    except Exception:
        pass
    
    # Por defecto, asumir PDF
    return "pdf"


@router.get("/validar-firma-universal/ejemplo")
async def ejemplo_validacion_universal():
    """
    Proporciona ejemplos de uso del endpoint universal de validación.
    
    Returns:
        Ejemplos de uso y documentación
    """
    return {
        "endpoint": "POST /validar-firma-universal",
        "descripcion": "Validación universal de firmas digitales",
        "body": {
            "documento_base64": "string - Documento codificado en base64",
            "tipo_documento": "string - 'pdf', 'xml', o 'auto' (default: 'pdf')",
            "verificar_crypto": "boolean - Verificar firma criptográfica (default: false)",
            "verificar_cadena": "boolean - Verificar cadena de certificados (default: false)",
            "validar_autorizacion_sri": "boolean - Validar autorización en el SRI (default: false)"
        },
        "tipos_documento_soportados": {
            "pdf": "Documentos PDF con firmas digitales",
            "xml": "Documentos XML con firmas XAdES",
            "auto": "Detección automática del tipo de documento"
        },
        "tipos_firma_detectados": {
            "pdf": [
                "Firmas básicas (Adobe PKCS#7)",
                "PAdES (PDF Advanced Electronic Signatures)",
                "Firmas criptográficas (RSA/ECDSA)",
                "Documentos RIDE del SRI"
            ],
            "xml": [
                "XAdES (XML Advanced Electronic Signatures)",
                "Documentos fiscales del SRI",
                "Certificados digitales"
            ]
        },
        "respuesta_ejemplo": {
            "success": True,
            "mensaje": "Validación universal de firmas completada",
            "tipo_documento": "pdf",
            "resultado": {
                "firma_detectada": True,
                "tipo_firma": "pades",
                "es_pades": True,
                "es_documento_sri": False,
                "metodos_deteccion": {
                    "deteccion_basica": True,
                    "deteccion_patrones": True,
                    "confianza_patrones": 0.85
                },
                "resumen": {
                    "tiene_firma": True,
                    "total_firmas": 1,
                    "firmas_validas": 1,
                    "firmas_pades": 1,
                    "integridad_ok": 1,
                    "crypto_ok": 1,
                    "chain_ok": 1,
                    "autorizado_sri": True
                },
                "extraccion_autorizacion": {
                    "cerca_de_etiqueta": ["1234567890001123456789000112345678900011234567890001"],
                    "en_adjuntos_xml": [],
                    "en_texto_global": ["1234567890001123456789000112345678900011234567890001"],
                    "numero_autorizacion": "1234567890001123456789000112345678900011234567890001",
                    "total_encontrados": 1
                },
                "validacion_sri": {
                    "autorizado": True,
                    "mensaje": "Autorizado",
                    "clave_acceso": "1234567890001123456789000112345678900011234567890001",
                    "firma_xml_valida": True,
                    "comparacion_valores": {
                        "valores_coinciden": True,
                        "valor_pdf": 1610.00,
                        "valor_xml": 1610.00,
                        "diferencia": 0.00,
                        "porcentaje_diferencia": 0.0,
                        "validacion": "EXITOSA"
                    }
                }
            }
        }
    }
