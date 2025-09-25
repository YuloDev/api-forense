"""
Controlador API para gestión de reclamos.

Endpoints para obtener, crear, actualizar y eliminar reclamos.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from application.use_cases.ReclamosUseCases.get_reclamos_use_case import GetReclamosUseCase
from application.use_cases.ReclamosUseCases.manage_reclamos_use_case import ManageReclamosUseCase
from adapters.persistence.repository.ReclamosRepository.reclamos_service_impl import ReclamosServiceAdapter

# Crear router
router = APIRouter(prefix="/reclamos", tags=["Reclamos"])

# Modelos de request
class ProveedorRequest(BaseModel):
    """Request para datos de proveedor"""
    nombre: str
    tipo_servicio: str

class AccionesRequest(BaseModel):
    """Request para acciones de reclamo"""
    ver: bool
    subir: bool

class ReclamoCreateRequest(BaseModel):
    """Request para crear un reclamo"""
    id_reclamo: str
    fecha_envio: str
    proveedor: ProveedorRequest
    estado: str
    monto_solicitado: float
    monto_aprobado: Optional[float] = None
    moneda: str = "$"
    acciones: AccionesRequest

class ReclamoUpdateRequest(BaseModel):
    """Request para actualizar un reclamo"""
    id_reclamo: str
    fecha_envio: str
    proveedor: ProveedorRequest
    estado: str
    monto_solicitado: float
    monto_aprobado: Optional[float] = None
    moneda: str = "$"
    acciones: AccionesRequest

class EstadoUpdateRequest(BaseModel):
    """Request para actualizar estado de reclamo"""
    nuevo_estado: str

class MontoAprobadoUpdateRequest(BaseModel):
    """Request para actualizar monto aprobado"""
    monto_aprobado: Optional[float]

@router.get("")
async def get_reclamos(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    proveedor: Optional[str] = Query(None, description="Filtrar por proveedor")
) -> JSONResponse:
    """
    Obtiene todos los reclamos con filtros opcionales.
    
    Args:
        estado: Estado para filtrar
        proveedor: Nombre del proveedor para filtrar
        
    Returns:
        JSONResponse con los reclamos
    """
    try:
        # Inicializar servicios
        reclamos_service = ReclamosServiceAdapter()
        get_use_case = GetReclamosUseCase(reclamos_service)
        
        # Aplicar filtros
        if estado:
            result = get_use_case.execute_by_estado(estado)
        elif proveedor:
            result = get_use_case.execute_by_proveedor(proveedor)
        else:
            result = get_use_case.execute_all()
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result["message"],
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
                    "data": [],
                    "count": 0
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "data": [],
                "count": 0
            }
        )

@router.get("/{id_reclamo}")
async def get_reclamo_by_id(id_reclamo: str) -> JSONResponse:
    """
    Obtiene un reclamo específico por ID.
    
    Args:
        id_reclamo: ID del reclamo
        
    Returns:
        JSONResponse con el reclamo
    """
    try:
        # Inicializar servicios
        reclamos_service = ReclamosServiceAdapter()
        get_use_case = GetReclamosUseCase(reclamos_service)
        
        # Obtener reclamo
        result = get_use_case.execute_by_id(id_reclamo)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result["message"],
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

@router.post("")
async def create_reclamo(request: ReclamoCreateRequest) -> JSONResponse:
    """
    Crea un nuevo reclamo.
    
    Args:
        request: Datos del nuevo reclamo
        
    Returns:
        JSONResponse con el resultado de la creación
    """
    try:
        # Inicializar servicios
        reclamos_service = ReclamosServiceAdapter()
        manage_use_case = ManageReclamosUseCase(reclamos_service)
        
        # Convertir request a dict
        reclamo_data = {
            "id_reclamo": request.id_reclamo,
            "fecha_envio": request.fecha_envio,
            "proveedor": request.proveedor.dict(),
            "estado": request.estado,
            "monto_solicitado": request.monto_solicitado,
            "monto_aprobado": request.monto_aprobado,
            "moneda": request.moneda,
            "acciones": request.acciones.dict()
        }
        
        # Crear reclamo
        result = manage_use_case.execute_create(reclamo_data)
        
        if result["success"]:
            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "created": result["created"]
                }
            )
        else:
            return JSONResponse(
                status_code=400 if "validación" in result["error"].lower() else 409,
                content={
                    "success": False,
                    "error": result["error"],
                    "created": result["created"]
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "created": False
            }
        )

@router.put("/{id_reclamo}")
async def update_reclamo(id_reclamo: str, request: ReclamoUpdateRequest) -> JSONResponse:
    """
    Actualiza un reclamo existente.
    
    Args:
        id_reclamo: ID del reclamo
        request: Datos del reclamo a actualizar
        
    Returns:
        JSONResponse con el resultado de la actualización
    """
    try:
        # Inicializar servicios
        reclamos_service = ReclamosServiceAdapter()
        manage_use_case = ManageReclamosUseCase(reclamos_service)
        
        # Convertir request a dict
        reclamo_data = {
            "id_reclamo": request.id_reclamo,
            "fecha_envio": request.fecha_envio,
            "proveedor": request.proveedor.dict(),
            "estado": request.estado,
            "monto_solicitado": request.monto_solicitado,
            "monto_aprobado": request.monto_aprobado,
            "moneda": request.moneda,
            "acciones": request.acciones.dict()
        }
        
        # Actualizar reclamo
        result = manage_use_case.execute_update(id_reclamo, reclamo_data)
        
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

@router.delete("/{id_reclamo}")
async def delete_reclamo(id_reclamo: str) -> JSONResponse:
    """
    Elimina un reclamo.
    
    Args:
        id_reclamo: ID del reclamo a eliminar
        
    Returns:
        JSONResponse con el resultado de la eliminación
    """
    try:
        # Inicializar servicios
        reclamos_service = ReclamosServiceAdapter()
        manage_use_case = ManageReclamosUseCase(reclamos_service)
        
        # Eliminar reclamo
        result = manage_use_case.execute_delete(id_reclamo)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result["message"],
                    "deleted": result["deleted"]
                }
            )
        else:
            return JSONResponse(
                status_code=404 if "no encontrado" in result["error"].lower() else 400,
                content={
                    "success": False,
                    "error": result["error"],
                    "deleted": result["deleted"]
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "deleted": False
            }
        )

@router.patch("/{id_reclamo}/estado")
async def update_reclamo_estado(id_reclamo: str, request: EstadoUpdateRequest) -> JSONResponse:
    """
    Actualiza el estado de un reclamo.
    
    Args:
        id_reclamo: ID del reclamo
        request: Nuevo estado
        
    Returns:
        JSONResponse con el resultado de la actualización
    """
    try:
        # Inicializar servicios
        reclamos_service = ReclamosServiceAdapter()
        manage_use_case = ManageReclamosUseCase(reclamos_service)
        
        # Actualizar estado
        result = manage_use_case.execute_update_estado(id_reclamo, request.nuevo_estado)
        
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

@router.patch("/{id_reclamo}/monto-aprobado")
async def update_reclamo_monto_aprobado(id_reclamo: str, request: MontoAprobadoUpdateRequest) -> JSONResponse:
    """
    Actualiza el monto aprobado de un reclamo.
    
    Args:
        id_reclamo: ID del reclamo
        request: Nuevo monto aprobado
        
    Returns:
        JSONResponse con el resultado de la actualización
    """
    try:
        # Inicializar servicios
        reclamos_service = ReclamosServiceAdapter()
        manage_use_case = ManageReclamosUseCase(reclamos_service)
        
        # Actualizar monto aprobado
        result = manage_use_case.execute_update_monto_aprobado(id_reclamo, request.monto_aprobado)
        
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

@router.get("/stats/estadisticas")
async def get_reclamos_stats() -> JSONResponse:
    """
    Obtiene estadísticas de los reclamos.
    
    Returns:
        JSONResponse con las estadísticas
    """
    try:
        # Inicializar servicios
        reclamos_service = ReclamosServiceAdapter()
        get_use_case = GetReclamosUseCase(reclamos_service)
        
        # Obtener estadísticas
        result = get_use_case.execute_stats()
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result["message"],
                    "data": result["data"]
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": result["error"],
                    "data": {}
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "data": {}
            }
        )
