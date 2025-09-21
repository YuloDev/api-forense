def decision_texto_aplanado_ruido(
    analisis_forense: dict,
    rois_montos_fechas: list = None,
    policy: str = "balanced",
    contexto: dict = None
) -> dict:
    """
    Regla PRIORITARIA: Texto sintético aplanado + Ruido/Bordes + Localización.
    - policy: 'strict' (menos sensibles), 'balanced', 'lenient' (más sensibles)
    - contexto: {'is_screenshot': bool, 'is_whatsapp_like': bool, 'dpi': int, 'ancho': int, 'alto': int}
    """

    # ---------- helpers ----------
    def _p(v, d=0.0):
        try:
            return float(v)
        except Exception:
            return d

    af  = analisis_forense or {}
    afp = af.get("analisis_forense_profesional", {}) or {}

    # ---------- Texto sintético ----------
    ts = afp.get("texto_sintetico", {}) or {}
    tiene_texto_sint = bool(ts.get("tiene_texto_sintetico"))
    n_cajas = int(ts.get("cajas_texto_detectadas", 0) or 0)
    sw_mean = _p(ts.get("stroke_width_mean"), 0.0)
    sw_std  = _p(ts.get("stroke_width_std"), 0.0)
    color_casi_puro = bool(ts.get("color_casi_puro", False))
    sw_cv = (sw_std / sw_mean) if sw_mean > 1e-6 else 999.0

    # ---------- Ruido/Bordes ----------
    rb = af.get("ruido_bordes", {}) or {}
    halo_ratio    = _p(rb.get("halo_ratio"), 0.0)
    outlier_ratio = _p(rb.get("outlier_ratio"), 0.0)
    edge_density  = _p(rb.get("edge_density"), 0.0)

    # ---------- Localización / cuadrícula ----------
    grid = afp.get("cuadricula_jpeg", {}) or {}
    loc  = grid.get("localizacion_analisis", {}) or {}
    es_localizado = bool(loc.get("es_localizado", False))
    dens_bordes_sospechosos = _p(loc.get("densidad_bordes_sospechosos"), 0.0)
    bordes_agrupados = bool(loc.get("bordes_agrupados", False))

    # ---------- ELA ----------
    ela_basic = af.get("ela", {}) or {}
    ela_prof  = afp.get("ela", {}) or {}
    ela_pct_global = _p(ela_basic.get("porcentaje_sospechoso"), 0.0)
    ela_pct_reg    = _p(afp.get("ela_focalizado_analisis", {}).get("ela_promedio_cajas"), 0.0)

    # ---------- Policy tuning ----------
    policy = (policy or "balanced").lower()
    if policy == "strict":
        TH_BOXES, TH_SW_CV, TH_HALO, TH_OUTLIER, TH_DENSLOC, TH_ELA_REG = 40, 0.45, 0.50, 0.07, 0.15, 10.0
    elif policy == "lenient":
        TH_BOXES, TH_SW_CV, TH_HALO, TH_OUTLIER, TH_DENSLOC, TH_ELA_REG = 25, 0.65, 0.42, 0.04, 0.10, 7.0
    else:  # balanced
        TH_BOXES, TH_SW_CV, TH_HALO, TH_OUTLIER, TH_DENSLOC, TH_ELA_REG = 30, 0.55, 0.45, 0.05, 0.12, 8.0

    # ---------- Context-aware (reduce sensibilidad donde hay muchos falsos +) ----------
    ctx = contexto or {}
    if ctx.get("is_screenshot") or ctx.get("is_whatsapp_like"):
        # screenshots y WhatsApp generan halos y doble compresión por naturaleza
        TH_HALO += 0.03
        TH_OUTLIER += 0.01
        TH_DENSLOC += 0.02

    # baja resolución: bordes/ruido y ELA se vuelven menos confiables
    dpi = int(ctx.get("dpi", 0) or 0)
    if 0 < dpi < 120:
        TH_HALO += 0.02
        TH_ELA_REG += 2.0

    # ---------- Condiciones ----------
    cond_texto = (
        tiene_texto_sint or
        (n_cajas >= TH_BOXES and sw_cv <= TH_SW_CV) or
        (n_cajas >= TH_BOXES and color_casi_puro)
    )

    cond_ruido = (halo_ratio >= TH_HALO and outlier_ratio > TH_OUTLIER)

    cond_loc = (es_localizado or bordes_agrupados or dens_bordes_sospechosos >= TH_DENSLOC)

    cond_ela_apoyo = (ela_pct_reg >= TH_ELA_REG)
    pista_ela_global = (ela_pct_global >= 8.0)

    # ROIs (refuerzo si tu upstream ya detectó montos/fechas y pasó hits)
    toca_montos_fechas = bool(rois_montos_fechas)

    # ---------- Scoring ----------
    razones, flags = [], {}
    score = 0

    if cond_texto:
        score += 25
        razones.append(f"Texto sintético: cajas={n_cajas}, sw_cv={sw_cv:.2f}, color_puro={color_casi_puro}")
    flags["cond_texto"] = cond_texto

    if cond_ruido:
        score += 25
        razones.append(f"Ruido/bordes: halo={halo_ratio:.2f}, outliers={outlier_ratio:.2%}")
    flags["cond_ruido"] = cond_ruido

    if cond_loc:
        score += 20
        razones.append(f"Localización: es_localizado={es_localizado or bordes_agrupados}, dens_sosp={dens_bordes_sospechosos:.3f}")
    flags["cond_loc"] = cond_loc

    if cond_ela_apoyo:
        score += 10
        razones.append(f"ELA focalizado alto: {ela_pct_reg:.2f}%")
    elif pista_ela_global:
        score += 4
        razones.append(f"ELA global elevado: {ela_pct_global:.2f}%")
    flags["cond_ela"] = cond_ela_apoyo or pista_ela_global

    if toca_montos_fechas:
        score += 10
        razones.append("Refuerzo: coincide con zona de montos/fechas")
    flags["toca_montos_fechas"] = toca_montos_fechas

    score = max(0, min(score, 100))

    # PRIORITARIO si Texto + Ruido + Localización
    match_prioritario = (cond_texto and cond_ruido and cond_loc)

    if score >= 70 or match_prioritario:
        nivel, match = "PRIORITARIO", True
    elif score >= 45:
        nivel, match = "MEDIO", False
    else:
        nivel, match = "BAJO", False

    return {
        "match": match,
        "nivel": nivel,
        "match_prioritario": match_prioritario,
        "score": score,
        "razones": razones,
        "flags": flags,
        "metricas": {
            "n_cajas": n_cajas,
            "sw_cv": sw_cv,
            "halo_ratio": halo_ratio,
            "outlier_ratio": outlier_ratio,
            "edge_density": edge_density,
            "densidad_bordes_sospechosos": dens_bordes_sospechosos,
            "bordes_agrupados": bordes_agrupados,
            "es_localizado": es_localizado,
            "ela_pct_reg": ela_pct_reg,
            "ela_pct_global": ela_pct_global
        },
        "umbrales": {
            "TH_BOXES": TH_BOXES,
            "TH_SW_CV": TH_SW_CV,
            "TH_HALO": TH_HALO,
            "TH_OUTLIER": TH_OUTLIER,
            "TH_DENSLOC": TH_DENSLOC,
            "TH_ELA_REG": TH_ELA_REG,
            "policy": policy
        }
    }
