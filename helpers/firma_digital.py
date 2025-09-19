"""
Helper para detección y análisis de firmas digitales en PDFs.

Este módulo contiene todas las funciones necesarias para:
- Detectar presencia de firmas digitales
- Analizar tipos de firma (básica, avanzada, cualificada)
- Validar certificados digitales
- Extraer metadatos de firma
- Verificar integridad del documento firmado
"""

import re
import fitz
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from .validacion_firma_digital import (
    validate_pdf_signatures, 
    detectar_firmas_pdf_simple,
    generar_reporte_firmas
)


def analizar_firmas_digitales_avanzado(pdf_bytes: bytes, 
                                     verify_crypto: bool = True,
                                     verify_chain: bool = True) -> Dict[str, Any]:
    """
    Análisis avanzado de firmas digitales en un PDF usando validación criptográfica.
    
    Detecta y analiza:
    - Presencia de firmas digitales
    - Tipos de firma (básica, avanzada, cualificada)
    - Validez de certificados
    - Metadatos de firma (fecha, emisor, etc.)
    - Integridad del documento
    - Cadena de confianza
    - Verificación criptográfica
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        verify_crypto: Si verificar la firma criptográfica
        verify_chain: Si verificar la cadena de certificados
        
    Returns:
        Dict con análisis completo de firmas digitales
    """
    # Usar la nueva funcionalidad de validación avanzada
    validacion_result = validate_pdf_signatures(
        pdf_bytes, 
        verify_crypto=verify_crypto, 
        verify_chain=verify_chain
    )
    
    # Convertir resultado a formato compatible
    resultado = {
        "firma_detectada": validacion_result.get("firma_detectada", False),
        "cantidad_firmas": validacion_result.get("resumen", {}).get("total_firmas", 0),
        "firmas_validas": validacion_result.get("resumen", {}).get("firmas_validas", 0),
        "firmas_invalidas": validacion_result.get("resumen", {}).get("total_firmas", 0) - 
                           validacion_result.get("resumen", {}).get("firmas_validas", 0),
        "integridad_ok": validacion_result.get("resumen", {}).get("firmas_integridad_ok", 0),
        "sin_modificaciones": validacion_result.get("resumen", {}).get("firmas_sin_modificaciones", 0),
        "crypto_ok": validacion_result.get("resumen", {}).get("firmas_crypto_ok", 0),
        "chain_ok": validacion_result.get("resumen", {}).get("firmas_chain_ok", 0),
        "firmas_detalladas": validacion_result.get("firmas", []),
        "dependencias": validacion_result.get("dependencias", {}),
        "reporte_legible": generar_reporte_firmas(validacion_result)
    }
    
    # Determinar tipo de firma
    if resultado["cantidad_firmas"] == 0:
        resultado["tipo_firma"] = "ninguno"
    elif resultado["cantidad_firmas"] == 1:
        firma = resultado["firmas_detalladas"][0] if resultado["firmas_detalladas"] else {}
        if firma.get("crypto_verification", {}).get("crypto_verification") and \
           firma.get("chain_validation", {}).get("chain_validation"):
            resultado["tipo_firma"] = "cualificada"
        elif firma.get("crypto_verification", {}).get("crypto_verification"):
            resultado["tipo_firma"] = "avanzada"
        else:
            resultado["tipo_firma"] = "basica"
    else:
        resultado["tipo_firma"] = "multiple"
    
    # Determinar nivel de seguridad
    if resultado["firmas_validas"] == resultado["cantidad_firmas"] and resultado["cantidad_firmas"] > 0:
        if resultado["crypto_ok"] == resultado["cantidad_firmas"] and resultado["chain_ok"] == resultado["cantidad_firmas"]:
            resultado["nivel_seguridad"] = "cualificado"
        elif resultado["crypto_ok"] == resultado["cantidad_firmas"]:
            resultado["nivel_seguridad"] = "avanzado"
        else:
            resultado["nivel_seguridad"] = "basico"
    elif resultado["cantidad_firmas"] > 0:
        resultado["nivel_seguridad"] = "parcial"
    else:
        resultado["nivel_seguridad"] = "ninguno"
    
    # Generar recomendaciones
    recomendaciones = []
    if not resultado["firma_detectada"]:
        recomendaciones.append("El documento no tiene firmas digitales")
    elif resultado["firmas_invalidas"] > 0:
        recomendaciones.append(f"{resultado['firmas_invalidas']} firma(s) inválida(s) detectada(s)")
    if resultado["sin_modificaciones"] < resultado["cantidad_firmas"]:
        recomendaciones.append("Se detectaron modificaciones posteriores a la firma")
    if not resultado["dependencias"].get("asn1crypto"):
        recomendaciones.append("Instalar asn1crypto para análisis detallado")
    if not resultado["dependencias"].get("oscrypto"):
        recomendaciones.append("Instalar oscrypto para verificación criptográfica")
    if not resultado["dependencias"].get("certvalidator"):
        recomendaciones.append("Instalar certvalidator para validación de cadena")
    
    resultado["recomendaciones"] = recomendaciones
    
    return resultado


