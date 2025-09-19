"""
Endpoint para detección detallada de texto superpuesto en PDFs e imágenes.

Analiza las 4 zonas principales donde se puede "tapar" texto:
1. Anotaciones (Annotations) sobre la página
2. Contenido nuevo en la propia página (Page Contents)  
3. Form XObject llamado desde la página
4. Campo de formulario (AcroForm)

Para imágenes, analiza metadatos, capas y superposición de texto.
"""

from fastapi import APIRouter, HTTPException, Query, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any
import base64
import json

from helpers.deteccion_texto_superpuesto import (
    detectar_texto_superpuesto_detallado,
    generar_reporte_texto_superpuesto
)
from helpers.analisis_imagenes import analizar_imagen_completa, detectar_tipo_archivo

router = APIRouter()


class ArchivoRequest(BaseModel):
    """Modelo para solicitud de análisis de archivo (PDF o imagen)"""
    archivo_base64: str
    tipo_archivo: Optional[str] = None  # Si no se especifica, se detecta automáticamente


class PDFRequest(BaseModel):
    """Modelo para solicitud de análisis de PDF (compatibilidad)"""
    pdfbase64: str


class TextoSuperpuestoResponse(BaseModel):
    """Modelo para respuesta de análisis de texto superpuesto"""
    success: bool
    mensaje: str
    tipo_archivo: str
    analisis_detallado: Dict[str, Any]
    reporte_texto: Optional[str] = None
    xml_estructura: Optional[Dict[str, Any]] = None
    resumen: Dict[str, Any]


