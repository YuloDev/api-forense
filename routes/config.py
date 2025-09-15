from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
import json
import os

from config import RISK_WEIGHTS, CONFIG_FILE

router = APIRouter()

class RiskWeightsPayload(BaseModel):
    RISK_WEIGHTS: Dict[str, int]

@router.get("/config/risk-weights")
def get_risk_weights():
    """Devuelve los pesos de riesgo actuales."""
    return {"RISK_WEIGHTS": RISK_WEIGHTS}

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
