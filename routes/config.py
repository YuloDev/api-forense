from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
import json
import os

from config import RISK_WEIGHTS, RISK_WEIGHTS_DESCRIPTIONS, CONFIG_FILE

router = APIRouter()

class RiskWeightsPayload(BaseModel):
    RISK_WEIGHTS: Dict[str, int]

@router.get("/config/risk-weights")
def get_risk_weights():
    """Devuelve los pesos de riesgo actuales con sus descripciones."""
    return {
        "RISK_WEIGHTS": RISK_WEIGHTS,
        "RISK_WEIGHTS_DESCRIPTIONS": RISK_WEIGHTS_DESCRIPTIONS
    }

@router.put("/config/risk-weights")
def update_risk_weights(payload: RiskWeightsPayload):
    new_weights = payload.RISK_WEIGHTS

    # Validar que las claves coincidan exactamente
    if set(new_weights.keys()) != set(RISK_WEIGHTS.keys()):
        raise HTTPException(
            status_code=400,
            detail="Las claves no coinciden con la configuración actual. Solo puedes modificar valores."
        )

    # Actualizar valores
    for key, value in new_weights.items():
        if not isinstance(value, int):
            raise HTTPException(status_code=400, detail=f"El valor de {key} debe ser un entero")
        RISK_WEIGHTS[key] = value

    # Guardar en JSON para persistencia
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(RISK_WEIGHTS, f, indent=2, ensure_ascii=False)

    return {"message": "Pesos actualizados correctamente", "RISK_WEIGHTS": RISK_WEIGHTS}

@router.get("/config/risk-weights-descriptions")
def get_risk_weights_descriptions():
    """Devuelve solo las descripciones de los pesos de riesgo."""
    return {"RISK_WEIGHTS_DESCRIPTIONS": RISK_WEIGHTS_DESCRIPTIONS}

@router.get("/config/risk-weights-detailed")
def get_risk_weights_detailed():
    """Devuelve los pesos con descripciones en formato detallado para frontend."""
    detailed_weights = {}
    for key in RISK_WEIGHTS.keys():
        detailed_weights[key] = {
            "valor": RISK_WEIGHTS[key],
            "descripcion": RISK_WEIGHTS_DESCRIPTIONS.get(key, {}).get("descripcion", "Sin descripción"),
            "explicacion": RISK_WEIGHTS_DESCRIPTIONS.get(key, {}).get("explicacion", "Sin explicación")
        }
    
    return {
        "weights_detailed": detailed_weights,
        "total_criterios": len(RISK_WEIGHTS),
        "peso_maximo_positivo": max([v for v in RISK_WEIGHTS.values() if v > 0]),
        "peso_maximo_negativo": min([v for v in RISK_WEIGHTS.values() if v < 0], default=0)
    }
