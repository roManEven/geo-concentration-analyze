import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# --- КОНФИГУРАЦИЯ ---
BACKEND_URL = st.secrets["MY_BACKEND_LINK"] + "/analyze"

st.set_page_config(
    page_title="Картограф концентраций",
    layout="wide",
    page_icon="🗺️"
)

# Инициализация состояния
if "results" not in st.session_state:
    st.session_state.results = None

st.title("🗺️ Анализатор географических концентраций")
st.info("📍 Загрузите Excel-файл с координатами для анализа зон концентрации")

# --- ПАРАМЕТРЫ В БОКОВОЙ ПАНЕЛИ ---
with st.sidebar:
    st.header("⚙️ Настройки анализа")
    
    radius = st.number_input(
        "Радиус зоны (метры)",
        min_value=10,
        max_value=5000,
        value=500,
        help="Радиус поиска соседних точек"
    )
    
    min_points = st.number_input(
        "Мин. точек для зоны",
        min_value=1,
        max_value=100,
        value=5,
        help="Минимальное количество точек для формирования зоны"
    )
    
    st.markdown("---")
    
    if st.button("🗑️ Сбросить всё", use_container_width=True, type="secondary"):
        st.session_state.results = None
        st.rerun()

# --- ЗАГРУЗКА И ОТПРАВКА ---
uploaded_file = st.file_uploader(
    "Загрузите файл Excel (.xlsx)",
    type=["xlsx"],
    help="Файл должен содержать колонки с координатами"
)

if uploaded_file:
    st.success(f"✅ Файл загружен: **{uploaded_file.name}**")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Запустить анализ", type="primary", use_container_width=True):
            with st.spinner("⏳ Файл обрабатывается..."):
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    }
                    
                    payload = {
                        "radius": radius,
                        "min_points": min_points
                    }

                    response = requests.post(
                        BACKEND_URL,
                        files=files,
                        data=payload,
                        timeout=30
                    )

                    if response.status_code == 200:
                        st.session_state.results = response.json()
                        st.success("✅ Данные успешно получены!")
                    else:
                        st.error(f"❌ Ошибка связи: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    st.error("⏱️ Превышено время ожидания ответа")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Не удалось подключиться к серверу")
                except Exception as e:
                    st.error(f"⚠️ Ошибка: {str(e)}")

# --- ВИЗУАЛИЗАЦИЯ РЕЗУЛЬТАТОВ ---
if st.session_state.results:
    res = st.session_state.results

    if res.get("status") == "ok":
        # --- МЕТРИКИ ---
        col1, col2, col3 = st.columns(3)
        
        total_points = res.get("total_parsed", 
                              len(res.get("all_points", [])) if res.get("all_points") else 0)
        zones_count = len(res.get("zones", []))
        
        with col1:
            st.metric("Всего точек", total_points)
        with col2:
            st.metric("Найдено зон", zones_count)
        with col3:
            st.metric("Радиус анализа", f"{radius} м")
        
        st.markdown("---")
        
        # --- СОЗДАНИЕ КАРТЫ ---
        # Центрируем на первой точке или на Москве по умолчанию
        if res.get("all_points") and len(res["all_points"]) > 0:
            start_pos = res["all_points"][0]
        else:
            start_pos = [55.75, 37.62]  # Москва по умолчанию
        
        # Создаем карту с OpenStreetMap
        m = folium.Map(
            location=start_pos,
            zoom_start=11,
            tiles='OpenStreetMap',
            attr='© OpenStreetMap contributors',
            control_scale=True,
            attribution_control=False
        )
        
        # 1. Рисуем все исходные точки (маленькие синие кружки)
        if res.get("all_points"):
            for point in res["all_points"]:
                folium.CircleMarker(
                    location=point,
                    radius=3,
                    color="#1E88E5",
                    fill=True,
                    fill_color="#1E88E5",
                    fill_opacity=0.4,
                    weight=1
                ).add_to(m)
        
        # 2. Рисуем зоны концентрации с адресами
        if res.get("zones"):
            for i, zone in enumerate(res["zones"], 1):
                # Получаем адрес из зоны (если есть)
                address = zone.get('address', 'Адрес не определен')
                
                # Форматируем всплывающее окно
                popup_text = f"""
                <div style='font-family: Arial; width: 220px;'>
                    <h4 style='margin-bottom: 8px; color: #D32F2F;'>Зона №{i}</h4>
                    <p style='margin: 5px 0;'><b>📊 Точек:</b> {zone['count']}</p>
                    <p style='margin: 5px 0;'><b>📍 Центр:</b></p>
                    <p style='margin: 2px 0; font-size: 12px;'>
                        {zone['center'][0]:.6f}, {zone['center'][1]:.6f}
                    </p>
                    <p style='margin: 5px 0;'><b>🏠 Адрес:</b></p>
                    <p style='margin: 2px 0; font-size: 12px; color: #555;'>
                        {address}
                    </p>
                </div>
                """
                
                # Маркер центра зоны
                folium.Marker(
                    location=zone["center"],
                    popup=folium.Popup(popup_text, max_width=250),
                    tooltip=f"Зона {i} ({zone['count']} точек)",
                    icon=folium.Icon(color="red", icon="star", prefix="fa")
                ).add_to(m)
                
                # Круг радиуса зоны
                folium.Circle(
                    location=zone["center"],
                    radius=radius,
                    color="#D32F2F",
                    fill=True,
                    fill_color="#D32F2F",
                    fill_opacity=0.15,
                    weight=2,
                    dash_array="5, 5"
                ).add_to(m)
        
        # Отображение карты
        st.subheader("🗺️ Интерактивная карта результатов")
        st_folium(
            m,
            width="100%",
            height=650,
            returned_objects=[]
        )
        
        # --- ТАБЛИЦА РЕЗУЛЬТАТОВ ---
        if res.get("zones"):
            st.markdown("---")
            st.subheader("📋 Список зон концентрации")
            
            # Подготавливаем данные для таблицы
            zones_data = []
            for i, zone in enumerate(res["zones"], 1):
                zones_data.append({
                    "№ зоны": i,
                    "Широта центра": f"{zone['center'][0]:.6f}",
                    "Долгота центра": f"{zone['center'][1]:.6f}",
                    "Количество точек": zone['count'],
                    "Адрес": zone.get('address', 'Не определен'),
                    "Радиус (м)": radius
                })
            
            zones_df = pd.DataFrame(zones_data)
            
            # Настройка отображения таблицы
            st.dataframe(
                zones_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "№ зоны": st.column_config.NumberColumn(width="small"),
                    "Количество точек": st.column_config.NumberColumn(width="medium"),
                    "Радиус (м)": st.column_config.NumberColumn(width="small"),
                    "Адрес": st.column_config.TextColumn(width="large")
                }
            )
            
            # Кнопка для экспорта результатов
            csv_data = zones_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Скачать результаты (CSV)",
                data=csv_data,
                file_name="зоны_концентрации.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    elif res.get("status") == "error":
        st.error(f"❌ Ошибка при обработке: {res.get('message', 'Неизвестная ошибка')}")
    
    else:
        st.warning("⚠️ Неизвестный формат ответа от сервера")

# --- ПОДВАЛ ---
st.markdown("---")
st.caption("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    Картограф концентраций • Анализ географических данных • Версия 2.0
</div>
""", unsafe_allow_html=True)
