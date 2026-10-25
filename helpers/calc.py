"""
Cálculos derivados: saldo real de la tarjeta, proyecciones, gastos hormiga, comparativos.
"""
import re
from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

from helpers.estado_cuenta import (
    resumen_periodos, tasa_efectiva_mensual, proyectar, Escenario,
)

TZ = ZoneInfo("America/Guatemala")


# ============ FECHAS (zona horaria de Guatemala, no la del servidor) ============

def ahora_gt() -> datetime:
    return datetime.now(TZ)


def hoy_gt() -> date:
    return ahora_gt().date()


def mes_actual_dt() -> tuple:
    """Devuelve (año, mes) del mes en curso en Guatemala."""
    hoy = hoy_gt()
    return hoy.year, hoy.month


def saludo() -> str:
    h = ahora_gt().hour
    return "Buenos días" if h < 12 else "Buenas tardes" if h < 19 else "Buenas noches"


_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def nombre_mes_es(mes: int) -> str:
    return _MESES[mes - 1]


def mes_corto(f) -> str:
    if f is None or pd.isna(f):
        return "—"
    return f"{_MESES[f.month - 1][:3]} {f.year}"


def fecha_larga(f) -> str:
    if f is None or pd.isna(f):
        return "—"
    return f"{f.day} {_MESES[f.month - 1][:3].lower()} {f.year}"


# ============ TRANSACCIONES ============

def filtrar_mes(df: pd.DataFrame, año: int, mes: int) -> pd.DataFrame:
    """Filtra transacciones de un mes específico."""
    if df.empty:
        return df
    return df[(df["fecha"].dt.year == año) & (df["fecha"].dt.month == mes)].copy()


def resumen_mes(df: pd.DataFrame, año: int, mes: int) -> dict:
    """Calcula ingresos, egresos y diferencia del mes."""
    sub = filtrar_mes(df, año, mes)
    if sub.empty:
        return {"ingresos": 0.0, "egresos": 0.0, "diferencia": 0.0, "n_transacciones": 0}
    ingresos = sub[sub["tipo"] == "INGRESO"]["monto"].sum()
    egresos = sub[sub["tipo"] == "EGRESO"]["monto"].sum()
    return {
        "ingresos": float(ingresos),
        "egresos": float(egresos),
        "diferencia": float(ingresos - egresos),
        "n_transacciones": len(sub),
    }


def gastos_hormiga(df: pd.DataFrame, año: int, mes: int) -> pd.DataFrame:
    """Gastos marcados como hormiga del mes, agrupados por categoría."""
    sub = filtrar_mes(df, año, mes)
    if sub.empty:
        return pd.DataFrame(columns=["categoria", "total", "conteo", "promedio"])
    sub = sub[(sub["tipo"] == "EGRESO") & (sub["es_hormiga"])]
    if sub.empty:
        return pd.DataFrame(columns=["categoria", "total", "conteo", "promedio"])
    return (
        sub.groupby("categoria")
        .agg(total=("monto", "sum"), conteo=("monto", "count"), promedio=("monto", "mean"))
        .reset_index()
        .sort_values("total", ascending=False)
    )


def egresos_por_categoria(df: pd.DataFrame, año: int, mes: int) -> pd.DataFrame:
    """Egresos totales del mes agrupados por categoría."""
    sub = filtrar_mes(df, año, mes)
    if sub.empty:
        return pd.DataFrame(columns=["categoria", "total", "conteo"])
    sub = sub[sub["tipo"] == "EGRESO"]
    if sub.empty:
        return pd.DataFrame(columns=["categoria", "total", "conteo"])
    return (
        sub.groupby("categoria")
        .agg(total=("monto", "sum"), conteo=("monto", "count"))
        .reset_index()
        .sort_values("total", ascending=False)
    )


def historico_mensual(df: pd.DataFrame, n_meses: int = 6) -> pd.DataFrame:
    """Resumen mensual ingresos/egresos/diferencia de los últimos N meses (incluye meses vacíos)."""
    if df.empty or df["fecha"].isna().all():
        return pd.DataFrame()
    df = df.dropna(subset=["fecha"]).copy()
    df["año_mes"] = df["fecha"].dt.to_period("M")
    grouped = df.groupby(["año_mes", "tipo"])["monto"].sum().unstack(fill_value=0)
    for c in ("INGRESO", "EGRESO"):
        if c not in grouped.columns:
            grouped[c] = 0.0
    rango = pd.period_range(grouped.index.min(), grouped.index.max(), freq="M")
    grouped = grouped.reindex(rango, fill_value=0.0)
    grouped.index.name = "año_mes"
    grouped["diferencia"] = grouped["INGRESO"] - grouped["EGRESO"]
    grouped = grouped.reset_index()
    grouped["año_mes_str"] = grouped["año_mes"].apply(lambda p: mes_corto(p.to_timestamp()))
    return grouped.sort_values("año_mes").tail(n_meses)


