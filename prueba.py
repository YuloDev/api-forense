# -*- coding: utf-8 -*-
"""
Validador SRI + OCR (EasyOCR) + Comparación completa (cabecera + productos)
+ Evaluación de Riesgo Heurístico cuando no se puede verificar en el SRI.
"""

import os, io, re, time, json, base64, html, math, statistics, unicodedata, sqlite3, threading
from datetime import datetime, date
from typing import Dict, Tuple, Optional, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from pdfminer.high_level import extract_text
from zeep import Client
from zeep.transports import Transport
import requests, xml.etree.ElementTree as ET
import fitz  # PyMuPDF
from PIL import Image
try:
    import easyocr
    HAS_EASYOCR = True
except Exception:
    HAS_EASYOCR = False
from difflib import SequenceMatcher
try:
    from importlib.metadata import version as pkg_version
except Exception:
    pkg_version = None

# ===================== CONFIG DINÁMICA CON SQLITE =====================
_CFG_LOCK = threading.RLock()
_CFG_DB_PATH = os.getenv("CONFIG_DB_PATH", "config.db")
_DEFAULTS = {
    "MAX_PDF_BYTES": 10 * 1024 * 1024,
    "SRI_TIMEOUT": 12.0,
    "TEXT_MIN_LEN_FOR_DOC": 50,
    "RENDER_DPI": 260,
    "EASYOCR_LANGS": ["es", "en"],
    "EASYOCR_GPU": False,
    "QTY_EPS": 0.001,
    "PRICE_EPS": 0.01,
    "TOTAL_EPS": 0.02,
    "MATCH_THRESHOLD": 0.60,
    "RISK_WEIGHTS": {
        "fecha_creacion_vs_emision": 15,
        "fecha_mod_vs_creacion": 12,
        "software_conocido": 12,
        "num_paginas": 10,
        "capas_multiples": 10,
        "consistencia_fuentes": 8,
        "dpi_uniforme": 8,
        "compresion_estandar": 6,
        "alineacion_texto": 6,
        "tamano_esperado": 6,
        "anotaciones_o_formularios": 3,
        "javascript_embebido": 2,
        "archivos_incrustados": 3,
        "firmas_pdf": -4,
        "actualizaciones_incrementales": 3,
        "cifrado_permisos_extra": 2,
    },
    "RISK_LEVELS": {"bajo": (0, 29), "medio": (30, 59), "alto": (60, 100)},
    "MAX_DIAS_CREACION_EMISION_OK": 30,
    "MAX_DIAS_MOD_VS_CREACION_OK": 10,
    "ONEPAGE_MIN_BYTES": 20000,
    "ONEPAGE_MAX_BYTES_TEXTUAL": 1200000,
    "ONEPAGE_MAX_BYTES_ESCANEADO": 3500000,
    "KNOWN_PRODUCERS": [
        "adobe","itext","apache pdfbox","libreoffice","microsoft",
        "wkhtmltopdf","reportlab","foxit","tcpdf","aspose","prince","weasyprint"
    ],
    "STD_IMAGE_FILTERS": ["DCTDecode","FlateDecode","JPXDecode","JBIG2Decode","CCITTFaxDecode","RunLengthDecode","LZWDecode"],
}

