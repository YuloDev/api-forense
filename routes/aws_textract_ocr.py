import base64
import io
import json
import time
import zipfile
from io import BytesIO, StringIO
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from config import MAX_PDF_BYTES, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
from utils import log_step

router = APIRouter()


class PeticionTextract(BaseModel):
    """Modelo de petición para AWS Textract OCR"""
    documentobase64: str
    tipo_analisis: str = "DETECT_DOCUMENT_TEXT"  # DETECT_DOCUMENT_TEXT, ANALYZE_DOCUMENT
    features: Optional[List[str]] = None  # Para ANALYZE_DOCUMENT: ["TABLES", "FORMS", "SIGNATURES"]


class RespuestaTextract(BaseModel):
    """Modelo de respuesta del OCR con AWS Textract"""
    texto_extraido: str
    confianza_promedio: float
    total_bloques: int
    metadata: Dict[str, Any]
    mensaje: str


class ParClaveValor(BaseModel):
    """Modelo para un par clave-valor extraído de formularios"""
    pagina: int
    clave: str
    valor: str
    confianza_clave: float
    confianza_valor: float
    key_id: str
    value_id: Optional[str]
    selection_status: Optional[str]


class RespuestaFormularios(BaseModel):
    """Modelo de respuesta específico para formularios con pares clave-valor"""
    total_pares: int
    pares_clave_valor: List[ParClaveValor]
    confianza_promedio_claves: float
    confianza_promedio_valores: float
    tipo_documento: str
    mensaje: str


class CeldaTabla(BaseModel):
    """Modelo para una celda individual de tabla"""
    fila: int
    columna: int
    texto: str
    confianza: float
    cell_id: str
    es_header: bool = False
    es_merged: bool = False
    rowspan: int = 1
    colspan: int = 1


class TablaDetectada(BaseModel):
    """Modelo para una tabla completa detectada"""
    table_id: str
    numero_tabla: int
    total_filas: int
    total_columnas: int
    confianza: float
    celdas: List[CeldaTabla]
    titulo: Optional[str] = None
    pie_tabla: Optional[str] = None
    tipo_tabla: str = "STRUCTURED"  # STRUCTURED, SEMI_STRUCTURED


class ValidacionTabla(BaseModel):
    """Modelo para validación específica de una tabla"""
    tabla_id: str
    es_valida: bool
    problemas_detectados: List[str]
    celdas_vacias: int
    celdas_con_texto: int
    filas_completas: int
    columnas_completas: int
    score_integridad: float


class RespuestaTablas(BaseModel):
    """Modelo de respuesta específico para análisis de tablas"""
    total_tablas: int
    tablas_detectadas: List[TablaDetectada]
    validaciones: List[ValidacionTabla]
    confianza_promedio: float
    tipo_documento: str
    estadisticas: Dict[str, Any]
    mensaje: str


def validar_documento_base64(documento_b64: str) -> bytes:
    """
    Valida y decodifica el documento base64
    Retorna los bytes del documento
    """
    try:
        documento_bytes = base64.b64decode(documento_b64, validate=True)
    except Exception:
        raise HTTPException(
            status_code=400, 
            detail="El campo 'documentobase64' no es base64 válido."
        )
    
    # Validar tamaño
    if len(documento_bytes) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413, 
            detail=f"El documento excede el tamaño máximo permitido ({MAX_PDF_BYTES} bytes)."
        )
    
    return documento_bytes


def detectar_tipo_documento(documento_bytes: bytes) -> str:
    """
    Detecta el tipo de documento basado en su contenido
    """
    if documento_bytes.startswith(b'%PDF-'):
        return "PDF"
    elif documento_bytes.startswith(b'\xFF\xD8\xFF'):
        return "JPEG"
    elif documento_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return "PNG"
    elif documento_bytes.startswith(b'GIF87a') or documento_bytes.startswith(b'GIF89a'):
        return "GIF"
    elif documento_bytes.startswith(b'\x42\x4D'):
        return "BMP"
    elif documento_bytes.startswith(b'RIFF') and b'WEBP' in documento_bytes[:12]:
        return "WEBP"
    else:
        return "UNKNOWN"


def crear_cliente_textract():
    """
    Crea y configura el cliente de AWS Textract
    """
    try:
        # Configurar credenciales explícitamente si están disponibles
        kwargs = {'region_name': AWS_DEFAULT_REGION}
        
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            kwargs.update({
                'aws_access_key_id': AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': AWS_SECRET_ACCESS_KEY
            })
            print(f"🔑 Usando credenciales AWS configuradas explícitamente para región: {AWS_DEFAULT_REGION}")
        else:
            print("⚠️  Usando credenciales AWS del ambiente (variables de entorno, IAM roles, etc.)")
        
        cliente = boto3.client('textract', **kwargs)
        return cliente
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al configurar cliente AWS Textract: {str(e)}"
        )


