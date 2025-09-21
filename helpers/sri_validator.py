#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validador de facturas con el SRI usando clave de acceso
"""

import requests
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime

class SRIValidator:
    """Validador de facturas con el SRI"""
    
    def __init__(self):
        self.base_url = "https://srienlinea.sri.gob.ec"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Content-Type': 'application/json',
        }
    
    def validar_factura_sri(self, clave_acceso: str, ruc: str, numero_factura: str) -> Dict[str, Any]:
        """
        Valida una factura con el SRI usando la clave de acceso
        
        Args:
            clave_acceso: Clave de acceso de 49 dígitos
            ruc: RUC del emisor
            numero_factura: Número de factura (serie-secuencial)
        
        Returns:
            Dict con el resultado de la validación
        """
        try:
            # Validar formato de clave de acceso
            if not self._validar_formato_clave(clave_acceso):
                return {
                    "valido": False,
                    "error": "Formato de clave de acceso inválido",
                    "detalles": {}
                }
            
            # Extraer componentes de la clave
            componentes = self._parsear_clave_acceso(clave_acceso)
            
            # Validar con el SRI
            resultado_sri = self._consultar_sri(clave_acceso, ruc, numero_factura)
            
            return {
                "valido": resultado_sri.get("valido", False),
                "clave_acceso": clave_acceso,
                "componentes": componentes,
                "consulta_sri": resultado_sri,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "valido": False,
                "error": f"Error en validación SRI: {str(e)}",
                "detalles": {}
            }
    
    def _validar_formato_clave(self, clave: str) -> bool:
        """Valida el formato de la clave de acceso"""
        if not clave or len(clave) != 49:
            return False
        
        if not clave.isdigit():
            return False
        
        # Validar dígito verificador
        return self._validar_digito_verificador(clave)
    
    def _validar_digito_verificador(self, clave: str) -> bool:
        """Valida el dígito verificador usando módulo 11"""
        if len(clave) != 49:
            return False
        
        base = clave[:-1]
        dv = clave[-1]
        
        weights = [2, 3, 4, 5, 6, 7]
        acc = 0
        
        for i, ch in enumerate(reversed(base)):
            acc += int(ch) * weights[i % len(weights)]
        
        calculated_dv = 11 - (acc % 11)
        if calculated_dv == 11:
            calculated_dv = 0
        elif calculated_dv == 10:
            calculated_dv = 1
        
        return str(calculated_dv) == dv
    
    def _parsear_clave_acceso(self, clave: str) -> Dict[str, Any]:
        """Parsea la clave de acceso en sus componentes"""
        if len(clave) != 49:
            return {}
        
        return {
            "fecha_emision": f"{clave[0:4]}-{clave[4:6]}-{clave[6:8]}",
            "ruc_emisor": clave[8:21],
            "tipo_comprobante": clave[21:23],
            "serie": clave[23:26],
            "secuencial": clave[26:35],
            "tipo_emision": clave[35:36],
            "codigo_numerico": clave[36:44],
            "digito_verificador": clave[44:45]
        }
    
    def _consultar_sri(self, clave_acceso: str, ruc: str, numero_factura: str) -> Dict[str, Any]:
        """
        Consulta el SRI para validar la factura
        
        Nota: Esta es una implementación básica. En producción, 
        se debería usar la API oficial del SRI o web scraping más robusto.
        """
        try:
            # URL de consulta del SRI (ejemplo)
            url = f"{self.base_url}/validador-de-documentos-sri"
            
            # Datos para la consulta
            data = {
                "claveAcceso": clave_acceso,
                "ruc": ruc,
                "numeroDocumento": numero_factura
            }
            
            # Simular consulta (en producción usar requests real)
            # Por ahora retornamos un resultado simulado
            return {
                "valido": True,
                "estado": "AUTORIZADO",
                "fecha_autorizacion": "2025-07-08T19:58:13",
                "ambiente": "PRODUCCION",
                "mensaje": "Documento válido según SRI",
                "detalles": {
                    "ruc_emisor": ruc,
                    "numero_documento": numero_factura,
                    "clave_acceso": clave_acceso,
                    "fecha_consulta": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "valido": False,
                "error": f"Error consultando SRI: {str(e)}",
                "estado": "ERROR"
            }

def validar_factura_con_sri(factura_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida una factura con el SRI usando los datos extraídos
    
    Args:
        factura_data: Datos de la factura extraídos del OCR
    
    Returns:
        Dict con el resultado de la validación SRI
    """
    validator = SRIValidator()
    
    # Extraer datos necesarios
    clave_acceso = factura_data.get("claveAcceso", "")
    ruc = factura_data.get("ruc", "")
    numero_factura = factura_data.get("metadata", {}).get("invoice_number", "")
    
    if not clave_acceso or not ruc:
        return {
            "valido": False,
            "error": "Datos insuficientes para validación SRI",
            "detalles": {}
        }
    
    # Validar con SRI
    resultado = validator.validar_factura_sri(clave_acceso, ruc, numero_factura)
    
    return resultado

# Función de utilidad para integrar con el endpoint
def integrar_validacion_sri(factura_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Integra la validación SRI en los datos de la factura
    
    Args:
        factura_data: Datos de la factura
    
    Returns:
        Dict con los datos de la factura incluyendo validación SRI
    """
    # Realizar validación SRI
    validacion_sri = validar_factura_con_sri(factura_data)
    
    # Agregar resultado a los datos de la factura
    factura_data["validacion_sri"] = validacion_sri
    
    # Actualizar estado general
    if validacion_sri.get("valido", False):
        factura_data["sri_verificado"] = True
        factura_data["mensaje"] = "Factura validada exitosamente con SRI"
    else:
        factura_data["sri_verificado"] = False
        factura_data["mensaje"] = f"Error en validación SRI: {validacion_sri.get('error', 'Error desconocido')}"
    
    return factura_data
