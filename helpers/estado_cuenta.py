"""
Estados de cuenta de tarjeta (Banco Industrial · "Detalle de movimientos").

Lee los PDF / XLS que descarga la Banca en Línea, clasifica cada movimiento,
reconstruye la cadena de saldos corte a corte y proyecta cuándo se liquida la deuda.

No depende de Streamlit: se puede usar desde scripts o pruebas.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional

import pandas as pd


# ============ CLASIFICACIÓN ============

# Orden importa: la primera regla que coincide gana.
_REGLAS = [
    ("INTERES",        r"INTER/DEVENGADO"),
    ("MORA",           r"INTERES MORATORIO|IVA-INT/MORATORIO"),
    ("GESTION_COBRO",  r"GESTION DE COBRO|GESTION DE$"),
    ("IVA",            r"^IVA"),
    ("CUOTA_FIN",      r"FIN/CT"),
    ("CUOTA_ANUAL",    r"CUOTA ANUAL|MEMBRESIA"),
    ("SEGURO",         r"CERO RIESGO|SEGURO|PROTECCION"),
    ("COMISION",       r"BIMOVIL|COMISION|CARGO POR|RECARGO|SOBREGIRO|EXCESO"),
]

CATEGORIAS = {
    "INTERES":       "Intereses",
    "IVA":           "IVA sobre intereses",
    "MORA":          "Interés moratorio",
    "GESTION_COBRO": "Gestión de cobro",
    "CUOTA_FIN":     "Cuota extrafinanciamiento",
    "CUOTA_ANUAL":   "Cuota anual",
    "SEGURO":        "Seguro (Cero Riesgo)",
    "COMISION":      "Comisiones",
    "COMPRA":        "Compras / consumos",
    "PAGO":          "Pagos",
}

# Cargos que son puro costo financiero (no compran nada)
COSTO_FINANCIERO = ["INTERES", "IVA", "MORA", "GESTION_COBRO", "CUOTA_ANUAL", "SEGURO", "COMISION"]
# Cargos que suman deuda pero no son "costo" del crédito revolvente
OTROS_CARGOS = ["CUOTA_FIN", "COMPRA"]


def clasificar(tipo: str, comercio: str) -> str:
    tipo = (tipo or "").upper()
    comercio = (comercio or "").upper().strip()
    if "PAGO" in tipo or "ABONO" in tipo or "CREDITO" in tipo or "NOTA C" in tipo:
        return "PAGO"
    for cat, patron in _REGLAS:
        if re.search(patron, comercio):
            return cat
    return "COMPRA"


# ============ MODELO ============

@dataclass
class Movimiento:
    fecha: Optional[date]          # None para cargos sin fecha (00/00/0000)
    tipo: str
    doc: str
    comercio: str
    valor: float                   # con signo: + aumenta deuda, − la reduce
    saldo: float
    categoria: str = ""

    def __post_init__(self):
        if not self.categoria:
            self.categoria = clasificar(self.tipo, self.comercio)


@dataclass
class EstadoCuenta:
    archivo: str
    tarjeta: str = ""
    limite: Optional[float] = None
    disponible: Optional[float] = None
    saldo_mora: Optional[float] = None
    pago_minimo: Optional[float] = None
    fecha_pago: Optional[date] = None
    fecha_corte: Optional[date] = None
    movimientos: List[Movimiento] = field(default_factory=list)
    saldo_final: Optional[float] = None
    periodo_corte: Optional[date] = None   # fecha de corte que CIERRA este periodo

    @property
    def saldo_inicial(self) -> Optional[float]:
        if not self.movimientos:
            return None
        m = self.movimientos[0]
        return round(m.saldo - m.valor, 2)


# ============ PARSEO ============

_MONTO = r"-?[\d,]+\.\d{2}"
_RE_LINEA = re.compile(
    rf"^(\d{{2}}/\d{{2}}/\d{{4}})\s+(DEBITO|CREDITO|PAGO\s+\w+|NOTA\s+\w+|[A-Z]+(?:\s[A-Z]+)?)\s+(\d{{5,}})\s*(.*?)\s*Q\.\s*({_MONTO})\s+Q\.\s*({_MONTO})\s*$"
)


def _num(s) -> Optional[float]:
    if s is None:
        return None
    s = str(s).replace("Q.", "").replace("Q", "").replace(",", "").strip()
    if not s or s.lower() == "nan":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _fecha(s) -> Optional[date]:
    s = str(s or "").strip()
    if not s or s.startswith("00/00"):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _encabezado(texto: str, ec: EstadoCuenta):
    def busca(etiqueta):
        m = re.search(etiqueta + r"\s*:?\s*(Q\.\s*" + _MONTO + r"|\d{2}/\d{2}/\d{4})", texto)
        return m.group(1) if m else None

    ec.limite = _num(busca(r"L[ÍI]MITE CR[ÉE]DITO"))
    ec.disponible = _num(busca(r"L[ÍI]MITE DISPONIBLE"))
    ec.saldo_mora = _num(busca(r"SALDO MORA"))
    ec.pago_minimo = _num(busca(r"PAGO M[ÍI]NIMO"))
    ec.fecha_pago = _fecha(busca(r"FECHA DE PAGO"))
    ec.fecha_corte = _fecha(busca(r"FECHA DE CORTE"))
    m = re.search(r"(\d{4}-X{4}-X{4}-\d{4})", texto)
    ec.tarjeta = m.group(1) if m else ""
    m = re.search(r"Saldo al final de Mes Anterior[^:]*:\s*Q\.\s*(" + _MONTO + ")", texto)
    ec.saldo_final = _num(m.group(1)) if m else None


def _firmar(movs_crudos: list) -> List[Movimiento]:
    """
    Convierte (fecha, tipo, doc, comercio, valor_abs, saldo) a movimientos con signo.
    El signo se deduce de la cadena de saldos (más confiable que el tipo).
    """
    out: List[Movimiento] = []
    saldo_prev = None
    for fecha, tipo, doc, comercio, valor, saldo in movs_crudos:
        es_pago = clasificar(tipo, comercio) == "PAGO"
        if saldo_prev is None:
            signo = -1 if es_pago else 1
        else:
            delta = round(saldo - saldo_prev, 2)
            if abs(abs(delta) - valor) < 0.015:
                signo = 1 if delta > 0 else -1
            else:
                signo = -1 if es_pago else 1
        out.append(Movimiento(fecha, tipo.strip(), doc, comercio.strip(), round(signo * valor, 2), saldo))
        saldo_prev = saldo
    return out


def parse_pdf(data: bytes, archivo: str = "") -> EstadoCuenta:
    import pdfplumber

    ec = EstadoCuenta(archivo=archivo)
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        texto = "\n".join((p.extract_text() or "") for p in pdf.pages)
    _encabezado(texto, ec)
    crudos = []
    for linea in texto.splitlines():
        m = _RE_LINEA.match(linea.strip())
        if not m:
            continue
        f, tipo, doc, comercio, valor, saldo = m.groups()
        crudos.append((_fecha(f), tipo, doc, comercio, abs(_num(valor)), _num(saldo)))
    ec.movimientos = _firmar(crudos)
    _asignar_periodo(ec)
    return ec


def parse_xls(data: bytes, archivo: str = "") -> EstadoCuenta:
    ec = EstadoCuenta(archivo=archivo)
    try:
        raw = pd.read_excel(io.BytesIO(data), header=None, dtype=str)
    except Exception:
        # Algunos bancos exportan HTML con extensión .xls
        raw = pd.read_html(io.BytesIO(data))[0].astype(str)
    raw = raw.fillna("")
    texto = "\n".join(" ".join(c for c in fila if c and c != "nan") for fila in raw.values.tolist())
    _encabezado(texto, ec)

    # Ubicar fila de encabezados de la tabla
    hdr_idx, cols = None, {}
    for i, fila in raw.iterrows():
        vals = [str(v).strip().upper() for v in fila.tolist()]
        if "FECHA" in vals and any(v.startswith("VALOR") for v in vals):
            hdr_idx = i
            for j, v in enumerate(vals):
                if v == "FECHA": cols["fecha"] = j
                elif v.startswith("TIPO"): cols["tipo"] = j
                elif v.startswith("NO. DOC"): cols["doc"] = j
                elif v.startswith("COMERCIO"): cols["comercio"] = j
                elif v.startswith("VALOR"): cols["valor"] = j
                elif v.startswith("SALDO"): cols["saldo"] = j
            break
    if hdr_idx is None:
        raise ValueError("No encontré la tabla de movimientos en el XLS.")

    crudos = []
    for _, fila in raw.iloc[hdr_idx + 1:].iterrows():
        f = str(fila.iloc[cols["fecha"]]).strip()
        if not re.match(r"\d{2}/\d{2}/\d{4}", f):
            continue
        valor = _num(fila.iloc[cols["valor"]])
        saldo = _num(fila.iloc[cols["saldo"]])
        if valor is None or saldo is None:
            continue
        crudos.append((
            _fecha(f),
            str(fila.iloc[cols.get("tipo", 0)]).strip(),
            str(fila.iloc[cols.get("doc", 0)]).strip(),
            str(fila.iloc[cols.get("comercio", 0)]).strip(),
            abs(valor), saldo,
        ))
    ec.movimientos = _firmar(crudos)
    _asignar_periodo(ec)
    return ec


def parse_archivo(data: bytes, archivo: str) -> EstadoCuenta:
    nombre = archivo.lower()
    if nombre.endswith(".pdf") or data[:4] == b"%PDF":
        return parse_pdf(data, archivo)
    if nombre.endswith((".xls", ".xlsx")):
        return parse_xls(data, archivo)
    raise ValueError(f"Formato no soportado: {archivo}")


def _asignar_periodo(ec: EstadoCuenta):
    """La fecha de corte que cierra el periodo = primer día de corte ≥ último movimiento fechado."""
    dia = ec.fecha_corte.day if ec.fecha_corte else 11
    fechas = [m.fecha for m in ec.movimientos if m.fecha]
    if not fechas:
        return
    ult = max(fechas)
    corte = _dia_en_mes(ult.year, ult.month, dia)
    if corte < ult:
        corte = _sumar_mes(corte, dia)
    ec.periodo_corte = corte


def _dia_en_mes(y: int, m: int, d: int) -> date:
    import calendar
    return date(y, m, min(d, calendar.monthrange(y, m)[1]))


def _sumar_mes(f: date, dia: int) -> date:
    y, m = (f.year + 1, 1) if f.month == 12 else (f.year, f.month + 1)
    return _dia_en_mes(y, m, dia)


# ============ TABLAS ============

COLS_MOV = ["periodo_corte", "fecha", "tipo", "doc", "comercio", "categoria", "valor", "saldo", "archivo"]


def estados_a_df(estados: Iterable[EstadoCuenta]) -> pd.DataFrame:
    filas = []
    for ec in estados:
        for m in ec.movimientos:
            filas.append({
                "periodo_corte": ec.periodo_corte,
                "fecha": m.fecha,
                "tipo": m.tipo,
                "doc": m.doc,
                "comercio": m.comercio,
                "categoria": m.categoria,
                "valor": m.valor,
                "saldo": m.saldo,
                "archivo": ec.archivo,
            })
    df = pd.DataFrame(filas, columns=COLS_MOV)
    return normalizar_movs(df)


def normalizar_movs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=COLS_MOV)
    df = df.copy()
    df["periodo_corte"] = pd.to_datetime(df["periodo_corte"], errors="coerce")
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    df["saldo"] = pd.to_numeric(df["saldo"], errors="coerce")
    df["doc"] = df["doc"].astype(str).str.zfill(7)
    df["tipo"] = df["tipo"].fillna("").astype(str)
    df["comercio"] = df["comercio"].fillna("").astype(str)
    cats = df["categoria"].fillna("").astype(str) if "categoria" in df else pd.Series("", index=df.index)
    df["categoria"] = [c if c in CATEGORIAS else clasificar(t, co)
                       for c, t, co in zip(cats, df["tipo"], df["comercio"])]
    df["_orden"] = range(len(df))
    df = df.drop_duplicates(subset=["periodo_corte", "doc", "valor", "saldo"], keep="first")
    return df.sort_values(["periodo_corte", "_orden"]).drop(columns="_orden").reset_index(drop=True)


def resumen_periodos(movs: pd.DataFrame) -> pd.DataFrame:
    """
    Una fila por corte: saldo inicial, cada tipo de cargo, pagos, saldo final y
    cuánto de lo pagado realmente bajó la deuda.
    """
    if movs.empty:
        return pd.DataFrame()
    filas = []
    for corte, g in movs.groupby("periodo_corte", sort=True):
        g = g.reset_index(drop=True)
        ini = round(g.iloc[0]["saldo"] - g.iloc[0]["valor"], 2)
        fin = round(g.iloc[-1]["saldo"], 2)
        por_cat = g.groupby("categoria")["valor"].sum()
        fila = {"corte": corte, "saldo_inicial": ini}
        for cat in CATEGORIAS:
            fila[cat] = round(float(por_cat.get(cat, 0.0)), 2)
        fila["PAGO"] = -fila["PAGO"]  # pagos en positivo
        fila["costo_financiero"] = round(sum(fila[c] for c in COSTO_FINANCIERO), 2)
        fila["cargos_totales"] = round(fila["costo_financiero"] + sum(fila[c] for c in OTROS_CARGOS), 2)
        fila["saldo_final"] = fin
        fila["reduccion"] = round(ini - fin, 2)
        fila["cuadra"] = abs(ini + fila["cargos_totales"] - fila["PAGO"] - fin) < 0.02
        fila["pct_pago_a_deuda"] = (fila["reduccion"] / fila["PAGO"]) if fila["PAGO"] else None
        fila["pct_pago_a_costo"] = (fila["costo_financiero"] / fila["PAGO"]) if fila["PAGO"] else None
        pagos = g[g["categoria"] == "PAGO"]
        fila["n_pagos"] = len(pagos)
        fila["fecha_ult_pago"] = pagos["fecha"].max() if not pagos.empty else pd.NaT
        filas.append(fila)
    res = pd.DataFrame(filas)
    # ¿Los cortes encadenan? (saldo final de uno = saldo inicial del siguiente)
    res["encadena"] = (res["saldo_inicial"] - res["saldo_final"].shift(1)).abs().fillna(0) < 0.02
    return res


# ============ TASA Y PROYECCIÓN ============

def tasa_efectiva_mensual(resumen: pd.DataFrame, ultimos: int = 4) -> Optional[float]:
    """
    Tasa mensual efectiva observada (interés + IVA) sobre el saldo inicial del corte.
    Usa los últimos N cortes sin mora para no inflarla.
    """
    if resumen.empty:
        return None
    r = resumen[(resumen["saldo_inicial"] > 0) & (resumen["INTERES"] > 0)].copy()
    if r.empty:
        return None
    r["tasa"] = (r["INTERES"] + r["IVA"]) / r["saldo_inicial"]
    return float(r.tail(ultimos)["tasa"].median())


@dataclass
class Escenario:
    pago_mensual: float
    meses: int
    liquidado: bool
    fecha_liquidacion: Optional[date]
    total_pagado: float
    total_intereses: float
    total_cuotas_fin: float
    tabla: pd.DataFrame


def proyectar(
    saldo: float,
    pago_mensual: float,
    tasa: float,
    corte_actual: date,
    cuota_fin: float = 0.0,
    cuotas_fin_restantes: Optional[int] = None,
    cargos_fijos_mes: float = 0.0,
    pagos_extra: Optional[dict] = None,
    max_meses: int = 120,
) -> Escenario:
    """
    Simula corte a corte, con la misma mecánica que muestra el banco:
      saldo_corte_siguiente = saldo + interés(tasa·saldo) − pago + cuota_fin + cargos_fijos
    `cuotas_fin_restantes=None` asume que la cuota de extrafinanciamiento sigue mientras haya deuda.
    `pagos_extra` = {n_mes: monto} para abonos extraordinarios (bono, aguinaldo...).
    """
    pagos_extra = pagos_extra or {}
    dia = corte_actual.day
    filas, s, f = [], float(saldo), corte_actual
    tot_pag = tot_int = tot_fin = 0.0
    for n in range(1, max_meses + 1):
        f = _sumar_mes(f, dia)
        interes = round(s * tasa, 2)
        fin = cuota_fin if (cuotas_fin_restantes is None or n <= cuotas_fin_restantes) else 0.0
        deuda = s + interes + fin + cargos_fijos_mes
        pago = min(pago_mensual + pagos_extra.get(n, 0.0), deuda)
        s_nuevo = round(deuda - pago, 2)
        filas.append({
            "mes": n, "corte": f, "saldo_inicial": round(s, 2), "interes": interes,
            "cuota_fin": fin, "cargos": cargos_fijos_mes, "pago": round(pago, 2),
            "a_capital": round(pago - interes - fin - cargos_fijos_mes, 2), "saldo_final": s_nuevo,
        })
        tot_pag += pago; tot_int += interes; tot_fin += fin
        s = s_nuevo
        if s <= 0.005:
            return Escenario(pago_mensual, n, True, f, round(tot_pag, 2), round(tot_int, 2),
                             round(tot_fin, 2), pd.DataFrame(filas))
        if pago <= interes + fin + cargos_fijos_mes and n > 3:
            break  # el pago no alcanza ni para los cargos: nunca se liquida
    return Escenario(pago_mensual, len(filas), False, None, round(tot_pag, 2), round(tot_int, 2),
                     round(tot_fin, 2), pd.DataFrame(filas))


def pago_para_liquidar_en(saldo, meses, tasa, corte_actual, cuota_fin=0.0, cuotas_fin_restantes=None,
                          cargos_fijos_mes=0.0) -> float:
    """Pago mensual fijo mínimo para quedar en cero en `meses` cortes (búsqueda binaria)."""
    lo, hi = 0.0, saldo * 2 + 10_000
    for _ in range(60):
        mid = (lo + hi) / 2
        e = proyectar(saldo, mid, tasa, corte_actual, cuota_fin, cuotas_fin_restantes, cargos_fijos_mes,
                      max_meses=meses)
        if e.liquidado and e.meses <= meses:
            hi = mid
        else:
            lo = mid
    return round(hi + 0.005, 2)
