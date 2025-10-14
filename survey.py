import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import math
from io import BytesIO
import base64
import simplekml

# Configuración de la página
st.set_page_config(page_title="Site Survey - Telecomunicaciones", layout="wide", initial_sidebar_state="collapsed")

# Inicialización de session state
if 'project_name' not in st.session_state:
    st.session_state.project_name = ""
if 'task_name' not in st.session_state:
    st.session_state.task_name = ""
if 'elements' not in st.session_state:
    st.session_state.elements = []
if 'connections' not in st.session_state:
    st.session_state.connections = []
if 'temp_location' not in st.session_state:
    st.session_state.temp_location = None
if 'element_counters' not in st.session_state:
    st.session_state.element_counters = {'P': 0, 'HH': 0, 'CE': 0, 'BLD': 0}
if 'show_element_form' not in st.session_state:
    st.session_state.show_element_form = False
if 'map_center' not in st.session_state:
    st.session_state.map_center = [31.6904, -106.4245]
if 'auto_connect' not in st.session_state:
    st.session_state.auto_connect = True
if 'user_location' not in st.session_state:
    st.session_state.user_location = None
if 'selected_map_layer' not in st.session_state:
    st.session_state.selected_map_layer = 'hybrid'

# Funciones
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_next_element_name(element_type):
    prefix_map = {'Poste': 'P', 'Handhole': 'HH', 'Cierre de Empalme': 'CE', 'Edificio': 'BLD'}
    prefix = prefix_map[element_type]
    st.session_state.element_counters[prefix] += 1
    return f"{st.session_state.project_name}_{prefix}{st.session_state.element_counters[prefix]:03d}"

def get_element_style(element_type):
    styles = {
        'Poste': {'color': 'red', 'icon': 'plug'},
        'Handhole': {'color': 'blue', 'icon': 'square'},
        'Cierre de Empalme': {'color': 'green', 'icon': 'link'},
        'Edificio': {'color': 'orange', 'icon': 'building'}
    }
    return styles.get(element_type, {'color': 'gray', 'icon': 'circle'})

def suggest_construction_type(elem_a_type, elem_b_type):
    if elem_a_type == 'Handhole' and elem_b_type == 'Handhole':
        return 'Ducto'
    elif elem_a_type == 'Poste' and elem_b_type == 'Poste':
        return 'Aerial Route'
    elif ('Poste' in [elem_a_type, elem_b_type] and 'Handhole' in [elem_a_type, elem_b_type]):
        return 'Ducto'
    elif ('Edificio' in [elem_a_type, elem_b_type] and 'Handhole' in [elem_a_type, elem_b_type]):
        return 'Ducto'
    return 'Aerial Route'

def create_auto_connection(prev_elem, curr_elem):
    distance = calculate_distance(prev_elem['lat'], prev_elem['lon'], curr_elem['lat'], curr_elem['lon'])
    construction_type = suggest_construction_type(prev_elem['type'], curr_elem['type'])
    new_connection = {
        'element_a': prev_elem['name'],
        'element_b': curr_elem['name'],
        'construction_type': construction_type,
        'infraestructura': 'Nuevo',
        'distance': distance
    }
    st.session_state.connections.append(new_connection)
    return new_connection

