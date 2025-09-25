"""
Helper para análisis de actualizaciones incrementales.

Analiza múltiples actualizaciones incrementales del PDF que pueden indicar alteraciones sucesivas.
"""

import re
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF
import pikepdf
from datetime import datetime


class ActualizacionesAnalyzer:
    """Analizador de actualizaciones incrementales"""
    
    def __init__(self):
        # Patrones de actualizaciones incrementales sospechosas
        self.suspicious_patterns = [
            r'incremental\s+update',
            r'update\s+\d+',
            r'revision\s+\d+',
            r'version\s+\d+\.\d+',
            r'patch\s+\d+',
            r'hotfix\s+\d+',
            r'minor\s+update',
            r'major\s+update',
            r'security\s+update',
            r'bugfix\s+\d+'
        ]
        
        # Patrones de fechas de actualización
        self.date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}-\d{2}-\d{4}',
            r'\d{4}\.\d{2}\.\d{2}',
            r'\d{2}\.\d{2}\.\d{4}'
        ]
        
        # Patrones de versiones
        self.version_patterns = [
            r'v\d+\.\d+',
            r'version\s+\d+\.\d+',
            r'rev\s+\d+',
            r'build\s+\d+',
            r'r\d+'
        ]
    
    def analyze_pdf_actualizaciones(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza actualizaciones incrementales en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con información de actualizaciones y análisis
        """
        try:
            # Abrir PDF con PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            actualizaciones_encontradas = []
            fechas_actualizacion = []
            tipos_actualizacion = []
            indicadores_sospechosos = []
            
            # Buscar actualizaciones en metadatos
            metadata_updates = self._find_actualizaciones_in_metadata(pdf_document)
            actualizaciones_encontradas.extend(metadata_updates)
            
            # Buscar actualizaciones en contenido de páginas
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                page_updates = self._find_actualizaciones_in_page(page, page_num)
                actualizaciones_encontradas.extend(page_updates)
            
            # Buscar actualizaciones en anotaciones
            annotation_updates = self._find_actualizaciones_in_annotations(pdf_document)
            actualizaciones_encontradas.extend(annotation_updates)
            
            # Buscar actualizaciones en formularios
            form_updates = self._find_actualizaciones_in_forms(pdf_document)
            actualizaciones_encontradas.extend(form_updates)
            
            # Buscar actualizaciones en objetos del PDF
            object_updates = self._find_actualizaciones_in_objects(pdf_document)
            actualizaciones_encontradas.extend(object_updates)
            
            pdf_document.close()
            
            # Extraer fechas y tipos de actualizaciones
            for update in actualizaciones_encontradas:
                if update.get("fecha"):
                    fechas_actualizacion.append(update["fecha"])
                if update.get("tipo"):
                    tipos_actualizacion.append(update["tipo"])
            
            # Analizar actualizaciones encontradas
            cantidad_actualizaciones = len(actualizaciones_encontradas)
            actualizaciones_sospechosas = self._analyze_suspicious_actualizaciones(actualizaciones_encontradas)
            
            # Generar indicadores sospechosos
            indicadores_sospechosos = self._generate_suspicious_indicators(
                cantidad_actualizaciones, actualizaciones_sospechosas, 
                fechas_actualizacion, tipos_actualizacion
            )
            
            return {
                "actualizaciones_detectadas": cantidad_actualizaciones > 0,
                "cantidad_actualizaciones": cantidad_actualizaciones,
                "actualizaciones_sospechosas": actualizaciones_sospechosas,
                "actualizaciones_encontradas": actualizaciones_encontradas,
                "fechas_actualizacion": list(set(fechas_actualizacion)),
                "tipos_actualizacion": list(set(tipos_actualizacion)),
                "indicadores_sospechosos": indicadores_sospechosos
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando actualizaciones del PDF: {str(e)}",
                "actualizaciones_detectadas": False,
                "cantidad_actualizaciones": 0,
                "actualizaciones_sospechosas": 0
            }
    
    def analyze_image_actualizaciones(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza actualizaciones incrementales en una imagen (siempre retorna sin actualizaciones).
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de actualizaciones y análisis
        """
        # Las imágenes no pueden contener actualizaciones incrementales
        return {
            "actualizaciones_detectadas": False,
            "cantidad_actualizaciones": 0,
            "actualizaciones_sospechosas": 0,
            "actualizaciones_encontradas": [],
            "fechas_actualizacion": [],
            "tipos_actualizacion": [],
            "indicadores_sospechosos": []
        }
    
    def _find_actualizaciones_in_metadata(self, pdf_document) -> List[Dict[str, Any]]:
        """Busca actualizaciones en metadatos del PDF"""
        updates = []
        
        try:
            # Obtener metadatos
            metadata = pdf_document.metadata
            
            for key, value in metadata.items():
                if value and isinstance(value, str):
                    if self._contains_actualizacion_patterns(value):
                        update_info = self._extract_actualizacion_info(value, key)
                        if update_info:
                            updates.append({
                                "page": 0,
                                "type": "metadata",
                                "content": value,
                                "position": 0,
                                "suspicious": self._is_suspicious_actualizacion(update_info),
                                "metadata_key": key,
                                "fecha": update_info.get("fecha"),
                                "tipo": update_info.get("tipo"),
                                "version": update_info.get("version")
                            })
            
        except Exception:
            pass
        
        return updates
    
    def _find_actualizaciones_in_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Busca actualizaciones en el contenido de una página"""
        updates = []
        
        try:
            # Obtener el texto de la página
            page_text = page.get_text()
            
            # Buscar patrones de actualizaciones
            for pattern in self.suspicious_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    content = match.group(0)
                    update_info = self._extract_actualizacion_info(content, "page_content")
                    if update_info:
                        updates.append({
                            "page": page_num + 1,
                            "type": "page_content",
                            "content": content,
                            "position": match.start(),
                            "suspicious": self._is_suspicious_actualizacion(update_info),
                            "fecha": update_info.get("fecha"),
                            "tipo": update_info.get("tipo"),
                            "version": update_info.get("version")
                        })
            
            # Buscar patrones de fechas
            for pattern in self.date_patterns:
                matches = re.finditer(pattern, page_text)
                for match in matches:
                    content = match.group(0)
                    update_info = self._extract_actualizacion_info(content, "date")
                    if update_info:
                        updates.append({
                            "page": page_num + 1,
                            "type": "date",
                            "content": content,
                            "position": match.start(),
                            "suspicious": self._is_suspicious_actualizacion(update_info),
                            "fecha": update_info.get("fecha"),
                            "tipo": update_info.get("tipo"),
                            "version": update_info.get("version")
                        })
            
            # Buscar patrones de versiones
            for pattern in self.version_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    content = match.group(0)
                    update_info = self._extract_actualizacion_info(content, "version")
                    if update_info:
                        updates.append({
                            "page": page_num + 1,
                            "type": "version",
                            "content": content,
                            "position": match.start(),
                            "suspicious": self._is_suspicious_actualizacion(update_info),
                            "fecha": update_info.get("fecha"),
                            "tipo": update_info.get("tipo"),
                            "version": update_info.get("version")
                        })
            
        except Exception:
            pass
        
        return updates
    
    def _find_actualizaciones_in_annotations(self, pdf_document) -> List[Dict[str, Any]]:
        """Busca actualizaciones en anotaciones del PDF"""
        updates = []
        
        try:
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                annotations = page.annots()
                
                for annot in annotations:
                    if hasattr(annot, 'content') and annot.content:
                        if self._contains_actualizacion_patterns(annot.content):
                            update_info = self._extract_actualizacion_info(annot.content, "annotation")
                            if update_info:
                                updates.append({
                                    "page": page_num + 1,
                                    "type": "annotation",
                                    "content": annot.content,
                                    "position": 0,
                                    "suspicious": self._is_suspicious_actualizacion(update_info),
                                    "fecha": update_info.get("fecha"),
                                    "tipo": update_info.get("tipo"),
                                    "version": update_info.get("version")
                                })
            
        except Exception:
            pass
        
        return updates
    
    def _find_actualizaciones_in_forms(self, pdf_document) -> List[Dict[str, Any]]:
        """Busca actualizaciones en formularios del PDF"""
        updates = []
        
        try:
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                widgets = page.widgets()
                
                for widget in widgets:
                    if hasattr(widget, 'field_value') and widget.field_value:
                        if self._contains_actualizacion_patterns(widget.field_value):
                            update_info = self._extract_actualizacion_info(widget.field_value, "form")
                            if update_info:
                                updates.append({
                                    "page": page_num + 1,
                                    "type": "form",
                                    "content": widget.field_value,
                                    "position": 0,
                                    "suspicious": self._is_suspicious_actualizacion(update_info),
                                    "fecha": update_info.get("fecha"),
                                    "tipo": update_info.get("tipo"),
                                    "version": update_info.get("version")
                                })
            
        except Exception:
            pass
        
        return updates
    
    def _find_actualizaciones_in_objects(self, pdf_document) -> List[Dict[str, Any]]:
        """Busca actualizaciones en objetos del PDF"""
        updates = []
        
        try:
            # Buscar en objetos del PDF usando pikepdf
            pdf_pikepdf = pikepdf.Pdf.open(pdf_bytes)
            
            for obj_id, obj in pdf_pikepdf.objects.items():
                if hasattr(obj, 'get') and obj.get('/Type') == '/Catalog':
                    # Buscar en el catálogo
                    if hasattr(obj, 'get') and obj.get('/Version'):
                        version = str(obj.get('/Version'))
                        update_info = self._extract_actualizacion_info(version, "object")
                        if update_info:
                            updates.append({
                                "page": 0,
                                "type": "object",
                                "content": version,
                                "position": 0,
                                "suspicious": self._is_suspicious_actualizacion(update_info),
                                "fecha": update_info.get("fecha"),
                                "tipo": update_info.get("tipo"),
                                "version": update_info.get("version")
                            })
            
            pdf_pikepdf.close()
            
        except Exception:
            pass
        
        return updates
    
    def _contains_actualizacion_patterns(self, text: str) -> bool:
        """Verifica si un texto contiene patrones de actualizaciones"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Buscar patrones de actualizaciones
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Buscar patrones de fechas
        for pattern in self.date_patterns:
            if re.search(pattern, text):
                return True
        
        # Buscar patrones de versiones
        for pattern in self.version_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _extract_actualizacion_info(self, content: str, source_type: str) -> Optional[Dict[str, Any]]:
        """Extrae información de actualización del contenido"""
        if not content:
            return None
        
        info = {
            "fecha": None,
            "tipo": None,
            "version": None
        }
        
        # Extraer fecha
        for pattern in self.date_patterns:
            match = re.search(pattern, content)
            if match:
                info["fecha"] = match.group(0)
                break
        
        # Extraer tipo de actualización
        for pattern in self.suspicious_patterns:
            match = re.search(pattern, content.lower())
            if match:
                info["tipo"] = match.group(0)
                break
        
        # Extraer versión
        for pattern in self.version_patterns:
            match = re.search(pattern, content.lower())
            if match:
                info["version"] = match.group(0)
                break
        
        return info if any(info.values()) else None
    
    def _is_suspicious_actualizacion(self, update_info: Dict[str, Any]) -> bool:
        """Determina si una actualización es sospechosa"""
        if not update_info:
            return False
        
        # Verificar si tiene múltiples indicadores
        indicators = sum(1 for v in update_info.values() if v)
        
        # Verificar patrones sospechosos
        tipo = update_info.get("tipo", "").lower()
        suspicious_types = ["incremental", "patch", "hotfix", "security", "bugfix"]
        
        return indicators > 1 or any(st in tipo for st in suspicious_types)
    
    def _analyze_suspicious_actualizaciones(self, actualizaciones: List[Dict[str, Any]]) -> int:
        """Analiza y cuenta actualizaciones sospechosas"""
        suspicious_count = 0
        
        for update in actualizaciones:
            if update.get("suspicious", False):
                suspicious_count += 1
        
        return suspicious_count
    
    def _generate_suspicious_indicators(self, cantidad_actualizaciones: int, actualizaciones_sospechosas: int, 
                                      fechas_actualizacion: List[str], tipos_actualizacion: List[str]) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if cantidad_actualizaciones > 0:
            indicators.append(f"Actualizaciones incrementales detectadas ({cantidad_actualizaciones} actualizaciones)")
        
        if actualizaciones_sospechosas > 0:
            indicators.append(f"{actualizaciones_sospechosas} actualizaciones con patrones sospechosos")
        
        if len(fechas_actualizacion) > 1:
            indicators.append(f"Múltiples fechas de actualización: {len(fechas_actualizacion)}")
        
        if len(tipos_actualizacion) > 1:
            indicators.append(f"Múltiples tipos de actualización: {len(tipos_actualizacion)}")
        
        if cantidad_actualizaciones > 5:
            indicators.append("Múltiples actualizaciones incrementales - posible manipulación sucesiva")
        
        if actualizaciones_sospechosas > 2:
            indicators.append("Alto número de actualizaciones sospechosas - posible alteración documental")
        
        return indicators
