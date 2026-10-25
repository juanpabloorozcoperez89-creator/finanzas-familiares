"""
Plan de pago de la tarjeta — saldo REAL del banco, simulador y plan mensual.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from helpers.sheets import get_plan, get_config, get_movs_tarjeta, update_pago_real, replace_plan, upsert_config
from helpers.estado_cuenta import proyectar, pago_para_liquidar_en
from helpers.calc import (
    calcular_saldo_actual_tarjeta, situacion_tarjeta, hallazgos, mes_corto, fecha_larga, hoy_gt,
)
from helpers.theme import (
    apply_theme, hero, fmt_q, fmt_q_short, COLORS, style_plotly, render_html,
    section, spacer, alert, kpi_row, esc,
)


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
    movs = get_movs_tarjeta()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    import traceback
    with st.expander("Ver detalles técnicos"):
        st.code(traceback.format_exc())
    st.stop()


pago_cfg = float(config.get("pago_mensual_tarjeta", 5500) or 5500)
sit = situacion_tarjeta(movs, config, pago_mensual=pago_cfg)

hero(
    eyebrow="💳 Plan de pago",
    title="Tarjeta de crédito",
    subtitle="Saldo real del banco, a dónde se va cada cuota y cuándo quedan libres.",
)

if not sit["hay_datos"]:
    alert("info", "Todavía no hay estados de cuenta importados",
          "Sin ellos la app solo puede mostrar el plan teórico. Importalos en la página "
          "<b>Estados de Cuenta</b> para ver el saldo real y la proyección correcta.")
    st.page_link("pages/6_Estados_de_Cuenta.py", label="Ir a Estados de Cuenta", icon="🏦")
    spacer(1.5)


# =====================================================================
# HERO con saldo real
# =====================================================================
if sit["hay_datos"]:
    esc_base = sit["proyeccion"]
    libre_txt = (f"Último pago en {mes_corto(esc_base.fecha_liquidacion - pd.DateOffset(months=1))}"
                 if esc_base.liquidado else "Con este pago la deuda no se liquida")
    avance = max(0.0, min(1.0, sit["avance"]))
    fecha_pago = fecha_larga(sit["fecha_pago"]) if sit.get("fecha_pago") else "—"
    mora = sit.get("saldo_mora") or 0

    render_html(f"""
    <div style="background:linear-gradient(135deg,{COLORS['ink']} 0%,#1a3530 100%);border-radius:20px;
                padding:2.3rem;color:white;box-shadow:0 4px 24px rgba(15,31,28,0.12);position:relative;overflow:hidden;">
        <div style="position:absolute;top:-60px;right:-60px;width:250px;height:250px;
                    background:radial-gradient(circle,rgba(10,110,78,0.35) 0%,transparent 70%);border-radius:50%;"></div>
        <div style="position:relative;">
            <div style="font-family:'Geist Mono',monospace;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.16em;
                        color:{COLORS['accent_2']};opacity:0.65;margin-bottom:0.6rem;">Saldo real al corte del {fecha_larga(sit['corte'])}</div>
            <div style="font-family:'Fraunces',serif;font-size:clamp(2.4rem,7vw,3.6rem);font-weight:500;line-height:1;
                        letter-spacing:-0.025em;margin-bottom:1.4rem;">{fmt_q(sit['saldo'])}</div>
            <div style="display:flex;flex-wrap:wrap;gap:2.2rem;margin-bottom:1.4rem;">
                <div><div style="font-family:'Geist Mono',monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;opacity:0.55;">Pago mínimo</div>
                     <div style="font-family:'Fraunces',serif;font-size:1.3rem;">{fmt_q(sit.get('pago_minimo'))}</div>
                     <div style="font-size:0.78rem;opacity:0.6;">vence {fecha_pago}</div></div>
                <div><div style="font-family:'Geist Mono',monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;opacity:0.55;">Disponible</div>
                     <div style="font-family:'Fraunces',serif;font-size:1.3rem;">{fmt_q(sit.get('disponible'))}</div>
                     <div style="font-size:0.78rem;opacity:0.6;">de {fmt_q_short(sit.get('limite'))}</div></div>
                <div><div style="font-family:'Geist Mono',monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;opacity:0.55;">Tasa real</div>
                     <div style="font-family:'Fraunces',serif;font-size:1.3rem;">{sit['tasa']:.2%}</div>
                     <div style="font-size:0.78rem;opacity:0.6;">mensual · ≈{sit['tasa'] * 12:.0%} anual</div></div>
                <div><div style="font-family:'Geist Mono',monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;opacity:0.55;">Pagando {fmt_q_short(pago_cfg)}/mes</div>
                     <div style="font-family:'Fraunces',serif;font-size:1.3rem;color:{COLORS['accent_2']};">{libre_txt}</div>
                     <div style="font-size:0.78rem;opacity:0.6;">{esc_base.meses} pagos más · {fmt_q_short(esc_base.total_intereses)} de intereses</div></div>
            </div>
            <div style="background:rgba(255,255,255,0.1);height:8px;border-radius:100px;overflow:hidden;margin-bottom:0.6rem;">
                <div style="background:linear-gradient(90deg,{COLORS['accent']} 0%,#2ba078 100%);height:100%;width:{avance * 100:.1f}%;border-radius:100px;"></div>
            </div>
            <div style="font-size:0.82rem;opacity:0.7;">{avance:.0%} pagado desde el máximo de {fmt_q_short(sit['pico'])}</div>
        </div>
    </div>""")

    if mora > 0:
        spacer(1)
        alert("danger", f"Saldo en mora: {fmt_q(mora)}",
              f"Pagalo antes del {fecha_pago} para evitar interés moratorio y Q168 de gestión de cobro.")

    spacer(2.5)

    # =================================================================
    # ¿A dónde se va la próxima cuota?
    # =================================================================
    section("Tu próxima cuota", f"Así se reparte tu pago de {fmt_q(pago_cfg)}",
            "Estimado con la tasa real y los cargos fijos que el banco te está cobrando.")
    m1 = esc_base.tabla.iloc[0]
    partes = [
        ("Intereses", m1["interes"], COLORS["danger"]),
        ("Cuota extrafinanciamiento", m1["cuota_fin"], COLORS["warn"]),
        ("Seguros / comisiones", m1["cargos"], "#C9A15A"),
        ("Baja la deuda", max(0.0, m1["a_capital"]), COLORS["accent"]),
    ]
    total_p = sum(p[1] for p in partes) or 1
    barra = "".join(
        f'<div title="{n}: {fmt_q(v)}" style="width:{v / total_p * 100:.2f}%;background:{c};height:100%;"></div>'
        for n, v, c in partes if v > 0)
    leyenda = "".join(
        f'<div style="display:flex;align-items:center;gap:0.5rem;"><span style="width:10px;height:10px;border-radius:3px;background:{c};"></span>'
        f'<span style="color:var(--ink-soft);font-size:0.86rem;">{n}</span>'
        f'<b style="font-family:\'Fraunces\',serif;font-weight:500;">{fmt_q(v)}</b>'
        f'<span style="color:var(--ink-mute);font-size:0.8rem;">{v / total_p:.0%}</span></div>'
        for n, v, c in partes if v > 0)
    render_html(f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:1.5rem;box-shadow:var(--shadow);">
        <div style="display:flex;height:22px;border-radius:100px;overflow:hidden;margin-bottom:1.1rem;">{barra}</div>
        <div style="display:flex;flex-wrap:wrap;gap:0.8rem 1.8rem;">{leyenda}</div>
    </div>""")

    spacer(1.5)
    with st.expander("Diagnóstico completo de la tarjeta"):
        for kind, titulo, detalle in hallazgos(sit):
            alert(kind, titulo, detalle)

    spacer(2)

    # =================================================================
    # SIMULADOR
    # =================================================================
    section("Simulador", "¿Y si pago diferente?",
            "Mové los números y mirá cuándo quedan libres y cuánto se ahorran en intereses.")

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            pago_sim = st.number_input("Pago mensual (Q)", min_value=0.0, value=pago_cfg, step=250.0, format="%.2f")
        with c2:
            extra = st.number_input("Abono extraordinario (Q)", min_value=0.0, value=0.0, step=500.0, format="%.2f",
                                    help="Bono 14, aguinaldo, etc. Va completo a la tarjeta.")
        with c3:
            meses_opts = list(range(1, 13))
            base_corte = sit["corte"]
            mes_extra = st.selectbox(
                "Mes del abono", meses_opts, index=1,
                format_func=lambda n: mes_corto(pd.Timestamp(base_corte) + pd.DateOffset(months=n - 1)),
                help="Mes en que hacés el pago (antes del corte del día 11 siguiente).",
            )

        c4, c5 = st.columns(2)
        recurrentes = sit.get("cargos_recurrentes", {})
        nuevos = {k: v for k, v in recurrentes.items() if v["es_nuevo"]}
        with c4:
            incluir_nuevos = st.toggle(
                "Asumir que los cargos nuevos se repiten cada mes"
                + (f" ({', '.join(nuevos)}: {fmt_q(sum(v['monto'] for v in nuevos.values()))})" if nuevos else ""),
                value=False, disabled=not nuevos,
            )
        with c5:
            fin_info = sit.get("cuotas_fin", [])
            fin_txt = ", ".join(f"plan {f['plan']} cuota #{f['cuota_num']} de {fmt_q(f['monto'])}" for f in fin_info) or "ninguna"
            sabe_fin = st.toggle(f"Sé cuántas cuotas FIN/CT me quedan ({fin_txt})",
                                 value=sit.get("cuotas_fin_restantes") is not None, disabled=not fin_info)
            fin_rest = None
            if sabe_fin:
                fin_rest = int(st.number_input("Cuotas FIN/CT restantes", min_value=0, max_value=120,
                                               value=int(sit.get("cuotas_fin_restantes") or 12), step=1))

    sit_sim = situacion_tarjeta(movs, config, pago_mensual=pago_sim, incluir_cargos_nuevos=incluir_nuevos,
                                cuotas_fin_restantes=fin_rest)
    cargos_mes = sit_sim["cargos_mes_proyectados"]
    e_sim = proyectar(sit["saldo"], pago_sim, sit["tasa"], sit["corte"], sit["cuota_fin"], fin_rest,
                      cargos_mes, pagos_extra={mes_extra: extra} if extra else None)
    e_ref = proyectar(sit["saldo"], pago_cfg, sit["tasa"], sit["corte"], sit["cuota_fin"], fin_rest, cargos_mes)

    spacer(1)
    if not e_sim.liquidado:
        alert("danger", "Con ese pago la deuda no se termina de pagar",
              f"El pago apenas cubre intereses y cuotas ({fmt_q(e_sim.tabla.iloc[0]['interes'] + sit['cuota_fin'] + cargos_mes)}/mes aprox.).")
    else:
        ult_pago = e_sim.fecha_liquidacion - pd.DateOffset(months=1)
        dif_meses = e_ref.meses - e_sim.meses if e_ref.liquidado else None
        dif_int = e_ref.total_intereses - e_sim.total_intereses
        kpi_row([
            ("Último pago", mes_corto(ult_pago), f"{e_sim.meses} pagos · último de {fmt_q(e_sim.tabla.iloc[-1]['pago'])}", COLORS["accent"]),
            ("Intereses por pagar", fmt_q(e_sim.total_intereses), f"tasa {sit['tasa']:.2%} mensual", COLORS["danger"]),
            ("Total a desembolsar", fmt_q(e_sim.total_pagado), f"incluye {fmt_q_short(e_sim.total_cuotas_fin)} de cuotas FIN"),
            ("Vs. pagar " + fmt_q_short(pago_cfg),
             (f"{dif_meses:+d} meses" if dif_meses else "mismo plazo") if dif_meses is not None else "—",
             (f"ahorrás {fmt_q(dif_int)} de intereses" if dif_int > 0.5 else
              f"pagás {fmt_q(-dif_int)} más de intereses" if dif_int < -0.5 else "sin diferencia")),
        ])

    spacer(1)
    with st.container(border=True):
        res = sit["resumen"]
        hx = [res.iloc[0]["corte"] - pd.DateOffset(months=1)] + list(res["corte"])
        hy = [res.iloc[0]["saldo_inicial"]] + list(res["saldo_final"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hx, y=hy, name="Real (banco)", mode="lines+markers",
            line=dict(color=COLORS["ink"], width=3), marker=dict(size=7, line=dict(width=2, color="white")),
            hovertemplate="Real: Q%{y:,.2f}<extra></extra>",
        ))
        for e, nombre, color, dash in [(e_ref, f"Pagando {fmt_q_short(pago_cfg)}", COLORS["ink_mute"], "dot"),
                                       (e_sim, "Simulación", COLORS["accent"], "solid")]:
            fig.add_trace(go.Scatter(
                x=[pd.Timestamp(sit["corte"])] + list(pd.to_datetime(e.tabla["corte"])),
                y=[sit["saldo"]] + list(e.tabla["saldo_final"]),
                name=nombre, mode="lines+markers", line=dict(color=color, width=2.5, dash=dash), marker=dict(size=6),
                hovertemplate=nombre + ": Q%{y:,.2f}<extra></extra>",
            ))
        if sit.get("limite"):
            fig.add_hline(y=sit["limite"], line_dash="dot", line_color=COLORS["danger"], opacity=0.5,
                          annotation_text="Límite", annotation_font=dict(color=COLORS["danger"], size=10))
        fig = style_plotly(fig)
        ticks = pd.date_range(pd.Timestamp(hx[0]), pd.Timestamp(e_ref.tabla["corte"].max() if not e_ref.tabla.empty else hx[-1]), freq="3MS")
        fig.update_xaxes(tickvals=ticks, ticktext=[mes_corto(t) for t in ticks])
        fig.update_layout(height=380, hovermode="x unified",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                          yaxis=dict(tickprefix="Q", tickformat=",.0f", rangemode="tozero"))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with st.expander("Tabla de amortización de la simulación"):
        t = e_sim.tabla.copy()
        t["Pago en"] = [mes_corto(pd.Timestamp(c) - pd.DateOffset(months=1)) for c in t["corte"]]
        t["Corte"] = [fecha_larga(c) for c in t["corte"]]
        filas = ""
        for _, f in t.iterrows():
            filas += ("<tr>" + "".join(
                f'<td style="padding:0.5rem 0.8rem;border-top:1px solid var(--border);text-align:{a};white-space:nowrap;">{v}</td>'
                for v, a in [(f["Pago en"], "left"), (f["Corte"], "left"), (fmt_q(f["saldo_inicial"]), "right"),
                             (fmt_q(f["interes"]), "right"), (fmt_q(f["cuota_fin"] + f["cargos"]), "right"),
                             (fmt_q(f["pago"]), "right"), (fmt_q(f["a_capital"]), "right"),
                             (fmt_q(f["saldo_final"]), "right")]) + "</tr>")
        heads = ["Pago en", "Corte", "Saldo inicial", "Interés", "Cuota FIN + cargos", "Pago", "A deuda", "Saldo final"]
        render_html(
            '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:0.84rem;font-variant-numeric:tabular-nums;">'
            '<thead><tr style="color:var(--ink-mute);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">'
            + "".join(f'<th style="padding:0.6rem 0.8rem;text-align:{"left" if i < 2 else "right"};">{h}</th>' for i, h in enumerate(heads))
            + f"</tr></thead><tbody>{filas}</tbody></table></div>")

    spacer(2)

    # =================================================================
    # ESCENARIOS
    # =================================================================
    section("Escenarios", "Comparativo rápido")
    cA, cB = st.columns([1.4, 1])
    with cA:
        filas = ""
        for p in sorted({pago_cfg, 6000.0, 6500.0, 7000.0, 8000.0, 10000.0}):
            e = proyectar(sit["saldo"], p, sit["tasa"], sit["corte"], sit["cuota_fin"], fin_rest, cargos_mes)
            ult = mes_corto(e.fecha_liquidacion - pd.DateOffset(months=1)) if e.liquidado else "nunca"
            actual = p == pago_cfg
            estilo = "background:var(--accent-2);font-weight:600;" if actual else ""
            filas += (f'<tr style="{estilo}">'
                      f'<td style="padding:0.6rem 1rem;border-top:1px solid var(--border);">{fmt_q(p)}{" · actual" if actual else ""}</td>'
                      f'<td style="padding:0.6rem 1rem;border-top:1px solid var(--border);text-align:right;">{e.meses if e.liquidado else "—"}</td>'
                      f'<td style="padding:0.6rem 1rem;border-top:1px solid var(--border);">{ult}</td>'
                      f'<td style="padding:0.6rem 1rem;border-top:1px solid var(--border);text-align:right;">{fmt_q(e.total_intereses)}</td></tr>')
        render_html(
            '<div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;box-shadow:var(--shadow);">'
            '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;font-variant-numeric:tabular-nums;">'
            '<thead><tr style="color:var(--ink-mute);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;text-align:left;">'
            '<th style="padding:0.7rem 1rem;">Pago mensual</th><th style="padding:0.7rem 1rem;text-align:right;">Pagos</th>'
            '<th style="padding:0.7rem 1rem;">Último pago</th><th style="padding:0.7rem 1rem;text-align:right;">Intereses</th>'
            f'</tr></thead><tbody>{filas}</tbody></table></div>')
    with cB:
        with st.container(border=True):
            n_obj = st.slider("Quiero quedar libre en (pagos)", 2, 18, 4)
            p_obj = pago_para_liquidar_en(sit["saldo"], n_obj, sit["tasa"], sit["corte"], sit["cuota_fin"], fin_rest, cargos_mes)
            fecha_obj = mes_corto(pd.Timestamp(sit["corte"]) + pd.DateOffset(months=n_obj - 1))
            render_html(f"""
            <div style="font-size:0.85rem;color:var(--ink-mute);">Pago mensual necesario</div>
            <div style="font-family:'Fraunces',serif;font-size:2.1rem;font-weight:500;color:var(--accent);line-height:1.15;">{fmt_q(p_obj)}</div>
            <div style="font-size:0.85rem;color:var(--ink-soft);margin-top:0.3rem;">último pago en {fecha_obj}
            · {fmt_q(p_obj - pago_cfg)} más que hoy</div>""")
            if st.button(f"Usar {fmt_q_short(p_obj)} como pago mensual", width="stretch"):
                upsert_config({"pago_mensual_tarjeta": round(p_obj, 2)})
                st.toast("Pago mensual actualizado.", icon="✅")
                st.rerun()

    spacer(2.5)