def export_to_kml():
    kml = simplekml.Kml()
    for elem in st.session_state.elements:
        pnt = kml.newpoint(name=elem['name'], coords=[(elem['lon'], elem['lat'])])
        if elem['type'] == 'Poste':
            pnt.style.iconstyle.color = simplekml.Color.yellow
            pnt.style.iconstyle.scale = 2.0
            pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png'
        elif elem['type'] == 'Handhole':
            pnt.style.iconstyle.color = simplekml.Color.yellow
            pnt.style.iconstyle.scale = 1.0
            pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_square.png'
        elif elem['type'] == 'Cierre de Empalme':
            pnt.style.iconstyle.color = simplekml.Color.green
            pnt.style.iconstyle.scale = 1.0
            pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/target.png'
        elif elem['type'] == 'Edificio':
            pnt.style.iconstyle.color = simplekml.Color.orange
            pnt.style.iconstyle.scale = 1.0
            pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/homegardenbusiness.png'
        
        description_html = '<div style="font-family: Arial; font-size: 20px; max-width: 800px;">'
        description_html += f'<h1 style="color: #2c3e50; margin-bottom: 15px; font-size: 28px;">{elem["type"]}</h1>'
        if 'photo' in elem and elem['photo']:
            description_html += f'<img src="data:image/jpeg;base64,{elem["photo"]}" style="max-width: 600px; max-height: 500px; margin: 15px 0; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"/><br/>'
        description_html += '<table style="border-collapse: collapse; width: 100%; margin-top: 15px;">'
        for key, value in elem.items():
            if key not in ['lat', 'lon', 'name', 'type', 'photo']:
                description_html += f'<tr style="border-bottom: 2px solid #ddd;"><td style="padding: 12px; font-weight: bold; background-color: #f2f2f2; width: 40%; font-size: 18px;">{key}:</td><td style="padding: 12px; font-size: 18px;">{value}</td></tr>'
        description_html += '</table>'
        description_html += f'<p style="margin-top: 20px; color: #7f8c8d; font-size: 16px;"><strong>Coordenadas:</strong><br/>Lat: {elem["lat"]:.6f}<br/>Lon: {elem["lon"]:.6f}</p></div>'
        pnt.description = description_html
    
    for conn in st.session_state.connections:
        elem_a = next((e for e in st.session_state.elements if e['name'] == conn['element_a']), None)
        elem_b = next((e for e in st.session_state.elements if e['name'] == conn['element_b']), None)
        if elem_a and elem_b:
            line = kml.newlinestring(name=f"{conn['element_a']} - {conn['element_b']}")
            line.coords = [(elem_a['lon'], elem_a['lat']), (elem_b['lon'], elem_b['lat'])]
            if conn['construction_type'] == 'Ducto':
                line.style.linestyle.color = simplekml.Color.blue
                line.style.linestyle.width = 4
            elif conn['construction_type'] == 'Aerial Route':
                line.style.linestyle.color = simplekml.Color.green
                line.style.linestyle.width = 4
            elif conn['construction_type'] == 'ADSS':
                line.style.linestyle.color = simplekml.Color.red
                line.style.linestyle.width = 4
            infra_status = conn.get('infraestructura', 'N/A')
            line.description = f'<div style="font-family: Arial; font-size: 20px;"><h2 style="color: #2c3e50; font-size: 26px;">Conexión</h2><table style="border-collapse: collapse; width: 100%;"><tr style="border-bottom: 2px solid #ddd;"><td style="padding: 12px; font-weight: bold; background-color: #f2f2f2; font-size: 18px;">Tipo:</td><td style="padding: 12px; font-size: 18px;">{conn["construction_type"]}</td></tr><tr style="border-bottom: 2px solid #ddd;"><td style="padding: 12px; font-weight: bold; background-color: #f2f2f2; font-size: 18px;">Infraestructura:</td><td style="padding: 12px; font-size: 18px;">{infra_status}</td></tr><tr style="border-bottom: 2px solid #ddd;"><td style="padding: 12px; font-weight: bold; background-color: #f2f2f2; font-size: 18px;">Distancia:</td><td style="padding: 12px; font-size: 18px;">{conn["distance"]:.2f} metros</td></tr></table></div>'
    return kml.kml()

# CSS
st.markdown("""
<style>
    .stButton button {width: 100%; border-radius: 8px; font-weight: 600; padding: 0.5rem;}
</style>
""", unsafe_allow_html=True)

# Título
st.title("📡 Site Survey")