# ============ TARJETA: PLAN (hoja Plan_Tarjeta) ============

def calcular_saldo_actual_tarjeta(plan_df: pd.DataFrame, saldo_inicial: float) -> dict:
    """
    Progreso del PLAN (lo que se planeó pagar). OJO: no es el saldo del banco;
    el saldo real sale de `situacion_tarjeta()` con los estados de cuenta.
    """
    if plan_df.empty:
        return {"saldo_actual": saldo_inicial, "meses_pagados": 0, "total_pagado": 0.0,
                "total_planeado": 0.0, "proximo_mes": None}
    pagados = plan_df.dropna(subset=["pago_real"])
    proximo = plan_df[plan_df["pago_real"].isna()]
    proximo_mes = proximo.iloc[0].to_dict() if not proximo.empty else None
    saldo_actual = float(proximo_mes["saldo_inicial_plan"]) if proximo_mes is not None else 0.0
    return {
        "saldo_actual": saldo_actual,
        "meses_pagados": int(len(pagados)),
        "total_pagado": float(pagados["pago_real"].sum()),
        "total_planeado": float(plan_df["pago_planeado"].sum()),
        "proximo_mes": proximo_mes,
    }


# ============ TARJETA: SITUACIÓN REAL (estados de cuenta) ============

_RE_FIN = re.compile(r"FIN/CT\s+\d+\s+(\d+)\s+(\d+)")


def _num(config: dict, clave: str, default=None):
    v = config.get(clave, default)
    try:
        if v is None or (isinstance(v, str) and not v.strip()):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _fecha_cfg(config: dict, clave: str) -> Optional[date]:
    v = config.get(clave)
    if not v:
        return None
    try:
        return pd.to_datetime(str(v), dayfirst=False).date()
    except (ValueError, TypeError):
        return None


def info_cuotas_fin(movs: pd.DataFrame) -> list:
    """
    Planes de extrafinanciamiento (FIN/CT) vistos en el último corte:
    [{plan, cuota_num, monto}]. 'FIN/CT 0013 000002 27' → plan 000002, cuota #27.
    """
    if movs.empty:
        return []
    ult = movs[movs["periodo_corte"] == movs["periodo_corte"].max()]
    out = []
    for _, r in ult[ult["categoria"] == "CUOTA_FIN"].iterrows():
        m = _RE_FIN.search(r["comercio"])
        out.append({
            "plan": m.group(1) if m else "?",
            "cuota_num": int(m.group(2)) if m else None,
            "monto": float(r["valor"]),
        })
    return out


def cargos_recurrentes(movs: pd.DataFrame, categorias=("SEGURO", "COMISION")) -> dict:
    """Seguros/comisiones del último corte y si se repiten en los cortes anteriores."""
    if movs.empty:
        return {}
    cortes = sorted(movs["periodo_corte"].dropna().unique())
    ult = cortes[-1]
    previos = cortes[-4:-1]
    out = {}
    for _, r in movs[(movs["periodo_corte"] == ult) & (movs["categoria"].isin(categorias))].iterrows():
        veces = int(((movs["periodo_corte"].isin(previos)) & (movs["comercio"] == r["comercio"])).sum())
        out[r["comercio"]] = {"monto": float(r["valor"]), "categoria": r["categoria"],
                              "recurrente": veces >= 1, "es_nuevo": veces == 0}
    return out


