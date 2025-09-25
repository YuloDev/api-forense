"""
Helper para manejo de archivos de reclamos.

Maneja la lectura y escritura del archivo reclamos_data.json.
"""

import json
import os
from typing import Dict, Any, List, Optional
from domain.entities.reclamos.reclamo import Reclamo
from domain.entities.reclamos.reclamos_collection import ReclamosCollection


class ReclamosFileHandler:
    """Helper para manejo de archivos de reclamos"""
    
    def __init__(self, file_path: str = "reclamos_data.json"):
        """
        Inicializa el handler con la ruta del archivo.
        
        Args:
            file_path: Ruta al archivo de datos de reclamos
        """
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Asegura que el archivo de reclamos existe"""
        if not os.path.exists(self.file_path):
            # Crear archivo con estructura vacía
            default_data = {"reclamos": []}
            self._write_to_file(default_data)
    
    def _read_from_file(self) -> Dict[str, List[Dict]]:
        """
        Lee los datos desde el archivo JSON.
        
        Returns:
            Dict con los datos de reclamos
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise Exception(f"Error leyendo archivo de reclamos: {str(e)}")
    
    def _write_to_file(self, data: Dict[str, List[Dict]]) -> None:
        """
        Escribe los datos al archivo JSON.
        
        Args:
            data: Datos a escribir
        """
        try:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Error escribiendo archivo de reclamos: {str(e)}")
    
    def load_reclamos(self) -> ReclamosCollection:
        """
        Carga los reclamos desde el archivo.
        
        Returns:
            ReclamosCollection con los reclamos cargados
        """
        try:
            data = self._read_from_file()
            return ReclamosCollection.from_dict(data)
        except Exception as e:
            raise Exception(f"Error cargando reclamos: {str(e)}")
    
    def save_reclamos(self, reclamos: ReclamosCollection) -> None:
        """
        Guarda los reclamos al archivo.
        
        Args:
            reclamos: Colección de reclamos a guardar
        """
        try:
            data = reclamos.to_dict()
            self._write_to_file(data)
        except Exception as e:
            raise Exception(f"Error guardando reclamos: {str(e)}")
    
    def get_reclamo_by_id(self, id_reclamo: str) -> Optional[Reclamo]:
        """
        Obtiene un reclamo específico por ID.
        
        Args:
            id_reclamo: ID del reclamo
            
        Returns:
            Reclamo encontrado o None
        """
        try:
            reclamos = self.load_reclamos()
            return reclamos.get_reclamo_by_id(id_reclamo)
        except Exception as e:
            raise Exception(f"Error obteniendo reclamo '{id_reclamo}': {str(e)}")
    
    def add_reclamo(self, reclamo: Reclamo) -> None:
        """
        Agrega un nuevo reclamo.
        
        Args:
            reclamo: Reclamo a agregar
        """
        try:
            reclamos = self.load_reclamos()
            reclamos.add_reclamo(reclamo)
            self.save_reclamos(reclamos)
        except Exception as e:
            raise Exception(f"Error agregando reclamo: {str(e)}")
    
    def update_reclamo(self, id_reclamo: str, reclamo: Reclamo) -> None:
        """
        Actualiza un reclamo existente.
        
        Args:
            id_reclamo: ID del reclamo
            reclamo: Datos actualizados del reclamo
        """
        try:
            reclamos = self.load_reclamos()
            reclamos.update_reclamo(id_reclamo, reclamo)
            self.save_reclamos(reclamos)
        except Exception as e:
            raise Exception(f"Error actualizando reclamo '{id_reclamo}': {str(e)}")
    
    def remove_reclamo(self, id_reclamo: str) -> None:
        """
        Elimina un reclamo.
        
        Args:
            id_reclamo: ID del reclamo a eliminar
        """
        try:
            reclamos = self.load_reclamos()
            reclamos.remove_reclamo(id_reclamo)
            self.save_reclamos(reclamos)
        except Exception as e:
            raise Exception(f"Error eliminando reclamo '{id_reclamo}': {str(e)}")
    
    def validate_reclamo_data(self, reclamo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos de un reclamo.
        
        Args:
            reclamo_data: Datos del reclamo a validar
            
        Returns:
            Dict con resultado de la validación
        """
        try:
            # Validar campos requeridos
            required_fields = ["id_reclamo", "fecha_envio", "proveedor", "estado", "monto_solicitado", "moneda"]
            for field in required_fields:
                if field not in reclamo_data:
                    return {"valid": False, "error": f"El campo '{field}' es requerido"}
            
            # Validar proveedor
            if not isinstance(reclamo_data["proveedor"], dict):
                return {"valid": False, "error": "El campo 'proveedor' debe ser un objeto"}
            
            proveedor = reclamo_data["proveedor"]
            if "nombre" not in proveedor or "tipo_servicio" not in proveedor:
                return {"valid": False, "error": "El proveedor debe tener 'nombre' y 'tipo_servicio'"}
            
            # Validar monto
            try:
                monto = float(reclamo_data["monto_solicitado"])
                if monto < 0:
                    return {"valid": False, "error": "El monto solicitado no puede ser negativo"}
            except (ValueError, TypeError):
                return {"valid": False, "error": "El monto solicitado debe ser un número válido"}
            
            # Validar monto aprobado si existe
            if "monto_aprobado" in reclamo_data and reclamo_data["monto_aprobado"] is not None:
                try:
                    monto_aprobado = float(reclamo_data["monto_aprobado"])
                    if monto_aprobado < 0:
                        return {"valid": False, "error": "El monto aprobado no puede ser negativo"}
                except (ValueError, TypeError):
                    return {"valid": False, "error": "El monto aprobado debe ser un número válido"}
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": f"Error en validación: {str(e)}"}
