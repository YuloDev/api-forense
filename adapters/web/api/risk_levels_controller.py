"""
Controlador API para gestión de niveles de riesgo.

Endpoints para obtener y actualizar los niveles de riesgo del sistema.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from application.use_cases.ConfigUseCases.get_risk_levels_use_case import GetRiskLevelsUseCase
from application.use_cases.ConfigUseCases.update_risk_levels_use_case import UpdateRiskLevelsUseCase
from adapters.persistence.repository.ConfigRepository.risk_levels_service_impl import RiskLevelsServiceAdapter

# Crear router
router = APIRouter(prefix="/config", tags=["Configuración"])

# Modelos de request
class RiskLevelUpdateRequest(BaseModel):
    """Request para actualizar un nivel de riesgo individual"""
    name: str
    min_score: int
    max_score: int
    description: str = ""

class RiskLevelAddRequest(BaseModel):
    """Request para agregar un nuevo nivel de riesgo"""
    name: str
    min_score: int
    max_score: int
    description: str = ""

class RiskLevelsBatchUpdateRequest(BaseModel):
    """Request para actualizar todos los niveles de riesgo"""
    levels: Dict[str, List[int]]

@router.get("/risk-levels")
async def get_risk_levels() -> JSONResponse:
    """
    Obtiene todos los niveles de riesgo del sistema.
    
    Returns:
        JSONResponse con todos los niveles de riesgo
    """
    try:
        # Inicializar servicios
        risk_levels_service = RiskLevelsServiceAdapter()
        get_use_case = GetRiskLevelsUseCase(risk_levels_service)
        
        # Obtener todos los niveles
        result = get_use_case.execute_all()
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Niveles de riesgo obtenidos correctamente",
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

@router.get("/risk-levels/{name}")
async def get_risk_level(name: str) -> JSONResponse:
    """
    Obtiene un nivel de riesgo específico por nombre.
    
    Args:
        name: Nombre del nivel de riesgo
        
    Returns:
        JSONResponse con el nivel de riesgo solicitado
    """
    try:
        # Inicializar servicios
        risk_levels_service = RiskLevelsServiceAdapter()
        get_use_case = GetRiskLevelsUseCase(risk_levels_service)
        
        # Obtener nivel específico
        result = get_use_case.execute_by_name(name)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Nivel de riesgo '{name}' obtenido correctamente",
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

@router.get("/risk-levels/score/{score}")
async def get_risk_level_by_score(score: int) -> JSONResponse:
    """
    Obtiene el nivel de riesgo para un puntaje específico.
    
    Args:
        score: Puntaje a evaluar
        
    Returns:
        JSONResponse con el nivel de riesgo correspondiente
    """
    try:
        # Inicializar servicios
        risk_levels_service = RiskLevelsServiceAdapter()
        get_use_case = GetRiskLevelsUseCase(risk_levels_service)
        
        # Obtener nivel por puntaje
        result = get_use_case.execute_by_score(score)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Nivel encontrado para puntaje {score}",
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

@router.put("/risk-levels/{name}")
async def update_risk_level(name: str, request: RiskLevelUpdateRequest) -> JSONResponse:
    """
    Actualiza un nivel de riesgo específico.
    
    Args:
        name: Nombre del nivel de riesgo
        request: Datos del nivel a actualizar
        
    Returns:
        JSONResponse con el resultado de la actualización
    """
    try:
        # Inicializar servicios
        risk_levels_service = RiskLevelsServiceAdapter()
        update_use_case = UpdateRiskLevelsUseCase(risk_levels_service)
        
        # Convertir request a dict
        level_data = {
            "name": request.name,
            "min_score": request.min_score,
            "max_score": request.max_score,
            "description": request.description
        }
        
        # Actualizar nivel
        result = update_use_case.execute_single(name, level_data)
        
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

@router.post("/risk-levels")
async def add_risk_level(request: RiskLevelAddRequest) -> JSONResponse:
    """
    Agrega un nuevo nivel de riesgo.
    
    Args:
        request: Datos del nuevo nivel
        
    Returns:
        JSONResponse con el resultado de la adición
    """
    try:
        # Inicializar servicios
        risk_levels_service = RiskLevelsServiceAdapter()
        update_use_case = UpdateRiskLevelsUseCase(risk_levels_service)
        
        # Convertir request a dict
        level_data = {
            "name": request.name,
            "min_score": request.min_score,
            "max_score": request.max_score,
            "description": request.description
        }
        
        # Agregar nivel
        result = update_use_case.execute_add(level_data)
        
        if result["success"]:
            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "added": result["added"]
                }
            )
        else:
            return JSONResponse(
                status_code=400 if "validación" in result["error"].lower() else 409,
                content={
                    "success": False,
                    "error": result["error"],
                    "added": result["added"]
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "added": False
            }
        )

@router.delete("/risk-levels/{name}")
async def remove_risk_level(name: str) -> JSONResponse:
    """
    Elimina un nivel de riesgo.
    
    Args:
        name: Nombre del nivel a eliminar
        
    Returns:
        JSONResponse con el resultado de la eliminación
    """
    try:
        # Inicializar servicios
        risk_levels_service = RiskLevelsServiceAdapter()
        update_use_case = UpdateRiskLevelsUseCase(risk_levels_service)
        
        # Eliminar nivel
        result = update_use_case.execute_remove(name)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "removed": result["removed"]
                }
            )
        else:
            return JSONResponse(
                status_code=404 if "no encontrado" in result["error"].lower() else 400,
                content={
                    "success": False,
                    "error": result["error"],
                    "removed": result["removed"]
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "removed": False
            }
        )

@router.put("/risk-levels")
async def update_all_risk_levels(request: RiskLevelsBatchUpdateRequest) -> JSONResponse:
    """
    Actualiza todos los niveles de riesgo.
    
    Args:
        request: Datos de todos los niveles
        
    Returns:
        JSONResponse con el resultado de las actualizaciones
    """
    try:
        # Inicializar servicios
        risk_levels_service = RiskLevelsServiceAdapter()
        update_use_case = UpdateRiskLevelsUseCase(risk_levels_service)
        
        # Actualizar todos los niveles
        result = update_use_case.execute_all(request.levels)
        
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
                status_code=400,
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
