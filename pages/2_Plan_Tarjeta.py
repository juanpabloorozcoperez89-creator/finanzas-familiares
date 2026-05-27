"""
Plan de pago de la tarjeta de crédito.
Muestra el calendario de 7 meses y permite marcar pagos reales.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

from helpers.sheets import get_plan, get_config, update_pago_real
from helpers.calc import calcular_saldo_actual_tarjeta


st.set_page_config(page_title="Plan Tarjeta", page_icon="💳", layout="wide")
st.title("💳 Plan de Pago Tarjeta")


def fmt_q(v):
    if pd.isna(v):
        return "—"
    return f"Q {v:,.2f}"


try:
    plan = get_plan()
    config = get_config()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    with st.expander("Ver detalles técnicos"):
        import traceback
        st.code(traceback.format_exc())
    st.stop()

if plan.empty:
    st.warning("La hoja `Plan_Tarjeta` está vacía. Revisa el README para configurarla.")
    st.stop()


saldo_inicial = config.get("saldo_inicial_tarjeta", 39671.28)
info = calcular_saldo_actual_tarjeta(plan, saldo_inicial)

# ============ Métricas clave ============
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Saldo inicial", fmt_q(saldo_inicial))
with c2:
    st.metric("Total pagado", fmt_q(info["total_pagado"]))
with c3:
    st.metric("Saldo restante", fmt_q(info["saldo_actual"]))
with c4:
    avance = (info["total_pagado"] / saldo_inicial * 100) if saldo_inicial else 0
    st.metric("% Avance", f"{avance:.1f}%")

st.progress(
    min(info["total_pagado"] / saldo_inicial, 1.0) if saldo_inicial else 0,
    text=f"Pagado {fmt_q(info['total_pagado'])} de {fmt_q(saldo_inicial)}",
)

st.divider()

# ============ Próximo pago - acción rápida ============
if info["proximo_mes"]:
    prox = info["proximo_mes"]
    st.subheader(f"📅 Próxima cuota: {prox['mes_label']}")
    cprox1, cprox2 = st.columns([2, 1])
    with cprox1:
        st.write(f"**Monto planeado:** {fmt_q(prox['pago_planeado'])}")
        if prox.get('notas'):
            st.caption(f"Nota: {prox['notas']}")

    with cprox2:
        with st.expander("✅ Marcar pago como realizado"):
            with st.form(f"pago_{int(prox['mes_num'])}"):
                pago_real = st.number_input(
                    "Monto pagado real",
                    value=float(prox['pago_planeado']),
                    step=100.0,
                    format="%.2f",
                )
                fecha_pago = st.date_input("Fecha de pago", value=date.today(), format="DD/MM/YYYY")
                notas_nuevas = st.text_input("Notas (opcional)", value=prox.get('notas', ''))
                if st.form_submit_button("Guardar pago", type="primary"):
                    try:
                        update_pago_real(
                            mes_num=int(prox['mes_num']),
                            pago_real=pago_real,
                            fecha_pago=fecha_pago.strftime("%Y-%m-%d"),
                            notas=notas_nuevas,
                        )
                        st.success("Pago registrado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"**{type(e).__name__}:** {e}")
    with st.expander("Ver detalles técnicos"):
        import traceback
        st.code(traceback.format_exc())
else:
    st.success("🎉 ¡Plan completado! Todos los pagos del plan ya están registrados.")

st.divider()

# ============ Tabla del plan ============
st.subheader("📋 Calendario completo del plan")

plan_show = plan.copy()
plan_show["estado"] = plan_show["pago_real"].apply(
    lambda x: "✅ Pagado" if pd.notna(x) else "⏳ Pendiente"
)
plan_show["pago_planeado_fmt"] = plan_show["pago_planeado"].apply(fmt_q)
plan_show["pago_real_fmt"] = plan_show["pago_real"].apply(fmt_q)
plan_show["saldo_inicial_fmt"] = plan_show["saldo_inicial_plan"].apply(fmt_q)

st.dataframe(
    plan_show[["mes_num", "mes_label", "saldo_inicial_fmt", "pago_planeado_fmt", "pago_real_fmt", "fecha_pago_real", "estado", "notas"]].rename(columns={
        "mes_num": "#",
        "mes_label": "Mes",
        "saldo_inicial_fmt": "Saldo inicial",
        "pago_planeado_fmt": "Plan",
        "pago_real_fmt": "Real",
        "fecha_pago_real": "Fecha real",
        "estado": "Estado",
        "notas": "Notas",
    }),
    hide_index=True,
    use_container_width=True,
)

# ============ Gráfica: saldo proyectado vs real ============
st.divider()
st.subheader("📉 Evolución del saldo")

# Calcular saldo proyectado mes a mes
tasa = config.get("tasa_mensual", 0.0375)
iva = config.get("iva", 0.12)

saldo_proyectado = [saldo_inicial]
saldo_real = [saldo_inicial]
labels = ["Inicio"]
s_p = saldo_inicial
s_r = saldo_inicial
for _, row in plan.iterrows():
    interes = s_p * tasa
    iva_c = interes * iva
    s_p = s_p + interes + iva_c - row["pago_planeado"]
    if s_p < 0:
        s_p = 0
    saldo_proyectado.append(s_p)

    if pd.notna(row["pago_real"]):
        interes_r = s_r * tasa
        iva_r = interes_r * iva
        s_r = s_r + interes_r + iva_r - row["pago_real"]
        if s_r < 0:
            s_r = 0
        saldo_real.append(s_r)
    else:
        saldo_real.append(None)
    labels.append(row["mes_label"])

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=labels, y=saldo_proyectado, name="Saldo planeado",
    mode="lines+markers", line=dict(color="#1F4E78", dash="dash"),
))
fig.add_trace(go.Scatter(
    x=labels, y=saldo_real, name="Saldo real (según pagos hechos)",
    mode="lines+markers", line=dict(color="#2E8B57", width=3),
))
fig.update_layout(
    yaxis_title="Saldo restante (Q)",
    height=400,
    margin=dict(l=10, r=10, t=20, b=20),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ============ Resumen del plan ============
with st.expander("📖 Detalle del plan optimizado"):
    st.markdown(f"""
    **Plan diseñado en mayo 2026 con base en:**
    - Saldo inicial: **{fmt_q(saldo_inicial)}**
    - Tasa de interés: **{tasa*100:.2f}% mensual** + IVA {iva*100:.0f}%
    - Bono 14 (julio): refuerzo de Q7,500 → pago de Q13,000 en julio
    - Aguinaldo (diciembre): pago de cierre Q5,493 (sobra Q9,506 para fin de año)

    **Total a pagar en 7 meses:** Q 45,993.35
    **Intereses + IVA totales:** ~Q 6,322
    **Mes de liquidación:** Diciembre 2026
    """)
