from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Tuple, List
import json
import os

from config import RISK_LEVELS

router = APIRouter()

class RiskLevelsPayload(BaseModel):
    RISK_LEVELS: Dict[str, List[int]]  # Usando List[int] para JSON, se convertirá a tupla internamente

class RiskLevelItem(BaseModel):
    nivel: str
    rango_min: int
    rango_max: int
    descripcion: str

@router.get("/risk-levels")
def get_risk_levels():
    """Devuelve los niveles de riesgo actuales con descripción."""
    return {
        "RISK_LEVELS": RISK_LEVELS,
        "descripcion": "Rangos de puntuación para clasificar el nivel de riesgo de documentos",
        "niveles_disponibles": ["bajo", "medio", "alto"]
    }

@router.put("/risk-levels")
def update_risk_levels(payload: RiskLevelsPayload):
    """Actualiza los rangos de los niveles de riesgo."""
    new_levels = payload.RISK_LEVELS
    
    # Validar que las claves coincidan exactamente con las esperadas
    expected_keys = {"bajo", "medio", "alto"}
    if set(new_levels.keys()) != expected_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Las claves deben ser exactamente: {', '.join(expected_keys)}"
        )
    
    # Validar formato de rangos
    for level_name, range_values in new_levels.items():
        if not isinstance(range_values, list) or len(range_values) != 2:
            raise HTTPException(
                status_code=400,
                detail=f"El nivel '{level_name}' debe tener exactamente 2 valores [min, max]"
            )
        
        min_val, max_val = range_values
        
        if not isinstance(min_val, int) or not isinstance(max_val, int):
            raise HTTPException(
                status_code=400, 
                detail=f"Los valores de '{level_name}' deben ser enteros"
            )
        
        if min_val < 0 or max_val > 100:
            raise HTTPException(
                status_code=400,
                detail=f"Los valores de '{level_name}' deben estar entre 0 y 100"
            )
        
        if min_val >= max_val:
            raise HTTPException(
                status_code=400,
                detail=f"El valor mínimo de '{level_name}' debe ser menor que el máximo"
            )
    
    # Validar que no haya solapamientos entre rangos
    ranges = [(name, values) for name, values in new_levels.items()]
    ranges.sort(key=lambda x: x[1][0])  # Ordenar por valor mínimo
    
    for i in range(len(ranges) - 1):
        current_name, current_range = ranges[i]
        next_name, next_range = ranges[i + 1]
        
        if current_range[1] >= next_range[0]:
            raise HTTPException(
                status_code=400,
                detail=f"Los rangos de '{current_name}' y '{next_name}' no pueden solaparse"
            )
    
    # Actualizar valores en memoria (convertir a tuplas)
    for key, value in new_levels.items():
        RISK_LEVELS[key] = tuple(value)
    
    # Guardar en archivo específico para niveles de riesgo
    config_file = "risk_levels_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(new_levels, f, indent=2, ensure_ascii=False)
    
    return {
        "message": "Niveles de riesgo actualizados correctamente", 
        "RISK_LEVELS": RISK_LEVELS,
        "archivo_guardado": config_file
    }

@router.get("/risk-levels/example")
def get_risk_levels_example():
    """Devuelve ejemplos de configuración para maquetado/frontend."""
    return {
        "ejemplo_configuracion_actual": {
            "descripcion": "Configuración actual de niveles de riesgo",
            "valores": dict(RISK_LEVELS)
        },
        "ejemplo_payload_actualizacion": {
            "descripcion": "Estructura para actualizar niveles de riesgo",
            "endpoint": "PUT /risk-levels",
            "content_type": "application/json",
            "payload": {
                "RISK_LEVELS": {
                    "bajo": [0, 29],
                    "medio": [30, 59], 
                    "alto": [60, 100]
                }
            }
        },
        "ejemplo_payload_personalizado": {
            "descripcion": "Ejemplo de configuración personalizada",
            "payload": {
                "RISK_LEVELS": {
                    "bajo": [0, 39],
                    "medio": [40, 69],
                    "alto": [70, 100]
                }
            }
        },
        "ejemplo_respuesta_analisis": {
            "descripcion": "Cómo se usa en el análisis de documentos",
            "estructura": {
                "riesgo": {
                    "score": 45,
                    "nivel": "medio",  # Determinado por RISK_LEVELS
                    "es_falso": True,
                    "prioritarias": [],
                    "secundarias": [],
                    "adicionales": []
                }
            }
        },
        "validaciones": {
            "rangos_validos": "Valores entre 0 y 100",
            "no_solapamiento": "Los rangos no pueden solaparse",
            "orden_requerido": "min < max para cada nivel",
            "niveles_obligatorios": ["bajo", "medio", "alto"]
        }
    }

@router.get("/risk-levels/validate")
def validate_current_levels():
    """Valida la configuración actual de niveles de riesgo."""
    validation_result = {
        "es_valido": True,
        "errores": [],
        "advertencias": [],
        "configuracion_actual": dict(RISK_LEVELS)
    }
    
    # Verificar rangos válidos
    for level_name, (min_val, max_val) in RISK_LEVELS.items():
        if min_val < 0 or max_val > 100:
            validation_result["es_valido"] = False
            validation_result["errores"].append(
                f"Nivel '{level_name}': valores fuera del rango 0-100"
            )
        
        if min_val >= max_val:
            validation_result["es_valido"] = False
            validation_result["errores"].append(
                f"Nivel '{level_name}': valor mínimo debe ser menor que máximo"
            )
    
    # Verificar solapamientos
    ranges = list(RISK_LEVELS.items())
    ranges.sort(key=lambda x: x[1][0])
    
    for i in range(len(ranges) - 1):
        current_name, (_, current_max) = ranges[i]
        next_name, (next_min, _) = ranges[i + 1]
        
        if current_max >= next_min:
            validation_result["es_valido"] = False
            validation_result["errores"].append(
                f"Solapamiento entre '{current_name}' y '{next_name}'"
            )
    
    # Verificar cobertura completa 0-100
    sorted_ranges = sorted(RISK_LEVELS.values(), key=lambda x: x[0])
    if sorted_ranges[0][0] > 0:
        validation_result["advertencias"].append(
            f"Gap en el rango: 0-{sorted_ranges[0][0]-1} no está cubierto"
        )
    
    if sorted_ranges[-1][1] < 100:
        validation_result["advertencias"].append(
            f"Gap en el rango: {sorted_ranges[-1][1]+1}-100 no está cubierto"
        )
    
    return validation_result

@router.post("/risk-levels/reset")
def reset_risk_levels():
    """Restaura los niveles de riesgo a los valores por defecto."""
    default_levels = {"bajo": (0, 29), "medio": (30, 59), "alto": (60, 100)}
    
    # Actualizar en memoria
    for key, value in default_levels.items():
        RISK_LEVELS[key] = value
    
    # Eliminar archivo de configuración personalizada si existe
    config_file = "risk_levels_config.json"
    if os.path.exists(config_file):
        os.remove(config_file)
    
    return {
        "message": "Niveles de riesgo restaurados a valores por defecto",
        "RISK_LEVELS": RISK_LEVELS,
        "archivo_eliminado": config_file if os.path.exists(config_file) else None
    }