# Información del proyecto
with st.expander("📋 Información del Proyecto", expanded=not st.session_state.project_name):
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Proyecto", value=st.session_state.project_name, placeholder="Nombre del proyecto")
    with col2:
        task_name = st.text_input("Tarea", value=st.session_state.task_name, placeholder="Nombre de la tarea")
    
    st.session_state.auto_connect = st.checkbox("🔗 Crear conexiones automáticamente", value=st.session_state.auto_connect)
    
    # Selector de tipo de mapa
    map_layer_option = st.selectbox("🗺️ Tipo de Mapa", ["Híbrido (Satélite + Calles)", "Satélite", "Satélite Google", "Mapa Calles", "Terreno"], index=0, key="map_layer_selector")
    layer_map = {"Híbrido (Satélite + Calles)": "hybrid", "Satélite": "satellite", "Satélite Google": "satellite_google", "Mapa Calles": "streets", "Terreno": "terrain"}
    st.session_state.selected_map_layer = layer_map[map_layer_option]
    
    # Ubicación manual simple
    with st.expander("📍 Establecer Mi Ubicación"):
        st.info("Ingresa tus coordenadas GPS actuales para crear elementos en tu posición")
        col1, col2 = st.columns(2)
        with col1:
            manual_lat = st.number_input("Latitud", value=31.737974, format="%.6f", step=0.000001)
        with col2:
            manual_lon = st.number_input("Longitud", value=-106.433306, format="%.6f", step=0.000001)
        
        if st.button("✅ Guardar Mi Ubicación", use_container_width=True, type="primary"):
            st.session_state.user_location = {'lat': manual_lat, 'lon': manual_lon, 'accuracy': 50}
            st.session_state.temp_location = {'lat': manual_lat, 'lon': manual_lon}
            st.success(f"✅ Tu ubicación: {manual_lat:.6f}, {manual_lon:.6f}")
            st.rerun()
    
    # Mostrar ubicación guardada
    if st.session_state.user_location and isinstance(st.session_state.user_location, dict):
        if 'lat' in st.session_state.user_location and 'lon' in st.session_state.user_location:
            st.success(f"📍 Ubicación activa: {st.session_state.user_location['lat']:.6f}, {st.session_state.user_location['lon']:.6f}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📌 Crear Elemento en Mi Ubicación", use_container_width=True):
                    st.session_state.temp_location = {'lat': st.session_state.user_location['lat'], 'lon': st.session_state.user_location['lon']}
                    st.session_state.show_element_form = True
                    st.rerun()
            with col2:
                if st.button("🗑️ Limpiar Ubicación", use_container_width=True):
                    st.session_state.user_location = None
                    st.rerun()
    
    if project_name != st.session_state.project_name:
        st.session_state.project_name = project_name
    if task_name != st.session_state.task_name:
        st.session_state.task_name = task_name

# Mapa
st.subheader("🗺️ Mapa de Ubicaciones")

# Centrar mapa
if st.session_state.elements:
    last_elem = st.session_state.elements[-1]
    st.session_state.map_center = [last_elem['lat'], last_elem['lon']]
elif st.session_state.temp_location:
    st.session_state.map_center = [st.session_state.temp_location['lat'], st.session_state.temp_location['lon']]
elif st.session_state.user_location and isinstance(st.session_state.user_location, dict):
    if 'lat' in st.session_state.user_location and 'lon' in st.session_state.user_location:
        st.session_state.map_center = [st.session_state.user_location['lat'], st.session_state.user_location['lon']]

# Crear mapa con capa seleccionada
m = folium.Map(location=st.session_state.map_center, zoom_start=18, zoom_control=True, scrollWheelZoom=True, dragging=True, prefer_canvas=True)
selected_layer = st.session_state.get('selected_map_layer', 'hybrid')
if selected_layer == 'streets':
    folium.TileLayer('OpenStreetMap', name='Mapa Calles').add_to(m)
elif selected_layer == 'satellite':
    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
elif selected_layer == 'satellite_google':
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Satélite Google').add_to(m)
elif selected_layer == 'terrain':
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', attr='Google', name='Terreno').add_to(m)
else:
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Híbrido').add_to(m)

# Agregar elementos
for elem in st.session_state.elements:
    style = get_element_style(elem['type'])
    folium.Marker([elem['lat'], elem['lon']], popup=f"<b>{elem['name']}</b><br>{elem['type']}", tooltip=elem['name'], icon=folium.Icon(color=style['color'], icon=style['icon'])).add_to(m)

# Agregar conexiones
for conn in st.session_state.connections:
    elem_a = next((e for e in st.session_state.elements if e['name'] == conn['element_a']), None)
    elem_b = next((e for e in st.session_state.elements if e['name'] == conn['element_b']), None)
    if elem_a and elem_b:
        color = 'blue' if conn['construction_type'] == 'Ducto' else 'red' if conn['construction_type'] == 'Aerial Route' else 'green'
        folium.PolyLine([[elem_a['lat'], elem_a['lon']], [elem_b['lat'], elem_b['lon']]], color=color, weight=3, opacity=0.7, popup=f"{conn['construction_type']}<br>{conn['distance']:.2f} m").add_to(m)

