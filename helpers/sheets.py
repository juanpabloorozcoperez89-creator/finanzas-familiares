"""
Helper para operaciones con Google Sheets.
Patrón consistente con sheets_helper.py de Viáticos Argos.
"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import List, Dict, Optional, Tuple

from helpers.calc import ahora_gt
from helpers.estado_cuenta import COLS_MOV, normalizar_movs


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_TRANSACCIONES = "Transacciones"
SHEET_CATEGORIAS = "Categorias"
SHEET_PLAN = "Plan_Tarjeta"
SHEET_CONFIG = "Config"
SHEET_MOVS_TC = "Movimientos_Tarjeta"

HEADERS = {
    SHEET_TRANSACCIONES: ["fecha", "tipo", "persona", "categoria", "descripcion", "monto", "es_hormiga", "timestamp"],
    SHEET_CATEGORIAS: ["nombre", "tipo", "umbral_hormiga", "activa"],
    SHEET_PLAN: ["mes_num", "mes_label", "saldo_inicial_plan", "pago_planeado", "pago_real", "fecha_pago_real", "notas"],
    SHEET_CONFIG: ["clave", "valor"],
    SHEET_MOVS_TC: COLS_MOV + ["importado"],
}


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


def _ws(name: str, crear: bool = False):
    """Devuelve la pestaña. Si `crear` y no existe, la crea con sus encabezados."""
    sh = get_sheet()
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        if not crear:
            raise
        headers = HEADERS[name]
        ws = sh.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.update([headers], "A1", value_input_option="RAW")
        ws.freeze(rows=1)
        return ws


def _records(name: str, crear: bool = False) -> list:
    return _ws(name, crear=crear).get_all_records()


# ============ TRANSACCIONES ============

@st.cache_data(ttl=30, show_spinner=False)
def get_transacciones() -> pd.DataFrame:
    """Lee todas las transacciones como DataFrame. `fila` = número de fila real en el sheet."""
    data = _records(SHEET_TRANSACCIONES)
    if not data:
        return pd.DataFrame(columns=HEADERS[SHEET_TRANSACCIONES] + ["fila"])
    df = pd.DataFrame(data)
    df["fila"] = range(2, len(df) + 2)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", format="mixed")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    df["tipo"] = df["tipo"].astype(str).str.strip().str.upper()
    df["es_hormiga"] = df["es_hormiga"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "1", "SI"])
    for c in ("persona", "categoria", "descripcion"):
        df[c] = df[c].astype(str)
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
        ahora_gt().strftime("%Y-%m-%d %H:%M:%S"),
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    get_transacciones.clear()


def delete_transaccion(fila: int):
    """Elimina una transacción por su número de fila real en el sheet (columna `fila`)."""
    _ws(SHEET_TRANSACCIONES).delete_rows(int(fila))
    get_transacciones.clear()


# ============ CATEGORIAS ============

@st.cache_data(ttl=60, show_spinner=False)
def get_categorias() -> pd.DataFrame:
    """Lee el catálogo de categorías."""
    data = _records(SHEET_CATEGORIAS)
    if not data:
        return pd.DataFrame(columns=HEADERS[SHEET_CATEGORIAS])
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
    """Crea una nueva categoría (si ya existe con el mismo nombre, no la duplica)."""
    existentes = get_categorias()
    if not existentes.empty and nombre.strip().lower() in existentes["nombre"].str.strip().str.lower().tolist():
        raise ValueError(f"La categoría '{nombre}' ya existe.")
    ws = _ws(SHEET_CATEGORIAS)
    row = [nombre, tipo, umbral_hormiga if umbral_hormiga is not None else "", "TRUE"]
    ws.append_row(row, value_input_option="USER_ENTERED")
    get_categorias.clear()


def set_categoria_activa(nombre: str, activa: bool):
    ws = _ws(SHEET_CATEGORIAS)
    cell = ws.find(nombre, in_column=1)
    if cell:
        ws.update_cell(cell.row, 4, "TRUE" if activa else "FALSE")
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
    data = _records(SHEET_PLAN)
    if not data:
        return pd.DataFrame(columns=HEADERS[SHEET_PLAN])
    df = pd.DataFrame(data)
    for c in ("mes_num", "saldo_inicial_plan", "pago_planeado", "pago_real"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["mes_label"] = df["mes_label"].apply(_normalizar_mes_label)
    df["notas"] = df.get("notas", "").astype(str)
    return df.sort_values("mes_num").reset_index(drop=True)


_MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _normalizar_mes_label(val) -> str:
    """
    Normaliza mes_label a formato 'Mes YYYY' (ej: 'Jun 2026').
    Google Sheets a veces auto-convierte 'Jun 2026' a fecha '2026-06-01 00:00:00';
    esta función la regresa al formato original.
    """
    s = str(val).strip()
    if not s or s.lower() in ("nan", "nat", "none"):
        return ""
    if len(s) <= 12 and not s.startswith("20"):
        return s
    try:
        d = pd.to_datetime(s)
        return f"{_MESES_ES[d.month - 1]} {d.year}"
    except (ValueError, TypeError):
        return s


def update_pago_real(mes_num: int, pago_real: float, fecha_pago: str, notas: str = ""):
    """Marca el pago real de un mes del plan (una sola llamada a la API)."""
    ws = _ws(SHEET_PLAN)
    col = ws.col_values(1)
    for i, v in enumerate(col[1:], start=2):
        try:
            if int(float(v)) == int(mes_num):
                valores = [[round(float(pago_real), 2), fecha_pago, notas]]
                ws.update(valores, f"E{i}:G{i}", value_input_option="RAW")
                break
        except ValueError:
            continue
    get_plan.clear()


def replace_plan(filas: List[dict]):
    """Reescribe toda la hoja Plan_Tarjeta (encabezado + filas)."""
    ws = _ws(SHEET_PLAN)
    headers = HEADERS[SHEET_PLAN]
    values = [headers] + [[f.get(h, "") for h in headers] for f in filas]
    ws.clear()
    ws.update(values, "A1", value_input_option="RAW")
    get_plan.clear()


# ============ MOVIMIENTOS DE TARJETA (estados de cuenta) ============

@st.cache_data(ttl=60, show_spinner=False)
def get_movs_tarjeta() -> pd.DataFrame:
    """Movimientos importados de los estados de cuenta del banco."""
    try:
        data = _records(SHEET_MOVS_TC, crear=True)
    except Exception:
        return pd.DataFrame(columns=COLS_MOV)
    if not data:
        return pd.DataFrame(columns=COLS_MOV)
    df = pd.DataFrame(data)
    for c in COLS_MOV:
        if c not in df:
            df[c] = ""
    df["fecha"] = df["fecha"].replace("", None)
    df["comercio"] = df["comercio"].fillna("").astype(str)
    return normalizar_movs(df[COLS_MOV])


def add_movs_tarjeta(nuevos: pd.DataFrame) -> Tuple[int, int]:
    """
    Agrega movimientos evitando duplicados (mismo corte + doc + valor + saldo).
    Devuelve (insertados, ya_existían).
    """
    if nuevos.empty:
        return 0, 0
    actuales = get_movs_tarjeta()
    nuevos = normalizar_movs(nuevos)

    def clave(df):
        return (
            df["periodo_corte"].dt.strftime("%Y-%m-%d") + "|" + df["doc"].astype(str) + "|"
            + df["valor"].round(2).astype(str) + "|" + df["saldo"].round(2).astype(str)
        )

    ya = set(clave(actuales)) if not actuales.empty else set()
    mask = ~clave(nuevos).isin(ya)
    insertar = nuevos[mask]
    if insertar.empty:
        return 0, len(nuevos)

    stamp = ahora_gt().strftime("%Y-%m-%d %H:%M:%S")
    filas = []
    for _, r in insertar.iterrows():
        filas.append([
            r["periodo_corte"].strftime("%Y-%m-%d"),
            r["fecha"].strftime("%Y-%m-%d") if pd.notna(r["fecha"]) else "",
            r["tipo"], str(r["doc"]), r["comercio"], r["categoria"],
            round(float(r["valor"]), 2), round(float(r["saldo"]), 2), r["archivo"], stamp,
        ])
    _ws(SHEET_MOVS_TC, crear=True).append_rows(filas, value_input_option="RAW")
    get_movs_tarjeta.clear()
    return len(insertar), int((~mask).sum())


def borrar_movs_tarjeta():
    """Vacía la hoja de movimientos (deja solo encabezados)."""
    ws = _ws(SHEET_MOVS_TC, crear=True)
    ws.clear()
    ws.update([HEADERS[SHEET_MOVS_TC]], "A1", value_input_option="RAW")
    get_movs_tarjeta.clear()


# ============ CONFIG ============

@st.cache_data(ttl=120, show_spinner=False)
def get_config() -> Dict[str, object]:
    """Lee parámetros de configuración como diccionario."""
    data = _records(SHEET_CONFIG)
    out = {}
    for r in data:
        clave = str(r.get("clave", "")).strip()
        if not clave:
            continue
        val = r.get("valor", "")
        try:
            out[clave] = float(str(val).replace(",", ""))
        except (ValueError, TypeError):
            out[clave] = val
    return out


def upsert_config(valores: Dict[str, object]):
    """Crea o actualiza varias claves de Config en una sola escritura."""
    ws = _ws(SHEET_CONFIG)
    filas = ws.get_all_values()
    idx = {str(f[0]).strip(): i for i, f in enumerate(filas) if f}
    updates, nuevas = [], []
    for k, v in valores.items():
        v = "" if v is None else v
        if k in idx:
            updates.append({"range": f"B{idx[k] + 1}", "values": [[v]]})
        else:
            nuevas.append([k, v])
    if updates:
        ws.batch_update(updates, value_input_option="RAW")
    if nuevas:
        ws.append_rows(nuevas, value_input_option="RAW")
    get_config.clear()


def clear_all_caches():
    """Forza recarga de todas las cachés."""
    get_transacciones.clear()
    get_categorias.clear()
    get_plan.clear()
    get_config.clear()
    get_movs_tarjeta.clear()
