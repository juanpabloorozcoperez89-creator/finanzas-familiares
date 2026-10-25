"""
Estados de cuenta del banco — importar PDF/XLS y analizar corte a corte
a dónde se fue cada quetzal pagado a la tarjeta.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from helpers.sheets import (
    get_movs_tarjeta, add_movs_tarjeta, borrar_movs_tarjeta, get_config, upsert_config,
)
from helpers.estado_cuenta import parse_archivo, estados_a_df, resumen_periodos, CATEGORIAS
from helpers.calc import situacion_tarjeta, hallazgos, mes_corto, fecha_larga
from helpers.theme import (
    apply_theme, hero, fmt_q, fmt_q_short, COLORS, style_plotly, render_html,
    section, spacer, alert, kpi_row, esc,
)


st.set_page_config(
    page_title="Estados de cuenta · Finanzas",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="auto",
)
apply_theme()

hero(
    eyebrow="🏦 Estados de cuenta",
    title="Lo que dice el banco",
    subtitle="Subí los PDF o XLS de “Detalle de movimientos” de Banco Industrial. "
             "La app los lee, valida que cuadren y te dice a dónde se fue cada quetzal.",
)

try:
    movs = get_movs_tarjeta()
    config = get_config()
except Exception as e:
    st.error(f"**Error conectando a Google Sheets** · {type(e).__name__}: {e}")
    st.stop()

tab_an, tab_imp, tab_det = st.tabs(["📊 Análisis mes a mes", "⬆️ Importar estados", "🔎 Movimientos"])


# =====================================================================
# IMPORTAR
# =====================================================================
with tab_imp:
    section("Paso 1", "Subí uno o varios estados de cuenta",
            "Banca en Línea BI → Tarjeta → Detalle de movimientos → Descargar PDF o Excel. "
            "Podés subir todos los meses de una vez; los repetidos se ignoran solos.")

    archivos = st.file_uploader(
        "Estados de cuenta", type=["pdf", "xls", "xlsx"], accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if archivos:
        estados, errores = [], []
        for a in archivos:
            try:
                ec = parse_archivo(a.getvalue(), a.name)
                if not ec.movimientos:
                    raise ValueError("no se encontraron movimientos")
                estados.append(ec)
            except Exception as e:
                errores.append((a.name, f"{type(e).__name__}: {e}"))

        for nombre, err in errores:
            alert("danger", f"No pude leer {esc(nombre)}", esc(err))

        if estados:
            estados.sort(key=lambda e: e.periodo_corte or pd.Timestamp.min)
            nuevos = estados_a_df(estados)
            res_prev = resumen_periodos(nuevos)

            filas = ""
            for ec in estados:
                cuadra = ec.saldo_final is None or abs(ec.movimientos[-1].saldo - ec.saldo_final) < 0.02
                badge = (f'<span style="color:var(--accent);font-weight:600;">✓ cuadra</span>' if cuadra
                         else f'<span style="color:var(--danger);font-weight:600;">✗ no cuadra</span>')
                td = 'style="padding:0.65rem 1rem;border-top:1px solid var(--border);'
                filas += (
                    f'<tr><td {td}">{fecha_larga(ec.periodo_corte)}</td><td {td}">{esc(ec.archivo)}</td>'
                    f'<td {td}text-align:right">{len(ec.movimientos)}</td>'
                    f'<td {td}text-align:right">{fmt_q(ec.saldo_inicial)}</td>'
                    f'<td {td}text-align:right">{fmt_q(ec.movimientos[-1].saldo)}</td><td {td}">{badge}</td></tr>'
                )
            render_html(f"""
            <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow-x:auto;box-shadow:var(--shadow);">
            <table style="width:100%;border-collapse:collapse;font-size:0.86rem;">
            <thead><tr style="text-align:left;color:var(--ink-mute);font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">
            <th style="padding:0.8rem 1rem">Corte</th><th>Archivo</th><th style="text-align:right">Movs</th>
            <th style="text-align:right">Saldo inicial</th><th style="text-align:right">Saldo final</th><th style="padding-right:1rem">Validación</th>
            </tr></thead><tbody>{filas}</tbody></table></div>
            """)

            huecos = res_prev[~res_prev["encadena"]]
            if len(res_prev) > 1 and not huecos.empty:
                alert("warn", "Faltan meses entre los archivos",
                      "Los saldos no encadenan antes de: " + ", ".join(fecha_larga(c) for c in huecos["corte"])
                      + ". Subí los cortes faltantes para que el análisis sea completo.")

            spacer(1)
            ultimo = estados[-1]
            if st.button(f"Importar {len(nuevos)} movimientos de {len(estados)} estado(s)", type="primary"):
                with st.spinner("Guardando en Google Sheets…"):
                    ins, dup = add_movs_tarjeta(nuevos)
                    upsert_config({
                        "tc_tarjeta": ultimo.tarjeta,
                        "tc_limite": ultimo.limite,
                        "tc_disponible": ultimo.disponible,
                        "tc_saldo_mora": ultimo.saldo_mora,
                        "tc_pago_minimo": ultimo.pago_minimo,
                        "tc_fecha_pago": ultimo.fecha_pago.isoformat() if ultimo.fecha_pago else "",
                        "tc_fecha_corte": ultimo.fecha_corte.isoformat() if ultimo.fecha_corte else "",
                    })
                st.toast(f"Listo: {ins} movimientos nuevos, {dup} ya existían.", icon="✅")
                st.rerun()

    spacer(2)
    with st.expander("Mantenimiento: borrar todos los movimientos importados"):
        st.caption("Útil si importaste algo mal. No toca transacciones, plan ni categorías.")
        ok = st.checkbox("Sí, quiero borrar la hoja Movimientos_Tarjeta")
        if st.button("Borrar movimientos", disabled=not ok):
            borrar_movs_tarjeta()
            st.toast("Hoja vaciada.", icon="🗑️")
            st.rerun()


# =====================================================================
# ANÁLISIS
# =====================================================================
with tab_an:
    if movs.empty:
        render_html("""
        <div style="background:var(--surface);border:1px dashed var(--border);border-radius:14px;
                    padding:3.5rem 1.5rem;text-align:center;">
            <div style="font-size:2.5rem;margin-bottom:0.5rem;">🏦</div>
            <div style="font-family:'Fraunces',serif;font-size:1.3rem;margin-bottom:0.3rem;">Todavía no hay estados importados</div>
            <div style="color:var(--ink-mute);">Andá a la pestaña <b style="color:var(--accent);">Importar estados</b> y subí tus PDF.</div>
        </div>""")
    else:
        sit = situacion_tarjeta(movs, config)
        res: pd.DataFrame = sit["resumen"]

        # ---- Rango de cortes ----
        cortes = list(res["corte"])
        if len(cortes) > 1:
            ini, fin = st.select_slider(
                "Rango de cortes", options=cortes, value=(cortes[0], cortes[-1]),
                format_func=lambda c: mes_corto(c),
            )
            r = res[(res["corte"] >= ini) & (res["corte"] <= fin)].reset_index(drop=True)
        else:
            r = res

        pagado = r["PAGO"].sum()
        bajo = r["reduccion"].sum()
        costo = r["costo_financiero"].sum()
        cfin = r["CUOTA_FIN"].sum()
        kpi_row([
            ("Saldo al corte", fmt_q(r.iloc[-1]["saldo_final"]), fecha_larga(r.iloc[-1]["corte"])),
            ("Pagaste", fmt_q(pagado), f"{int(r['n_pagos'].sum())} pagos en {len(r)} cortes"),
            ("Bajó la deuda", fmt_q(bajo), f"{bajo / pagado:.0%} de lo pagado" if pagado else "", COLORS["accent"]),
            ("Costo financiero", fmt_q(costo), f"{costo / pagado:.0%} de lo pagado" if pagado else "", COLORS["danger"]),
            ("Cuotas extrafin.", fmt_q(cfin), f"{cfin / pagado:.0%} de lo pagado" if pagado else "", COLORS["warn"]),
        ])

        spacer(2)
        section("Diagnóstico", "Por qué la deuda no baja más rápido")
        for kind, titulo, detalle in hallazgos(sit):
            alert(kind, titulo, detalle)

        spacer(2)
        section("Corte a corte", "¿A dónde se fue cada pago?",
                "Verde = lo que realmente bajó la deuda. Si cae bajo cero, ese mes la deuda creció.")
        x = [mes_corto(c) for c in r["corte"]]
        otros = r["CUOTA_ANUAL"] + r["SEGURO"] + r["COMISION"]
        mora_gest = r["MORA"] + r["GESTION_COBRO"]
        with st.container(border=True):
            fig = go.Figure()
            serie = [
                ("Intereses + IVA", r["INTERES"] + r["IVA"], COLORS["danger"]),
                ("Mora + gestión de cobro", mora_gest, "#D9775F"),
                ("Anualidad, seguro, comisiones", otros, "#C9A15A"),
                ("Cuota extrafinanciamiento", r["CUOTA_FIN"], COLORS["warn"]),
                ("Compras", r["COMPRA"], COLORS["ink_mute"]),
                ("Bajó la deuda", r["reduccion"], COLORS["accent"]),
            ]
            for nombre, y, color in serie:
                if (y.abs() > 0).any():
                    fig.add_trace(go.Bar(name=nombre, x=x, y=y, marker_color=color,
                                         hovertemplate=f"<b>%{{x}}</b><br>{nombre}: Q%{{y:,.2f}}<extra></extra>"))
            fig.add_trace(go.Scatter(
                name="Total pagado", x=x, y=r["PAGO"], mode="markers+text",
                marker=dict(symbol="line-ew", size=26, line=dict(width=3, color=COLORS["ink"])),
                text=[fmt_q_short(v) for v in r["PAGO"]], textposition="top center",
                textfont=dict(family="Geist Mono", size=10, color=COLORS["ink_soft"]),
                hovertemplate="<b>%{x}</b><br>Pagado: Q%{y:,.2f}<extra></extra>",
            ))
            fig = style_plotly(fig)
            fig.update_layout(barmode="relative", height=430, hovermode="x unified",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                              yaxis=dict(tickprefix="Q", tickformat=",.0f"))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        spacer(1.5)
        section("Evolución", "Saldo al cierre de cada corte")
        with st.container(border=True):
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=[mes_corto(r.iloc[0]["corte"] - pd.DateOffset(months=1))] + x,
                y=[r.iloc[0]["saldo_inicial"]] + list(r["saldo_final"]),
                mode="lines+markers", name="Saldo", line=dict(color=COLORS["accent"], width=3),
                marker=dict(size=8, line=dict(width=2, color="white")),
                fill="tozeroy", fillcolor="rgba(10,110,78,0.06)",
                hovertemplate="<b>%{x}</b><br>Saldo: Q%{y:,.2f}<extra></extra>",
            ))
            if sit.get("limite"):
                fig2.add_hline(y=sit["limite"], line_dash="dot", line_color=COLORS["danger"],
                               annotation_text=f"Límite {fmt_q_short(sit['limite'])}",
                               annotation_position="top left",
                               annotation_font=dict(color=COLORS["danger"], size=11))
            fig2 = style_plotly(fig2)
            fig2.update_layout(height=320, showlegend=False, yaxis=dict(tickprefix="Q", tickformat=",.0f"))
            st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

        spacer(1.5)
        section("Tabla", "Detalle mes a mes")
        cols = [
            ("Corte", lambda f: fecha_larga(f["corte"])),
            ("Saldo inicial", lambda f: fmt_q(f["saldo_inicial"])),
            ("Interés + IVA", lambda f: fmt_q(f["INTERES"] + f["IVA"])),
            ("Mora + gestión", lambda f: fmt_q(f["MORA"] + f["GESTION_COBRO"])),
            ("Otros cargos", lambda f: fmt_q(f["CUOTA_ANUAL"] + f["SEGURO"] + f["COMISION"] + f["COMPRA"])),
            ("Cuota FIN", lambda f: fmt_q(f["CUOTA_FIN"])),
            ("Pagos", lambda f: fmt_q(f["PAGO"])),
            ("Saldo final", lambda f: fmt_q(f["saldo_final"])),
            ("Bajó", lambda f: f'<b style="color:{COLORS["accent"] if f["reduccion"] >= 0 else COLORS["danger"]}">{fmt_q(f["reduccion"])}</b>'),
            ("% del pago a deuda", lambda f: f'{f["pct_pago_a_deuda"]:.0%}' if f["PAGO"] and f["reduccion"] > 0 else "—"),
        ]
        thead = "".join(f'<th style="padding:0.7rem 0.8rem;text-align:{"left" if i == 0 else "right"};white-space:nowrap;">{c}</th>'
                        for i, (c, _) in enumerate(cols))
        tbody = ""
        for _, f in r.iterrows():
            tds = "".join(f'<td style="padding:0.6rem 0.8rem;text-align:{"left" if i == 0 else "right"};white-space:nowrap;border-top:1px solid var(--border);">{fn(f)}</td>'
                          for i, (_, fn) in enumerate(cols))
            tbody += f"<tr>{tds}</tr>"
        tot = {
            "Saldo inicial": fmt_q(r.iloc[0]["saldo_inicial"]),
            "Interés + IVA": fmt_q((r["INTERES"] + r["IVA"]).sum()),
            "Mora + gestión": fmt_q(mora_gest.sum()),
            "Otros cargos": fmt_q((otros + r["COMPRA"]).sum()),
            "Cuota FIN": fmt_q(cfin), "Pagos": fmt_q(pagado),
            "Saldo final": fmt_q(r.iloc[-1]["saldo_final"]), "Bajó": fmt_q(bajo),
            "% del pago a deuda": f"{bajo / pagado:.0%}" if pagado else "—",
        }
        tfoot = '<td style="padding:0.7rem 0.8rem;font-weight:600;">Total</td>' + "".join(
            f'<td style="padding:0.7rem 0.8rem;text-align:right;font-weight:600;white-space:nowrap;">{tot.get(c, "")}</td>'
            for c, _ in cols[1:])
        render_html(f"""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow-x:auto;box-shadow:var(--shadow);">
        <table style="width:100%;border-collapse:collapse;font-size:0.84rem;font-variant-numeric:tabular-nums;">
        <thead><tr style="color:var(--ink-mute);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">{thead}</tr></thead>
        <tbody>{tbody}</tbody>
        <tfoot><tr style="background:var(--accent-2);border-top:2px solid var(--border);">{tfoot}</tr></tfoot>
        </table></div>""")

        spacer(1)
        exp = r.copy()
        exp["corte"] = exp["corte"].dt.strftime("%Y-%m-%d")
        st.download_button("⬇ Descargar análisis (CSV)", exp.to_csv(index=False).encode("utf-8-sig"),
                           file_name="analisis_tarjeta_por_corte.csv", mime="text/csv")


# =====================================================================
# MOVIMIENTOS
# =====================================================================
with tab_det:
    if movs.empty:
        st.info("Sin movimientos importados.")
    else:
        cortes = sorted(movs["periodo_corte"].unique(), reverse=True)
        corte_sel = st.selectbox("Corte", cortes, format_func=lambda c: f"Corte {fecha_larga(pd.Timestamp(c))}")
        g = movs[movs["periodo_corte"] == corte_sel].reset_index(drop=True)
        colores = {
            "PAGO": COLORS["accent"], "INTERES": COLORS["danger"], "IVA": COLORS["danger"],
            "MORA": "#D9775F", "GESTION_COBRO": "#D9775F", "CUOTA_FIN": COLORS["warn"],
        }
        filas = ""
        for i, m in g.iterrows():
            color = colores.get(m["categoria"], COLORS["ink_soft"])
            es_pago = m["valor"] < 0
            fecha = m["fecha"].strftime("%d/%m/%Y") if pd.notna(m["fecha"]) else "inicio de corte"
            borde = "" if i == len(g) - 1 else "border-bottom:1px solid var(--border);"
            filas += f"""
            <div style="padding:0.85rem 1.3rem;display:flex;align-items:center;gap:1rem;{borde}">
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:500;font-size:0.92rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{esc(m['comercio'] or m['tipo'])}</div>
                    <div style="font-size:0.78rem;color:var(--ink-mute);">
                        <span style="color:{color};font-weight:500;">{CATEGORIAS.get(m['categoria'], m['categoria'])}</span> · {fecha} · doc {esc(m['doc'])}
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-family:'Fraunces',serif;font-size:1.05rem;font-weight:500;color:{COLORS['accent'] if es_pago else COLORS['ink']};">
                        {'−' if es_pago else '+'}{fmt_q(abs(m['valor']))}</div>
                    <div style="font-size:0.74rem;color:var(--ink-mute);">saldo {fmt_q(m['saldo'])}</div>
                </div>
            </div>"""
        render_html(f'<div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);overflow:hidden;">{filas}</div>')
