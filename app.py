%%writefile app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Corporate Sales Analytics Dashboard", page_icon="📊", layout="wide")

# Estilos CSS personalizados para tarjetas e indicadores modernos
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #007bff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 2. CARGA DE DATOS OPTIMIZADA
@st.cache_data
def load_data():
    file_path = 'SalidaVentas.xlsx'
    df = pd.read_excel(file_path)
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Ship Date'] = pd.to_datetime(df['Ship Date'])
    # Asegurar que nulos en Discount se traten como 0
    df['Discount'] = df['Discount'].fillna(0)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"❌ No se pudo cargar el archivo Excel en la ruta especificada. Error: {e}")
    st.stop()

# 3. BARRA LATERAL - FILTROS DINÁMICOS
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1006/1006193.png", width=80)
st.sidebar.title("Filtros de Control")

# Filtro de Fechas
min_date = df_raw['Order Date'].min().to_pydatetime()
max_date = df_raw['Order Date'].max().to_pydatetime()
fecha_seleccionada = st.sidebar.date_input(
    "Rango de Fechas",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Asegurar manejo correcto del rango
if isinstance(fecha_seleccionada, list) or isinstance(fecha_seleccionada, tuple):
    if len(fecha_seleccionada) == 2:
        start_date, end_date = pd.to_datetime(fecha_seleccionada[0]), pd.to_datetime(fecha_seleccionada[1])
    else:
        start_date, end_date = pd.to_datetime(fecha_seleccionada[0]), pd.to_datetime(max_date)
else:
    start_date, end_date = pd.to_datetime(fecha_seleccionada), pd.to_datetime(max_date)

# Filtrar inicialmente por fecha para actualizar filtros en cascada
df_fecha = df_raw[(df_raw['Order Date'] >= start_date) & (df_raw['Order Date'] <= end_date)]

# Filtros en Cascada
regiones_disponibles = sorted(df_fecha['Region'].dropna().unique())
regiones_selected = st.sidebar.multiselect("Región", options=regiones_disponibles, default=regiones_disponibles)

df_reg = df_fecha[df_fecha['Region'].isin(regiones_selected)]

estados_disponibles = sorted(df_reg['State'].dropna().unique())
estados_selected = st.sidebar.multiselect("Estado", options=estados_disponibles, default=estados_disponibles)

df_est = df_reg[df_reg['State'].isin(estados_selected)]

categorias_disponibles = sorted(df_est['Category'].dropna().unique())
categorias_selected = st.sidebar.multiselect("Categoría", options=categorias_disponibles, default=categorias_disponibles)

df_cat = df_est[df_est['Category'].isin(categorias_selected)]

clientes_disponibles = sorted(df_cat['Customer Name'].dropna().unique())
clientes_selected = st.sidebar.multiselect("Cliente", options=clientes_disponibles)

# DataFrame de Trabajo Final Filtrado
df_filtrado = df_cat.copy()
if clientes_selected:
    df_filtrado = df_filtrado[df_filtrado['Customer Name'].isin(clientes_selected)]

# 4. CUERPO PRINCIPAL
st.title("📊 Corporate Sales Analytics Portal")
st.markdown("Plataforma inteligente de visualización y monitoreo operativo de ventas, rendimiento y rentabilidad transaccional.")

# 5. RESUMEN GENERAL (KPIs)
if df_filtrado.empty:
    st.warning("⚠️ No hay registros que coincidan con la selección de filtros actual.")
    st.stop()

ventas_totales = df_filtrado['Sales'].sum()
ganancias_totales = df_filtrado['Profit'].clip(lower=0).sum() # Sólo ganancias positivas
perdidas_totales = abs(df_filtrado['Profit'].clip(upper=0).sum()) # Pérdidas absolutas
rentabilidad_neta = df_filtrado['Profit'].sum()
cantidad_pedidos = df_filtrado['Order ID-1'].nunique()
productos_vendidos = df_filtrado['Quantity'].sum()
rentabilidad_porcentaje = (rentabilidad_neta / ventas_totales * 100) if ventas_totales > 0 else 0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.markdown(f'<div class="metric-card"><h5>Ventas Totales</h5><h3>${ventas_totales:,.2f}</h3></div>', unsafe_allow_html=True)
with kpi2:
    st.markdown(f'<div class="metric-card"><h5>Ganancias</h5><h3 style="color:green;">${ganancias_totales:,.2f}</h3></div>', unsafe_allow_html=True)
with kpi3:
    st.markdown(f'<div class="metric-card"><h5>Pérdidas</h5><h3 style="color:red;">-${perdidas_totales:,.2f}</h3></div>', unsafe_allow_html=True)
with kpi4:
    st.markdown(f'<div class="metric-card"><h5>Pedidos Realizados</h5><h3>{cantidad_pedidos:,}</h3></div>', unsafe_allow_html=True)
with kpi5:
    st.markdown(f'<div class="metric-card"><h5>Margen de Retorno</h5><h3>{rentabilidad_porcentaje:.2f}%</h3></div>', unsafe_allow_html=True)

# Creación de Pestañas (Tabs) de Análisis
tab_resumen, tab_region, tab_vendedores, tab_productos, tab_perdidas, tab_exportar = st.tabs([
    "📈 Tendencias y Distribuciones", 
    "🗺️ Análisis Regional", 
    "👥 Clientes y Fuerza de Venta",
    "📦 Productos",
    "⚠️ Diagnóstico de Pérdidas",
    "📥 Descarga de Reportes"
])

# --- PESTAÑA 1: TENDENCIAS Y DISTRIBUCIONES ---
with tab_resumen:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Evolución Histórica de Ventas y Ganancias")
        df_temporal = df_filtrado.groupby(df_filtrado['Order Date'].dt.to_period('M')).agg(
            Ventas=('Sales', 'sum'),
            Profit=('Profit', 'sum')
        ).reset_index()
        df_temporal['Order Date'] = df_temporal['Order Date'].dt.to_timestamp()
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=df_temporal['Order Date'], y=df_temporal['Ventas'], name='Ventas', line=dict(color='blue')))
        fig_line.add_trace(go.Scatter(x=df_temporal['Order Date'], y=df_temporal['Profit'], name='Margen (Profit)', line=dict(color='green')))
        st.plotly_chart(fig_line, use_container_width=True)
        
    with col_t2:
        st.subheader("Distribución del Valor de Transacciones")
        fig_hist = px.histogram(
            df_filtrado, 
            x='Sales', 
            nbins=50, 
            log_y=True, 
            title="Distribución de Ventas (Escala Logarítmica en Frecuencia)",
            color_discrete_sequence=['royalblue']
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# --- PESTAÑA 2: ANÁLISIS REGIONAL ---
with tab_region:
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("Distribución de Ventas por Región")
        region_sales = df_filtrado.groupby('Region')['Sales'].sum().reset_index()
        fig_pie = px.pie(region_sales, values='Sales', names='Region', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_r2:
        st.subheader("Margen de Ganancias por Estado")
        region_profit = df_filtrado.groupby('State')['Profit'].sum().reset_index().sort_values(by='Profit', ascending=False)
        fig_bar_reg = px.bar(region_profit, x='State', y='Profit', color='Profit', color_continuous_scale='Viridis')
        st.plotly_chart(fig_bar_reg, use_container_width=True)

# --- PESTAÑA 3: CLIENTES Y VENDEDORES ---
with tab_vendedores:
    st.subheader("Análisis del Personal Comercial (Vendedores)")
    st.info("ℹ️ **Limitación de Datos:** El archivo original `SalidaVentas.xlsx` no cuenta con una columna que detalle el nombre de los vendedores asociados a cada transacción (únicamente registra campos relacionados con el cliente, aprobador de devoluciones e ID del producto). Se sugiere evitar la confusión de los registros de clientes con asesores comerciales.")
    
    st.markdown("---")
    st.subheader("Top Clientes con Mayor Aportación de Valor")
    top_clientes = df_filtrado.groupby('Customer Name').agg(
        Compras_Totales=('Sales', 'sum'),
        Rentabilidad_Aportada=('Profit', 'sum'),
        Transacciones=('Quantity', 'count')
    ).sort_values(by='Compras_Totales', ascending=False).head(15).reset_index()
    
    top_clientes['Participacion_%'] = (top_clientes['Compras_Totales'] / ventas_totales) * 100
    st.dataframe(top_clientes.style.format({
        'Compras_Totales': '${:,.2f}',
        'Rentabilidad_Aportada': '${:,.2f}',
        'Participacion_%': '{:.2f}%'
    }))

# --- PESTAÑA 4: PRODUCTOS ---
with tab_productos:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("Top 10 Productos con Mayores Ganancias")
        top_prod_ganancia = df_filtrado.groupby('Product Name')['Profit'].sum().reset_index().sort_values(by='Profit', ascending=False).head(10)
        fig_top_p = px.bar(top_prod_ganancia, x='Profit', y='Product Name', orientation='h', color='Profit', color_continuous_scale='Greens')
        st.plotly_chart(fig_top_p, use_container_width=True)
        
    with col_p2:
        st.subheader("Top 10 Productos Generadores de Pérdidas")
        top_prod_perdida = df_filtrado.groupby('Product Name')['Profit'].sum().reset_index().sort_values(by='Profit', ascending=True).head(10)
        fig_low_p = px.bar(top_prod_perdida, x='Profit', y='Product Name', orientation='h', color='Profit', color_continuous_scale='Reds')
        st.plotly_chart(fig_low_p, use_container_width=True)

# --- PESTAÑA 5: DIAGNÓSTICO DE PÉRDIDAS ---
with tab_perdidas:
    st.subheader("Correlación entre Descuentos Aplicados y Rentabilidad")
    st.write("A continuación analizamos de qué manera influyen las políticas agresivas de descuento comercial en la pérdida directa de utilidad.")
    
    col_per1, col_per2 = st.columns([1, 2])
    with col_per1:
        st.metric("Tasa Media de Descuento General", f"{df_filtrado['Discount'].mean()*100:.2f}%")
        # Analizar subcategorías que sufren por descuentos
        sub_descuento = df_filtrado.groupby('Sub-Category').agg(
            Margen_Total=('Profit', 'sum'),
            Descuento_Medio=('Discount', 'mean')
        ).sort_values(by='Margen_Total').reset_index()
        st.dataframe(sub_descuento.style.format({
            'Margen_Total': '${:,.2f}',
            'Descuento_Medio': '{:.2%}'
        }))
        
    with col_per2:
        fig_scat = px.scatter(
            df_filtrado, 
            x='Discount', 
            y='Profit', 
            color='Category', 
            trendline='ols',
            title="Relación de Pérdida Transaccional vs Porcentaje de Descuento"
        )
        st.plotly_chart(fig_scat, use_container_width=True)

# --- PESTAÑA 6: EXPORTACIÓN Y CONCLUSIONES ---
with tab_exportar:
    st.subheader("Generación de Reportes Ejecutivos")
    st.markdown("Descarga los registros filtrados actuales en formato Excel para un análisis complementario off-line.")
    
    # Función de descarga en búfer de memoria
    def to_excel(df_in):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_in.to_excel(writer, index=False, sheet_name='ReporteVentas')
        processed_data = output.getvalue()
        return processed_data
        
    excel_data = to_excel(df_filtrado)
    st.download_button(
        label="📥 Descargar Data Filtrada en Excel",
        data=excel_data,
        file_name='Reporte_Ventas_Filtrado.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    st.markdown("---")
    st.subheader("🎯 Conclusiones y Recomendaciones Clave")
    st.markdown("""
    * **Control de Políticas de Descuento:** Existe una correlación negativa directa entre el volumen de descuento aplicado y el margen neto. Se sugiere fijar límites de descuento estrictos para la región West (específicamente en estados de alto volumen con pérdidas como Colorado, Oregon y Arizona).
    * **Estrategia en Tecnología y Muebles:** Segmentos como máquinas y mesas demandan revisiones de su estructura de precios antes de autorizar descuentos comerciales.
    * **Optimización Comercial:** Al no contarse con un registro de agentes/vendedores dentro del set de datos original, se recomienda incorporar esta variable en sistemas de captura futuros para poder ligar e incentivar la efectividad de la fuerza comercial.
    """)

        st.dataframe(df_filtrado[['State', 'Category', 'Sub-Category', 'Sales', 'Profit', 'Discount']].head(100))

exceppt Exception as e:
    st.error(f"Error al cargar los datos: {e}")
