"""
Plan de pago tarjeta — rediseñado con timeline visual.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

from helpers.sheets import get_plan, get_config, update_pago_real
from helpers.calc import calcular_saldo_actual_tarjeta
from helpers.theme import apply_theme, hero, fmt_q, fmt_q_short, COLORS, style_plotly, render_html


st.set_page_config(
    page_title="Plan Tarjeta · Finanzas",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="auto",
)
apply_theme()


try:
    plan = get_plan()
    config = get_config()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    import traceback
    with st.expander("Ver detalles técnicos"):
        st.code(traceback.format_exc())
    st.stop()

if plan.empty:
    st.warning("La hoja `Plan_Tarjeta` está vacía.")
    st.stop()


saldo_inicial = config.get("saldo_inicial_tarjeta", 37661.81)
info = calcular_saldo_actual_tarjeta(plan, saldo_inicial)
# Avance basado en capital reducido (coherente con saldo_actual del próximo mes)
avance = ((saldo_inicial - info["saldo_actual"]) / saldo_inicial * 100) if saldo_inicial else 0


hero(
    eyebrow="💳 Plan de pago",
    title="Tarjeta de crédito",
    subtitle="10 meses para quedar libre. Cada cuota cuenta.",
)


# ============ HERO CARD oscura con el saldo ============
proximo_html = f'<div style="font-size: 0.95rem; opacity: 0.85;"><b>Próxima cuota:</b> {fmt_q(info["proximo_mes"]["pago_planeado"])} · {info["proximo_mes"]["mes_label"]}</div>' if info['proximo_mes'] else '<div style="font-size: 0.95rem; opacity: 0.85;">🎉 Plan completado</div>'

st.markdown(f"""
<div style="background: linear-gradient(135deg, {COLORS['ink']} 0%, #1a3530 100%);
            border-radius: 20px; padding: 2.5rem; color: white;
            box-shadow: 0 4px 24px rgba(15,31,28,0.12);
            position: relative; overflow: hidden;">
    <div style="position: absolute; top: -60px; right: -60px; width: 250px; height: 250px;
                background: radial-gradient(circle, rgba(10,110,78,0.35) 0%, transparent 70%);
                border-radius: 50%;"></div>
    <div style="position: absolute; bottom: -80px; left: -60px; width: 220px; height: 220px;
                background: radial-gradient(circle, rgba(10,110,78,0.15) 0%, transparent 70%);
                border-radius: 50%;"></div>
    <div style="position: relative;">
        <div style="font-family: 'Geist Mono', monospace; font-size: 0.7rem;
                    text-transform: uppercase; letter-spacing: 0.16em;
                    color: {COLORS['accent_2']}; opacity: 0.6; margin-bottom: 0.6rem;">
            Saldo restante
        </div>
        <div style="font-family: 'Fraunces', serif; font-size: clamp(2.5rem, 7vw, 3.8rem);
                    font-weight: 500; line-height: 1; letter-spacing: -0.025em; margin-bottom: 1.5rem;">
            {fmt_q(info['saldo_actual'])}
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 2.5rem; margin-bottom: 1.5rem;">
            <div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.5; margin-bottom: 0.3rem;">Pagado</div>
                <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 500;">{fmt_q(info['total_pagado'])}</div>
            </div>
            <div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.5; margin-bottom: 0.3rem;">Avance</div>
                <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 500; color: {COLORS['accent_2']};">{avance:.1f}%</div>
            </div>
            <div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.5; margin-bottom: 0.3rem;">Cuotas</div>
                <div style="font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 500;">{info['meses_pagados']}/{len(plan)}</div>
            </div>
        </div>
        <div style="background: rgba(255,255,255,0.1); height: 8px; border-radius: 100px; overflow: hidden; margin-bottom: 1rem;">
            <div style="background: linear-gradient(90deg, {COLORS['accent']} 0%, #2ba078 100%); height: 100%;
                        width: {min(avance, 100)}%; border-radius: 100px;
                        transition: width 0.5s ease;"></div>
        </div>
        {proximo_html}
    </div>
