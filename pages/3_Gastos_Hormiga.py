"""
Análisis detallado de gastos hormiga.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from helpers.sheets import get_transacciones
from helpers.calc import filtrar_mes, gastos_hormiga, mes_actual_dt, nombre_mes_es
from helpers.theme import apply_theme, hero, fmt_q, fmt_q_short, COLORS, style_plotly


st.set_page_config(
    page_title="Gastos Hormiga · Finanzas",
    page_icon="🐜",
    layout="wide",
    initial_sidebar_state="auto",
)
apply_theme()


hero(
    eyebrow="🐜 Gastos hormiga",
    title="Lo pequeño que se acumula",
    subtitle="Los gastos chiquitos individualmente no se notan. Sumados al mes, son cuotas completas de tarjeta.",
)


# Selector de mes
año_actual, mes_actual = mes_actual_dt()
c1, c2 = st.columns([1, 2])
with c1:
    año_sel = st.number_input("Año", min_value=2025, max_value=2030, value=año_actual, step=1)
with c2:
    mes_sel = st.selectbox("Mes", options=list(range(1, 13)),
                           index=mes_actual - 1, format_func=nombre_mes_es)

try:
    df = get_transacciones()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    st.stop()


sub = filtrar_mes(df, año_sel, mes_sel)
hormigas = sub[(sub["tipo"] == "EGRESO") & (sub["es_hormiga"])].copy()

if hormigas.empty:
    st.markdown(f"""
    <div style="background: var(--surface); border: 1px dashed var(--border);
                border-radius: 14px; padding: 4rem 1.5rem; text-align: center; margin-top: 2rem;">
        <div style="font-size: 3rem; margin-bottom: 0.8rem;">🌱</div>
        <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; color: var(--ink); margin-bottom: 0.5rem;">
            Mes limpio
        </div>
        <div style="color: var(--ink-mute); max-width: 35ch; margin: 0 auto;">
            No hay gastos hormiga registrados en {nombre_mes_es(mes_sel)} {año_sel}.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ============ MÉTRICAS BIG ============
total = hormigas["monto"].sum()
n = len(hormigas)
promedio = hormigas["monto"].mean()
egresos_totales = sub[sub["tipo"] == "EGRESO"]["monto"].sum()
porcentaje = (total / egresos_totales * 100) if egresos_totales else 0
proyectado_anual = total * 12

st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

# Card hero con el total
st.markdown(f"""
<div style="background: linear-gradient(135deg, {COLORS['warn_soft']} 0%, #fef9ec 100%);
            border: 1px solid rgba(184,134,44,0.2);
            border-radius: 20px; padding: 2.5rem 2rem; text-align: center;
            position: relative; overflow: hidden;">
    <div style="position: absolute; top: -30px; right: -30px; font-size: 8rem; opacity: 0.05;">🐜</div>
    <div style="position: relative;">
        <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                    text-transform: uppercase; letter-spacing: 0.14em;
                    color: {COLORS['warn']}; margin-bottom: 0.6rem;">
            Total en {nombre_mes_es(mes_sel)}
        </div>
        <div style="font-family: 'Fraunces', serif; font-size: clamp(2.8rem, 8vw, 4rem);
                    font-weight: 500; line-height: 1; letter-spacing: -0.03em; color: var(--ink);">
            {fmt_q(total)}
        </div>
        <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 1.5rem; flex-wrap: wrap;">
            <div>
                <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 500; color: var(--ink);">{n}</div>
                <div style="font-size: 0.78rem; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.08em;">Compras</div>
            </div>
            <div>
                <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 500; color: var(--ink);">{fmt_q_short(promedio)}</div>
                <div style="font-size: 0.78rem; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.08em;">Promedio</div>
            </div>
            <div>
                <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 500; color: {COLORS['warn']};">{porcentaje:.1f}%</div>
                <div style="font-size: 0.78rem; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.08em;">Del total egresos</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ Por categoría ============
agrupado = gastos_hormiga(df, año_sel, mes_sel)

st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Distribución
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Por categoría</h3>
</div>
""", unsafe_allow_html=True)