def situacion_tarjeta(movs: pd.DataFrame, config: dict, pago_mensual: Optional[float] = None,
                      incluir_cargos_nuevos: Optional[bool] = None,
                      cuotas_fin_restantes: Optional[int] = None) -> dict:
    """
    Todo lo que el dashboard y el plan necesitan saber de la tarjeta, calculado con
    los estados de cuenta reales. Si no hay estados importados, `hay_datos=False`.
    """
    pago = pago_mensual if pago_mensual is not None else _num(config, "pago_mensual_tarjeta", 5500.0)
    out = {"hay_datos": False, "pago_mensual": pago}
    if movs is None or movs.empty:
        return out

    res = resumen_periodos(movs)
    ult = res.iloc[-1]
    corte = ult["corte"].date()
    tasa = _num(config, "tasa_mensual_override") or tasa_efectiva_mensual(res) or _num(config, "tasa_mensual", 0.0396)

    fin = info_cuotas_fin(movs)
    cuota_fin = sum(f["monto"] for f in fin)
    if cuotas_fin_restantes is None:
        total_cuotas = _num(config, "tc_fin_total_cuotas")
        if total_cuotas and fin and fin[0]["cuota_num"]:
            cuotas_fin_restantes = max(0, int(total_cuotas) - max(f["cuota_num"] for f in fin))

    recurrentes = cargos_recurrentes(movs)
    if incluir_cargos_nuevos is None:
        cargos_mes = sum(v["monto"] for v in recurrentes.values() if v["recurrente"])
    else:
        cargos_mes = sum(v["monto"] for v in recurrentes.values() if v["recurrente"] or incluir_cargos_nuevos)

    esc: Escenario = proyectar(
        saldo=float(ult["saldo_final"]), pago_mensual=pago, tasa=tasa, corte_actual=corte,
        cuota_fin=cuota_fin, cuotas_fin_restantes=cuotas_fin_restantes, cargos_fijos_mes=cargos_mes,
    )

    limite = _num(config, "tc_limite")
    pico = float(res["saldo_inicial"].max())
    out.update({
        "hay_datos": True,
        "resumen": res,
        "saldo": float(ult["saldo_final"]),
        "corte": corte,
        "primer_corte": res.iloc[0]["corte"].date(),
        "saldo_inicio_historial": float(res.iloc[0]["saldo_inicial"]),
        "pico": pico,
        "limite": limite,
        "disponible": _num(config, "tc_disponible"),
        "pago_minimo": _num(config, "tc_pago_minimo"),
        "fecha_pago": _fecha_cfg(config, "tc_fecha_pago"),
        "saldo_mora": _num(config, "tc_saldo_mora", 0.0),
        "tasa": tasa,
        "cuota_fin": cuota_fin,
        "cuotas_fin": fin,
        "cuotas_fin_restantes": cuotas_fin_restantes,
        "cargos_recurrentes": recurrentes,
        "cargos_mes_proyectados": cargos_mes,
        "proyeccion": esc,
        "avance": (pico - float(ult["saldo_final"])) / pico if pico else 0.0,
        "ultimo": ult.to_dict(),
    })
    return out


def hallazgos(sit: dict) -> list:
    """Diagnóstico automático en lenguaje claro: [(kind, título, detalle), ...]."""
    if not sit.get("hay_datos"):
        return []
    from helpers.theme import fmt_q
    res: pd.DataFrame = sit["resumen"]
    out = []

    if (sit.get("saldo_mora") or 0) > 0:
        out.append(("danger", f"Tenés saldo en mora: {fmt_q(sit['saldo_mora'])}",
                    "Pagalo antes de la fecha de pago. Cada mes en mora el banco cobra interés moratorio "
                    "y Q168 de gestión de cobro (Q150 + IVA)."))

    lim = sit.get("limite")
    if lim and sit["saldo"] > lim:
        out.append(("danger", "Saldo arriba del límite de crédito",
                    f"Debés {fmt_q(sit['saldo'])} con límite de {fmt_q(lim)}."))

    tot_pag = res["PAGO"].sum()
    tot_costo = res["costo_financiero"].sum()
    tot_fin = res["CUOTA_FIN"].sum()
    tot_red = res["reduccion"].sum()
    if tot_pag > 0:
        out.append(("warn", f"De {fmt_q(tot_pag)} pagados, solo {fmt_q(tot_red)} bajaron la deuda",
                    f"{fmt_q(tot_costo)} se fueron en intereses, IVA, mora, gestión, anualidad y seguros "
                    f"({tot_costo / tot_pag:.0%}) y {fmt_q(tot_fin)} en cuotas de extrafinanciamiento "
                    f"({tot_fin / tot_pag:.0%})."))

    sube = res[res["reduccion"] < 0]
    if not sube.empty:
        meses = ", ".join(mes_corto(c) for c in sube["corte"])
        out.append(("warn", f"La deuda subió en {len(sube)} corte(s): {meses}",
                    "Esos meses lo pagado no alcanzó ni para cubrir intereses y cuotas."))

    gest = res[res["GESTION_COBRO"] > 0]
    if not gest.empty:
        out.append(("warn", f"Gestión de cobro en {len(gest)} cortes: {fmt_q(gest['GESTION_COBRO'].sum())}",
                    "Se cobra cuando el pago no llega a tiempo. Pagar antes del día de pago lo elimina."))

    mora = res[res["MORA"] > 0]
    if not mora.empty:
        out.append(("warn", f"Interés moratorio en {len(mora)} cortes: {fmt_q(mora['MORA'].sum())}",
                    "Aparece cuando el pago cae después de la fecha límite."))

    for nombre, info in sit.get("cargos_recurrentes", {}).items():
        if info["es_nuevo"]:
            out.append(("info", f"Cargo nuevo: {nombre} · {fmt_q(info['monto'])}",
                        "Apareció por primera vez en el último corte. Si se repite cada mes, suma a la deuda; "
                        "confirmá con el banco si podés cancelarlo."))

    out.append(("info", f"Tasa efectiva observada: {sit['tasa']:.2%} mensual (≈ {sit['tasa'] * 12:.1%} anual)",
                "Calculada como (interés + IVA) ÷ saldo inicial de cada corte; mediana de los últimos 4."))
    return out
