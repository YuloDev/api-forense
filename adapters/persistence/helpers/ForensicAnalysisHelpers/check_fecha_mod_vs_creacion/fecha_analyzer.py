"""
Helper para análisis de fechas de creación y modificación.

Analiza metadatos temporales de archivos PDF e imágenes para detectar
posibles manipulaciones en las fechas de creación y modificación.
"""

import fitz
import pikepdf
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import io
import os


class FechaAnalyzer:
    """Analizador de fechas de creación y modificación"""
    
    def __init__(self):
        self.suspicious_indicators = []
        self.analysis_notes = []
    
    def analyze_pdf_dates(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza las fechas de un PDF usando PyMuPDF y pikepdf.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con información de fechas y análisis
        """
        try:
            # Análisis con PyMuPDF
            pymupdf_result = self._analyze_pdf_pymupdf(pdf_bytes)
            
            # Análisis con pikepdf
            pikepdf_result = self._analyze_pdf_pikepdf(pdf_bytes)
            
            # Combinar resultados
            combined_result = self._combine_pdf_results(pymupdf_result, pikepdf_result)
            
            return combined_result
            
        except Exception as e:
            return {
                "error": f"Error analizando fechas PDF: {str(e)}",
                "creation_date": None,
                "modification_date": None,
                "has_creation_date": False,
                "has_modification_date": False
            }
    
    def analyze_image_dates(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza las fechas de una imagen usando PIL/Exif.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de fechas y análisis
        """
        try:
            # Análisis con PIL/Exif
            pil_result = self._analyze_image_pil(image_bytes)
            
            # Análisis de metadatos del sistema de archivos (si es posible)
            filesystem_result = self._analyze_filesystem_metadata(image_bytes)
            
            # Combinar resultados
            combined_result = self._combine_image_results(pil_result, filesystem_result)
            
            return combined_result
            
        except Exception as e:
            return {
                "error": f"Error analizando fechas imagen: {str(e)}",
                "creation_date": None,
                "modification_date": None,
                "has_creation_date": False,
                "has_modification_date": False
            }
    
    def _analyze_pdf_pymupdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Análisis de fechas usando PyMuPDF"""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata = doc.metadata
            
            creation_date = None
            modification_date = None
            
            # Extraer fecha de creación
            if metadata.get('creationDate'):
                creation_date = self._parse_pdf_date(metadata['creationDate'])
            
            # Extraer fecha de modificación
            if metadata.get('modDate'):
                modification_date = self._parse_pdf_date(metadata['modDate'])
            
            doc.close()
            
            return {
                "creation_date": creation_date,
                "modification_date": modification_date,
                "has_creation_date": creation_date is not None,
                "has_modification_date": modification_date is not None,
                "metadata_source": "pymupdf",
                "raw_metadata": metadata
            }
            
        except Exception as e:
            return {
                "error": f"Error en análisis PyMuPDF: {str(e)}",
                "creation_date": None,
                "modification_date": None,
                "has_creation_date": False,
                "has_modification_date": False
            }
    
    def _analyze_pdf_pikepdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Análisis de fechas usando pikepdf"""
        try:
            with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
                metadata = pdf.docinfo
                
                creation_date = None
                modification_date = None
                
                # Extraer fecha de creación
                if hasattr(metadata, 'CreationDate') and metadata.CreationDate:
                    creation_date = self._parse_pikepdf_date(metadata.CreationDate)
                
                # Extraer fecha de modificación
                if hasattr(metadata, 'ModDate') and metadata.ModDate:
                    modification_date = self._parse_pikepdf_date(metadata.ModDate)
                
                return {
                    "creation_date": creation_date,
                    "modification_date": modification_date,
                    "has_creation_date": creation_date is not None,
                    "has_modification_date": modification_date is not None,
                    "metadata_source": "pikepdf",
                    "raw_metadata": {
                        "CreationDate": str(metadata.CreationDate) if hasattr(metadata, 'CreationDate') else None,
                        "ModDate": str(metadata.ModDate) if hasattr(metadata, 'ModDate') else None,
                        "Title": str(metadata.Title) if hasattr(metadata, 'Title') else None,
                        "Author": str(metadata.Author) if hasattr(metadata, 'Author') else None,
                        "Subject": str(metadata.Subject) if hasattr(metadata, 'Subject') else None,
                        "Keywords": str(metadata.Keywords) if hasattr(metadata, 'Keywords') else None,
                        "Creator": str(metadata.Creator) if hasattr(metadata, 'Creator') else None,
                        "Producer": str(metadata.Producer) if hasattr(metadata, 'Producer') else None
                    }
                }
                
        except Exception as e:
            return {
                "error": f"Error en análisis pikepdf: {str(e)}",
                "creation_date": None,
                "modification_date": None,
                "has_creation_date": False,
                "has_modification_date": False
            }
    
    def _analyze_image_pil(self, image_bytes: bytes) -> Dict[str, Any]:
        """Análisis de fechas usando PIL/Exif"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            exif_data = image._getexif()
            
            creation_date = None
            modification_date = None
            
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # Fecha de creación (DateTime)
                    if tag == "DateTime":
                        creation_date = self._parse_exif_date(value)
                    # Fecha de modificación (DateTimeOriginal)
                    elif tag == "DateTimeOriginal":
                        modification_date = self._parse_exif_date(value)
                    # Fecha de digitalización (DateTimeDigitized)
                    elif tag == "DateTimeDigitized" and not modification_date:
                        modification_date = self._parse_exif_date(value)
            
            return {
                "creation_date": creation_date,
                "modification_date": modification_date,
                "has_creation_date": creation_date is not None,
                "has_modification_date": modification_date is not None,
                "metadata_source": "pil_exif",
                "exif_tags_found": list(TAGS.get(tag_id, tag_id) for tag_id in exif_data.keys()) if exif_data else []
            }
            
        except Exception as e:
            return {
                "error": f"Error en análisis PIL: {str(e)}",
                "creation_date": None,
                "modification_date": None,
                "has_creation_date": False,
                "has_modification_date": False
            }
    
    def _analyze_filesystem_metadata(self, file_bytes: bytes) -> Dict[str, Any]:
        """Análisis de metadatos del sistema de archivos (limitado)"""
        # Para archivos en memoria, no podemos acceder a metadatos del sistema de archivos
        # Esto sería útil si tuviéramos acceso al archivo original
        return {
            "creation_date": None,
            "modification_date": None,
            "has_creation_date": False,
            "has_modification_date": False,
            "metadata_source": "filesystem_unavailable"
        }
    
    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        """Parsea fecha en formato PDF (D:YYYYMMDDHHmmSSOHH'mm')"""
        try:
            if not date_str or not date_str.startswith('D:'):
                return None
            
            # Extraer la parte de fecha (D:YYYYMMDDHHmmSS)
            date_part = date_str[2:16]  # D: + 14 caracteres
            
            if len(date_part) >= 14:
                year = int(date_part[:4])
                month = int(date_part[4:6])
                day = int(date_part[6:8])
                hour = int(date_part[8:10])
                minute = int(date_part[10:12])
                second = int(date_part[12:14])
                
                return datetime(year, month, day, hour, minute, second)
            
            return None
            
        except (ValueError, IndexError):
            return None
    
    def _parse_pikepdf_date(self, pikepdf_date) -> Optional[datetime]:
        """Parsea fecha de pikepdf"""
        try:
            if hasattr(pikepdf_date, 'to_datetime'):
                return pikepdf_date.to_datetime()
            elif hasattr(pikepdf_date, 'isoformat'):
                return datetime.fromisoformat(pikepdf_date.isoformat())
            else:
                return self._parse_pdf_date(str(pikepdf_date))
        except:
            return None
    
    def _parse_exif_date(self, date_str: str) -> Optional[datetime]:
        """Parsea fecha en formato Exif (YYYY:MM:DD HH:MM:SS)"""
        try:
            return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            return None
    
    def _combine_pdf_results(self, pymupdf_result: Dict, pikepdf_result: Dict) -> Dict[str, Any]:
        """Combina resultados de PyMuPDF y pikepdf"""
        # Priorizar pikepdf para fechas más precisas
        creation_date = pikepdf_result.get("creation_date") or pymupdf_result.get("creation_date")
        modification_date = pikepdf_result.get("modification_date") or pymupdf_result.get("modification_date")
        
        # Detectar inconsistencias
        inconsistencies = []
        if (pymupdf_result.get("creation_date") and pikepdf_result.get("creation_date") and 
            pymupdf_result["creation_date"] != pikepdf_result["creation_date"]):
            inconsistencies.append("Inconsistencia en fecha de creación entre PyMuPDF y pikepdf")
        
        if (pymupdf_result.get("modification_date") and pikepdf_result.get("modification_date") and 
            pymupdf_result["modification_date"] != pikepdf_result["modification_date"]):
            inconsistencies.append("Inconsistencia en fecha de modificación entre PyMuPDF y pikepdf")
        
        return {
            "creation_date": creation_date,
            "modification_date": modification_date,
            "has_creation_date": creation_date is not None,
            "has_modification_date": modification_date is not None,
            "inconsistencies": inconsistencies,
            "pymupdf_result": pymupdf_result,
            "pikepdf_result": pikepdf_result
        }
    
    def _combine_image_results(self, pil_result: Dict, filesystem_result: Dict) -> Dict[str, Any]:
        """Combina resultados de PIL y sistema de archivos"""
        creation_date = pil_result.get("creation_date")
        modification_date = pil_result.get("modification_date")
        
        return {
            "creation_date": creation_date,
            "modification_date": modification_date,
            "has_creation_date": creation_date is not None,
            "has_modification_date": modification_date is not None,
            "pil_result": pil_result,
            "filesystem_result": filesystem_result
        }
    
    def calculate_time_difference(self, creation_date: Optional[datetime], modification_date: Optional[datetime]) -> Tuple[Optional[float], Optional[float]]:
        """Calcula la diferencia de tiempo entre fechas"""
        if not creation_date or not modification_date:
            return None, None
        
        time_diff = modification_date - creation_date
        hours = time_diff.total_seconds() / 3600
        days = hours / 24
        
        return hours, days
    
    def detect_suspicious_patterns(self, creation_date: Optional[datetime], modification_date: Optional[datetime]) -> List[str]:
        """Detecta patrones sospechosos en las fechas"""
        suspicious = []
        
        # Si no hay fecha de modificación, no se detectan patrones sospechosos
        if not modification_date:
            return suspicious
        
        # Si no hay fecha de creación, solo se detectan patrones básicos
        if not creation_date:
            # Solo detectar fechas futuras
            now = datetime.now()
            if modification_date > now:
                suspicious.append("Fecha de modificación en el futuro")
            return suspicious
        
        # Fecha de modificación anterior a creación
        if modification_date < creation_date:
            suspicious.append("Fecha de modificación anterior a fecha de creación")
        
        # Fechas iguales (posible manipulación)
        if creation_date == modification_date:
            suspicious.append("Fechas de creación y modificación idénticas")
        
        # Cualquier diferencia temporal es sospechosa según la descripción del riesgo
        # "Modificaciones posteriores a la creación pueden sugerir alteraciones del documento original"
        time_diff = modification_date - creation_date
        if time_diff.total_seconds() > 0:  # Hay diferencia temporal
            if time_diff.days > 365:
                suspicious.append(f"Diferencia temporal muy grande: {time_diff.days} días")
            elif time_diff.days > 30:
                suspicious.append(f"Diferencia temporal significativa: {time_diff.days} días")
            elif time_diff.days > 1:
                suspicious.append(f"Diferencia temporal detectada: {time_diff.days} días")
            elif time_diff.total_seconds() < 3600:
                suspicious.append("Diferencia temporal muy pequeña (menos de 1 hora)")
            else:
                suspicious.append(f"Diferencia temporal detectada: {time_diff.total_seconds()/3600:.1f} horas")
        
        # Fechas futuras
        now = datetime.now()
        if creation_date > now:
            suspicious.append("Fecha de creación en el futuro")
        
        if modification_date > now:
            suspicious.append("Fecha de modificación en el futuro")
        
        return suspicious