def _db():
    conn = sqlite3.connect(_CFG_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return conn

def _json_dump(val): return json.dumps(val, ensure_ascii=False)
def _json_load(txt, default=None):
    try: return json.loads(txt)
    except Exception: return default

def _load_all_from_db() -> dict:
    with _db() as c:
        rows = c.execute("SELECT key,value FROM config").fetchall()
    return {k:_json_load(v,None) for k,v in rows}

def _save_many_to_db(upd:dict):
    with _db() as c:
        c.executemany("INSERT INTO config(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      [(k,_json_dump(v)) for k,v in upd.items()])
        c.commit()

_CURRENT_CFG = {}
def _apply_globals(cfg:dict):
    global MAX_PDF_BYTES,SRI_TIMEOUT,TEXT_MIN_LEN_FOR_DOC,RENDER_DPI,EASYOCR_LANGS,EASYOCR_GPU
    global QTY_EPS,PRICE_EPS,TOTAL_EPS,MATCH_THRESHOLD,RISK_WEIGHTS,RISK_LEVELS
    global MAX_DIAS_CREACION_EMISION_OK,MAX_DIAS_MOD_VS_CREACION_OK
    global ONEPAGE_MIN_BYTES,ONEPAGE_MAX_BYTES_TEXTUAL,ONEPAGE_MAX_BYTES_ESCANEADO
    global KNOWN_PRODUCERS,STD_IMAGE_FILTERS,_reader_cache
    MAX_PDF_BYTES=int(cfg.get("MAX_PDF_BYTES",_DEFAULTS["MAX_PDF_BYTES"]))
    SRI_TIMEOUT=float(cfg.get("SRI_TIMEOUT",_DEFAULTS["SRI_TIMEOUT"]))
    TEXT_MIN_LEN_FOR_DOC=int(cfg.get("TEXT_MIN_LEN_FOR_DOC",_DEFAULTS["TEXT_MIN_LEN_FOR_DOC"]))
    RENDER_DPI=int(cfg.get("RENDER_DPI",_DEFAULTS["RENDER_DPI"]))
    langs=cfg.get("EASYOCR_LANGS",_DEFAULTS["EASYOCR_LANGS"])
    if isinstance(langs,str): langs=[s.strip() for s in langs.split(",")]
    EASYOCR_LANGS=langs; EASYOCR_GPU=bool(cfg.get("EASYOCR_GPU",False))
    QTY_EPS=float(cfg.get("QTY_EPS",_DEFAULTS["QTY_EPS"]))
    PRICE_EPS=float(cfg.get("PRICE_EPS",_DEFAULTS["PRICE_EPS"]))
    TOTAL_EPS=float(cfg.get("TOTAL_EPS",_DEFAULTS["TOTAL_EPS"]))
    MATCH_THRESHOLD=float(cfg.get("MATCH_THRESHOLD",_DEFAULTS["MATCH_THRESHOLD"]))
    RISK_WEIGHTS=dict(cfg.get("RISK_WEIGHTS",_DEFAULTS["RISK_WEIGHTS"]))
    RISK_LEVELS=dict(cfg.get("RISK_LEVELS",_DEFAULTS["RISK_LEVELS"]))
    MAX_DIAS_CREACION_EMISION_OK=int(cfg.get("MAX_DIAS_CREACION_EMISION_OK",30))
    MAX_DIAS_MOD_VS_CREACION_OK=int(cfg.get("MAX_DIAS_MOD_VS_CREACION_OK",10))
    ONEPAGE_MIN_BYTES=int(cfg.get("ONEPAGE_MIN_BYTES",20000))
    ONEPAGE_MAX_BYTES_TEXTUAL=int(cfg.get("ONEPAGE_MAX_BYTES_TEXTUAL",1200000))
    ONEPAGE_MAX_BYTES_ESCANEADO=int(cfg.get("ONEPAGE_MAX_BYTES_ESCANEADO",3500000))
    KNOWN_PRODUCERS=list(cfg.get("KNOWN_PRODUCERS",_DEFAULTS["KNOWN_PRODUCERS"]))
    STD_IMAGE_FILTERS=set(cfg.get("STD_IMAGE_FILTERS",_DEFAULTS["STD_IMAGE_FILTERS"]))
    _reader_cache=None

def load_config():
    with _CFG_LOCK:
        cfg=dict(_DEFAULTS)
        cfg.update(_load_all_from_db())
        _apply_globals(cfg)
        _CURRENT_CFG.clear(); _CURRENT_CFG.update(cfg)
def update_config(upd:dict)->dict:
    with _CFG_LOCK:
        if "EASYOCR_LANGS" in upd and isinstance(upd["EASYOCR_LANGS"],str):
            upd["EASYOCR_LANGS"]=[s.strip() for s in upd["EASYOCR_LANGS"].split(",")]
        if "RISK_WEIGHTS" in upd:
            merged=dict(_CURRENT_CFG.get("RISK_WEIGHTS",_DEFAULTS["RISK_WEIGHTS"]))
            merged.update(upd["RISK_WEIGHTS"]); upd["RISK_WEIGHTS"]=merged
        _save_many_to_db(upd); load_config(); return dict(_CURRENT_CFG)

class ConfigPatch(BaseModel):
    MAX_PDF_BYTES: Optional[int]=Field(None,ge=1024,le=100*1024*1024)
    SRI_TIMEOUT: Optional[float]=Field(None,ge=1,le=120)
    RENDER_DPI: Optional[int]=Field(None,ge=72,le=600)
    EASYOCR_LANGS: Optional[List[str]|str]=None
    EASYOCR_GPU: Optional[bool]=None
    QTY_EPS: Optional[float]=None; PRICE_EPS: Optional[float]=None; TOTAL_EPS: Optional[float]=None
    MATCH_THRESHOLD: Optional[float]=None; RISK_WEIGHTS: Optional[dict]=None
    @validator("EASYOCR_LANGS")
    def normlangs(cls,v):
        if isinstance(v,str): return [s.strip() for s in v.split(",") if s.strip()]
        return v
load_config()
# ================== FIN CONFIG DINÁMICA =====================

app=FastAPI(title="Validador SRI + OCR",version="1.51.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

@app.get("/config")
def get_config(): return dict(_CURRENT_CFG)
@app.patch("/config")
def patch_config(patch:ConfigPatch):
    updated=update_config({k:v for k,v in patch.dict(exclude_unset=True).items()})
    return {"ok":True,"config":updated}
@app.post("/config/reset")
def reset_config():
    with _db() as c: c.execute("DELETE FROM config"); c.commit()
    load_config(); return {"ok":True,"config":dict(_CURRENT_CFG)}

# ----------------- resto de tu lógica (validar_factura etc) ---------------
# (Debido al límite, omito repetir TODO tu código de extracción/riesgo; 
# simplemente inserta aquí el bloque que ya tienes.)
# Lo único que debes ajustar es en CADA return de validar_factura 
# agregar `"textoAnalizado": fuente_texto`.

# --------------------------- RUN -------------------------------------
if __name__=="__main__":
    import uvicorn
    uvicorn.run("prueba:app",host="0.0.0.0",port=8000,reload=True)
