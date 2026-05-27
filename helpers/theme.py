"""
Sistema de diseño compartido — paleta, tipografía, componentes, animaciones.
Importar al inicio de cada página: from helpers.theme import apply_theme
"""
import streamlit as st


# ============ PALETA Y TOKENS DE DISEÑO ============
COLORS = {
    "bg":         "#FAFAF7",   # fondo principal — beige cálido casi blanco
    "surface":    "#FFFFFF",   # cards
    "ink":        "#0F1F1C",   # texto principal — verde casi negro
    "ink_soft":   "#5C6B68",   # texto secundario
    "ink_mute":   "#8B9893",   # texto terciario
    "accent":     "#0A6E4E",   # verde signature (deep forest)
    "accent_2":   "#E8F3EE",   # verde muy suave
    "warn":       "#B8862C",   # ámbar
    "warn_soft":  "#FBF3E1",
    "danger":     "#A8341C",   # rojo terracota
    "danger_soft":"#FCEEEA",
    "border":     "#E8E6DD",   # divisores sutiles
    "shadow":     "0 1px 2px rgba(15,31,28,0.04), 0 4px 16px rgba(15,31,28,0.06)",
}


def apply_theme():
    """Aplica CSS global. Llamar al inicio de cada página después de set_page_config."""
    st.markdown(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Geist:wght@300;400;500;600&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>
    :root {{
        --bg: {COLORS['bg']};
        --surface: {COLORS['surface']};
        --ink: {COLORS['ink']};
        --ink-soft: {COLORS['ink_soft']};
        --ink-mute: {COLORS['ink_mute']};
        --accent: {COLORS['accent']};
        --accent-2: {COLORS['accent_2']};
        --warn: {COLORS['warn']};
        --warn-soft: {COLORS['warn_soft']};
        --danger: {COLORS['danger']};
        --danger-soft: {COLORS['danger_soft']};
        --border: {COLORS['border']};
        --shadow: {COLORS['shadow']};
        --radius: 14px;
        --radius-sm: 10px;
        --radius-lg: 20px;
    }}

    /* ============ Fondo y tipografía base ============ */
    html, body, [class*="css"], .stApp {{
        background: var(--bg) !important;
        color: var(--ink) !important;
        font-family: 'Geist', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-feature-settings: 'ss01', 'cv11';
        -webkit-font-smoothing: antialiased;
    }}

    /* Titulares con font editorial */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Fraunces', Georgia, serif !important;
        font-weight: 500 !important;
        letter-spacing: -0.02em !important;
        color: var(--ink) !important;
    }}
    h1 {{ font-size: clamp(1.85rem, 5vw, 2.6rem) !important; line-height: 1.1 !important; font-weight: 500 !important; }}
    h2 {{ font-size: clamp(1.35rem, 4vw, 1.8rem) !important; line-height: 1.2 !important; }}
    h3 {{ font-size: clamp(1.1rem, 3vw, 1.3rem) !important; line-height: 1.25 !important; }}

    /* ============ Header principal de la app ============ */
    header[data-testid="stHeader"] {{
        background: rgba(250, 250, 247, 0.7) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }}

    /* ============ Contenedor principal ============ */
    .main .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        max-width: 1200px;
    }}

    @media (max-width: 768px) {{
        .main .block-container {{
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 1rem !important;
        }}
    }}

    /* ============ Sidebar ============ */
    section[data-testid="stSidebar"] {{
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }}
    section[data-testid="stSidebar"] > div {{
        padding-top: 2rem !important;
    }}
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] a {{
        font-size: 0.92rem !important;
        font-weight: 400 !important;
    }}

    /* Links de navegación entre páginas */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
        background: transparent !important;
        padding-top: 1rem;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul li a {{
        padding: 0.6rem 1rem !important;
        border-radius: 8px !important;
        margin: 0.15rem 0.5rem !important;
        transition: background 0.15s ease;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul li a:hover {{
        background: var(--accent-2) !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul li a span {{
        font-family: 'Geist', sans-serif !important;
        font-weight: 500 !important;
        color: var(--ink) !important;
    }}

    /* CRÍTICO: botón de toggle del sidebar SIEMPRE visible */
    button[data-testid="stSidebarCollapseButton"],
    button[kind="header"],
    [data-testid="collapsedControl"] {{
        visibility: visible !important;
        display: flex !important;
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        box-shadow: var(--shadow) !important;
        color: var(--ink) !important;
        z-index: 999 !important;
    }}
    button[data-testid="stSidebarCollapseButton"]:hover,
    [data-testid="collapsedControl"]:hover {{
        background: var(--accent-2) !important;
    }}

    /* ============ Métricas (st.metric) ============ */
    [data-testid="stMetric"] {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1.25rem 1.4rem;
        box-shadow: var(--shadow);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }}
    [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(15,31,28,0.06), 0 12px 24px rgba(15,31,28,0.08);
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        color: var(--ink-mute) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }}
    [data-testid="stMetricValue"] {{
        font-family: 'Fraunces', Georgia, serif !important;
        font-size: 1.95rem !important;
        font-weight: 500 !important;
        color: var(--ink) !important;
        letter-spacing: -0.02em !important;
        line-height: 1.1 !important;
        margin-top: 0.25rem !important;
    }}
    [data-testid="stMetricDelta"] {{
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        margin-top: 0.4rem !important;
    }}

    /* ============ Inputs ============ */
    .stTextInput input, .stNumberInput input, .stDateInput input,
    .stSelectbox > div > div, .stTextArea textarea {{
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--ink) !important;
        font-family: 'Geist', sans-serif !important;
        font-size: 0.95rem !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    .stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(10,110,78,0.1) !important;
        outline: none !important;
    }}
    label {{
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: var(--ink-soft) !important;
        letter-spacing: 0.01em !important;
    }}

    /* ============ Botones ============ */
    .stButton button, .stFormSubmitButton button, .stDownloadButton button {{
        background: var(--surface) !important;
        color: var(--ink) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        font-family: 'Geist', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        padding: 0.6rem 1.4rem !important;
        transition: all 0.15s ease;
    }}
    .stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover {{
        border-color: var(--ink) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(15,31,28,0.08);
    }}
    .stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {{
        background: var(--accent) !important;
        color: white !important;
        border-color: var(--accent) !important;
    }}
    .stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {{
        background: #084d37 !important;
        border-color: #084d37 !important;
    }}

    /* ============ Radio horizontal — toggle style ============ */
    .stRadio > div[role="radiogroup"] {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        padding: 4px;
        display: inline-flex;
        gap: 4px;
    }}
    .stRadio > div[role="radiogroup"] label {{
        background: transparent;
        border-radius: 8px;
        padding: 0.5rem 1rem !important;
        transition: all 0.15s ease;
        cursor: pointer;
        margin: 0 !important;
    }}
    .stRadio > div[role="radiogroup"] label:has(input:checked) {{
        background: var(--accent);
        color: white !important;
    }}
    .stRadio > div[role="radiogroup"] label:has(input:checked) p {{
        color: white !important;
    }}

    /* ============ Tablas / DataFrames ============ */
    [data-testid="stDataFrame"] {{
        border-radius: var(--radius) !important;
        overflow: hidden;
        border: 1px solid var(--border);
    }}

    /* ============ Progress bar ============ */
    .stProgress > div > div > div {{
        background-color: var(--accent) !important;
        border-radius: 100px !important;
    }}
    .stProgress > div > div {{
        background-color: var(--accent-2) !important;
        border-radius: 100px !important;
    }}

    /* ============ Alertas (st.info, st.success, etc) ============ */
    div[data-baseweb="notification"], .stAlert {{
        border-radius: var(--radius) !important;
        border-left-width: 3px !important;
        padding: 1rem 1.2rem !important;
    }}

    /* ============ Dividers ============ */
    hr {{
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 2rem 0 !important;
    }}

    /* ============ Captions ============ */
    [data-testid="stCaptionContainer"], .stCaption {{
        color: var(--ink-mute) !important;
        font-size: 0.85rem !important;
    }}

    /* ============ Expander ============ */
    [data-testid="stExpander"] {{
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        background: var(--surface) !important;
    }}
    [data-testid="stExpander"] summary {{
        padding: 0.85rem 1.1rem !important;
        font-weight: 500 !important;
    }}

    /* ============ Animaciones de entrada ============ */
    @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .stApp > div:not(:empty) {{
        animation: fadeUp 0.4s ease-out;
    }}

    /* ============ Mobile-first refinements ============ */
    @media (max-width: 640px) {{
        [data-testid="stMetricValue"] {{
            font-size: 1.55rem !important;
        }}
        [data-testid="stMetric"] {{
            padding: 1rem 1.1rem;
        }}
        .stRadio > div[role="radiogroup"] {{
            width: 100%;
        }}
        .stRadio > div[role="radiogroup"] label {{
            flex: 1;
            justify-content: center;
            text-align: center;
        }}
    }}

    /* Quitar el botón "Deploy" y branding de Streamlit en el navbar */
    /* IMPORTANTE: NO ocultar [data-testid="stToolbar"] completo, solo ciertos hijos */
    [data-testid="stToolbar"] > div:nth-child(2),
    footer,
    #MainMenu {{
        visibility: hidden;
        height: 0;
    }}

    </style>
    """, unsafe_allow_html=True)


# ============ COMPONENTES REUTILIZABLES ============

def hero(eyebrow: str, title: str, subtitle: str = ""):
    """Header de página con eyebrow + título editorial + bajada."""
    html = f"""
    <div style="margin: 0.5rem 0 2rem;">
        <div style="font-family: 'Geist Mono', monospace; font-size: 0.72rem;
                    text-transform: uppercase; letter-spacing: 0.14em;
                    color: var(--accent); margin-bottom: 0.5rem; font-weight: 500;">
            {eyebrow}
        </div>
        <h1 style="font-family: 'Fraunces', serif; font-weight: 500;
                   font-size: clamp(2rem, 5.5vw, 2.8rem); line-height: 1.05;
                   margin: 0 0 0.5rem; letter-spacing: -0.025em; color: var(--ink);">
            {title}
        </h1>
        {f'<p style="color: var(--ink-soft); font-size: 1rem; margin: 0; max-width: 60ch;">{subtitle}</p>' if subtitle else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def card_open(title: str = None, subtitle: str = None):
    """Abre un card. Cerrar con card_close()."""
    title_html = f'<h3 style="margin: 0 0 0.3rem; font-size: 1.05rem;">{title}</h3>' if title else ''
    subtitle_html = f'<p style="color: var(--ink-mute); font-size: 0.85rem; margin: 0 0 1.2rem;">{subtitle}</p>' if subtitle else ''
    header = f'<div style="margin-bottom: 1.2rem;">{title_html}{subtitle_html}</div>' if title or subtitle else ''
    st.markdown(f"""
    <div style="background: var(--surface); border: 1px solid var(--border);
                border-radius: 14px; padding: 1.5rem; box-shadow: var(--shadow);">
        {header}
    """, unsafe_allow_html=True)


def card_close():
    st.markdown("</div>", unsafe_allow_html=True)


def stat_pill(label: str, value: str, color: str = "ink"):
    """Pill compacto con label y valor — para inline stats."""
    color_var = f"var(--{color.replace('_', '-')})"
    return f"""
    <span style="display: inline-flex; align-items: center; gap: 0.5rem;
                  background: var(--accent-2); padding: 0.35rem 0.75rem;
                  border-radius: 100px; font-size: 0.82rem;">
        <span style="color: var(--ink-mute);">{label}</span>
        <span style="font-weight: 600; color: {color_var};">{value}</span>
    </span>
    """


def fmt_q(v) -> str:
    """Formato moneda quetzales."""
    import pandas as pd
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"Q{v:,.2f}"


def fmt_q_short(v) -> str:
    """Formato compacto: Q39,671 sin centavos."""
    import pandas as pd
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"Q{v:,.0f}"


def render_html(html: str):
    """
    Renderiza HTML de forma segura en Streamlit.
    Compacta el HTML para evitar que el parser de markdown interprete
    indentaciones de 4+ espacios como bloques de código.
    """
    import re
    # Eliminar saltos de línea con indentación que confunden a markdown
    compact = re.sub(r'\n\s+', '', html)
    compact = re.sub(r'\s{2,}', ' ', compact)
    st.markdown(compact, unsafe_allow_html=True)


# ============ PALETA PARA PLOTLY ============
PLOTLY_THEME = dict(
    layout=dict(
        font=dict(family="Geist, sans-serif", color=COLORS["ink"], size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=10),
        colorway=[COLORS["accent"], COLORS["warn"], COLORS["danger"], COLORS["ink_soft"], COLORS["ink_mute"]],
        xaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
        yaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
        hoverlabel=dict(bgcolor="white", bordercolor=COLORS["border"], font_family="Geist"),
    )
)


def style_plotly(fig):
    """Aplica el tema a una figura Plotly."""
    fig.update_layout(**PLOTLY_THEME["layout"])
    return fig
