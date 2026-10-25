"""
Mi deuda · Tarjeta de crédito
Cómo va bajando la deuda, cuánto de cada pago es capital vs. interés y cuánto pagar al mes.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from helpers.sheets import get_plan, get_config, get_movs_tarjeta, update_pago_real, replace_plan, upsert_config
from helpers.estado_cuenta import proyectar, pago_para_liquidar_en
from helpers.calc import (
    calcular_saldo_actual_tarjeta, situacion_tarjeta, hallazgos, mes_corto, fecha_larga, hoy_gt,
)
from helpers.deuda import (
    COMPONENTES, COLOR, LABEL, linea_tiempo, acumulado, inicio_plan_fijo,
    pago_equilibrio, tabla_metas, tasa_anual_efectiva,
)
from helpers.theme import (
    apply_theme, hero, fmt_q, fmt_q_short, COLORS, style_plotly, render_html,
    section, spacer, alert, esc,
)


st.set_page_config(page_title="Mi deuda · Finanzas", page_icon="💳", layout="wide", initial_sidebar_state="auto")
apply_theme()

# ---------- estilos propios de esta página (look financiero) ----------
render_html("""
<style>
.fx-num{font-family:'Geist Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums;letter-spacing:-0.01em;}
.fx-lbl{font-family:'Geist Mono',monospace;font-size:0.66rem;text-transform:uppercase;letter-spacing:0.12em;}
.fx-panel{background:#0F1F1C;border-radius:18px;color:#E9EFEC;box-shadow:0 6px 30px rgba(15,31,28,0.18);overflow:hidden;}
.fx-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));}
.fx-cell{padding:1.05rem 1.3rem;border-left:1px solid rgba(255,255,255,0.07);border-top:1px solid rgba(255,255,255,0.07);}
.fx-up{color:#F08C78;} .fx-down{color:#5FD3A5;}
.fx-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);}
.fx-table{width:100%;border-collapse:collapse;font-size:0.84rem;}
.fx-table th{font-family:'Geist Mono',monospace;font-size:0.64rem;text-transform:uppercase;letter-spacing:0.08em;
             color:var(--ink-mute);font-weight:500;padding:0.6rem 0.65rem;text-align:right;white-space:nowrap;
             border-bottom:1px solid var(--border);background:#FBFBF8;position:sticky;top:0;}
.fx-table td{padding:0.5rem 0.65rem;text-align:right;white-space:nowrap;border-bottom:1px solid #F0EEE7;
             font-family:'Geist Mono',monospace;font-variant-numeric:tabular-nums;font-size:0.8rem;}
.fx-table td:first-child,.fx-table th:first-child{text-align:left;}
.fx-table tr.proy td{color:#7C8A86;background:repeating-linear-gradient(135deg,transparent 0 6px,rgba(15,31,28,0.018) 6px 12px);}
.fx-table tr.hoy td{border-bottom:2px solid var(--ink);}
.fx-chip{display:inline-flex;align-items:center;gap:0.4rem;font-size:0.8rem;color:var(--ink-soft);margin-right:1.1rem;}
.fx-chip i{width:10px;height:10px;border-radius:2px;display:inline-block;}
</style>
""")


# =====================================================================
# DATOS
# =====================================================================
try:
    plan = get_plan()
    config = get_config()
    movs = get_movs_tarjeta()
except Exception as e:
    st.error(f"**{type(e).__name__}:** {e}")
    st.stop()

pago_cfg = float(config.get("pago_mensual_tarjeta", 5500) or 5500)
sit = situacion_tarjeta(movs, config, pago_mensual=pago_cfg)

hero(eyebrow="💳 Mi deuda", title="Tarjeta de crédito",
     subtitle="Cuánto debés, cómo va bajando, qué parte de cada pago es capital y qué parte es interés, "
              "y cuánto pagar para quedar libres.")

if not sit["hay_datos"]:
    alert("info", "Importá tus estados de cuenta para ver tu deuda real",
          "Esta página trabaja con los movimientos del banco. Subí los PDF/XLS en <b>Estados de Cuenta</b>.")
    st.page_link("pages/6_Estados_de_Cuenta.py", label="Ir a Estados de Cuenta", icon="🏦")
    st.stop()

res = sit["resumen"]
saldo, tasa, corte = sit["saldo"], sit["tasa"], sit["corte"]
cuota_fin, fin_rest = sit["cuota_fin"], sit.get("cuotas_fin_restantes")
cargos_mes = sit["cargos_mes_proyectados"]
equilibrio = pago_equilibrio(saldo, tasa, cuota_fin, cargos_mes)

# Pago que se está simulando (lo cambian el input y los botones de "metas")
if "pago_sim" not in st.session_state:
    st.session_state["pago_sim"] = pago_cfg
if "extra_sim" not in st.session_state:
    st.session_state["extra_sim"] = 0.0


def _usar_pago(p: float):
    st.session_state["pago_sim"] = float(p)


# =====================================================================
# 1. PANEL PRINCIPAL
# =====================================================================
prev = res.iloc[-2]["saldo_final"] if len(res) > 1 else res.iloc[-1]["saldo_inicial"]
delta_mes = saldo - prev
pico = sit["pico"]
avance = max(0.0, min(1.0, (pico - saldo) / pico)) if pico else 0
e_actual = proyectar(saldo, pago_cfg, tasa, corte, cuota_fin, fin_rest, cargos_mes)
ultimo_pago_txt = (mes_corto(pd.Timestamp(e_actual.fecha_liquidacion) - pd.DateOffset(months=1))
                   if e_actual.liquidado else "nunca")
pmin = sit.get("pago_minimo")
fpago = fecha_larga(sit["fecha_pago"]) if sit.get("fecha_pago") else "—"


def _cell(lbl, val, sub="", cls=""):
    return (f'<div class="fx-cell"><div class="fx-lbl" style="opacity:0.55;">{lbl}</div>'
            f'<div class="fx-num {cls}" style="font-size:1.25rem;margin-top:0.3rem;">{val}</div>'
            f'<div style="font-size:0.76rem;opacity:0.55;margin-top:0.15rem;">{sub}</div></div>')


render_html(f"""
<div class="fx-panel">
  <div style="display:flex;flex-wrap:wrap;gap:1.5rem;justify-content:space-between;align-items:flex-end;padding:1.8rem 1.8rem 1.4rem;
              background:radial-gradient(circle at 100% 0%,rgba(10,110,78,0.35),transparent 55%);">
    <div>
      <div class="fx-lbl" style="opacity:0.6;">Deuda total · corte {fecha_larga(corte)}</div>
      <div class="fx-num" style="font-size:clamp(2.4rem,7vw,3.6rem);font-weight:500;line-height:1.05;margin-top:0.4rem;color:#fff;">{fmt_q(saldo)}</div>
      <div style="margin-top:0.5rem;font-size:0.9rem;">
        <span class="fx-num {'fx-down' if delta_mes < 0 else 'fx-up'}">{'▼' if delta_mes < 0 else '▲'} {fmt_q(abs(delta_mes))}</span>
        <span style="opacity:0.6;"> vs. corte anterior</span>
        <span style="opacity:0.35;margin:0 0.5rem;">|</span>
        <span class="fx-num fx-down">▼ {fmt_q(pico - saldo)}</span><span style="opacity:0.6;"> desde el máximo ({fmt_q_short(pico)})</span>
      </div>
    </div>
    <div style="text-align:right;min-width:200px;margin-left:auto;">
      <div class="fx-lbl" style="opacity:0.6;">Pagando {fmt_q_short(pago_cfg)}/mes</div>
      <div style="font-family:'Fraunces',serif;font-size:1.9rem;color:#5FD3A5;line-height:1.1;margin-top:0.3rem;">Último pago: {ultimo_pago_txt}</div>
      <div style="font-size:0.8rem;opacity:0.6;">{e_actual.meses} pagos más · {fmt_q(e_actual.total_intereses)} de intereses por delante</div>
    </div>
  </div>
  <div style="padding:0 1.8rem 1.2rem;">
    <div style="display:flex;justify-content:space-between;font-size:0.74rem;opacity:0.6;margin-bottom:0.35rem;">
      <span>Máximo {fmt_q_short(pico)}</span><span>{avance:.0%} pagado · falta {1 - avance:.0%}</span><span>Q0</span></div>
    <div style="background:rgba(255,255,255,0.08);height:10px;border-radius:100px;overflow:hidden;">
      <div style="width:{avance * 100:.1f}%;height:100%;background:linear-gradient(90deg,#0A6E4E,#5FD3A5);border-radius:100px;"></div></div>
  </div>
  <div class="fx-grid">
    {_cell("Tasa mensual", f"{tasa:.2%}", f"≈ {tasa_anual_efectiva(tasa):.0%} anual efectiva")}
    {_cell("Interés del mes", fmt_q(saldo * tasa), "lo que cuesta deber hoy", "fx-up")}
    {_cell("Pago para no crecer", fmt_q(equilibrio), "interés + cuota FIN + cargos")}
    {_cell("Pago mínimo del banco", fmt_q(pmin), f"vence {fpago}")}
    {_cell("Disponible", fmt_q(sit.get('disponible')), f"límite {fmt_q_short(sit.get('limite'))}")}
  </div>
</div>
""")

if (sit.get("saldo_mora") or 0) > 0:
    spacer(0.8)
    alert("danger", f"Tenés {fmt_q(sit['saldo_mora'])} en mora",
          f"Pagalo antes del {fpago}. Si no, el banco cobra interés moratorio y Q168 de gestión de cobro.")

spacer(2.5)


# =====================================================================
# 2. CÓMO VA BAJANDO LA DEUDA  (real + proyección)
# =====================================================================
section("Trayectoria", "Cómo va bajando la deuda",
        "Lo sólido es lo que ya pasó según el banco; lo tenue es la proyección con el pago que elijás aquí.")

with st.container(border=True):
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        pago_sim = st.number_input("Pago mensual a simular (Q)", min_value=0.0, step=250.0, format="%.2f", key="pago_sim")
    with c2:
        extra = st.number_input("Abono extra único (Q)", min_value=0.0, step=500.0, format="%.2f", key="extra_sim",
                                help="Bono 14, aguinaldo, etc.")
    with c3:
        mes_extra = st.selectbox(
            "Mes del abono", list(range(1, 13)), index=1,
            format_func=lambda n: mes_corto(pd.Timestamp(corte) + pd.DateOffset(months=n - 1)),
        )

    e_sim = proyectar(saldo, pago_sim, tasa, corte, cuota_fin, fin_rest, cargos_mes,
                      pagos_extra={mes_extra: extra} if extra else None)
    tl = linea_tiempo(res, e_sim)

    if pago_sim <= equilibrio:
        alert("danger", f"Con {fmt_q(pago_sim)} al mes la deuda no baja",
              f"Necesitás más de {fmt_q(equilibrio)} solo para cubrir interés, cuota FIN y cargos.")

    real = tl[tl["tipo"] == "real"]
    proy = tl[tl["tipo"] == "proyectado"]
    x0 = real.iloc[0]["corte"] - pd.DateOffset(months=1)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.58, 0.42], vertical_spacing=0.07)
    # --- saldo real
    fig.add_trace(go.Scatter(
        x=[x0] + list(real["corte"]), y=[real.iloc[0]["saldo_inicial"]] + list(real["saldo_final"]),
        name="Saldo real", mode="lines+markers", line=dict(color=COLORS["ink"], width=3),
        marker=dict(size=7, color=COLORS["ink"], line=dict(width=2, color="white")),
        fill="tozeroy", fillcolor="rgba(15,31,28,0.05)",
        hovertemplate="Saldo real: Q%{y:,.2f}<extra></extra>",
    ), row=1, col=1)
    # --- saldo proyectado
    if not proy.empty:
        fig.add_trace(go.Scatter(
            x=[real.iloc[-1]["corte"]] + list(proy["corte"]), y=[saldo] + list(proy["saldo_final"]),
            name="Proyección", mode="lines+markers", line=dict(color=COLORS["accent"], width=3, dash="dot"),
            marker=dict(size=7, color="white", line=dict(width=2, color=COLORS["accent"])),
            fill="tozeroy", fillcolor="rgba(10,110,78,0.06)",
            hovertemplate="Proyección: Q%{y:,.2f}<extra></extra>",
        ), row=1, col=1)
    # --- composición de cada pago
    opac = [1.0 if t == "real" else 0.42 for t in tl["tipo"]]
    for k, lbl, color in COMPONENTES:
        fig.add_trace(go.Bar(
            x=tl["corte"], y=tl[k], name=lbl, marker=dict(color=color, opacity=opac),
            customdata=tl["tipo"], showlegend=False,
            hovertemplate=f"{lbl}: Q%{{y:,.2f}} <span style='color:#999'>(%{{customdata}})</span><extra></extra>",
        ), row=2, col=1)
    if sit.get("limite"):
        fig.add_hline(y=sit["limite"], line_dash="dash", line_color=COLORS["danger"], line_width=1, opacity=0.5,
                      annotation_text=f"Límite {fmt_q_short(sit['limite'])}", annotation_position="top right",
                      annotation_font=dict(size=10, color=COLORS["danger"]), row=1, col=1)
    fig.add_vline(x=real.iloc[-1]["corte"], line_color=COLORS["ink_mute"], line_width=1, line_dash="dot")
    fig.add_annotation(x=real.iloc[-1]["corte"], y=1.0, yref="paper", text="HOY", showarrow=False,
                       font=dict(family="Geist Mono", size=10, color=COLORS["ink_mute"]), yshift=10)

    todos = [x0] + list(tl["corte"])
    paso = 1 if len(todos) <= 14 else 2
    ticks = todos[::paso]
    fig = style_plotly(fig)
    fig.update_layout(height=560, barmode="relative", hovermode="x unified", bargap=0.25,
                      legend=dict(orientation="h", yanchor="bottom", y=1.03, x=0),
                      margin=dict(l=10, r=10, t=30, b=10))
    fig.update_xaxes(tickvals=ticks, ticktext=[pd.Timestamp(t).strftime("%m/%y") for t in ticks], showgrid=False)
    fig.update_yaxes(tickprefix="Q", tickformat=",.0f", row=1, col=1, rangemode="tozero")
    fig.update_yaxes(tickprefix="Q", tickformat=",.0f", row=2, col=1, title=dict(text="cada pago", font=dict(size=10)))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    render_html("<div>" + "".join(f'<span class="fx-chip"><i style="background:{c}"></i>{l}</span>' for _, l, c in COMPONENTES)
                + '<span class="fx-chip" style="opacity:0.7;">Barras tenues = proyección · eje X = mes del corte (día 11)</span></div>')

    # Resultado de la simulación
    if e_sim.liquidado:
        ult = pd.Timestamp(e_sim.fecha_liquidacion) - pd.DateOffset(months=1)
        dm = e_actual.meses - e_sim.meses if e_actual.liquidado else 0
        di = e_actual.total_intereses - e_sim.total_intereses
        comp = ("Igual que tu pago actual" if abs(di) < 1 and dm == 0 else
                f"Terminás {abs(dm)} mes(es) {'antes' if dm > 0 else 'después'} y {fmt_q(abs(di))} {'menos' if di > 0 else 'más'} de intereses que pagando {fmt_q_short(pago_cfg)}")
        render_html(f"""
        <div style="margin-top:0.8rem;padding:0.9rem 1.1rem;background:var(--accent-2);border-radius:12px;font-size:0.92rem;">
          Pagando <b class="fx-num">{fmt_q(pago_sim)}</b>{f' + abono de <b class="fx-num">{fmt_q(extra)}</b>' if extra else ''}:
          último pago en <b>{mes_corto(ult)}</b> ({e_sim.meses} pagos, el último de <span class="fx-num">{fmt_q(e_sim.tabla.iloc[-1]['pago'])}</span>),
          intereses por pagar <b class="fx-num">{fmt_q(e_sim.total_intereses)}</b>. <span style="color:var(--ink-soft);">{comp}.</span>
        </div>""")
    if abs(pago_sim - pago_cfg) > 0.5 and st.button(f"Guardar {fmt_q(pago_sim)} como mi pago mensual"):
        upsert_config({"pago_mensual_tarjeta": round(pago_sim, 2)})
        st.toast("Pago mensual actualizado.", icon="✅")
        st.rerun()

spacer(2.5)


# =====================================================================
# 3. CAPITAL VS. INTERÉS
# =====================================================================
section("Anatomía del pago", "¿Cuánto de lo que pagás baja la deuda y cuánto es interés?",
        "Cada barra suma 100 % de lo pagado en ese periodo.")

inicio_fijo = inicio_plan_fijo(res, pago_cfg)
ult_real = real.iloc[-1]
filas_comp = [
    (f"Último pago · corte {fecha_larga(ult_real['corte'])}", {
        "pago": ult_real["pago"], **{k: ult_real[k] for k, _, _ in COMPONENTES}}),
]
if inicio_fijo is not None and inicio_fijo != ult_real["corte"]:
    a = acumulado(tl, desde=inicio_fijo)
    filas_comp.append((f"Desde que pagás fijo · {mes_corto(inicio_fijo)} → hoy ({a['n']} cortes)", a))
a_all = acumulado(tl)
filas_comp.append((f"Todo el historial · {a_all['n']} cortes", a_all))
if not proy.empty:
    filas_comp.append((f"Lo que falta (proyección con {fmt_q_short(pago_sim)}/mes)", {
        "pago": proy["pago"].sum(), **{k: proy[k].sum() for k, _, _ in COMPONENTES}}))

bloques = ""
for titulo, d in filas_comp:
    pago = d["pago"] or 1
    segs, leyenda = "", ""
    for k, lbl, color in COMPONENTES:
        v = d[k]
        if v <= 0:
            continue
        pct = v / pago
        segs += (f'<div title="{lbl}: {fmt_q(v)}" style="width:{pct * 100:.2f}%;background:{color};height:100%;'
                 f'display:flex;align-items:center;justify-content:center;color:white;font-size:0.72rem;font-weight:600;'
                 f'font-family:Geist Mono,monospace;overflow:hidden;">{f"{pct:.0%}" if pct >= 0.07 else ""}</div>')
        leyenda += (f'<span class="fx-chip"><i style="background:{color}"></i>{lbl.split(" (")[0]} '
                    f'<b class="fx-num" style="color:var(--ink);">{fmt_q(v)}</b></span>')
    neg = d["capital"] < 0
    nota = (f'<div style="font-size:0.8rem;color:var(--danger);margin-top:0.3rem;">La deuda subió {fmt_q(-d["capital"])}: '
            f'lo pagado no alcanzó para cubrir los cargos.</div>' if neg else "")
    bloques += f"""
    <div style="padding:1.1rem 1.3rem;border-bottom:1px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.55rem;flex-wrap:wrap;gap:0.4rem;">
        <span style="font-weight:600;font-size:0.92rem;">{titulo}</span>
        <span class="fx-num" style="font-size:0.95rem;">Pagado {fmt_q(d['pago'])}</span>
      </div>
      <div style="display:flex;height:24px;border-radius:6px;overflow:hidden;background:#F0EEE7;">{segs}</div>
      <div style="margin-top:0.55rem;line-height:1.9;">{leyenda}</div>{nota}
    </div>"""
render_html(f'<div class="fx-card" style="overflow:hidden;">{bloques}</div>')

spacer(1.2)
pq100 = a_all["interes"] / a_all["pago"] * 100 if a_all["pago"] else 0
cq100 = a_all["capital"] / a_all["pago"] * 100 if a_all["pago"] else 0
alert("warn", f"De cada Q100 que le pagaste a la tarjeta, Q{cq100:.0f} bajaron la deuda y Q{pq100:.0f} fueron intereses",
      "El resto fueron la cuota del extrafinanciamiento y cargos (mora, gestión de cobro, anualidad, seguros). "
      "Mientras más rápido baje el saldo, menos interés se genera cada mes.")

spacer(1.5)

# ---- Tabla mes a mes (real + proyección) ----
with st.expander("📋 Tabla mes a mes: pago, capital, interés y saldo (real + proyección)", expanded=True):
    filas = ""
    for i, f in tl.iterrows():
        es_hoy = f["tipo"] == "real" and f["corte"] == real.iloc[-1]["corte"]
        cls = "proy" if f["tipo"] == "proyectado" else ("hoy" if es_hoy else "")
        pc = f["pct_capital"]
        barra = ""
        if pc is not None and pd.notna(pc) and pc < 0:
            barra = f'<span style="color:{COLORS["danger"]};font-weight:600;">▲ subió</span>'
        elif pc is not None and pd.notna(pc):
            w = max(0.0, min(1.0, pc)) * 100
            col = COLORS["accent"] if pc >= 0.5 else COLORS["warn"] if pc >= 0.2 else COLORS["danger"]
            barra = (f'<div style="display:flex;align-items:center;gap:0.5rem;justify-content:flex-end;">'
                     f'<div style="width:44px;height:6px;background:#F0EEE7;border-radius:4px;overflow:hidden;">'
                     f'<div style="width:{w:.0f}%;height:100%;background:{col};"></div></div>'
                     f'<span style="min-width:2.6rem;color:{col if pc < 0.5 else "inherit"};">{pc:.0%}</span></div>')
        badge = ('<span style="font-size:0.6rem;background:#EEF4F1;color:var(--accent);padding:0.1rem 0.4rem;'
                 'border-radius:4px;margin-left:0.4rem;">PROY</span>') if f["tipo"] == "proyectado" else ""
        cap_color = COLORS["danger"] if f["capital"] < 0 else COLORS["accent"]
        filas += (f'<tr class="{cls}"><td>{mes_corto(f["corte"])}{badge}</td>'
                  f'<td><b>{fmt_q(f["pago"])}</b></td>'
                  f'<td style="color:{cap_color};font-weight:600;">{fmt_q(f["capital"])}</td>'
                  f'<td style="color:{COLORS["danger"]};">{fmt_q(f["interes"])}</td>'
                  f'<td title="Cuota FIN {fmt_q(f["cuota_fin"])} · cargos {fmt_q(f["cargos"])}">{fmt_q(f["cuota_fin"] + f["cargos"])}</td>'
                  f'<td><b>{fmt_q(f["saldo_final"])}</b></td><td>{barra or "—"}</td></tr>')
    render_html(f"""
    <div style="overflow-x:auto;max-height:560px;">
    <table class="fx-table"><thead><tr>
      <th>Corte</th><th>Pago</th><th>A capital</th><th>Interés + IVA</th>
      <th>Cuota FIN + cargos</th><th>Deuda al corte</th><th>% a capital</th>
    </tr></thead><tbody>{filas}</tbody></table></div>""")
    exp = tl.copy()
    exp["corte"] = exp["corte"].dt.strftime("%Y-%m-%d")
    st.download_button("⬇ Descargar tabla (CSV)", exp.to_csv(index=False).encode("utf-8-sig"),
                       file_name="deuda_tarjeta_mes_a_mes.csv", mime="text/csv")

spacer(2.5)


# =====================================================================
# 4. ¿CUÁNTO DEBO PAGAR AL MES?
# =====================================================================
section("Recomendación", "¿Cuánto debo pagar al mes?",
        "Elegí en cuántos meses querés quedar libre y la app te dice el pago exacto (redondeado a Q50).")

pmin_capital = (pmin - equilibrio) if pmin else None
render_html(f"""
<div class="fx-grid" style="gap:0.9rem;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));margin-bottom:1rem;">
  <div class="fx-card" style="padding:1.1rem 1.3rem;border-left:4px solid {COLORS['danger']};">
    <div class="fx-lbl" style="color:{COLORS['danger']};">Zona roja</div>
    <div class="fx-num" style="font-size:1.5rem;margin:0.25rem 0;">&lt; {fmt_q(equilibrio)}</div>
    <div style="font-size:0.84rem;color:var(--ink-soft);">Con menos que esto la deuda <b>crece</b>: no alcanza ni para interés + cuota FIN + cargos.</div>
  </div>
  <div class="fx-card" style="padding:1.1rem 1.3rem;border-left:4px solid {COLORS['warn']};">
    <div class="fx-lbl" style="color:{COLORS['warn']};">Pago mínimo del banco</div>
    <div class="fx-num" style="font-size:1.5rem;margin:0.25rem 0;">{fmt_q(pmin)}</div>
    <div style="font-size:0.84rem;color:var(--ink-soft);">Solo {fmt_q(pmin_capital) if pmin_capital is not None else "—"} irían a capital.
      Pagando el mínimo la deuda dura años.</div>
  </div>
  <div class="fx-card" style="padding:1.1rem 1.3rem;border-left:4px solid {COLORS['accent']};">
    <div class="fx-lbl" style="color:{COLORS['accent']};">Tu pago actual</div>
    <div class="fx-num" style="font-size:1.5rem;margin:0.25rem 0;">{fmt_q(pago_cfg)}</div>
    <div style="font-size:0.84rem;color:var(--ink-soft);">{fmt_q(pago_cfg - equilibrio)} a capital el próximo mes ·
      último pago en <b>{ultimo_pago_txt}</b>.</div>
  </div>
</div>""")

metas = tabla_metas(saldo, tasa, corte, cuota_fin, fin_rest, cargos_mes, pago_cfg)
cols = st.columns(len(metas))
for col, m in zip(cols, metas):
    with col:
        es_actual = e_actual.liquidado and m.meses == e_actual.meses
        borde = f"2px solid {COLORS['accent']}" if es_actual else "1px solid var(--border)"
        ahorro = (f'<div style="color:{COLORS["accent"]};font-size:0.78rem;margin-top:0.4rem;">ahorrás {fmt_q_short(m.ahorro_vs_actual)} de interés</div>'
                  if m.ahorro_vs_actual > 1 and not es_actual else
                  '<div style="color:var(--accent);font-size:0.78rem;margin-top:0.4rem;font-weight:600;">★ tu pago actual ya te deja en este plazo</div>'
                  if es_actual else
                  f'<div style="color:{COLORS["danger"]};font-size:0.78rem;margin-top:0.4rem;">{fmt_q_short(-m.ahorro_vs_actual)} más de interés</div>'
                  if m.ahorro_vs_actual < -1 else '<div style="font-size:0.78rem;margin-top:0.4rem;color:var(--ink-mute);">≈ tu ritmo actual</div>')
        render_html(f"""
        <div style="background:var(--surface);border:{borde};border-radius:14px;padding:1rem 1.1rem;box-shadow:var(--shadow);margin-bottom:0.5rem;min-height:205px;">
          <div class="fx-lbl" style="color:var(--ink-mute);">{m.meses} pagos</div>
          <div class="fx-num" style="font-size:1.45rem;font-weight:500;margin-top:0.3rem;">{fmt_q_short(m.pago)}<span style="font-size:0.8rem;color:var(--ink-mute);">/mes</span></div>
          <div style="font-size:0.8rem;color:var(--ink-soft);margin-top:0.3rem;">último pago <b>{mes_corto(m.ultimo_pago)}</b></div>
          <div style="font-size:0.78rem;color:var(--ink-mute);">intereses {fmt_q_short(m.intereses)}</div>
          {ahorro}
        </div>""")
        st.button("Simular", key=f"meta_{m.meses}_{m.pago}", on_click=_usar_pago, args=(m.pago,), width="stretch")

spacer(1)
with st.container(border=True):
    cA, cB = st.columns([1, 1.3])
    with cA:
        opciones = [pd.Timestamp(corte) + pd.DateOffset(months=n) for n in range(0, 24)]
        meta_fecha = st.selectbox("Quiero hacer mi último pago en…", opciones, index=5, format_func=mes_corto)
    n_pagos = opciones.index(meta_fecha) + 1
    p_meta = pago_para_liquidar_en(saldo, n_pagos, tasa, corte, cuota_fin, fin_rest, cargos_mes)
    e_meta = proyectar(saldo, p_meta, tasa, corte, cuota_fin, fin_rest, cargos_mes)
    with cB:
        render_html(f"""
        <div style="padding-top:0.2rem;">
          <div class="fx-lbl" style="color:var(--ink-mute);">Tenés que pagar</div>
          <div class="fx-num" style="font-size:2rem;color:var(--accent);font-weight:500;line-height:1.15;">{fmt_q(p_meta)}<span style="font-size:0.9rem;color:var(--ink-mute);"> /mes × {n_pagos}</span></div>
          <div style="font-size:0.85rem;color:var(--ink-soft);">intereses totales {fmt_q(e_meta.total_intereses)} ·
          {('+' if p_meta >= pago_cfg else '−')}{fmt_q(abs(p_meta - pago_cfg))} vs. tu pago actual</div>
        </div>""")
    st.button(f"Simular {fmt_q(p_meta)} en la gráfica", on_click=_usar_pago, args=(round(p_meta, 2),))

fin_info = sit.get("cuotas_fin", [])
if fin_info and fin_rest is None:
    st.caption("Supuesto: la cuota de extrafinanciamiento ("
               + ", ".join(f"plan {f['plan']} cuota #{f['cuota_num']} de {fmt_q(f['monto'])}" for f in fin_info)
               + ") sigue mientras haya deuda. Si sabés el total de cuotas, ponelo en Configuración y la proyección se ajusta.")

spacer(2.5)


# =====================================================================
# 5. SEGUIMIENTO Y DIAGNÓSTICO
# =====================================================================
section("Seguimiento", "Plan de cuotas y diagnóstico")

with st.expander("🩺 Diagnóstico: por qué la deuda no bajó más rápido"):
    for kind, titulo, detalle in hallazgos(sit):
        alert(kind, titulo, detalle)

saldo_inicial_plan = float(config.get("saldo_inicial_tarjeta", 0) or 0)
info = calcular_saldo_actual_tarjeta(plan, saldo_inicial_plan)

with st.expander(f"🗓️ Plan de cuotas · {info['meses_pagados']}/{len(plan)} pagadas", expanded=False):
    cL, cR = st.columns([1, 1])
    with cL:
        if info["proximo_mes"]:
            prox = info["proximo_mes"]
            render_html(f"""
            <div class="fx-lbl" style="color:var(--accent);">Próxima cuota</div>
            <div style="font-family:'Fraunces',serif;font-size:1.3rem;margin:0.2rem 0;">{esc(prox['mes_label'])} ·
              <span class="fx-num">{fmt_q(prox['pago_planeado'])}</span></div>
            <div style="font-size:0.85rem;color:var(--ink-soft);">{esc(prox.get('notas') or '')}</div>""")
            with st.form(f"pago_{int(prox['mes_num'])}"):
                pago_real = st.number_input("Monto pagado", value=float(prox["pago_planeado"]), step=100.0, format="%.2f")
                fecha_in = st.date_input("Fecha de pago", value=hoy_gt(), format="DD/MM/YYYY")
                notas = st.text_input("Notas", value=prox.get("notas", "") or "")
                if st.form_submit_button("✓ Marcar como pagado", type="primary", width="stretch"):
                    update_pago_real(int(prox["mes_num"]), pago_real, fecha_in.strftime("%Y-%m-%d"), notas)
                    st.toast("Pago registrado.", icon="✅")
                    st.rerun()
        else:
            alert("ok", "Plan completado", "Todas las cuotas del plan están pagadas.")
    with cR:
        st.caption(f"Regenera las cuotas pendientes desde el saldo real ({fmt_q(saldo)}) con el pago guardado "
                   f"({fmt_q(pago_cfg)}). Conserva las cuotas ya pagadas.")
        if st.button("↻ Regenerar plan con el saldo real", width="stretch"):
            pagadas = plan.dropna(subset=["pago_real"]).to_dict("records") if not plan.empty else []
            filas = []
            for i, r in enumerate(pagadas, start=1):
                r = {k: ("" if pd.isna(v) else v) for k, v in r.items()}
                r["mes_num"] = i
                filas.append(r)
            base = len(filas)
            dia_pago = sit["fecha_pago"].day if sit.get("fecha_pago") else 5
            for _, f in e_actual.tabla.iterrows():
                corte_f = pd.Timestamp(f["corte"])
                filas.append({
                    "mes_num": base + int(f["mes"]), "mes_label": mes_corto(corte_f),
                    "saldo_inicial_plan": round(f["saldo_inicial"], 2), "pago_planeado": round(f["pago"], 2),
                    "pago_real": "", "fecha_pago_real": "",
                    "notas": ("Cierre final" if int(f["mes"]) == len(e_actual.tabla) else "Cuota base")
                             + f" · pagar antes del {dia_pago} {mes_corto(corte_f).split()[0].lower()}",
                })
            replace_plan(filas)
            upsert_config({"saldo_inicial_tarjeta": round(saldo, 2)})
            st.toast("Plan regenerado con datos reales.", icon="✅")
            st.rerun()

    if not plan.empty:
        filas = ""
        for _, row in plan.iterrows():
            pagado = pd.notna(row["pago_real"])
            es_prox = info["proximo_mes"] is not None and int(row["mes_num"]) == int(info["proximo_mes"]["mes_num"])
            estado = ("✓ pagado" if pagado else "● próximo" if es_prox else "pendiente")
            color = COLORS["accent"] if pagado else COLORS["warn"] if es_prox else COLORS["ink_mute"]
            dif = ""
            if pagado and abs(row["pago_real"] - row["pago_planeado"]) >= 0.5:
                d = row["pago_real"] - row["pago_planeado"]
                dif = f'<span style="color:{COLORS["danger"] if d < 0 else COLORS["accent"]};">{fmt_q(d)}</span>'
            filas += (f'<tr><td>#{int(row["mes_num"])} · {esc(row["mes_label"])}</td>'
                      f'<td>{fmt_q(row["pago_planeado"])}</td><td>{fmt_q(row["pago_real"]) if pagado else "—"}</td>'
                      f'<td>{dif or "—"}</td><td style="color:{color};">{estado}</td></tr>')
        render_html(f"""<div style="overflow-x:auto;margin-top:1rem;"><table class="fx-table"><thead><tr>
          <th>Cuota</th><th>Planeado</th><th>Real</th><th>Diferencia</th><th>Estado</th></tr></thead>
          <tbody>{filas}</tbody></table></div>""")
