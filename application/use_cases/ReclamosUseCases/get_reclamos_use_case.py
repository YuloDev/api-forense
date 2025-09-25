"""
Caso de uso para obtener reclamos.

Maneja la lógica de negocio para obtener reclamos.
"""

from typing import Dict, Any, Optional
from domain.ports.reclamos.reclamos_service import ReclamosServicePort


class GetReclamosUseCase:
    """Caso de uso para obtener reclamos"""
    
    def __init__(self, reclamos_service: ReclamosServicePort):
        """
        Inicializa el caso de uso.
        
        Args:
            reclamos_service: Servicio de reclamos
        """
        self.reclamos_service = reclamos_service
    
    def execute_all(self) -> Dict[str, Any]:
        """
        Obtiene todos los reclamos.
        
        Returns:
            Dict con resultado de la operación
        """
        try:
            result = self.reclamos_service.get_all_reclamos()
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Reclamos obtenidos correctamente",
                    "data": result["data"],
                    "count": result["count"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": [],
                    "count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "data": [],
                "count": 0
            }
    
    def execute_by_id(self, id_reclamo: str) -> Dict[str, Any]:
        """
        Obtiene un reclamo específico por ID.
        
        Args:
            id_reclamo: ID del reclamo
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not id_reclamo or not id_reclamo.strip():
                return {
                    "success": False,
                    "error": "El ID del reclamo es requerido",
                    "data": {},
                    "count": 0
                }
            
            result = self.reclamos_service.get_reclamo_by_id(id_reclamo)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Reclamo '{id_reclamo}' obtenido correctamente",
                    "data": result["data"],
                    "count": result["count"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": {},
                    "count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "data": {},
                "count": 0
            }
    
    def execute_by_estado(self, estado: str) -> Dict[str, Any]:
        """
        Obtiene reclamos por estado.
        
        Args:
            estado: Estado de los reclamos
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not estado or not estado.strip():
                return {
                    "success": False,
                    "error": "El estado es requerido",
                    "data": [],
                    "count": 0
                }
            
            result = self.reclamos_service.get_reclamos_by_estado(estado)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Reclamos con estado '{estado}' obtenidos correctamente",
                    "data": result["data"],
                    "count": result["count"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": [],
                    "count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "data": [],
                "count": 0
            }
    
    def execute_by_proveedor(self, nombre_proveedor: str) -> Dict[str, Any]:
        """
        Obtiene reclamos por nombre de proveedor.
        
        Args:
            nombre_proveedor: Nombre del proveedor
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not nombre_proveedor or not nombre_proveedor.strip():
                return {
                    "success": False,
                    "error": "El nombre del proveedor es requerido",
                    "data": [],
                    "count": 0
                }
            
            result = self.reclamos_service.get_reclamos_by_proveedor(nombre_proveedor)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Reclamos del proveedor '{nombre_proveedor}' obtenidos correctamente",
                    "data": result["data"],
                    "count": result["count"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": [],
                    "count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "data": [],
                "count": 0
            }
    
    def execute_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de los reclamos.
        
        Returns:
            Dict con estadísticas
        """
        try:
            result = self.reclamos_service.get_reclamos_stats()
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Estadísticas obtenidas correctamente",
                    "data": result["data"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": {}
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "data": {}
            }
