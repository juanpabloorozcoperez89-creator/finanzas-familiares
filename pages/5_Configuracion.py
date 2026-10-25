"""
Configuración: categorías, parámetros editables y mantenimiento.
"""
import streamlit as st
import pandas as pd

from helpers.sheets import (
    get_categorias, add_categoria, set_categoria_activa, get_config, upsert_config, clear_all_caches
)
from helpers.calc import fecha_larga
from helpers.theme import apply_theme, hero, fmt_q, COLORS, render_html, section, spacer, esc


st.set_page_config(
    page_title="Configuración · Finanzas",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="auto",
)
apply_theme()


hero(
    eyebrow="⚙️ Configuración",
    title="Ajustes",
    subtitle="Categorías, parámetros del sistema y mantenimiento.",
)

TIPO_LBL = {"EGRESO_VARIABLE": "Egreso variable", "EGRESO_FIJO": "Egreso fijo", "INGRESO": "Ingreso"}


# ============ AGREGAR CATEGORÍA ============
section("Nueva", "Agregar categoría")

with st.container(border=True):
    with st.form("nueva_cat_manual", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            nombre = st.text_input("Nombre", placeholder="Mascotas, Veterinario...")
        with c2:
            tipo = st.selectbox("Tipo", list(TIPO_LBL), format_func=TIPO_LBL.get,
                                help="Variable = cambia mes a mes · Fijo = pagos recurrentes")
        with c3:
            umbral = st.number_input("Umbral hormiga Q", value=200.0, step=50.0,
                                     help="Solo aplica a egresos variables.")

        if st.form_submit_button("Crear categoría", type="primary"):
            if not nombre.strip():
                st.error("Nombre vacío.")
            else:
                try:
                    add_categoria(nombre.strip(), tipo, umbral if tipo == "EGRESO_VARIABLE" else None)
                    st.toast(f"Categoría '{nombre}' creada.", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"{type(e).__name__}: {e}")


spacer()


# ============ LISTAR CATEGORÍAS EXISTENTES ============
section("Catálogo", "Categorías existentes")

try:
    cats = get_categorias()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    st.stop()


if not cats.empty:
    tipo_colors = {"INGRESO": COLORS["accent"], "EGRESO_FIJO": COLORS["ink"], "EGRESO_VARIABLE": COLORS["warn"]}
    for t in ["INGRESO", "EGRESO_FIJO", "EGRESO_VARIABLE"]:
        sub = cats[cats["tipo"] == t]
        if sub.empty:
            continue
        chips = ""
        for _, row in sub.iterrows():
            off = "" if row["activa"] else "opacity:0.45;text-decoration:line-through;"
            umb = (f' <span style="color:var(--ink-mute);font-family:Geist Mono;font-size:0.7rem;">≤{fmt_q(row["umbral_hormiga"])}</span>'
                   if pd.notna(row["umbral_hormiga"]) else "")
            chips += (f'<div style="background:var(--surface);border:1px solid var(--border);border-radius:100px;'
                      f'padding:0.4rem 1rem;font-size:0.85rem;{off}">{esc(row["nombre"])}{umb}</div>')
        render_html(f"""
        <div style="font-family:'Geist Mono',monospace;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.12em;
                    color:{tipo_colors[t]};margin:1.5rem 0 0.6rem;">{TIPO_LBL[t]} · {len(sub)}</div>
        <div style="display:flex;flex-wrap:wrap;gap:0.5rem;">{chips}</div>""")

    spacer(1.2)
    with st.expander("Activar / desactivar una categoría"):
        cA, cB = st.columns([3, 1])
        with cA:
            cat_sel = st.selectbox("Categoría", cats["nombre"].tolist(),
                                   format_func=lambda n: f"{n} · {'activa' if bool(cats.loc[cats['nombre'] == n, 'activa'].iloc[0]) else 'inactiva'}")
        actual = bool(cats.loc[cats["nombre"] == cat_sel, "activa"].iloc[0])
        with cB:
            st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
            if st.button("Desactivar" if actual else "Activar", width="stretch"):
                set_categoria_activa(cat_sel, not actual)
                st.rerun()


spacer()


# ============ PARÁMETROS ============
section("Sistema", "Parámetros", "Se guardan en la hoja Config del Google Sheet.")

config = get_config()


def _f(k, d):
    try:
        return float(config.get(k, d) or d)
    except (TypeError, ValueError):
        return d


with st.container(border=True):
    with st.form("params"):
        c1, c2, c3 = st.columns(3)
        with c1:
            pago = st.number_input("Pago mensual a la tarjeta (Q)", value=_f("pago_mensual_tarjeta", 5500.0), step=250.0, format="%.2f")
            meta = st.number_input("Meta de ingresos mensual (Q)", value=_f("meta_ingresos_mes", 0.0), step=500.0, format="%.2f")
        with c2:
            umbral_def = st.number_input("Umbral hormiga default (Q)", value=_f("umbral_hormiga_default", 200.0), step=25.0)
            fin_total = st.number_input("Total de cuotas del extrafinanciamiento FIN/CT",
                                        value=int(_f("tc_fin_total_cuotas", 0)), min_value=0, step=1,
                                        help="Mirá tu contrato (p. ej. 36 o 48). 0 = no sé; se asume que sigue mientras haya deuda.")
        with c3:
            tasa_ovr = st.number_input("Forzar tasa mensual (%)", value=_f("tasa_mensual_override", 0.0) * 100, step=0.05,
                                       format="%.2f", help="0 = usar la tasa real calculada de tus estados de cuenta.")
        if st.form_submit_button("Guardar parámetros", type="primary"):
            upsert_config({
                "pago_mensual_tarjeta": round(pago, 2),
                "meta_ingresos_mes": round(meta, 2),
                "umbral_hormiga_default": round(umbral_def, 2),
                "tc_fin_total_cuotas": int(fin_total) if fin_total else "",
                "tasa_mensual_override": round(tasa_ovr / 100, 6) if tasa_ovr else "",
            })
            st.toast("Parámetros guardados.", icon="✅")
            st.rerun()

spacer(1.2)

# ---- Datos de la tarjeta (vienen del último estado de cuenta importado) ----
tc = [
    ("Tarjeta", config.get("tc_tarjeta") or "—"),
    ("Límite de crédito", fmt_q(_f("tc_limite", 0)) if config.get("tc_limite") else "—"),
    ("Disponible", fmt_q(_f("tc_disponible", 0)) if config.get("tc_disponible") not in (None, "") else "—"),
    ("Pago mínimo", fmt_q(_f("tc_pago_minimo", 0)) if config.get("tc_pago_minimo") else "—"),
    ("Saldo en mora", fmt_q(_f("tc_saldo_mora", 0)) if config.get("tc_saldo_mora") not in (None, "") else "—"),
    ("Fecha de pago", fecha_larga(pd.to_datetime(config["tc_fecha_pago"])) if config.get("tc_fecha_pago") else "—"),
    ("Fecha de corte", fecha_larga(pd.to_datetime(config["tc_fecha_corte"])) if config.get("tc_fecha_corte") else "—"),
]
items = ""
for i, (k, v) in enumerate(tc):
    borde = "" if i == len(tc) - 1 else "border-bottom:1px solid var(--border);"
    items += (f'<div style="padding:0.8rem 1.4rem;display:flex;justify-content:space-between;{borde}">'
              f'<span style="color:var(--ink-soft);">{k}</span>'
              f'<span style="font-family:Fraunces,serif;font-weight:500;">{esc(v)}</span></div>')
render_html(f"""
<div style="font-size:0.85rem;color:var(--ink-mute);margin-bottom:0.5rem;">Datos de la tarjeta según el último estado de cuenta importado</div>
<div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);overflow:hidden;">{items}</div>""")


spacer()


# ============ MANTENIMIENTO ============
section("Mantenimiento", "Caché")

if st.button("↻ Limpiar caché y recargar todo"):
    clear_all_caches()
    st.success("Caché limpiada. Los próximos datos vendrán frescos del Google Sheet.")
    st.rerun()

spacer(2)

with st.expander("ℹ️ Sobre esta app"):
    st.markdown("""
    **Finanzas Familiares v4.0**

    Streamlit + Google Sheets como backend.

    **Hojas:** Transacciones, Categorias, Plan_Tarjeta, Config y Movimientos_Tarjeta
    (esta última se crea sola al importar el primer estado de cuenta).

    **Tarjeta:** el saldo, la tasa y la proyección salen de los estados de cuenta reales del banco;
    el plan de cuotas es solo el compromiso de pago.

    **Backup:** el propio Google Sheet tiene historial en Archivo → Historial de versiones.
    """)
