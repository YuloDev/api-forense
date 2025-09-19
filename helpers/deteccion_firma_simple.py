"""
Helper simple para detección de firmas digitales en PDFs desde base64.

Funcionalidad:
- Detección rápida de firmas digitales
- Análisis básico de metadatos de firma
- Compatible con base64
- Sin dependencias externas pesadas

Autor: Sistema de Análisis Forense
Versión: 1.0
"""

import base64
import re
from typing import Dict, Any, Optional
from .type_conversion import safe_serialize_dict, ensure_python_bool


def detectar_firma_desde_base64(pdf_base64: str) -> Dict[str, Any]:
    """
    Detecta si un PDF tiene firmas digitales desde base64.
    
    Args:
        pdf_base64: PDF codificado en base64
        
    Returns:
        Dict con información de detección de firma
    """
    try:
        # Decodificar PDF
        pdf_bytes = base64.b64decode(pdf_base64)
        
        # Detectar firmas usando patrones
        resultado = _detectar_firmas_patrones(pdf_bytes)
        
        return safe_serialize_dict(resultado)
        
    except Exception as e:
        return safe_serialize_dict({
            "firma_detectada": False,
            "error": f"Error procesando PDF: {str(e)}",
            "metadatos": {},
            "resumen": "Error en detección"
        })


