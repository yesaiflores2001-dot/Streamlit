from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# Configuración de página
st.set_page_config(
    page_title="Sales Analytics | Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta visual y estilos
NAVY = "#10264f"
BLUE = "#2563eb"
GREEN = "#22a06b"
RED = "#e25555"
MUTED = "#68758b"

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
      :root { --ink:#10264f; --blue:#2563eb; --muted:#68758b; }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .stApp { background: linear-gradient(180deg, #f6f9ff 0%, #f8fafc 36%, #f4f7fb 100%); }
      [data-testid="stSidebar"] { background: linear-gradient(180deg, #0b1d3a 0%, #102b57 100%); }
      [data-testid="stSidebar"] * { color: #eef4ff; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#c8d6ed; }
      [data-testid="stSidebar"] [data-baseweb="select"] > div { background:#17345f; }
      [data-testid="stSidebar"] [data-testid="stDateInput"] input { background:#17345f; }
      .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
      h1, h2, h3 { color:var(--ink); font-family:'Manrope', sans-serif; letter-spacing:-.03em; }
      .eyebrow { color:var(--blue); font-size:.76rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase; margin-bottom:.35rem; }
      .hero-title { color:var(--ink); font-family:'Manrope', sans-serif; font-size:2.55rem; line-height:1.08; font-weight:800; letter-spacing:-.055em; margin:0; }
      .hero-copy { color:var(--muted); font-size:1.02rem; margin:.6rem 0 0; }
      .hero-tag { display:inline-block; padding:.45rem .8rem; border-radius:999px; background:#e8f0ff; color:#1e56c5; font-size:.82rem; font-weight:700; }
      .section-label { color:var(--muted); font-size:.82rem; font-weight:600; }
      [data-testid="stMetric"] { background:white; border:1px solid #e8edf5; border-radius:16px; padding:17px 18px; box-shadow:0 6px 20px rgba(16,38,79,.045); min-height:128px; }
      [data-testid="stMetricLabel"] { color:#66748b; font-size:.88rem; font-weight:600; }
      [data-testid="stMetricValue"] { color:var(--ink); font-family:'Manrope',sans-serif; font-size:1.65rem; font-weight:800; }
      [data-testid="stMetricDelta"] { font-size:.8rem; }
      div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] { background:white; border:1px solid #e8edf5; border-radius:16px; padding:8px; box-shadow:0 6px 20px rgba(16,38,79,.035); }
      div[data-testid="stTabs"] button { font-weight:600; }
      div.stDownloadButton > button { border-radius:10px; background:var(--blue); color:white; border:0; font-weight:700; padding:.65rem 1rem; }
      div.stDownloadButton > button:hover { background:#174ec2; color:white; }
      .stAlert { border-radius:12px; }
      @media (max-width: 760px) { .hero-title {font-size:2rem;} .block-container {padding-top:1rem;} }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Cargando datos de ventas...")
def load_data(file_path: str) -> pd.DataFrame:
    data = pd.read_excel(file_path)
    data["Order Date"] = pd.to_datetime(data["Order Date"], errors="coerce")
    if "Ship Date" in data.columns:
        data["Ship Date"] = pd.to_datetime(data["Ship Date"], errors="coerce")
    for column in ("Sales", "Profit", "Quantity", "Discount"):
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0)
    if "Discount" not in data.columns:
        data["Discount"] = 0
    return data.dropna(subset=["Order Date"])


def money(value: float) -> str:
    return f"${value:,.2f}"


def style_chart(fig, height: int = 360):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=12, r=12, t=25, b=12),
        font=dict(family="DM Sans, sans-serif", color=NAVY),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#edf1f7", zeroline=False)
    return fig


file_path = Path(__file__).with_name("SalidaVentas.xlsx")
try:
    if not file_path.exists():
        st.error(f"No se encontró el archivo de datos: `{file_path.name}`. Colócalo junto a `app.py`.")
        st.stop()
    df_raw = load_data(str(file_path))
except Exception as error:
    st.error(f"No se pudieron cargar los datos. Revisa `SalidaVentas.xlsx` y sus columnas. Detalle: {error}")
    st.stop()

if df_raw.empty:
    st.warning("El archivo no contiene registros con una fecha de pedido válida.")
    st.stop()

# Barra lateral: filtros
with st.sidebar:
    st.markdown("### 📊 Sales Analytics")
    st.caption("Panel de control · Ventas y rentabilidad")
    st.divider()
    st.markdown("#### Ajusta tu análisis")

    min_date = df_raw["Order Date"].min().date()
    max_date = df_raw["Order Date"].max().date()
    selected_dates = st.date_input(
        "Período de pedidos",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Selecciona el período que quieres analizar.",
    )
    if isinstance(selected_dates, (tuple, list)):
        start_date = selected_dates[0]
        end_date = selected_dates[-1] if len(selected_dates) == 2 else max_date
    else:
        start_date = end_date = selected_dates

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1)
    df_date = df_raw[(df_raw["Order Date"] >= start_ts) & (df_raw["Order Date"] < end_ts)]

    region_options = sorted(df_date["Region"].dropna().unique()) if "Region" in df_date else []
    selected_regions = st.multiselect("Región", region_options, default=region_options)
    df_region = df_date[df_date["Region"].isin(selected_regions)] if "Region" in df_date else df_date

    state_options = sorted(df_region["State"].dropna().unique()) if "State" in df_region else []
    selected_states = st.multiselect("Estado", state_options, default=state_options)
    df_state = df_region[df_region["State"].isin(selected_states)] if "State" in df_region else df_region

    category_options = sorted(df_state["Category"].dropna().unique()) if "Category" in df_state else []
    selected_categories = st.multiselect("Categoría", category_options, default=category_options)
    df_category = df_state[df_state["Category"].isin(selected_categories)] if "Category" in df_state else df_state

    customer_options = sorted(df_category["Customer Name"].dropna().unique()) if "Customer Name" in df_category else []
    selected_customers = st.multiselect("Cliente (opcional)", customer_options)
    df_filtered = df_category.copy()
    if selected_customers:
        df_filtered = df_filtered[df_filtered["Customer Name"].isin(selected_customers)]
    st.divider()
    st.caption(f"{len(df_filtered):,} registros incluidos")

# Encabezado
header, badge = st.columns([5, 1])
with header:
    st.markdown('<div class="eyebrow">Panel de inteligencia comercial</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Ventas, analizadas<br>con claridad.</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-copy">Sigue el rendimiento, descubre tendencias y toma decisiones basadas en tus datos.</p>', unsafe_allow_html=True)
with badge:
    st.markdown('<div style="text-align:right;padding-top:1rem"><span class="hero-tag">● En vivo</span></div>', unsafe_allow_html=True)
st.write("")

if df_filtered.empty:
    st.warning("No hay registros que coincidan con los filtros seleccionados. Amplía el período o cambia los filtros.")
    st.stop()

sales_total = df_filtered["Sales"].sum() if "Sales" in df_filtered else 0
net_profit = df_filtered["Profit"].sum() if "Profit" in df_filtered else 0
positive_profit = df_filtered["Profit"].clip(lower=0).sum() if "Profit" in df_filtered else 0
losses = abs(df_filtered["Profit"].clip(upper=0).sum()) if "Profit" in df_filtered else 0
order_count = df_filtered["Order ID-1"].nunique() if "Order ID-1" in df_filtered else len(df_filtered)
quantity = df_filtered["Quantity"].sum() if "Quantity" in df_filtered else 0
margin_pct = (net_profit / sales_total * 100) if sales_total else 0

st.markdown("#### Resumen del período")
st.markdown('<div class="section-label">Indicadores clave · Actualizados según tus filtros</div>', unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Ventas totales", money(sales_total), help="Suma de ventas del período seleccionado")
k2.metric("Ganancia bruta positiva", money(positive_profit), delta="Antes de pérdidas")
k3.metric("Pérdidas", money(losses), delta="Profit negativo", delta_color="inverse")
k4.metric("Pedidos", f"{order_count:,}", help=f"Unidades vendidas: {quantity:,.0f}")
k5.metric("Margen neto", f"{margin_pct:.1f}%", delta=money(net_profit))
st.write("")

# Áreas de análisis
(tab_overview, tab_region, tab_customers, tab_products, tab_losses, tab_reports) = st.tabs(
    ["📈  Tendencias", "🌎  Regiones", "👥  Clientes", "📦  Productos", "⚠️  Descuentos", "📥  Reportes"]
)

with tab_overview:
    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Evolución de ventas y ganancias")
        temporal = df_filtered.set_index("Order Date").resample("MS").agg(
            Ventas=("Sales", "sum"), Ganancia=("Profit", "sum")
        ).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=temporal["Order Date"], y=temporal["Ventas"], name="Ventas", mode="lines+markers", line=dict(color=BLUE, width=3), fill="tozeroy", fillcolor="rgba(37,99,235,.08)"))
        fig.add_trace(go.Scatter(x=temporal["Order Date"], y=temporal["Ganancia"], name="Ganancia neta", mode="lines+markers", line=dict(color=GREEN, width=2.5, dash="dot")))
        fig.update_layout(hovermode="x unified", yaxis_title="Importe ($)", xaxis_title=None)
        st.plotly_chart(style_chart(fig, 380), use_container_width=True)
    with right:
        st.subheader("¿Cuánto valen las ventas?")
        fig_hist = px.histogram(df_filtered, x="Sales", nbins=35, color_discrete_sequence=[BLUE], labels={"Sales": "Importe de venta", "count": "Transacciones"})
        fig_hist.update_traces(marker_line_color="white", marker_line_width=1)
        fig_hist.update_layout(xaxis_title="Importe ($)", yaxis_title="Número de transacciones")
        st.plotly_chart(style_chart(fig_hist, 380), use_container_width=True)

    st.subheader("Rendimiento por categoría")
    if "Category" in df_filtered:
        category_data = df_filtered.groupby("Category", as_index=False).agg(Ventas=("Sales", "sum"), Ganancia=("Profit", "sum"))
        cat_col1, cat_col2 = st.columns([1, 1.4])
        with cat_col1:
            fig_cat = px.pie(category_data, values="Ventas", names="Category", hole=.68, color_discrete_sequence=px.colors.qualitative.Set2)
            fig_cat.update_layout(showlegend=True, legend=dict(orientation="h", y=-.12))
            st.plotly_chart(style_chart(fig_cat, 320), use_container_width=True)
        with cat_col2:
            fig_cat_bar = px.bar(category_data.sort_values("Ventas"), x="Ventas", y="Category", orientation="h", color="Ganancia", color_continuous_scale="Blues", labels={"Category": "Categoría", "Ventas": "Ventas ($)"})
            st.plotly_chart(style_chart(fig_cat_bar, 320), use_container_width=True)

with tab_region:
    region_col, state_col = st.columns(2)
    with region_col:
        st.subheader("Ventas por región")
        if "Region" in df_filtered:
            region_sales = df_filtered.groupby("Region", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False)
            fig_region = px.pie(region_sales, values="Sales", names="Region", hole=.58, color_discrete_sequence=px.colors.qualitative.Bold)
            fig_region.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(style_chart(fig_region, 390), use_container_width=True)
    with state_col:
        st.subheader("Ganancia neta por estado")
        if "State" in df_filtered:
            state_profit = df_filtered.groupby("State", as_index=False)["Profit"].sum().sort_values("Profit", ascending=True).tail(15)
            fig_state = px.bar(state_profit, x="Profit", y="State", orientation="h", color="Profit", color_continuous_scale="RdYlGn", labels={"Profit": "Ganancia ($)"})
            st.plotly_chart(style_chart(fig_state, 440), use_container_width=True)
    if "Region" in df_filtered:
        st.subheader("Detalle regional")
        region_summary = df_filtered.groupby("Region", as_index=False).agg(Ventas=("Sales", "sum"), Ganancia=("Profit", "sum"), Pedidos=("Order ID-1", "nunique") if "Order ID-1" in df_filtered else ("Sales", "count"))
        st.dataframe(region_summary.style.format({"Ventas": "${:,.2f}", "Ganancia": "${:,.2f}", "Pedidos": "{:,.0f}"}), use_container_width=True, hide_index=True)

with tab_customers:
    st.subheader("Clientes con mayor aportación")
    st.caption("Identifica tus cuentas principales por ventas y contribución a la ganancia.")
    if "Customer Name" in df_filtered:
        customer_summary = df_filtered.groupby("Customer Name", as_index=False).agg(
            Ventas=("Sales", "sum"), Ganancia=("Profit", "sum"),
            Transacciones=("Quantity", "count") if "Quantity" in df_filtered else ("Sales", "count"),
        ).sort_values("Ventas", ascending=False).head(15)
        customer_summary["Participación"] = customer_summary["Ventas"] / sales_total if sales_total else 0
        customer_summary = customer_summary.rename(columns={"Customer Name": "Cliente"})
        st.dataframe(customer_summary.style.format({"Ventas": "${:,.2f}", "Ganancia": "${:,.2f}", "Participación": "{:.1%}"}), use_container_width=True, hide_index=True)
    st.info("El archivo de origen no incluye información de vendedores. Para analizar el rendimiento del equipo comercial, agrega esa dimensión a los datos.")

with tab_products:
    if "Product Name" in df_filtered:
        product_summary = df_filtered.groupby("Product Name", as_index=False).agg(Ventas=("Sales", "sum"), Ganancia=("Profit", "sum"), Unidades=("Quantity", "sum") if "Quantity" in df_filtered else ("Sales", "count"))
        col_profit, col_loss = st.columns(2)
        with col_profit:
            st.subheader("Productos más rentables")
            best = product_summary.nlargest(10, "Ganancia").sort_values("Ganancia")
            fig_best = px.bar(best, x="Ganancia", y="Product Name", orientation="h", color="Ganancia", color_continuous_scale="Greens", labels={"Product Name": "Producto", "Ganancia": "Ganancia ($)"})
            st.plotly_chart(style_chart(fig_best, 430), use_container_width=True)
        with col_loss:
            st.subheader("Productos con mayor pérdida")
            worst = product_summary.nsmallest(10, "Ganancia").sort_values("Ganancia")
            fig_worst = px.bar(worst, x="Ganancia", y="Product Name", orientation="h", color="Ganancia", color_continuous_scale="Reds", labels={"Product Name": "Producto", "Ganancia": "Ganancia ($)"})
            st.plotly_chart(style_chart(fig_worst, 430), use_container_width=True)
        st.subheader("Resumen de productos")
        st.dataframe(product_summary.sort_values("Ventas", ascending=False).head(20).style.format({"Ventas": "${:,.2f}", "Ganancia": "${:,.2f}", "Unidades": "{:,.0f}"}), use_container_width=True, hide_index=True)

with tab_losses:
    st.subheader("Descuentos y rentabilidad")
    st.caption("Explora cómo se relacionan los descuentos aplicados con el resultado de cada venta.")
    discount_col, scatter_col = st.columns([.8, 1.7])
    with discount_col:
        st.metric("Descuento medio", f"{df_filtered['Discount'].mean():.1%}")
        if "Sub-Category" in df_filtered:
            subcategory = df_filtered.groupby("Sub-Category", as_index=False).agg(Ganancia=("Profit", "sum"), Descuento=("Discount", "mean")).sort_values("Ganancia")
            st.dataframe(subcategory.style.format({"Ganancia": "${:,.2f}", "Descuento": "{:.1%}"}), use_container_width=True, hide_index=True)
    with scatter_col:
        if "Category" in df_filtered:
            fig_scatter = px.scatter(df_filtered, x="Discount", y="Profit", color="Category", opacity=.65, title="Descuento frente a ganancia por transacción", labels={"Discount": "Descuento", "Profit": "Ganancia ($)"}, hover_data=[c for c in ["Product Name", "Order Date"] if c in df_filtered])
        else:
            fig_scatter = px.scatter(df_filtered, x="Discount", y="Profit", opacity=.65, title="Descuento frente a ganancia por transacción", labels={"Discount": "Descuento", "Profit": "Ganancia ($)"})
        fig_scatter.update_xaxes(tickformat=".0%")
        st.plotly_chart(style_chart(fig_scatter, 430), use_container_width=True)

with tab_reports:
    st.subheader("Descarga tu reporte")
    st.markdown("Exporta la selección actual para compartirla o continuar el análisis en Excel.")
    @st.cache_data
    def to_excel(data: pd.DataFrame) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            data.to_excel(writer, index=False, sheet_name="Reporte de ventas")
            worksheet = writer.sheets["Reporte de ventas"]
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(0, 0, len(data), max(len(data.columns) - 1, 0))
        return output.getvalue()

    report_col, summary_col = st.columns([1, 1.5])
    with report_col:
        st.download_button(
            "⬇️ Descargar Excel filtrado",
            data=to_excel(df_filtered),
            file_name="reporte_ventas_filtrado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption(f"{len(df_filtered):,} filas · {len(df_filtered.columns)} columnas")
    with summary_col:
        st.markdown("#### Resumen de la selección")
        st.write(f"- **Período:** {start_date:%d/%m/%Y} – {end_date:%d/%m/%Y}")
        st.write(f"- **Ventas:** {money(sales_total)}")
        st.write(f"- **Ganancia neta:** {money(net_profit)} ({margin_pct:.1f}% de margen)")
        st.write(f"- **Unidades vendidas:** {quantity:,.0f}")

st.markdown("<div style='text-align:center;color:#8a96a9;font-size:.78rem;padding-top:2rem'>Sales Analytics · Dashboard de rendimiento comercial</div>", unsafe_allow_html=True)
