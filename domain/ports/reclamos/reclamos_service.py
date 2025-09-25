"""
Puerto/interfaz para el servicio de reclamos.

Define el contrato para la gestión de reclamos del sistema.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from domain.entities.reclamos.reclamo import Reclamo


class ReclamosServicePort(ABC):
    """Puerto para el servicio de reclamos"""
    
    @abstractmethod
    def get_all_reclamos(self) -> Dict[str, Any]:
        """
        Obtiene todos los reclamos.
        
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def get_reclamo_by_id(self, id_reclamo: str) -> Dict[str, Any]:
        """
        Obtiene un reclamo específico por ID.
        
        Args:
            id_reclamo: ID del reclamo
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def get_reclamos_by_estado(self, estado: str) -> Dict[str, Any]:
        """
        Obtiene reclamos por estado.
        
        Args:
            estado: Estado de los reclamos
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def get_reclamos_by_proveedor(self, nombre_proveedor: str) -> Dict[str, Any]:
        """
        Obtiene reclamos por nombre de proveedor.
        
        Args:
            nombre_proveedor: Nombre del proveedor
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def create_reclamo(self, reclamo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo reclamo.
        
        Args:
            reclamo_data: Datos del nuevo reclamo
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def update_reclamo(self, id_reclamo: str, reclamo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un reclamo existente.
        
        Args:
            id_reclamo: ID del reclamo
            reclamo_data: Datos del reclamo a actualizar
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def delete_reclamo(self, id_reclamo: str) -> Dict[str, Any]:
        """
        Elimina un reclamo.
        
        Args:
            id_reclamo: ID del reclamo a eliminar
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def update_reclamo_estado(self, id_reclamo: str, nuevo_estado: str) -> Dict[str, Any]:
        """
        Actualiza el estado de un reclamo.
        
        Args:
            id_reclamo: ID del reclamo
            nuevo_estado: Nuevo estado
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def update_reclamo_monto_aprobado(self, id_reclamo: str, monto_aprobado: Optional[float]) -> Dict[str, Any]:
        """
        Actualiza el monto aprobado de un reclamo.
        
        Args:
            id_reclamo: ID del reclamo
            monto_aprobado: Nuevo monto aprobado
            
        Returns:
            Dict con resultado de la operación
        """
        pass
    
    @abstractmethod
    def get_reclamos_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de los reclamos.
        
        Returns:
            Dict con estadísticas
        """
        pass
