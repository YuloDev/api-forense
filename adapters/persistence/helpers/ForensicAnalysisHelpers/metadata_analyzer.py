"""
Helper para análisis de metadatos forenses
"""
import base64
import io
from typing import Dict, Any, Optional, List
from datetime import datetime
from PIL import Image, ExifTags
import xml.etree.ElementTree as ET

class MetadataAnalyzer:
    """Analizador de metadatos forenses"""
    
    @staticmethod
    def analyze_image_metadata(image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza metadatos de una imagen
        
        Args:
            image_bytes: Bytes de la imagen
            
        Returns:
            Dict con análisis de metadatos
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Análisis EXIF
            exif_data = {}
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif_data = MetadataAnalyzer._extract_exif_data(img._getexif())
            
            # Análisis XMP
            xmp_data = MetadataAnalyzer._extract_xmp_data(image_bytes)
            
            # Análisis básico de imagen
            basic_info = {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "has_transparency": img.mode in ("RGBA", "LA", "P")
            }
            
            # Detectar anomalías
            anomalies = MetadataAnalyzer._detect_metadata_anomalies(exif_data, xmp_data, basic_info)
            
            return {
                "has_exif": bool(exif_data),
                "has_xmp": bool(xmp_data),
                "exif_data": exif_data,
                "xmp_data": xmp_data,
                "basic_info": basic_info,
                "anomalies": anomalies,
                "creation_date": MetadataAnalyzer._extract_creation_date(exif_data, xmp_data),
                "modification_date": MetadataAnalyzer._extract_modification_date(exif_data, xmp_data),
                "software_used": MetadataAnalyzer._extract_software_used(exif_data, xmp_data),
                "camera_info": MetadataAnalyzer._extract_camera_info(exif_data)
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando metadatos: {str(e)}",
                "has_exif": False,
                "has_xmp": False,
                "anomalies": [f"Error de procesamiento: {str(e)}"]
            }
    
    @staticmethod
    def analyze_pdf_metadata(pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza metadatos de un PDF
        
        Args:
            pdf_bytes: Bytes del PDF
            
        Returns:
            Dict con análisis de metadatos
        """
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata = doc.metadata
            
            # Análisis de metadatos del PDF
            pdf_info = {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "page_count": doc.page_count,
                "pdf_version": doc.pdf_version()
            }
            
            # Detectar anomalías en PDF
            anomalies = MetadataAnalyzer._detect_pdf_anomalies(pdf_info)
            
            doc.close()
            
            return {
                "has_metadata": bool(metadata),
                "pdf_info": pdf_info,
                "anomalies": anomalies,
                "creation_date": MetadataAnalyzer._parse_pdf_date(metadata.get("creationDate")),
                "modification_date": MetadataAnalyzer._parse_pdf_date(metadata.get("modDate")),
                "software_used": [metadata.get("creator", ""), metadata.get("producer", "")],
                "camera_info": {}  # Los PDFs no tienen info de cámara
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando metadatos PDF: {str(e)}",
                "has_metadata": False,
                "anomalies": [f"Error de procesamiento: {str(e)}"]
            }
    
    @staticmethod
    def _extract_exif_data(exif_dict) -> Dict[str, Any]:
        """Extrae datos EXIF de forma legible"""
        if not exif_dict:
            return {}
        
        exif_data = {}
        for tag_id, value in exif_dict.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            if isinstance(value, bytes):
                try:
                    value = value.decode('utf-8', errors='ignore')
                except:
                    value = str(value)
            exif_data[tag] = value
        
        return exif_data
    
    @staticmethod
    def _extract_xmp_data(image_bytes: bytes) -> Dict[str, str]:
        """Extrae datos XMP de la imagen"""
        try:
            start = image_bytes.find(b"<x:xmpmeta")
            if start == -1:
                return {}
            
            end = image_bytes.find(b"</x:xmpmeta>")
            if end == -1:
                return {}
            
            xmp_xml = image_bytes[start:end + len(b"</x:xmpmeta>")]
            root = ET.fromstring(xmp_xml)
            
            xmp_data = {}
            nsmap = {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
            
            for desc in root.findall(".//rdf:Description", nsmap):
                for k, v in desc.attrib.items():
                    if any(ns in k for ns in ("http://ns.adobe.com/xap/1.0/", 
                                            "http://ns.adobe.com/exif/1.0/",
                                            "http://ns.adobe.com/photoshop/1.0/")):
                        key = k.split("}")[-1]
                        xmp_data[key] = v
            
            return xmp_data
            
        except Exception:
            return {}
    
    @staticmethod
    def _detect_metadata_anomalies(exif_data: Dict, xmp_data: Dict, basic_info: Dict) -> List[str]:
        """Detecta anomalías en los metadatos"""
        anomalies = []
        
        # Verificar inconsistencias de fechas
        if exif_data.get("DateTime") and xmp_data.get("ModifyDate"):
            try:
                exif_date = datetime.strptime(exif_data["DateTime"], "%Y:%m:%d %H:%M:%S")
                xmp_date = datetime.fromisoformat(xmp_data["ModifyDate"].replace("Z", "+00:00"))
                if abs((exif_date - xmp_date).total_seconds()) > 3600:  # Más de 1 hora de diferencia
                    anomalies.append("Inconsistencia en fechas de modificación entre EXIF y XMP")
            except:
                pass
        
        # Verificar software sospechoso
        software_indicators = ["photoshop", "gimp", "paint", "editor"]
        for data_source in [exif_data, xmp_data]:
            for key, value in data_source.items():
                if any(indicator in str(value).lower() for indicator in software_indicators):
                    anomalies.append(f"Software de edición detectado: {value}")
        
        # Verificar metadatos faltantes sospechosos
        if not exif_data and basic_info.get("format") in ["JPEG", "PNG"]:
            anomalies.append("Falta de metadatos EXIF en imagen que debería tenerlos")
        
        return anomalies
    
    @staticmethod
    def _detect_pdf_anomalies(pdf_info: Dict) -> List[str]:
        """Detecta anomalías en metadatos de PDF"""
        anomalies = []
        
        # Verificar fechas inconsistentes
        if pdf_info.get("creation_date") and pdf_info.get("modification_date"):
            if pdf_info["creation_date"] == pdf_info["modification_date"]:
                anomalies.append("Fecha de creación y modificación idénticas")
        
        # Verificar software sospechoso
        creator = pdf_info.get("creator", "").lower()
        producer = pdf_info.get("producer", "").lower()
        
        if "adobe" in creator and "itext" in producer:
            anomalies.append("Inconsistencia entre creador y productor del PDF")
        
        return anomalies
    
    @staticmethod
    def _extract_creation_date(exif_data: Dict, xmp_data: Dict) -> Optional[datetime]:
        """Extrae fecha de creación"""
        # Prioridad: EXIF DateTimeOriginal > XMP CreateDate > EXIF DateTime
        for source, key in [(exif_data, "DateTimeOriginal"), (xmp_data, "CreateDate"), (exif_data, "DateTime")]:
            if key in source:
                try:
                    if ":" in source[key]:
                        return datetime.strptime(source[key][:19], "%Y:%m:%d %H:%M:%S")
                    else:
                        return datetime.fromisoformat(source[key].replace("Z", "+00:00"))
                except:
                    continue
        return None
    
    @staticmethod
    def _extract_modification_date(exif_data: Dict, xmp_data: Dict) -> Optional[datetime]:
        """Extrae fecha de modificación"""
        for source, key in [(exif_data, "DateTime"), (xmp_data, "ModifyDate")]:
            if key in source:
                try:
                    if ":" in source[key]:
                        return datetime.strptime(source[key][:19], "%Y:%m:%d %H:%M:%S")
                    else:
                        return datetime.fromisoformat(source[key].replace("Z", "+00:00"))
                except:
                    continue
        return None
    
    @staticmethod
    def _extract_software_used(exif_data: Dict, xmp_data: Dict) -> List[str]:
        """Extrae software utilizado"""
        software = []
        
        # De EXIF
        if "Software" in exif_data:
            software.append(exif_data["Software"])
        
        # De XMP
        for key, value in xmp_data.items():
            if "software" in key.lower() or "creator" in key.lower():
                software.append(str(value))
        
        return list(set(software))  # Eliminar duplicados
    
    @staticmethod
    def _extract_camera_info(exif_data: Dict) -> Dict[str, Any]:
        """Extrae información de la cámara"""
        camera_info = {}
        
        camera_fields = ["Make", "Model", "LensModel", "FocalLength", "FNumber", "ISO", "ExposureTime"]
        for field in camera_fields:
            if field in exif_data:
                camera_info[field] = exif_data[field]
        
        return camera_info
    
    @staticmethod
    def _parse_pdf_date(date_str: str) -> Optional[datetime]:
        """Parsea fecha de PDF"""
        if not date_str:
            return None
        
        try:
            # Formato PDF: D:YYYYMMDDHHmmSSOHH'mm'
            if date_str.startswith("D:"):
                date_str = date_str[2:]
            
            if len(date_str) >= 14:
                return datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
        except:
            pass
        
        return None
