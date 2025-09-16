#!/usr/bin/env python3
"""
Endpoints para el sistema de reclamos
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime, date
from generar_id_reclamo import generar_id_reclamo, obtener_siguiente_id

router = APIRouter()

# Archivo de datos de reclamos
RECLAMOS_FILE = "reclamos_data.json"

# Modelos Pydantic
class Proveedor(BaseModel):
    nombre: str
    tipo_servicio: str

class Acciones(BaseModel):
    ver: bool = True
    subir: bool = False

class Reclamo(BaseModel):
    id_reclamo: str
    fecha_envio: str
    proveedor: Proveedor
    estado: str
    monto_solicitado: float
    monto_aprobado: Optional[float] = None
    moneda: str = "$"
    acciones: Acciones

class NuevoReclamo(BaseModel):
    proveedor: Proveedor
    estado: str
    monto_solicitado: float
    moneda: str = "$"
    observaciones: Optional[str] = ""

class ActualizarReclamo(BaseModel):
    estado: Optional[str] = None
    monto_aprobado: Optional[float] = None
    observaciones: Optional[str] = None

# Funciones auxiliares
def cargar_reclamos() -> Dict[str, Any]:
    """Carga los reclamos desde el archivo JSON"""
    if not os.path.exists(RECLAMOS_FILE):
        # Si no existe, crear estructura inicial
        data = {
            "reclamos": [],
            "metadatos": {
                "total_reclamos": 0,
                "estados_disponibles": ["En Revisión", "Aprobado", "Rechazado"],
                "configuracion_id": {
                    "prefijo": "CLM",
                    "formato": "CLM-{secuencial:000-000}",
                    "ejemplo": "CLM-000-001"
                }
            }
        }
        guardar_reclamos(data)
        return data
    
    try:
        with open(RECLAMOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar reclamos: {str(e)}")

def guardar_reclamos(data: Dict[str, Any]) -> None:
    """Guarda los reclamos en el archivo JSON"""
    try:
        with open(RECLAMOS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar reclamos: {str(e)}")

def obtener_ultimo_id(reclamos: List[Dict]) -> str:
    """Obtiene el último ID de la lista de reclamos"""
    if not reclamos:
        return None
    
    # Ordenar por ID para obtener el último
    ids = [r["id_reclamo"] for r in reclamos]
    ids.sort()
    return ids[-1] if ids else None

# Endpoints

@router.get("/reclamos")
def listar_reclamos(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (DD/MM/YYYY)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (DD/MM/YYYY)"),
    proveedor: Optional[str] = Query(None, description="Buscar por nombre de proveedor"),
    limit: Optional[int] = Query(None, description="Límite de resultados"),
    offset: Optional[int] = Query(0, description="Desplazamiento para paginación")
):
    """
    Lista todos los reclamos con filtros opcionales
    """
    data = cargar_reclamos()
    reclamos = data["reclamos"]
    
    # Aplicar filtros
    if estado:
        reclamos = [r for r in reclamos if r["estado"].lower() == estado.lower()]
    
    if proveedor:
        reclamos = [r for r in reclamos if proveedor.lower() in r["proveedor"]["nombre"].lower()]
    
    # TODO: Implementar filtros de fecha si es necesario
    
    # Paginación (solo si se especifica limit)
    total = len(reclamos)
    if limit is not None:
        reclamos_paginados = reclamos[offset:offset + limit]
    else:
        reclamos_paginados = reclamos[offset:] if offset > 0 else reclamos
    
    return {
        "reclamos": reclamos_paginados,
        "total": total,
        "limit": limit,
        "offset": offset,
        "metadatos": data["metadatos"]
    }

@router.get("/reclamos/{id_reclamo}")
def obtener_reclamo(id_reclamo: str):
    """
    Obtiene un reclamo específico por ID
    """
    data = cargar_reclamos()
    
    for reclamo in data["reclamos"]:
        if reclamo["id_reclamo"] == id_reclamo:
            return reclamo
    
    raise HTTPException(status_code=404, detail=f"Reclamo {id_reclamo} no encontrado")

@router.post("/reclamos")
def crear_reclamo(nuevo_reclamo: NuevoReclamo):
    """
    Crea un nuevo reclamo
    """
    data = cargar_reclamos()
    
    # Generar nuevo ID
    ultimo_id = obtener_ultimo_id(data["reclamos"])
    nuevo_id = obtener_siguiente_id(ultimo_id)
    
    # Crear fecha actual
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    
    # Crear el reclamo
    reclamo = {
        "id_reclamo": nuevo_id,
        "fecha_envio": fecha_actual,
        "proveedor": {
            "nombre": nuevo_reclamo.proveedor.nombre,
            "tipo_servicio": nuevo_reclamo.proveedor.tipo_servicio
        },
        "estado": nuevo_reclamo.estado,  # Estado enviado por el frontend
        "monto_solicitado": nuevo_reclamo.monto_solicitado,
        "monto_aprobado": None,
        "moneda": nuevo_reclamo.moneda,
        "acciones": {
            "ver": True,
            "subir": nuevo_reclamo.estado in ["En Revisión", "Rechazado"]  # Puede subir según el estado
        }
    }
    
    # Agregar a la lista
    data["reclamos"].append(reclamo)
    data["metadatos"]["total_reclamos"] = len(data["reclamos"])
    
    # Guardar
    guardar_reclamos(data)
    
    return {
        "mensaje": "Reclamo creado exitosamente",
        "reclamo": reclamo
    }

@router.put("/reclamos/{id_reclamo}")
def actualizar_reclamo(id_reclamo: str, actualizacion: ActualizarReclamo):
    """
    Actualiza un reclamo existente
    """
    data = cargar_reclamos()
    
    # Buscar el reclamo
    reclamo_encontrado = None
    for i, reclamo in enumerate(data["reclamos"]):
        if reclamo["id_reclamo"] == id_reclamo:
            reclamo_encontrado = i
            break
    
    if reclamo_encontrado is None:
        raise HTTPException(status_code=404, detail=f"Reclamo {id_reclamo} no encontrado")
    
    # Actualizar campos
    reclamo = data["reclamos"][reclamo_encontrado]
    
    if actualizacion.estado:
        reclamo["estado"] = actualizacion.estado
        
        # Ajustar acciones según el estado
        if actualizacion.estado == "Aprobado":
            reclamo["acciones"]["subir"] = False  # Ya no puede subir más documentos
        elif actualizacion.estado == "Rechazado":
            reclamo["acciones"]["subir"] = True   # Puede subir documentos para corrección
    
    if actualizacion.monto_aprobado is not None:
        reclamo["monto_aprobado"] = actualizacion.monto_aprobado
    
    # Guardar
    guardar_reclamos(data)
    
    return {
        "mensaje": "Reclamo actualizado exitosamente",
        "reclamo": reclamo
    }

@router.delete("/reclamos/{id_reclamo}")
def eliminar_reclamo(id_reclamo: str):
    """
    Elimina un reclamo
    """
    data = cargar_reclamos()
    
    # Buscar y eliminar
    reclamos_originales = len(data["reclamos"])
    data["reclamos"] = [r for r in data["reclamos"] if r["id_reclamo"] != id_reclamo]
    
    if len(data["reclamos"]) == reclamos_originales:
        raise HTTPException(status_code=404, detail=f"Reclamo {id_reclamo} no encontrado")
    
    # Actualizar metadatos
    data["metadatos"]["total_reclamos"] = len(data["reclamos"])
    
    # Guardar
    guardar_reclamos(data)
    
    return {"mensaje": f"Reclamo {id_reclamo} eliminado exitosamente"}

@router.get("/reclamos/estadisticas/resumen")
def obtener_estadisticas():
    """
    Obtiene estadísticas resumidas de los reclamos
    """
    data = cargar_reclamos()
    reclamos = data["reclamos"]
    
    # Contar por estado
    estados = {}
    monto_total_solicitado = 0
    monto_total_aprobado = 0
    
    for reclamo in reclamos:
        estado = reclamo["estado"]
        estados[estado] = estados.get(estado, 0) + 1
        
        monto_total_solicitado += reclamo["monto_solicitado"]
        if reclamo["monto_aprobado"]:
            monto_total_aprobado += reclamo["monto_aprobado"]
    
    return {
        "total_reclamos": len(reclamos),
        "por_estado": estados,
        "montos": {
            "total_solicitado": round(monto_total_solicitado, 2),
            "total_aprobado": round(monto_total_aprobado, 2),
            "moneda": "$"
        },
        "estados_disponibles": data["metadatos"]["estados_disponibles"]
    }

@router.get("/reclamos/config/estados")
def obtener_estados_disponibles():
    """
    Obtiene la lista de estados disponibles
    """
    data = cargar_reclamos()
    return {
        "estados": data["metadatos"]["estados_disponibles"],
        "descripcion": "Estados disponibles para los reclamos"
    }
