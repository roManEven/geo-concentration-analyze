import streamlit as st
import folium
import requests
import pandas as pd
from streamlit_folium import st_folium

# Конфигурация страницы
BACKEND_URL = st.secrets["MY_BACKEND_LINK"] + "/analyze"
st.set_page_config(page_title="Картограф", layout="wide")

# Инициализация состояния
if "results" not in st.session_state:
    st.session_state.results = None

st.title("📊 Глобальный анализатор")

# Боковая панель с настройками
with st.sidebar:
    st.header("⚙️ Настройки")
    
    radius = st.number_input(
        "Радиус (м)",
        min_value=10,
        value=500,
        help="Радиус для поиска соседних точек"
    )
    
    min_points = st.number_input(
        "Мин. точек",
        min_value=1,
        value=5,
        help="Минимальное количество точек для формирования зоны"
    )
    
    if st.button("🗑️ Сброс", use_container_width=True):
        st.session_state.results = None
        st.rerun()

# Загрузка файла
uploaded_file = st.file_uploader(
    "Загрузите Excel файл",
    type=["xlsx"],
    help="Поддерживаются только файлы формата .xlsx"
)

if uploaded_file:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Запуск анализа", type="primary", use_container_width=True):
            with st.spinner("Обработка данных..."):
                try:
                    # Подготовка файла для отправки
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    }
                    
                    # Подготовка параметров
                    payload = {
                        "radius": radius,
                        "min_points": min_points
                    }
                    
                    # Отправка запроса
                    response = requests.post(
                        BACKEND_URL,
                        files=files,
                        data=payload,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        st.session_state.results = response.json()
                        st.success("Анализ успешно завершен!")
                    else:
                        st.error(f"Ошибка связи с сервером: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    st.error("Превышено время ожидания ответа от сервера")
                except requests.exceptions.ConnectionError:
                    st.error("Не удалось подключиться к серверу")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# Отображение результатов
if st.session_state.results:
    res = st.session_state.results
    
    if res.get("status") == "ok":
        # Определяем начальную позицию карты
        if res.get("all_points") and len(res["all_points"]) > 0:
            start_pos = res["all_points"][0]
        else:
            start_pos = [55.75, 37.62]  # Координаты Москвы по умолчанию
        
        # Создаём карту БЕЗ логотипа Leaflet (attributionControl=False)
        m = folium.Map( location=start_pos, zoom_start=11, tiles='{x}&y={y}&z={z}', attr=' ', control_scale=True, attribution_control=False )
        
        # Отображаем все точки
        if res.get("all_points"):
            points_count = len(res["all_points"])
            st.caption(f"Общее количество точек: **{points_count}**")
            
            for point in res["all_points"]:
                folium.CircleMarker(
                    location=point,
                    radius=3,
                    color="blue",
                    fill=True,
                    fill_color="blue",
                    fill_opacity=0.7,
                    weight=1
                ).add_to(m)
        
        # Отображаем зоны
        if res.get("zones"):
            zones_count = len(res["zones"])
            st.caption(f"Найдено зон концентрации: **{zones_count}**")
            
            for i, zone in enumerate(res["zones"], 1):
                # Создаем всплывающее окно
                popup_text = f"""
                <div style='font-family: Arial, sans-serif;'>
                    <h4 style='margin-bottom: 8px;'>Зона {i}</h4>
                    <p style='margin: 4px 0;'><b>Количество точек:</b> {zone['count']}</p>
                    <p style='margin: 4px 0;'><b>Центр зоны:</b></p>
                    <p style='margin: 4px 0;'>
                        {zone['center'][0]:.6f}, {zone['center'][1]:.6f}
                    </p>
                </div>
                """
                
                # Маркер центра зоны
                folium.Marker(
                    location=zone["center"],
                    popup=folium.Popup(popup_text, max_width=250),
                    icon=folium.Icon(color="red", icon="info-sign"),
                    tooltip=f"Зона {i} ({zone['count']} точек)"
                ).add_to(m)
                
                # Круг зоны
                folium.Circle(
                    location=zone["center"],
                    radius=radius,
                    color="red",
                    fill=True,
                    fill_color="red",
                    fill_opacity=0.15,
                    weight=2,
                    dash_array="5, 5"
                ).add_to(m)
        
        # Отображаем карту в Streamlit
        st_folium(
            m,
            width="100%",
            height=650,
            returned_objects=[]
        )
        
        # Отображаем таблицу зон
        if res.get("zones"):
            st.subheader("📋 Результаты анализа зон")
            
            # Подготавливаем данные для таблицы
            zones_data = []
            for i, zone in enumerate(res["zones"], 1):
                zones_data.append({
                    "№ зоны": i,
                    "Широта центра": f"{zone['center'][0]:.6f}",
                    "Долгота центра": f"{zone['center'][1]:.6f}",
                    "Количество точек": zone['count']
                })
            
            zones_df = pd.DataFrame(zones_data)
            
            # Отображаем таблицу
            st.dataframe(
                zones_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "№ зоны": st.column_config.NumberColumn(width="small"),
                    "Количество точек": st.column_config.NumberColumn(width="medium"),
                }
            )
            
            # Добавляем возможность скачать результаты
            csv_data = zones_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Скачать результаты (CSV)",
                data=csv_data,
                file_name="zones_analysis.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    elif res.get("status") == "error":
        st.error(f"Ошибка при обработке данных: {res.get('message', 'Неизвестная ошибка')}")
    else:
        st.warning("Получен неожиданный формат ответа от сервера")

# Информация о приложении в футере
st.markdown("---")
st.caption("Картограф • Система анализа географических данных • v1.0")

