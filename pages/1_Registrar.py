"""
Registrar un nuevo movimiento (ingreso o egreso).
Diseñado para uso rápido desde el celular.
"""
import streamlit as st
from datetime import date

from helpers.sheets import (
    get_categorias, get_categorias_activas, add_transaccion,
    add_categoria, get_umbral_hormiga,
)


st.set_page_config(page_title="Registrar", page_icon="➕", layout="centered")
st.title("➕ Registrar movimiento")


# ============ Toggle: ingreso o egreso ============
tipo = st.radio(
    "Tipo de movimiento",
    options=["EGRESO", "INGRESO"],
    horizontal=True,
    key="tipo_mov",
)

# ============ Formulario ============
with st.form("nuevo_movimiento", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
    with col2:
        persona = st.selectbox("Persona", ["Pablo", "Sofi", "Familia"])

    # Categorías filtradas por tipo seleccionado
    cats = get_categorias_activas(tipo=tipo)
    cats_options = cats + ["➕ Crear nueva categoría..."]
    categoria_sel = st.selectbox("Categoría", cats_options)

    nueva_cat_input = None
    if categoria_sel == "➕ Crear nueva categoría...":
        nueva_cat_input = st.text_input(
            "Nombre de la nueva categoría",
            placeholder="ej. Veterinario, Restaurante X, etc.",
        )
        if tipo == "EGRESO":
            sub_tipo = st.radio(
                "¿Es un egreso fijo (mensual) o variable?",
                ["EGRESO_VARIABLE", "EGRESO_FIJO"],
                horizontal=True,
                help="Variable = gastos que cambian mes a mes (comida fuera, salud, etc.). Fijo = pagos recurrentes (luz, internet).",
            )
            umbral_nueva = st.number_input(
                "Umbral hormiga (gastos menores a esto se consideran 'hormiga')",
                value=200.0, min_value=0.0, step=50.0,
            ) if sub_tipo == "EGRESO_VARIABLE" else None
        else:
            sub_tipo = "INGRESO"
            umbral_nueva = None

    descripcion = st.text_input(
        "Descripción",
        placeholder="ej. Súper La Torre semana 1, Gasolina CX-5, Corte hija",
    )
    monto = st.number_input(
        "Monto (Q)",
        min_value=0.0, step=10.0, format="%.2f",
    )

    submitted = st.form_submit_button("💾 Guardar movimiento", type="primary", use_container_width=True)

    if submitted:
        if monto <= 0:
            st.error("El monto debe ser mayor a cero.")
            st.stop()
        if not descripcion.strip():
            st.error("Agrega una descripción para que después lo identifiques.")
            st.stop()

        # Resolver categoría final
        if categoria_sel == "➕ Crear nueva categoría...":
            if not nueva_cat_input or not nueva_cat_input.strip():
                st.error("Escribe el nombre de la nueva categoría.")
                st.stop()
            try:
                add_categoria(nueva_cat_input.strip(), sub_tipo, umbral_nueva)
                categoria_final = nueva_cat_input.strip()
                st.success(f"Categoría '{categoria_final}' creada.")
            except Exception as e:
                st.error(f"No se pudo crear la categoría: {e}")
                st.stop()
        else:
            categoria_final = categoria_sel

        # Decidir si es gasto hormiga
        es_hormiga = False
        if tipo == "EGRESO":
            umbral = get_umbral_hormiga(categoria_final)
            if umbral is not None and monto < umbral:
                es_hormiga = True

        # Guardar
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
            etiqueta = "🐜 (gasto hormiga)" if es_hormiga else ""
            st.success(f"✅ Guardado: {tipo} de Q{monto:,.2f} en '{categoria_final}' {etiqueta}")
            st.balloons()
        except Exception as e:
            st.error(f"Error guardando: {e}")


# ============ Ayuda contextual ============
with st.expander("💡 Cómo usar esta página"):
    st.markdown("""
    **Para registrar rápido cualquier gasto:**

    1. Selecciona si es EGRESO (gastaste) o INGRESO (recibiste dinero)
    2. La fecha por defecto es hoy
    3. Elige quién hizo el gasto (Pablo, Sofi o Familia para gastos compartidos)
    4. Escoge una categoría existente o crea una nueva
    5. Pon una descripción corta para acordarte después
    6. Monto en quetzales

    **¿Qué es un gasto hormiga?**
    Es cualquier compra pequeña (menor al umbral de su categoría, default Q200) que individualmente no parece nada
    pero acumulada al mes puede ser Q1,500-3,000.
    La app los marca solos y los suma aparte en el dashboard.

    **Tip:** Agrega esta página como acceso directo en tu pantalla de inicio del celular.
    Cada vez que pagues algo, abres y registras en 10 segundos.
    """)