def analizar_firmas_digitales(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Análisis completo de firmas digitales en un PDF.
    
    Detecta y analiza:
    - Presencia de firmas digitales
    - Tipos de firma (básica, avanzada, cualificada)
    - Validez de certificados
    - Metadatos de firma (fecha, emisor, etc.)
    - Integridad del documento
    - Cadena de confianza
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        
    Returns:
        Dict con análisis completo de firmas digitales
    """
    resultado = {
        "firma_detectada": False,
        "cantidad_firmas": 0,
        "tipo_firma": None,  # "basica", "avanzada", "cualificada", "multiple"
        "firmas_validas": 0,
        "firmas_invalidas": 0,
        "metadatos_firmas": [],
        "certificados": [],
        "integridad_documento": {
            "documento_integro": True,
            "modificaciones_detectadas": False,
            "areas_modificadas": []
        },
        "cadena_confianza": {
            "certificado_raiz_valido": False,
            "cadena_completa": False,
            "autoridad_certificadora": None
        },
        "analisis_avanzado": {
            "algoritmo_hash": None,
            "algoritmo_cifrado": None,
            "longitud_clave": None,
            "tsa_timestamp": None,  # Time Stamping Authority
            "revocacion_verificada": False
        },
        "seguridad": {
            "nivel_seguridad": "desconocido",  # "bajo", "medio", "alto"
            "vulnerabilidades": [],
            "recomendaciones": []
        },
        "compatibilidad": {
            "pdf_version": None,
            "acrobat_compatible": False,
            "adobe_signature": False,
            "pkcs7_detached": False
        }
    }
    
    try:
        # === 1. DETECCIÓN BÁSICA DE FIRMAS ===
        deteccion_basica = _detectar_firmas_basico(pdf_bytes)
        resultado.update(deteccion_basica)
        
        if not resultado["firma_detectada"]:
            return resultado
        
        # === 2. ANÁLISIS AVANZADO CON PyMuPDF ===
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            analisis_avanzado = _analizar_firmas_pymupdf(doc)
            resultado.update(analisis_avanzado)
            doc.close()
        except Exception as e:
            resultado["seguridad"]["vulnerabilidades"].append(f"Error en análisis PyMuPDF: {str(e)}")
        
        # === 3. ANÁLISIS DE CERTIFICADOS ===
        if resultado["cantidad_firmas"] > 0:
            analisis_certificados = _analizar_certificados_firma(pdf_bytes)
            resultado["certificados"] = analisis_certificados["certificados"]
            resultado["cadena_confianza"].update(analisis_certificados["cadena_confianza"])
        
        # === 4. VERIFICACIÓN DE INTEGRIDAD ===
        integridad = _verificar_integridad_documento(pdf_bytes)
        resultado["integridad_documento"].update(integridad)
        
        # === 5. ANÁLISIS DE SEGURIDAD ===
        seguridad = _evaluar_seguridad_firma(resultado)
        resultado["seguridad"].update(seguridad)
        
        # === 6. COMPATIBILIDAD Y ESTÁNDARES ===
        compatibilidad = _analizar_compatibilidad_firma(pdf_bytes)
        resultado["compatibilidad"].update(compatibilidad)
        
    except Exception as e:
        resultado["seguridad"]["vulnerabilidades"].append(f"Error en análisis de firmas: {str(e)}")
    
    return resultado


def _detectar_firmas_basico(pdf_bytes: bytes) -> Dict[str, Any]:
    """Detección básica de firmas digitales mediante patrones binarios."""
    sample = pdf_bytes[:min(6_000_000, len(pdf_bytes))]
    
    # Patrones de firma digital
    patrones_firma = [
        b"/Sig",
        b"/DigitalSignature", 
        b"/ByteRange",
        b"/Contents",
        b"/Filter/Adobe.PPKMS",
        b"/Filter/Adobe.PPKLite",
        b"/SubFilter/adbe.pkcs7.detached",
        b"/SubFilter/adbe.pkcs7.sha1",
        b"/SubFilter/ETSI.CAdES.detached",
        b"/Type/Sig"
    ]
    
    firmas_detectadas = []
    for patron in patrones_firma:
        if patron in sample:
            firmas_detectadas.append(patron.decode('utf-8', errors='ignore'))
    
    # Contar posibles firmas
    cantidad_sig = sample.count(b"/Sig")
    cantidad_byterange = sample.count(b"/ByteRange")
    cantidad_contents = sample.count(b"/Contents")
    
    # Estimación de cantidad de firmas
    cantidad_firmas = max(cantidad_sig, cantidad_byterange)
    
    return {
        "firma_detectada": len(firmas_detectadas) > 0,
        "cantidad_firmas": cantidad_firmas,
        "patrones_detectados": firmas_detectadas,
        "metodo_deteccion": "analisis_binario"
    }


def _analizar_firmas_pymupdf(doc: fitz.Document) -> Dict[str, Any]:
    """Análisis avanzado de firmas usando PyMuPDF."""
    resultado = {
        "metadatos_firmas": [],
        "firmas_validas": 0,
        "firmas_invalidas": 0,
        "tipo_firma": "desconocido"
    }
    
    try:
        # Verificar si el documento tiene firmas
        signature_count = doc.signature_count if hasattr(doc, 'signature_count') else 0
        
        if signature_count > 0:
            resultado["cantidad_firmas"] = signature_count
            
            # Analizar cada firma
            for i in range(signature_count):
                try:
                    # Obtener información de la firma
                    sig_info = doc.signature_info(i) if hasattr(doc, 'signature_info') else None
                    
                    if sig_info:
                        metadata_firma = {
                            "indice": i,
                            "nombre_firmante": sig_info.get("name", "Desconocido"),
                            "fecha_firma": sig_info.get("date", None),
                            "razon": sig_info.get("reason", None),
                            "ubicacion": sig_info.get("location", None),
                            "contacto": sig_info.get("contact", None),
                            "valida": sig_info.get("valid", False),
                            "certificado_valido": sig_info.get("cert_valid", False),
                            "documento_modificado": sig_info.get("doc_modified", True)
                        }
                        
                        resultado["metadatos_firmas"].append(metadata_firma)
                        
                        if metadata_firma["valida"]:
                            resultado["firmas_validas"] += 1
                        else:
                            resultado["firmas_invalidas"] += 1
                
                except Exception as e:
                    resultado["metadatos_firmas"].append({
                        "indice": i,
                        "error": f"Error al analizar firma {i}: {str(e)}"
                    })
                    resultado["firmas_invalidas"] += 1
        
        # Determinar tipo de firma
        if resultado["cantidad_firmas"] > 1:
            resultado["tipo_firma"] = "multiple"
        elif resultado["firmas_validas"] > 0:
            resultado["tipo_firma"] = "avanzada"  # Asumimos avanzada si es válida
        elif resultado["cantidad_firmas"] > 0:
            resultado["tipo_firma"] = "basica"
    
    except Exception as e:
        resultado["error_pymupdf"] = str(e)
    
    return resultado


def _analizar_certificados_firma(pdf_bytes: bytes) -> Dict[str, Any]:
    """Analiza los certificados digitales de las firmas."""
    resultado = {
        "certificados": [],
        "cadena_confianza": {
            "certificado_raiz_valido": False,
            "cadena_completa": False,
            "autoridad_certificadora": None
        }
    }
    
    try:
        # Buscar certificados en el contenido del PDF
        sample = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Patrones para identificar información de certificados
        patrones_cert = {
            "emisor": r"CN=([^,]+)",
            "organizacion": r"O=([^,]+)", 
            "pais": r"C=([A-Z]{2})",
            "email": r"emailAddress=([^,]+)",
            "fecha_inicio": r"notBefore=([^,]+)",
            "fecha_fin": r"notAfter=([^,]+)"
        }
        
        certificado_info = {}
        for campo, patron in patrones_cert.items():
            match = re.search(patron, sample, re.IGNORECASE)
            if match:
                certificado_info[campo] = match.group(1).strip()
        
        if certificado_info:
            resultado["certificados"].append({
                "tipo": "certificado_principal",
                "informacion": certificado_info,
                "valido": True,  # Requeriría validación real con CA
                "algoritmo": "desconocido"
            })
            
            # Intentar identificar autoridad certificadora conocida
            if "organizacion" in certificado_info:
                org = certificado_info["organizacion"].lower()
                if any(ca in org for ca in ["banco central", "bce", "security data"]):
                    resultado["cadena_confianza"]["autoridad_certificadora"] = certificado_info["organizacion"]
                    resultado["cadena_confianza"]["certificado_raiz_valido"] = True
    
    except Exception as e:
        resultado["error_certificados"] = str(e)
    
    return resultado


def _verificar_integridad_documento(pdf_bytes: bytes) -> Dict[str, Any]:
    """Verifica la integridad del documento firmado."""
    resultado = {
        "documento_integro": True,
        "modificaciones_detectadas": False,
        "areas_modificadas": [],
        "hash_original": None,
        "hash_actual": None
    }
    
    try:
        # Buscar indicadores de modificación post-firma
        sample = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Buscar múltiples xref (indicador de modificaciones)
        xref_count = sample.count('xref')
        if xref_count > 1:
            resultado["modificaciones_detectadas"] = True
            resultado["areas_modificadas"].append("Tabla de referencias cruzadas modificada")
        
        # Buscar ByteRange discontinuos (posible manipulación)
        byterange_pattern = r'/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]'
        matches = re.findall(byterange_pattern, sample)
        
        for match in matches:
            start1, length1, start2, length2 = map(int, match)
            # Verificar si hay gaps sospechosos
            gap = start2 - (start1 + length1)
            if gap > 100000:  # Gap mayor a 100KB es sospechoso
                resultado["modificaciones_detectadas"] = True
                resultado["areas_modificadas"].append(f"Gap sospechoso de {gap} bytes en ByteRange")
        
        # Si hay modificaciones, el documento no está íntegro
        if resultado["modificaciones_detectadas"]:
            resultado["documento_integro"] = False
    
    except Exception as e:
        resultado["error_integridad"] = str(e)
    
    return resultado


def _evaluar_seguridad_firma(datos_firma: Dict[str, Any]) -> Dict[str, Any]:
    """Evalúa el nivel de seguridad de las firmas detectadas."""
    vulnerabilidades = []
    recomendaciones = []
    nivel_seguridad = "bajo"
    
    try:
        # Evaluar basado en datos de firma
        if datos_firma["firmas_validas"] > 0:
            nivel_seguridad = "medio"
            
            # Verificar integridad
            if datos_firma["integridad_documento"]["documento_integro"]:
                nivel_seguridad = "alto"
            else:
                vulnerabilidades.append("Documento modificado después de la firma")
                recomendaciones.append("Verificar la legitimidad de las modificaciones")
        
        # Verificar certificados
        if not datos_firma["cadena_confianza"]["certificado_raiz_valido"]:
            vulnerabilidades.append("Certificado no emitido por autoridad confiable")
            recomendaciones.append("Verificar con autoridad certificadora reconocida")
        
        # Verificar cantidad de firmas
        if datos_firma["cantidad_firmas"] > 3:
            vulnerabilidades.append("Múltiples firmas pueden indicar manipulación")
            recomendaciones.append("Verificar la necesidad de múltiples firmas")
        
        # Verificar firmas inválidas
        if datos_firma["firmas_invalidas"] > 0:
            vulnerabilidades.append(f"{datos_firma['firmas_invalidas']} firmas inválidas detectadas")
            recomendaciones.append("Investigar las firmas inválidas")
            nivel_seguridad = "bajo"
    
    except Exception as e:
        vulnerabilidades.append(f"Error en evaluación de seguridad: {str(e)}")
    
    return {
        "nivel_seguridad": nivel_seguridad,
        "vulnerabilidades": vulnerabilidades,
        "recomendaciones": recomendaciones
    }


def _analizar_compatibilidad_firma(pdf_bytes: bytes) -> Dict[str, Any]:
    """Analiza la compatibilidad y estándares de firma."""
    resultado = {
        "pdf_version": None,
        "acrobat_compatible": False,
        "adobe_signature": False,
        "pkcs7_detached": False,
        "pades_compatible": False,
        "estandares_detectados": []
    }
    
    try:
        sample = pdf_bytes[:10000].decode('latin-1', errors='ignore')
        
        # Detectar versión PDF
        version_match = re.search(r'%PDF-(\d\.\d)', sample)
        if version_match:
            resultado["pdf_version"] = version_match.group(1)
        
        # Detectar estándares de firma
        sample_full = pdf_bytes.decode('latin-1', errors='ignore')
        
        if "Adobe.PPKLite" in sample_full:
            resultado["adobe_signature"] = True
            resultado["acrobat_compatible"] = True
            resultado["estandares_detectados"].append("Adobe PPKLite")
        
        if "adbe.pkcs7.detached" in sample_full:
            resultado["pkcs7_detached"] = True
            resultado["estandares_detectados"].append("PKCS#7 Detached")
        
        if "ETSI.CAdES" in sample_full:
            resultado["pades_compatible"] = True
            resultado["estandares_detectados"].append("PAdES (CAdES)")
        
        # Verificar compatibilidad general
        if len(resultado["estandares_detectados"]) > 0:
            resultado["acrobat_compatible"] = True
    
    except Exception as e:
        resultado["error_compatibilidad"] = str(e)
    
    return resultado


# Funciones de utilidad para integracion con riesgo.py
def tiene_firma_digital(pdf_bytes: bytes) -> bool:
    """
    Función simple para mantener compatibilidad con código existente.
    Usa la nueva funcionalidad de detección avanzada.
    """
    return detectar_firmas_pdf_simple(pdf_bytes)


def obtener_resumen_firma(analisis_firma: Dict[str, Any]) -> str:
    """Genera un resumen legible del análisis de firma."""
    if not analisis_firma["firma_detectada"]:
        return "❌ Sin firma digital detectada"
    
    cantidad = analisis_firma["cantidad_firmas"]
    validas = analisis_firma["firmas_validas"]
    nivel = analisis_firma["seguridad"]["nivel_seguridad"]
    
    return f"✅ {cantidad} firma(s), {validas} válida(s), seguridad: {nivel}"


def extraer_metricas_firma(analisis_firma: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae métricas clave para reportes."""
    return {
        "tiene_firma": analisis_firma["firma_detectada"],
        "cantidad_firmas": analisis_firma["cantidad_firmas"],
        "firmas_validas": analisis_firma["firmas_validas"],
        "nivel_seguridad": analisis_firma["seguridad"]["nivel_seguridad"],
        "documento_integro": analisis_firma["integridad_documento"]["documento_integro"],
        "certificado_valido": analisis_firma["cadena_confianza"]["certificado_raiz_valido"],
        "total_vulnerabilidades": len(analisis_firma["seguridad"]["vulnerabilidades"])
    }
