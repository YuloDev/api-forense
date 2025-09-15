import time
import html
import unicodedata
import re

def log_step(step: str, t0: float):
    print(f"[TIMING] {step}: {time.perf_counter() - t0:.3f}s")

def normalize_comprobante_xml(x: str) -> str:
    if not isinstance(x, str):
        x = str(x or "")
    s = x.strip()
    if s.startswith("<![CDATA[") and s.endswith("]]>"):
        s = s[9:-3].strip()
    if "&lt;" in s or "&gt;" in s or "&amp;" in s:
        s = html.unescape(s)
    if s.startswith("\ufeff"):
        s = s.lstrip("\ufeff")
    return s

def strip_accents(s: str) -> str:
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')

def _to_float(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except:
        return None
