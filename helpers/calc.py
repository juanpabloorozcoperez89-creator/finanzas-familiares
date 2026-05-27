"""
Cálculos derivados: saldo proyectado, gastos hormiga, comparativos.
"""
import pandas as pd
from datetime import datetime, date
from typing import Optional


def filtrar_mes(df: pd.DataFrame, año: int, mes: int) -> pd.DataFrame:
    """Filtra transacciones de un mes específico."""
    if df.empty:
        return df
    return df[
        (df["fecha"].dt.year == año) & (df["fecha"].dt.month == mes)
    ].copy()


def resumen_mes(df: pd.DataFrame, año: int, mes: int) -> dict:
    """Calcula ingresos, egresos y diferencia del mes."""
    sub = filtrar_mes(df, año, mes)
    ingresos = sub[sub["tipo"] == "INGRESO"]["monto"].sum()
    egresos = sub[sub["tipo"] == "EGRESO"]["monto"].sum()
    return {
        "ingresos": float(ingresos),
        "egresos": float(egresos),
        "diferencia": float(ingresos - egresos),
        "n_transacciones": len(sub),
    }


def gastos_hormiga(df: pd.DataFrame, año: int, mes: int) -> pd.DataFrame:
    """Devuelve solo los gastos marcados como hormiga del mes, agrupados por categoría."""
    sub = filtrar_mes(df, año, mes)
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
    """Resumen mensual ingresos/egresos/diferencia para los últimos N meses con datos."""
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["año_mes"] = df["fecha"].dt.to_period("M")
    grouped = df.groupby(["año_mes", "tipo"])["monto"].sum().unstack(fill_value=0)
    if "INGRESO" not in grouped.columns:
        grouped["INGRESO"] = 0
    if "EGRESO" not in grouped.columns:
        grouped["EGRESO"] = 0
    grouped["diferencia"] = grouped["INGRESO"] - grouped["EGRESO"]
    grouped = grouped.reset_index()
    grouped["año_mes_str"] = grouped["año_mes"].astype(str)
    return grouped.sort_values("año_mes").tail(n_meses)


def calcular_saldo_actual_tarjeta(plan_df: pd.DataFrame, saldo_inicial: float) -> dict:
    """
    Calcula el saldo proyectado actual de la tarjeta basado en pagos reales registrados.
    Retorna saldo proyectado, mes actual del plan, pagos hechos y planeados.
    """
    if plan_df.empty:
        return {
            "saldo_actual": saldo_inicial,
            "meses_pagados": 0,
            "total_pagado": 0.0,
            "total_planeado": 0.0,
            "proximo_mes": None,
        }

    pagados = plan_df.dropna(subset=["pago_real"])
    meses_pagados = len(pagados)
    total_pagado = pagados["pago_real"].sum()
    total_planeado = plan_df["pago_planeado"].sum()

    proximo = plan_df[plan_df["pago_real"].isna()]
    proximo_mes = proximo.iloc[0].to_dict() if not proximo.empty else None

    saldo_actual = saldo_inicial - total_pagado
    if saldo_actual < 0:
        saldo_actual = 0

    return {
        "saldo_actual": float(saldo_actual),
        "meses_pagados": int(meses_pagados),
        "total_pagado": float(total_pagado),
        "total_planeado": float(total_planeado),
        "proximo_mes": proximo_mes,
    }


def mes_actual_dt() -> tuple:
    """Devuelve (año, mes) del mes en curso."""
    hoy = date.today()
    return hoy.year, hoy.month


def nombre_mes_es(mes: int) -> str:
    nombres = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    return nombres[mes - 1]
