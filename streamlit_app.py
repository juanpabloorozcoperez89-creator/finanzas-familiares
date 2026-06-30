"""
Finanzas Familiares · Pablo & Maite
Dashboard principal — diseño fintech refinado.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

from helpers.sheets import (
    get_transacciones, get_plan, get_config, clear_all_caches
)
from helpers.calc import (
    resumen_mes, gastos_hormiga, egresos_por_categoria,
    calcular_saldo_actual_tarjeta, mes_actual_dt, nombre_mes_es,
)
from helpers.theme import apply_theme, hero, fmt_q, fmt_q_short, COLORS, style_plotly, render_html


st.set_page_config(
    page_title="Finanzas · Pablo & Maite",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="auto",
)
apply_theme()


# ============ Sidebar ============
año_actual, mes_actual = mes_actual_dt()
with st.sidebar:
    st.markdown("""
    <div style="padding: 0 1rem 1.5rem; border-bottom: 1px solid var(--border); margin-bottom: 1.5rem;">
        <div style="font-family: 'Fraunces', serif; font-size: 1.3rem; font-weight: 500; color: var(--ink); letter-spacing: -0.01em;">
            Finanzas
        </div>
        <div style="font-size: 0.78rem; color: var(--ink-mute); margin-top: 0.15rem;">
            Pablo · Maite
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Periodo**")
    año_sel = st.number_input("Año", min_value=2025, max_value=2030, value=año_actual, step=1, label_visibility="collapsed")
    mes_sel = st.selectbox("Mes", options=list(range(1, 13)),
                            index=mes_actual - 1, format_func=nombre_mes_es, label_visibility="collapsed")
    st.markdown("<div style='margin: 1rem 0'></div>", unsafe_allow_html=True)
    if st.button("↻ Refrescar datos", use_container_width=True):
        clear_all_caches()
        st.rerun()


# ============ Cargar datos ============
try:
    df = get_transacciones()
    plan = get_plan()
    config = get_config()
except Exception as e:
    st.error(f"**Error conectando a Google Sheets**\n\n{type(e).__name__}: {e}")
    import traceback
    with st.expander("Ver detalles técnicos"):
        st.code(traceback.format_exc())
    st.stop()


# ============ HERO ============
hero(
    eyebrow=f"{nombre_mes_es(mes_sel)} {año_sel}",
    title="Buenos días, Pablo.",
    subtitle="Aquí está cómo van las finanzas familiares este mes.",
)


# ============ MÉTRICAS DEL MES ============
resumen = resumen_mes(df, año_sel, mes_sel)
meta_ingresos = config.get("meta_ingresos_mes", 26007.95)

c1, c2, c3, c4 = st.columns(4)
with c1:
    pct = ((resumen["ingresos"] / meta_ingresos * 100) - 100) if meta_ingresos else None
    st.metric(
        "Ingresos",
        fmt_q(resumen["ingresos"]),
        delta=f"{pct:+.1f}% vs meta" if pct is not None else None,
    )
with c2:
    st.metric("Egresos", fmt_q(resumen["egresos"]))
with c3:
    diff = resumen["diferencia"]
    st.metric(
        "Margen",
        fmt_q(diff),
        delta=("Positivo" if diff >= 0 else "Negativo"),
        delta_color="normal" if diff >= 0 else "inverse",
    )
with c4:
    st.metric("Movimientos", resumen["n_transacciones"])


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ PLAN TARJETA (HERO CARD) ============
saldo_inicial = config.get("saldo_inicial_tarjeta", 30990.85)
info = calcular_saldo_actual_tarjeta(plan, saldo_inicial)
avance = (info["total_pagado"] / saldo_inicial * 100) if saldo_inicial else 0

proximo_html = f'<span>Próxima: {fmt_q(info["proximo_mes"]["pago_planeado"])} · {info["proximo_mes"]["mes_label"]}</span>' if info['proximo_mes'] else '<span>✓ Plan completado</span>'

