"""
Controlador API para gestión de risk weights.

Endpoints para obtener y actualizar los pesos de riesgo del sistema.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from application.use_cases.ConfigUseCases.get_risk_weights_use_case import GetRiskWeightsUseCase
from application.use_cases.ConfigUseCases.update_risk_weights_use_case import UpdateRiskWeightsUseCase
from adapters.persistence.repository.ConfigRepository.risk_weights_service_impl import RiskWeightsServiceAdapter

# Crear router
router = APIRouter(prefix="/config", tags=["Configuración"])

# Modelos de request
class RiskWeightUpdateRequest(BaseModel):
    """Request para actualizar un risk weight individual"""
    valor: int
    descripcion: str
    explicacion: str

class RiskWeightsBatchUpdateRequest(BaseModel):
    """Request para actualizar múltiples risk weights"""
    updates: Dict[str, RiskWeightUpdateRequest]

@router.get("/risk-weights")
async def get_risk_weights() -> JSONResponse:
    """
    Obtiene todos los risk weights del sistema.
    
    Returns:
        JSONResponse con todos los risk weights
    """
    try:
        # Inicializar servicios
        risk_weights_service = RiskWeightsServiceAdapter()
        get_use_case = GetRiskWeightsUseCase(risk_weights_service)
        
        # Obtener todos los risk weights
        result = get_use_case.execute_all()
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Risk weights obtenidos correctamente",
                    "data": result["data"],
                    "count": result["count"]
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": result["error"],
                    "data": {},
                    "count": 0
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "data": {},
                "count": 0
            }
        )

@router.get("/risk-weights/{key}")
async def get_risk_weight(key: str) -> JSONResponse:
    """
    Obtiene un risk weight específico por su clave.
    
    Args:
        key: Clave del risk weight
        
    Returns:
        JSONResponse con el risk weight solicitado
    """
    try:
        # Inicializar servicios
        risk_weights_service = RiskWeightsServiceAdapter()
        get_use_case = GetRiskWeightsUseCase(risk_weights_service)
        
        # Obtener risk weight específico
        result = get_use_case.execute_single(key)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Risk weight '{key}' obtenido correctamente",
                    "data": result["data"],
                    "count": result["count"]
                }
            )
        else:
            return JSONResponse(
                status_code=404 if "no encontrado" in result["error"].lower() else 500,
                content={
                    "success": False,
                    "error": result["error"],
                    "data": {},
                    "count": 0
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "data": {},
                "count": 0
            }
        )

@router.put("/risk-weights/{key}")
async def update_risk_weight(key: str, request: RiskWeightUpdateRequest) -> JSONResponse:
    """
    Actualiza un risk weight específico.
    
    Args:
        key: Clave del risk weight
        request: Datos del risk weight a actualizar
        
    Returns:
        JSONResponse con el resultado de la actualización
    """
    try:
        # Inicializar servicios
        risk_weights_service = RiskWeightsServiceAdapter()
        update_use_case = UpdateRiskWeightsUseCase(risk_weights_service)
        
        # Convertir request a dict
        weight_data = {
            "valor": request.valor,
            "descripcion": request.descripcion,
            "explicacion": request.explicacion
        }
        
        # Actualizar risk weight
        result = update_use_case.execute_single(key, weight_data)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "updated": result["updated"]
                }
            )
        else:
            return JSONResponse(
                status_code=400 if "validación" in result["error"].lower() else 404,
                content={
                    "success": False,
                    "error": result["error"],
                    "updated": result["updated"]
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "updated": False
            }
        )

@router.put("/risk-weights")
async def update_risk_weights_batch(request: RiskWeightsBatchUpdateRequest) -> JSONResponse:
    """
    Actualiza múltiples risk weights en lote.
    
    Args:
        request: Datos de los risk weights a actualizar
        
    Returns:
        JSONResponse con el resultado de las actualizaciones
    """
    try:
        # Inicializar servicios
        risk_weights_service = RiskWeightsServiceAdapter()
        update_use_case = UpdateRiskWeightsUseCase(risk_weights_service)
        
        # Convertir request a dict
        updates = {}
        for key, weight_data in request.updates.items():
            updates[key] = {
                "valor": weight_data.valor,
                "descripcion": weight_data.descripcion,
                "explicacion": weight_data.explicacion
            }
        
        # Actualizar risk weights en lote
        result = update_use_case.execute_batch(updates)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result["message"],
                    "results": result["results"],
                    "success_count": result["success_count"],
                    "error_count": result["error_count"],
                    "errors": result["errors"]
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result["error"],
                    "results": result["results"],
                    "success_count": result["success_count"],
                    "error_count": result["error_count"],
                    "errors": result["errors"]
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "results": {},
                "success_count": 0,
                "error_count": 0,
                "errors": [str(e)]
            }
        )
