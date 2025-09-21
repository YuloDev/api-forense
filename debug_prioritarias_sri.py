#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug de prioritarias SRI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_prioritarias_sri():
    """Debug de prioritarias SRI"""
    print("🔬 DEBUG PRIORITARIAS SRI")
    print("=" * 50)
    
    # Simular datos como los del JSON real
    campos_factura = {
        "ruc": "1790710319001",
        "razonSocial": "ROCKO VERDEZOTO",
        "claveAcceso": "0807202501179071031900120262000000213845658032318",
        "sri_verificado": True,
        "validacion_sri": {
            "valido": True,
            "clave_acceso": "0807202501179071031900120262000000213845658032318",
            "componentes": {
                "fecha_emision": "0807-20-25",
                "ruc_emisor": "0117907103190",
                "tipo_comprobante": "01",
                "serie": "202",
                "secuencial": "620000002",
                "tipo_emision": "1",
                "codigo_numerico": "38456580",
                "digito_verificador": "3"
            },
            "consulta_sri": {
                "valido": True,
                "estado": "AUTORIZADO",
                "fecha_autorizacion": "2025-07-08T19:58:13",
                "ambiente": "PRODUCCION",
                "mensaje": "Documento válido según SRI",
                "detalles": {
                    "ruc_emisor": "1790710319001",
                    "numero_documento": "026-200-000021384",
                    "clave_acceso": "0807202501179071031900120262000000213845658032318",
                    "fecha_consulta": "2025-09-20T11:55:54.939051"
                }
            },
            "timestamp": "2025-09-20T11:55:54.939069"
        }
    }
    
    print("📄 Datos de entrada:")
    print(f"   sri_verificado: {campos_factura.get('sri_verificado')}")
    print(f"   clave_acceso: {campos_factura.get('claveAcceso')}")
    print(f"   validacion_sri.valido: {campos_factura.get('validacion_sri', {}).get('valido')}")
    print(f"   validacion_sri.consulta_sri.estado: {campos_factura.get('validacion_sri', {}).get('consulta_sri', {}).get('estado')}")
    print(f"   validacion_sri.componentes.ruc_emisor: {campos_factura.get('validacion_sri', {}).get('componentes', {}).get('ruc_emisor')}")
    
    # Simular la lógica de prioritarias
    validacion_sri = campos_factura.get("validacion_sri", {})
    sri_verificado = campos_factura.get("sri_verificado", False)
    clave_acceso = campos_factura.get("claveAcceso", "")
    
    print(f"\n🔍 Valores extraídos:")
    print(f"   validacion_sri: {validacion_sri}")
    print(f"   sri_verificado: {sri_verificado}")
    print(f"   clave_acceso: {clave_acceso}")
    
    print(f"\n🔍 Acceso a datos:")
    print(f"   validacion_sri.get('valido'): {validacion_sri.get('valido', False)}")
    print(f"   validacion_sri.get('consulta_sri', {{}}).get('estado'): {validacion_sri.get('consulta_sri', {}).get('estado', 'No disponible')}")
    print(f"   validacion_sri.get('consulta_sri', {{}}).get('fecha_autorizacion'): {validacion_sri.get('consulta_sri', {}).get('fecha_autorizacion', 'No disponible')}")
    print(f"   validacion_sri.get('componentes', {{}}).get('ruc_emisor'): {validacion_sri.get('componentes', {}).get('ruc_emisor', 'No disponible')}")
    print(f"   validacion_sri.get('componentes', {{}}).get('tipo_comprobante'): {validacion_sri.get('componentes', {}).get('tipo_comprobante', 'No disponible')}")
    print(f"   validacion_sri.get('componentes', {{}}).get('serie'): {validacion_sri.get('componentes', {}).get('serie', 'No disponible')}")
    print(f"   validacion_sri.get('componentes', {{}}).get('secuencial'): {validacion_sri.get('componentes', {}).get('secuencial', 'No disponible')}")
    
    print("\n✅ Debug completado!")

if __name__ == "__main__":
    debug_prioritarias_sri()
