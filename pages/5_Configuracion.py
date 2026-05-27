"""
Configuración: ver/editar categorías y ver parámetros.
"""
import streamlit as st
import pandas as pd

from helpers.sheets import (
    get_categorias, add_categoria, get_config, clear_all_caches
)


st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
st.title("⚙️ Configuración")


# ============ Categorías ============
st.subheader("📁 Categorías existentes")
try:
    cats = get_categorias()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    with st.expander("Ver detalles técnicos"):
        import traceback
        st.code(traceback.format_exc())
    st.stop()

if not cats.empty:
    cats_show = cats.copy()
    cats_show["umbral_hormiga"] = cats_show["umbral_hormiga"].apply(
        lambda v: f"Q {v:,.0f}" if pd.notna(v) else "—"
    )
    cats_show["activa"] = cats_show["activa"].apply(lambda v: "✅" if v else "❌")
    st.dataframe(
        cats_show.rename(columns={
            "nombre": "Nombre", "tipo": "Tipo",
            "umbral_hormiga": "Umbral hormiga", "activa": "Activa",
        }),
        hide_index=True,
        use_container_width=True,
    )

st.divider()

# ============ Agregar categoría manual ============
st.subheader("➕ Agregar categoría manualmente")
with st.form("nueva_cat_manual", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        nombre = st.text_input("Nombre", placeholder="ej. Mascotas, Veterinario")
    with c2:
        tipo = st.selectbox(
            "Tipo",
            ["EGRESO_VARIABLE", "EGRESO_FIJO", "INGRESO"],
            help="VARIABLE = cambia mes a mes. FIJO = recurrente (luz, internet).",
        )
    with c3:
        umbral = st.number_input("Umbral hormiga", value=200.0, step=50.0) if tipo == "EGRESO_VARIABLE" else None

    if st.form_submit_button("Crear", type="primary"):
        if not nombre.strip():
            st.error("Nombre vacío.")
        else:
            try:
                add_categoria(nombre.strip(), tipo, umbral)
                st.success(f"Categoría '{nombre}' creada.")
                st.rerun()
            except Exception as e:
                st.error(f"**{type(e).__name__}:** {e}")
    with st.expander("Ver detalles técnicos"):
        import traceback
        st.code(traceback.format_exc())

st.divider()

# ============ Parámetros ============
st.subheader("🔧 Parámetros del sistema")
st.caption("Edita estos valores directamente en la hoja `Config` del Google Sheet.")

try:
    config = get_config()
    config_df = pd.DataFrame([
        {"Parámetro": k, "Valor": v} for k, v in config.items()
    ])
    st.dataframe(config_df, hide_index=True, use_container_width=True)
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    with st.expander("Ver detalles técnicos"):
        import traceback
        st.code(traceback.format_exc())

st.divider()

# ============ Mantenimiento ============
st.subheader("🧹 Mantenimiento")
if st.button("🔄 Limpiar caché y recargar todo", type="secondary"):
    clear_all_caches()
    st.success("Caché limpiada. Los próximos datos vendrán frescos del Google Sheet.")
    st.rerun()

with st.expander("ℹ️ Sobre esta app"):
    st.markdown("""
    **Finanzas Familiares v1.0**

    Construida con Streamlit + Google Sheets.

    **Cómo funciona:**
    - Toda la data vive en un Google Sheet (4 pestañas).
    - La app cachea datos por 30-120 segundos para que sea rápida.
    - Para forzar recarga, usa el botón de arriba.

    **Cómo editar manualmente:**
    Abre el Google Sheet directamente. Cualquier cambio que hagas allí
    se verá reflejado en la app cuando se actualice la caché (o lo fuerces).

    **Backup:**
    El propio Google Sheet es el backup. Tiene historial de cambios automático.
    Si algo se rompe, puedes restaurar versión anterior desde Archivo → Historial.
    """)