</div>
""", unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ ACCIÓN: marcar pago ============
if info["proximo_mes"]:
    prox = info["proximo_mes"]
    cL, cR = st.columns([1.2, 1])
    with cL:
        st.markdown(f"""
        <div style="background: var(--surface); border: 1px solid var(--border);
                    border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">
            <div style="font-family: 'Geist Mono', monospace; font-size: 0.7rem;
                        text-transform: uppercase; letter-spacing: 0.14em;
                        color: var(--accent); margin-bottom: 0.6rem;">
                Acción pendiente
            </div>
            <h3 style="margin: 0 0 0.4rem; font-size: 1.3rem;">Pago de {prox['mes_label']}</h3>
            <div style="font-size: 0.92rem; color: var(--ink-soft); margin-bottom: 1rem;">
                {prox.get('notas', 'Cuota base mensual')}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; padding-top: 1rem; border-top: 1px solid var(--border);">
                <span style="color: var(--ink-mute); font-size: 0.85rem;">Monto planeado</span>
                <span style="font-family: 'Fraunces', serif; font-size: 1.8rem; font-weight: 500; color: var(--ink);">
                    {fmt_q(prox['pago_planeado'])}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cR:
        with st.expander(f"✓ Marcar como pagado", expanded=False):
            with st.form(f"pago_{int(prox['mes_num'])}"):
                pago_real = st.number_input(
                    "Monto pagado real",
                    value=float(prox['pago_planeado']),
                    step=100.0, format="%.2f",
                )
                fecha_pago = st.date_input("Fecha de pago", value=date.today(), format="DD/MM/YYYY")
                notas_nuevas = st.text_input("Notas (opcional)", value=prox.get('notas', ''))
                if st.form_submit_button("Confirmar pago", type="primary", use_container_width=True):
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
                        st.error(f"{type(e).__name__}: {e}")
else:
    st.markdown("""
    <div style="background: var(--accent-2); border: 1px solid rgba(10,110,78,0.2);
                border-radius: 14px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎉</div>
        <h3 style="margin: 0; color: var(--accent);">¡Felicidades, plan completado!</h3>
        <p style="margin: 0.5rem 0 0; color: var(--ink-soft);">
            Liberaron la deuda de la tarjeta. Tiempo de empezar a ahorrar.
        </p>
    </div>
    """, unsafe_allow_html=True)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ TIMELINE de cuotas ============
st.markdown("""
<div style="margin-bottom: 1.2rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Calendario
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">10 meses al cero</h3>
</div>
""", unsafe_allow_html=True)


# Construir todo el HTML en una sola línea (sin saltos de línea internos)
# Esto evita que el parser de Streamlit confunda HTML con markdown.
timeline_parts = ['<div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);overflow:hidden;">']

for i, (_, row) in enumerate(plan.iterrows()):
    is_paid = pd.notna(row["pago_real"])
    is_last = i == len(plan) - 1
    is_next = info["proximo_mes"] is not None and int(row["mes_num"]) == int(info["proximo_mes"]["mes_num"])

    if is_paid:
        bullet_color = COLORS["accent"]
        bullet_bg = COLORS["accent_2"]
        bullet_icon = "✓"
        status = f"Pagado · {row['fecha_pago_real']}"
        status_color = COLORS["accent"]
    elif is_next:
        bullet_color = COLORS["warn"]
        bullet_bg = COLORS["warn_soft"]
        bullet_icon = "•"
        status = "Próximo pago"
        status_color = COLORS["warn"]
    else:
        bullet_color = COLORS["ink_mute"]
        bullet_bg = "#F5F2EC"
        bullet_icon = "○"
        status = "Pendiente"
        status_color = COLORS["ink_mute"]

    border_css = "" if is_last else "border-bottom:1px solid var(--border);"
    pago_real_extra = f' · <span style="color:var(--ink-mute);">Real: {fmt_q(row["pago_real"])}</span>' if is_paid else ''

    # Construir cada fila SIN saltos de línea internos para evitar parsing como markdown
    row_html = (
        f'<div style="padding:1.2rem 1.4rem;display:flex;align-items:center;gap:1.2rem;{border_css}">'
        f'<div style="width:38px;height:38px;border-radius:50%;background:{bullet_bg};color:{bullet_color};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.1rem;flex-shrink:0;border:2px solid {bullet_color};">{bullet_icon}</div>'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:baseline;gap:0.6rem;margin-bottom:0.2rem;flex-wrap:wrap;">'
        f'<span style="font-family:Fraunces,serif;font-size:1.1rem;font-weight:500;">{row["mes_label"]}</span>'
        f'<span style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;color:{status_color};font-weight:500;">{status}</span>'
        f'</div>'
        f'<div style="font-size:0.82rem;color:var(--ink-mute);">Saldo inicial: {fmt_q(row["saldo_inicial_plan"])}{pago_real_extra}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-family:Fraunces,serif;font-size:1.3rem;font-weight:500;color:var(--ink);">{fmt_q(row["pago_planeado"])}</div>'
        f'<div style="font-size:0.72rem;color:var(--ink-mute);text-transform:uppercase;letter-spacing:0.06em;">cuota #{int(row["mes_num"])}</div>'
        f'</div>'
        f'</div>'
    )
    timeline_parts.append(row_html)

