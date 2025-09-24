#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilidades para el sistema de reclamos
"""

import json
import os
from datetime import datetime


def obtener_siguiente_id(ultimo_id: str = None) -> str:
    """
    Obtener el siguiente ID disponible para un reclamo
    """
    try:
        # Si se proporciona un último ID, extraer el número
        if ultimo_id:
            # Extraer número del ID (ej: "CLM-000001" -> 1)
            import re
            match = re.search(r'(\d+)$', ultimo_id)
            if match:
                siguiente_numero = int(match.group(1)) + 1
            else:
                siguiente_numero = 1
        else:
            # Usar configuración
            config_file = "reclamos_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    siguiente_numero = config.get("ultimo_id", 0) + 1
            else:
                siguiente_numero = 1
        
        # Generar ID con formato
        config_file = "reclamos_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {
                "prefijo": "CLM",
                "formato": "CLM-{secuencial:06d}",
                "ejemplo": "CLM-000001"
            }
        
        formato = config.get("formato", "CLM-{secuencial:06d}")
        id_reclamo = formato.format(secuencial=siguiente_numero)
        
        # Actualizar último ID en configuración
        config["ultimo_id"] = siguiente_numero
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return id_reclamo
        
    except Exception as e:
        print(f"Error obteniendo siguiente ID: {e}")
        # Fallback: usar timestamp
        timestamp = int(datetime.now().timestamp())
        return f"CLM-{timestamp:06d}"


def generar_id_reclamo() -> str:
    """
    Generar un ID único para un reclamo
    """
    try:
        # Obtener siguiente ID
        siguiente_id = obtener_siguiente_id()
        
        # Cargar configuración
        config_file = "reclamos_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {
                "prefijo": "CLM",
                "formato": "CLM-{secuencial:06d}",
                "ejemplo": "CLM-000001"
            }
        
        # Generar ID con formato
        formato = config.get("formato", "CLM-{secuencial:06d}")
        id_reclamo = formato.format(secuencial=siguiente_id)
        
        # Actualizar último ID
        config["ultimo_id"] = siguiente_id
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return id_reclamo
        
    except Exception as e:
        print(f"Error generando ID de reclamo: {e}")
        # Fallback: usar timestamp
        timestamp = int(datetime.now().timestamp())
        return f"CLM-{timestamp:06d}"