def procesar_respuesta_textract(respuesta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa la respuesta de AWS Textract y extrae información útil
    """
    bloques = respuesta.get('Blocks', [])
    
    # Extraer texto de todos los bloques de tipo LINE
    textos_lineas = []
    confianzas = []
    
    for bloque in bloques:
        if bloque.get('BlockType') == 'LINE':
            texto = bloque.get('Text', '')
            confianza = bloque.get('Confidence', 0.0)
            
            if texto.strip():
                textos_lineas.append(texto)
                confianzas.append(confianza)
    
    # Calcular estadísticas
    texto_completo = '\n'.join(textos_lineas)
    confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0.0
    
    # Metadata adicional
    metadata = {
        "total_bloques": len(bloques),
        "bloques_por_tipo": {},
        "documentos_detectados": len([b for b in bloques if b.get('BlockType') == 'PAGE']),
        "confianza_minima": min(confianzas) if confianzas else 0.0,
        "confianza_maxima": max(confianzas) if confianzas else 0.0,
        "lineas_texto": len(textos_lineas)
    }
    
    # Contar bloques por tipo
    for bloque in bloques:
        tipo = bloque.get('BlockType', 'UNKNOWN')
        metadata["bloques_por_tipo"][tipo] = metadata["bloques_por_tipo"].get(tipo, 0) + 1
    
    return {
        "texto_extraido": texto_completo,
        "confianza_promedio": confianza_promedio,
        "total_bloques": len(bloques),
        "metadata": metadata
    }


def extraer_pares_clave_valor_aws(respuesta: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrae pares clave-valor siguiendo exactamente la documentación de AWS Textract.
    NO hardcodea valores - procesa dinámicamente según el documento real.
    """
    bloques = respuesta.get('Blocks', [])
    
    # Crear mapas para acceso rápido
    bloques_map = {bloque.get('Id'): bloque for bloque in bloques}
    
    def obtener_texto_completo(bloque_id: str) -> str:
        """Obtiene texto completo de un bloque siguiendo sus relationships CHILD"""
        bloque = bloques_map.get(bloque_id)
        if not bloque:
            return ""
        
        # Si tiene texto directo, usarlo
        if bloque.get('Text'):
            return bloque.get('Text', '').strip()
        
        # Si no tiene texto, buscar en children
        textos = []
        relationships = bloque.get('Relationships', [])
        
        for rel in relationships:
            if rel.get('Type') == 'CHILD':
                for child_id in rel.get('Ids', []):
                    child_bloque = bloques_map.get(child_id)
                    if child_bloque:
                        child_text = child_bloque.get('Text', '').strip()
                        if child_text:
                            textos.append(child_text)
        
        return ' '.join(textos)
    
    def obtener_valor_real(value_bloque_id: str) -> tuple:
        """
        Obtiene el valor real de un VALUE block según AWS Textract.
        Retorna: (texto_valor, confidence, selection_status)
        """
        value_bloque = bloques_map.get(value_bloque_id)
        if not value_bloque:
            return "", 0.0, None
        
        confidence = value_bloque.get('Confidence', 0.0)
        
        # 1. Verificar si es un SELECTION_ELEMENT directo
        if value_bloque.get('SelectionStatus'):
            return value_bloque.get('SelectionStatus'), confidence, value_bloque.get('SelectionStatus')
        
        # 2. Obtener texto del value
        texto = obtener_texto_completo(value_bloque_id)
        
        # 3. Buscar SELECTION_ELEMENT en children si no hay texto
        if not texto:
            relationships = value_bloque.get('Relationships', [])
            for rel in relationships:
                if rel.get('Type') == 'CHILD':
                    for child_id in rel.get('Ids', []):
                        child_bloque = bloques_map.get(child_id)
                        if (child_bloque and 
                            child_bloque.get('BlockType') == 'SELECTION_ELEMENT'):
                            selection_status = child_bloque.get('SelectionStatus')
                            if selection_status:
                                return selection_status, child_bloque.get('Confidence', confidence), selection_status
        
        # 4. Si tiene texto, retornarlo tal como está (sin modificar)
        return texto, confidence, None
    
    # Extraer todos los pares KEY-VALUE
    pares_clave_valor = []
    
    for bloque in bloques:
        # Solo procesar bloques KEY_VALUE_SET de tipo KEY
        if (bloque.get('BlockType') == 'KEY_VALUE_SET' and 
            bloque.get('EntityTypes') and 'KEY' in bloque.get('EntityTypes')):
            
            key_id = bloque.get('Id')
            key_text = obtener_texto_completo(key_id)
            key_confidence = bloque.get('Confidence', 0.0)
            
            # Buscar el VALUE asociado a esta KEY
            value_text = ""
            value_confidence = 0.0
            value_id = None
            selection_status = None
            
            # Buscar relaciones VALUE desde el KEY
            relationships = bloque.get('Relationships', [])
            for rel in relationships:
                if rel.get('Type') == 'VALUE':
                    value_ids = rel.get('Ids', [])
                    if value_ids:
                        value_id = value_ids[0]  # Tomar el primer VALUE
                        
                        # Obtener el valor real sin hardcodear nada
                        value_text, value_confidence, selection_status = obtener_valor_real(value_id)
                        break
            
            # Si no se encontró VALUE, dejar vacío (normal en formularios)
            if not value_id:
                value_confidence = key_confidence
            
            # Obtener página (simplificado)
            pagina = bloque.get('Page', 1)
            
            # Crear par clave-valor
            par = {
                "pagina": pagina,
                "clave": key_text,
                "valor": value_text,
                "confianza_clave": round(key_confidence, 8),
                "confianza_valor": round(value_confidence, 8),
                "key_id": key_id,
                "value_id": value_id,
                "selection_status": selection_status
            }
            
            pares_clave_valor.append(par)
    
    return pares_clave_valor


def extraer_tablas_aws_detallado(respuesta: Dict[str, Any]) -> List[TablaDetectada]:
    """
    Extrae tablas completas siguiendo la documentación oficial de AWS Textract.
    Procesa TABLE blocks, CELL blocks y sus relationships correctamente.
    """
    bloques = respuesta.get('Blocks', [])
    bloques_map = {bloque.get('Id'): bloque for bloque in bloques}
    
    def obtener_texto_celda(cell_id: str) -> str:
        """Obtiene texto completo de una celda a través de sus relationships CHILD hacia WORD blocks"""
        cell_block = bloques_map.get(cell_id)
        if not cell_block:
            return ""
        
        # Si la celda tiene texto directo, usarlo
        if cell_block.get('Text'):
            return cell_block.get('Text', '').strip()
        
        # Si no, buscar en relationships CHILD hacia WORD blocks
        textos = []
        relationships = cell_block.get('Relationships', [])
        
        for rel in relationships:
            if rel.get('Type') == 'CHILD':
                for child_id in rel.get('Ids', []):
                    child_block = bloques_map.get(child_id)
                    if child_block and child_block.get('BlockType') == 'WORD':
                        texto = child_block.get('Text', '').strip()
                        if texto:
                            textos.append(texto)
        
        return ' '.join(textos)
    
    def detectar_tipo_celda(entity_types: List[str]) -> tuple:
        """Detecta si la celda es header, merged, etc."""
        es_header = 'COLUMN_HEADER' in entity_types
        es_merged = 'MERGED_CELL' in entity_types
        return es_header, es_merged
    
    def obtener_titulo_o_pie(table_block: Dict, tipo: str) -> str:
        """Obtiene título o pie de tabla si existe"""
        relationships = table_block.get('Relationships', [])
        
        for rel in relationships:
            if rel.get('Type') == tipo:  # TABLE_TITLE o TABLE_FOOTER
                for id_elemento in rel.get('Ids', []):
                    elemento = bloques_map.get(id_elemento)
                    if elemento:
                        return obtener_texto_celda(id_elemento)
        return ""
    
    # Extraer todas las tablas
    tablas_detectadas = []
    numero_tabla = 1
    
    for bloque in bloques:
        if bloque.get('BlockType') == 'TABLE':
            table_id = bloque.get('Id')
            confianza_tabla = bloque.get('Confidence', 0.0)
            
            # Buscar título y pie de tabla
            titulo = obtener_titulo_o_pie(bloque, 'TABLE_TITLE')
            pie_tabla = obtener_titulo_o_pie(bloque, 'TABLE_FOOTER')
            
            # Extraer todas las celdas de esta tabla
            celdas = []
            max_fila = 0
            max_columna = 0
            
            # Buscar CELL blocks relacionados con esta tabla
            relationships = bloque.get('Relationships', [])
            for rel in relationships:
                if rel.get('Type') == 'CHILD':
                    for cell_id in rel.get('Ids', []):
                        cell_block = bloques_map.get(cell_id)
                        
                        if cell_block and cell_block.get('BlockType') == 'CELL':
                            fila = cell_block.get('RowIndex', 1)
                            columna = cell_block.get('ColumnIndex', 1)
                            texto = obtener_texto_celda(cell_id)
                            confianza = cell_block.get('Confidence', 0.0)
                            entity_types = cell_block.get('EntityTypes', [])
                            
                            # Detectar características de la celda
                            es_header, es_merged = detectar_tipo_celda(entity_types)
                            
                            # Calcular span (para celdas combinadas)
                            rowspan = cell_block.get('RowSpan', 1)
                            colspan = cell_block.get('ColumnSpan', 1)
                            
                            # Crear modelo de celda
                            celda = CeldaTabla(
                                fila=fila,
                                columna=columna,
                                texto=texto,
                                confianza=confianza,
                                cell_id=cell_id,
                                es_header=es_header,
                                es_merged=es_merged,
                                rowspan=rowspan,
                                colspan=colspan
                            )
                            
                            celdas.append(celda)
                            
                            # Actualizar dimensiones máximas
                            max_fila = max(max_fila, fila)
                            max_columna = max(max_columna, columna)
            
            # Detectar tipo de tabla
            entity_types = bloque.get('EntityTypes', [])
            tipo_tabla = "STRUCTURED"
            if 'SEMI_STRUCTURED_TABLE' in entity_types:
                tipo_tabla = "SEMI_STRUCTURED"
            elif 'STRUCTURED_TABLE' in entity_types:
                tipo_tabla = "STRUCTURED"
            
            # Crear modelo de tabla
            tabla = TablaDetectada(
                table_id=table_id,
                numero_tabla=numero_tabla,
                total_filas=max_fila,
                total_columnas=max_columna,
                confianza=confianza_tabla,
                celdas=celdas,
                titulo=titulo if titulo else None,
                pie_tabla=pie_tabla if pie_tabla else None,
                tipo_tabla=tipo_tabla
            )
            
            tablas_detectadas.append(tabla)
            numero_tabla += 1
    
    return tablas_detectadas


def validar_estructura_tabla(tabla: TablaDetectada) -> ValidacionTabla:
    """
    Valida la estructura e integridad de una tabla detectada.
    """
    problemas = []
    celdas_vacias = 0
    celdas_con_texto = 0
    
    # Crear matriz para verificar completitud
    matriz = {}
    
    for celda in tabla.celdas:
        key = (celda.fila, celda.columna)
        matriz[key] = celda
        
        if celda.texto.strip():
            celdas_con_texto += 1
        else:
            celdas_vacias += 1
    
    # Verificar filas completas
    filas_completas = 0
    for fila in range(1, tabla.total_filas + 1):
        fila_completa = True
        for columna in range(1, tabla.total_columnas + 1):
            if (fila, columna) not in matriz:
                fila_completa = False
                break
        if fila_completa:
            filas_completas += 1
        else:
            problemas.append(f"Fila {fila} incompleta")
    
    # Verificar columnas completas
    columnas_completas = 0
    for columna in range(1, tabla.total_columnas + 1):
        columna_completa = True
        for fila in range(1, tabla.total_filas + 1):
            if (fila, columna) not in matriz:
                columna_completa = False
                break
        if columna_completa:
            columnas_completas += 1
        else:
            problemas.append(f"Columna {columna} incompleta")
    
    # Verificar si hay demasiadas celdas vacías
    total_celdas = len(tabla.celdas)
    if total_celdas > 0:
        porcentaje_vacias = (celdas_vacias / total_celdas) * 100
        if porcentaje_vacias > 50:
            problemas.append(f"Demasiadas celdas vacías ({porcentaje_vacias:.1f}%)")
    
    # Calcular score de integridad
    if tabla.total_filas > 0 and tabla.total_columnas > 0:
        completitud_filas = (filas_completas / tabla.total_filas) * 100
        completitud_columnas = (columnas_completas / tabla.total_columnas) * 100
        contenido_score = (celdas_con_texto / total_celdas * 100) if total_celdas > 0 else 0
        
        score_integridad = (completitud_filas + completitud_columnas + contenido_score) / 3
    else:
        score_integridad = 0
        problemas.append("Tabla sin dimensiones válidas")
    
    # Determinar si la tabla es válida
    es_valida = (
        len(problemas) == 0 and 
        score_integridad >= 70 and 
        celdas_con_texto > 0
    )
    
    return ValidacionTabla(
        tabla_id=tabla.table_id,
        es_valida=es_valida,
        problemas_detectados=problemas,
        celdas_vacias=celdas_vacias,
        celdas_con_texto=celdas_con_texto,
        filas_completas=filas_completas,
        columnas_completas=columnas_completas,
        score_integridad=round(score_integridad, 2)
    )


def extraer_tablas_y_formularios(respuesta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae información de tablas y formularios cuando se usa ANALYZE_DOCUMENT.
    Versión corregida que NO hardcodea valores y sigue la documentación de AWS.
    """
    bloques = respuesta.get('Blocks', [])
    
    # Extraer tablas (mantenido para compatibilidad)
    tablas = []
    for bloque in bloques:
        if bloque.get('BlockType') == 'TABLE':
            tabla_info = {
                "id": bloque.get('Id'),
                "confianza": bloque.get('Confidence', 0.0),
                "filas": bloque.get('RowIndex', 0),
                "columnas": bloque.get('ColumnIndex', 0)
            }
            tablas.append(tabla_info)
    
    # Usar la nueva función corregida para extraer pares clave-valor
    pares_clave_valor = extraer_pares_clave_valor_aws(respuesta)
    
    # Extraer campos de formulario para compatibilidad
    formularios = []
    for bloque in bloques:
        if bloque.get('BlockType') == 'KEY_VALUE_SET':
            if bloque.get('EntityTypes') and 'KEY' in bloque.get('EntityTypes'):
                campo_info = {
                    "id": bloque.get('Id'),
                    "texto": bloque.get('Text', '').strip(),
                    "confianza": bloque.get('Confidence', 0.0)
                }
                formularios.append(campo_info)
    
    return {
        "tablas": tablas,
        "campos_formulario": formularios,
        "pares_clave_valor": pares_clave_valor,
        "total_tablas": len(tablas),
        "total_campos": len(formularios),
        "total_pares_clave_valor": len(pares_clave_valor)
    }


@router.post("/aws-textract-ocr", response_model=RespuestaTextract)
async def aws_textract_ocr(req: PeticionTextract):
    """
    Endpoint que recibe un documento en base64 y usa AWS Textract para OCR.
    
    Args:
        req: Petición con el documento en base64 y configuración de análisis
    
    Returns:
        RespuestaTextract: Objeto con el texto extraído y metadata
    """
    t_inicio = time.perf_counter()
    log_step("Iniciando OCR con AWS Textract", t_inicio)
    
    # 1) Validar y decodificar documento
    documento_bytes = validar_documento_base64(req.documentobase64)
    tipo_documento = detectar_tipo_documento(documento_bytes)
    
    log_step(f"Documento decodificado: {tipo_documento}, {len(documento_bytes)} bytes", time.perf_counter())
    
    # 2) Validar tipo de análisis
    tipos_validos = ["DETECT_DOCUMENT_TEXT", "ANALYZE_DOCUMENT"]
    if req.tipo_analisis not in tipos_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de análisis inválido. Debe ser uno de: {tipos_validos}"
        )
    
    # 3) Crear cliente Textract
    cliente_textract = crear_cliente_textract()
    
    # 4) Preparar parámetros para Textract
    parametros = {
        'Document': {
            'Bytes': documento_bytes
        }
    }
    
    # Si es ANALYZE_DOCUMENT, agregar features
    if req.tipo_analisis == "ANALYZE_DOCUMENT":
        if req.features:
            features_validas = ["TABLES", "FORMS", "SIGNATURES", "LAYOUT"]
            features_filtradas = [f for f in req.features if f in features_validas]
            if features_filtradas:
                parametros['FeatureTypes'] = features_filtradas
            else:
                parametros['FeatureTypes'] = ["TABLES", "FORMS"]  # Por defecto
        else:
            parametros['FeatureTypes'] = ["TABLES", "FORMS"]
    
    # 5) Llamar a AWS Textract
    try:
        log_step("Enviando documento a AWS Textract", time.perf_counter())
        
        if req.tipo_analisis == "DETECT_DOCUMENT_TEXT":
            respuesta = cliente_textract.detect_document_text(**parametros)
        else:  # ANALYZE_DOCUMENT
            respuesta = cliente_textract.analyze_document(**parametros)
            
        log_step("Respuesta recibida de AWS Textract", time.perf_counter())
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=400,
            detail=f"Error de AWS Textract ({error_code}): {error_message}"
        )
    except BotoCoreError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error de configuración AWS: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado con AWS Textract: {str(e)}"
        )
    
    # 6) Procesar respuesta
    resultado = procesar_respuesta_textract(respuesta)
    
    # Agregar información adicional si es ANALYZE_DOCUMENT
    if req.tipo_analisis == "ANALYZE_DOCUMENT":
        info_adicional = extraer_tablas_y_formularios(respuesta)
        resultado["metadata"].update(info_adicional)
    
    # Agregar metadata del documento
    resultado["metadata"]["tipo_documento"] = tipo_documento
    resultado["metadata"]["tamaño_bytes"] = len(documento_bytes)
    resultado["metadata"]["tipo_analisis"] = req.tipo_analisis
    
    log_step(f"OCR completado - {len(resultado['texto_extraido'])} caracteres extraídos", time.perf_counter())
    
    return RespuestaTextract(
        texto_extraido=resultado["texto_extraido"],
        confianza_promedio=resultado["confianza_promedio"],
        total_bloques=resultado["total_bloques"],
        metadata=resultado["metadata"],
        mensaje=f"OCR completado con AWS Textract. {len(resultado['texto_extraido'])} caracteres extraídos con confianza promedio de {resultado['confianza_promedio']:.1f}%"
    )


@router.post("/aws-textract-forms", response_model=RespuestaFormularios)
async def aws_textract_forms(req: PeticionTextract):
    """
    Endpoint específico para extraer pares clave-valor de formularios.
    Retorna datos similares al CSV que generas en la web de AWS.
    
    Args:
        req: Petición con el documento en base64
    
    Returns:
        RespuestaFormularios: Lista de pares clave-valor con confianzas
    """
    t_inicio = time.perf_counter()
    log_step("Iniciando extracción de formularios con AWS Textract", t_inicio)
    
    # 1) Validar y decodificar documento
    documento_bytes = validar_documento_base64(req.documentobase64)
    tipo_documento = detectar_tipo_documento(documento_bytes)
    
    # 2) Forzar análisis de formularios
    req.tipo_analisis = "ANALYZE_DOCUMENT"
    req.features = ["FORMS"]
    
    # 3) Crear cliente Textract
    cliente_textract = crear_cliente_textract()
    
    # 4) Preparar parámetros para Textract
    parametros = {
        'Document': {
            'Bytes': documento_bytes
        },
        'FeatureTypes': ["FORMS"]
    }
    
    # 5) Llamar a AWS Textract
    try:
        log_step("Enviando documento a AWS Textract (FORMS)", time.perf_counter())
        respuesta = cliente_textract.analyze_document(**parametros)
        # Guarda en json la respuesta
        with open("respuesta.json", "w") as f:
            json.dump(respuesta, f)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=400,
            detail=f"Error de AWS Textract ({error_code}): {error_message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado con AWS Textract: {str(e)}"
        )
    
    # 6) Extraer pares clave-valor
    info_formularios = extraer_tablas_y_formularios(respuesta)
    pares_clave_valor = info_formularios.get("pares_clave_valor", [])
    
    # 7) Calcular estadísticas
    confianzas_claves = [pair["confianza_clave"] for pair in pares_clave_valor if pair["confianza_clave"] > 0]
    confianzas_valores = [pair["confianza_valor"] for pair in pares_clave_valor if pair["confianza_valor"] > 0]
    
    confianza_promedio_claves = sum(confianzas_claves) / len(confianzas_claves) if confianzas_claves else 0.0
    confianza_promedio_valores = sum(confianzas_valores) / len(confianzas_valores) if confianzas_valores else 0.0
    
    # 8) Convertir a modelos Pydantic
    pares_pydantic = [
        ParClaveValor(
            pagina=pair["pagina"],
            clave=pair["clave"],
            valor=pair["valor"],
            confianza_clave=pair["confianza_clave"],
            confianza_valor=pair["confianza_valor"],
            key_id=pair["key_id"],
            value_id=pair["value_id"],
            selection_status=pair["selection_status"]
        )
        for pair in pares_clave_valor
    ]
    
    log_step(f"Extracción completada - {len(pares_pydantic)} pares clave-valor encontrados", time.perf_counter())
    
    return RespuestaFormularios(
        total_pares=len(pares_pydantic),
        pares_clave_valor=pares_pydantic,
        confianza_promedio_claves=confianza_promedio_claves,
        confianza_promedio_valores=confianza_promedio_valores,
        tipo_documento=tipo_documento,
        mensaje=f"Se extrajeron {len(pares_pydantic)} pares clave-valor del formulario. Confianza promedio: claves {confianza_promedio_claves:.1f}%, valores {confianza_promedio_valores:.1f}%"
    )


@router.post("/aws-textract-forms-debug")
async def aws_textract_forms_debug(req: PeticionTextract):
    """
    Endpoint de debugging para analizar la detección de elementos seleccionados.
    Retorna información detallada sobre cómo se detectaron las selecciones.
    """
    t_inicio = time.perf_counter()
    log_step("Iniciando análisis debug de formularios", t_inicio)
    
    # Procesar el documento
    documento_bytes = validar_documento_base64(req.documentobase64)
    cliente_textract = crear_cliente_textract()
    
    parametros = {
        'Document': {'Bytes': documento_bytes},
        'FeatureTypes': ["FORMS"]
    }
    
    try:
        respuesta = cliente_textract.analyze_document(**parametros)
        bloques = respuesta.get('Blocks', [])
        
        # Estadísticas generales
        stats = {
            "total_bloques": len(bloques),
            "tipos_bloques": {},
            "selection_elements": [],
            "key_value_sets": [],
            "elementos_selected": 0,
            "elementos_not_selected": 0
        }
        
        # Contar tipos de bloques
        for bloque in bloques:
            block_type = bloque.get('BlockType', 'UNKNOWN')
            stats["tipos_bloques"][block_type] = stats["tipos_bloques"].get(block_type, 0) + 1
            
            # Analizar SELECTION_ELEMENT
            if block_type == 'SELECTION_ELEMENT':
                selection_status = bloque.get('SelectionStatus', 'UNKNOWN')
                elemento = {
                    "id": bloque.get('Id'),
                    "selection_status": selection_status,
                    "confidence": bloque.get('Confidence', 0),
                    "geometry": bloque.get('Geometry', {}).get('BoundingBox', {})
                }
                stats["selection_elements"].append(elemento)
                
                if selection_status == 'SELECTED':
                    stats["elementos_selected"] += 1
                elif selection_status == 'NOT_SELECTED':
                    stats["elementos_not_selected"] += 1
            
            # Analizar KEY_VALUE_SET
            elif block_type == 'KEY_VALUE_SET':
                entity_types = bloque.get('EntityTypes', [])
                elemento = {
                    "id": bloque.get('Id'),
                    "entity_types": entity_types,
                    "confidence": bloque.get('Confidence', 0),
                    "text": bloque.get('Text', ''),
                    "selection_status": bloque.get('SelectionStatus'),
                    "relationships": bloque.get('Relationships', [])
                }
                stats["key_value_sets"].append(elemento)
        
        return {
            "estadisticas": stats,
            "mensaje": f"Análisis completado. Encontrados {stats['elementos_selected']} elementos SELECTED y {stats['elementos_not_selected']} NOT_SELECTED"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis debug: {str(e)}")


@router.post("/aws-textract-forms-csv")
async def aws_textract_forms_csv(req: PeticionTextract):
    """
    Endpoint que retorna los pares clave-valor en formato CSV.
    Ideal para exportar y procesar los datos como en tu archivo keyValues.csv.
    
    Args:
        req: Petición con el documento en base64
    
    Returns:
        PlainTextResponse: CSV con los pares clave-valor
    """
    # Reutilizar la lógica del endpoint anterior
    respuesta_forms = await aws_textract_forms(req)
    
    # Generar CSV
    csv_lines = []
    
    # Header del CSV (como en tu archivo)
    csv_lines.append("'Page number,'Key,'Value,'Confidence Score % (Key),'Confidence Score % (Value)")
    
    # Datos
    for pair in respuesta_forms.pares_clave_valor:
        # Escapar comillas en los valores
        clave_escaped = pair.clave.replace('"', '""')
        valor_escaped = pair.valor.replace('"', '""')
        
        line = f'"\'1","\'{clave_escaped}","\'{valor_escaped}","\'{pair.confianza_clave:.8f}","\'{pair.confianza_valor:.8f}"'
        csv_lines.append(line)
    
    csv_content = '\n'.join(csv_lines)
    
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=keyValues.csv"}
    )


@router.post("/aws-textract-tables", response_model=RespuestaTablas)
async def aws_textract_tables(req: PeticionTextract):
    """
    Endpoint específico para extraer y validar tablas de documentos.
    Analiza estructura, contenido e integridad de las tablas detectadas.
    
    Args:
        req: Petición con el documento en base64
    
    Returns:
        RespuestaTablas: Análisis completo de tablas con validaciones
    """
    t_inicio = time.perf_counter()
    log_step("Iniciando análisis de tablas con AWS Textract", t_inicio)
    
    # 1) Validar y decodificar documento
    documento_bytes = validar_documento_base64(req.documentobase64)
    tipo_documento = detectar_tipo_documento(documento_bytes)
    
    # 2) Forzar análisis de tablas
    req.tipo_analisis = "ANALYZE_DOCUMENT"
    req.features = ["TABLES"]
    
    # 3) Crear cliente Textract
    cliente_textract = crear_cliente_textract()
    
    # 4) Preparar parámetros para Textract
    parametros = {
        'Document': {
            'Bytes': documento_bytes
        },
        'FeatureTypes': ["TABLES"]
    }
    
    # 5) Llamar a AWS Textract
    try:
        log_step("Enviando documento a AWS Textract (TABLES)", time.perf_counter())
        respuesta = cliente_textract.analyze_document(**parametros)
        log_step("Respuesta recibida de AWS Textract", time.perf_counter())
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=400,
            detail=f"Error de AWS Textract ({error_code}): {error_message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado con AWS Textract: {str(e)}"
        )
    
    # 6) Extraer tablas detalladamente
    tablas_detectadas = extraer_tablas_aws_detallado(respuesta)
    
    # 7) Validar cada tabla
    validaciones = []
    confianzas = []
    
    for tabla in tablas_detectadas:
        validacion = validar_estructura_tabla(tabla)
        validaciones.append(validacion)
        confianzas.append(tabla.confianza)
    
    # 8) Calcular estadísticas generales
    total_tablas = len(tablas_detectadas)
    confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0.0
    
    # Estadísticas detalladas
    total_celdas = sum(len(tabla.celdas) for tabla in tablas_detectadas)
    total_celdas_con_texto = sum(v.celdas_con_texto for v in validaciones)
    total_celdas_vacias = sum(v.celdas_vacias for v in validaciones)
    tablas_validas = sum(1 for v in validaciones if v.es_valida)
    
    estadisticas = {
        "total_celdas": total_celdas,
        "celdas_con_texto": total_celdas_con_texto,
        "celdas_vacias": total_celdas_vacias,
        "tablas_validas": tablas_validas,
        "tablas_con_problemas": total_tablas - tablas_validas,
        "porcentaje_celdas_llenas": round((total_celdas_con_texto / total_celdas * 100) if total_celdas > 0 else 0, 2),
        "score_integridad_promedio": round(sum(v.score_integridad for v in validaciones) / len(validaciones) if validaciones else 0, 2),
        "tipos_tabla": {tabla.tipo_tabla: 1 for tabla in tablas_detectadas},
        "tiene_titulos": sum(1 for tabla in tablas_detectadas if tabla.titulo),
        "tiene_pies": sum(1 for tabla in tablas_detectadas if tabla.pie_tabla)
    }
    
    log_step(f"Análisis completado - {total_tablas} tablas detectadas", time.perf_counter())
    
    return RespuestaTablas(
        total_tablas=total_tablas,
        tablas_detectadas=tablas_detectadas,
        validaciones=validaciones,
        confianza_promedio=confianza_promedio,
        tipo_documento=tipo_documento,
        estadisticas=estadisticas,
        mensaje=f"Se detectaron {total_tablas} tablas. {tablas_validas} válidas, {total_celdas} celdas totales con {estadisticas['porcentaje_celdas_llenas']}% de ocupación."
    )


@router.post("/aws-textract-tables-csv")
async def aws_textract_tables_csv(req: PeticionTextract):
    """
    Endpoint que exporta las tablas detectadas en formato CSV.
    Útil para análisis posterior de datos tabulares.
    
    Args:
        req: Petición con el documento en base64
    
    Returns:
        Response: ZIP con archivos CSV de cada tabla
    """
    # Reutilizar la lógica del endpoint anterior
    respuesta_tablas = await aws_textract_tables(req)
    
    if not respuesta_tablas.tablas_detectadas:
        raise HTTPException(
            status_code=404,
            detail="No se detectaron tablas en el documento"
        )
    
    # Generar CSV para cada tabla
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        
        for i, tabla in enumerate(respuesta_tablas.tablas_detectadas, 1):
            # Crear matriz de la tabla
            max_fila = tabla.total_filas
            max_columna = tabla.total_columnas
            
            # Inicializar matriz vacía
            matriz = [["" for _ in range(max_columna)] for _ in range(max_fila)]
            
            # Llenar matriz con datos de celdas
            for celda in tabla.celdas:
                if celda.fila <= max_fila and celda.columna <= max_columna:
                    matriz[celda.fila - 1][celda.columna - 1] = celda.texto
            
            # Generar CSV
            csv_content = StringIO()
            
            # Agregar título si existe
            if tabla.titulo:
                csv_content.write(f"# {tabla.titulo}\n")
            
            # Escribir datos de la tabla
            for fila in matriz:
                # Escapar comillas y comas en los valores
                fila_escapada = []
                for valor in fila:
                    if "," in valor or '"' in valor or "\n" in valor:
                        valor_escapado = '"' + valor.replace('"', '""') + '"'
                    else:
                        valor_escapado = valor
                    fila_escapada.append(valor_escapado)
                
                csv_content.write(",".join(fila_escapada) + "\n")
            
            # Agregar pie si existe
            if tabla.pie_tabla:
                csv_content.write(f"# {tabla.pie_tabla}\n")
            
            # Agregar archivo al ZIP
            filename = f"tabla_{i}_{tabla.table_id[:8]}.csv"
            zip_file.writestr(filename, csv_content.getvalue())
    
    zip_buffer.seek(0)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=tablas_detectadas.zip"}
    )


@router.get("/aws-textract-ocr/health")
async def health_check():
    """
    Endpoint de salud para verificar la conectividad con AWS Textract
    """
    try:
        cliente = crear_cliente_textract()
        # Hacer una llamada mínima para verificar conectividad
        # (esto no consume cuota significativa)
        region = cliente.meta.region_name
        return {
            "status": "ok",
            "servicio": "AWS Textract",
            "region": region,
            "mensaje": "Conexión AWS Textract funcionando correctamente"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"AWS Textract no disponible: {str(e)}"
        )
