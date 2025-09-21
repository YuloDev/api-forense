#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test local de validación SRI para PDFs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.sri_validator import integrar_validacion_sri

def test_pdf_sri_local():
    """Test local de validación SRI para PDFs"""
    print("🔬 TEST LOCAL VALIDACIÓN SRI PARA PDFS")
    print("=" * 50)
    
    # Datos de la factura (simulando el resultado del PDF)
    factura_data = {
        "ruc": "1790710319001",
        "razonSocial": "ROCKO VERDEZOTO",
        "fechaEmision": "2025-07-08T19:58:13",
        "importeTotal": 47.00,
        "claveAcceso": "0807202501179071031900120262000000213845658032318",
        "detalles": [],
        "totals": {
            "subtotal15": None,
            "subtotal0": None,
            "subtotal_no_objeto": None,
            "subtotal_sin_impuestos": None,
            "descuento": None,
            "iva15": None,
            "total": 47.00
        },
        "barcodes": [],
        "financial_checks": {},
        "metadata": {
            "invoice_number": "026-200-000021384",
            "authorization": "0807202501179071031900120262000000213845658032318",
            "environment": "PRODUCCION",
            "buyer_id": None,
            "emitter_name": "FARMACIAS Y COMISARIATOS DE MEDICINAS S.A.",
            "file_metadata": {
                "sha256": "test_hash",
                "pages_processed": 1,
                "text_methods": ["native"],
                "text_length": 1000
            }
        }
    }
    
    print("📄 Datos de entrada (PDF):")
    print(f"   RUC: {factura_data['ruc']}")
    print(f"   Clave Acceso: {factura_data['claveAcceso']}")
    print(f"   Número: {factura_data['metadata']['invoice_number']}")
    print(f"   Total: ${factura_data['importeTotal']}")
    
    print("\n🔍 Aplicando validación SRI...")
    
    # Aplicar validación SRI
    factura_con_sri = integrar_validacion_sri(factura_data)
    
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
    mensaje_sri = factura_con_sri.get("mensaje", "Análisis forense de PDF completado")
    
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
    
    # Simular respuesta completa del endpoint
    print("\n📋 Simulando respuesta completa del endpoint:")
    response = {
        "sri_verificado": sri_verificado,
        "mensaje": mensaje_sri,
        "tipo_archivo": "PDF",
        "coincidencia": "si" if sri_verificado else "no",
        "factura": factura_con_sri,
        "clave_acceso_parseada": {
            "valida": True,
            "clave_completa": "0807202501179071031900120262000000213845658032318",
            "fecha_emision": "0807-20-25",
            "ruc_emisor": "0117907103190",
            "tipo_comprobante": {
                "codigo": "01",
                "descripcion": "Factura"
            },
            "serie": "202",
            "secuencial": "620000002",
            "tipo_emision": {
                "codigo": "1",
                "descripcion": "Normal"
            },
            "codigo_numerico": "38456580",
            "digito_verificador": "3"
        }
    }
    
    print(f"   sri_verificado: {response['sri_verificado']}")
    print(f"   mensaje: {response['mensaje']}")
    print(f"   coincidencia: {response['coincidencia']}")
    print(f"   factura.sri_verificado: {response['factura']['sri_verificado']}")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_pdf_sri_local()
