%%writefile app.py
import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="Análisis de Pérdidas - Región West", layout="wide")

st.title("🔍 Diagnóstico de Pérdidas y Descuentos - Región West")
st.markdown("Esta aplicación permite investigar las causas raíz de las pérdidas financieras en estados críticos como Colorado, Arizona y Oregon.")

# Cargar datos
@st.cache_data
def load_data():
    file_path = 'SalidaVentas.xlsx'
    df = pd.read_excel(file_path)
    df_west = df[df['Region'] == 'West'].copy()
    return df_west

try:
    df_west = load_data()
    
    # Sidebar - Filtros
    st.sidebar.header("Filtros de Análisis")
    estados_por_defecto = ['Colorado', 'Arizona', 'Oregon']
    estados_disponibles = sorted(df_west['State'].unique())
    
    estados_seleccionados = st.sidebar.multiselect(
        "Selecciona los Estados a analizar:",
        options=estados_disponibles,
        default=[e for e in estados_por_defecto if e in estados_disponibles]
    )
    
    if not estados_seleccionados:
        st.warning("Por favor, selecciona al menos un estado en la barra lateral.")
    else:
        # Filtrar datos según selección
        df_filtrado = df_west[df_west['State'].isin(estados_seleccionados)]
        
        # Métricas principales
        ventas_totales = df_filtrado['Sales'].sum()
        ganancias_totales = df_filtrado['Profit'].sum()
        descuento_promedio = df_filtrado['Discount'].mean() * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Ventas Totales", f"${ventas_totales:,.2f}")
        col2.metric("Ganancias / Pérdidas Totales", f"${ganancias_totales:,.2f}", delta=f"{ganancias_totales:,.2f}")
        col3.metric("Descuento Promedio", f"{descuento_promedio:.2f}%")
        
        st.markdown("---")
        
        # Agrupación por subcategoría
        df_subcat = df_filtrado.groupby(['Category', 'Sub-Category']).agg(
            Ventas=('Sales', 'sum'),
            Ganancias=('Profit', 'sum'),
            Descuento_Medio=('Discount', 'mean')
        ).reset_index().sort_values(by='Ganancias')
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Desempeño Financiero por Subcategoría")
            fig_profit = px.bar(
                df_subcat.head(10),
                x='Ganancias',
                y='Sub-Category',
                color='Category',
                orientation='h',
                title="Top 10 Subcategorías con Mayor Impacto en el Margen",
                labels={'Ganancias': 'Ganancias Netas ($)', 'Sub-Category': 'Subcategoría'}
            )
            fig_profit.add_vline(x=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_profit, use_container_width=True)
            
        with col_graf2:
            st.subheader("Nivel de Descuento Promedio Aplicado")
            fig_disc = px.bar(
                df_subcat.head(10),
                x='Descuento_Medio',
                y='Sub-Category',
                color='Descuento_Medio',
                orientation='h',
                color_continuous_scale='Reds',
                title="Descuento Medio por Subcategoría Crítica",
                labels={'Descuento_Medio': 'Descuento Medio (Decimal)', 'Sub-Category': 'Subcategoría'}
            )
            st.plotly_chart(fig_disc, use_container_width=True)
            
        # Tabla de datos detallados
        st.subheader("Datos de Transacciones Detalladas")
        st.dataframe(df_filtrado[['State', 'Category', 'Sub-Category', 'Sales', 'Profit', 'Discount']].head(100))

exceppt Exception as e:
    st.error(f"Error al cargar los datos: {e}")