# =====================================================================
# PLAN REGISTRADO (hoja Plan_Tarjeta)
# =====================================================================
section("Seguimiento", "Plan de cuotas",
        "Las cuotas que se comprometieron a pagar. Marcá cada pago cuando lo hagan.")

saldo_inicial_plan = float(config.get("saldo_inicial_tarjeta", 0) or 0)
info = calcular_saldo_actual_tarjeta(plan, saldo_inicial_plan)

if sit["hay_datos"]:
    with st.expander("↻ Regenerar el plan con el saldo real del banco"):
        st.caption(f"Conserva las cuotas ya pagadas y recalcula las pendientes desde {fmt_q(sit['saldo'])} "
                   f"(corte {fecha_larga(sit['corte'])}) pagando {fmt_q(pago_cfg)} al mes.")
        if st.button("Regenerar plan", type="primary"):
            pagadas = plan.dropna(subset=["pago_real"]).to_dict("records") if not plan.empty else []
            filas = []
            for i, r in enumerate(pagadas, start=1):
                r = {k: ("" if pd.isna(v) else v) for k, v in r.items()}
                r["mes_num"] = i
                filas.append(r)
            base = len(filas)
            dia_pago = sit["fecha_pago"].day if sit.get("fecha_pago") else 5
            for _, f in esc_base.tabla.iterrows():
                # Misma convención del plan original: la cuota se llama por el mes en que VENCE
                # (ej. "Nov 2026" = pagar antes del 5 de noviembre, idealmente a fin de octubre).
                corte_f = pd.Timestamp(f["corte"])
                filas.append({
                    "mes_num": base + int(f["mes"]),
                    "mes_label": mes_corto(corte_f),
                    "saldo_inicial_plan": round(f["saldo_inicial"], 2),
                    "pago_planeado": round(f["pago"], 2),
                    "pago_real": "", "fecha_pago_real": "",
                    "notas": ("Cierre final" if int(f["mes"]) == len(esc_base.tabla) else "Cuota base")
                             + f" · pagar antes del {dia_pago} {mes_corto(corte_f).split()[0].lower()}",
                })
            replace_plan(filas)
            upsert_config({"saldo_inicial_tarjeta": round(sit["saldo"], 2)})
            st.toast("Plan regenerado con datos reales.", icon="✅")
            st.rerun()

