"""
Motor financiero de la deuda de la tarjeta.

Une la historia REAL (estados de cuenta) con la PROYECCIÓN, y descompone cada pago en:
    capital  → lo que de verdad bajó la deuda
    interés  → interés corriente + IVA
    cargos   → mora, gestión de cobro, anualidad, seguros, comisiones, compras
    cuota FIN→ cuota de extrafinanciamiento que el banco carga a la tarjeta
Identidad que siempre se cumple:  pago = capital + interés + cargos + cuota FIN
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import pandas as pd

from helpers.estado_cuenta import proyectar, pago_para_liquidar_en, Escenario


COMPONENTES = [
    # clave,      etiqueta,                    color
    ("capital",   "Baja la deuda (capital)",   "#0A6E4E"),
    ("interes",   "Intereses + IVA",           "#A8341C"),
    ("cuota_fin", "Cuota extrafinanciamiento", "#B8862C"),
    ("cargos",    "Mora, seguros y comisiones", "#8B9893"),
]
COLOR = {k: c for k, _, c in COMPONENTES}
LABEL = {k: l for k, l, _ in COMPONENTES}


# ============ LÍNEA DE TIEMPO REAL + PROYECTADA ============

def linea_tiempo(resumen: pd.DataFrame, esc: Optional[Escenario]) -> pd.DataFrame:
    """
    Una fila por corte (pasados y futuros) con: saldo_inicial, saldo_final, pago y su descomposición.
    `tipo` = 'real' | 'proyectado'.
    """
    filas = []
    for _, r in resumen.iterrows():
        filas.append({
            "corte": pd.Timestamp(r["corte"]), "tipo": "real",
            "saldo_inicial": r["saldo_inicial"], "saldo_final": r["saldo_final"],
            "pago": r["PAGO"],
            "interes": r["INTERES"] + r["IVA"],
            "cargos": r["MORA"] + r["GESTION_COBRO"] + r["CUOTA_ANUAL"] + r["SEGURO"] + r["COMISION"] + r["COMPRA"],
            "cuota_fin": r["CUOTA_FIN"],
            "capital": r["reduccion"],
        })
    if esc is not None and not esc.tabla.empty:
        for _, r in esc.tabla.iterrows():
            filas.append({
                "corte": pd.Timestamp(r["corte"]), "tipo": "proyectado",
                "saldo_inicial": r["saldo_inicial"], "saldo_final": r["saldo_final"],
                "pago": r["pago"], "interes": r["interes"], "cargos": r["cargos"],
                "cuota_fin": r["cuota_fin"], "capital": r["a_capital"],
            })
    df = pd.DataFrame(filas)
    if df.empty:
        return df
    df["pct_capital"] = df.apply(lambda f: f["capital"] / f["pago"] if f["pago"] > 0 else None, axis=1)
    df["pct_interes"] = df.apply(lambda f: f["interes"] / f["pago"] if f["pago"] > 0 else None, axis=1)
    return df


def acumulado(df: pd.DataFrame, desde: Optional[pd.Timestamp] = None) -> dict:
    """Totales de pagos reales y su descomposición."""
    r = df[df["tipo"] == "real"]
    if desde is not None:
        r = r[r["corte"] >= desde]
    pago = float(r["pago"].sum())
    out = {"pago": pago, "n": len(r)}
    for k, _, _ in COMPONENTES:
        out[k] = float(r[k].sum())
        out["pct_" + k] = out[k] / pago if pago else 0.0
    return out


def inicio_plan_fijo(resumen: pd.DataFrame, pago_ref: float) -> Optional[pd.Timestamp]:
    """Primer corte desde el cual todos los cortes tienen un pago ≥ 40 % del pago de referencia
    (detecta cuándo empezó el pago fijo; con tus datos: corte jun-2026, pago del 30-may)."""
    if resumen.empty:
        return None
    ok = resumen["PAGO"] >= pago_ref * 0.4
    inicio = None
    for corte, v in zip(resumen["corte"], ok):
        if v and inicio is None:
            inicio = corte
        elif not v:
            inicio = None
    return pd.Timestamp(inicio) if inicio is not None else None


# ============ CUÁNTO PAGAR ============

def pago_equilibrio(saldo: float, tasa: float, cuota_fin: float, cargos_mes: float) -> float:
    """Pago con el que la deuda NI SUBE NI BAJA el próximo mes. Menos de esto → la deuda crece."""
    return round(saldo * tasa + cuota_fin + cargos_mes, 2)


@dataclass
class Meta:
    meses: int
    pago: float
    ultimo_pago: pd.Timestamp     # mes en que se hace el último pago
    intereses: float
    total: float
    ahorro_vs_actual: float
    escenario: Escenario


def tabla_metas(saldo: float, tasa: float, corte: date, cuota_fin: float, cuotas_fin_rest: Optional[int],
                cargos_mes: float, pago_actual: float, metas=(3, 4, 6, 9, 12)) -> List[Meta]:
    ref = proyectar(saldo, pago_actual, tasa, corte, cuota_fin, cuotas_fin_rest, cargos_mes)
    out = []
    for n in metas:
        p = pago_para_liquidar_en(saldo, n, tasa, corte, cuota_fin, cuotas_fin_rest, cargos_mes)
        p = _redondear_arriba(p, 50)
        e = proyectar(saldo, p, tasa, corte, cuota_fin, cuotas_fin_rest, cargos_mes)
        out.append(Meta(
            meses=e.meses, pago=p,
            ultimo_pago=pd.Timestamp(e.fecha_liquidacion) - pd.DateOffset(months=1),
            intereses=e.total_intereses, total=e.total_pagado,
            ahorro_vs_actual=(ref.total_intereses - e.total_intereses) if ref.liquidado else 0.0,
            escenario=e,
        ))
    return out


def _redondear_arriba(v: float, paso: int) -> float:
    import math
    return float(math.ceil(v / paso) * paso)


def tasa_anual_efectiva(tasa_mensual: float) -> float:
    return (1 + tasa_mensual) ** 12 - 1
