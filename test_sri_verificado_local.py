#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test local de la corrección del sri_verificado
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.sri_validator import integrar_validacion_sri

def test_sri_verificado_local():
    """Test local de la corrección del sri_verificado"""
    print("🔬 TEST LOCAL SRI_VERIFICADO CORREGIDO")
    print("=" * 50)
    
    # Datos de la factura (simulando el resultado del OCR)
    campos_factura = {
        "ruc": "1790710319001",
        "razonSocial": "ROCKO VERDEZOTO",
        "fechaEmision": "2025-07-08T19:58:13",
        "importeTotal": 1,
        "claveAcceso": "0807202501179071031900120262000000213845658032318",
        "detalles": [
            {
                "cantidad": 1,
                "descripcion": "forte\n\nForma Pago\n\nVator\n\nPlazo\n\nTlempo\n\nTARJETA DE CREDITO",
                "precioTotal": 1
            },
            {
                "cantidad": 1,
                "descripcion": "forte\n\nForma Pago\n\nVator\n\nPlazo\n\nTlempo\n\nTARJETA DE CREDITO",
                "precioTotal": 23
            },
            {
                "cantidad": 1,
                "descripcion": "forte\n\nForma Pago\n\nVator\n\nPlazo\n\nTlempo\n\nTARJETA DE CREDITO",
                "precioTotal": 23
            }
        ],
        "metadata": {
            "invoice_number": "026-200-000021384",
            "authorization": "0807202501179071031900120262000000213845658032318",
            "environment": "PRODUCCION",
            "buyer_id": None,
            "emitter_name": "FARMACIAS Y COMISARIATOS DE MEDICINAS S.A."
        }
    }
    
    print("📄 Datos de entrada:")
    print(f"   RUC: {campos_factura['ruc']}")
    print(f"   Clave Acceso: {campos_factura['claveAcceso']}")
    print(f"   Número: {campos_factura['metadata']['invoice_number']}")
    
    print("\n🔍 Aplicando validación SRI...")
    
    # Aplicar validación SRI
    factura_con_sri = integrar_validacion_sri(campos_factura)
    
    print("\n✅ Resultado de la validación:")
    print(f"   sri_verificado: {factura_con_sri.get('sri_verificado', False)}")
    print(f"   mensaje: {factura_con_sri.get('mensaje', 'N/A')}")
    
    # Verificar validacion_sri
    if 'validacion_sri' in factura_con_sri:
        validacion = factura_con_sri['validacion_sri']
        print(f"\n🔍 Detalles de validación:")
        print(f"   válido: {validacion.get('valido', False)}")
        print(f"   clave_acceso: {validacion.get('clave_acceso', 'N/A')}")
        
        if validacion.get('consulta_sri'):
            sri = validacion['consulta_sri']
            print(f"   estado: {sri.get('estado', 'N/A')}")
            print(f"   fecha_autorizacion: {sri.get('fecha_autorizacion', 'N/A')}")
    
    # Simular la lógica del endpoint
    print("\n🔄 Simulando lógica del endpoint:")
    sri_verificado = factura_con_sri.get("sri_verificado", False)
    mensaje_sri = factura_con_sri.get("mensaje", "Análisis forense de imagen PNG completado.")
    
    print(f"   sri_verificado (principal): {sri_verificado}")
    print(f"   mensaje (principal): {mensaje_sri}")
    
    # Verificar consistencia
    sri_verificado_factura = factura_con_sri.get('sri_verificado', False)
    if sri_verificado == sri_verificado_factura:
        print(f"\n✅ CONSISTENCIA: Los valores coinciden")
    else:
        print(f"\n❌ INCONSISTENCIA: Los valores NO coinciden")
        print(f"   Principal: {sri_verificado}")
        print(f"   Factura: {sri_verificado_factura}")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_sri_verificado_local()
