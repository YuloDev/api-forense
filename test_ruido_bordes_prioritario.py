#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de Ruido y bordes como prioritario
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.validar_imagen import _evaluar_riesgo_imagen

def test_ruido_bordes_prioritario():
    """Test de Ruido y bordes como prioritario"""
    print("🔬 TEST RUIDO Y BORDES COMO PRIORITARIO")
    print("=" * 50)
    
    # Simular datos de entrada
    imagen_bytes = b"fake_image_data"
    texto_extraido = "R.U.C.: 1790710319001\nFACTURA No. 026-200-000021384\nNUMERO DE AUTORIZACION\n0807202501179071031900120262000000213845658032318"
    
    # Caso 1: Con edición local detectada (con penalización)
    print("\n1️⃣ CASO: CON EDICIÓN LOCAL DETECTADA")
    print("-" * 40)
    
    campos_factura = {
        "ruc": "1790710319001",
        "razonSocial": "ROCKO VERDEZOTO",
        "claveAcceso": "0807202501179071031900120262000000213845658032318",
        "sri_verificado": True,
        "validacion_sri": {
            "valido": True,
            "consulta_sri": {"estado": "AUTORIZADO"},
            "componentes": {"ruc_emisor": "0117907103190", "tipo_comprobante": "01", "serie": "202", "secuencial": "620000002"}
        }
    }
    
    analisis_forense_con_edicion = {
        "metadatos": {
            "exif": {},
            "xmp": {},
            "basicos": {}
        },
        "analisis_forense": {
            "ruido_bordes": {
                "tiene_edicion_local": True,
                "nivel_sospecha": "MEDIO",
                "laplacian_variance": 9046.25,
                "edge_density": 0.0944,
                "num_lines": 315,
                "parallel_lines": 3,
                "outlier_ratio": 0.0333,
                "gradient_peaks": 39470,
                "peak_ratio": 0.0748
            }
        }
    }
    
    resultado_con_edicion = _evaluar_riesgo_imagen(imagen_bytes, texto_extraido, campos_factura, analisis_forense_con_edicion)
    
    print(f"Score: {resultado_con_edicion['score']}")
    print(f"Nivel: {resultado_con_edicion['nivel']}")
    print(f"Prioritarias: {len(resultado_con_edicion['prioritarias'])}")
    
    for i, check in enumerate(resultado_con_edicion['prioritarias']):
        print(f"  {i+1}. {check['check']} (penalización: {check['penalizacion']})")
        if check['check'] == "Ruido y bordes":
            print(f"     Detectado: {check['detalle']['detectado']}")
            print(f"     Nivel Sospecha: {check['detalle']['nivel_sospecha']}")
            print(f"     Ratio Outliers: {check['detalle']['outlier_ratio']:.2%}")
            print(f"     Líneas Paralelas: {check['detalle']['parallel_lines']}")
            print(f"     Interpretación: {check['detalle']['interpretacion']}")
            print(f"     Umbral Sugerido: {check['detalle']['umbral_sugerido']}")
    
    # Caso 2: Sin edición local detectada (sin penalización)
    print("\n2️⃣ CASO: SIN EDICIÓN LOCAL DETECTADA")
    print("-" * 40)
    
    analisis_forense_sin_edicion = {
        "metadatos": {
            "exif": {},
            "xmp": {},
            "basicos": {}
        },
        "analisis_forense": {
            "ruido_bordes": {
                "tiene_edicion_local": False,
                "nivel_sospecha": "BAJO",
                "laplacian_variance": 2000.0,
                "edge_density": 0.05,
                "num_lines": 100,
                "parallel_lines": 0,
                "outlier_ratio": 0.01,
                "gradient_peaks": 10000,
                "peak_ratio": 0.02
            }
        }
    }
    
    resultado_sin_edicion = _evaluar_riesgo_imagen(imagen_bytes, texto_extraido, campos_factura, analisis_forense_sin_edicion)
    
    print(f"Score: {resultado_sin_edicion['score']}")
    print(f"Nivel: {resultado_sin_edicion['nivel']}")
    print(f"Prioritarias: {len(resultado_sin_edicion['prioritarias'])}")
    
    for i, check in enumerate(resultado_sin_edicion['prioritarias']):
        print(f"  {i+1}. {check['check']} (penalización: {check['penalizacion']})")
        if check['check'] == "Ruido y bordes":
            print(f"     Detectado: {check['detalle']['detectado']}")
            print(f"     Nivel Sospecha: {check['detalle']['nivel_sospecha']}")
            print(f"     Ratio Outliers: {check['detalle']['outlier_ratio']:.2%}")
            print(f"     Líneas Paralelas: {check['detalle']['parallel_lines']}")
            print(f"     Interpretación: {check['detalle']['interpretacion']}")
    
    # Verificar que el check está en prioritarias
    ruido_check_con = next((check for check in resultado_con_edicion['prioritarias'] if check['check'] == "Ruido y bordes"), None)
    ruido_check_sin = next((check for check in resultado_sin_edicion['prioritarias'] if check['check'] == "Ruido y bordes"), None)
    
    if ruido_check_con and ruido_check_sin:
        print("\n✅ Ruido y bordes aparece correctamente en prioritarias!")
        print(f"   Con edición: penalización {ruido_check_con['penalizacion']}")
        print(f"   Sin edición: penalización {ruido_check_sin['penalizacion']}")
    else:
        print("\n❌ Ruido y bordes NO aparece en prioritarias!")
    
    print("\n✅ Test completado!")

if __name__ == "__main__":
    test_ruido_bordes_prioritario()
