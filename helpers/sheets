"""
Helper para operaciones con Google Sheets.
Patrón consistente con sheets_helper.py de Viáticos Argos.
"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_TRANSACCIONES = "Transacciones"
SHEET_CATEGORIAS = "Categorias"
SHEET_PLAN = "Plan_Tarjeta"
SHEET_CONFIG = "Config"


@st.cache_resource(show_spinner=False)
def get_client():
    """Cliente gspread autenticado vía service account."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_sheet():
    """Abre el spreadsheet por ID."""
    client = get_client()
    return client.open_by_key(st.secrets["sheets"]["sheet_id"])


def _ws(name: str):
    return get_sheet().worksheet(name)


# ============ TRANSACCIONES ============

@st.cache_data(ttl=30, show_spinner=False)
def get_transacciones() -> pd.DataFrame:
    """Lee todas las transacciones como DataFrame."""
    data = _ws(SHEET_TRANSACCIONES).get_all_records()
    if not data:
        return pd.DataFrame(columns=[
            "fecha", "tipo", "persona", "categoria",
            "descripcion", "monto", "es_hormiga", "timestamp"
        ])
    df = pd.DataFrame(data)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", dayfirst=False)
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    df["es_hormiga"] = df["es_hormiga"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "1", "SI"])
    return df


def add_transaccion(
    fecha: str,
    tipo: str,
    persona: str,
    categoria: str,
    descripcion: str,
    monto: float,
    es_hormiga: bool,
):
    """Agrega una nueva fila de transacción."""
    ws = _ws(SHEET_TRANSACCIONES)
    row = [
        fecha,
        tipo,
        persona,
        categoria,
        descripcion,
        round(float(monto), 2),
        "TRUE" if es_hormiga else "FALSE",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    get_transacciones.clear()


def delete_transaccion(row_index: int):
    """Elimina una transacción por su índice en el sheet (1-based, +1 por encabezado)."""
    ws = _ws(SHEET_TRANSACCIONES)
    ws.delete_rows(row_index + 2)
    get_transacciones.clear()


# ============ CATEGORIAS ============

@st.cache_data(ttl=60, show_spinner=False)
def get_categorias() -> pd.DataFrame:
    """Lee el catálogo de categorías."""
    data = _ws(SHEET_CATEGORIAS).get_all_records()
    if not data:
        return pd.DataFrame(columns=["nombre", "tipo", "umbral_hormiga", "activa"])
    df = pd.DataFrame(data)
    df["umbral_hormiga"] = pd.to_numeric(df["umbral_hormiga"], errors="coerce")
    df["activa"] = df["activa"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "1", "SI"])
    return df


def get_categorias_activas(tipo: Optional[str] = None) -> List[str]:
    """Devuelve nombres de categorías activas. Si tipo se pasa, filtra."""
    df = get_categorias()
    df = df[df["activa"]]
    if tipo:
        if tipo == "EGRESO":
            df = df[df["tipo"].isin(["EGRESO_FIJO", "EGRESO_VARIABLE"])]
        else:
            df = df[df["tipo"] == tipo]
    return df["nombre"].tolist()


def add_categoria(nombre: str, tipo: str, umbral_hormiga: Optional[float] = None):
    """Crea una nueva categoría."""
    ws = _ws(SHEET_CATEGORIAS)
    row = [
        nombre,
        tipo,
        umbral_hormiga if umbral_hormiga is not None else "",
        "TRUE",
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    get_categorias.clear()


def get_umbral_hormiga(categoria: str) -> Optional[float]:
    """Devuelve el umbral hormiga de una categoría (None si no aplica)."""
    df = get_categorias()
    match = df[df["nombre"] == categoria]
    if match.empty:
        return None
    val = match.iloc[0]["umbral_hormiga"]
    if pd.isna(val):
        return None
    return float(val)


# ============ PLAN TARJETA ============

@st.cache_data(ttl=30, show_spinner=False)
def get_plan() -> pd.DataFrame:
    """Lee el plan de pago de la tarjeta."""
    data = _ws(SHEET_PLAN).get_all_records()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["mes_num"] = pd.to_numeric(df["mes_num"], errors="coerce")
    df["saldo_inicial_plan"] = pd.to_numeric(df["saldo_inicial_plan"], errors="coerce")
    df["pago_planeado"] = pd.to_numeric(df["pago_planeado"], errors="coerce")
    df["pago_real"] = pd.to_numeric(df["pago_real"], errors="coerce")
    return df.sort_values("mes_num").reset_index(drop=True)


def update_pago_real(mes_num: int, pago_real: float, fecha_pago: str, notas: str = ""):
    """Marca el pago real de un mes del plan."""
    ws = _ws(SHEET_PLAN)
    records = ws.get_all_records()
    for i, row in enumerate(records, start=2):
        if int(row["mes_num"]) == mes_num:
            ws.update_cell(i, 5, round(float(pago_real), 2))
            ws.update_cell(i, 6, fecha_pago)
            if notas:
                ws.update_cell(i, 7, notas)
            break
    get_plan.clear()


# ============ CONFIG ============

@st.cache_data(ttl=120, show_spinner=False)
def get_config() -> Dict[str, float]:
    """Lee parámetros de configuración como diccionario."""
    data = _ws(SHEET_CONFIG).get_all_records()
    out = {}
    for r in data:
        try:
            out[r["clave"]] = float(r["valor"])
        except (ValueError, TypeError):
            out[r["clave"]] = r["valor"]
    return out


def clear_all_caches():
    """Forza recarga de todas las cachés."""
    get_transacciones.clear()
    get_categorias.clear()
    get_plan.clear()
    get_config.clear()