timeline_parts.append('</div>')
timeline_html = ''.join(timeline_parts)
render_html(timeline_html)


st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)


# ============ GRÁFICA evolución del saldo ============
st.markdown("""
<div style="margin-bottom: 1.2rem;">
    <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                text-transform: uppercase; letter-spacing: 0.14em;
                color: var(--accent); margin-bottom: 0.4rem;">
        Proyección
    </div>
    <h3 style="margin: 0; font-size: 1.3rem;">Cómo bajará el saldo</h3>
</div>
""", unsafe_allow_html=True)

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
    s_p = max(0, s_p + interes + iva_c - row["pago_planeado"])
    saldo_proyectado.append(s_p)

    if pd.notna(row["pago_real"]):
        interes_r = s_r * tasa
        iva_r = interes_r * iva
        s_r = max(0, s_r + interes_r + iva_r - row["pago_real"])
        saldo_real.append(s_r)
    else:
        saldo_real.append(None)
    labels.append(row["mes_label"])

st.markdown('<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">', unsafe_allow_html=True)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=labels, y=saldo_proyectado, name="Plan",
    mode="lines+markers",
    line=dict(color=COLORS["ink_mute"], dash="dot", width=2),
    marker=dict(size=6),
    fill="tozeroy", fillcolor="rgba(139,152,147,0.06)",
    hovertemplate="<b>%{x}</b><br>Plan: Q%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=labels, y=saldo_real, name="Real",
    mode="lines+markers",
    line=dict(color=COLORS["accent"], width=3),
    marker=dict(size=8, line=dict(width=2, color="white")),
    hovertemplate="<b>%{x}</b><br>Real: Q%{y:,.0f}<extra></extra>",
))
fig = style_plotly(fig)
fig.update_layout(
    height=340,
    margin=dict(l=10, r=10, t=10, b=10),
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
    yaxis=dict(tickprefix="Q", tickformat=",.0f"),
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
st.markdown('</div>', unsafe_allow_html=True)


st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)

with st.expander("Detalles del plan"):
    st.markdown(f"""
    **Plan recalculado al 30 de junio 2026 con base en:**

    · Saldo al inicio del plan (Jun 2026): **{fmt_q(saldo_inicial)}**
    · Pago mensual fijo: **Q 5,500** todos los meses (sin bonos)
    · Tasa de interés implícita observada en últimos 11 ciclos: **3.75% mensual** + IVA 12%
    · Cargos mensuales del banco (intereses + IVA + visacuota + gestión): **~Q 2,000/mes** (decrecientes)
    · **Marzo 2027:** cierre con cuota final de **Q 3,573.68**

    **Total a pagar:** ~Q 53,074 · **Cargos del banco proyectados:** ~Q 15,412 · **Liquidación:** marzo 2027

    > ⚠️ Este plan asume pago fijo Q5,500/mes sin bonos y SIN finiquito negociado.
    > Si Banco Industrial acepta negociación de intereses con pago de contado, el plan
    > colapsa a un solo pago y las cuotas mensuales pasan a ser pagos a la persona
    > prestamista (no al banco).
    """)
