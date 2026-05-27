"""
Histórico mensual — comparativo y heatmap.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from helpers.sheets import get_transacciones
from helpers.calc import historico_mensual
from helpers.theme import apply_theme, hero, fmt_q, fmt_q_short, COLORS, style_plotly


st.set_page_config(
    page_title="Histórico · Finanzas",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()


hero(
    eyebrow="📈 Histórico",
    title="Mes a mes",
    subtitle="¿Estamos mejorando o se nos está yendo de las manos?",
)


try:
    df = get_transacciones()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    st.stop()


if df.empty:
    st.markdown("""
    <div style="background: var(--surface); border: 1px dashed var(--border);
                border-radius: 14px; padding: 4rem 1.5rem; text-align: center; margin-top: 2rem;">
        <div style="font-size: 3rem; margin-bottom: 0.8rem;">📊</div>
        <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; color: var(--ink); margin-bottom: 0.5rem;">
            Sin datos históricos
        </div>
        <div style="color: var(--ink-mute);">
            Registra transacciones para ver tendencias mes a mes.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


n_meses = st.slider("Meses a comparar", min_value=2, max_value=12, value=6)
hist = historico_mensual(df, n_meses=n_meses)

if hist.empty:
    st.info("No hay datos suficientes para comparar.")
    st.stop()


st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)


# ============ Gráfica principal ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Flujo mensual
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Ingresos vs egresos</h3>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">', unsafe_allow_html=True)

fig = go.Figure()
fig.add_trace(go.Bar(
    name="Ingresos", x=hist["año_mes_str"], y=hist["INGRESO"],
    marker=dict(color=COLORS["accent"]),
    text=[fmt_q_short(v) for v in hist["INGRESO"]],
    textposition="outside",
    textfont=dict(family="Geist Mono", size=10, color=COLORS["ink_soft"]),
    hovertemplate="<b>%{x}</b><br>Ingresos: Q%{y:,.2f}<extra></extra>",
))
fig.add_trace(go.Bar(
    name="Egresos", x=hist["año_mes_str"], y=hist["EGRESO"],
    marker=dict(color=COLORS["danger"]),
    text=[fmt_q_short(v) for v in hist["EGRESO"]],
    textposition="outside",
    textfont=dict(family="Geist Mono", size=10, color=COLORS["ink_soft"]),
    hovertemplate="<b>%{x}</b><br>Egresos: Q%{y:,.2f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    name="Margen", x=hist["año_mes_str"], y=hist["diferencia"],
    mode="lines+markers", line=dict(color=COLORS["ink"], width=2.5),
    marker=dict(size=8, line=dict(width=2, color="white")),
    hovertemplate="<b>%{x}</b><br>Margen: Q%{y:,.2f}<extra></extra>",
))
fig = style_plotly(fig)
fig.update_layout(
    barmode="group", height=420,
    margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
    yaxis=dict(tickprefix="Q", tickformat=",.0f"),
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
st.markdown('</div>', unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ Tabla resumen estilo cards ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Detalle
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Resumen por mes</h3>
</div>
""", unsafe_allow_html=True)

rows_html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">'
for _, row in hist.iterrows():
    margen = row["diferencia"]
    margen_color = COLORS["accent"] if margen >= 0 else COLORS["danger"]
    margen_signo = "+" if margen >= 0 else ""
    rows_html += f"""
    <div style="background: var(--surface); border: 1px solid var(--border);
                border-radius: 14px; padding: 1.3rem; box-shadow: var(--shadow);">
        <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                    text-transform: uppercase; letter-spacing: 0.1em;
                    color: var(--ink-mute); margin-bottom: 0.6rem;">
            {row['año_mes_str']}
        </div>
        <div style="font-family: 'Fraunces', serif; font-size: 1.6rem; font-weight: 500; color: {margen_color}; margin-bottom: 0.8rem;">
            {margen_signo}{fmt_q(margen)}
        </div>
        <div style="font-size: 0.8rem; color: var(--ink-soft); display: flex; justify-content: space-between;">
            <span>↑ {fmt_q_short(row['INGRESO'])}</span>
            <span>↓ {fmt_q_short(row['EGRESO'])}</span>
        </div>
    </div>
    """
rows_html += '</div>'
st.markdown(rows_html, unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ HEATMAP ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Mapa de calor
    </div>
    <h3 style="margin: 0 0 0.3rem; font-size: 1.3rem;">Egresos por categoría a través del tiempo</h3>
    <p style="color: var(--ink-mute); font-size: 0.9rem; margin: 0;">
        Si una categoría se pone más oscura mes a mes, hay un patrón ahí.
    </p>
</div>
""", unsafe_allow_html=True)

df_eg = df[df["tipo"] == "EGRESO"].copy()
if not df_eg.empty:
    df_eg["año_mes"] = df_eg["fecha"].dt.to_period("M").astype(str)
    pivot = df_eg.pivot_table(
        index="categoria", columns="año_mes",
        values="monto", aggfunc="sum", fill_value=0,
    )
    pivot = pivot.iloc[:, -n_meses:]
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    st.markdown('<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">', unsafe_allow_html=True)

    fig2 = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale=[
            [0, "#FAFAF7"],
            [0.3, COLORS["accent_2"]],
            [0.6, "#7BA89B"],
            [1, COLORS["accent"]],
        ],
        text=[[fmt_q_short(v) if v > 0 else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont={"family": "Geist Mono", "size": 10, "color": COLORS["ink"]},
        hovertemplate="<b>%{y}</b><br>%{x}: Q%{z:,.2f}<extra></extra>",
        showscale=False,
    ))
    fig2 = style_plotly(fig2)
    fig2.update_layout(
        height=max(400, 28 * len(pivot) + 100),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(side="top"),
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("No hay egresos registrados aún.")
