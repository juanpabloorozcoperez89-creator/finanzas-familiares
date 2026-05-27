"""
Análisis detallado de gastos hormiga.
Muestra todos los gastos pequeños del mes con detalle por transacción.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from helpers.sheets import get_transacciones
from helpers.calc import filtrar_mes, gastos_hormiga, mes_actual_dt, nombre_mes_es


st.set_page_config(page_title="Gastos Hormiga", page_icon="🐜", layout="wide")
st.title("🐜 Gastos Hormiga")
st.caption("Los pequeños gastos que individualmente no se notan, pero suman.")


# Selector de mes
año_actual, mes_actual = mes_actual_dt()
c1, c2 = st.columns(2)
with c1:
    año_sel = st.number_input("Año", min_value=2025, max_value=2030, value=año_actual, step=1)
with c2:
    mes_sel = st.selectbox("Mes", options=list(range(1, 13)),
                           index=mes_actual - 1, format_func=nombre_mes_es)

try:
    df = get_transacciones()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    with st.expander("Ver detalles técnicos"):
        import traceback
        st.code(traceback.format_exc())
    st.stop()


sub = filtrar_mes(df, año_sel, mes_sel)
hormigas = sub[(sub["tipo"] == "EGRESO") & (sub["es_hormiga"])].copy()

if hormigas.empty:
    st.info(f"No hay gastos hormiga registrados en {nombre_mes_es(mes_sel)} {año_sel}.")
    st.stop()


# ============ Métricas top ============
total = hormigas["monto"].sum()
n = len(hormigas)
promedio = hormigas["monto"].mean()
egresos_totales = sub[sub["tipo"] == "EGRESO"]["monto"].sum()
porcentaje = (total / egresos_totales * 100) if egresos_totales else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total hormiga", f"Q {total:,.2f}")
with c2:
    st.metric("# de gastos", n)
with c3:
    st.metric("Promedio por gasto", f"Q {promedio:,.2f}")
with c4:
    st.metric("% del egreso total", f"{porcentaje:.1f}%")

st.divider()

# ============ Por categoría ============
st.subheader("📊 Por categoría")
agrupado = gastos_hormiga(df, año_sel, mes_sel)

cA, cB = st.columns([1, 1])
with cA:
    fig = px.pie(
        agrupado, names="categoria", values="total",
        hole=0.4,
    )
    fig.update_traces(textposition="outside", textinfo="label+percent")
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=20), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with cB:
    st.dataframe(
        agrupado.rename(columns={
            "categoria": "Categoría", "total": "Total Q",
            "conteo": "#", "promedio": "Promedio Q",
        }).style.format({"Total Q": "Q {:,.2f}", "Promedio Q": "Q {:,.2f}"}),
        hide_index=True,
        use_container_width=True,
        height=400,
    )

st.divider()

# ============ Detalle transacción por transacción ============
st.subheader("📜 Cada gasto individual")
hormigas_show = hormigas.sort_values("fecha", ascending=False).copy()
hormigas_show["fecha"] = hormigas_show["fecha"].dt.strftime("%d/%m/%Y")
hormigas_show["monto"] = hormigas_show["monto"].apply(lambda v: f"Q {v:,.2f}")

st.dataframe(
    hormigas_show[["fecha", "persona", "categoria", "descripcion", "monto"]].rename(columns={
        "fecha": "Fecha", "persona": "Persona", "categoria": "Categoría",
        "descripcion": "Descripción", "monto": "Monto",
    }),
    hide_index=True,
    use_container_width=True,
)

# ============ Insight contextual ============
st.divider()
total_anual_proyectado = total * 12
st.info(
    f"**Si este ritmo de gasto hormiga se mantiene todo el año, gastarían "
    f"Q {total_anual_proyectado:,.2f} solo en cosas pequeñas.** "
    f"Equivale a {total_anual_proyectado / 5500:.1f} cuotas de tarjeta de las que estás pagando."
)
