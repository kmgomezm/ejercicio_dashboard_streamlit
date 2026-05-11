import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sales Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── URL del CSV en GitHub (raw) ────────────────────────────────────────────────
CSV_URL = (
    "https://raw.githubusercontent.com/"
    "kmgomezm/ejercicio_dashboard_streamlit/main/sales_data_sample.csv"
)

# ── CSS personalizado ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600;700&display=swap');
    html, body, [class*="css"]  { font-family: 'DM Sans', sans-serif; }
    .main                        { background-color: #0d0f14; }
    .block-container             { padding: 2rem 2.5rem; }
    h1, h2, h3                   { font-family: 'Space Mono', monospace; }
    .kpi-card {
        background: linear-gradient(135deg,#1a1d27 0%,#12151f 100%);
        border: 1px solid #2a2d3e; border-radius: 12px;
        padding: 1.4rem 1.6rem; text-align: center;
    }
    .kpi-label {
        font-size:.75rem; letter-spacing:.15em; text-transform:uppercase;
        color:#6b7280; margin-bottom:.4rem;
    }
    .kpi-value {
        font-family:'Space Mono',monospace; font-size:1.35rem;
        font-weight:700; color:#e2e8f0;
    }
    .section-title {
        font-family:'Space Mono',monospace; font-size:.8rem;
        letter-spacing:.2em; text-transform:uppercase;
        color:#6366f1; margin-bottom:.5rem;
    }
    div[data-testid="stSidebar"] {
        background-color:#0d0f14; border-right:1px solid #1e2130;
    }
</style>
""", unsafe_allow_html=True)

# ── Paleta & layout base Plotly ───────────────────────────────────────────────
PALETTE = ["#6366f1","#34d399","#f59e0b","#ec4899","#38bdf8",
           "#a78bfa","#fb923c","#4ade80","#f472b6","#60a5fa"]

BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#9ca3af"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    xaxis=dict(gridcolor="#1e2130", linecolor="#2a2d3e", tickfont=dict(size=11)),
    yaxis=dict(gridcolor="#1e2130", linecolor="#2a2d3e", tickfont=dict(size=11)),
)

# ── Carga y limpieza ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando datos desde GitHub…")
def load_data() -> pd.DataFrame:
    import requests, io
    response = requests.get(CSV_URL)
    response.raise_for_status()
    raw_bytes = response.content

    # Detectar encoding automáticamente
    for enc in ("latin-1", "cp1252", "iso-8859-1", "utf-8"):
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc)
            break
        except (UnicodeDecodeError, Exception):
            continue
    else:
        # Último recurso: ignorar bytes inválidos
        df = pd.read_csv(io.BytesIO(raw_bytes), encoding="utf-8", errors="replace")
    df.columns = df.columns.str.strip().str.upper()

    # Limpiar nulos: numéricas → mediana, categóricas → moda
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())
    for col in df.select_dtypes(include="object").columns:
        if df[col].isna().any():
            mode_val = df[col].mode()
            df[col] = df[col].fillna(mode_val[0] if not mode_val.empty else "Unknown")

    # Parseo de fecha
    if "ORDERDATE" in df.columns:
        df["ORDERDATE"] = pd.to_datetime(df["ORDERDATE"], errors="coerce")

    # Tipos numéricos
    for col in ["YEAR_ID", "MONTH_ID", "QTR_ID"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if "SALES" in df.columns:
        df["SALES"] = pd.to_numeric(df["SALES"], errors="coerce").fillna(0)

    return df


try:
    df_raw = load_data()
except Exception as e:
    st.error(f"No se pudo cargar el archivo desde GitHub: {e}")
    st.stop()

# ── Sidebar – filtros ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔎 Filtros")

    years = sorted(df_raw["YEAR_ID"].dropna().unique().tolist())
    sel_years = st.multiselect("Año", years, default=years)

    plines = sorted(df_raw["PRODUCTLINE"].dropna().unique().tolist())
    sel_pl = st.multiselect("Línea de producto", plines, default=plines)

    dsizes = sorted(df_raw["DEALSIZE"].dropna().unique().tolist())
    sel_ds = st.multiselect("Tamaño de deal", dsizes, default=dsizes)

    statuses = sorted(df_raw["STATUS"].dropna().unique().tolist())
    sel_st = st.multiselect("Estado de orden", statuses, default=statuses)

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df = df_raw.copy()
if sel_years: df = df[df["YEAR_ID"].isin(sel_years)]
if sel_pl:    df = df[df["PRODUCTLINE"].isin(sel_pl)]
if sel_ds:    df = df[df["DEALSIZE"].isin(sel_ds)]
if sel_st:    df = df[df["STATUS"].isin(sel_st)]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📊 Sales Intelligence Dashboard")
st.markdown('<p class="section-title">Análisis de comportamiento de ventas · kmgomezm</p>',
            unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_sales  = df["SALES"].sum()
total_orders = df["ORDERNUMBER"].nunique() if "ORDERNUMBER" in df.columns else len(df)
avg_order    = df.groupby("ORDERNUMBER")["SALES"].sum().mean() \
               if "ORDERNUMBER" in df.columns else df["SALES"].mean()
top_country  = df.groupby("COUNTRY")["SALES"].sum().idxmax() \
               if "COUNTRY" in df.columns and len(df) > 0 else "N/A"
top_product  = df.groupby("PRODUCTLINE")["SALES"].sum().idxmax() \
               if "PRODUCTLINE" in df.columns and len(df) > 0 else "N/A"

k1, k2, k3, k4, k5 = st.columns(5)
for col, label, value in zip(
    [k1, k2, k3, k4, k5],
    ["Ventas Totales", "Órdenes Únicas", "Ticket Promedio", "País Top", "Línea Top"],
    [f"${total_sales:,.0f}", f"{total_orders:,}", f"${avg_order:,.0f}", top_country, top_product],
):
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Fila 1: Serie temporal + Línea de producto ────────────────────────────────
c1, c2 = st.columns([2, 1])

with c1:
    st.markdown('<p class="section-title">Evolución de Ventas Mensuales</p>',
                unsafe_allow_html=True)
    if "ORDERDATE" in df.columns and not df["ORDERDATE"].isna().all():
        ts = (df.dropna(subset=["ORDERDATE"])
                .groupby(df["ORDERDATE"].dt.to_period("M"))["SALES"]
                .sum().reset_index())
        ts["ORDERDATE"] = ts["ORDERDATE"].astype(str)
        fig = px.area(ts, x="ORDERDATE", y="SALES",
                      color_discrete_sequence=["#6366f1"],
                      labels={"SALES": "Ventas ($)", "ORDERDATE": ""})
        fig.update_traces(fill="tozeroy", line_width=2,
                          fillcolor="rgba(99,102,241,0.15)")
        fig.update_layout(**BASE, height=300)
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown('<p class="section-title">Ventas por Línea de Producto</p>',
                unsafe_allow_html=True)
    pl = (df.groupby("PRODUCTLINE")["SALES"].sum()
            .reset_index().sort_values("SALES", ascending=True))
    fig2 = px.bar(pl, x="SALES", y="PRODUCTLINE", orientation="h",
                  color="PRODUCTLINE", color_discrete_sequence=PALETTE,
                  labels={"SALES": "Ventas ($)", "PRODUCTLINE": ""})
    fig2.update_layout(**BASE, height=300, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

# ── Fila 2: Deal size + Status ────────────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown('<p class="section-title">Distribución por Tamaño de Deal</p>',
                unsafe_allow_html=True)
    ds = df.groupby("DEALSIZE")["SALES"].sum().reset_index()
    fig3 = px.pie(ds, names="DEALSIZE", values="SALES",
                  color_discrete_sequence=PALETTE, hole=0.55)
    fig3.update_traces(textposition="outside", textinfo="percent+label",
                       marker=dict(line=dict(color="#0d0f14", width=2)))
    fig3.update_layout(**BASE, height=320, legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.markdown('<p class="section-title">Ventas por Estado de Orden</p>',
                unsafe_allow_html=True)
    st_df = (df.groupby("STATUS")["SALES"].sum()
               .reset_index().sort_values("SALES", ascending=False))
    fig4 = px.bar(st_df, x="STATUS", y="SALES",
                  color="STATUS", color_discrete_sequence=PALETTE,
                  labels={"SALES": "Ventas ($)", "STATUS": ""})
    fig4.update_layout(**BASE, height=320, showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)

# ── Fila 3: Top clientes + Mapa ───────────────────────────────────────────────
c5, c6 = st.columns([1, 2])

with c5:
    st.markdown('<p class="section-title">Top 10 Clientes</p>',
                unsafe_allow_html=True)
    top_c = (df.groupby("CUSTOMERNAME")["SALES"].sum()
               .reset_index().sort_values("SALES", ascending=True).tail(10))
    fig5 = px.bar(top_c, x="SALES", y="CUSTOMERNAME", orientation="h",
                  color_discrete_sequence=["#34d399"],
                  labels={"SALES": "Ventas ($)", "CUSTOMERNAME": ""})
    fig5.update_layout(**BASE, height=380, showlegend=False)
    st.plotly_chart(fig5, use_container_width=True)

with c6:
    st.markdown('<p class="section-title">Ventas por País</p>',
                unsafe_allow_html=True)
    cty = df.groupby("COUNTRY")["SALES"].sum().reset_index()
    fig6 = px.choropleth(cty, locations="COUNTRY", locationmode="country names",
                          color="SALES", color_continuous_scale="Purples",
                          labels={"SALES": "Ventas ($)"})
    fig6.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False,
                 showcoastlines=True, coastlinecolor="#2a2d3e",
                 showland=True, landcolor="#1a1d27",
                 showocean=True, oceancolor="#0d0f14"),
        margin=dict(l=0, r=0, t=30, b=0), height=380,
        coloraxis_colorbar=dict(
            tickfont=dict(color="#9ca3af"),
            title=dict(font=dict(color="#9ca3af")),
            bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig6, use_container_width=True)

# ── Fila 4: Trimestral + Scatter ──────────────────────────────────────────────
c7, c8 = st.columns(2)

with c7:
    st.markdown('<p class="section-title">Ventas por Trimestre y Año</p>',
                unsafe_allow_html=True)
    q_df = (df.groupby(["YEAR_ID", "QTR_ID"])["SALES"].sum().reset_index())
    q_df["Trimestre"] = "Q" + q_df["QTR_ID"].astype(str)
    fig7 = px.line(q_df, x="Trimestre", y="SALES",
                   color=q_df["YEAR_ID"].astype(str),
                   color_discrete_sequence=PALETTE, markers=True,
                   labels={"SALES": "Ventas ($)", "color": "Año"})
    fig7.update_traces(line_width=2, marker_size=8)
    fig7.update_layout(**BASE, height=320)
    st.plotly_chart(fig7, use_container_width=True)

with c8:
    st.markdown('<p class="section-title">Precio Unitario vs Cantidad por Línea</p>',
                unsafe_allow_html=True)
    fig8 = px.scatter(df, x="PRICEEACH", y="QUANTITYORDERED",
                      color="PRODUCTLINE", size="SALES",
                      color_discrete_sequence=PALETTE, opacity=0.7,
                      labels={"PRICEEACH": "Precio Unitario ($)",
                               "QUANTITYORDERED": "Cantidad Ordenada",
                               "PRODUCTLINE": "Línea"})
    fig8.update_layout(**BASE, height=320)
    st.plotly_chart(fig8, use_container_width=True)

# ── Heatmap mes × año ─────────────────────────────────────────────────────────
st.markdown('<p class="section-title">Heatmap de Ventas — Mes × Año</p>',
            unsafe_allow_html=True)
MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
hm = (df.groupby(["YEAR_ID","MONTH_ID"])["SALES"].sum()
        .reset_index()
        .pivot(index="YEAR_ID", columns="MONTH_ID", values="SALES")
        .fillna(0))
hm.columns = [MESES.get(int(c), c) for c in hm.columns]
fig9 = px.imshow(hm, color_continuous_scale="Purples", aspect="auto",
                 labels=dict(x="Mes", y="Año", color="Ventas ($)"))
fig9.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#9ca3af"),
    margin=dict(l=10,r=10,t=20,b=10), height=220,
    coloraxis_colorbar=dict(
        tickfont=dict(color="#9ca3af"),
        title=dict(font=dict(color="#9ca3af")),
        bgcolor="rgba(0,0,0,0)"),
)
st.plotly_chart(fig9, use_container_width=True)

# ── Reporte de calidad de datos ───────────────────────────────────────────────
with st.expander("🔍 Reporte de Calidad de Datos"):
    null_counts = df_raw.isnull().sum()
    quality = pd.DataFrame({
        "Columna": df_raw.columns,
        "Tipo": df_raw.dtypes.astype(str).values,
        "Nulos originales": null_counts.values,
        "Tratamiento aplicado": [
            "Mediana" if df_raw[c].dtype in [np.float64, np.int64]
            else "Moda" if null_counts[c] > 0 else "—"
            for c in df_raw.columns
        ],
    })
    st.dataframe(quality, use_container_width=True, hide_index=True)
    st.markdown(
        f"**Filas totales:** `{len(df_raw):,}` &nbsp;|&nbsp; "
        f"**Filas filtradas:** `{len(df):,}` &nbsp;|&nbsp; "
        f"**Columnas:** `{len(df_raw.columns)}`"
    )

# ── Vista previa ──────────────────────────────────────────────────────────────
with st.expander("📋 Vista previa de datos (primeras 100 filas)"):
    st.dataframe(df.head(100), use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#374151;font-size:.78rem;'
    'font-family:\'Space Mono\',monospace;">'
    'Sales Intelligence Dashboard · kmgomezm/ejercicio_dashboard_streamlit · '
    'Powered by Streamlit & Plotly</p>',
    unsafe_allow_html=True,
)
