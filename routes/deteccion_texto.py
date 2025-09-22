"""
Endpoint para detección detallada de texto superpuesto en PDFs.

Analiza las 4 zonas principales donde se puede "tapar" texto:
1. Anotaciones (Annotations) sobre la página
2. Contenido nuevo en la propia página (Page Contents)  
3. Form XObject llamado desde la página
4. Campo de formulario (AcroForm)
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
from helpers.type_conversion import safe_serialize_dict
from helpers.analisis_imagenes import analizar_imagen_completa
from helpers.analisis_forense_profesional import analisis_forense_completo

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
            from helpers.analisis_imagenes import detectar_tipo_archivo
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
            # Solo análisis forense profesional
            imagen_bytes = base64.b64decode(request.archivo_base64)
            
            # Convertir imagen a JPEG si no es JPEG/JPG para análisis forense
            imagen_bytes_jpeg = imagen_bytes
            if not tipo_archivo in ["JPEG", "JPG"]:
                try:
                    from PIL import Image
                    import io
                    
                    # Abrir imagen original
                    img_original = Image.open(io.BytesIO(imagen_bytes))
                    
                    # Convertir a RGB si es necesario
                    if img_original.mode not in ("RGB", "L"):
                        img_original = img_original.convert("RGB")
                    
                    # Convertir a JPEG con calidad 95
                    jpeg_buffer = io.BytesIO()
                    img_original.save(jpeg_buffer, format="JPEG", quality=95, optimize=True)
                    imagen_bytes_jpeg = jpeg_buffer.getvalue()
                    
                    print(f"Imagen convertida a JPEG para análisis forense. Tamaño original: {len(imagen_bytes)} bytes, JPEG: {len(imagen_bytes_jpeg)} bytes")
                    
                except Exception as e:
                    print(f"Error convirtiendo imagen a JPEG: {e}")
                    # Usar imagen original si falla la conversión
                    imagen_bytes_jpeg = imagen_bytes
            
            # Análisis forense profesional
            try:
                from helpers.analisis_forense_profesional import analisis_forense_completo as analisis_forense_profesional
                analisis_forense_profesional = analisis_forense_profesional(imagen_bytes)
                
            except Exception as e:
                # Si falla el análisis profesional, devolver error
                raise HTTPException(
                    status_code=500,
                    detail=f"Error en análisis forense profesional: {str(e)}"
                )
            
            # Crear respuesta simplificada solo con análisis forense profesional
            analisis_detallado = {
                "analisis_forense_profesional": analisis_forense_profesional
            }
            
            # Generar reporte simple
            reporte_texto = f"Análisis forense profesional completado para {tipo_archivo}"
            xml_estructura = None
            
            # Resumen simple
            probabilidad = 0.5 if analisis_forense_profesional.get("grado_confianza") in ["ALTO", "MEDIO"] else 0.1
            nivel_riesgo = "HIGH" if analisis_forense_profesional.get("grado_confianza") == "ALTO" else "MEDIUM" if analisis_forense_profesional.get("grado_confianza") == "MEDIO" else "LOW"
            resumen = {
                "probabilidad_manipulacion": probabilidad,
                "nivel_riesgo": nivel_riesgo,
                "grado_confianza": analisis_forense_profesional.get("grado_confianza", "BAJO"),
                "porcentaje_confianza": analisis_forense_profesional.get("porcentaje_confianza", 0),
                "evidencias": analisis_forense_profesional.get("evidencias", [])
            }
        
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
    - `pdfbase64`: PDF codificado en base64 (string)
    
    **Returns:**
    - Análisis detallado de las 4 zonas
    - Probabilidad de superposición
    - Nivel de riesgo (LOW/MEDIUM/HIGH)
    - Reporte legible
    - Estructura XML del PDF
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
            "zonas_analizadas": 4,
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


@router.get("/detectar-texto-superpuesto/info")
async def info_deteccion_texto():
    """
    Información sobre el endpoint de detección de texto superpuesto.
    
    Explica las 4 zonas analizadas y sus características.
    """
    return {
        "endpoint": "/detectar-texto-superpuesto",
        "descripcion": "Detecta texto superpuesto en PDFs analizando 4 zonas principales",
        "metodo": "POST",
        "parametros": {
            "pdfbase64": "PDF codificado en base64 (requerido)",
            "incluir_reporte": "Incluir reporte legible (opcional, default: true)",
            "incluir_xml": "Incluir estructura XML del PDF (opcional, default: true)"
        },
        "zonas_analizadas": {
            "zona_1_anotaciones": {
                "nombre": "Anotaciones (Annotations)",
                "descripcion": "Comentarios, notas, sellos, campos de formulario",
                "ubicacion": "/Annots (array) de cada página",
                "caracteristicas": ["/Subtype y /Rect (bbox)", "/AP /N (appearance stream)"],
                "probabilidad": "Alta - método más común"
            },
            "zona_2_contenido_pagina": {
                "nombre": "Contenido de Página (Page Contents)",
                "descripcion": "Nuevo contenido agregado al final del stream",
                "ubicacion": "/Contents (stream o array de streams)",
                "caracteristicas": ["BT ... Tj/TJ ... ET (texto)", "re f (rectángulo)"],
                "probabilidad": "Alta - editores 'estampan' texto"
            },
            "zona_3_form_xobject": {
                "nombre": "Form XObject",
                "descripcion": "Objetos de formulario reutilizables",
                "ubicacion": "/Resources /XObject",
                "caracteristicas": ["Se invocan con /Nombre Do", "No toca stream principal"],
                "probabilidad": "Media - forma elegante de superponer"
            },
            "zona_4_acroform": {
                "nombre": "AcroForm (Campos de Formulario)",
                "descripcion": "Campos de formulario del documento",
                "ubicacion": "/AcroForm /Fields",
                "caracteristicas": ["/Subtype /Widget", "/AP /N (apariencia)"],
                "probabilidad": "Baja - para formularios específicos"
            }
        },
        "respuesta": {
            "success": "boolean - si el análisis fue exitoso",
            "mensaje": "string - mensaje descriptivo",
            "analisis_detallado": "object - análisis completo de las 4 zonas",
            "reporte_texto": "string - reporte legible (opcional)",
            "xml_estructura": "object - estructura XML del PDF (opcional)",
            "resumen": "object - resumen con métricas clave"
        },
        "ejemplo_uso": {
            "pdfbase64": "JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDMgMCBSCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDYgMCBSCj4+Cj4+Ci9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCi9Db250ZW50cyA3IDAgUgo+PgplbmRvYmoK...",
            "incluir_reporte": True,
            "incluir_xml": True
        }
    }


@router.post("/detectar-texto-superpuesto-simple")
async def detectar_texto_superpuesto_simple(
    pdfbase64: str = Form(..., description="PDF codificado en base64"),
    incluir_reporte: bool = Form(True, description="Incluir reporte legible"),
    incluir_xml: bool = Form(True, description="Incluir estructura XML")
):
    """
    Versión simplificada del endpoint que acepta base64 como form data.
    Solo maneja PDFs. Para imágenes usa el endpoint universal.
    Más fácil de probar desde herramientas como Postman o curl.
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
        
        # Realizar análisis detallado de PDF
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
            "zonas_analizadas": 4,
            "zonas_con_superposicion": resumen_general.get("zones_with_overlay", 0),
            "total_anotaciones": analisis.get("zona_1_anotaciones", {}).get("total_annotations", 0),
            "streams_contenido": analisis.get("zona_2_contenido_pagina", {}).get("stream_count", 0),
            "form_xobjects": analisis.get("zona_3_form_xobject", {}).get("xobject_count", 0),
            "campos_formulario": len(analisis.get("zona_4_acroform", {}).get("form_fields", [])),
            "recomendaciones": resumen_general.get("recommendations", [])
        }
        
        return safe_serialize_dict({
            "success": True,
            "mensaje": "Análisis de texto superpuesto completado exitosamente",
            "analisis_detallado": analisis,
            "reporte_texto": reporte_texto,
            "xml_estructura": xml_estructura,
            "resumen": resumen
        })
        
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
            "zonas_analizadas": 4,
            "zonas_con_superposicion": resumen_general.get("zones_with_overlay", 0),
            "total_anotaciones": analisis.get("zona_1_anotaciones", {}).get("total_annotations", 0),
            "streams_contenido": analisis.get("zona_2_contenido_pagina", {}).get("stream_count", 0),
            "form_xobjects": analisis.get("zona_3_form_xobject", {}).get("xobject_count", 0),
            "campos_formulario": len(analisis.get("zona_4_acroform", {}).get("form_fields", [])),
            "recomendaciones": resumen_general.get("recommendations", [])
        }
        
        return safe_serialize_dict({
            "success": True,
            "mensaje": "Análisis de texto superpuesto completado exitosamente",
            "analisis_detallado": analisis,
            "reporte_texto": reporte_texto,
            "xml_estructura": xml_estructura,
            "resumen": resumen
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/detectar-texto-superpuesto/ejemplo")
async def ejemplo_deteccion_texto():
    """
    Ejemplo de uso del endpoint de detección de texto superpuesto.
    """
    return {
        "mensaje": "Ejemplo de uso del endpoint /detectar-texto-superpuesto",
        "curl_ejemplo_json": """
curl -X POST "http://localhost:8001/detectar-texto-superpuesto" \\
  -H "Content-Type: application/json" \\
  -d '{
    "pdfbase64": "JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDMgMCBSCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDYgMCBSCj4+Cj4+Ci9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCi9Db250ZW50cyA3IDAgUgo+PgplbmRvYmoK..."
  }'
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

# Procesar respuesta
if response.status_code == 200:
    data = response.json()
    print(f"Probabilidad de superposición: {data['resumen']['probabilidad_superposicion']:.1%}")
    print(f"Nivel de riesgo: {data['resumen']['nivel_riesgo']}")
    print(f"Reporte: {data['reporte_texto']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
        """,
        "notas": [
            "El PDF debe estar codificado en base64",
            "El análisis puede tomar varios segundos dependiendo del tamaño del PDF",
            "Se analizan las 4 zonas principales donde se puede superponer texto",
            "El reporte incluye detalles técnicos de cada zona analizada"
        ]
    }


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
    
    # Análisis forense avanzado
    analisis_forense = analisis_imagen.get("analisis_forense", {})
    if analisis_forense and not analisis_forense.get("error"):
        report.append("🔬 ANÁLISIS FORENSE AVANZADO:")
        
        # Hashes forenses
        hashes = analisis_forense.get("hashes", {})
        if hashes:
            report.append("   📋 HASHES FORENSES:")
            report.append(f"     MD5: {hashes.get('md5', 'N/A')}")
            report.append(f"     SHA256: {hashes.get('sha256', 'N/A')}")
            report.append(f"     pHash: {hashes.get('phash', 'N/A')}")
            report.append(f"     Timestamp: {hashes.get('timestamp', 'N/A')}")
        
        # Análisis ELA (solo para JPEG)
        if "ela" in analisis_forense and not analisis_forense["ela"].get("error"):
            ela = analisis_forense["ela"]
            report.append("   🖼️  ERROR LEVEL ANALYSIS (ELA):")
            report.append(f"     Nivel de sospecha: {ela.get('nivel_sospecha', 'N/A')}")
            report.append(f"     Porcentaje sospechoso: {ela.get('porcentaje_sospechoso', 0):.1f}%")
            report.append(f"     Densidad de bordes: {ela.get('edge_density', 0):.3f}")
            if ela.get("tiene_ediciones"):
                report.append("     🚨 EDICIONES DETECTADAS por ELA")
        
        # Doble compresión
        if "doble_compresion" in analisis_forense and not analisis_forense["doble_compresion"].get("error"):
            dc = analisis_forense["doble_compresion"]
            report.append("   🔄 ANÁLISIS DE DOBLE COMPRESIÓN:")
            report.append(f"     Confianza: {dc.get('confianza', 'N/A')}")
            report.append(f"     Periodicidad: {dc.get('periodicidad_detectada', False)}")
            report.append(f"     Varianza alta: {dc.get('varianza_alta', False)}")
            if dc.get("tiene_doble_compresion"):
                report.append("     🚨 DOBLE COMPRESIÓN DETECTADA")
        
        # Ruido y bordes
        if "ruido_bordes" in analisis_forense and not analisis_forense["ruido_bordes"].get("error"):
            rb = analisis_forense["ruido_bordes"]
            report.append("   🔍 ANÁLISIS DE RUIDO Y BORDES:")
            report.append(f"     Nivel de sospecha: {rb.get('nivel_sospecha', 'N/A')}")
            report.append(f"     Líneas detectadas: {rb.get('num_lines', 0)}")
            report.append(f"     Líneas paralelas: {rb.get('parallel_lines', 0)}")
            report.append(f"     Ratio de outliers: {rb.get('outlier_ratio', 0):.3f}")
            if rb.get("tiene_edicion_local"):
                report.append("     🚨 EDICIÓN LOCAL DETECTADA")
        
        # pHash por bloques
        if "phash_bloques" in analisis_forense and not analisis_forense["phash_bloques"].get("error"):
            ph = analisis_forense["phash_bloques"]
            report.append("   🧩 ANÁLISIS pHash POR BLOQUES:")
            report.append(f"     Nivel de sospecha: {ph.get('nivel_sospecha', 'N/A')}")
            report.append(f"     Bloques analizados: {ph.get('num_bloques', 0)}")
            report.append(f"     Diferencia máxima: {ph.get('max_difference', 0)}")
            report.append(f"     Ratio de outliers: {ph.get('outlier_ratio', 0):.3f}")
            if ph.get("tiene_diferencias_locales"):
                report.append("     🚨 DIFERENCIAS LOCALES DETECTADAS")
        
        # SSIM regional
        if "ssim_regional" in analisis_forense and not analisis_forense["ssim_regional"].get("error"):
            ss = analisis_forense["ssim_regional"]
            report.append("   📊 ANÁLISIS SSIM REGIONAL:")
            report.append(f"     Nivel de sospecha: {ss.get('nivel_sospecha', 'N/A')}")
            report.append(f"     Comparaciones: {ss.get('num_comparaciones', 0)}")
            report.append(f"     SSIM mínimo: {ss.get('min_ssim', 0):.3f}")
            report.append(f"     Ratio baja similitud: {ss.get('low_similarity_ratio', 0):.3f}")
            if ss.get("tiene_inconsistencias"):
                report.append("     🚨 INCONSISTENCIAS REGIONALES DETECTADAS")
        
        # Grado de confianza final
        grado_confianza = analisis_forense.get("grado_confianza", {})
        if grado_confianza:
            report.append("   🎯 GRADO DE CONFIANZA FINAL:")
            report.append(f"     Grado: {grado_confianza.get('grado_confianza', 'N/A')}")
            report.append(f"     Porcentaje: {grado_confianza.get('porcentaje_confianza', 0):.1f}%")
            report.append(f"     Puntuación: {grado_confianza.get('puntuacion', 0)}/{grado_confianza.get('max_puntuacion', 0)}")
            report.append(f"     Justificación: {grado_confianza.get('justificacion', 'N/A')}")
            report.append(f"     Recomendación: {grado_confianza.get('recomendacion', 'N/A')}")
            
            evidencias = grado_confianza.get("evidencias", [])
            if evidencias:
                report.append("     Evidencias encontradas:")
                for evidencia in evidencias:
                    report.append(f"       • {evidencia}")
        
        report.append("")
    
    # Análisis forense profesional
    analisis_profesional = analisis_imagen.get("analisis_forense_profesional", {})
    if analisis_profesional and not analisis_profesional.get("error"):
        report.append("🔬 ANÁLISIS FORENSE PROFESIONAL:")
        
        # Metadatos forenses
        metadatos_prof = analisis_profesional.get("metadatos", {})
        if metadatos_prof:
            report.append("   📋 METADATOS FORENSES:")
            
            # Software de edición
            software_edicion = metadatos_prof.get("software_edicion", [])
            if software_edicion:
                report.append("     Software detectado:")
                for sw in software_edicion:
                    report.append(f"       • {sw}")
            
            # Análisis de fechas
            fechas_analisis = metadatos_prof.get("fechas_analisis", [])
            if fechas_analisis:
                report.append("     Análisis de fechas:")
                for fecha in fechas_analisis:
                    report.append(f"       • {fecha}")
            
            # Análisis de cámara
            camara_analisis = metadatos_prof.get("camara_analisis", [])
            if camara_analisis:
                report.append("     Análisis de cámara/dispositivo:")
                for camara in camara_analisis:
                    report.append(f"       • {camara}")
        
        # Análisis de compresión
        compresion_prof = analisis_profesional.get("compresion", {})
        if compresion_prof:
            report.append("   🔄 ANÁLISIS DE COMPRESIÓN AVANZADO:")
            
            # Calidad detectada
            quality_analysis = compresion_prof.get("quality_analysis", {})
            if quality_analysis:
                report.append(f"     Calidad probable: {quality_analysis.get('calidad_probable', 'N/A')}")
            
            # Indicadores de app
            app_indicators = compresion_prof.get("app_indicators", [])
            if app_indicators:
                report.append("     Indicadores de aplicación:")
                for indicator in app_indicators:
                    report.append(f"       • {indicator}")
        
        # Análisis de cuadrícula JPEG
        cuadricula_prof = analisis_profesional.get("cuadricula_jpeg", {})
        if cuadricula_prof and not cuadricula_prof.get("error"):
            report.append("   🔲 ANÁLISIS DE CUADRÍCULA JPEG:")
            
            # Desalineación de bloques
            desalineacion = cuadricula_prof.get("desalineacion_analisis", {})
            if desalineacion:
                report.append(f"     Discontinuidades en filas: {desalineacion.get('discontinuidades_filas', 0)}")
                report.append(f"     Discontinuidades en columnas: {desalineacion.get('discontinuidades_columnas', 0)}")
                report.append(f"     Total discontinuidades: {desalineacion.get('total_discontinuidades', 0)}")
            
            # Análisis de splicing
            splicing = cuadricula_prof.get("splicing_analisis", {})
            if splicing:
                report.append(f"     Bordes sospechosos: {splicing.get('bordes_sospechosos', 0)}")
            
            # Localización
            localizacion = cuadricula_prof.get("localizacion_analisis", {})
            if localizacion:
                report.append(f"     Densidad de bordes: {localizacion.get('densidad_bordes_sospechosos', 0):.3f}")
                report.append(f"     Es localizado: {localizacion.get('es_localizado', False)}")
                report.append(f"     Bordes agrupados: {localizacion.get('bordes_agrupados', False)}")
            
            # Resultado final
            if cuadricula_prof.get("tiene_splicing"):
                report.append("     🚨 SPLICING DETECTADO - CUADRÍCULA JPEG LOCALIZADA")
            elif cuadricula_prof.get("nivel_sospecha") == "ALTO":
                report.append("     ⚠️ ALTA SOSPECHA DE MANIPULACIÓN")
            else:
                report.append("     ✅ Sin evidencia de splicing")
        
        # Análisis de texto sintético aplanado
        texto_sintetico_prof = analisis_profesional.get("texto_sintetico", {})
        if texto_sintetico_prof and not texto_sintetico_prof.get("error"):
            report.append("   📝 ANÁLISIS DE TEXTO SINTÉTICO APLANADO:")
            
            # Regla de re-guardado + bordes
            reguardado = texto_sintetico_prof.get("reguardado_analisis", {})
            if reguardado:
                report.append(f"     Líneas horizontales: {reguardado.get('lineas_horizontales', 0)}")
                report.append(f"     Líneas verticales: {reguardado.get('lineas_verticales', 0)}")
                report.append(f"     Densidad de líneas: {reguardado.get('densidad_lineas', 0):.3f}")
            
            # Stroke Width Transform
            swt = texto_sintetico_prof.get("swt_analisis", {})
            if swt:
                report.append(f"     Cajas de texto detectadas: {swt.get('cajas_texto_detectadas', 0)}")
                if "stroke_width_mean" in swt:
                    report.append(f"     Grosor promedio: {swt.get('stroke_width_mean', 0):.2f}px")
                    report.append(f"     Desviación estándar: {swt.get('stroke_width_std', 0):.2f}px")
                    report.append(f"     Grosor uniforme: {swt.get('stroke_width_uniforme', False)}")
            
            # Frecuencia y entropía
            freq_ent = texto_sintetico_prof.get("frecuencia_entropia_analisis", {})
            if freq_ent:
                report.append(f"     Energía alta frecuencia: {freq_ent.get('energia_promedio', 0):.1f}")
                report.append(f"     Entropía de color: {freq_ent.get('entropia_promedio', 0):.2f}")
                report.append(f"     Texto sintético: {freq_ent.get('texto_sintetico', False)}")
            
            # ELA focalizado
            ela_focal = texto_sintetico_prof.get("ela_focalizado_analisis", {})
            if ela_focal:
                report.append(f"     ELA promedio en cajas: {ela_focal.get('ela_promedio_cajas', 0):.2f}")
                report.append(f"     Texto brilla en ELA: {ela_focal.get('texto_brilla_ela', False)}")
            
            # Color y anti-alias
            color_antialias = texto_sintetico_prof.get("color_antialias_analisis", {})
            if color_antialias:
                report.append(f"     Color trazo promedio: {color_antialias.get('color_trazo_promedio', 0):.1f}")
                report.append(f"     Color casi puro: {color_antialias.get('color_casi_puro', False)}")
                report.append(f"     Gradiente estable: {color_antialias.get('gradiente_estable', False)}")
            
            # Patrones de texto (método de respaldo)
            patrones = texto_sintetico_prof.get("patrones_texto_analisis", {})
            if patrones:
                report.append(f"     Color uniforme: {patrones.get('color_uniforme', False)}")
                report.append(f"     Gradiente estable (patrones): {patrones.get('gradiente_estable', False)}")
            
            # Resultado final
            if texto_sintetico_prof.get("tiene_texto_sintetico"):
                report.append("     🚨 TEXTO SINTÉTICO APLANADO DETECTADO")
            elif texto_sintetico_prof.get("nivel_sospecha") == "ALTO":
                report.append("     ⚠️ ALTA SOSPECHA DE TEXTO SINTÉTICO")
            else:
                report.append("     ✅ Sin evidencia de texto sintético")
        
        # ELA mejorado
        ela_prof = analisis_profesional.get("ela", {})
        if ela_prof and not ela_prof.get("error"):
            report.append("   🖼️  ELA MEJORADO:")
            report.append(f"     Nivel de sospecha: {ela_prof.get('nivel_sospecha', 'N/A')}")
            report.append(f"     Porcentaje sospechoso: {ela_prof.get('porcentaje_sospechoso', 0):.1f}%")
            report.append(f"     Densidad de bordes: {ela_prof.get('edge_density', 0):.3f}")
            report.append(f"     Rectángulos detectados: {ela_prof.get('rectangulos_detectados', 0)}")
            
            patrones = ela_prof.get("patrones_edicion", [])
            if patrones:
                report.append("     Patrones de edición:")
                for patron in patrones:
                    report.append(f"       • {patron}")
        
        # Análisis de ruido y bordes avanzado
        ruido_prof = analisis_profesional.get("ruido_bordes", {})
        if ruido_prof and not ruido_prof.get("error"):
            report.append("   🔍 ANÁLISIS DE RUIDO Y BORDES AVANZADO:")
            
            ruido_analisis = ruido_prof.get("ruido_analisis", {})
            if ruido_analisis:
                report.append(f"     Varianza Laplaciano: {ruido_analisis.get('laplacian_variance', 0):.1f}")
                report.append(f"     Diferencia máxima regiones: {ruido_analisis.get('diferencia_maxima_regiones', 0):.1f}")
                inconsistencias = ruido_analisis.get("inconsistencias_ruido", "")
                if inconsistencias:
                    report.append(f"     • {inconsistencias}")
            
            halo_analisis = ruido_prof.get("halo_analisis", {})
            if halo_analisis:
                report.append(f"     Ratio de halo: {halo_analisis.get('halo_ratio', 0):.3f}")
                halo_detectado = halo_analisis.get("halo_detectado", "")
                if halo_detectado:
                    report.append(f"     • {halo_detectado}")
        
        # Análisis de hashes
        hashes_prof = analisis_profesional.get("hashes", {})
        if hashes_prof and not hashes_prof.get("error"):
            report.append("   🔐 ANÁLISIS DE HASHES FORENSES:")
            
            hashes_analisis = hashes_prof.get("hashes_analisis", {})
            if hashes_analisis:
                report.append(f"     SHA256: {hashes_analisis.get('sha256', 'N/A')[:16]}...")
                report.append(f"     pHash: {hashes_analisis.get('phash', 'N/A')}")
                report.append(f"     dHash: {hashes_analisis.get('dhash', 'N/A')}")
            
            inconsistencias = hashes_prof.get("inconsistencias", [])
            if inconsistencias:
                report.append("     Inconsistencias detectadas:")
                for inc in inconsistencias:
                    report.append(f"       • {inc}")
        
        # Resumen profesional
        grado_confianza_prof = analisis_profesional.get("grado_confianza", "N/A")
        porcentaje_confianza_prof = analisis_profesional.get("porcentaje_confianza", 0)
        evidencias_prof = analisis_profesional.get("evidencias", [])
        
        report.append("   🎯 RESUMEN PROFESIONAL:")
        report.append(f"     Grado de confianza: {grado_confianza_prof}")
        report.append(f"     Porcentaje: {porcentaje_confianza_prof:.1f}%")
        report.append(f"     Tipo de imagen: {analisis_profesional.get('tipo_imagen', 'N/A')}")
        
        if analisis_profesional.get('es_screenshot'):
            report.append("     ℹ️ Imagen clasificada como screenshot/web")
        
        if evidencias_prof:
            report.append("     Evidencias profesionales:")
            for evidencia in evidencias_prof:
                report.append(f"       • {evidencia}")
        
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
