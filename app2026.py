import sqlite3
import datetime
import io
import random
import pandas as pd
import streamlit as st
import plotly.express as px

# Módulos de ReportLab para la exportación PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS
# ==========================================
st.set_page_config(
    page_title="Gestión de Inventario Hogar",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fondo de frutas dispersas y con transparencia aleatoria
FRUITS = ['🍎', '🍌', '🍊', '🍐', '🍓', '🍏', '🍉', '🍇', '🍋', '🍒', '🍑', '🍍', '🥑', '🫐', '🥝']
random.seed(42)
fruits_html_list = []

for _ in range(28):
    fruit = random.choice(FRUITS)
    top = random.randint(2, 92)
    left = random.randint(2, 92)
    size = round(random.uniform(2.5, 6.5), 1)
    rotate = random.randint(-35, 35)
    fruits_html_list.append(
        f'<div style="position: absolute; top: {top}vh; left: {left}vw; font-size: {size}rem; transform: rotate({rotate}deg);">{fruit}</div>'
    )

bg_fruits_html = "".join(fruits_html_list)

CUSTOM_CSS = f"""
<style>
    /* Estilos globales: tonos verdes suaves y limpios */
    .stApp {{
        background-color: #f4f8f5;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #2b3a30;
    }}
    
    /* Fondo de frutas dispersas y con transparencia */
    .bg-fruits-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 0;
        opacity: 0.10;
        overflow: hidden;
    }}

    /* Contenido por encima del fondo */
    [data-testid="stAppViewContainer"] > .main {{
        position: relative;
        z-index: 1;
    }}
    
    /* Tarjetas de métricas prolijas */
    .metric-card {{
        background: #ffffff;
        border: 1px solid #d8e6dc;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
        border-left: 4px solid #52796f;
        margin-bottom: 10px;
    }}
    .metric-card-title {{
        color: #6b8a7a;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .metric-card-value {{
        color: #1b4332;
        font-size: 1.8rem;
        font-weight: 800;
        margin-top: 4px;
    }}
    
    /* Badges de estado */
    .badge-disponible {{
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
        border: 1px solid #c8e6c9;
    }}
    .badge-poco {{
        background-color: #fff8e1;
        color: #f57f17;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
        border: 1px solid #ffe082;
    }}
    .badge-agotado {{
        background-color: #ffebee;
        color: #c62828;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
        border: 1px solid #ffcdd2;
    }}

    /* Barra lateral en tonos verdes */
    [data-testid="stSidebar"] {{
        background-color: #e8f5e9 !important;
        border-right: 2px solid #a5d6a7;
        padding: 20px 10px;
    }}
    
    /* Ocultar el label de la barra lateral */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
        display: none;
    }}

    /* Menú lateral */
    div[role="radiogroup"] > label {{
        background-color: #ffffff;
        border: 1px solid #a5d6a7;
        padding: 10px 14px !important;
        margin-bottom: 8px !important;
        border-radius: 10px !important;
        font-weight: 600;
        color: #1b4332;
    }}
    div[role="radiogroup"] > label:hover {{
        border-color: #2e7d32;
        background-color: #c8e6c9;
    }}
    
    /* Botones principales estilizados */
    .stButton > button {{
        border-radius: 8px;
        border: 1px solid #a3c9ad;
        background-color: #ffffff;
        color: #2e7d32;
        font-weight: 600;
        padding: 6px 14px;
    }}
    .stButton > button:hover {{
        background-color: #52796f;
        color: #ffffff;
        border-color: #52796f;
    }}

    /* Ocultar elementos predeterminados */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Animación de 5 segundos */
    .fruits-falling-container {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 9999;
        overflow: hidden;
        animation: fadeOut 0.5s ease 4.8s forwards;
    }}

    .fruit-item {{
        position: absolute;
        top: -80px;
        font-size: 2.2rem;
        animation: fall 4.5s linear 1 forwards;
    }}

    @keyframes fall {{
        0% {{ transform: translateY(0) rotate(0deg); opacity: 1; }}
        90% {{ opacity: 1; }}
        100% {{ transform: translateY(105vh) rotate(360deg); opacity: 0; }}
    }}

    @keyframes fadeOut {{
        to {{ opacity: 0; visibility: hidden; }}
    }}
</style>

<div class="bg-fruits-overlay">
    {bg_fruits_html}
</div>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DB_FILE = "inventario_hogar.db"

# ==========================================
# 2. CAPA DE BASE DE DATOS (SQLITE)
# ==========================================
def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Elimina la tabla previa si existe para resetear la base de datos limpia
        cursor.execute("DROP TABLE IF EXISTS productos")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                cantidad REAL NOT NULL DEFAULT 0,
                unidad TEXT NOT NULL,
                minimo REAL NOT NULL DEFAULT 1,
                ultima_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                descripcion TEXT NOT NULL
            )
        """)
        conn.commit()

