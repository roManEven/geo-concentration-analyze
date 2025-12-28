import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# Конфигурация бэкенда
BACKEND_URL = st.secrets["MY_BACKEND_LINK"] + "/analyze"

# Конфигурация страницы
st.set_page_config(
    page_title="Картограф",
    layout="wide",
    page_icon="🗺️"
)

# Инициализация состояния сессии
if "results" not in st.session_state:
    st.session_state.results = None

# Заголовок приложения
st.title("🗺️ Глобальный анализатор географических данных")

# Боковая панель с настройками
with st.sidebar:
    st.header("⚙️ Настройки анализа")
    
    radius = st.number_input(
        "Радиус кластеризации (м)",
        min_value=10,
        value=500,
        help="Радиус для поиска соседних точек"
    )
    
    min_points = st.number_input(
        "Минимальное количество точек",
        min_value=1,
        value=5,
        help="Минимальное количество точек для формирования зоны"
    )
    
    st.markdown("---")
    
    if st.button("🗑️ Очистить результаты", type="secondary", use_container_width=True):
        st.session_state.results = None
        st.rerun()

# Область загрузки файла
st.subheader("📤 Загрузка данных")
uploaded_file = st.file_uploader(
    "Загрузите Excel файл с координатами",
    type=["xlsx"],
    help="Файл должен содержать колонки с координатами (широта и долгота)"
)

# Кнопка запуска анализа
if uploaded_file:
    st.success(f"✅ Файл загружен: **{uploaded_file.name}**")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Запуск анализа", type="primary", use_container_width=True):
            with st.spinner("🔍 Анализируем данные..."):
                try:
                    # Подготовка файла для отправки
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    }
                    
                    # Параметры запроса
                    payload = {
                        "radius": radius,
                        "min_points": min_points
                    }
                    
                    # Отправка запроса на бэкенд
                    response = requests.post(
                        BACKEND_URL,
                        files=files,
                        data=payload,
                        timeout=30
                    )
                    
                    # Обработка ответа
                    if response.status_code == 200:
                        st.session_state.results = response.json()
                        st.success("✅ Анализ успешно завершен!")
                    else:
                        st.error(f"❌ Ошибка сервера: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    st.error("⏱️ Превышено время ожидания ответа")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Ошибка подключения к серверу")
                except Exception as e:
                    st.error(f"⚠️ Ошибка: {str(e)}")

# Отображение результатов
if st.session_state.results:
    res = st.session_state.results
    
    if res.get("status") == "ok":
        # Определение начальной позиции карты
        if res.get("all_points") and len(res["all_points"]) > 0:
            start_pos = res["all_points"][0]
        else:
            start_pos = [55.75, 37.62]  # Москва по умолчанию
        
        # СОЗДАНИЕ КАРТЫ С OPENSTREETMAP
        m = folium.Map(
            location=start_pos,
            zoom_start=11,
            tiles='OpenStreetMap',
            attr='© OpenStreetMap contributors',
            control_scale=True,
            attribution_control=False  # Убираем нижнюю подпись
        )
        
        # Отображение статистики
        if res.get("all_points"):
            points_count = len(res["all_points"])
            st.caption(f"📊 Всего точек: **{points_count}**")
        
        if res.get("zones"):
            zones_count = len(res["zones"])
            st.caption(f"📍 Найдено зон концентрации: **{zones_count}**")
        
        # Отображение всех точек
        if res.get("all_points"):
            for point in res["all_points"]:
                folium.CircleMarker(
                    location=point,
                    radius=3,
                    color="#1E88E5",
                    fill=True,
                    fill_color="#1E88E5",
                    fill_opacity=0.7,
                    weight=1
                ).add_to(m)
        
        # Отображение зон концентрации
        if res.get("zones"):
            for i, zone in enumerate(res["zones"], 1):
                # Всплывающее окно с информацией
                popup_text = f"""
                <div style='font-family: Arial; min-width: 180px;'>
                    <h4 style='margin-bottom: 8px;'>Зона {i}</h4>
                    <p style='margin: 5px 0;'><b>Точек:</b> {zone['count']}</p>
                    <p style='margin: 5px 0;'><b>Центр:</b></p>
                    <p style='margin: 5px 0; font-size: 12px;'>
                        {zone['center'][0]:.6f}, {zone['center'][1]:.6f}
                    </p>
                </div>
                """
                
                # Маркер центра зоны
                folium.Marker(
                    location=zone["center"],
                    popup=folium.Popup(popup_text, max_width=250),
                    icon=folium.Icon(
                        color="red",
                        icon="info-sign",
                        prefix="fa"
                    ),
                    tooltip=f"Зона {i}"
                ).add_to(m)
                
                # Область зоны
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
        st_folium(
            m,
            width="100%",
            height=650,
            returned_objects=[]
        )
        
        # Таблица с результатами
        if res.get("zones"):
            st.subheader("📋 Детализация зон концентрации")
            
            # Подготовка данных для таблицы
            zones_data = []
            for i, zone in enumerate(res["zones"], 1):
                zones_data.append({
                    "№": i,
                    "Широта центра": f"{zone['center'][0]:.6f}",
                    "Долгота центра": f"{zone['center'][1]:.6f}",
                    "Количество точек": zone['count'],
                    "Радиус (м)": radius
                })
            
            zones_df = pd.DataFrame(zones_data)
            
            # Отображение таблицы
            st.dataframe(
                zones_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "№": st.column_config.NumberColumn(width="small"),
                    "Количество точек": st.column_config.NumberColumn(width="medium"),
                    "Радиус (м)": st.column_config.NumberColumn(width="medium")
                }
            )
            
            # Кнопка для скачивания результатов
            csv_data = zones_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Скачать результаты (CSV)",
                data=csv_data,
                file_name="анализ_зон.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    elif res.get("status") == "error":
        st.error(f"❌ Ошибка при обработке: {res.get('message', 'Неизвестная ошибка')}")
    
    else:
        st.warning("⚠️ Неизвестный формат ответа от сервера")

# Футер приложения
st.markdown("---")
st.caption("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    Картограф • Система анализа географических данных • Версия 1.0
</div>
""", unsafe_allow_html=True)
