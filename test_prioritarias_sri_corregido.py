#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de validación SRI en prioritarias corregido
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.validar_imagen import _evaluar_riesgo_imagen

def test_prioritarias_sri_corregido():
    """Test de validación SRI en prioritarias corregido"""
    print("🔬 TEST VALIDACIÓN SRI EN PRIORITARIAS CORREGIDO")
    print("=" * 60)
    
    # Simular datos de entrada
    imagen_bytes = b"fake_image_data"
    texto_extraido = "R.U.C.: 1790710319001\nFACTURA No. 026-200-000021384\nNUMERO DE AUTORIZACION\n0807202501179071031900120262000000213845658032318"
    
    # Caso 1: SRI verificado (sin penalización)
    print("\n1️⃣ CASO: SRI VERIFICADO")
    print("-" * 30)
    
    campos_factura_sri_ok = {
        "ruc": "1790710319001",
        "razonSocial": "ROCKO VERDEZOTO",
        "claveAcceso": "0807202501179071031900120262000000213845658032318",
        "sri_verificado": True,
        "validacion_sri": {
            "valido": True,
            "clave_acceso": "0807202501179071031900120262000000213845658032318",
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
            "timestamp": "2025-09-20T11:55:54.939069"
        }
    }
    
    analisis_forense = {
        "metadatos": {
            "exif": {},
            "xmp": {},
            "basicos": {}
        }
    }
    
    resultado_sri_ok = _evaluar_riesgo_imagen(imagen_bytes, texto_extraido, campos_factura_sri_ok, analisis_forense)
    
    print(f"Score: {resultado_sri_ok['score']}")
    print(f"Nivel: {resultado_sri_ok['nivel']}")
    print(f"Prioritarias: {len(resultado_sri_ok['prioritarias'])}")
    
    for i, check in enumerate(resultado_sri_ok['prioritarias']):
        print(f"  {i+1}. {check['check']} (penalización: {check['penalizacion']})")
        if check['check'] == "Validación SRI":
            print(f"     SRI Verificado: {check['detalle']['sri_verificado']}")
            print(f"     Estado: {check['detalle']['estado_sri']}")
            print(f"     RUC Emisor: {check['detalle']['ruc_emisor']}")
            print(f"     Tipo: {check['detalle']['tipo_comprobante']}")
            print(f"     Serie: {check['detalle']['serie']}")
            print(f"     Secuencial: {check['detalle']['secuencial']}")
            print(f"     Interpretación: {check['detalle']['interpretacion']}")
    
    # Verificar que los valores son correctos
    sri_check = next((check for check in resultado_sri_ok['prioritarias'] if check['check'] == "Validación SRI"), None)
    if sri_check:
        assert sri_check['detalle']['sri_verificado'] == True, f"Expected True, got {sri_check['detalle']['sri_verificado']}"
        assert sri_check['detalle']['estado_sri'] == "AUTORIZADO", f"Expected 'AUTORIZADO', got {sri_check['detalle']['estado_sri']}"
        assert sri_check['detalle']['ruc_emisor'] == "0117907103190", f"Expected '0117907103190', got {sri_check['detalle']['ruc_emisor']}"
        assert sri_check['penalizacion'] == 0, f"Expected 0, got {sri_check['penalizacion']}"
        print("✅ Valores correctos!")
    else:
        print("❌ No se encontró el check de Validación SRI")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_prioritarias_sri_corregido()