def registrar_log(descripcion):
    with get_connection() as conn:
        conn.cursor().execute("INSERT INTO historial (descripcion) VALUES (?)", (descripcion,))
        conn.commit()

def obtener_productos():
    query = """
        SELECT id, nombre, cantidad, unidad, minimo, ultima_modificacion,
               CASE 
                   WHEN cantidad == 0 THEN 'Agotado'
                   WHEN cantidad <= minimo THEN 'Poco Stock'
                   ELSE 'Disponible'
               END as estado
        FROM productos
        ORDER BY nombre ASC
    """
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn)
    return df

def agregar_producto(nombre, cantidad, unidad, minimo):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO productos (nombre, cantidad, unidad, minimo)
            VALUES (?, ?, ?, ?)
        """, (nombre, cantidad, unidad, minimo))
        conn.commit()
    registrar_log(f"Se creó el producto '{nombre}' con {cantidad} {unidad}.")

def editar_producto_db(prod_id, nombre, cantidad, unidad, minimo):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE productos
            SET nombre = ?, cantidad = ?, unidad = ?, minimo = ?, ultima_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (nombre, cantidad, unidad, minimo, prod_id))
        conn.commit()
    registrar_log(f"Producto actualizado: '{nombre}'.")

def actualizar_stock(prod_id, nuevo_stock, nombre_producto):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE productos 
            SET cantidad = ?, ultima_modificacion = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (nuevo_stock, prod_id))
        conn.commit()
    
    estado = "Agotado" if nuevo_stock == 0 else ("Poco Stock" if nuevo_stock <= 1 else "Disponible")
    registrar_log(f"Stock actualizado de '{nombre_producto}' a {nuevo_stock} (Estado: {estado}).")

def eliminar_producto(prod_id, nombre_producto):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM productos WHERE id = ?", (prod_id,))
        conn.commit()
    registrar_log(f"Producto eliminado: '{nombre_producto}'.")

# ==========================================
# 3. GENERADOR DE REPORTES PDF (REPORTLAB)
# ==========================================
def generar_pdf_lista_compras(df_faltantes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2e7d32'),
        spaceAfter=10
    )
    
    story.append(Paragraph("Lista de Compras del Hogar", title_style))
    fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"<b>Fecha de emisión:</b> {fecha_str}", styles['Normal']))
    story.append(Spacer(1, 15))
    
    data = [["[  ]", "Producto", "Stock Actual", "Notas"]]
    for _, row in df_faltantes.iterrows():
        stock_text = f"{row['cantidad']} {row['unidad']}"
        data.append(["[  ]", row['nombre'], stock_text, ""])
    
    t = Table(data, colWidths=[40, 220, 120, 170])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e8f5e9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1b4332')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#c8e6c9')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

def animacion_frutas_5s():
    html_code = """
    <div class="fruits-falling-container">
        <div class="fruit-item" style="left: 8%;">🍎</div>
        <div class="fruit-item" style="left: 24%; animation-delay: 0.3s;">🍌</div>
        <div class="fruit-item" style="left: 40%; animation-delay: 0.1s;">🍊</div>
        <div class="fruit-item" style="left: 58%; animation-delay: 0.4s;">🍐</div>
        <div class="fruit-item" style="left: 74%; animation-delay: 0.2s;">🍓</div>
        <div class="fruit-item" style="left: 88%; animation-delay: 0.5s;">🍏</div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)

# ==========================================
# 4. APLICACIÓN Y NAVEGACIÓN PRINCIPAL
# ==========================================
init_db()