# Marcador temporal
if st.session_state.temp_location:
    folium.Marker([st.session_state.temp_location['lat'], st.session_state.temp_location['lon']], popup="📍 Nueva ubicación", tooltip="Nueva ubicación", icon=folium.Icon(color='lightgreen', icon='star', prefix='fa')).add_to(m)

# Marcador ubicación usuario (azul)
if st.session_state.user_location and isinstance(st.session_state.user_location, dict):
    if 'lat' in st.session_state.user_location and 'lon' in st.session_state.user_location:
        folium.Marker([st.session_state.user_location['lat'], st.session_state.user_location['lon']], popup="📍 Tu Ubicación", tooltip="Tu ubicación", icon=folium.Icon(color='blue', icon='user', prefix='fa')).add_to(m)
        accuracy = st.session_state.user_location.get('accuracy', 50)
        if accuracy > 0:
            folium.Circle([st.session_state.user_location['lat'], st.session_state.user_location['lon']], radius=accuracy, color='blue', fill=True, fillColor='blue', fillOpacity=0.2, popup=f"Precisión: {accuracy:.1f} m").add_to(m)

map_data = st_folium(m, width=None, height=400, returned_objects=["last_clicked"], key=f"map_{st.session_state.selected_map_layer}")

# Capturar click
if map_data and map_data.get('last_clicked'):
    clicked_lat = map_data['last_clicked']['lat']
    clicked_lon = map_data['last_clicked']['lng']
    is_new_click = True
    if st.session_state.temp_location:
        lat_diff = abs(st.session_state.temp_location['lat'] - clicked_lat)
        lon_diff = abs(st.session_state.temp_location['lon'] - clicked_lon)
        is_new_click = (lat_diff > 0.00001 or lon_diff > 0.00001)
    if is_new_click:
        st.session_state.temp_location = {'lat': clicked_lat, 'lon': clicked_lon}
        st.session_state.show_element_form = True
        st.rerun()

