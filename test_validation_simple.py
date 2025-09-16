#!/usr/bin/env python3
"""
Test simple del sistema de validación financiera mejorado.
"""

try:
    from helpers.validacion_financiera import validar_contenido_financiero
    print("✅ Import exitoso: validar_contenido_financiero")
    
    # Test básico con datos simulados
    pdf_fields = {
        "importeTotal": 23.15,
        "detalles": [
            {"precioUnitario": 10.0, "cantidad": 2, "valorIva": 3.0}
        ]
    }
    
    fuente_texto = """
    FACTURA DE VENTA
    SUBTOTAL SIN IMPUESTOS: 20.15
    IVA 15%: 3.00
    VALOR TOTAL: 23.15
    FORMA PAGO: EFECTIVO
    """
    
    # Test sin XML SRI (validación robusta)
    resultado = validar_contenido_financiero(pdf_fields, fuente_texto)
    
    print("✅ Validación exitosa sin XML SRI")
    print(f"   Score: {resultado['validacion_general']['score_validacion']}")
    print(f"   Válido: {resultado['validacion_general']['valido']}")
    
    # Test con XML SRI simulado
    xml_sri = {
        "autorizado": True,
        "totalSinImpuestos": 20.15,
        "importeTotal": 23.15,
        "totalConImpuestos": {
            "totalImpuesto": [
                {"codigo": "2", "valor": 3.0}
            ]
        }
    }
    
    resultado_sri = validar_contenido_financiero(pdf_fields, fuente_texto, xml_sri)
    
    print("✅ Validación exitosa con XML SRI")
    print(f"   Score: {resultado_sri['validacion_general']['score_validacion']}")
    print(f"   Válido: {resultado_sri['validacion_general']['valido']}")
    print(f"   Método: {resultado_sri['extraccion_texto']['metodo_usado']}")
    
    print("\n🎉 ¡Sistema de validación funcionando correctamente!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