if plan.empty:
    st.info("La hoja `Plan_Tarjeta` está vacía.")
    st.stop()

if info["proximo_mes"]:
    prox = info["proximo_mes"]
    cL, cR = st.columns([1.2, 1])
    with cL:
        render_html(f"""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:1.5rem;box-shadow:var(--shadow);">
            <div style="font-family:'Geist Mono',monospace;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.14em;color:var(--accent);margin-bottom:0.6rem;">Acción pendiente</div>
            <h3 style="margin:0 0 0.4rem;font-size:1.3rem;">Pago de {esc(prox['mes_label'])}</h3>
            <div style="font-size:0.92rem;color:var(--ink-soft);margin-bottom:1rem;">{esc(prox.get('notas') or 'Cuota base mensual')}</div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;padding-top:1rem;border-top:1px solid var(--border);">
                <span style="color:var(--ink-mute);font-size:0.85rem;">Monto planeado · {info['meses_pagados']}/{len(plan)} pagadas</span>
                <span style="font-family:'Fraunces',serif;font-size:1.8rem;font-weight:500;">{fmt_q(prox['pago_planeado'])}</span>
            </div>
        </div>""")
    with cR:
        with st.expander("✓ Marcar como pagado", expanded=False):
            with st.form(f"pago_{int(prox['mes_num'])}"):
                pago_real = st.number_input("Monto pagado real", value=float(prox['pago_planeado']), step=100.0, format="%.2f")
                fecha_pago_in = st.date_input("Fecha de pago", value=hoy_gt(), format="DD/MM/YYYY")
                notas_nuevas = st.text_input("Notas (opcional)", value=prox.get('notas', '') or '')
                if st.form_submit_button("Confirmar pago", type="primary", width="stretch"):
                    try:
                        update_pago_real(int(prox['mes_num']), pago_real, fecha_pago_in.strftime("%Y-%m-%d"), notas_nuevas)
                        st.success("Pago registrado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"{type(e).__name__}: {e}")
else:
    alert("ok", "¡Plan completado!", "Liberaron la deuda de la tarjeta. Tiempo de empezar a ahorrar.")

spacer(1.5)

parts = ['<div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);overflow:hidden;">']
for i, (_, row) in enumerate(plan.iterrows()):
    is_paid = pd.notna(row["pago_real"])
    is_next = info["proximo_mes"] is not None and int(row["mes_num"]) == int(info["proximo_mes"]["mes_num"])
    if is_paid:
        bc, bb, ic, status, sc = COLORS["accent"], COLORS["accent_2"], "✓", f"Pagado · {esc(row['fecha_pago_real'])}", COLORS["accent"]
    elif is_next:
        bc, bb, ic, status, sc = COLORS["warn"], COLORS["warn_soft"], "•", "Próximo pago", COLORS["warn"]
    else:
        bc, bb, ic, status, sc = COLORS["ink_mute"], "#F5F2EC", "○", "Pendiente", COLORS["ink_mute"]
    borde = "" if i == len(plan) - 1 else "border-bottom:1px solid var(--border);"
    real = ""
    if is_paid:
        dif = row["pago_real"] - row["pago_planeado"]
        dif_txt = "" if abs(dif) < 0.5 else f' <span style="color:{COLORS["danger"] if dif < 0 else COLORS["accent"]};">({fmt_q(dif)} vs plan)</span>'
        real = f' · Real: {fmt_q(row["pago_real"])}{dif_txt}'
    parts.append(
        f'<div style="padding:1.1rem 1.4rem;display:flex;align-items:center;gap:1.2rem;{borde}">'
        f'<div style="width:36px;height:36px;border-radius:50%;background:{bb};color:{bc};display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0;border:2px solid {bc};">{ic}</div>'
        f'<div style="flex:1;min-width:0;"><div style="display:flex;align-items:baseline;gap:0.6rem;flex-wrap:wrap;">'
        f'<span style="font-family:Fraunces,serif;font-size:1.08rem;font-weight:500;">{esc(row["mes_label"])}</span>'
        f'<span style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;color:{sc};font-weight:500;">{status}</span></div>'
        f'<div style="font-size:0.82rem;color:var(--ink-mute);">Saldo inicial: {fmt_q(row["saldo_inicial_plan"])}{real}</div></div>'
        f'<div style="text-align:right;"><div style="font-family:Fraunces,serif;font-size:1.25rem;font-weight:500;">{fmt_q(row["pago_planeado"])}</div>'
        f'<div style="font-size:0.72rem;color:var(--ink-mute);text-transform:uppercase;letter-spacing:0.06em;">cuota #{int(row["mes_num"])}</div></div></div>'
    )
parts.append("</div>")
render_html("".join(parts))