st.markdown(f"""
<div style="background: linear-gradient(135deg, {COLORS['ink']} 0%, #1a3530 100%);
            border-radius: 20px; padding: 2rem 2.2rem; color: white;
            box-shadow: 0 4px 24px rgba(15,31,28,0.12);
            position: relative; overflow: hidden;">
    <div style="position: absolute; top: -40px; right: -40px; width: 200px; height: 200px;
                background: radial-gradient(circle, rgba(10,110,78,0.4) 0%, transparent 70%);
                border-radius: 50%;"></div>
    <div style="position: relative;">
        <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                    text-transform: uppercase; letter-spacing: 0.14em;
                    color: {COLORS['accent_2']}; opacity: 0.7; margin-bottom: 0.4rem;">
            Plan de pago · Tarjeta de crédito
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 2rem; align-items: flex-end; margin-bottom: 1.2rem;">
            <div>
                <div style="font-family: 'Fraunces', serif; font-size: 2.5rem; font-weight: 500;
                            line-height: 1; letter-spacing: -0.025em;">
                    {fmt_q(info['saldo_actual'])}
                </div>
                <div style="font-size: 0.85rem; opacity: 0.7; margin-top: 0.4rem;">
                    Saldo restante de {fmt_q(saldo_inicial)}
                </div>
            </div>
            <div style="margin-left: auto; text-align: right;">
                <div style="font-family: 'Geist Mono', monospace; font-size: 0.7rem;
                            text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.6;">
                    Avance
                </div>
                <div style="font-family: 'Fraunces', serif; font-size: 1.6rem; font-weight: 500;">
                    {avance:.1f}%
                </div>
            </div>
        </div>
        <div style="background: rgba(255,255,255,0.1); height: 6px; border-radius: 100px; overflow: hidden;">
            <div style="background: {COLORS['accent']}; height: 100%;
                        width: {min(avance, 100)}%; border-radius: 100px;
                        transition: width 0.5s ease;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 1rem; font-size: 0.82rem; opacity: 0.7; flex-wrap: wrap; gap: 0.5rem;">
            <span>{info['meses_pagados']} de {len(plan)} cuotas pagadas</span>
            {proximo_html}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ GASTOS HORMIGA + EGRESOS POR CATEGORÍA ============
cA, cB = st.columns([1, 1.2])

with cA:
    st.markdown("""
    <div style="margin-bottom: 1rem;">
        <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                    text-transform: uppercase; letter-spacing: 0.14em;
                    color: var(--accent); margin-bottom: 0.4rem;">
            🐜 Gastos hormiga
        </div>
        <h3 style="margin: 0; font-size: 1.3rem;">Lo que se va sin sentirlo</h3>
    </div>
    """, unsafe_allow_html=True)

    hormiga_df = gastos_hormiga(df, año_sel, mes_sel)
    if hormiga_df.empty:
        st.markdown("""
        <div style="background: var(--surface); border: 1px dashed var(--border);
                    border-radius: 14px; padding: 2.5rem 1.5rem; text-align: center;
                    color: var(--ink-mute);">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🌱</div>
            <div style="font-size: 0.92rem;">Aún no hay gastos hormiga este mes.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        total_hormiga = hormiga_df["total"].sum()
        n_hormiga = int(hormiga_df["conteo"].sum())

        bars_html = ""
        for _, row in hormiga_df.head(6).iterrows():
            barpct = (row["total"] / hormiga_df["total"].max() * 100)
            bars_html += f"""
            <div style="margin-bottom: 0.85rem;">
                <div style="display: flex; justify-content: space-between; font-size: 0.88rem; margin-bottom: 0.3rem;">
                    <span style="color: var(--ink);">{row['categoria']}</span>
                    <span style="font-family: 'Geist Mono', monospace; color: var(--ink-soft);">{fmt_q(row['total'])} · {int(row['conteo'])}×</span>
                </div>
                <div style="background: var(--accent-2); height: 5px; border-radius: 100px; overflow: hidden;">
                    <div style="background: var(--accent); height: 100%; width: {barpct}%; border-radius: 100px;"></div>
                </div>
            </div>
            """

        st.markdown(f"""
        <div style="background: var(--surface); border: 1px solid var(--border);
                    border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 1.2rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
                <div>
                    <div style="font-size: 0.78rem; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.08em;">Acumulado</div>
                    <div style="font-family: 'Fraunces', serif; font-size: 2rem; font-weight: 500; color: var(--ink); letter-spacing: -0.02em; margin-top: 0.2rem;">
                        {fmt_q(total_hormiga)}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.78rem; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.08em;">Compras</div>
                    <div style="font-family: 'Fraunces', serif; font-size: 2rem; font-weight: 500; color: var(--accent);">
                        {n_hormiga}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        # Render bars separately to avoid markdown parser confusion
        render_html(bars_html)


with cB:
    st.markdown("""
    <div style="margin-bottom: 1rem;">
        <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                    text-transform: uppercase; letter-spacing: 0.14em;
                    color: var(--accent); margin-bottom: 0.4rem;">
            Distribución
        </div>
        <h3 style="margin: 0; font-size: 1.3rem;">A dónde se fue cada quetzal</h3>
    </div>
    """, unsafe_allow_html=True)

    egresos_cat = egresos_por_categoria(df, año_sel, mes_sel)
    if egresos_cat.empty:
        st.markdown("""
        <div style="background: var(--surface); border: 1px dashed var(--border);
                    border-radius: 14px; padding: 2.5rem 1.5rem; text-align: center;
                    color: var(--ink-mute);">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📭</div>
            <div style="font-size: 0.92rem;">Sin egresos registrados aún.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">', unsafe_allow_html=True)

        top = egresos_cat.head(8)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=top["total"], y=top["categoria"], orientation="h",
            marker=dict(color=COLORS["accent"]),
            text=[fmt_q_short(v) for v in top["total"]],
            textposition="outside",
            textfont=dict(family="Geist Mono", size=11, color=COLORS["ink_soft"]),
            hovertemplate="<b>%{y}</b><br>Q%{x:,.2f}<extra></extra>",
        ))
        fig = style_plotly(fig)
        fig.update_layout(
            height=max(280, 38 * len(top) + 60),
            showlegend=False,
            margin=dict(l=10, r=60, t=10, b=10),
            yaxis=dict(categoryorder="total ascending", showgrid=False),
            xaxis=dict(showticklabels=False, showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ ÚLTIMAS TRANSACCIONES ============
st.markdown("""
<div style="margin-bottom: 1rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Actividad reciente
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Últimos movimientos</h3>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.markdown("""
    <div style="background: var(--surface); border: 1px dashed var(--border);
                border-radius: 14px; padding: 3rem 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">✨</div>
        <div style="font-family: 'Fraunces', serif; font-size: 1.2rem; color: var(--ink); margin-bottom: 0.3rem;">
            Empieza tu historial
        </div>
        <div style="color: var(--ink-mute); font-size: 0.9rem; max-width: 30ch; margin: 0 auto;">
            Ve a la página <b style="color: var(--accent);">Registrar</b> para anotar tu primer movimiento.
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    ult = df.sort_values("fecha", ascending=False).head(8).copy()

    rows_html = ""
    for i, (_, row) in enumerate(ult.iterrows()):
        is_ingreso = row["tipo"] == "INGRESO"
        is_last = i == len(ult) - 1
        signo = "+" if is_ingreso else "−"
        color = COLORS["accent"] if is_ingreso else COLORS["ink"]
        bullet = "↑" if is_ingreso else "↓"
        bullet_bg = COLORS["accent_2"] if is_ingreso else "#F5F2EC"
        bullet_color = COLORS["accent"] if is_ingreso else COLORS["ink_soft"]
        fecha_str = row["fecha"].strftime("%d %b") if pd.notna(row["fecha"]) else "—"
        hormiga_tag = ' <span style="background: var(--warn-soft); color: var(--warn); padding: 0.1rem 0.5rem; border-radius: 100px; font-size: 0.7rem; font-weight: 500; margin-left: 0.3rem;">🐜 hormiga</span>' if row.get("es_hormiga") else ''
        border = "" if is_last else "border-bottom: 1px solid var(--border);"

        rows_html += f"""
        <div style="padding: 1rem 1.4rem; display: flex; align-items: center; gap: 1rem; {border}">
            <div style="width: 36px; height: 36px; border-radius: 50%;
                        background: {bullet_bg}; color: {bullet_color};
                        display: flex; align-items: center; justify-content: center;
                        font-weight: 600; font-size: 1rem; flex-shrink: 0;">
                {bullet}
            </div>
            <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 500; color: var(--ink); font-size: 0.95rem; margin-bottom: 0.15rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {row['descripcion']}{hormiga_tag}
                </div>
                <div style="font-size: 0.8rem; color: var(--ink-mute); display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <span>{row['categoria']}</span>
                    <span>·</span>
                    <span>{row['persona']}</span>
                    <span>·</span>
                    <span>{fecha_str}</span>
                </div>
            </div>
            <div style="font-family: 'Fraunces', serif; font-size: 1.15rem; font-weight: 500; color: {color}; white-space: nowrap;">
                {signo}{fmt_q(row['monto'])}
            </div>
        </div>
        """

    render_html(f'<div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);overflow:hidden;">{rows_html}</div>')

st.markdown("<div style='height: 3rem'></div>", unsafe_allow_html=True)
