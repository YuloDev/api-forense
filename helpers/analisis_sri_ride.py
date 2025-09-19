"""
Módulo para análisis de documentos del SRI (RIDE).

Implementa análisis específico para:
1. Documentos RIDE del SRI (sin firma digital propia)
2. Detección de firmas XAdES en XMLs relacionados
3. Validación de integridad de documentos fiscales
4. Análisis de metadatos fiscales

Autor: Sistema de Análisis Forense
Versión: 1.0
"""

import re
import base64
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .validacion_xades import validar_xades
from .type_conversion import safe_serialize_dict, ensure_python_bool


def analizar_documento_sri(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Analiza un documento del SRI (RIDE) para detectar firmas digitales.
    
    Args:
        pdf_bytes: Contenido del PDF del RIDE
        
    Returns:
        Dict con análisis del documento SRI
    """
    try:
        # Convertir a texto para análisis
        text = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Análisis básico del documento
        analisis_basico = _analizar_documento_basico(text)
        
        # Buscar referencias a XMLs firmados
        referencias_xml = _buscar_referencias_xml(text)
        
        # Buscar metadatos fiscales
        metadatos_fiscales = _extraer_metadatos_fiscales(text)
        
        # Determinar tipo de documento
        tipo_documento = _determinar_tipo_documento(text, metadatos_fiscales)
        
        # Generar resumen
        resumen = _generar_resumen_sri(analisis_basico, referencias_xml, metadatos_fiscales)
        
        return safe_serialize_dict({
            "tipo_documento": tipo_documento,
            "firma_detectada": False,  # Los RIDE no tienen firma propia
            "analisis_basico": analisis_basico,
            "referencias_xml": referencias_xml,
            "metadatos_fiscales": metadatos_fiscales,
            "resumen": resumen,
            "observaciones": _generar_observaciones_sri(tipo_documento, referencias_xml)
        })
        
    except Exception as e:
        return safe_serialize_dict({
            "tipo_documento": "desconocido",
            "firma_detectada": False,
            "error": f"Error en análisis: {str(e)}",
            "resumen": "Error en análisis"
        })


def _analizar_documento_basico(text: str) -> Dict[str, Any]:
    """Analiza el documento básico del SRI"""
    analisis = {
        "es_ride": False,
        "version_pdf": None,
        "fecha_generacion": None,
        "numero_documento": None,
        "ruc_emisor": None,
        "razon_social": None,
        "patrones_detectados": []
    }
    
    # Detectar si es un RIDE
    patrones_ride = [
        r"RIDE",
        r"RUC:\s*\d{13}",
        r"Razón Social:",
        r"Fecha de Emisión:",
        r"Número de Autorización:",
        r"Clave de Acceso:",
        r"Ambiente:",
        r"Tipo de Emisión:"
    ]
    
    for patron in patrones_ride:
        if re.search(patron, text, re.IGNORECASE):
            analisis["patrones_detectados"].append(patron)
            if patron == "RIDE":
                analisis["es_ride"] = True
    
    # Detectar versión PDF
    version_match = re.search(r'%PDF-(\d\.\d)', text)
    if version_match:
        analisis["version_pdf"] = version_match.group(1)
    
    # Extraer información específica del RIDE
    if analisis["es_ride"]:
        # RUC del emisor
        ruc_match = re.search(r'RUC:\s*(\d{13})', text)
        if ruc_match:
            analisis["ruc_emisor"] = ruc_match.group(1)
        
        # Razón social
        razon_match = re.search(r'Razón Social:\s*([^\n]+)', text)
        if razon_match:
            analisis["razon_social"] = razon_match.group(1).strip()
        
        # Fecha de emisión
        fecha_match = re.search(r'Fecha de Emisión:\s*([^\n]+)', text)
        if fecha_match:
            analisis["fecha_generacion"] = fecha_match.group(1).strip()
        
        # Número de documento
        num_match = re.search(r'Número:\s*([^\n]+)', text)
        if num_match:
            analisis["numero_documento"] = num_match.group(1).strip()
    
    return analisis


def _buscar_referencias_xml(text: str) -> List[Dict[str, Any]]:
    """Busca referencias a XMLs firmados en el documento"""
    referencias = []
    
    # Patrones para buscar referencias a XMLs
    patrones_xml = [
        r'Clave de Acceso:\s*([A-Z0-9]{49})',
        r'XML:\s*([^\n]+)',
        r'Archivo XML:\s*([^\n]+)',
        r'Firma Digital:\s*([^\n]+)',
        r'Certificado:\s*([^\n]+)'
    ]
    
    for patron in patrones_xml:
        matches = re.findall(patron, text, re.IGNORECASE)
        for match in matches:
            referencias.append({
                "tipo": "referencia_xml",
                "valor": match,
                "patron": patron
            })
    
    # Buscar URLs o rutas de archivos
    url_patterns = [
        r'https?://[^\s]+',
        r'file://[^\s]+',
        r'[A-Za-z]:\\[^\s]+',
        r'/[^\s]+\.xml'
    ]
    
    for patron in url_patterns:
        matches = re.findall(patron, text)
        for match in matches:
            referencias.append({
                "tipo": "url_archivo",
                "valor": match,
                "patron": patron
            })
    
    return referencias


def _extraer_metadatos_fiscales(text: str) -> Dict[str, Any]:
    """Extrae metadatos fiscales del documento"""
    metadatos = {
        "ambiente": None,
        "tipo_emision": None,
        "tipo_documento": None,
        "establecimiento": None,
        "punto_emision": None,
        "secuencial": None,
        "clave_acceso": None,
        "numero_autorizacion": None,
        "fecha_autorizacion": None,
        "total": None,
        "moneda": None
    }
    
    # Ambiente
    ambiente_match = re.search(r'Ambiente:\s*([^\n]+)', text, re.IGNORECASE)
    if ambiente_match:
        metadatos["ambiente"] = ambiente_match.group(1).strip()
    
    # Tipo de emisión
    tipo_emision_match = re.search(r'Tipo de Emisión:\s*([^\n]+)', text, re.IGNORECASE)
    if tipo_emision_match:
        metadatos["tipo_emision"] = tipo_emision_match.group(1).strip()
    
    # Tipo de documento
    tipo_doc_match = re.search(r'Tipo de Documento:\s*([^\n]+)', text, re.IGNORECASE)
    if tipo_doc_match:
        metadatos["tipo_documento"] = tipo_doc_match.group(1).strip()
    
    # Establecimiento
    estab_match = re.search(r'Establecimiento:\s*([^\n]+)', text, re.IGNORECASE)
    if estab_match:
        metadatos["establecimiento"] = estab_match.group(1).strip()
    
    # Punto de emisión
    punto_match = re.search(r'Punto de Emisión:\s*([^\n]+)', text, re.IGNORECASE)
    if punto_match:
        metadatos["punto_emision"] = punto_match.group(1).strip()
    
    # Secuencial
    secuencial_match = re.search(r'Secuencial:\s*([^\n]+)', text, re.IGNORECASE)
    if secuencial_match:
        metadatos["secuencial"] = secuencial_match.group(1).strip()
    
    # Clave de acceso
    clave_match = re.search(r'Clave de Acceso:\s*([A-Z0-9]{49})', text)
    if clave_match:
        metadatos["clave_acceso"] = clave_match.group(1)
    
    # Número de autorización
    auth_match = re.search(r'Número de Autorización:\s*([^\n]+)', text, re.IGNORECASE)
    if auth_match:
        metadatos["numero_autorizacion"] = auth_match.group(1).strip()
    
    # Fecha de autorización
    fecha_auth_match = re.search(r'Fecha de Autorización:\s*([^\n]+)', text, re.IGNORECASE)
    if fecha_auth_match:
        metadatos["fecha_autorizacion"] = fecha_auth_match.group(1).strip()
    
    # Total
    total_match = re.search(r'Total:\s*([^\n]+)', text, re.IGNORECASE)
    if total_match:
        metadatos["total"] = total_match.group(1).strip()
    
    # Moneda
    moneda_match = re.search(r'Moneda:\s*([^\n]+)', text, re.IGNORECASE)
    if moneda_match:
        metadatos["moneda"] = moneda_match.group(1).strip()
    
    return metadatos


def _determinar_tipo_documento(text: str, metadatos: Dict[str, Any]) -> str:
    """Determina el tipo de documento del SRI"""
    
    # Verificar si es RIDE
    if "RIDE" in text.upper():
        return "ride"
    
    # Verificar tipo de documento fiscal
    tipo_doc = metadatos.get("tipo_documento", "").upper()
    if "FACTURA" in tipo_doc:
        return "factura"
    elif "NOTA DE CRÉDITO" in tipo_doc or "NOTA DE CREDITO" in tipo_doc:
        return "nota_credito"
    elif "NOTA DE DÉBITO" in tipo_doc or "NOTA DE DEBITO" in tipo_doc:
        return "nota_debito"
    elif "RETENCIÓN" in tipo_doc or "RETENCION" in tipo_doc:
        return "retencion"
    elif "LIQUIDACIÓN" in tipo_doc or "LIQUIDACION" in tipo_doc:
        return "liquidacion"
    elif "GUÍA" in tipo_doc or "GUIA" in tipo_doc:
        return "guia_remision"
    
    # Verificar por patrones en el texto
    if re.search(r'FACTURA', text, re.IGNORECASE):
        return "factura"
    elif re.search(r'NOTA DE CRÉDITO|NOTA DE CREDITO', text, re.IGNORECASE):
        return "nota_credito"
    elif re.search(r'NOTA DE DÉBITO|NOTA DE DEBITO', text, re.IGNORECASE):
        return "nota_debito"
    elif re.search(r'RETENCIÓN|RETENCION', text, re.IGNORECASE):
        return "retencion"
    elif re.search(r'LIQUIDACIÓN|LIQUIDACION', text, re.IGNORECASE):
        return "liquidacion"
    elif re.search(r'GUÍA|GUIA', text, re.IGNORECASE):
        return "guia_remision"
    
    return "documento_fiscal"


def _generar_resumen_sri(analisis_basico: Dict[str, Any], 
                        referencias_xml: List[Dict[str, Any]], 
                        metadatos_fiscales: Dict[str, Any]) -> Dict[str, Any]:
    """Genera resumen del análisis del SRI"""
    
    return {
        "es_documento_sri": analisis_basico.get("es_ride", False),
        "tiene_referencias_xml": len(referencias_xml) > 0,
        "cantidad_referencias": len(referencias_xml),
        "tiene_metadatos_fiscales": any(metadatos_fiscales.values()),
        "ambiente": metadatos_fiscales.get("ambiente"),
        "tipo_emision": metadatos_fiscales.get("tipo_emision"),
        "ruc_emisor": metadatos_fiscales.get("ruc_emisor") or analisis_basico.get("ruc_emisor"),
        "razon_social": metadatos_fiscales.get("razon_social") or analisis_basico.get("razon_social"),
        "clave_acceso": metadatos_fiscales.get("clave_acceso"),
        "numero_autorizacion": metadatos_fiscales.get("numero_autorizacion")
    }


def _generar_observaciones_sri(tipo_documento: str, referencias_xml: List[Dict[str, Any]]) -> List[str]:
    """Genera observaciones sobre el documento del SRI"""
    observaciones = []
    
    if tipo_documento == "ride":
        observaciones.append("Documento RIDE del SRI - No contiene firma digital propia")
        observaciones.append("El RIDE es una vista/impresión del documento fiscal")
        observaciones.append("La firma digital se encuentra en el XML original")
    
    if referencias_xml:
        observaciones.append(f"Se encontraron {len(referencias_xml)} referencias a XMLs")
        for ref in referencias_xml:
            if ref["tipo"] == "referencia_xml":
                observaciones.append(f"Clave de acceso encontrada: {ref['valor']}")
    
    if not referencias_xml:
        observaciones.append("No se encontraron referencias a XMLs firmados")
        observaciones.append("El documento puede ser una copia o impresión")
    
    return observaciones


def validar_xml_firmado_sri(xml_content: str) -> Dict[str, Any]:
    """
    Valida un XML firmado del SRI usando XAdES.
    
    Args:
        xml_content: Contenido XML del documento fiscal
        
    Returns:
        Resultado de validación XAdES del XML
    """
    try:
        # Validar XAdES
        resultado_xades = validar_xades(xml_content)
        
        # Análisis específico del SRI
        analisis_sri = _analizar_xml_sri(xml_content)
        
        # Combinar resultados
        resultado_completo = {
            "validacion_xades": resultado_xades,
            "analisis_sri": analisis_sri,
            "es_documento_sri": analisis_sri.get("es_documento_sri", False),
            "firma_valida": resultado_xades.get("firma_detectada", False) and 
                           resultado_xades.get("resumen", {}).get("firmas_validas", 0) > 0
        }
        
        return safe_serialize_dict(resultado_completo)
        
    except Exception as e:
        return safe_serialize_dict({
            "error": f"Error en validación: {str(e)}",
            "es_documento_sri": False,
            "firma_valida": False
        })


def _analizar_xml_sri(xml_content: str) -> Dict[str, Any]:
    """Analiza un XML del SRI para detectar metadatos fiscales"""
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_content)
        
        # Buscar información fiscal
        info_fiscal = {
            "es_documento_sri": False,
            "ruc_emisor": None,
            "razon_social": None,
            "numero_documento": None,
            "fecha_emision": None,
            "clave_acceso": None,
            "ambiente": None,
            "tipo_emision": None
        }
        
        # Buscar en todos los elementos
        for elem in root.iter():
            if elem.text and elem.text.strip():
                text = elem.text.strip()
                
                # RUC (13 dígitos)
                if re.match(r'^\d{13}$', text):
                    info_fiscal["ruc_emisor"] = text
                
                # Clave de acceso (49 caracteres alfanuméricos)
                if re.match(r'^[A-Z0-9]{49}$', text):
                    info_fiscal["clave_acceso"] = text
                    info_fiscal["es_documento_sri"] = True
                
                # Fecha (formato YYYY-MM-DD)
                if re.match(r'^\d{4}-\d{2}-\d{2}', text):
                    info_fiscal["fecha_emision"] = text
        
        # Buscar por atributos
        for elem in root.iter():
            for attr_name, attr_value in elem.attrib.items():
                if attr_value:
                    # RUC
                    if re.match(r'^\d{13}$', attr_value):
                        info_fiscal["ruc_emisor"] = attr_value
                    
                    # Clave de acceso
                    if re.match(r'^[A-Z0-9]{49}$', attr_value):
                        info_fiscal["clave_acceso"] = attr_value
                        info_fiscal["es_documento_sri"] = True
        
        return info_fiscal
        
    except Exception as e:
        return {
            "es_documento_sri": False,
            "error": str(e)
        }


def generar_reporte_sri(analisis_result: Dict[str, Any]) -> str:
    """
    Genera un reporte legible del análisis del SRI.
    
    Args:
        analisis_result: Resultado de analizar_documento_sri
        
    Returns:
        Reporte en texto legible
    """
    if not analisis_result.get("tipo_documento"):
        return "❌ No se pudo determinar el tipo de documento"
    
    report = []
    report.append("🏛️ ANÁLISIS DE DOCUMENTO SRI")
    report.append("=" * 50)
    
    # Información básica
    tipo_doc = analisis_result.get("tipo_documento", "desconocido")
    report.append(f"📄 Tipo de documento: {tipo_doc.upper()}")
    
    analisis_basico = analisis_result.get("analisis_basico", {})
    if analisis_basico.get("es_ride"):
        report.append("📋 Documento: RIDE (Representación Impresa de Documento Electrónico)")
        report.append("⚠️  Nota: Los RIDE no contienen firma digital propia")
        report.append("🔍 La firma digital se encuentra en el XML original")
    
    # Metadatos fiscales
    metadatos = analisis_result.get("metadatos_fiscales", {})
    if metadatos:
        report.append("\n📊 METADATOS FISCALES:")
        if metadatos.get("ruc_emisor"):
            report.append(f"   RUC: {metadatos['ruc_emisor']}")
        if metadatos.get("razon_social"):
            report.append(f"   Razón Social: {metadatos['razon_social']}")
        if metadatos.get("numero_documento"):
            report.append(f"   Número: {metadatos['numero_documento']}")
        if metadatos.get("fecha_emision"):
            report.append(f"   Fecha: {metadatos['fecha_emision']}")
        if metadatos.get("clave_acceso"):
            report.append(f"   Clave de Acceso: {metadatos['clave_acceso']}")
        if metadatos.get("ambiente"):
            report.append(f"   Ambiente: {metadatos['ambiente']}")
        if metadatos.get("tipo_emision"):
            report.append(f"   Tipo de Emisión: {metadatos['tipo_emision']}")
    
    # Referencias XML
    referencias = analisis_result.get("referencias_xml", [])
    if referencias:
        report.append(f"\n🔗 REFERENCIAS XML ({len(referencias)}):")
        for i, ref in enumerate(referencias, 1):
            report.append(f"   {i}. {ref['tipo']}: {ref['valor']}")
    else:
        report.append("\n⚠️  No se encontraron referencias a XMLs firmados")
    
    # Observaciones
    observaciones = analisis_result.get("observaciones", [])
    if observaciones:
        report.append("\n📝 OBSERVACIONES:")
        for obs in observaciones:
            report.append(f"   - {obs}")
    
    # Resumen
    resumen = analisis_result.get("resumen", {})
    if resumen:
        report.append("\n📈 RESUMEN:")
        report.append(f"   Es documento SRI: {'Sí' if resumen.get('es_documento_sri') else 'No'}")
        report.append(f"   Tiene referencias XML: {'Sí' if resumen.get('tiene_referencias_xml') else 'No'}")
        report.append(f"   Cantidad de referencias: {resumen.get('cantidad_referencias', 0)}")
    
    return "\n".join(report)
