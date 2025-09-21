#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de validación SRI en prioritarias
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.validar_imagen import _evaluar_riesgo_imagen

def test_prioritarias_sri():
    """Test de validación SRI en prioritarias"""
    print("🔬 TEST VALIDACIÓN SRI EN PRIORITARIAS")
    print("=" * 50)
    
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
                "estado": "AUTORIZADO",
                "fecha_autorizacion": "2025-07-08T19:58:13"
            },
            "componentes": {
                "ruc_emisor": "0117907103190",
                "tipo_comprobante": "01",
                "serie": "202",
                "secuencial": "620000002"
            }
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
            print(f"     Interpretación: {check['detalle']['interpretacion']}")
    
    # Caso 2: SRI no verificado (con penalización)
    print("\n2️⃣ CASO: SRI NO VERIFICADO")
    print("-" * 30)
    
    campos_factura_sri_ko = {
        "ruc": "1790710319001",
        "razonSocial": "ROCKO VERDEZOTO",
        "claveAcceso": "0807202501179071031900120262000000213845658032318",
        "sri_verificado": False,
        "validacion_sri": {
            "valido": False,
            "clave_acceso": "0807202501179071031900120262000000213845658032318",
            "consulta_sri": {
                "estado": "ERROR",
                "fecha_autorizacion": "No disponible"
            },
            "componentes": {
                "ruc_emisor": "0117907103190",
                "tipo_comprobante": "01",
                "serie": "202",
                "secuencial": "620000002"
            }
        }
    }
    
    resultado_sri_ko = _evaluar_riesgo_imagen(imagen_bytes, texto_extraido, campos_factura_sri_ko, analisis_forense)
    
    print(f"Score: {resultado_sri_ko['score']}")
    print(f"Nivel: {resultado_sri_ko['nivel']}")
    print(f"Prioritarias: {len(resultado_sri_ko['prioritarias'])}")
    
    for i, check in enumerate(resultado_sri_ko['prioritarias']):
        print(f"  {i+1}. {check['check']} (penalización: {check['penalizacion']})")
        if check['check'] == "Validación SRI":
            print(f"     SRI Verificado: {check['detalle']['sri_verificado']}")
            print(f"     Estado: {check['detalle']['estado_sri']}")
            print(f"     Interpretación: {check['detalle']['interpretacion']}")
    
    # Caso 3: Sin clave de acceso (con penalización)
    print("\n3️⃣ CASO: SIN CLAVE DE ACCESO")
    print("-" * 30)
    
    campos_factura_sin_clave = {
        "ruc": "1790710319001",
        "razonSocial": "ROCKO VERDEZOTO",
        "claveAcceso": "",
        "sri_verificado": False,
        "validacion_sri": {}
    }
    
    resultado_sin_clave = _evaluar_riesgo_imagen(imagen_bytes, texto_extraido, campos_factura_sin_clave, analisis_forense)
    
    print(f"Score: {resultado_sin_clave['score']}")
    print(f"Nivel: {resultado_sin_clave['nivel']}")
    print(f"Prioritarias: {len(resultado_sin_clave['prioritarias'])}")
    
    for i, check in enumerate(resultado_sin_clave['prioritarias']):
        print(f"  {i+1}. {check['check']} (penalización: {check['penalizacion']})")
        if check['check'] == "Validación SRI":
            print(f"     SRI Verificado: {check['detalle']['sri_verificado']}")
            print(f"     Clave Acceso: {check['detalle']['clave_acceso']}")
            print(f"     Interpretación: {check['detalle']['interpretacion']}")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_prioritarias_sri()
