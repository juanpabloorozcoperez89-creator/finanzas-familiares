"""
Configuración: categorías y parámetros.
"""
import streamlit as st
import pandas as pd

from helpers.sheets import (
    get_categorias, add_categoria, get_config, clear_all_caches
)
from helpers.theme import apply_theme, hero, fmt_q, COLORS


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
    subtitle="Categorías, parámetros del sistema, y mantenimiento.",
)


# ============ AGREGAR CATEGORÍA ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Nueva
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Agregar categoría</h3>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">', unsafe_allow_html=True)

with st.form("nueva_cat_manual", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        nombre = st.text_input("Nombre", placeholder="Mascotas, Veterinario...")
    with c2:
        tipo = st.selectbox(
            "Tipo",
            ["EGRESO_VARIABLE", "EGRESO_FIJO", "INGRESO"],
            format_func=lambda x: {"EGRESO_VARIABLE": "Egreso variable", "EGRESO_FIJO": "Egreso fijo", "INGRESO": "Ingreso"}[x],
            help="Variable = cambia mes a mes · Fijo = pagos recurrentes",
        )
    with c3:
        umbral = st.number_input("Umbral Q", value=200.0, step=50.0) if tipo == "EGRESO_VARIABLE" else None

    if st.form_submit_button("Crear categoría", type="primary"):
        if not nombre.strip():
            st.error("Nombre vacío.")
        else:
            try:
                add_categoria(nombre.strip(), tipo, umbral)
                st.success(f"Categoría '{nombre}' creada.")
                st.rerun()
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")

st.markdown('</div>', unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ LISTAR CATEGORÍAS EXISTENTES ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Catálogo
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Categorías existentes</h3>
</div>
""", unsafe_allow_html=True)

try:
    cats = get_categorias()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    st.stop()


if not cats.empty:
    # Agrupar por tipo
    tipos_orden = ["INGRESO", "EGRESO_FIJO", "EGRESO_VARIABLE"]
    tipo_labels = {"INGRESO": "Ingresos", "EGRESO_FIJO": "Egresos fijos", "EGRESO_VARIABLE": "Egresos variables"}
    tipo_colors = {"INGRESO": COLORS["accent"], "EGRESO_FIJO": COLORS["ink"], "EGRESO_VARIABLE": COLORS["warn"]}

    for t in tipos_orden:
        sub = cats[cats["tipo"] == t]
        if sub.empty:
            continue
        st.markdown(f"""
        <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                    text-transform: uppercase; letter-spacing: 0.12em;
                    color: {tipo_colors[t]}; margin: 1.5rem 0 0.6rem;">
            {tipo_labels[t]} · {len(sub)}
        </div>
        """, unsafe_allow_html=True)

        chips_html = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">'
        for _, row in sub.iterrows():
            active_style = "" if row["activa"] else "opacity: 0.5; text-decoration: line-through;"
            umbral_label = f' <span style="color: var(--ink-mute); font-family: Geist Mono; font-size: 0.7rem;">≤{fmt_q(row["umbral_hormiga"])}</span>' if pd.notna(row["umbral_hormiga"]) else ''
            chips_html += f"""
            <div style="background: var(--surface); border: 1px solid var(--border);
                        border-radius: 100px; padding: 0.4rem 1rem; font-size: 0.85rem;
                        {active_style}">
                {row['nombre']}{umbral_label}
            </div>
            """
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ PARÁMETROS ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Sistema
    </div>
    <h3 style="margin: 0 0 0.3rem; font-size: 1.3rem;">Parámetros</h3>
    <p style="color: var(--ink-mute); font-size: 0.9rem; margin: 0;">
        Edita estos valores directamente en la hoja <code>Config</code> del Google Sheet.
    </p>
</div>
""", unsafe_allow_html=True)

try:
    config = get_config()
    labels = {
        "saldo_inicial_tarjeta": ("Saldo inicial de la tarjeta", "Q"),
        "tasa_mensual": ("Tasa de interés mensual", "%"),
        "iva": ("IVA sobre intereses", "%"),
        "umbral_hormiga_default": ("Umbral hormiga default", "Q"),
        "meta_ingresos_mes": ("Meta de ingresos mensual", "Q"),
    }

    items_html = '<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; box-shadow: var(--shadow); overflow: hidden;">'
    for i, (k, v) in enumerate(config.items()):
        label, unit = labels.get(k, (k, ""))
        if unit == "%":
            val_display = f"{v*100:.2f}%"
        elif unit == "Q":
            val_display = fmt_q(v) if isinstance(v, (int, float)) else str(v)
        else:
            val_display = str(v)
        is_last = i == len(config) - 1
        border = "" if is_last else "border-bottom: 1px solid var(--border);"
        items_html += f"""
        <div style="padding: 1rem 1.4rem; display: flex; justify-content: space-between; align-items: center; {border}">
            <div>
                <div style="color: var(--ink); font-size: 0.95rem;">{label}</div>
                <div style="color: var(--ink-mute); font-size: 0.78rem; font-family: 'Geist Mono', monospace; margin-top: 0.1rem;">{k}</div>
            </div>
            <div style="font-family: 'Fraunces', serif; font-size: 1.15rem; font-weight: 500;">
                {val_display}
            </div>
        </div>
        """
    items_html += '</div>'
    st.markdown(items_html, unsafe_allow_html=True)
except Exception as e:
    st.error(f"{type(e).__name__}: {e}")


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ MANTENIMIENTO ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Mantenimiento
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Cache</h3>
</div>
""", unsafe_allow_html=True)

if st.button("↻ Limpiar caché y recargar todo"):
    clear_all_caches()
    st.success("Caché limpiada. Los próximos datos vendrán frescos del Google Sheet.")
    st.rerun()

st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)

with st.expander("ℹ️ Sobre esta app"):
    st.markdown("""
    **Finanzas Familiares v3.0**

    Streamlit + Google Sheets como backend. Diseño fintech con paleta verde forest y tipografía editorial (Fraunces + Geist).

    **Estructura:**
    - 4 pestañas en Google Sheets: Transacciones, Categorias, Plan_Tarjeta, Config
    - Cache de 30-120 segundos para velocidad
    - Mobile-first responsive

    **Backup:** El propio Google Sheet es el backup. Tiene historial automático en Archivo → Historial de versiones.
    """)
