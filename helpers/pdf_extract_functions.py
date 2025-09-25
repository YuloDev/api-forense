"""
Funciones de extracción de PDF que fueron eliminadas del archivo pdf_extract.py.

Contiene las funciones necesarias para extraer información de facturas desde texto.
"""

import re
from typing import Dict, Any, Tuple, Optional
from helpers.invoice_capture_parser import extract_sri_access_key, extract_fields_from_text


def extract_clave_acceso_from_text(text: str) -> Tuple[Optional[str], str]:
    """
    Extrae la clave de acceso SRI desde texto de factura.
    
    Args:
        text: Texto extraído del PDF
        
    Returns:
        Tuple con (clave_acceso, etiqueta_encontrada)
    """
    if not text or not text.strip():
        return None, "Sin texto"
    
    try:
        # Usar la función existente del invoice_capture_parser
        clave = extract_sri_access_key(text)
        
        if clave:
            return clave, "Clave de acceso encontrada"
        else:
            return None, "Clave de acceso no encontrada"
            
    except Exception as e:
        return None, f"Error extrayendo clave: {str(e)}"


def extract_invoice_fields_from_text(text: str, clave_acceso: str = None, type: str = "factura") -> Dict[str, Any]:
    """
    Extrae campos de factura desde texto.
    
    Args:
        text: Texto extraído del PDF
        clave_acceso: Clave de acceso si ya se conoce
        type: Tipo de documento (factura, nota_credito, etc.)
        
    Returns:
        Dict con los campos extraídos
    """
    if not text or not text.strip():
        return {
            "ruc": None,
            "numero_factura": None,
            "clave_acceso": None,
            "fecha_emision": None,
            "total": None,
            "subtotal": None,
            "iva": None,
            "tipo_documento": type,
            "error": "Sin texto para procesar"
        }
    
    try:
        # Usar la función existente del invoice_capture_parser
        fields = extract_fields_from_text(text)
        
        # Mapear campos al formato esperado
        result = {
            "ruc": fields.get("ruc"),
            "numero_factura": fields.get("invoice_number"),
            "clave_acceso": clave_acceso or fields.get("access_key") or fields.get("authorization"),
            "fecha_emision": fields.get("date"),
            "total": fields.get("total"),
            "subtotal": fields.get("subtotal"),
            "iva": fields.get("iva"),
            "tipo_documento": type,
            "ambiente": fields.get("environment"),
            "punto_emision": fields.get("point_of_sale"),
            "establecimiento": fields.get("establishment"),
            "error": None
        }
        
        return result
        
    except Exception as e:
        return {
            "ruc": None,
            "numero_factura": None,
            "clave_acceso": clave_acceso,
            "fecha_emision": None,
            "total": None,
            "subtotal": None,
            "iva": None,
            "tipo_documento": type,
            "error": f"Error procesando texto: {str(e)}"
        }
