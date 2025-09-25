"""
Caso de uso para gestionar reclamos.

Maneja la lógica de negocio para crear, actualizar y eliminar reclamos.
"""

from typing import Dict, Any, Optional
from domain.ports.reclamos.reclamos_service import ReclamosServicePort


class ManageReclamosUseCase:
    """Caso de uso para gestionar reclamos"""
    
    def __init__(self, reclamos_service: ReclamosServicePort):
        """
        Inicializa el caso de uso.
        
        Args:
            reclamos_service: Servicio de reclamos
        """
        self.reclamos_service = reclamos_service
    
    def execute_create(self, reclamo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo reclamo.
        
        Args:
            reclamo_data: Datos del nuevo reclamo
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            result = self.reclamos_service.create_reclamo(reclamo_data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "created": result["created"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "created": result["created"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "created": False
            }
    
    def execute_update(self, id_reclamo: str, reclamo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un reclamo existente.
        
        Args:
            id_reclamo: ID del reclamo
            reclamo_data: Datos del reclamo a actualizar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not id_reclamo or not id_reclamo.strip():
                return {
                    "success": False,
                    "error": "El ID del reclamo es requerido",
                    "updated": False
                }
            
            result = self.reclamos_service.update_reclamo(id_reclamo, reclamo_data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "updated": result["updated"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "updated": result["updated"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "updated": False
            }
    
    def execute_delete(self, id_reclamo: str) -> Dict[str, Any]:
        """
        Elimina un reclamo.
        
        Args:
            id_reclamo: ID del reclamo a eliminar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not id_reclamo or not id_reclamo.strip():
                return {
                    "success": False,
                    "error": "El ID del reclamo es requerido",
                    "deleted": False
                }
            
            result = self.reclamos_service.delete_reclamo(id_reclamo)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "deleted": result["deleted"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "deleted": result["deleted"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "deleted": False
            }
    
    def execute_update_estado(self, id_reclamo: str, nuevo_estado: str) -> Dict[str, Any]:
        """
        Actualiza el estado de un reclamo.
        
        Args:
            id_reclamo: ID del reclamo
            nuevo_estado: Nuevo estado
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not id_reclamo or not id_reclamo.strip():
                return {
                    "success": False,
                    "error": "El ID del reclamo es requerido",
                    "updated": False
                }
            
            if not nuevo_estado or not nuevo_estado.strip():
                return {
                    "success": False,
                    "error": "El nuevo estado es requerido",
                    "updated": False
                }
            
            result = self.reclamos_service.update_reclamo_estado(id_reclamo, nuevo_estado)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "updated": result["updated"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "updated": result["updated"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "updated": False
            }
    
    def execute_update_monto_aprobado(self, id_reclamo: str, monto_aprobado: Optional[float]) -> Dict[str, Any]:
        """
        Actualiza el monto aprobado de un reclamo.
        
        Args:
            id_reclamo: ID del reclamo
            monto_aprobado: Nuevo monto aprobado
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not id_reclamo or not id_reclamo.strip():
                return {
                    "success": False,
                    "error": "El ID del reclamo es requerido",
                    "updated": False
                }
            
            if monto_aprobado is not None and monto_aprobado < 0:
                return {
                    "success": False,
                    "error": "El monto aprobado no puede ser negativo",
                    "updated": False
                }
            
            result = self.reclamos_service.update_reclamo_monto_aprobado(id_reclamo, monto_aprobado)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "updated": result["updated"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "updated": result["updated"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "updated": False
            }