def _detectar_firmas_patrones(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Detecta firmas digitales usando patrones de texto en el PDF.
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        
    Returns:
        Dict con información de detección
    """
    try:
        # Convertir a texto para búsqueda de patrones
        text = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Patrones de detección
        patrones_firma = [
            r'/ByteRange\s*\[',  # ByteRange es indicador de firma
            r'/Sig\b',           # Objeto de firma
            r'/DigitalSignature\b',  # Firma digital
            r'/Contents\s*<[0-9A-Fa-f\s]+>',  # Contenido de firma
            r'/SubFilter\s*/',   # Tipo de firma
            r'/Location\s*\(',   # Ubicación de firma
            r'/Reason\s*\(',     # Razón de firma
            r'/Name\s*\(',       # Nombre del firmante
        ]
        
        # Contar coincidencias
        coincidencias = {}
        for patron in patrones_firma:
            matches = re.findall(patron, text)
            coincidencias[patron] = len(matches)
        
        # Detectar si hay firma
        tiene_byterange = coincidencias.get(r'/ByteRange\s*\[', 0) > 0
        tiene_sig = coincidencias.get(r'/Sig\b', 0) > 0
        tiene_digitalsig = coincidencias.get(r'/DigitalSignature\b', 0) > 0
        tiene_contents = coincidencias.get(r'/Contents\s*<[0-9A-Fa-f\s]+>', 0) > 0
        
        firma_detectada = tiene_byterange or tiene_sig or tiene_digitalsig or tiene_contents
        
        # Extraer metadatos básicos
        metadatos = _extraer_metadatos_basicos(text)
        
        # Determinar tipo de firma
        tipo_firma = _determinar_tipo_firma(coincidencias, metadatos)
        
        # Generar resumen
        resumen = _generar_resumen_deteccion(firma_detectada, coincidencias, metadatos)
        
        return {
            "firma_detectada": ensure_python_bool(firma_detectada),
            "tipo_firma": tipo_firma,
            "metadatos": metadatos,
            "patrones_encontrados": coincidencias,
            "resumen": resumen,
            "confianza": _calcular_confianza_deteccion(coincidencias)
        }
        
    except Exception as e:
        return {
            "firma_detectada": False,
            "error": f"Error en detección: {str(e)}",
            "metadatos": {},
            "resumen": "Error en análisis"
        }


def _extraer_metadatos_basicos(text: str) -> Dict[str, Any]:
    """
    Extrae metadatos básicos de firma del texto del PDF.
    
    Args:
        text: Texto del PDF
        
    Returns:
        Dict con metadatos extraídos
    """
    metadatos = {}
    
    try:
        # Buscar SubFilter (tipo de firma)
        m_subfilter = re.search(r'/SubFilter\s*/([A-Za-z0-9\.\-]+)', text)
        if m_subfilter:
            metadatos['subfilter'] = m_subfilter.group(1)
        
        # Buscar Location (ubicación)
        m_location = re.search(r'/Location\s*\(([^)]+)\)', text)
        if m_location:
            metadatos['location'] = m_location.group(1)
        
        # Buscar Reason (razón)
        m_reason = re.search(r'/Reason\s*\(([^)]+)\)', text)
        if m_reason:
            metadatos['reason'] = m_reason.group(1)
        
        # Buscar Name (nombre del firmante)
        m_name = re.search(r'/Name\s*\(([^)]+)\)', text)
        if m_name:
            metadatos['name'] = m_name.group(1)
        
        # Buscar M (fecha de firma)
        m_date = re.search(r'/M\s*\(([^)]+)\)', text)
        if m_date:
            metadatos['signing_date'] = m_date.group(1)
        
        # Buscar ContactInfo
        m_contact = re.search(r'/ContactInfo\s*\(([^)]+)\)', text)
        if m_contact:
            metadatos['contact_info'] = m_contact.group(1)
        
        # Contar número de firmas
        byterange_matches = re.findall(r'/ByteRange\s*\[', text)
        metadatos['numero_firmas'] = len(byterange_matches)
        
    except Exception as e:
        metadatos['error_metadatos'] = str(e)
    
    return metadatos


def _determinar_tipo_firma(coincidencias: Dict[str, int], metadatos: Dict[str, Any]) -> str:
    """
    Determina el tipo de firma basado en los patrones encontrados.
    
    Args:
        coincidencias: Diccionario con conteo de patrones
        metadatos: Metadatos extraídos
        
    Returns:
        Tipo de firma detectado
    """
    if coincidencias.get(r'/ByteRange\s*\[', 0) == 0:
        return "ninguna"
    
    # Verificar si es Adobe Signature
    if metadatos.get('subfilter') == 'adbe.pkcs7.detached':
        return "adobe_pkcs7"
    
    # Verificar si es PAdES
    if 'pades' in str(metadatos.get('subfilter', '')).lower():
        return "pades"
    
    # Verificar si es XAdES
    if 'xades' in str(metadatos.get('subfilter', '')).lower():
        return "xades"
    
    # Verificar si tiene metadatos completos
    if metadatos.get('name') and metadatos.get('reason'):
        return "avanzada"
    
    # Verificar si tiene al menos ByteRange y Contents
    if coincidencias.get(r'/Contents\s*<[0-9A-Fa-f\s]+>', 0) > 0:
        return "basica"
    
    return "indeterminada"


def _generar_resumen_deteccion(firma_detectada: bool, coincidencias: Dict[str, int], 
                             metadatos: Dict[str, Any]) -> str:
    """
    Genera un resumen legible de la detección.
    
    Args:
        firma_detectada: Si se detectó firma
        coincidencias: Conteo de patrones
        metadatos: Metadatos extraídos
        
    Returns:
        Resumen en texto legible
    """
    if not firma_detectada:
        return "❌ No se detectaron firmas digitales en el documento"
    
    num_firmas = metadatos.get('numero_firmas', 0)
    tipo_firma = _determinar_tipo_firma(coincidencias, metadatos)
    
    resumen = f"✅ Se detectaron {num_firmas} firma(s) digital(es)"
    
    if tipo_firma != "indeterminada":
        resumen += f" (Tipo: {tipo_firma})"
    
    if metadatos.get('name'):
        resumen += f" - Firmante: {metadatos['name']}"
    
    if metadatos.get('location'):
        resumen += f" - Ubicación: {metadatos['location']}"
    
    return resumen


def _calcular_confianza_deteccion(coincidencias: Dict[str, int]) -> float:
    """
    Calcula un nivel de confianza para la detección.
    
    Args:
        coincidencias: Conteo de patrones encontrados
        
    Returns:
        Nivel de confianza entre 0.0 y 1.0
    """
    # Peso de cada patrón
    pesos = {
        r'/ByteRange\s*\[': 0.4,  # Más importante
        r'/Sig\b': 0.2,
        r'/DigitalSignature\b': 0.2,
        r'/Contents\s*<[0-9A-Fa-f\s]+>': 0.3,
        r'/SubFilter\s*/': 0.1,
        r'/Location\s*\(': 0.05,
        r'/Reason\s*\(': 0.05,
        r'/Name\s*\(': 0.05,
    }
    
    confianza = 0.0
    for patron, peso in pesos.items():
        if coincidencias.get(patron, 0) > 0:
            confianza += peso
    
    return min(1.0, confianza)


def validar_firma_rapida(pdf_base64: str) -> Dict[str, Any]:
    """
    Validación rápida de firma digital desde base64.
    
    Args:
        pdf_base64: PDF codificado en base64
        
    Returns:
        Dict con resultado de validación rápida
    """
    try:
        # Decodificar PDF
        pdf_bytes = base64.b64decode(pdf_base64)
        
        # Detección básica
        deteccion = _detectar_firmas_patrones(pdf_bytes)
        
        # Validación simple
        es_valida = (
            deteccion.get('firma_detectada', False) and
            deteccion.get('confianza', 0.0) > 0.3
        )
        
        return safe_serialize_dict({
            "firma_detectada": deteccion.get('firma_detectada', False),
            "es_valida": ensure_python_bool(es_valida),
            "confianza": deteccion.get('confianza', 0.0),
            "tipo": deteccion.get('tipo_firma', 'ninguna'),
            "metadatos": deteccion.get('metadatos', {}),
            "resumen": deteccion.get('resumen', 'Sin información')
        })
        
    except Exception as e:
        return safe_serialize_dict({
            "firma_detectada": False,
            "es_valida": False,
            "confianza": 0.0,
            "tipo": "error",
            "metadatos": {},
            "resumen": f"Error: {str(e)}"
        })
