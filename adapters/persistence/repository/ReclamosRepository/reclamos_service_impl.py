"""
Implementación del servicio de reclamos.

Implementa el puerto ReclamosServicePort usando el file handler.
"""

from typing import Dict, Any, Optional
from domain.ports.reclamos.reclamos_service import ReclamosServicePort
from adapters.persistence.helpers.ReclamosHelpers.reclamos_file_handler import ReclamosFileHandler
from domain.entities.reclamos.reclamo import Reclamo
from domain.entities.reclamos.reclamos_collection import ReclamosCollection


class ReclamosServiceAdapter(ReclamosServicePort):
    """Adaptador para el servicio de reclamos"""
    
    def __init__(self, file_path: str = "reclamos_data.json"):
        """
        Inicializa el adaptador.
        
        Args:
            file_path: Ruta al archivo de datos de reclamos
        """
        self.file_handler = ReclamosFileHandler(file_path)
    
    def get_all_reclamos(self) -> Dict[str, Any]:
        """
        Obtiene todos los reclamos.
        
        Returns:
            Dict con resultado de la operación
        """
        try:
            reclamos = self.file_handler.load_reclamos()
            reclamos_list = reclamos.to_list()
            
            return {
                "success": True,
                "data": reclamos_list,
                "count": len(reclamos_list),
                "message": "Reclamos obtenidos correctamente"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo reclamos: {str(e)}",
                "data": [],
                "count": 0
            }
    
    def get_reclamo_by_id(self, id_reclamo: str) -> Dict[str, Any]:
        """
        Obtiene un reclamo específico por ID.
        
        Args:
            id_reclamo: ID del reclamo
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            reclamo = self.file_handler.get_reclamo_by_id(id_reclamo)
            
            if reclamo:
                return {
                    "success": True,
                    "data": reclamo.to_dict(),
                    "count": 1,
                    "message": f"Reclamo '{id_reclamo}' obtenido correctamente"
                }
            else:
                return {
                    "success": False,
                    "error": f"Reclamo '{id_reclamo}' no encontrado",
                    "data": {},
                    "count": 0
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo reclamo '{id_reclamo}': {str(e)}",
                "data": {},
                "count": 0
            }
    
    def get_reclamos_by_estado(self, estado: str) -> Dict[str, Any]:
        """
        Obtiene reclamos por estado.
        
        Args:
            estado: Estado de los reclamos
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            reclamos = self.file_handler.load_reclamos()
            reclamos_filtrados = reclamos.get_reclamos_by_estado(estado)
            reclamos_list = [r.to_dict() for r in reclamos_filtrados]
            
            return {
                "success": True,
                "data": reclamos_list,
                "count": len(reclamos_list),
                "message": f"Reclamos con estado '{estado}' obtenidos correctamente"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo reclamos por estado '{estado}': {str(e)}",
                "data": [],
                "count": 0
            }
    
    def get_reclamos_by_proveedor(self, nombre_proveedor: str) -> Dict[str, Any]:
        """
        Obtiene reclamos por nombre de proveedor.
        
        Args:
            nombre_proveedor: Nombre del proveedor
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            reclamos = self.file_handler.load_reclamos()
            reclamos_filtrados = reclamos.get_reclamos_by_proveedor(nombre_proveedor)
            reclamos_list = [r.to_dict() for r in reclamos_filtrados]
            
            return {
                "success": True,
                "data": reclamos_list,
                "count": len(reclamos_list),
                "message": f"Reclamos del proveedor '{nombre_proveedor}' obtenidos correctamente"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo reclamos por proveedor '{nombre_proveedor}': {str(e)}",
                "data": [],
                "count": 0
            }
    
    def create_reclamo(self, reclamo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo reclamo.
        
        Args:
            reclamo_data: Datos del nuevo reclamo
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Validar datos
            validation = self.file_handler.validate_reclamo_data(reclamo_data)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": f"Error de validación: {validation['error']}",
                    "created": False
                }
            
            # Crear reclamo
            reclamo = Reclamo.from_dict(reclamo_data)
            
            # Agregar reclamo
            self.file_handler.add_reclamo(reclamo)
            
            return {
                "success": True,
                "message": f"Reclamo '{reclamo.id_reclamo}' creado correctamente",
                "data": reclamo.to_dict(),
                "created": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error creando reclamo: {str(e)}",
                "created": False
            }
    
    def update_reclamo(self, id_reclamo: str, reclamo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un reclamo existente.
        
        Args:
            id_reclamo: ID del reclamo
            reclamo_data: Datos del reclamo a actualizar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Validar datos
            validation = self.file_handler.validate_reclamo_data(reclamo_data)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": f"Error de validación: {validation['error']}",
                    "updated": False
                }
            
            # Crear reclamo actualizado
            reclamo = Reclamo.from_dict(reclamo_data)
            
            # Actualizar reclamo
            self.file_handler.update_reclamo(id_reclamo, reclamo)
            
            return {
                "success": True,
                "message": f"Reclamo '{id_reclamo}' actualizado correctamente",
                "data": reclamo.to_dict(),
                "updated": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error actualizando reclamo '{id_reclamo}': {str(e)}",
                "updated": False
            }
    
    def delete_reclamo(self, id_reclamo: str) -> Dict[str, Any]:
        """
        Elimina un reclamo.
        
        Args:
            id_reclamo: ID del reclamo a eliminar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Eliminar reclamo
            self.file_handler.remove_reclamo(id_reclamo)
            
            return {
                "success": True,
                "message": f"Reclamo '{id_reclamo}' eliminado correctamente",
                "deleted": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error eliminando reclamo '{id_reclamo}': {str(e)}",
                "deleted": False
            }
    
    def update_reclamo_estado(self, id_reclamo: str, nuevo_estado: str) -> Dict[str, Any]:
        """
        Actualiza el estado de un reclamo.
        
        Args:
            id_reclamo: ID del reclamo
            nuevo_estado: Nuevo estado
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Obtener reclamo existente
            reclamo = self.file_handler.get_reclamo_by_id(id_reclamo)
            if not reclamo:
                return {
                    "success": False,
                    "error": f"Reclamo '{id_reclamo}' no encontrado",
                    "updated": False
                }
            
            # Actualizar estado
            reclamo.update_estado(nuevo_estado)
            
            # Guardar cambios
            self.file_handler.update_reclamo(id_reclamo, reclamo)
            
            return {
                "success": True,
                "message": f"Estado del reclamo '{id_reclamo}' actualizado a '{nuevo_estado}'",
                "data": reclamo.to_dict(),
                "updated": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error actualizando estado del reclamo '{id_reclamo}': {str(e)}",
                "updated": False
            }
    
    def update_reclamo_monto_aprobado(self, id_reclamo: str, monto_aprobado: Optional[float]) -> Dict[str, Any]:
        """
        Actualiza el monto aprobado de un reclamo.
        
        Args:
            id_reclamo: ID del reclamo
            monto_aprobado: Nuevo monto aprobado
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Obtener reclamo existente
            reclamo = self.file_handler.get_reclamo_by_id(id_reclamo)
            if not reclamo:
                return {
                    "success": False,
                    "error": f"Reclamo '{id_reclamo}' no encontrado",
                    "updated": False
                }
            
            # Actualizar monto aprobado
            reclamo.update_monto_aprobado(monto_aprobado)
            
            # Guardar cambios
            self.file_handler.update_reclamo(id_reclamo, reclamo)
            
            return {
                "success": True,
                "message": f"Monto aprobado del reclamo '{id_reclamo}' actualizado",
                "data": reclamo.to_dict(),
                "updated": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error actualizando monto aprobado del reclamo '{id_reclamo}': {str(e)}",
                "updated": False
            }
    
    def get_reclamos_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de los reclamos.
        
        Returns:
            Dict con estadísticas
        """
        try:
            reclamos = self.file_handler.load_reclamos()
            
            # Calcular estadísticas
            total_reclamos = reclamos.get_count()
            estados = {}
            total_monto_solicitado = 0.0
            total_monto_aprobado = 0.0
            
            for reclamo in reclamos.get_all_reclamos():
                # Contar por estado
                estado = reclamo.estado
                estados[estado] = estados.get(estado, 0) + 1
                
                # Sumar montos
                total_monto_solicitado += reclamo.monto_solicitado
                if reclamo.monto_aprobado is not None:
                    total_monto_aprobado += reclamo.monto_aprobado
            
            stats = {
                "total_reclamos": total_reclamos,
                "por_estado": estados,
                "total_monto_solicitado": total_monto_solicitado,
                "total_monto_aprobado": total_monto_aprobado,
                "monto_pendiente": total_monto_solicitado - total_monto_aprobado
            }
            
            return {
                "success": True,
                "data": stats,
                "message": "Estadísticas obtenidas correctamente"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo estadísticas: {str(e)}",
                "data": {}
            }
