#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de validación SRI con la clave de acceso corregida
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.sri_validator import validar_factura_con_sri, integrar_validacion_sri

def test_validacion_sri():
    """Test de validación SRI"""
    print("🔬 TEST VALIDACIÓN SRI")
    print("=" * 50)
    
    # Datos de la factura corregida
    factura_data = {
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
    
    print("📄 Datos de la factura:")
    print(f"   RUC: {factura_data['ruc']}")
    print(f"   Razón Social: {factura_data['razonSocial']}")
    print(f"   Fecha: {factura_data['fechaEmision']}")
    print(f"   Clave Acceso: {factura_data['claveAcceso']}")
    print(f"   Número: {factura_data['metadata']['invoice_number']}")
    
    print("\n🔍 Validando con SRI...")
    
    # Test 1: Validación directa
    print("\n1️⃣ VALIDACIÓN DIRECTA")
    print("-" * 30)
    resultado = validar_factura_con_sri(factura_data)
    
    print(f"✅ Válido: {resultado.get('valido', False)}")
    if resultado.get('error'):
        print(f"❌ Error: {resultado['error']}")
    
    if resultado.get('consulta_sri'):
        sri = resultado['consulta_sri']
        print(f"📊 Estado SRI: {sri.get('estado', 'N/A')}")
        print(f"📊 Mensaje: {sri.get('mensaje', 'N/A')}")
        print(f"📊 Fecha Autorización: {sri.get('fecha_autorizacion', 'N/A')}")
    
    # Test 2: Integración completa
    print("\n2️⃣ INTEGRACIÓN COMPLETA")
    print("-" * 30)
    factura_integrada = integrar_validacion_sri(factura_data.copy())
    
    print(f"✅ SRI Verificado: {factura_integrada.get('sri_verificado', False)}")
    print(f"📝 Mensaje: {factura_integrada.get('mensaje', 'N/A')}")
    
    if 'validacion_sri' in factura_integrada:
        validacion = factura_integrada['validacion_sri']
        print(f"🔑 Clave Acceso: {validacion.get('clave_acceso', 'N/A')}")
        print(f"✅ Válido: {validacion.get('valido', False)}")
        
        if validacion.get('componentes'):
            comp = validacion['componentes']
            print(f"📅 Fecha Emisión: {comp.get('fecha_emision', 'N/A')}")
            print(f"🏢 RUC Emisor: {comp.get('ruc_emisor', 'N/A')}")
            print(f"📄 Tipo Comprobante: {comp.get('tipo_comprobante', 'N/A')}")
            print(f"🔢 Serie: {comp.get('serie', 'N/A')}")
            print(f"🔢 Secuencial: {comp.get('secuencial', 'N/A')}")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_validacion_sri()