st.sidebar.markdown("### Inventario Hogar")
opcion_menu = st.sidebar.radio(
    "",
    [
        "Panel Central",
        "Inventario Principal",
        "Añadir Alimento",
        "Editar Alimento",
        "Lista de Compras & PDF"
    ]
)

# ------------------------------------------
# MÓDULO 1: PANEL CENTRAL
# ------------------------------------------
if opcion_menu == "Panel Central":
    animacion_frutas_5s()
    
    st.header("Panel Central")
    df = obtener_productos()
    
    total = len(df)
    disponibles = len(df[df['estado'] == 'Disponible'])
    poco_stock = len(df[df['estado'] == 'Poco Stock'])
    agotados = len(df[df['estado'] == 'Agotado'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="metric-card"><div class="metric-card-title">Total Alimentos</div><div class="metric-card-value">{total}</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><div class="metric-card-title">Disponibles</div><div class="metric-card-value" style="color:#2e7d32;">{disponibles}</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><div class="metric-card-title">Poco Stock</div><div class="metric-card-value" style="color:#f57f17;">{poco_stock}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="metric-card"><div class="metric-card-title">Agotados</div><div class="metric-card-value" style="color:#c62828;">{agotados}</div></div>', unsafe_allow_html=True)
    
    st.divider()
    
    if not df.empty:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            with st.container(border=True):
                st.markdown("**Estado del Inventario**")
                estado_counts = df['estado'].value_counts().reset_index()
                estado_counts.columns = ['Estado', 'Cantidad']
                
                color_map = {'Disponible': '#2e7d32', 'Poco Stock': '#f57f17', 'Agotado': '#c62828'}
                fig1 = px.pie(estado_counts, values='Cantidad', names='Estado', hole=0.5,
                              color='Estado', color_discrete_map=color_map)
                fig1.update_traces(textposition='inside', textinfo='percent+label')
                fig1.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=220, showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)

        with col_chart2:
            with st.container(border=True):
                # Nuevo widget: lista directa de productos sin stock
                st.markdown("**Productos Agotados**")
                df_agotados = df[df['estado'] == 'Agotado']
                if not df_agotados.empty:
                    st.error(f"Hay {len(df_agotados)} alimento(s) sin stock:")
                    st.dataframe(df_agotados[['nombre', 'unidad']], use_container_width=True)
                else:
                    st.info("No hay alimentos agotados actualmente.")
    else:
        st.info("La base de datos está vacía. Añade productos desde el menú lateral.")

# ------------------------------------------
# MÓDULO 2: INVENTARIO PRINCIPAL
# ------------------------------------------
elif opcion_menu == "Inventario Principal":
    st.header("Gestión de Inventario")
    df = obtener_productos()
    
    with st.container(border=True):
        col_search, col_est = st.columns([3, 1])
        with col_search:
            busqueda = st.text_input("Buscar alimento por nombre:", "")
        with col_est:
            est_filtro = st.selectbox("Estado:", ["Todos", "Disponible", "Poco Stock", "Agotado"])
        
    if busqueda:
        df = df[df['nombre'].str.contains(busqueda, case=False, na=False)]
    if est_filtro != "Todos":
        df = df[df['estado'] == est_filtro]
        
    st.divider()
    
    if df.empty:
        st.warning("No se encontraron productos en la base de datos.")
    else:
        for idx, row in df.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([4, 2, 2, 2, 2])
                c1.markdown(f"**{row['nombre']}**")
                
                badge = f"<span class='badge-{row['estado'].lower().replace(' ', '')}'>{row['estado']}</span>"
                c2.markdown(badge, unsafe_allow_html=True)
                
                c3.write(f"Stock: **{row['cantidad']}** {row['unidad']}")
                
                if c4.button("+ 1", key=f"add_{row['id']}"):
                    actualizar_stock(row['id'], row['cantidad'] + 1, row['nombre'])
                    st.rerun()
                if c5.button("- 1", key=f"sub_{row['id']}"):
                    nueva_cant = max(0.0, row['cantidad'] - 1)
                    actualizar_stock(row['id'], nueva_cant, row['nombre'])
                    st.rerun()

# ------------------------------------------
# MÓDULO 3: AÑADIR ALIMENTO
# ------------------------------------------
elif opcion_menu == "Añadir Alimento":
    st.header("Añadir Nuevo Alimento")
    
    with st.container(border=True):
        with st.form("form_anadir_producto", clear_on_submit=True):
            nombre = st.text_input("Nombre del alimento:").strip()
            
            col_qty, col_unit, col_min = st.columns(3)
            with col_qty:
                cantidad = st.number_input("Cantidad inicial:", min_value=0.0, step=1.0, value=1.0)
            with col_unit:
                unidad = st.selectbox("Unidad:", ["Unidades", "Kg", "Gramos", "Litros", "Packs", "Cajas"])
            with col_min:
                minimo = st.number_input("Stock mínimo (alerta):", min_value=0.0, step=1.0, value=1.0)
            
            submitted = st.form_submit_button("Guardar Alimento")
            
            if submitted:
                if not nombre:
                    st.error("El nombre del alimento es obligatorio.")
                else:
                    agregar_producto(nombre, cantidad, unidad, minimo)
                    st.success(f"Producto '{nombre}' guardado exitosamente.")

# ------------------------------------------
# MÓDULO 4: EDITAR ALIMENTO
# ------------------------------------------
elif opcion_menu == "Editar Alimento":
    st.header("Editar Alimento Existente")
    df_prod = obtener_productos()
    
    if df_prod.empty:
        st.info("No hay productos registrados para editar.")
    else:
        with st.container(border=True):
            producto_sel_nombre = st.selectbox("Seleccione el producto a editar:", df_prod['nombre'].values)
            prod_data = df_prod[df_prod['nombre'] == producto_sel_nombre].iloc[0]
            
            with st.form("form_editar_producto"):
                nuevo_nombre = st.text_input("Nombre del alimento:", value=prod_data['nombre']).strip()
                
                col_qty, col_unit, col_min = st.columns(3)
                with col_qty:
                    cantidad = st.number_input("Cantidad:", min_value=0.0, step=1.0, value=float(prod_data['cantidad']))
                with col_unit:
                    unidades_lista = ["Unidades", "Kg", "Gramos", "Litros", "Packs", "Cajas"]
                    idx_u = unidades_lista.index(prod_data['unidad']) if prod_data['unidad'] in unidades_lista else 0
                    unidad = st.selectbox("Unidad:", unidades_lista, index=idx_u)
                with col_min:
                    minimo = st.number_input("Stock mínimo:", min_value=0.0, step=1.0, value=float(prod_data['minimo']))
                
                btn_guardar = st.form_submit_button("Actualizar Alimento")
                
                if btn_guardar:
                    if not nuevo_nombre:
                        st.error("El nombre no puede estar vacío.")
                    else:
                        editar_producto_db(prod_data['id'], nuevo_nombre, cantidad, unidad, minimo)
                        st.success("Producto actualizado correctamente.")
                        st.rerun()

            st.divider()
            if st.button("Eliminar Producto"):
                eliminar_producto(prod_data['id'], prod_data['nombre'])
                st.success(f"Producto '{prod_data['nombre']}' eliminado.")
                st.rerun()

# ------------------------------------------
# MÓDULO 5: LISTA DE COMPRAS Y PDF
# ------------------------------------------
elif opcion_menu == "Lista de Compras & PDF":
    st.header("Lista de Compras Automática")
    df = obtener_productos()
    
    df_faltantes = df[df['estado'].isin(['Agotado', 'Poco Stock'])].copy()
    
    with st.container(border=True):
        if df_faltantes.empty:
            st.success("No tienes productos faltantes ni con poco stock.")
        else:
            st.warning(f"Se encontraron {len(df_faltantes)} productos que requieren reposición.")
            st.dataframe(df_faltantes[['nombre', 'cantidad', 'unidad', 'estado']], use_container_width=True)
            
            pdf_buffer = generar_pdf_lista_compras(df_faltantes)
            
            st.download_button(
                label="Descargar Lista de Compras en PDF",
                data=pdf_buffer,
                file_name=f"lista_compras_{datetime.date.today()}.pdf",
                mime="application/pdf"
            ) 