# Formulario crear elemento
if st.session_state.show_element_form and st.session_state.temp_location:
    st.success(f"📍 Ubicación seleccionada: {st.session_state.temp_location['lat']:.6f}, {st.session_state.temp_location['lon']:.6f}")
    is_from_gps = False
    if st.session_state.user_location and isinstance(st.session_state.user_location, dict):
        if 'lat' in st.session_state.user_location:
            is_from_gps = (abs(st.session_state.temp_location['lat'] - st.session_state.user_location['lat']) < 0.00001 and abs(st.session_state.temp_location['lon'] - st.session_state.user_location['lon']) < 0.00001)
    if is_from_gps:
        st.info("🔵 Ubicación GPS (Tu posición actual)")
    else:
        st.info("🟢 Ubicación desde click en el mapa")
    
    with st.container():
        st.subheader("➕ Crear Nuevo Elemento")
        if not st.session_state.project_name:
            st.warning("⚠️ Ingresa el nombre del proyecto primero")
        else:
            element_type = st.selectbox("Tipo de Elemento", ["Poste", "Handhole", "Cierre de Empalme", "Edificio"], key="elem_type")
            new_element = {'type': element_type, 'name': get_next_element_name(element_type), 'lat': st.session_state.temp_location['lat'], 'lon': st.session_state.temp_location['lon'], 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            st.info(f"📝 Nombre: **{new_element['name']}**")
            
            if element_type == "Poste":
                col1, col2 = st.columns(2)
                with col1:
                    new_element['dueño'] = st.selectbox("Dueño", ["CFE", "ATC", "Flo Networks", "Maxcom", "XC Networks", "Municipio", "Parque Industrial", "Privado"])
                    new_element['altura'] = st.selectbox("Altura (m)", [6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
                    new_element['id_cfe'] = st.text_input("ID de CFE")
                with col2:
                    new_element['usado_por'] = st.multiselect("Usado por", ["ATC", "Flo Networks", "Maxcom", "XC Networks", "Otro"], default=["Flo Networks"])
                    new_element['material'] = st.selectbox("Material", ["Concreto", "Madera", "Metal"])
                    new_element['tipo_construccion'] = st.selectbox("Tipo", ["Poste nuevo", "Poste ya utilizado por Infra", "Poste sin utilizar por nuestra Infra"])
                
            elif element_type == "Handhole":
                col1, col2 = st.columns(2)
                with col1:
                    new_element['dueño'] = st.selectbox("Dueño", ["CFE", "ATC", "Flo Networks", "Maxcom", "XC Networks", "Municipio", "Parque Industrial", "Privado"])
                    new_element['dimensiones'] = st.selectbox("Dimensiones", ["24x24x24", "24x36x24", "48x48x48", "Otro"])
                with col2:
                    new_element['usado_por'] = st.multiselect("Usado por", ["ATC", "Flo Networks", "Maxcom", "XC Networks", "Otro"], default=["Flo Networks"])
                    new_element['instalado_en'] = st.selectbox("Instalado en", ["Banqueta", "Arroyo", "Propiedad Privada"])
                
            elif element_type == "Cierre de Empalme":
                col1, col2 = st.columns(2)
                with col1:
                    new_element['estado'] = st.selectbox("Estado", ["Nuevo", "Existente"])
                with col2:
                    new_element['nombre_cierre'] = st.text_input("Nombre del Cierre")
                
            elif element_type == "Edificio":
                new_element['direccion'] = st.text_area("Dirección Completa", height=60)
                col1, col2 = st.columns(2)
                with col1:
                    new_element['nombre_edificio'] = st.text_input("Nombre de Edificio")
                    new_element['piso'] = st.text_input("Piso del Cliente")
                with col2:
                    new_element['suite'] = st.text_input("Suite del Cliente")
                    new_element['datos_adicionales'] = st.text_input("Datos Adicionales")
            
            st.write("**📷 Capturar Foto**")
            camera_photo = st.camera_input("Tomar foto con cámara", key="camera_input")
            if camera_photo is not None:
                new_element['photo'] = base64.b64encode(camera_photo.read()).decode()
                st.success("✅ Foto capturada")
            else:
                uploaded_photo = st.file_uploader("O subir foto existente", type=['png', 'jpg', 'jpeg'], key="photo_upload")
                if uploaded_photo is not None:
                    new_element['photo'] = base64.b64encode(uploaded_photo.read()).decode()
                    st.success("✅ Foto subida")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Guardar Elemento", type="primary", use_container_width=True):
                    st.session_state.elements.append(new_element)
                    if st.session_state.auto_connect and len(st.session_state.elements) > 1:
                        prev_elem = st.session_state.elements[-2]
                        curr_elem = st.session_state.elements[-1]
                        create_auto_connection(prev_elem, curr_elem)
                        st.success(f"✅ {element_type} guardado y conectado: {new_element['name']}")
                    else:
                        st.success(f"✅ {element_type} guardado: {new_element['name']}")
                    st.session_state.temp_location = None
                    st.session_state.show_element_form = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.temp_location = None
                    st.session_state.show_element_form = False
                    st.rerun()

# Elementos capturados
if st.session_state.elements:
    st.divider()
    st.subheader("📊 Elementos Capturados")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric("Total elementos", len(st.session_state.elements))
    with col2:
        if st.button("🔄 Reconectar Todo", use_container_width=True):
            st.session_state.connections = []
            for i in range(len(st.session_state.elements) - 1):
                create_auto_connection(st.session_state.elements[i], st.session_state.elements[i + 1])
            st.success("✅ Conexiones recreadas")
            st.rerun()
    
    postes = [e for e in st.session_state.elements if e['type'] == 'Poste']
    handholes = [e for e in st.session_state.elements if e['type'] == 'Handhole']
    cierres = [e for e in st.session_state.elements if e['type'] == 'Cierre de Empalme']
    edificios = [e for e in st.session_state.elements if e['type'] == 'Edificio']
    
    if postes:
        with st.expander(f"🔴 Postes ({len(postes)})", expanded=True):
            df_postes = pd.DataFrame(postes)
            display_cols = [col for col in df_postes.columns if col != 'photo']
            edited_postes = st.data_editor(df_postes[display_cols], use_container_width=True, hide_index=True, num_rows="dynamic", key="postes_editor")
            if st.button("💾 Guardar Cambios Postes", type="primary", use_container_width=True, key="save_postes"):
                for idx, row in edited_postes.iterrows():
                    elem_idx = next(i for i, e in enumerate(st.session_state.elements) if e['name'] == row['name'])
                    for col in display_cols:
                        if col in row:
                            st.session_state.elements[elem_idx][col] = row[col]
                st.success("✅ Cambios guardados")
                st.rerun()
    
    if handholes:
        with st.expander(f"🔵 Handholes ({len(handholes)})", expanded=True):
            df_handholes = pd.DataFrame(handholes)
            display_cols = [col for col in df_handholes.columns if col != 'photo']
            edited_handholes = st.data_editor(df_handholes[display_cols], use_container_width=True, hide_index=True, num_rows="dynamic", key="handholes_editor")
            if st.button("💾 Guardar Cambios Handholes", type="primary", use_container_width=True, key="save_handholes"):
                for idx, row in edited_handholes.iterrows():
                    elem_idx = next(i for i, e in enumerate(st.session_state.elements) if e['name'] == row['name'])
                    for col in display_cols:
                        if col in row:
                            st.session_state.elements[elem_idx][col] = row[col]
                st.success("✅ Cambios guardados")
                st.rerun()
    
    if cierres:
        with st.expander(f"🟢 Cierres de Empalme ({len(cierres)})", expanded=True):
            df_cierres = pd.DataFrame(cierres)
            display_cols = [col for col in df_cierres.columns if col != 'photo']
            edited_cierres = st.data_editor(df_cierres[display_cols], use_container_width=True, hide_index=True, num_rows="dynamic", key="cierres_editor")
            if st.button("💾 Guardar Cambios Cierres", type="primary", use_container_width=True, key="save_cierres"):
                for idx, row in edited_cierres.iterrows():
                    elem_idx = next(i for i, e in enumerate(st.session_state.elements) if e['name'] == row['name'])
                    for col in display_cols:
                        if col in row:
                            st.session_state.elements[elem_idx][col] = row[col]
                st.success("✅ Cambios guardados")
                st.rerun()
    
    if edificios:
        with st.expander(f"🟠 Edificios ({len(edificios)})", expanded=True):
            df_edificios = pd.DataFrame(edificios)
            display_cols = [col for col in df_edificios.columns if col != 'photo']
            edited_edificios = st.data_editor(df_edificios[display_cols], use_container_width=True, hide_index=True, num_rows="dynamic", key="edificios_editor")
            if st.button("💾 Guardar Cambios Edificios", type="primary", use_container_width=True, key="save_edificios"):
                for idx, row in edited_edificios.iterrows():
                    elem_idx = next(i for i, e in enumerate(st.session_state.elements) if e['name'] == row['name'])
                    for col in display_cols:
                        if col in row:
                            st.session_state.elements[elem_idx][col] = row[col]
                st.success("✅ Cambios guardados")
                st.rerun()
    
    with st.expander("🗑️ Eliminar Elemento"):
        element_to_delete = st.selectbox("Seleccionar elemento", [""] + [e['name'] for e in st.session_state.elements])
        if element_to_delete and st.button("Confirmar Eliminación", type="primary"):
            st.session_state.elements = [e for e in st.session_state.elements if e['name'] != element_to_delete]
            st.session_state.connections = [c for c in st.session_state.connections if c['element_a'] != element_to_delete and c['element_b'] != element_to_delete]
            st.success(f"✅ {element_to_delete} eliminado")
            st.rerun()

# Conexiones
if st.session_state.connections:
    st.divider()
    st.subheader("🔗 Conexiones")
    total_distance = sum(c['distance'] for c in st.session_state.connections)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total conexiones", len(st.session_state.connections))
    with col2:
        st.metric("Distancia total", f"{total_distance:.2f} m")
    
    df_connections = pd.DataFrame(st.session_state.connections)
    df_connections['distance'] = df_connections['distance'].round(2)
    if 'infraestructura' not in df_connections.columns:
        df_connections['infraestructura'] = 'Nuevo'
    cols_order = ['element_a', 'element_b', 'construction_type', 'infraestructura', 'distance']
    df_connections = df_connections[cols_order]
    
    edited_connections = st.data_editor(df_connections, use_container_width=True, hide_index=True, num_rows="dynamic", key="connections_editor",
        column_config={
            "element_a": st.column_config.TextColumn("Elemento A"),
            "element_b": st.column_config.TextColumn("Elemento B"),
            "construction_type": st.column_config.SelectboxColumn("Tipo Construcción", options=["Aerial Route", "ADSS", "Ducto"]),
            "infraestructura": st.column_config.SelectboxColumn("Infraestructura", options=["Existente", "Nuevo"], required=True),
            "distance": st.column_config.NumberColumn("Distancia (m)", format="%.2f")
        })
    
    col_save, col_delete = st.columns(2)
    with col_save:
        if st.button("💾 Guardar Cambios Conexiones", type="primary", use_container_width=True):
            st.session_state.connections = edited_connections.to_dict('records')
            st.success("✅ Cambios guardados")
            st.rerun()
    with col_delete:
        if st.button("🗑️ Limpiar todas", use_container_width=True):
            st.session_state.connections = []
            st.success("✅ Conexiones eliminadas")
            st.rerun()

# Agregar conexión manual
if len(st.session_state.elements) >= 2:
    st.divider()
    with st.expander("➕ Agregar Conexión Manual"):
        element_names = [e['name'] for e in st.session_state.elements]
        col1, col2 = st.columns(2)
        with col1:
            elem_a_name = st.selectbox("Elemento A", element_names, key="manual_conn_a")
        with col2:
            elem_b_name = st.selectbox("Elemento B", [e for e in element_names if e != elem_a_name], key="manual_conn_b")
        elem_a = next((e for e in st.session_state.elements if e['name'] == elem_a_name), None)
        elem_b = next((e for e in st.session_state.elements if e['name'] == elem_b_name), None)
        suggested_type = suggest_construction_type(elem_a['type'], elem_b['type']) if elem_a and elem_b else "Aerial Route"
        col1, col2 = st.columns(2)
        with col1:
            construction_type = st.selectbox("Tipo de Construcción", ["Aerial Route", "ADSS", "Ducto"], index=["Aerial Route", "ADSS", "Ducto"].index(suggested_type), key="manual_conn_type")
        with col2:
            infraestructura = st.selectbox("Infraestructura", ["Nuevo", "Existente"], key="manual_conn_infra")
        if st.button("Crear Conexión Manual", type="primary", use_container_width=True, key="manual_conn_btn"):
            if elem_a and elem_b:
                distance = calculate_distance(elem_a['lat'], elem_a['lon'], elem_b['lat'], elem_b['lon'])
                st.session_state.connections.append({'element_a': elem_a_name, 'element_b': elem_b_name, 'construction_type': construction_type, 'infraestructura': infraestructura, 'distance': distance})
                st.success(f"✅ Conexión creada: {distance:.2f} m")
                st.rerun()

# Exportación
if st.session_state.elements:
    st.divider()
    st.subheader("📤 Exportar")
    col1, col2, col3 = st.columns(3)
    with col1:
        df_export = pd.DataFrame(st.session_state.elements)
        csv = df_export.to_csv(index=False)
        st.download_button("📄 CSV Elementos", data=csv, file_name=f"{st.session_state.project_name}_elementos.csv", mime="text/csv", use_container_width=True)
    with col2:
        if st.session_state.connections:
            df_conn = pd.DataFrame(st.session_state.connections)
            csv_conn = df_conn.to_csv(index=False)
            st.download_button("📄 CSV Conexiones", data=csv_conn, file_name=f"{st.session_state.project_name}_conexiones.csv", mime="text/csv", use_container_width=True)
    with col3:
        try:
            kml_content = export_to_kml()
            st.download_button("🗺️ KML", data=kml_content, file_name=f"{st.session_state.project_name}_survey.kml", mime="application/vnd.google-earth.kml+xml", use_container_width=True)
        except:
            st.button("🗺️ KML", disabled=True, use_container_width=True)

st.divider()
st.caption(f"Site Survey - {st.session_state.project_name or 'Sin proyecto'} | {len(st.session_state.elements)} elementos | {len(st.session_state.connections)} conexiones")
