"""
Finanzas Familiares - Pablo & Maite
Dashboard principal con resumen del mes actual.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from helpers.sheets import (
    get_transacciones, get_plan, get_config, clear_all_caches
)
from helpers.calc import (
    resumen_mes, gastos_hormiga, egresos_por_categoria,
    calcular_saldo_actual_tarjeta, mes_actual_dt, nombre_mes_es,
)


st.set_page_config(
    page_title="Finanzas Familiares",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def fmt_q(v: float) -> str:
    return f"Q {v:,.2f}"


def main():
    st.title("💰 Finanzas Familiares")
    st.caption("Pablo & Maite · Control diario de ingresos y egresos")

    # Sidebar: selector de mes a analizar
    año_actual, mes_actual = mes_actual_dt()
    with st.sidebar:
        st.subheader("Periodo")
        año_sel = st.number_input("Año", min_value=2025, max_value=2030, value=año_actual, step=1)
        mes_sel = st.selectbox(
            "Mes",
            options=list(range(1, 13)),
            index=mes_actual - 1,
            format_func=nombre_mes_es,
        )
        st.divider()
        if st.button("🔄 Refrescar datos", use_container_width=True):
            clear_all_caches()
            st.rerun()

    # Cargar datos
    try:
        df = get_transacciones()
        plan = get_plan()
        config = get_config()
    except Exception as e:
        st.error(f"Error conectando a Google Sheets: {e}")
        st.info("Revisa que `secrets.toml` esté bien configurado y que el sheet esté compartido con la service account.")
        return

    # ============ FILA 1: Métricas del mes ============
    st.subheader(f"📊 Resumen · {nombre_mes_es(mes_sel)} {año_sel}")

    resumen = resumen_mes(df, año_sel, mes_sel)
    meta_ingresos = config.get("meta_ingresos_mes", 25541.40)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Ingresos",
            fmt_q(resumen["ingresos"]),
            delta=f"{(resumen['ingresos']/meta_ingresos*100 - 100):.1f}% vs meta" if meta_ingresos else None,
        )
    with c2:
        st.metric("Egresos", fmt_q(resumen["egresos"]))
    with c3:
        diff = resumen["diferencia"]
        st.metric(
            "Diferencia",
            fmt_q(diff),
            delta=("Positivo" if diff >= 0 else "Negativo"),
            delta_color="normal" if diff >= 0 else "inverse",
        )
    with c4:
        st.metric("Transacciones", resumen["n_transacciones"])

    # ============ FILA 2: Plan tarjeta + gastos hormiga ============
    st.divider()
    cA, cB = st.columns([1, 1])

    with cA:
        st.subheader("💳 Plan Tarjeta")
        saldo_inicial = config.get("saldo_inicial_tarjeta", 39671.28)
        info = calcular_saldo_actual_tarjeta(plan, saldo_inicial)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Saldo restante", fmt_q(info["saldo_actual"]))
            st.metric("Meses pagados", f"{info['meses_pagados']} / {len(plan)}")
        with c2:
            avance = (info["total_pagado"] / saldo_inicial * 100) if saldo_inicial else 0
            st.metric("Avance del plan", f"{avance:.1f}%")
            if info["proximo_mes"]:
                st.metric(
                    "Próxima cuota",
                    fmt_q(info["proximo_mes"]["pago_planeado"]),
                    delta=info["proximo_mes"]["mes_label"],
                    delta_color="off",
                )

        progress = min(info["total_pagado"] / saldo_inicial, 1.0) if saldo_inicial else 0
        st.progress(progress, text=f"Pagado: {fmt_q(info['total_pagado'])} de {fmt_q(saldo_inicial)}")

    with cB:
        st.subheader("🐜 Gastos Hormiga del Mes")
        hormiga_df = gastos_hormiga(df, año_sel, mes_sel)
        if hormiga_df.empty:
            st.info("Aún no hay gastos hormiga registrados este mes.")
        else:
            total_hormiga = hormiga_df["total"].sum()
            n_hormiga = hormiga_df["conteo"].sum()
            st.metric(
                "Total gastado en cosas pequeñas",
                fmt_q(total_hormiga),
                delta=f"{int(n_hormiga)} compras",
                delta_color="off",
            )
            st.dataframe(
                hormiga_df.rename(columns={
                    "categoria": "Categoría",
                    "total": "Total Q",
                    "conteo": "#",
                    "promedio": "Promedio Q",
                }).style.format({"Total Q": "Q {:,.2f}", "Promedio Q": "Q {:,.2f}"}),
                hide_index=True,
                use_container_width=True,
            )

    # ============ FILA 3: Egresos por categoría (chart) ============
    st.divider()
    st.subheader("📋 Egresos por categoría del mes")

    egresos_cat = egresos_por_categoria(df, año_sel, mes_sel)
    if egresos_cat.empty:
        st.info("Aún no hay egresos registrados este mes.")
    else:
        fig = px.bar(
            egresos_cat.head(15),
            x="total",
            y="categoria",
            orientation="h",
            text="total",
            labels={"total": "Q gastados", "categoria": ""},
        )
        fig.update_traces(texttemplate="Q %{text:,.0f}", textposition="outside")
        fig.update_layout(
            height=max(300, 30 * len(egresos_cat.head(15)) + 100),
            margin=dict(l=10, r=80, t=20, b=20),
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig, use_container_width=True)

    # ============ FILA 4: Últimas transacciones ============
    st.divider()
    st.subheader("🕐 Últimas 10 transacciones")
    if df.empty:
        st.info("Aún no hay transacciones registradas. Ve a la página '➕ Registrar' para empezar.")
    else:
        ult = df.sort_values("fecha", ascending=False).head(10).copy()
        ult["fecha"] = ult["fecha"].dt.strftime("%d/%m/%Y")
        ult["monto"] = ult["monto"].apply(fmt_q)
        st.dataframe(
            ult[["fecha", "tipo", "persona", "categoria", "descripcion", "monto"]].rename(columns={
                "fecha": "Fecha", "tipo": "Tipo", "persona": "Persona",
                "categoria": "Categoría", "descripcion": "Descripción", "monto": "Monto",
            }),
            hide_index=True,
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
