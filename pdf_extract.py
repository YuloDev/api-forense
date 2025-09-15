import re
from typing import Dict, Tuple, Optional, Any, List

from utils import strip_accents, _to_float

# ------------------ Clave de Acceso (robusto) ------------------------
DIGITS49_FLEX = r"((?:\d[\s-]*){49})"

def _normalize_digits(block: str) -> Optional[str]:
    if not block:
        return None
    only = re.sub(r"\D", "", block)
    return only if len(only) == 49 else None

def _search_after_label(text: str, labels: List[str], window_chars: int = 2000) -> Tuple[Optional[str], bool]:
    for label_regex in labels:
        for m in re.finditer(label_regex, text, flags=re.I | re.UNICODE):
            start = m.end()
            window = text[start:start + window_chars]
            m1 = re.search(r"[:\s-]*" + DIGITS49_FLEX, window)
            if m1:
                clave = _normalize_digits(m1.group(1))
                if clave:
                    return clave, True
            m2 = re.search(r"[\r\n]+[:\s-]*" + DIGITS49_FLEX, window)
            if m2:
                clave = _normalize_digits(m2.group(1))
                if clave:
                    return clave, True
    return None, False

def extract_clave_acceso_from_text(raw_text: str) -> Tuple[Optional[str], bool]:
    if not raw_text:
        return None, False
    t = strip_accents(raw_text)
    t = re.sub(r"[ \t]+", " ", t)
    labels = [
        r"\bCLAVE\s*DE\s*ACCESO\s*DOCUMENTO\s*ELECTRONICO\b",
        r"\bCLAVE\s*ACCESO\s*DOCUMENTO\s*ELECTRONICO\b",
        r"\bCLAVE\s*DE\s*ACCESO\b",
        r"\bCLAVE\s*ACCESO\b",
    ]
    clave, found = _search_after_label(t, labels, window_chars=2000)
    if found and clave:
        return clave, True
    for m in re.finditer(r"DOCUMENTO\s*ELECTRONICO", t, flags=re.I):
        start = m.end()
        window = t[start:start + 2000]
        mnum = re.search(DIGITS49_FLEX, window)
        if mnum:
            clave = _normalize_digits(mnum.group(1))
            if clave:
                return clave, True
    return None, False

# ------------- Extracción de campos e ÍTEMS desde texto --------------
def parse_money(token: str) -> Optional[float]:
    return _to_float(token)

def norm_desc(s: str) -> str:
    s = strip_accents(s or "")
    s = re.sub(r"[^A-Za-z0-9\s\.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s

def extract_items_from_text(raw_text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not raw_text:
        return items

    text = strip_accents(raw_text)
    start_idx = re.search(r"\bDESCRIPCION\b", text, re.I)
    if start_idx:
        text = text[start_idx.start():]

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    patt1 = re.compile(
        r"^(?P<desc>.+?)\s+(?P<cant>\d+(?:[.,]\d+)?)\s+(?P<unit>\d+(?:[.,]\d+)?)\s+(?P<tot>\d+(?:[.,]\d+)?)$"
    )
    patt2 = re.compile(
        r"^(?P<desc>.+?)\s+(?P<cant>\d+(?:[.,]\d+)?)\s+.*?(?P<unit>\d+(?:[.,]\d+)?)\s+(?P<tot>\d+(?:[.,]\d+)?)$"
    )

    for ln in lines:
        if re.search(r"(DESCRIPCION|CANTIDAD|PRE\.?U|UNI|PRE\.?TOT|TOTAL|SUBTOTAL|IVA|TARIFA)", ln, re.I):
            continue
        m = patt1.match(ln) or patt2.match(ln)
        if m:
            desc = m.group("desc")
            cant = _to_float(m.group("cant"))
            unit = parse_money(m.group("unit"))
            tot = parse_money(m.group("tot"))
            if cant is not None and unit is not None and tot is not None and cant > 0 and unit >= 0 and tot >= 0:
                items.append({
                    "descripcion": desc.strip(),
                    "cantidad": cant,
                    "precioUnitario": unit,
                    "precioTotal": tot,
                })

    # Eliminar duplicados
    uniq = []
    seen = set()
    for it in items:
        key = (norm_desc(it["descripcion"]), round(it["cantidad"], 4),
               round(it["precioUnitario"], 4), round(it["precioTotal"], 4))
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    return uniq

def extract_invoice_fields_from_text(raw_text: str, clave_acceso: Optional[str]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if not raw_text:
        if clave_acceso:
            data["claveAcceso"] = clave_acceso
        data["detalles"] = []
        return data

    text = strip_accents(raw_text)

    # RUC
    m = re.search(r"\bRUC[:\s]*([0-9]{13})\b", text, re.I) or re.search(r"\b([0-9]{13})\b", text)
    if m:
        data["ruc"] = m.group(1)

    # Fecha
    m = re.search(r"fecha\s*(?:de\s*)?emision[:\s]*([0-3]?\d[/-][01]?\d[/-]\d{2,4})", text, re.I) or \
        re.search(r"\b([0-3]?\d[/-][01]?\d[/-]\d{2,4})\b", text)
    if m:
        f = m.group(1).replace("-", "/")
        parts = f.split("/")
        if len(parts[2]) == 2:
            parts[2] = "20" + parts[2]
        data["fechaEmision"] = "/".join(parts)

    # Total a pagar
    m = re.search(r"total\s*a\s*pagar[:\s]*\$?\s*([0-9]+[\.,][0-9]{2})", text, re.I) or \
        re.search(r"\bTOTAL\b[^0-9]{0,15}\$?\s*([0-9]+[\.,][0-9]{2})", text, re.I)
    if m:
        data["importeTotal"] = _to_float(m.group(1))

    # Razón Social (heurística líneas cerca de RUC)
    try:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        ruc_idx = next((i for i, l in enumerate(lines) if re.search(r"\bRUC\b", l, re.I)), None)
        if ruc_idx and ruc_idx > 0:
            block = " ".join(lines[max(0, ruc_idx - 3):ruc_idx])
            block = re.sub(r"^(DIRECCION|SUCURSAL|MATRIZ).*$", "", block, flags=re.I)
            data["razonSocial"] = " ".join(block.split())[:120]
    except Exception:
        pass

    if clave_acceso:
        data["claveAcceso"] = clave_acceso

    # Ítems
    data["detalles"] = extract_items_from_text(raw_text)

    # Total calculado por ítems (si hay)
    if data["detalles"]:
        data["totalCalculadoPorItems"] = round(sum(_to_float(i["precioTotal"]) or 0.0 for i in data["detalles"]), 2)

    return data
