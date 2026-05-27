"""
Registrar un nuevo movimiento — UX optimizada para celular.
"""
import streamlit as st
from datetime import date

from helpers.sheets import (
    get_categorias_activas, add_transaccion,
    add_categoria, get_umbral_hormiga,
)
from helpers.theme import apply_theme, hero, fmt_q, COLORS


st.set_page_config(
    page_title="Registrar · Finanzas",
    page_icon="✏️",
    layout="centered",
    initial_sidebar_state="collapsed",
)
apply_theme()


hero(
    eyebrow="Nuevo movimiento",
    title="Registra un gasto o ingreso",
    subtitle="Toma 10 segundos. Cada movimiento cuenta.",
)


# ============ Toggle visual EGRESO/INGRESO ============
tipo = st.radio(
    "Tipo de movimiento",
    options=["EGRESO", "INGRESO"],
    horizontal=True,
    label_visibility="collapsed",
    key="tipo_mov",
)

st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)


# ============ FORMULARIO ============
with st.form("nuevo_movimiento", clear_on_submit=True):
    st.markdown(f"""
    <div style="background: {'rgba(10,110,78,0.06)' if tipo == 'INGRESO' else 'rgba(15,31,28,0.03)'};
                border: 1px solid {'rgba(10,110,78,0.2)' if tipo == 'INGRESO' else 'var(--border)'};
                border-radius: 14px; padding: 0.6rem 1rem; margin-bottom: 1.2rem;
                font-size: 0.85rem; color: var(--ink-soft);">
        Registrando un <b style="color: {'var(--accent)' if tipo == 'INGRESO' else 'var(--ink)'};">{tipo.lower()}</b>
    </div>
    """, unsafe_allow_html=True)

    # ---- Fila 1: Monto destacado ----
    st.markdown("**¿Cuánto?**")
    monto = st.number_input(
        "Monto",
        min_value=0.0, step=10.0, format="%.2f",
        label_visibility="collapsed",
        placeholder="0.00",
    )

    st.markdown("<div style='height: 0.7rem'></div>", unsafe_allow_html=True)

    # ---- Fila 2: Fecha y persona ----
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Fecha**")
        fecha = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY", label_visibility="collapsed")
    with col2:
        st.markdown("**Persona**")
        persona = st.selectbox("Persona", ["Pablo", "Sofi", "Familia"], label_visibility="collapsed")

    st.markdown("<div style='height: 0.7rem'></div>", unsafe_allow_html=True)

    # ---- Fila 3: Categoría ----
    st.markdown("**Categoría**")
    cats = get_categorias_activas(tipo=tipo)
    cats_options = cats + ["+ Crear nueva categoría..."]
    categoria_sel = st.selectbox("Categoría", cats_options, label_visibility="collapsed")

    nueva_cat_input = None
    sub_tipo = None
    umbral_nueva = None
    if categoria_sel == "+ Crear nueva categoría...":
        st.markdown("<div style='height: 0.4rem'></div>", unsafe_allow_html=True)
        nueva_cat_input = st.text_input(
            "Nombre de la nueva categoría",
            placeholder="Veterinario, Restaurante X, etc.",
        )
        if tipo == "EGRESO":
            cc1, cc2 = st.columns(2)
            with cc1:
                sub_tipo = st.radio(
                    "Tipo de gasto",
                    ["EGRESO_VARIABLE", "EGRESO_FIJO"],
                    horizontal=False,
                    format_func=lambda x: "Variable" if x == "EGRESO_VARIABLE" else "Fijo (mensual)",
                )
            with cc2:
                if sub_tipo == "EGRESO_VARIABLE":
                    umbral_nueva = st.number_input(
                        "Umbral hormiga (Q)",
                        value=200.0, min_value=0.0, step=50.0,
                        help="Gastos menores a esto se marcan como hormiga",
                    )
        else:
            sub_tipo = "INGRESO"

    st.markdown("<div style='height: 0.7rem'></div>", unsafe_allow_html=True)

    # ---- Fila 4: Descripción ----
    st.markdown("**Descripción**")
    descripcion = st.text_input(
        "Descripción",
        placeholder="Súper La Torre semana 1, Gasolina CX-5, Corte hija...",
        label_visibility="collapsed",
    )

    st.markdown("<div style='height: 1.2rem'></div>", unsafe_allow_html=True)

    # ---- Botón submit ----
    submitted = st.form_submit_button(
        "Guardar movimiento",
        type="primary",
        use_container_width=True,
    )

    if submitted:
        if monto <= 0:
            st.error("El monto debe ser mayor a cero.")
            st.stop()
        if not descripcion.strip():
            st.error("Agrega una descripción para identificarlo después.")
            st.stop()

        # Resolver categoría final
        if categoria_sel == "+ Crear nueva categoría...":
            if not nueva_cat_input or not nueva_cat_input.strip():
                st.error("Escribe el nombre de la nueva categoría.")
                st.stop()
            try:
                add_categoria(nueva_cat_input.strip(), sub_tipo, umbral_nueva)
                categoria_final = nueva_cat_input.strip()
            except Exception as e:
                st.error(f"No se pudo crear la categoría: {e}")
                st.stop()
        else:
            categoria_final = categoria_sel

        es_hormiga = False
        if tipo == "EGRESO":
            umbral = get_umbral_hormiga(categoria_final)
            if umbral is not None and monto < umbral:
                es_hormiga = True

        try:
            add_transaccion(
                fecha=fecha.strftime("%Y-%m-%d"),
                tipo=tipo,
                persona=persona,
                categoria=categoria_final,
                descripcion=descripcion.strip(),
                monto=float(monto),
                es_hormiga=es_hormiga,
            )
            hormiga_badge = '<span style="background: var(--warn-soft); color: var(--warn); padding: 0.15rem 0.6rem; border-radius: 100px; font-size: 0.75rem; font-weight: 500; margin-left: 0.4rem;">🐜 gasto hormiga</span>' if es_hormiga else ''
            signo_color = COLORS["accent"] if tipo == "INGRESO" else COLORS["ink"]
            signo = "+" if tipo == "INGRESO" else "−"

            st.markdown(f"""
            <div style="background: var(--accent-2); border: 1px solid rgba(10,110,78,0.2);
                        border-radius: 14px; padding: 1.5rem; margin-top: 1rem;
                        text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">✓</div>
                <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 500; color: var(--ink); margin-bottom: 0.3rem;">
                    Guardado correctamente
                </div>
                <div style="color: var(--ink-soft); font-size: 0.95rem; margin-bottom: 0.5rem;">
                    <span style="font-family: 'Fraunces', serif; font-size: 1.3rem; font-weight: 500; color: {signo_color};">{signo}{fmt_q(monto)}</span>
                    en <b>{categoria_final}</b>{hormiga_badge}
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
        except Exception as e:
            st.error(f"Error guardando: {e}")


# ============ Tips contextuales ============
st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)

with st.expander("💡 Tips para sacarle provecho"):
    st.markdown("""
    **Registra en el momento.** Cada vez que pagues algo, abre la app y anótalo. Si lo dejas para después, se olvida.

    **¿Qué es un gasto hormiga?** Una compra pequeña (menor al umbral, default Q200) que individualmente no parece nada pero acumulada en el mes suma Q1,500–3,000. La app los marca solos.

    **Persona "Familia"** úsala para gastos compartidos donde no importa quién pagó (renta, súper).

    **Tip de productividad:** Agrega esta página como atajo en tu pantalla de inicio del celular. Safari/Chrome → menú → "Agregar a pantalla de inicio".
    """)