@router.post("/detectar-texto-superpuesto-universal", response_model=TextoSuperpuestoResponse)
async def detectar_texto_superpuesto_universal(request: ArchivoRequest):
    """
    Detecta texto superpuesto en PDFs o imágenes analizando metadatos, capas y superposiciones.
    
    **Soporta:**
    - PDFs: Análisis de las 4 zonas principales (anotaciones, contenido, XObject, AcroForm)
    - Imágenes: Análisis de metadatos EXIF/IPTC/XMP, capas, y superposición de texto
    
    **Tipos de archivo soportados:**
    - PDF: application/pdf
    - JPEG: image/jpeg
    - PNG: image/png
    - GIF: image/gif
    - BMP: image/bmp
    - TIFF: image/tiff
    - PSD: image/vnd.adobe.photoshop
    - HEIC: image/heic
    
    **Args:**
    - archivo_base64: Archivo codificado en base64
    - tipo_archivo: Tipo de archivo (opcional, se detecta automáticamente)
    
    **Returns:**
    - Análisis detallado según el tipo de archivo
    - Reporte legible del análisis
    - Estructura XML (solo para PDFs)
    - Resumen con probabilidad de manipulación
    """
    try:
        # Detectar tipo de archivo si no se especifica
        if not request.tipo_archivo:
            tipo_info = detectar_tipo_archivo(request.archivo_base64)
            if not tipo_info["valido"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Archivo no válido: {tipo_info.get('error', 'Tipo desconocido')}"
                )
            tipo_archivo = tipo_info["tipo"]
        else:
            tipo_archivo = request.tipo_archivo.upper()
        
        # Procesar según el tipo de archivo
        if tipo_archivo == "PDF":
            # Análisis de PDF
            analisis_detallado = detectar_texto_superpuesto_detallado(request.archivo_base64)
            reporte_texto = generar_reporte_texto_superpuesto(analisis_detallado)
            xml_estructura = analisis_detallado.get("xml_estructura", {})
            
            # Extraer resumen
            resumen = analisis_detallado.get("resumen_general", {})
            probabilidad = resumen.get("overlay_probability", 0.0)
            nivel_riesgo = resumen.get("risk_level", "UNKNOWN")
            
        else:
            # Análisis de imagen
            analisis_detallado = analizar_imagen_completa(request.archivo_base64)
            
            if "error" in analisis_detallado:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error analizando imagen: {analisis_detallado['error']}"
                )
            
            # Generar reporte para imagen
            reporte_texto = _generar_reporte_imagen(analisis_detallado)
            xml_estructura = None
            
            # Extraer resumen
            probabilidad = analisis_detallado.get("probabilidad_manipulacion", 0.0)
            nivel_riesgo = analisis_detallado.get("nivel_riesgo", "UNKNOWN")
            resumen = analisis_detallado.get("resumen", {})
        
        return TextoSuperpuestoResponse(
            success=True,
            mensaje=f"Análisis completado para {tipo_archivo}",
            tipo_archivo=tipo_archivo,
            analisis_detallado=analisis_detallado,
            reporte_texto=reporte_texto,
            xml_estructura=xml_estructura,
            resumen={
                "probabilidad_manipulacion": probabilidad,
                "nivel_riesgo": nivel_riesgo,
                **resumen
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/detectar-texto-superpuesto", response_model=TextoSuperpuestoResponse)
async def detectar_texto_superpuesto_endpoint(request: PDFRequest):
    """
    Detecta texto superpuesto en un PDF analizando las 4 zonas principales:
    
    1. **Anotaciones (Annotations)**: Comentarios, notas, sellos, campos de formulario
    2. **Contenido de Página**: Nuevo contenido agregado al final del stream
    3. **Form XObject**: Objetos de formulario reutilizables
    4. **AcroForm**: Campos de formulario del documento
    
    **Args:**
    - pdfbase64: PDF codificado en base64
    
    **Returns:**
    - Análisis detallado de las 4 zonas
    - Reporte legible del análisis
    - Estructura XML del PDF
    - Resumen con probabilidad de superposición
    """
    try:
        # Validar entrada
        if not request.pdfbase64:
            raise HTTPException(status_code=400, detail="PDF en base64 es requerido")
        
        # Validar formato base64
        try:
            base64.b64decode(request.pdfbase64)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato base64 inválido")
        
        # Realizar análisis detallado
        analisis = detectar_texto_superpuesto_detallado(request.pdfbase64)
        
        if "error" in analisis:
            raise HTTPException(status_code=500, detail=f"Error en análisis: {analisis['error']}")
        
        # Generar reporte
        reporte_texto = generar_reporte_texto_superpuesto(analisis)
        
        # Extraer XML/estructura
        xml_estructura = analisis.get("xml_estructura", {})
        
        # Generar resumen
        resumen_general = analisis.get("resumen_general", {})
        resumen = {
            "probabilidad_superposicion": resumen_general.get("overlay_probability", 0.0),
            "nivel_riesgo": resumen_general.get("risk_level", "UNKNOWN"),
            "zonas_analizadas": 8,  # Incluyendo análisis avanzado, stream, capas e imágenes
            "zonas_con_superposicion": resumen_general.get("zones_with_overlay", 0),
            "total_anotaciones": analisis.get("zona_1_anotaciones", {}).get("total_annotations", 0),
            "streams_contenido": analisis.get("zona_2_contenido_pagina", {}).get("stream_count", 0),
            "form_xobjects": analisis.get("zona_3_form_xobject", {}).get("xobject_count", 0),
            "campos_formulario": len(analisis.get("zona_4_acroform", {}).get("form_fields", [])),
            "recomendaciones": resumen_general.get("recommendations", [])
        }
        
        return TextoSuperpuestoResponse(
            success=True,
            mensaje="Análisis de texto superpuesto completado exitosamente",
            tipo_archivo="PDF",
            analisis_detallado=analisis,
            reporte_texto=reporte_texto,
            xml_estructura=xml_estructura,
            resumen=resumen
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/detectar-texto-superpuesto-simple")
async def detectar_texto_superpuesto_simple(
    pdfbase64: str = Form(..., description="Archivo (PDF o imagen) codificado en base64"),
    incluir_reporte: bool = Form(True, description="Incluir reporte legible"),
    incluir_xml: bool = Form(True, description="Incluir estructura XML")
):
    """
    Versión simplificada del endpoint que acepta base64 como form data.
    Detecta automáticamente si es PDF o imagen y usa el análisis apropiado.
    Más fácil de probar desde herramientas como Postman o curl.
    """
    try:
        # Validar entrada
        if not pdfbase64:
            raise HTTPException(status_code=400, detail="Archivo en base64 es requerido")
        
        # Validar formato base64
        try:
            base64.b64decode(pdfbase64)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato base64 inválido")
        
        # Detectar tipo de archivo automáticamente
        tipo_info = detectar_tipo_archivo(pdfbase64)
        
        if not tipo_info["valido"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Archivo no válido: {tipo_info.get('error', 'Tipo desconocido')}"
            )
        
        tipo_archivo = tipo_info["tipo"]
        
        # Procesar según el tipo de archivo
        if tipo_archivo == "PDF":
            # Análisis de PDF
            analisis = detectar_texto_superpuesto_detallado(pdfbase64)
        else:
            # Análisis de imagen
            analisis = analizar_imagen_completa(pdfbase64)
        
        if "error" in analisis:
            raise HTTPException(status_code=500, detail=f"Error en análisis: {analisis['error']}")
        
        # Generar reporte si se solicita
        reporte_texto = None
        if incluir_reporte:
            if tipo_archivo == "PDF":
                reporte_texto = generar_reporte_texto_superpuesto(analisis)
            else:
                reporte_texto = _generar_reporte_imagen(analisis)
        
        # Extraer XML/estructura si se solicita (solo para PDFs)
        xml_estructura = None
        if incluir_xml and tipo_archivo == "PDF":
            xml_estructura = analisis.get("xml_estructura", {})
        
        # Generar resumen según el tipo de archivo
        if tipo_archivo == "PDF":
            resumen_general = analisis.get("resumen_general", {})
            resumen = {
                "probabilidad_superposicion": resumen_general.get("overlay_probability", 0.0),
                "nivel_riesgo": resumen_general.get("risk_level", "UNKNOWN"),
                "zonas_analizadas": 8,  # Incluyendo análisis avanzado, stream, capas e imágenes
                "zonas_con_superposicion": resumen_general.get("zones_with_overlay", 0),
                "total_anotaciones": analisis.get("zona_1_anotaciones", {}).get("total_annotations", 0),
                "streams_contenido": analisis.get("zona_2_contenido_pagina", {}).get("stream_count", 0),
                "form_xobjects": analisis.get("zona_3_form_xobject", {}).get("xobject_count", 0),
                "campos_formulario": len(analisis.get("zona_4_acroform", {}).get("form_fields", [])),
                "recomendaciones": resumen_general.get("recommendations", [])
            }
        else:
            # Resumen para imágenes
            resumen = {
                "probabilidad_manipulacion": analisis.get("probabilidad_manipulacion", 0.0),
                "nivel_riesgo": analisis.get("nivel_riesgo", "UNKNOWN"),
                "tipo_archivo": tipo_archivo,
                "tiene_metadatos_sospechosos": analisis.get("resumen", {}).get("tiene_metadatos_sospechosos", False),
                "tiene_texto_superpuesto": analisis.get("resumen", {}).get("tiene_texto_superpuesto", False),
                "tiene_capas_ocultas": analisis.get("resumen", {}).get("tiene_capas_ocultas", False),
                "total_indicadores": analisis.get("resumen", {}).get("total_indicadores", 0),
                "indicadores_sospechosos": analisis.get("indicadores_sospechosos", [])
            }
        
        return {
            "success": True,
            "mensaje": f"Análisis de {tipo_archivo} completado exitosamente",
            "tipo_archivo": tipo_archivo,
            "analisis_detallado": analisis,
            "reporte_texto": reporte_texto,
            "xml_estructura": xml_estructura,
            "resumen": resumen
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/detectar-texto-superpuesto-query")
async def detectar_texto_superpuesto_query(
    pdfbase64: str = Query(..., description="PDF codificado en base64"),
    incluir_reporte: bool = Query(True, description="Incluir reporte legible"),
    incluir_xml: bool = Query(True, description="Incluir estructura XML")
):
    """
    Versión que acepta base64 como query parameter.
    Útil para pruebas rápidas desde el navegador.
    """
    try:
        # Validar entrada
        if not pdfbase64:
            raise HTTPException(status_code=400, detail="PDF en base64 es requerido")
        
        # Validar formato base64
        try:
            base64.b64decode(pdfbase64)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato base64 inválido")
        
        # Realizar análisis detallado
        analisis = detectar_texto_superpuesto_detallado(pdfbase64)
        
        if "error" in analisis:
            raise HTTPException(status_code=500, detail=f"Error en análisis: {analisis['error']}")
        
        # Generar reporte si se solicita
        reporte_texto = None
        if incluir_reporte:
            reporte_texto = generar_reporte_texto_superpuesto(analisis)
        
        # Extraer XML/estructura si se solicita
        xml_estructura = None
        if incluir_xml:
            xml_estructura = analisis.get("xml_estructura", {})
        
        # Generar resumen
        resumen_general = analisis.get("resumen_general", {})
        resumen = {
            "probabilidad_superposicion": resumen_general.get("overlay_probability", 0.0),
            "nivel_riesgo": resumen_general.get("risk_level", "UNKNOWN"),
            "zonas_analizadas": 8,  # Incluyendo análisis avanzado, stream, capas e imágenes
            "zonas_con_superposicion": resumen_general.get("zones_with_overlay", 0),
            "total_anotaciones": analisis.get("zona_1_anotaciones", {}).get("total_annotations", 0),
            "streams_contenido": analisis.get("zona_2_contenido_pagina", {}).get("stream_count", 0),
            "form_xobjects": analisis.get("zona_3_form_xobject", {}).get("xobject_count", 0),
            "campos_formulario": len(analisis.get("zona_4_acroform", {}).get("form_fields", [])),
            "recomendaciones": resumen_general.get("recommendations", [])
        }
        
        return {
            "success": True,
            "mensaje": "Análisis de texto superpuesto completado exitosamente",
            "tipo_archivo": "PDF",
            "analisis_detallado": analisis,
            "reporte_texto": reporte_texto,
            "xml_estructura": xml_estructura,
            "resumen": resumen
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


def _generar_reporte_imagen(analisis_imagen: Dict[str, Any]) -> str:
    """
    Genera un reporte legible del análisis de imagen.
    
    Args:
        analisis_imagen: Resultado del análisis de imagen
        
    Returns:
        Reporte en formato texto
    """
    if "error" in analisis_imagen:
        return f"❌ Error en el análisis: {analisis_imagen['error']}"
    
    report = []
    report.append("=" * 80)
    report.append("🖼️  REPORTE DE ANÁLISIS FORENSE DE IMAGEN")
    report.append("=" * 80)
    
    # Información básica del archivo
    tipo_archivo = analisis_imagen.get("tipo_archivo", {})
    report.append(f"📁 Tipo de archivo: {tipo_archivo.get('tipo', 'UNKNOWN')}")
    report.append(f"📄 Extensión: {tipo_archivo.get('extension', 'unknown')}")
    report.append(f"🔗 MIME Type: {tipo_archivo.get('mime_type', 'unknown')}")
    report.append("")
    
    # Resumen general
    probabilidad = analisis_imagen.get("probabilidad_manipulacion", 0.0)
    nivel_riesgo = analisis_imagen.get("nivel_riesgo", "UNKNOWN")
    report.append(f"📊 Probabilidad de manipulación: {probabilidad:.1%}")
    report.append(f"⚠️  Nivel de riesgo: {nivel_riesgo}")
    report.append("")
    
    # Metadatos
    metadatos = analisis_imagen.get("metadatos", {})
    if metadatos:
        report.append("📋 METADATOS:")
        
        # Metadatos básicos
        basicos = metadatos.get("basicos", {})
        if basicos:
            report.append(f"   Formato: {basicos.get('formato', 'N/A')}")
            report.append(f"   Modo: {basicos.get('modo', 'N/A')}")
            report.append(f"   Tamaño: {basicos.get('ancho', 0)}x{basicos.get('alto', 0)}px")
            report.append(f"   Transparencia: {basicos.get('has_transparency', False)}")
        
        # EXIF data
        exif = metadatos.get("exif", {})
        if exif:
            report.append(f"   Metadatos EXIF: {len(exif)} campos")
            # Mostrar algunos campos importantes
            campos_importantes = ["Software", "DateTime", "Make", "Model", "GPS GPSLatitude"]
            for campo in campos_importantes:
                if campo in exif:
                    report.append(f"     {campo}: {exif[campo]}")
        
        # Metadatos sospechosos
        sospechosos = metadatos.get("sospechosos", [])
        if sospechosos:
            report.append("   🚨 METADATOS SOSPECHOSOS:")
            for sospechoso in sospechosos:
                report.append(f"     • {sospechoso}")
        else:
            report.append("   ✅ No se encontraron metadatos sospechosos")
        
        report.append("")
    
    # Análisis de capas
    capas = analisis_imagen.get("capas", {})
    if capas and not capas.get("error"):
        report.append("🎨 ANÁLISIS DE CAPAS:")
        report.append(f"   Tiene capas: {capas.get('tiene_capas', False)}")
        report.append(f"   Total capas: {capas.get('total_capas', 0)}")
        report.append(f"   Capas ocultas: {capas.get('capas_ocultas', 0)}")
        
        if capas.get("capas"):
            report.append("   Detalles de capas:")
            for i, capa in enumerate(capas["capas"][:5]):  # Mostrar solo las primeras 5
                report.append(f"     Capa {i+1}: {capa.get('tamaño', 'N/A')} - {capa.get('modo', 'N/A')}")
        
        if capas.get("sospechosas"):
            report.append("   🚨 CAPAS SOSPECHOSAS:")
            for sospechosa in capas["sospechosas"]:
                report.append(f"     • {sospechosa}")
        
        report.append("")
    
    # Análisis de superposición de texto
    superposicion = analisis_imagen.get("superposicion_texto", {})
    if superposicion and not superposicion.get("error"):
        report.append("🔍 ANÁLISIS DE SUPERPOSICIÓN DE TEXTO:")
        report.append(f"   Tiene texto superpuesto: {superposicion.get('tiene_texto_superpuesto', False)}")
        report.append(f"   Probabilidad: {superposicion.get('probabilidad', 0):.1%}")
        
        indicadores = superposicion.get("indicadores", [])
        if indicadores:
            report.append("   Indicadores detectados:")
            for indicador in indicadores:
                report.append(f"     • {indicador}")
        
        areas_sospechosas = superposicion.get("areas_sospechosas", [])
        if areas_sospechosas:
            report.append(f"   Áreas sospechosas: {len(areas_sospechosas)}")
        
        report.append("")
    
    # Indicadores generales
    indicadores_generales = analisis_imagen.get("indicadores_sospechosos", [])
    if indicadores_generales:
        report.append("🚨 INDICADORES SOSPECHOSOS GENERALES:")
        for indicador in indicadores_generales:
            report.append(f"   • {indicador}")
        report.append("")
    
    # Resumen final
    resumen = analisis_imagen.get("resumen", {})
    if resumen:
        report.append("📊 RESUMEN FINAL:")
        report.append(f"   Metadatos sospechosos: {resumen.get('tiene_metadatos_sospechosos', False)}")
        report.append(f"   Texto superpuesto: {resumen.get('tiene_texto_superpuesto', False)}")
        report.append(f"   Capas ocultas: {resumen.get('tiene_capas_ocultas', False)}")
        report.append(f"   Total indicadores: {resumen.get('total_indicadores', 0)}")
        report.append("")
    
    report.append("=" * 80)
    
    return "\n".join(report)


@router.get("/ejemplo_deteccion_texto")
async def ejemplo_deteccion_texto():
    """
    Ejemplo de uso del endpoint de detección de texto superpuesto.
    """
    return {
        "descripcion": "Endpoint para detectar texto superpuesto en PDFs e imágenes",
        "endpoints_disponibles": {
            "json": "/detectar-texto-superpuesto",
            "form_data": "/detectar-texto-superpuesto-simple", 
            "query_params": "/detectar-texto-superpuesto-query",
            "universal": "/detectar-texto-superpuesto-universal"
        },
        "curl_ejemplo_json": """
curl -X POST "http://localhost:8001/detectar-texto-superpuesto" \\
  -H "Content-Type: application/json" \\
  -d '{"pdfbase64": "JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDMgMCBSCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDYgMCBSCj4+Cj4+Ci9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCi9Db250ZW50cyA3IDAgUgo+PgplbmRvYmoK..."}'
        """,
        "curl_ejemplo_form": """
curl -X POST "http://localhost:8001/detectar-texto-superpuesto-simple" \\
  -F "pdfbase64=JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDMgMCBSCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDYgMCBSCj4+Cj4+Ci9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCi9Db250ZW50cyA3IDAgUgo+PgplbmRvYmoK..." \\
  -F "incluir_reporte=true" \\
  -F "incluir_xml=true"
        """,
        "curl_ejemplo_query": """
curl "http://localhost:8001/detectar-texto-superpuesto-query?pdfbase64=JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDMgMCBSCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDYgMCBSCj4+Cj4+Ci9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCi9Db250ZW50cyA3IDAgUgo+PgplbmRvYmoK...&incluir_reporte=true&incluir_xml=true"
        """,
        "python_ejemplo": """
import requests
import base64

# Leer PDF y codificar en base64
with open("documento.pdf", "rb") as f:
    pdf_base64 = base64.b64encode(f.read()).decode()

# Enviar solicitud
response = requests.post(
    "http://localhost:8001/detectar-texto-superpuesto",
    json={
        "pdfbase64": pdf_base64
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Probabilidad: {data['resumen']['probabilidad_superposicion']}")
    print(f"Nivel de riesgo: {data['resumen']['nivel_riesgo']}")
    print(f"Reporte: {data['reporte_texto']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
        """,
        "notas": [
            "El archivo debe estar codificado en base64",
            "El análisis puede tomar varios segundos dependiendo del tamaño del archivo",
            "Se analizan las 4 zonas principales donde se puede superponer texto (PDFs)",
            "Para imágenes se analizan metadatos, capas y superposición de texto",
            "El reporte incluye detalles técnicos de cada zona analizada"
        ]
    }