cA, cB = st.columns([1, 1])
with cA:
    st.markdown('<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=agrupado["categoria"], values=agrupado["total"],
        hole=0.55,
        marker=dict(colors=[COLORS["warn"], COLORS["accent"], COLORS["ink_soft"], COLORS["danger"], COLORS["ink_mute"], "#D4B16A", "#7BA89B"]),
        textfont=dict(family="Geist", size=11),
        textposition="outside",
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Q%{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig = style_plotly(fig)
    fig.update_layout(
        height=320,
        showlegend=False,
        margin=dict(l=10, r=10, t=20, b=10),
        annotations=[dict(
            text=f"<b>{fmt_q_short(total)}</b><br><span style='font-size:0.7rem; color:{COLORS['ink_mute']};'>total</span>",
            x=0.5, y=0.5, font=dict(family="Fraunces", size=20, color=COLORS["ink"]),
            showarrow=False,
        )],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with cB:
    rows_html = '<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; box-shadow: var(--shadow); overflow: hidden;">'
    for i, (_, row) in enumerate(agrupado.iterrows()):
        is_last = i == len(agrupado) - 1
        border = "" if is_last else "border-bottom: 1px solid var(--border);"
        pct = (row["total"] / total * 100)
        rows_html += f"""
        <div style="padding: 1rem 1.4rem; {border}">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.4rem;">
                <span style="font-weight: 500; color: var(--ink);">{row['categoria']}</span>
                <span style="font-family: 'Fraunces', serif; font-size: 1.1rem; font-weight: 500;">{fmt_q(row['total'])}</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--ink-mute); margin-bottom: 0.4rem;">
                <span>{int(row['conteo'])} compras · prom. {fmt_q(row['promedio'])}</span>
                <span>{pct:.1f}%</span>
            </div>
            <div style="background: var(--accent-2); height: 4px; border-radius: 100px; overflow: hidden;">
                <div style="background: {COLORS['warn']}; height: 100%; width: {pct}%; border-radius: 100px;"></div>
            </div>
        </div>
        """
    rows_html += '</div>'
    st.markdown(rows_html, unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ Insight de proyección anual ============
cuotas_equivalentes = proyectado_anual / 5500
st.markdown(f"""
<div style="background: linear-gradient(135deg, {COLORS['ink']} 0%, #1a3530 100%);
            border-radius: 20px; padding: 2rem; color: white;
            box-shadow: 0 4px 20px rgba(15,31,28,0.1);">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.7rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: {COLORS['accent_2']}; opacity: 0.7; margin-bottom: 0.6rem;">
        💡 Perspectiva
    </div>
    <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; line-height: 1.4; font-weight: 400;">
        Si este ritmo se mantiene todo el año, gastarán <b style="color: {COLORS['accent_2']};">{fmt_q_short(proyectado_anual)}</b>
        solo en gastos hormiga.
    </div>
    <div style="margin-top: 0.8rem; font-size: 0.95rem; opacity: 0.8;">
        Equivale a <b>{cuotas_equivalentes:.1f} cuotas</b> de las que están pagando de la tarjeta.
    </div>
</div>
""", unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ Detalle transacciones ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Detalle
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Cada gasto individual</h3>
</div>
""", unsafe_allow_html=True)

hormigas_sorted = hormigas.sort_values("fecha", ascending=False)

rows_html = '<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; box-shadow: var(--shadow); overflow: hidden;">'
for i, (_, row) in enumerate(hormigas_sorted.iterrows()):
    is_last = i == len(hormigas_sorted) - 1
    border = "" if is_last else "border-bottom: 1px solid var(--border);"
    fecha_str = row["fecha"].strftime("%d %b") if pd.notna(row["fecha"]) else "—"
    rows_html += f"""
    <div style="padding: 0.9rem 1.4rem; display: flex; align-items: center; gap: 1rem; {border}">
        <div style="width: 32px; height: 32px; border-radius: 50%; background: {COLORS['warn_soft']};
                    display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 0.9rem;">
            🐜
        </div>
        <div style="flex: 1; min-width: 0;">
            <div style="font-weight: 500; color: var(--ink); font-size: 0.92rem; margin-bottom: 0.1rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                {row['descripcion']}
            </div>
            <div style="font-size: 0.78rem; color: var(--ink-mute);">
                {row['categoria']} · {row['persona']} · {fecha_str}
            </div>
        </div>
        <div style="font-family: 'Fraunces', serif; font-size: 1.05rem; font-weight: 500; color: var(--ink); white-space: nowrap;">
            {fmt_q(row['monto'])}
        </div>
    </div>
    """
rows_html += '</div>'
st.markdown(rows_html, unsafe_allow_html=True)
